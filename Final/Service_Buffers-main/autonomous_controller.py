class AutonomousController:
    def __init__(self, name: str, battery, enable_voltage_control=True, enable_power_control=False,
                 soc_min=0.2, soc_max=0.95, soc_step=0.1):
        self.name = name
        self.battery = battery
        self.enable_voltage_control = enable_voltage_control
        self.enable_power_control = enable_power_control
        self.connected = False

        self.soc_min = soc_min
        self.soc_max = soc_max
        self.soc_step = soc_step  # Increment per control step (abstracted)

    def connect(self):
        if not self.connected:
            if self.battery.soc > self.soc_min:
                self.connected = True
                print(f"[INFO] {self.name}: Battery '{self.battery.name}' connected at Bus '{self.battery.bus.name}'")
            else:
                print(f"[WARN] {self.name}: Battery SOC too low to connect (SOC = {self.battery.soc:.2f})")

    def disconnect(self):
        if self.connected:
            self.connected = False
            print(f"[INFO] {self.name}: Battery '{self.battery.name}' disconnected from Bus '{self.battery.bus.name}'")

    def is_connected(self):
        return self.connected

    def control_step(self, grid_voltage=None, target_voltage=1.0):
        if not self.connected:
            return

        if self.enable_voltage_control and grid_voltage is not None:
            error = target_voltage - grid_voltage
            power_output = error * 10  # Simple proportional control
            self.update_soc(power_output)
            print(f"[DEBUG] {self.name}: V_error={error:.4f}, Power={power_output:.2f} MW, SOC={self.battery.soc:.2f}")

        if self.enable_power_control:
            # Placeholder for active power dispatch logic
            pass

    def update_soc(self, power):
        # Updates SOC based on power injection/absorption. Power > 0 = discharge.
        delta_soc = self.soc_step * (power / self.battery.power_rating)
        self.battery.soc -= delta_soc
        self.battery.soc = max(0.0, min(1.0, self.battery.soc))

        if self.battery.soc <= self.soc_min:
            print(f"[WARN] {self.name}: Battery SOC dropped below minimum. Disconnecting.")
            self.disconnect()

    def __repr__(self):
        return (f"AutonomousController(name='{self.name}', battery='{self.battery.name}', "
                f"connected={self.connected}, V-control={self.enable_voltage_control}, "
                f"P-control={self.enable_power_control}, SOC={self.battery.soc:.2f})")