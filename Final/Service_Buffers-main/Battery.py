class Battery:
    def __init__(self, name: str, bus, power_rating: float, voltage_setpoint: float, soc_init: float = 1.0,
                 max_charge_rate: float = None, max_discharge_rate: float = None, x1=None, x2=None, x0=None,
                 system_settings=None, grounding_impedance_ohm=None, is_grounded=True, connection_type="wye"):
        self.name = name
        self.bus = bus  # Connected Bus
        self.power_rating = power_rating  # MW
        self.voltage_setpoint = voltage_setpoint  # in p.u.
        self.soc = soc_init  # State of Charge (0 to 1)
        self.max_charge_rate = max_charge_rate or power_rating
        self.max_discharge_rate = max_discharge_rate or power_rating
        self.connection_type = connection_type.lower()
        self.is_grounded = is_grounded


        # Sequence impedance handling, similar to Generator
        self.x1 = x1
        self.x2 = x2
        self.x0 = x0
        self.Y1 = self.Y2 = self.Y0 = None
        self.Yn = None

        if system_settings and x1 and x2 and x0:
            self.convert_to_system_base(system_settings, grounding_impedance_ohm)

    def convert_to_system_base(self, settings, grounding_impedance_ohm):
        s_base = settings.base_power
        v_base = self.bus.base_kv
        base_ratio = s_base / self.power_rating

        self.x1 *= base_ratio
        self.x2 *= base_ratio
        self.x0 *= base_ratio

        if self.is_grounded and grounding_impedance_ohm:
            zb = (v_base ** 2) / self.power_rating
            zn_pu = (grounding_impedance_ohm / zb) * base_ratio
            self.zn_pu = zn_pu
            self.Yn = 1 / zn_pu
        elif self.is_grounded:
            self.Yn = float('inf')

    def calc_admittances(self):
        self.Y1 = 1 / (1j * self.x1) if self.x1 else None
        self.Y2 = 1 / (1j * self.x2) if self.x2 else None
        self.Y0 = 1 / (1j * self.x0) if self.x0 else None
        return self.Y1, self.Y2, self.Y0

    def __repr__(self):
        return (f"Battery(name={self.name}, bus={self.bus.name}, SOC={self.soc:.2f}, "
                f"rating={self.power_rating}MW, Vref={self.voltage_setpoint} p.u.)")
