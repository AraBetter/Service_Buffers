class ProtectionRelay:
    def __init__(self, name: str, faulted_bus: str, trip_voltage_threshold=0.3, trip_delay=0.1):
        self.name = name
        self.faulted_bus = faulted_bus
        self.trip_voltage_threshold = trip_voltage_threshold
        self.trip_delay = trip_delay
        self.tripped = False
        self.trip_timer = 0.0

    def evaluate(self, voltage_mag: float, dt: float = 0.01):
        if self.tripped:
            return

        if voltage_mag < self.trip_voltage_threshold:
            self.trip_timer += dt
            if self.trip_timer >= self.trip_delay:
                self.tripped = True
                print(f"[PROTECTION] {self.name} tripped. Isolating Bus '{self.faulted_bus}'.")
        else:
            self.trip_timer = 0.0

    def isolate_faulted_bus(self, circuit):
        if not self.tripped:
            return

        # 1. Disconnect transformers connected to the faulted bus
        circuit.transformers = {
            name: t for name, t in circuit.transformers.items()
            if t.bus1.name != self.faulted_bus and t.bus2.name != self.faulted_bus
        }

        # 2. Disconnect transmission lines connected to the faulted bus
        circuit.transmission_lines = {
            name: l for name, l in circuit.transmission_lines.items()
            if l.bus1.name != self.faulted_bus and l.bus2.name != self.faulted_bus
        }

        # 3. Disconnect generators at the faulted bus
        circuit.generators = {
            name: g for name, g in circuit.generators.items()
            if g.bus.name != self.faulted_bus
        }

        # 4. Optional: clear loads on the faulted bus
        circuit.loads = {
            name: l for name, l in circuit.loads.items()
            if l.bus.name != self.faulted_bus
        }

        # 5. Disable the bus logically (without deleting code)
        if self.faulted_bus in circuit.buses:
            circuit.buses[self.faulted_bus].is_active = False
            print(f"[PROTECTION] Bus '{self.faulted_bus}' flagged as inactive.")

        # 6. Rebuild Ybus
        circuit.update_bus_data()
        circuit.calc_ybus()

    def is_tripped(self):
        return self.tripped

    def reset(self):
        self.tripped = False
        self.trip_timer = 0.0
        print(f"[PROTECTION] {self.name} reset.")