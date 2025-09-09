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
import sys
import os

# Add path for battery modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from Battery import Battery
from autonomous_controller import AutonomousController, ControllerConfig

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

def create_seven_bus_system_with_batteries():
    """Create Seven Bus System with batteries connected to buses 3, 4, and 5"""
    
    # Initialize System Settings
    system_settings = SystemSettings(frequency=60, base_power=100)
    circuit = Circuit("Seven Bus Power System with Batteries", system_settings)
    s_base = system_settings.base_power
    frequency = system_settings.frequency

    # Define Buses
    bus1 = Bus("Bus 1", 20)   # Slack Bus
    bus2 = Bus("Bus 2", 230)
    bus3 = Bus("Bus 3", 230)  # With Battery
    bus4 = Bus("Bus 4", 230)  # With Battery
    bus5 = Bus("Bus 5", 230)  # With Battery
    bus6 = Bus("Bus 6", 230)
    bus7 = Bus("Bus 7", 18)   # PV Bus

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
    circuit.add_generator("G1", "Bus 1", per_unit=1.0, real_power=0, x1=0.12, x2=0.14, x0=0.05, 
                         is_grounded=True, grounding_impedance_ohm=0.0, connection_type="wye")
    circuit.add_generator("G2", "Bus 7", per_unit=1.0, real_power=200, x1=0.12, x2=0.14, x0=0.05, 
                         is_grounded=True, grounding_impedance_ohm=1, connection_type="wye")

    # Define Transformers
    transformer1 = Transformer("T1", bus1, bus2, power_rating=125, impedance_percent=8.5, x_over_r_ratio=10, s_base=s_base,
                               grounding_impedance_ohm_bus1=0.0, grounding_impedance_ohm_bus2=1.0, 
                               primary_connection_type="delta", secondary_connection_type="wye",
                               is_grounded_bus1=False, is_grounded_bus2=True)
    transformer2 = Transformer("T2", bus7, bus6, power_rating=200, impedance_percent=10.5, x_over_r_ratio=12, s_base=s_base,
                               grounding_impedance_ohm_bus1=0.0, grounding_impedance_ohm_bus2=0.0, 
                               primary_connection_type="delta", secondary_connection_type="wye",
                               is_grounded_bus1=False, is_grounded_bus2=False)

    # Add Transformers to Circuit
    for transformer in [transformer1, transformer2]:
        circuit.add_transformer(transformer)

    # Define Conductor & Bundle
    conductor = Conductor("Partridge", diam=0.642, GMR=0.0217, resistance=0.385, ampacity=460)
    bundle = Bundle("Double", num_conductors=2, spacing=1.5, conductor=conductor)
    geometry = Geometry("Standard_3Phase", xa=0, ya=0, xb=19.5, yb=0, xc=39, yc=0)

    # Define Transmission Lines
    lines = [
        TransmissionLine("L1", bus2, bus4, bundle, geometry, length=10, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled"),
        TransmissionLine("L2", bus2, bus3, bundle, geometry, length=25, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled"),
        TransmissionLine("L3", bus3, bus5, bundle, geometry, length=20, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled"),
        TransmissionLine("L4", bus4, bus6, bundle, geometry, length=20, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled"),
        TransmissionLine("L5", bus5, bus6, bundle, geometry, length=10, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled"),
        TransmissionLine("L6", bus4, bus5, bundle, geometry, length=35, s_base=s_base, frequency=frequency, 
                        connection_type="untransposed", zero_seq_model="enabled")
    ]

    # Add Transmission Lines to Circuit
    for line in lines:
        circuit.add_transmission_line(line)

    # Create Batteries with Controllers
    batteries = {}
    controllers = {}
    
    # Battery configurations (sized to support respective loads)
    battery_configs = {
        "Bus 3": {"S_rated": 120, "E_rated": 240, "Pmax": 110, "load_MW": 110, "load_Mvar": 50},
        "Bus 4": {"S_rated": 110, "E_rated": 220, "Pmax": 100, "load_MW": 100, "load_Mvar": 70},
        "Bus 5": {"S_rated": 110, "E_rated": 220, "Pmax": 100, "load_MW": 100, "load_Mvar": 65}
    }
    
    for bus_name, config in battery_configs.items():
        bus_obj = {"Bus 3": bus3, "Bus 4": bus4, "Bus 5": bus5}[bus_name]
        
        # Create battery
        battery = Battery(
            name=f"BESS_{bus_name.replace(' ', '_')}",
            bus=bus_obj,
            S_base_MVA=s_base,
            S_rated_MVA=config["S_rated"],
            E_rated_MWh=config["E_rated"],
            Pmin_MW=-config["Pmax"] * 0.8,  # Charging limit
            Pmax_MW=config["Pmax"],         # Discharge limit
            Qmin_Mvar=-config["S_rated"] * 0.6,
            Qmax_Mvar=config["S_rated"] * 0.6,
            soc0=0.80,  # Start at 80% SOC
            eta_ch=0.96,
            eta_dis=0.96,
            enabled=True
        )
        
        # Create controller configuration
        ctrl_config = ControllerConfig(
            V_connect=0.85,     # Connect when V < 0.85 pu
            V_restore=0.95,     # Start charging when V >= 0.95 pu
            soc_min=0.10,       # Minimum SOC 10%
            soc_max=0.95,       # Maximum SOC 95%
            P_limit_MW=config["Pmax"],
            Q_limit_Mvar=config["S_rated"] * 0.6,
            P_charge_default_MW=-config["Pmax"] * 0.5  # Moderate charging
        )
        
        # Create autonomous controller
        controller = AutonomousController(battery, bus_name, ctrl_config)
        battery.controller = controller
        
        batteries[bus_name] = battery
        controllers[bus_name] = controller

    return circuit, batteries, controllers

def run_battery_simulation(faulted_bus=None, fault_type="slg", fault_impedance=0.0, simulation_time_hours=2.0):
    """Run simulation with batteries responding to voltage conditions"""
    
    circuit, batteries, controllers = create_seven_bus_system_with_batteries()
    
    print(f"\n=== SEVEN BUS SYSTEM WITH BATTERIES ===")
    print(f"Batteries installed at: {list(batteries.keys())}")
    
    # Time parameters
    dt_minutes = 5.0  # 5-minute time steps
    dt_seconds = dt_minutes * 60
    total_steps = int((simulation_time_hours * 60) / dt_minutes)
    
    results = {
        "time_min": [],
        "voltages": {},
        "battery_states": {},
        "soc": {}
    }
    
    # Initialize result storage
    for i in range(1, 8):
        results["voltages"][f"Bus {i}"] = []
    for bus_name in batteries.keys():
        results["battery_states"][bus_name] = []
        results["soc"][bus_name] = []
    
    print(f"\nRunning simulation for {simulation_time_hours} hours with {dt_minutes}-minute steps...")
    
    for step in range(total_steps):
        current_time_min = step * dt_minutes
        results["time_min"].append(current_time_min)
        
        # Run power flow analysis
        try:
            if faulted_bus and step > 2:  # Fault occurs after 10 minutes
                solver = Solver(circuit, analysis_mode='fault', faulted_bus=faulted_bus, 
                              fault_type=fault_type, fault_impedance=fault_impedance)
            else:
                solver = Solver(circuit, analysis_mode='pf')
            
            # Capture solver output to get voltages
            import io
            from contextlib import redirect_stdout
            
            f = io.StringIO()
            with redirect_stdout(f):
                solver.run()
            
            output = f.getvalue()
            voltages = parse_voltage_output(output)
            
            # Store voltage results
            for bus_name, voltage_data in voltages.items():
                if bus_name in results["voltages"]:
                    results["voltages"][bus_name].append(voltage_data["magnitude"])
            
            # Update battery controllers based on local bus voltage
            for bus_name, controller in controllers.items():
                if bus_name in voltages:
                    V_pu = voltages[bus_name]["magnitude"]
                    info = controller.step(V_pu, dt_seconds)
                    
                    results["battery_states"][bus_name].append(info["state_after"])
                    results["soc"][bus_name].append(info["soc_after"])
                    
                    if step % 12 == 0:  # Print every hour
                        print(f"t={current_time_min:3.0f}min | {bus_name}: V={V_pu:.3f}pu, "
                              f"State={info['state_after']}, SOC={info['soc_after']:.1%}, "
                              f"P={info['Pset_after']:.1f}MW, Q={info['Qset_after']:.1f}Mvar")
        
        except Exception as e:
            print(f"Error at step {step}: {e}")
            # Fill with previous values or defaults
            for bus_name in results["voltages"]:
                if results["voltages"][bus_name]:
                    results["voltages"][bus_name].append(results["voltages"][bus_name][-1])
                else:
                    results["voltages"][bus_name].append(1.0)
            
            for bus_name in batteries.keys():
                results["battery_states"][bus_name].append("DISCONNECTED")
                results["soc"][bus_name].append(batteries[bus_name].soc)
    
    return results, batteries, controllers

def parse_voltage_output(output):
    """Parse solver output to extract voltage magnitudes and angles"""
    lines = output.split('\n')
    voltages = {}
    
    magnitude_section = False
    angle_section = False
    
    for line in lines:
        if "Final Voltage Magnitudes:" in line:
            magnitude_section = True
            continue
        elif "Final Voltage Angles" in line:
            magnitude_section = False
            angle_section = True
            continue
        elif magnitude_section and ":" in line:
            parts = line.strip().split(":")
            if len(parts) == 2:
                bus_name = parts[0].strip()
                magnitude = float(parts[1].strip())
                if bus_name not in voltages:
                    voltages[bus_name] = {}
                voltages[bus_name]["magnitude"] = magnitude
        elif angle_section and ":" in line:
            parts = line.strip().split(":")
            if len(parts) == 2:
                bus_name = parts[0].strip()
                angle = float(parts[1].strip())
                if bus_name not in voltages:
                    voltages[bus_name] = {}
                voltages[bus_name]["angle"] = angle
    
    return voltages

def print_final_results(results, batteries):
    """Print final simulation results"""
    print(f"\n=== FINAL RESULTS ===")
    
    # Final voltages
    print("\nFinal Bus Voltages:")
    for bus_name in sorted(results["voltages"].keys()):
        if results["voltages"][bus_name]:
            final_V = results["voltages"][bus_name][-1]
            print(f"{bus_name}: {final_V:.3f} pu")
    
    # Final battery states
    print("\nFinal Battery States:")
    for bus_name in batteries.keys():
        battery = batteries[bus_name]
        if results["soc"][bus_name]:
            final_soc = results["soc"][bus_name][-1]
            final_state = results["battery_states"][bus_name][-1]
            support_time = battery.controller.estimate_support_time_seconds(battery.Pmax * 0.9) / 60
            print(f"{bus_name}: SOC={final_soc:.1%}, State={final_state}, "
                  f"Support Time={support_time:.1f}min, P={battery.Pset_MW:.1f}MW")

# Example usage
if __name__ == "__main__":
    # Run simulation with fault at Bus 2
    results, batteries, controllers = run_battery_simulation(
        faulted_bus="Bus 3", 
        fault_type="slg", 
        fault_impedance=0.0,
        simulation_time_hours=1.0
    )
    
    print_final_results(results, batteries)