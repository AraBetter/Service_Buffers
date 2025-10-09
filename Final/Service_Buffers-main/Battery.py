# battery.py
from __future__ import annotations
from typing import Optional
import numpy as np
from dataclasses import dataclass

class Battery:
    """
    BESS para flujo de potencia (NR) con ÚNICAMENTE inyección P/Q.
    - P > 0  → descarga a la red (entrega MW)
    - P < 0  → carga desde la red (consume MW)
    - Q puede ser positivo/negativo (soporte de tensión)
    - Respeta límites P/Q y límite por S_rated (MVA)
    - SOC con eficiencias de carga/descarga
    - NO modifica Ybus (no shunt, no Norton)
    """

    EPS = 1e-9  # (1) Epsilon numérico para evitar micro-oscilaciones de signo

    def __init__(
        self,
        name: str,
        bus,                          # instancia Bus (con .name)
        S_base_MVA: float,            # base del sistema (p.ej., 100)
        S_rated_MVA: float = 20.0,    # rating del convertidor (MVA)
        E_rated_MWh: float = 40.0,    # energía útil (MWh)
        Pmin_MW: float = 0.0, Pmax_MW: float = 20.0,
        Qmin_Mvar: float = -10.0, Qmax_Mvar: float = 10.0,
        soc0: float = 0.95,
        eta_ch: float = 0.93,         # eficiencia de carga
        eta_dis: float = 0.96,        # eficiencia de descarga
        enabled: bool = True,
        controller: Optional[object] = None,  # se asignará luego por AutonomousController
        # Variables droop
        bus_name: str = "",
        V_ref_pu: float = 1.00,
        Kq_MVAr_per_pu: float = 60.0,
        P_ch_max_MW: float = 10.0,
        is_active: bool = True,
        sim_state: str = "prefault",
        Pref_MW: float = 0.0,
        mode: str = "DROOP",
    ):
        self.name = name
        self.bus = bus
        self.bus_name = bus_name or getattr(bus, 'name', str(bus))
        self.S_base = float(S_base_MVA)
        self.S_rated = float(S_rated_MVA)
        self.E_rated = float(E_rated_MWh)

        self.Pmin = float(Pmin_MW); self.Pmax = float(Pmax_MW)
        self.Qmin = float(Qmin_Mvar); self.Qmax = float(Qmax_Mvar)

        self.soc = float(soc0)
        self.SOC_min = 0.10
        self.SOC_max = 1.00
        self.eta_ch = float(eta_ch)
        self.eta_dis = float(eta_dis)

        self.enabled = enabled
        self.controller = controller

        # Variables droop
        self.V_ref_pu = float(V_ref_pu)
        self.Kq_MVAr_per_pu = float(Kq_MVAr_per_pu)
        self.P_ch_max_MW = float(P_ch_max_MW)
        self.is_active = is_active
        self.sim_state = sim_state
        self.Pref_MW = float(Pref_MW)
        self.mode = mode
        
        # Configuración individual por bus
        self.local_load_MW = self._get_local_load()
        self.individual_response = True  # Flag para control individual

        # Setpoints actuales (MW / Mvar)
        self.Pset_MW: float = 0.0
        self.Qset_Mvar: float = 0.0

    # --------- API principal ----------
    def set_PQ(self, P_MW: float, Q_Mvar: float):
        """
        Fija setpoints respetando SOC, límites P/Q y S_rated.
        - Si SOC <= 5% bloquea descarga (P>0 → se recorta a 0).
        - Si SOC >= 95% bloquea carga (P<0 → se eleva a 0).
        """
        if not self.enabled:
            self.Pset_MW, self.Qset_Mvar = 0.0, 0.0
            return

        # Ventanas por SOC
        if self.soc <= 0.05:
            P_MW = min(P_MW, 0.0)
        if self.soc >= 0.95:
            P_MW = max(P_MW, 0.0)

        # Límites duros P/Q
        P_MW = max(self.Pmin, min(self.Pmax, P_MW))
        Q_Mvar = max(self.Qmin, min(self.Qmax, Q_Mvar))

        # Límite por MVA del convertidor
        S_req = np.hypot(P_MW, Q_Mvar)
        if S_req > self.S_rated + 1e-12:
            scale = self.S_rated / S_req
            P_MW *= scale
            Q_Mvar *= scale

        # (1) Epsilon: evita micro-signos y ruido numérico
        if abs(P_MW) < self.EPS:
            P_MW = 0.0
        if abs(Q_Mvar) < self.EPS:
            Q_Mvar = 0.0

        self.Pset_MW = P_MW
        self.Qset_Mvar = Q_Mvar

    # --------- Para el solver: solo S (pu) ----------
    def S_injection_pu(self) -> complex:
        """
        Devuelve S = P + jQ en p.u. para sumarse al balance de potencia
        del bus correspondiente en el Newton–Raphson.
        """
        if not self.enabled:
            return 0.0 + 0.0j
        return complex(self.Pset_MW / self.S_base, self.Qset_Mvar / self.S_base)

    # --------- Energía (paso cuasiestático) ----------
    def step_energy(self, dt_s: float):
        """
        Actualiza SOC con Pset actual durante dt_s segundos.
        P>0: descarga (SOC baja); P<0: carga (SOC sube).
        """
        if not self.enabled or self.E_rated <= 0:
            return

        dt_h = dt_s / 3600.0  # convertir a horas
        
        if self.Pset_MW > 0.0:  # descarga
            self.soc_update_discharge(dt_h, self.Pset_MW)
        elif self.Pset_MW < 0.0:  # carga
            self.soc_update_charge(dt_h, self.Pset_MW)

    def soc_update_discharge(self, dt_h: float, P_MW: float):
        if P_MW > 0.0:
            # Aplicar eficiencia individual y límites por batería
            actual_power = min(P_MW, self.Pmax * max(0, (self.soc - 0.1) / 0.85))
            dSOC = (actual_power * dt_h) / (self.E_rated * self.eta_dis)
            self.soc = max(self.SOC_min, self.soc - dSOC)
            
            # Protección individual por SOC crítico
            if self.soc <= 0.12:
                self.is_active = False  # Desconectar batería individual

    def soc_update_charge(self, dt_h: float, P_MW: float):
        if P_MW < 0.0:
            # Carga individual con eficiencia específica
            charge_limit = min(abs(P_MW), self.P_ch_max_MW * (0.95 - self.soc) / 0.2)
            dSOC = (charge_limit * dt_h) / self.E_rated * self.eta_ch
            self.soc = min(self.SOC_max, self.soc + dSOC)
            
            # Reactivar batería si se ha cargado suficiente
            if self.soc >= 0.15 and not self.is_active:
                self.is_active = True

    # --------- Hook sencillo Volt/Var (opcional) ----------
    def compute_PQ(self, V_bus: complex) -> tuple[float, float]:
        if (not self.is_active) or (V_bus == 0j):
            return (0.0, 0.0)
        Vm = abs(V_bus)

        # P por estado con lógica individual
        if self.sim_state == "discharge":
            # Aplicar límites por SOC individual
            soc_factor = max(0.1, (self.soc - 0.1) / 0.85)  # Factor de disponibilidad por SOC
            available_power = self.Pmax * soc_factor
            
            if self.mode == "PV":
                # Modo PV: potencia fija para soportar carga local
                P = min(available_power, self.Pref_MW)
            else:  # DROOP
                # Modo DROOP: respuesta proporcional al déficit de voltaje
                voltage_deficit = max(0, self.V_ref_pu - Vm)
                droop_response = voltage_deficit * available_power * 2.0
                P = min(available_power, max(self.Pmin, droop_response))
                
        elif self.sim_state == "charge":
            # Carga individual basada en SOC
            soc_deficit = max(0, 0.95 - self.soc)
            charge_factor = min(1.0, soc_deficit / 0.2)  # Más carga si SOC es menor
            P = -min(self.P_ch_max_MW * charge_factor, self.Pmax)
        else:
            P = 0.0

        # Q por droop individual
        Q = self.Kq_MVAr_per_pu * (self.V_ref_pu - Vm)
        Q = max(self.Qmin, min(self.Qmax, Q))
        return (P, Q)
    
    def _get_local_load(self) -> float:
        """Obtiene la carga local del bus de esta batería"""
        load_map = {
            "Bus 3": 110.0,  # Load 3: 110 MW
            "Bus 4": 100.0,  # Load 4: 100 MW  
            "Bus 5": 100.0   # Load 5: 100 MW
        }
        return load_map.get(self.bus_name, 0.0)
    
    def get_individual_status(self) -> dict:
        """Retorna estado individual detallado de la batería"""
        return {
            "bus": self.bus_name,
            "soc": self.soc,
            "available_energy_MWh": self.soc * self.E_rated,
            "available_power_MW": self.Pmax * max(0, (self.soc - 0.1) / 0.85),
            "local_load_MW": self.local_load_MW,
            "can_support_local": (self.soc * self.E_rated) > (self.local_load_MW * 0.5),
            "mode": self.mode,
            "state": self.sim_state,
            "is_active": self.is_active
        }

    def set_reactive_by_volt_var(self, Vmag_pu: float, Vref: float = 1.0, slope_Mvar_per_pu: float = 50.0):
        Q_cmd = -slope_Mvar_per_pu * (Vmag_pu - Vref)
        self.set_PQ(self.Pset_MW, Q_cmd)

    # --------- Utilidades ----------
    def block(self):
        """Deshabilita la unidad (no inyecta S)."""
        self.enabled = False
        self.Pset_MW = 0.0
        self.Qset_Mvar = 0.0

    def enable(self):
        """Habilita la unidad."""
        self.enabled = True

    # (3) Snapshot de estado (para logging/UI)
    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "bus": getattr(self.bus, "name", str(self.bus)),
            "soc": self.soc,
            "Pset_MW": self.Pset_MW,
            "Qset_Mvar": self.Qset_Mvar,
            "S_rated_MVA": self.S_rated,
            "P_limits_MW": (self.Pmin, self.Pmax),
            "Q_limits_Mvar": (self.Qmin, self.Qmax),
            "enabled": self.enabled,
            "bus_name": self.bus_name,
            "V_ref_pu": self.V_ref_pu,
            "Kq_MVAr_per_pu": self.Kq_MVAr_per_pu,
            "SOC_min": self.SOC_min,
            "SOC_max": self.SOC_max,
            "P_ch_max_MW": self.P_ch_max_MW,
            "is_active": self.is_active,
            "sim_state": self.sim_state,
            "Pref_MW": self.Pref_MW,
            "mode": self.mode,
        }




