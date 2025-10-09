# NEW: battery_controller.py
from __future__ import annotations
from typing import Literal, Dict, Iterable

CaseId   = Literal[1, 2, 3]
SimState = Literal["prefault","fault","aftertrip","discharge","charge","normalized"]

class BatteryController:
    """
    Enfocado en ESTADOS 4 y 5:
      - Case 1 (loss of gen): Estado 4 = DROOP (P=deficit);  Estado 5 = DROOP (P<0)
      - Case 2 (loss of load bus): Estado 4 = PV (P=carga local); Estado 5 = DROOP (P<0)
      - Case 3 (comms loss): Estado 4 = DROOP (P=ΔP);          Estado 5 = DROOP (P<0)
    """
    def __init__(self, circuit):
        self.circuit = circuit
        self.V_MIN_SERVICE = getattr(circuit, "V_MIN_SERVICE", 0.85)  # Umbral más bajo para activación
        # Configuración individual por batería
        self.battery_configs = {
            "Bus 3": {"priority": 1, "response_factor": 1.2},
            "Bus 4": {"priority": 2, "response_factor": 1.0}, 
            "Bus 5": {"priority": 2, "response_factor": 1.0}
        }

    # --------- utilidades internas ---------
    def _loads_at(self, bus_name: str) -> float:
        """MW de carga en el bus específico."""
        P = 0.0
        # Cargas específicas por bus según el sistema de 7 buses
        load_map = {
            "Bus 3": 110.0,  # Load 3: 110 MW
            "Bus 4": 100.0,  # Load 4: 100 MW  
            "Bus 5": 100.0   # Load 5: 100 MW
        }
        return load_map.get(bus_name, 0.0)

    def _active_bess(self) -> Iterable:
        return [b for b in getattr(self.circuit, "bess_list", []) if getattr(b, "is_active", True)]

    # --------- API principal ---------
    def program_bess(self,
                     case_id: CaseId,
                     sim_state: SimState,
                     Vm: Dict[str, float] | None,
                     system_deficit_MW: float = 0.0,
                     delta_demand_MW: float = 0.0,
                     faulted_bus: str = None):
        """
        Control individual: solo la batería del bus afectado opera
        """
        for b in self._active_bess():
            b.sim_state = sim_state
            is_faulted_bus = (faulted_bus == b.bus_name)

            # Default: todas las baterías en standby
            b.Pref_MW = 0.0
            b.mode = "DROOP"
            
            if sim_state not in ("discharge", "charge"):
                continue

            # ----- Estado descarga: SOLO la batería del bus fallado -----
            if sim_state == "discharge":
                if is_faulted_bus:
                    # Solo la batería del bus fallado actúa
                    b.mode = "PV"
                    P_local = self._loads_at(b.bus_name)
                    b.Pref_MW = min(b.Pmax, max(b.Pmin, P_local))
                else:
                    # Todas las demás baterías permanecen inactivas
                    b.Pref_MW = 0.0

            # ----- Estado carga: SOLO la batería que descargó -----
            elif sim_state == "charge":
                if is_faulted_bus:
                    # Solo la batería que descargó se carga
                    b.mode = "DROOP"
                    charge_power = min(getattr(b, "P_ch_max_MW", b.Pmax * 0.5), b.Pmax * 0.5)
                    b.Pref_MW = -charge_power
                else:
                    # Todas las demás baterías permanecen inactivas
                    b.Pref_MW = 0.0

    # --------- actualización de SOC por paso ---------
    def update_soc(self, dt_h: float, V_complex: Dict[str, complex] | None = None, faulted_bus: str = None):
        """Actualiza SOC solo de la batería afectada"""
        for b in self._active_bess():
            is_faulted_bus = (faulted_bus == b.bus_name)
            
            # Solo actualizar SOC de la batería del bus afectado
            if not is_faulted_bus:
                continue
                
            bus_voltage = V_complex.get(b.bus_name, 1+0j) if V_complex else 1+0j
            
            if b.sim_state == "discharge":
                # Solo la batería del bus fallado descarga
                if b.mode == "PV":
                    actual_power = min(b.Pref_MW, b.Pmax * (b.soc - 0.1) / 0.85)
                    b.soc_update_discharge(dt_h, actual_power)
                else:
                    P, _ = b.compute_PQ(bus_voltage)
                    if b.soc <= 0.15:
                        P = min(P, b.Pmax * 0.1)
                    b.soc_update_discharge(dt_h, P)
                    
            elif b.sim_state == "charge":
                # Solo la batería que descargó se carga
                P, _ = b.compute_PQ(bus_voltage)
                if b.soc >= 0.90:
                    P = max(P, -b.P_ch_max_MW * 0.3)
                b.soc_update_charge(dt_h, P)