from Classes.bus import Bus


class Load:
    def __init__(self, name: str, bus, real_power: float, reactive_power: float):
        self.name = name
        self.bus = bus  # This should be a Bus object
        self.real_power = real_power  # MW
        self.reactive_power = reactive_power  # Mvar

    def __repr__(self):
        return (f"Load(name='{self.name}', bus='{self.bus.name}', "
                f"real_power={self.real_power} MW, reactive_power={self.reactive_power} Mvar)")