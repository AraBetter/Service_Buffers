# autonomous_controller.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import math

# --- utilidad: interpolación lineal por tramos ---
def piecewise_linear(x: float, points: List[Tuple[float, float]]) -> float:
    """
    x: valor de entrada (por ej. Vpu)
    points: lista ordenada [(x0,y0), (x1,y1), ...] con x ascendentes
    devuelve y interpolado; satura fuera de rango.
    """
    if not points:
        return 0.0
    if x <= points[0][0]: return points[0][1]
    if x >= points[-1][0]: return points[-1][1]
    # buscar tramo
    for (x0,y0), (x1,y1) in zip(points[:-1], points[1:]):
        if x0 <= x <= x1:
            t = 0.0 if x1==x0 else (x - x0) / (x1 - x0)
            return y0 + t*(y1 - y0)
    return points[-1][1]

@dataclass
class ControllerConfig:
    # Umbrales de estado
    V_connect: float = 0.85      # conectar si V < V_connect
    V_restore: float = 0.95      # empezar a cargar si V >= V_restore
    soc_min: float = 0.05        # no descargar por debajo de 5%
    soc_max: float = 0.95        # objetivo de carga/desconexión

      # IEEE 1547-2018 perfiles típicos (fracciones de Pmax y Qmax)
    volt_watt_points: Optional[list[tuple[float, float]]] = None
    volt_var_points:  Optional[list[tuple[float, float]]] = None

    # Límites absolutos de consignas (si quieres topes más conservadores que P/Q máx. de la batería)
    P_limit_MW: Optional[float] = None
    Q_limit_Mvar: Optional[float] = None

    # Potencia de carga por defecto cuando V está normal (MW negativa)
    P_charge_default_MW: Optional[float] = None

class AutonomousController:
    """
    Control automático con Volt/Watt (P) y Volt/Var (Q).
    Estados: DISCONNECTED, SUPPORTING, CHARGING.

    - Si V < V_connect y SOC > soc_min → SUPPORTING.
    - En SUPPORTING: P y Q siguen curvas volt-watt/volt-var (limitadas por SOC y ratings).
    - Si V >= V_restore → CHARGING (P negativa, Q según volt-var si se desea).
    - Si SOC >= soc_max en CHARGING → DISCONNECTED.
    """

    def __init__(self, battery, bus_name: str, cfg: Optional[ControllerConfig] = None):
        self.battery = battery
        self.bus_name = bus_name
        self.cfg = cfg or ControllerConfig()
        self.state = "DISCONNECTED"

        # Curvas por defecto si no se pasan
        
        if self.cfg.volt_watt_points is None:
            # Volt/Watt (VW) – recorte por sobre-tensión
            # (Vpu, fracción de Pmax)    ← típico 1547: 1.06→100%, 1.10→0%
            self.cfg.volt_watt_points = [
                (0.00, 1.00),   # por debajo de nominal: sin recorte
                (1.00, 1.00),
                (1.06, 1.00),
                (1.10, 0.00),
                (1.20, 0.00),
            ]

        if self.cfg.volt_var_points is None:
            # Volt/Var (VV) – banda muerta 0.98–1.02 pu; extremos 0.92/1.08 pu
            # (Vpu, fracción de Qmax)   + = capacitivo (sube V),  - = inductivo (baja V)
            self.cfg.volt_var_points = [
                (0.92, +1.00),
                (0.98,  0.00),
                (1.02,  0.00),
                (1.08, -1.00),
            ]

       

        # Ajustes por defecto de límites externos
        if self.cfg.P_limit_MW is None:
            self.cfg.P_limit_MW = self.battery.Pmax  # descarga máxima permitida
        if self.cfg.Q_limit_Mvar is None:
            self.cfg.Q_limit_Mvar = max(abs(self.battery.Qmin), abs(self.battery.Qmax))
        if self.cfg.P_charge_default_MW is None:
            self.cfg.P_charge_default_MW = -0.5 * self.battery.S_rated  # carga moderada

    # ---- paso principal ----
    def step(self, Vmag_pu: float, dt_s: float) -> Dict:
        info = {
            "state_before": self.state, "V": Vmag_pu,
            "soc": self.battery.soc, "Pset": self.battery.Pset_MW, "Qset": self.battery.Qset_Mvar
        }

        # Transiciones de estado
        if self.state == "DISCONNECTED":
            if Vmag_pu < self.cfg.V_connect and self.battery.soc > self.cfg.soc_min:
                self.state = "SUPPORTING"

        if self.state == "SUPPORTING":
            # consignas por curvas
            P_frac = piecewise_linear(Vmag_pu, self.cfg.volt_watt_points)   # [-, +]
            Q_frac = piecewise_linear(Vmag_pu, self.cfg.volt_var_points)    # [-, +]
            P_cmd = P_frac * self.battery.Pmax
            Q_cmd = Q_frac * self.battery.Qmax

            # aplica límites externos
            P_cmd = max(-abs(self.cfg.P_limit_MW), min(+abs(self.cfg.P_limit_MW), P_cmd))
            Q_cmd = max(-abs(self.cfg.Q_limit_Mvar), min(+abs(self.cfg.Q_limit_Mvar), Q_cmd))

            # setea respetando S_rated y SOC
            self.battery.set_PQ(P_cmd, Q_cmd)

            # pasar a carga si el voltaje se normaliza o SOC mínimo alcanzado
            if Vmag_pu >= self.cfg.V_restore or self.battery.soc <= self.cfg.soc_min:
                self.state = "CHARGING"

        if self.state == "CHARGING":
            if self.battery.soc < self.cfg.soc_max:
                P_cmd = min(0.0, self.cfg.P_charge_default_MW)  # MW negativa (cargando)
                # Q en carga: puedes dejarlo según volt-var para ayudar a mantener V
                Q_frac = piecewise_linear(Vmag_pu, self.cfg.volt_var_points)
                Q_cmd = Q_frac * self.battery.Qmax
                Q_cmd = max(-abs(self.cfg.Q_limit_Mvar), min(+abs(self.cfg.Q_limit_Mvar), Q_cmd))
                self.battery.set_PQ(P_cmd, Q_cmd)
            else:
                # cargada -> desconectar
                self.battery.set_PQ(0.0, 0.0)
                self.state = "DISCONNECTED"

        if self.state == "DISCONNECTED":
            self.battery.set_PQ(0.0, 0.0)

        # actualizar energía con el Pset aplicado
        self.battery.step_energy(dt_s)

        # tiempo de soporte estimado si volviera a apoyar a P = 0.9 Pmax
        tsec = self.estimate_support_time_seconds(P_support_MW=0.9*self.battery.Pmax)
        info.update({
            "state_after": self.state, "soc_after": self.battery.soc,
            "Pset_after": self.battery.Pset_MW, "Qset_after": self.battery.Qset_Mvar,
            "support_time_min_est": tsec/60.0
        })
        return info

    # ---- utilidades ----
    def estimate_support_time_seconds(self, P_support_MW: float) -> float:
        """ t = ((SOC - soc_min) * E_rated) / (P_support/eta_dis) """
        P_support_MW = max(0.0, P_support_MW)
        if P_support_MW <= 1e-9 or self.battery.E_rated <= 0.0:
            return 0.0
        soc_avail = max(0.0, self.battery.soc - self.cfg.soc_min)
        E_MWh = soc_avail * self.battery.E_rated
        P_net = P_support_MW / max(self.battery.eta_dis, 1e-6)
        return max(0.0, (E_MWh / P_net) * 3600.0)
