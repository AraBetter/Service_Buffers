from Circuit import Circuit
from FaultStudySolver import FaultStudySolver
from bus import Bus
from transformer import Transformer
from transmission_line import TransmissionLine
from bundle import Bundle
from geometry import Geometry
from conductor import Conductor
from system_setting import SystemSettings
from PowerFlowSolver import PowerFlowSolver  # Import power flow solver
from generator import Generator  # Import Generator
from load import Load
from Newton_Raphson import NewtonRaphson
import pandas as pd
import numpy as np
from MainSolver import Solver
from pprint import pprint

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

# Initialize System Settings
system_settings = SystemSettings(frequency=60, base_power=100)

# Create the Seven Bus Power System
circuit = Circuit("Seven Bus Power System", system_settings)

# Retrieve system settings from the circuit
s_base = system_settings.base_power
frequency = system_settings.frequency

# Define Buses
bus1 = Bus("Bus 1", 20)  # Slack Bus
bus2 = Bus("Bus 2", 230)
bus3 = Bus("Bus 3", 230)
bus4 = Bus("Bus 4", 230)
bus5 = Bus("Bus 5", 230)
bus6 = Bus("Bus 6", 230)
bus7 = Bus("Bus 7", 18)  # PV Bus

# Add Buses to Circuit
for bus in [bus1, bus2, bus3, bus4, bus5, bus6, bus7]:
    circuit.add_bus(bus)

# Define Loads
load3 = Load("Load 3", bus3, real_power=110, reactive_power=50)
load4 = Load("Load 4", bus4, real_power=100, reactive_power=70)
load5 = Load("Load 5", bus5, real_power=100, reactive_power=65)

# Add Loads to Circuit
for load in [load3, load4, load5]:
    circuit.add_load(load.name, load.bus.name, load.real_power, load.reactive_power)

# Define Generators
circuit.add_generator("G1", "Bus 1", per_unit=1.0, real_power=0, x1=0.12, x2=0.14, x0=0.05, is_grounded=True, grounding_impedance_ohm=0.0, connection_type="wye")     # Slack
circuit.add_generator("G2", "Bus 7", per_unit=1.0, real_power=200, x1=0.12, x2=0.14, x0=0.05, is_grounded=True, grounding_impedance_ohm=1, connection_type="wye")   # PV


# Define Transformers
transformer1 = Transformer("T1", bus1, bus2, power_rating=125, impedance_percent=8.5, x_over_r_ratio=10, s_base=s_base,
                           grounding_impedance_ohm_bus1=0.0, grounding_impedance_ohm_bus2=1.0, primary_connection_type="delta", secondary_connection_type="wye",
                           is_grounded_bus1=False, is_grounded_bus2=True)
transformer2 = Transformer("T2", bus7, bus6, power_rating=200, impedance_percent=10.5, x_over_r_ratio=12, s_base=s_base,
                           grounding_impedance_ohm_bus1=0.0, grounding_impedance_ohm_bus2=0.0, primary_connection_type="delta", secondary_connection_type="wye",
                           is_grounded_bus1=False, is_grounded_bus2=False)

# Add Transformers to Circuit
for transformer in [transformer1, transformer2]:
    circuit.add_transformer(transformer)

# Define Conductor & Bundle
conductor = Conductor("Partridge", diam=0.642, GMR=0.0217, resistance=0.385, ampacity=460)
bundle = Bundle("Double", num_conductors=2, spacing=1.5, conductor=conductor)

# Define Geometry
geometry = Geometry("Standard_3Phase", xa=0, ya=0, xb=19.5, yb=0, xc=39, yc=0)

# Define Transmission Lines
lines = [
    TransmissionLine("L1", bus2, bus4, bundle, geometry, length=10, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled"),
    TransmissionLine("L2", bus2, bus3, bundle, geometry, length=25, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled"),
    TransmissionLine("L3", bus3, bus5, bundle, geometry, length=20, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled"),
    TransmissionLine("L4", bus4, bus6, bundle, geometry, length=20, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled"),
    TransmissionLine("L5", bus5, bus6, bundle, geometry, length=10, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled"),
    TransmissionLine("L6", bus4, bus5, bundle, geometry, length=35, s_base=s_base, frequency=frequency, connection_type="untransposed", zero_seq_model="enabled")
]

# Add Transmission Lines to Circuit
for line in lines:
    circuit.add_transmission_line(line)


# Calculate Ybus and Display It
Ybus = circuit.calc_ybus()
print("\n--- Ybus (for Power Flow Analysis) ---")
print(Ybus)

# ➕ Show Ybus Sequence Matrices
ybus_positive = circuit.calc_ybus_positive()
print("\n--- Ybus Positive-Sequence (for Fault Analysis) ---")
print(ybus_positive)

ybus_negative = circuit.calc_ybus_negative()
print("\n--- Ybus Negative-Sequence (for Fault Analysis) ---")
print(ybus_negative)

ybus_zero = circuit.calc_ybus_zero()
print("\n--- Ybus Zero-Sequence (for Fault Analysis) ---")
print(ybus_zero)


# Comment/uncomment depending on which analysis you want to run.
from MainSolver import Solver

# # Example for Power Flow Analysis
#solver = Solver(circuit, analysis_mode='pf')
#solver.run()

# Run Line-to-Ground (SLG) Fault at Bus 5  
fault_solver = Solver(circuit, analysis_mode='fault', faulted_bus="Bus 2", fault_type="slg", fault_impedance=0.0)
fault_solver.run()



# # Example for 3 Phase (3ph) Fault at Bus 5
# fault_solver = Solver(circuit, analysis_mode='fault', faulted_bus="Bus 5", fault_type="3ph")
# fault_solver.run()

# Or for Line-to-Line (LL) Fault at Bus 3
# fault_solver = Solver(circuit, analysis_mode='fault', faulted_bus="Bus 3", fault_type="ll")
# fault_solver.run()
#
# # Or for Double-Line-to-Ground (DLG) Fault at Bus 6
# fault_solver = Solver(circuit, analysis_mode='fault', faulted_bus="Bus 5", fault_type="dlg")
# fault_solver.run()

