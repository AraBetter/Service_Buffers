class Bus:
    count = 0
    slack_assigned = False  # Ensures only one slack bus is assigned

    def __init__(self, name: str, base_kv: float):

        self.name = name
        self.base_kv = base_kv
        self.index = Bus.count
        self.real_power = 0.0
        self.reactive_power = 0.0
        self.bus_type = 'PQ Bus'
        self.loads = []
        Bus.count += 1







