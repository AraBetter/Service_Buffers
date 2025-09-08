from Circuit import Circuit
from FaultStudySolver import FaultStudySolver
from bus import Bus
from transformer import Transformer
from transmission_line import TransmissionLine
from bundle import Bundle
from geometry import Geometry
from conductor import Conductor
from system_setting import SystemSettings
from PowerFlowSolver import PowerFlowSolver
from generator import Generator
from load import Load
from Newton_Raphson import NewtonRaphson
import pandas as pd
import numpy as np
from MainSolver import Solver
from pprint import pprint

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def create_circuit_without_faulted_bus(faulted_bus_name):
    """Create a circuit without the specified faulted bus and its associated components"""
    
    # Initialize System Settings
    system_settings = SystemSettings(frequency=60, base_power=100)
    circuit = Circuit("Seven Bus Power System - Post Fault", system_settings)
    s_base = system_settings.base_power
    frequency = system_settings.frequency
    
    # Extract bus number from name (e.g., "Bus 5" -> 5)
    faulted_bus_num = int(faulted_bus_name.split()[-1])
    
    # Define all buses initially
    all_buses = {
        1: Bus("Bus 1", 20),   # Slack Bus
        2: Bus("Bus 2", 230),
        3: Bus("Bus 3", 230),
        4: Bus("Bus 4", 230),
        5: Bus("Bus 5", 230),
        6: Bus("Bus 6", 230),
        7: Bus("Bus 7", 18)    # PV Bus
    }
    
    # Remove faulted bus and dependent buses
    buses_to_remove = [faulted_bus_num]
    
    # Special cases: remove dependent buses
    if faulted_bus_num == 2:  # If Bus 2 fails, Bus 1 also disconnects
        buses_to_remove.append(1)
    elif faulted_bus_num == 6:  # If Bus 6 fails, Bus 7 also disconnects
        buses_to_remove.append(7)
    
    # Remove all buses that should be disconnected
    for bus_num in buses_to_remove:
        if bus_num in all_buses:
            del all_buses[bus_num]
    
    # Add remaining buses to circuit
    for bus in all_buses.values():
        circuit.add_bus(bus)
    
    # Define loads (only add if bus exists)
    loads_config = {
        3: {"name": "Load 3", "real_power": 110, "reactive_power": 50},
        4: {"name": "Load 4", "real_power": 100, "reactive_power": 70},
        5: {"name": "Load 5", "real_power": 100, "reactive_power": 65}
    }
    
    for bus_num, load_config in loads_config.items():
        if bus_num in all_buses:
            circuit.add_load(load_config["name"], f"Bus {bus_num}", 
                           load_config["real_power"], load_config["reactive_power"])
    
    # Define generators (only add if bus exists)
    if 1 in all_buses:
        circuit.add_generator("G1", "Bus 1", per_unit=1.0, real_power=0, x1=0.12, x2=0.14, x0=0.05, 
                            is_grounded=True, grounding_impedance_ohm=0.0, connection_type="wye")
    
    if 7 in all_buses:
        circuit.add_generator("G2", "Bus 7", per_unit=1.0, real_power=200, x1=0.12, x2=0.14, x0=0.05, 
                            is_grounded=True, grounding_impedance_ohm=1, connection_type="wye")
    
    # Define transformers (only add if both buses exist)
    transformers_to_add = []
    
    # Transformer 1: Bus 1 - Bus 2
    if 1 in all_buses and 2 in all_buses:
        transformer1 = Transformer("T1", all_buses[1], all_buses[2], power_rating=125, impedance_percent=8.5, 
                                  x_over_r_ratio=10, s_base=s_base, grounding_impedance_ohm_bus1=0.0, 
                                  grounding_impedance_ohm_bus2=1.0, primary_connection_type="delta", 
                                  secondary_connection_type="wye", is_grounded_bus1=False, is_grounded_bus2=True)
        transformers_to_add.append(transformer1)
    
    # Transformer 2: Bus 7 - Bus 6
    if 7 in all_buses and 6 in all_buses:
        transformer2 = Transformer("T2", all_buses[7], all_buses[6], power_rating=200, impedance_percent=10.5, 
                                  x_over_r_ratio=12, s_base=s_base, grounding_impedance_ohm_bus1=0.0, 
                                  grounding_impedance_ohm_bus2=0.0, primary_connection_type="delta", 
                                  secondary_connection_type="wye", is_grounded_bus1=False, is_grounded_bus2=False)
        transformers_to_add.append(transformer2)
    
    # Add transformers to circuit
    for transformer in transformers_to_add:
        circuit.add_transformer(transformer)
    
    # Define conductor & bundle
    conductor = Conductor("Partridge", diam=0.642, GMR=0.0217, resistance=0.385, ampacity=460)
    bundle = Bundle("Double", num_conductors=2, spacing=1.5, conductor=conductor)
    geometry = Geometry("Standard_3Phase", xa=0, ya=0, xb=19.5, yb=0, xc=39, yc=0)
    
    # Define transmission lines (only add if both buses exist)
    lines_config = [
        {"name": "L1", "from_bus": 2, "to_bus": 4, "length": 10},
        {"name": "L2", "from_bus": 2, "to_bus": 3, "length": 25},
        {"name": "L3", "from_bus": 3, "to_bus": 5, "length": 20},
        {"name": "L4", "from_bus": 4, "to_bus": 6, "length": 20},
        {"name": "L5", "from_bus": 5, "to_bus": 6, "length": 10},
        {"name": "L6", "from_bus": 4, "to_bus": 5, "length": 35}
    ]
    
    for line_config in lines_config:
        from_bus_num = line_config["from_bus"]
        to_bus_num = line_config["to_bus"]
        
        if from_bus_num in all_buses and to_bus_num in all_buses:
            line = TransmissionLine(line_config["name"], all_buses[from_bus_num], all_buses[to_bus_num], 
                                  bundle, geometry, length=line_config["length"], s_base=s_base, 
                                  frequency=frequency, connection_type="untransposed", zero_seq_model="enabled")
            circuit.add_transmission_line(line)
    
    return circuit

def run_post_fault_analysis(faulted_bus_name):
    """Run power flow analysis on the system without the faulted bus"""
    try:
        # Create circuit without faulted bus
        circuit = create_circuit_without_faulted_bus(faulted_bus_name)
        
        # Run power flow analysis
        solver = Solver(circuit, analysis_mode='pf')
        solver.run()
        
        return circuit
        
    except Exception as e:
        print(f"Error in post-fault analysis: {e}")
        return None


# Example usage (commented out)
circuit_post_fault = run_post_fault_analysis("Bus 2")