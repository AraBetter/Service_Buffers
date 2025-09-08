import numpy as np
import pandas as pd
from transformer import Transformer
from transmission_line import TransmissionLine
from generator import Generator
from load import Load
from system_setting import SystemSettings


class Circuit:
    """Represents a power system circuit, storing all components and managing configuration."""

    def __init__(self, name, system_settings: SystemSettings):
        """Initializes the circuit with a name and empty dictionaries for components."""
        self.name = name
        self.settings = system_settings
        self.buses = {}  # Stores Bus objects
        self.bus_type = {}  # Initialize the bus type dictionary
        self.transformers = {}  # Stores Transformer objects
        self.transmission_lines = {}  # Stores TransmissionLine objects
        self.generators = {}  # Stores Generator objects
        self.loads = {}  # Stores Load objects
        self.first_generator_added = False
        self.batteries = {}  # Stores Battery objects

        self.ybus: pd.DataFrame = None  # Explicitly hinting it's a DataFrame

    def add_bus(self, bus):
        """Adds a bus object to the circuit. Raises an error if the bus already exists."""
        if bus.name in self.buses:
            raise ValueError(f"Bus '{bus.name}' already exists in the circuit.")
        self.buses[bus.name] = bus
        self.bus_type[bus.name] = bus.bus_type

    def add_transformer(self, transformer):
        """Adds a transformer object to the circuit. Raises an error if the transformer already exists.
           Also ensures the transformer computes its sequence Y-prim matrices."""
        if transformer.name in self.transformers:
            raise ValueError(f"Transformer '{transformer.name}' already exists in the circuit.")

        self.transformers[transformer.name] = transformer

    def add_transmission_line(self, transmission_line):
        """Adds a transmission line object to the circuit. Raises an error if the line already exists.
           Also ensures the transmission line computes its sequence Y-prim matrices."""
        if transmission_line.name in self.transmission_lines:
            raise ValueError(f"Transmission Line '{transmission_line.name}' already exists in the circuit.")

        self.transmission_lines[transmission_line.name] = transmission_line

    def add_load(self, name:str, bus:str, real_power: float, reactive_power:float):
        self.loads[name] = Load(name, self.buses[bus], real_power, reactive_power)
        self.buses[bus].real_power -= real_power
        self.buses[bus].reactive_power -= reactive_power

        if not hasattr(self.buses[bus], 'loads'):
            self.buses[bus].loads = []
        self.buses[bus].loads.append(self.loads[name])


    def add_generator(self, name: str, bus: str, per_unit: float, real_power: float,
                      x1=None, x2=None, x0=None, grounding_impedance_ohm=None, is_grounded=True, connection_type="wye"):
        if name in self.generators:
            raise ValueError(f"Generator '{name}' already exists in the circuit.")

        generator = Generator(name, self.buses[bus], real_power, per_unit,
                              x1=x1, x2=x2, x0=x0, system_settings=self.settings,
                              grounding_impedance_ohm=grounding_impedance_ohm,
                              is_grounded=is_grounded, connection_type=connection_type
                              )
        self.generators[name] = generator

        # Only update bus real power once
        self.buses[bus].real_power += real_power

        # Set bus type based on whether it's the first generator
        if not self.first_generator_added:
            self.buses[bus].bus_type = "Slack Bus"
            self.first_generator_added = True
        elif self.buses[bus].bus_type != "Slack Bus":
            self.buses[bus].bus_type = "PV Bus"

        print(f"[DEBUG] Added generator '{name}' to {bus} → P = {real_power}")


    def add_battery(self, name: str, bus: str, S_base_MVA: float = None, **battery_kwargs):
        from Battery import Battery
        if not hasattr(self, "batteries"):
            self.batteries = {}
        if name in self.batteries:
            raise ValueError(f"Battery '{name}' already exists in the circuit.")
        if bus not in self.buses:
            raise ValueError(f"Bus '{bus}' not found in the circuit.")
        if S_base_MVA is None:
            S_base_MVA = self.settings.base_power
            
        bat = battery_kwargs.pop("battery", None)
            
        if bat is None:
             bat = Battery(name=name, bus=self.buses[bus], S_base_MVA=S_base_MVA, **battery_kwargs)
        
        
        self.batteries[name] = bat
        if not hasattr(self.buses[bus], "batteries"):
            self.buses[bus].batteries = []
        self.buses[bus].batteries.append(bat)
        return bat
    
    def get_battery(self, name: str):
        return self.batteries.get(name)

    
    def update_bus_data(self):
        self.bus_type = {}
        self.num_PV_buses = 0
        self.num_PQ_buses = 0
        self.real_power = {}
        self.reactive_power = {}

        for b in self.bus_order():
            # Copy from Bus object into Circuit dictionaries
            self.real_power[b] = self.buses[b].real_power
            self.reactive_power[b] = self.buses[b].reactive_power
            self.bus_type[b] = self.buses[b].bus_type

            # Count buses by type
            if self.buses[b].bus_type == "PQ Bus":
                self.num_PQ_buses += 1
            elif self.buses[b].bus_type == "PV Bus":
                self.num_PV_buses += 1

            print(f"[TRACE] During update: {b} classified as {self.buses[b].bus_type}")

    def calc_ybus(self):
        """Computes the system-wide Ybus admittance matrix in per-unit."""
        num_buses = len(self.buses)
        bus_names = list(self.buses.keys())
        # Initialize the Ybus matrix as an N x N zero matrix
        self.ybus = pd.DataFrame(np.zeros((num_buses, num_buses), dtype=complex), index=bus_names, columns=bus_names)

        # Accumulate contributions from all transformers
        for transformer in self.transformers.values():
            yprim_pu = transformer.yprim_pu  # Ensure using per-unit values
            if not isinstance(yprim_pu, pd.DataFrame):
                raise TypeError(f"{transformer.name} yprim_pu is not a DataFrame!")
            bus1, bus2 = transformer.bus1.name, transformer.bus2.name
            self.ybus.loc[bus1, bus1] += yprim_pu.loc[bus1, bus1]
            self.ybus.loc[bus2, bus2] += yprim_pu.loc[bus2, bus2]
            self.ybus.loc[bus1, bus2] += yprim_pu.loc[bus1, bus2]  # Off-diagonal term
            self.ybus.loc[bus2, bus1] += yprim_pu.loc[bus2, bus1]  # Mutual admittance (negative)

        # Accumulate contributions from all transmission lines
        for line in self.transmission_lines.values():
            yprim_pu = line.yprim_pu  # Ensure using per-unit values
            if not isinstance(yprim_pu, pd.DataFrame):
                raise TypeError(f"{line.name} yprim_pu is not a DataFrame!")
            bus1, bus2 = line.bus1.name, line.bus2.name
            self.ybus.loc[bus1, bus1] += yprim_pu.loc[bus1, bus1]
            self.ybus.loc[bus2, bus2] += yprim_pu.loc[bus2, bus2]
            self.ybus.loc[bus1, bus2] += yprim_pu.loc[bus1, bus2]  # Off-diagonal term
            self.ybus.loc[bus2, bus1] += yprim_pu.loc[bus2, bus1]  # Mutual admittance (negative)

        # Ensure numerical stability by checking that all buses have self-admittance entries
        for bus in bus_names:
            if self.ybus.loc[bus, bus] == 0:
                raise ValueError(f"Numerical instability detected: Bus {bus} has no self-admittance.")

        return self.ybus

    def calc_ybus_positive(self):
        """Constructs the Ybus matrix for symmetrical fault analysis (positive-sequence only),
        including generator subtransient admittances.
        """
        bus_names = list(self.buses.keys())
        Ybus_aug = pd.DataFrame(0j, index=bus_names, columns=bus_names)


        for transformer in self.transformers.values():
            yprim = transformer.calc_yprim_sequence("positive")
            if yprim is not None:
                for i in yprim.index:
                    for j in yprim.columns:
                        Ybus_aug.loc[i, j] += yprim.loc[i, j]


        for line in self.transmission_lines.values():
            yprim = line.calc_yprim_sequence("positive")
            if yprim is not None:
                for i in yprim.index:
                    for j in yprim.columns:
                        Ybus_aug.loc[i, j] += yprim.loc[i, j]


        for gen in self.generators.values():
            gen.calc_admittances()  # Ensure admittances are calculated

            if gen.Y1 is not None:
                bus_name = gen.bus.name
                if bus_name not in Ybus_aug.index:
                    raise ValueError(f"Bus {bus_name} not in Ybus index!")
                Ybus_aug.loc[bus_name, bus_name] += gen.Y1


        return Ybus_aug

    def calc_ybus_negative(self):
        """Constructs the negative-sequence Ybus matrix."""
        bus_names = list(self.buses.keys())
        Ybus_neg = pd.DataFrame(0j, index=bus_names, columns=bus_names)

        # Add transformer negative-sequence Yprim
        for transformer in self.transformers.values():
            yprim = transformer.calc_yprim_sequence("negative")
            for i in yprim.index:
                for j in yprim.columns:
                    Ybus_neg.loc[i, j] += yprim.loc[i, j]

        # Add transmission line negative-sequence Yprim
        for line in self.transmission_lines.values():
            yprim = line.calc_yprim_sequence("negative")
            for i in yprim.index:
                for j in yprim.columns:
                    Ybus_neg.loc[i, j] += yprim.loc[i, j]

        # Add generator negative-sequence admittance (shunt)
        for gen in self.generators.values():
            gen.calc_admittances()
            if gen.Y2 is not None:
                Ybus_neg.loc[gen.bus.name, gen.bus.name] += gen.Y2
                # print(f"[DEBUG] Added Y2 of Generator '{gen.name}' to bus {gen.bus.name}: {gen.Y2}")

        return Ybus_neg

    def calc_ybus_zero(self):
        """
        Constructs the zero-sequence Ybus matrix.
        Only includes contributions from components that allow zero-sequence current flow.
        """
        bus_names = list(self.buses.keys())
        Ybus_zero = pd.DataFrame(0j, index=bus_names, columns=bus_names)

        # Add transformer zero-sequence Yprim
        for transformer in self.transformers.values():
            yprim = transformer.calc_yprim_sequence("zero")
            if yprim is not None:
                for i in yprim.index:
                    for j in yprim.columns:
                        Ybus_zero.loc[i, j] += yprim.loc[i, j]
            # print(f"[DEBUG] Transformer {transformer.name} Yprim zero:\n{yprim}")

        # Add transmission line zero-sequence Yprim
        for line in self.transmission_lines.values():
            yprim = line.calc_yprim_sequence("zero")
            if yprim is not None:
                for i in yprim.index:
                    for j in yprim.columns:
                        Ybus_zero.loc[i, j] += yprim.loc[i, j]
            # print(f"[DEBUG] Line {line.name} Yprim zero:\n{yprim}")

        # Add generator zero-sequence admittance
        for gen in self.generators.values():
            gen.calc_admittances()
            if gen.Y0 is not None and gen.Yn is not None:
                bus_name = gen.bus.name
                Ybus_zero.loc[bus_name, bus_name] += gen.Y0
            # print(f"[DEBUG] Added Y0 of Generator '{gen.name}' to bus {bus_name}: {gen.Y0}")

        return Ybus_zero

    def get_base_power(self):
        """Returns the base power of the system."""
        return self.settings.base_power

    def get_frequency(self):
        """Returns the system frequency."""
        return self.settings.frequency

    def bus_order(self):
        """Returns the ordered list of bus names."""
        return list(self.buses.keys())

    def bus_types(self):
        """Returns a dictionary mapping bus names to their types."""
        return {bus.name: bus.bus_type for bus in self.buses.values()}

    def real_power_vector(self):
        real_power = {}

        for bus in self.buses.values():
            P_load = sum(load.real_power for load in getattr(bus, "loads", []))
            P_gen = sum(gen.real_power for gen in getattr(bus, "generators", []))

            total_P = P_gen - P_load
            real_power[bus.name] = total_P

        return real_power


    def reactive_power_vector(self):
        """Computes the reactive power vector (Q) from all buses."""
        reactive_power = {}

        for bus in self.buses.values():
            Q_load = sum(load.reactive_power for load in getattr(bus, "loads", []))
            reactive_power[bus.name] = -Q_load  # 🔥 NEGATIVE SIGN for PQ buses
            print(f"[DEBUG] {bus.name}: Q_load = {Q_load}, total = {-Q_load}")

        return reactive_power

    def show_network(self):
        """Displays the network configuration."""
        print(f"\nCircuit Name: {self.name}")
        print("\n--- Buses ---")
        for bus in self.buses.values():
            print(f"{bus.name} - {bus.base_kv} kV")
        print("\n--- Transformers ---")
        for transformer in self.transformers.values():
            print(f"{transformer.name}: {transformer.bus1.name} ↔ {transformer.bus2.name}")
        print("\n--- Transmission Lines ---")
        for line in self.transmission_lines.values():
            print(f"{line.name}: {line.bus1.name} ↔ {line.bus2.name}")
        print("\n--- Generators ---")
        for generator in self.generators.values():
            print(f"{generator.name}: Connected to {generator.bus.name}, MW Setpoint: {generator.mw_setpoint} MW")
        print("\n--- Loads ---")
        for load in self.loads.values():
            print(
                f"{load.name}: Connected to {load.bus.name}, Real Power: {load.real_power} MW, Reactive Power: {load.reactive_power} Mvar")


    def show_ybus(self):
        """Displays the Ybus matrix if it has been calculated."""
        if self.ybus is None:
            print("Ybus has not been calculated. Run calc_ybus() first.")



