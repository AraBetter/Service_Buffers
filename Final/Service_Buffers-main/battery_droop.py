from dataclasses import dataclass

@dataclass
class BatteryDroop:
    name: str
    bus_name: str
    # Ratings
    S_rated_MVA: float = 20.0
    E_rated_MWh: float = 40.0
    P_min_MW: float = 0.0
    P_max_MW: float = 20.0
    Q_min_MVAr: float = -10.0
    Q_max_MVAr: float = 10.0
    # Droop Q–V
    V_ref_pu: float = 1.00
    Kq_MVAr_per_pu: float = 60.0     # Q = Kq*(Vref - |V|)
    # Estado / energía
    SOC: float = 0.95
    SOC_min: float = 0.10
    SOC_max: float = 1.00
    eta_dis: float = 0.96
    eta_ch: float = 0.93
    P_ch_max_MW: float = 10.0
    # Flags
    is_active: bool = True
    sim_state: str = "prefault"       # prefault, fault, aftertrip, discharge, charge, normalized
    Pref_MW: float = 0.0              # MW, P>0 genera; P<0 carga
    mode: str = "DROOP"               # 'DROOP' | 'PV' (solo informativo aquí)

    def compute_PQ(self, V_bus: complex) -> tuple[float, float]:
        if (not self.is_active) or (V_bus == 0j):
            return (0.0, 0.0)
        Vm = abs(V_bus)

        # P por estado
        if self.sim_state == "discharge":
            P = max(self.P_min_MW, min(self.Pref_MW, self.P_max_MW))   # >0 genera
        elif self.sim_state == "charge":
            P = -min(self.P_ch_max_MW, self.P_max_MW)                  # <0 carga
        else:
            P = 0.0

        # Q por droop
        Q = self.Kq_MVAr_per_pu * (self.V_ref_pu - Vm)                 # Q>0 inyecta (capacitivo)
        if Q > self.Q_max_MVAr: Q = self.Q_max_MVAr
        if Q < self.Q_min_MVAr: Q = self.Q_min_MVAr
        return (P, Q)

    def norton_injection(self, V_bus: complex) -> complex:
        # I = conj(S)/conj(V)   con tu convención: S=P+jQ (P>0 genera, Q>0 inyecta)
        if V_bus == 0j:
            return 0j
        P, Q = self.compute_PQ(V_bus)
        return complex(P, -Q) / V_bus.conjugate()

    # --- Energía / SOC ---
    def soc_update_discharge(self, dt_h: float, P_MW: float):
        if P_MW > 0.0:
            dSOC = (P_MW * dt_h) / (self.E_rated_MWh * self.eta_dis)
            self.SOC = max(self.SOC_min, self.SOC - dSOC)

    def soc_update_charge(self, dt_h: float, P_MW: float):
        if P_MW < 0.0:
            dSOC = (abs(P_MW) * dt_h) / self.E_rated_MWh * self.eta_ch
            self.SOC = min(self.SOC_max, self.SOC + dSOC)