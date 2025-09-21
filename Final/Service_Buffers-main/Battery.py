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
            dSOC = (P_MW * dt_h) / (self.E_rated * self.eta_dis)
            self.soc = max(self.SOC_min, self.soc - dSOC)

    def soc_update_charge(self, dt_h: float, P_MW: float):
        if P_MW < 0.0:
            dSOC = (abs(P_MW) * dt_h) / self.E_rated * self.eta_ch
            self.soc = min(self.SOC_max, self.soc + dSOC)

    # --------- Hook sencillo Volt/Var (opcional) ----------
    def compute_PQ(self, V_bus: complex) -> tuple[float, float]:
        if (not self.is_active) or (V_bus == 0j):
            return (0.0, 0.0)
        Vm = abs(V_bus)

        # P por estado
        if self.sim_state == "discharge":
            P = max(self.Pmin, min(self.Pref_MW, self.Pmax))
        elif self.sim_state == "charge":
            P = -min(self.P_ch_max_MW, self.Pmax)
        else:
            P = 0.0

        # Q por droop
        Q = self.Kq_MVAr_per_pu * (self.V_ref_pu - Vm)
        Q = max(self.Qmin, min(self.Qmax, Q))
        return (P, Q)

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




