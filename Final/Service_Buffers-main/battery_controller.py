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
        self.V_MIN_SERVICE = getattr(circuit, "V_MIN_SERVICE", 0.95)

    # --------- utilidades internas ---------
    def _loads_at(self, bus_name: str) -> float:
        """MW de carga en el bus (aprox)."""
        P = 0.0
        for ld in getattr(self.circuit, "loads", {}).values():
            try:
                if ld.bus.name == bus_name and getattr(ld, "is_active", True):
                    P += float(getattr(ld, "P_MW", 0.0))
            except Exception:
                continue
        return P

    def _active_bess(self) -> Iterable:
        return [b for b in getattr(self.circuit, "bess_list", []) if getattr(b, "is_active", True)]

    # --------- API principal ---------
    def program_bess(self,
                     case_id: CaseId,
                     sim_state: SimState,
                     Vm: Dict[str, float] | None,
                     system_deficit_MW: float = 0.0,
                     delta_demand_MW: float = 0.0):
        """
        - Vm: dict {bus_name: |V|_pu} del paso actual (puede ser None en estado 5).
        - system_deficit_MW: para Case 1 (pérdida de gen) cuánto MW falta tras el trip.
        - delta_demand_MW:  para Case 3 (comms loss) el incremento de demanda no atendido por el gen.
        """
        for b in self._active_bess():
            b.sim_state = sim_state

            # Default: standby (modo que ya tenga)
            if sim_state not in ("discharge","charge"):
                b.Pref_MW = 0.0
                continue

            # ----- Estado 4: descarga -----
            if sim_state == "discharge":
                Vok = True if Vm is None else (Vm.get(b.bus_name, 1.0) >= self.V_MIN_SERVICE)
                # Si la tensión ya está bien, puedes mantener P=0 (tu política). Aquí seguimos política "actúa si Vm<0.95".
                if Vok:
                    b.Pref_MW = 0.0
                    continue

                if case_id == 1:
                    # Loss of generation → DROOP
                    b.mode = "DROOP"
                    # reparte el déficit entre bancos activos
                    n = max(1, len(self._active_bess()))
                    share = max(0.0, system_deficit_MW) / n
                    b.Pref_MW = min(b.Pmax, max(b.Pmin, share))

                elif case_id == 2:
                    # Loss of load bus → PV como generador local
                    b.mode = "PV"
                    P_local = self._loads_at(b.bus_name)
                    b.Pref_MW = min(b.Pmax, max(b.Pmin, P_local))

                elif case_id == 3:
                    # Comms loss → DROOP cubre ΔP
                    b.mode = "DROOP"
                    n = max(1, len(self._active_bess()))
                    share = max(0.0, delta_demand_MW) / n
                    b.Pref_MW = min(b.Pmax, max(b.Pmin, share))

            # ----- Estado 5: carga -----
            if sim_state == "charge":
                # En todos los casos: DROOP con P negativa
                b.mode = "DROOP"
                b.Pref_MW = -min(getattr(b, "P_ch_max_MW", b.Pmax), b.Pmax)

    # --------- actualización de SOC por paso ---------
    def update_soc(self, dt_h: float, V_complex: Dict[str, complex] | None = None):
        for b in self._active_bess():
            if b.sim_state == "discharge":
                if b.mode == "PV":
                    b.soc_update_discharge(dt_h, b.Pref_MW)
                else:  # DROOP
                    # calcular P según V_actual para ser más fiel
                    P, _ = b.compute_PQ(V_complex[b.bus_name] if V_complex else 1+0j)
                    b.soc_update_discharge(dt_h, P)
            elif b.sim_state == "charge":
                if b.mode == "PV":
                    b.soc_update_charge(dt_h, b.Pref_MW)        # poco probable en esta estrategia
                else:
                    P, _ = b.compute_PQ(V_complex[b.bus_name] if V_complex else 1+0j)
                    b.soc_update_charge(dt_h, P)