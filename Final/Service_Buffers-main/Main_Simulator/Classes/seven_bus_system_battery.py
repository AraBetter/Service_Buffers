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
from battery_controller import BatteryController
from battery_droop import BatteryDroop
try:
    from t_r_config import get_global_t_r
except ImportError:
    import random
    get_global_t_r = lambda: random.uniform(6, 600)

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

    # Create Batteries with Droop Control
    batteries = {}
    
    # Battery configurations with droop parameters
    battery_configs = {
        "Bus 3": {"S_rated": 120, "E_rated": 240, "Pmax": 110},
        "Bus 4": {"S_rated": 110, "E_rated": 220, "Pmax": 100},
        "Bus 5": {"S_rated": 110, "E_rated": 220, "Pmax": 100}
    }
    
    for bus_name, config in battery_configs.items():
        bus_obj = {"Bus 3": bus3, "Bus 4": bus4, "Bus 5": bus5}[bus_name]
        
        # Create battery with droop control
        battery = Battery(
            name=f"BESS_{bus_name.replace(' ', '_')}",
            bus=bus_obj,
            S_base_MVA=s_base,
            S_rated_MVA=config["S_rated"],
            E_rated_MWh=config["E_rated"],
            Pmin_MW=0.0,
            Pmax_MW=config["Pmax"],
            Qmin_Mvar=-config["S_rated"] * 0.5,
            Qmax_Mvar=config["S_rated"] * 0.5,
            soc0=0.95,
            bus_name=bus_name,
            V_ref_pu=1.00,
            Kq_MVAr_per_pu=60.0,
            P_ch_max_MW=config["Pmax"] * 0.5,
            is_active=True,
            sim_state="prefault",
            Pref_MW=0.0,
            mode="DROOP"
        )
        
        batteries[bus_name] = battery
    
    # Add batteries to circuit
    circuit.bess_list = list(batteries.values())
    
    # Create battery controller
    battery_controller = BatteryController(circuit)

    return circuit, batteries, battery_controller

def run_battery_simulation(case_id=1, faulted_bus=None, fault_type="slg", fault_impedance=0.0):
    """Run simulation with batteries responding to voltage conditions"""
    
    # Use global T_r value
    T_r_minutes = get_global_t_r()
    T_r_hours = T_r_minutes / 60.0
    simulation_time_hours = T_r_hours
    
    circuit, batteries, battery_controller = create_seven_bus_system_with_batteries()
    
    print(f"\n=== SEVEN BUS SYSTEM WITH BATTERIES ===")
    print(f"Batteries installed at: {list(batteries.keys())}")
    print(f"Random T_r generated: {T_r_hours:.2f} hours")
    print(f"Case ID: {case_id}")
    
    # Time parameters
    dt_minutes = 10.0  # 10-minute time steps
    dt_hours = dt_minutes / 60.0
    total_steps = int((simulation_time_hours * 60) / dt_minutes)
    
    results = {
        "time_min": [],
        "voltages": {},
        "angles": {},
        "battery_states": {},
        "soc": {},
        "battery_power": {}
    }
    
    # Initialize result storage
    for i in range(1, 8):
        results["voltages"][f"Bus {i}"] = []
        results["angles"][f"Bus {i}"] = []
    for bus_name in batteries.keys():
        results["battery_states"][bus_name] = []
        results["soc"][bus_name] = []
        results["battery_power"][bus_name] = []
    
    print(f"\nRunning simulation for {simulation_time_hours:.2f} hours with {dt_minutes}-minute steps...")
    
    # Simulation states
    fault_step = int(total_steps * 0.1)  # Fault at 10% of simulation
    recovery_step = int(total_steps * 0.9)  # Recovery at 90% of simulation
    
    for step in range(total_steps):
        current_time_min = step * dt_minutes
        results["time_min"].append(current_time_min)
        
        # Determine simulation state
        if step < fault_step:
            sim_state = "prefault"
        elif step < fault_step + 2:
            sim_state = "fault"
        elif step < recovery_step:
            sim_state = "discharge"
        else:
            sim_state = "charge"
        
        # Run power flow analysis
        try:
            if faulted_bus and fault_step <= step < recovery_step:
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
            
            # Store voltage and angle results (updated after battery integration)
            for bus_name, voltage_data in voltages.items():
                if bus_name in results["voltages"]:
                    results["voltages"][bus_name].append(voltage_data["magnitude"])
                if bus_name in results["angles"]:
                    results["angles"][bus_name].append(voltage_data.get("angle", 0.0))
            
            # Create voltage dict for battery controller (updated values)
            Vm_dict = {bus: data["magnitude"] for bus, data in voltages.items()}
            V_complex_dict = {bus: data["magnitude"] * (1+0j) for bus, data in voltages.items()}
            
            # Program batteries based on case and state
            battery_controller.program_bess(
                case_id=case_id,
                sim_state=sim_state,
                Vm=Vm_dict,
                system_deficit_MW=50.0 if case_id == 1 else 0.0,
                delta_demand_MW=30.0 if case_id == 3 else 0.0
            )
            
            # Apply battery injections to circuit
            for bus_name, battery in batteries.items():
                P, Q = battery.compute_PQ(V_complex_dict.get(bus_name, 1+0j))
                if abs(P) > 0.01 or abs(Q) > 0.01:  # Only if significant power
                    # Add battery as generator to modify power flow
                    try:
                        # Remove existing battery generator if exists
                        if hasattr(circuit, 'generators'):
                            circuit.generators = {k: v for k, v in circuit.generators.items() 
                                                if not k.startswith(f"BESS_{bus_name.replace(' ', '_')}")}
                        
                        # Add battery as generator with computed P only
                        circuit.add_generator(
                            f"BESS_{bus_name.replace(' ', '_')}", 
                            bus_name, 
                            per_unit=1.0, 
                            real_power=P,  # MW injection
                            x1=0.01, x2=0.01, x0=0.01,
                            is_grounded=False, 
                            grounding_impedance_ohm=0.0, 
                            connection_type="wye"
                        )
                        
                        # Add reactive power as separate load if needed
                        if abs(Q) > 0.01:
                            try:
                                # Remove existing battery load if exists
                                if hasattr(circuit, 'loads'):
                                    circuit.loads = {k: v for k, v in circuit.loads.items() 
                                                   if not k.startswith(f"BESS_Q_{bus_name.replace(' ', '_')}")}
                                
                                # Add reactive power as load (negative Q = capacitive)
                                circuit.add_load(f"BESS_Q_{bus_name.replace(' ', '_')}", bus_name, 0.0, -Q)
                            except Exception:
                                pass
                    except Exception as e:
                        pass  # Silently continue if battery cannot be added
            
            # Re-run solver with battery injections
            f2 = io.StringIO()
            with redirect_stdout(f2):
                if faulted_bus and fault_step <= step < recovery_step:
                    solver2 = Solver(circuit, analysis_mode='fault', faulted_bus=faulted_bus, 
                                   fault_type=fault_type, fault_impedance=fault_impedance)
                else:
                    solver2 = Solver(circuit, analysis_mode='pf')
                solver2.run()
            
            output2 = f2.getvalue()
            voltages_with_batteries = parse_voltage_output(output2)
            
            # Use voltages with battery effects
            if voltages_with_batteries:
                voltages = voltages_with_batteries
                Vm_dict = {bus: data["magnitude"] for bus, data in voltages.items()}
                V_complex_dict = {bus: data["magnitude"] * (1+0j) for bus, data in voltages.items()}
            
            # Update SOC
            battery_controller.update_soc(dt_hours, V_complex_dict)
            
            # Store battery results (after voltage update)
            for bus_name, battery in batteries.items():
                P, Q = battery.compute_PQ(V_complex_dict.get(bus_name, 1+0j))
                results["battery_states"][bus_name].append(battery.sim_state)
                results["soc"][bus_name].append(battery.soc)
                results["battery_power"][bus_name].append({"P": P, "Q": Q})
                
                if step % 3 == 0:  # Print every 30 minutes
                    V_pu = Vm_dict.get(bus_name, 1.0)
                    print(f"t={current_time_min:3.0f}min | {bus_name}: V={V_pu:.3f}pu, "
                          f"State={battery.sim_state}, SOC={battery.soc:.1%}, "
                          f"P={P:.1f}MW, Q={Q:.1f}Mvar")
        
        except Exception as e:
            print(f"Error at step {step}: {e}")
            # Fill with previous values or defaults
            for bus_name in results["voltages"]:
                if results["voltages"][bus_name]:
                    results["voltages"][bus_name].append(results["voltages"][bus_name][-1])
                    results["angles"][bus_name].append(results["angles"][bus_name][-1] if results["angles"][bus_name] else 0.0)
                else:
                    results["voltages"][bus_name].append(1.0)
                    results["angles"][bus_name].append(0.0)
            
            for bus_name in batteries.keys():
                results["battery_states"][bus_name].append("DISCONNECTED")
                results["soc"][bus_name].append(batteries[bus_name].soc)
                results["battery_power"][bus_name].append({"P": 0.0, "Q": 0.0})
    
    return results, batteries, battery_controller, T_r_hours

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

def print_final_results(results, batteries, T_r_hours):
    """Print final simulation results"""
    print(f"\n=== FINAL RESULTS (T_r = {T_r_hours:.2f} hours) ===")
    
    # Final voltages with angles
    print("\nFinal Bus Voltages (Magnitude ∠ Angle):")
    for bus_name in sorted(results["voltages"].keys()):
        if results["voltages"][bus_name] and results["angles"][bus_name]:
            final_V = results["voltages"][bus_name][-1]
            final_angle = results["angles"][bus_name][-1]
            print(f"{bus_name}: {final_V:.3f} ∠ {final_angle:.1f}° pu")
    
    # Final battery states
    print("\nFinal Battery States:")
    for bus_name in batteries.keys():
        battery = batteries[bus_name]
        if results["soc"][bus_name] and results["battery_power"][bus_name]:
            final_soc = results["soc"][bus_name][-1]
            final_state = results["battery_states"][bus_name][-1]
            final_power = results["battery_power"][bus_name][-1]
            discharge_time = (battery.soc * battery.E_rated) / max(battery.Pmax, 1) if battery.Pmax > 0 else 0
            print(f"{bus_name}: SOC={final_soc:.1%}, State={final_state}, "
                  f"Discharge Time={discharge_time:.1f}h, P={final_power['P']:.1f}MW, Q={final_power['Q']:.1f}Mvar")
    
    # Battery discharge percentages during T_r
    print("\nBattery Discharge Summary:")
    for bus_name in batteries.keys():
        if results["soc"][bus_name]:
            initial_soc = results["soc"][bus_name][0] if results["soc"][bus_name] else 0.95
            final_soc = results["soc"][bus_name][-1]
            discharge_percent = ((initial_soc - final_soc) / initial_soc) * 100 if initial_soc > 0 else 0
            print(f"{bus_name}: Discharged {discharge_percent:.1f}% over {T_r_hours:.2f}h")

# Example usage
if __name__ == "__main__":
    # Run simulation with different cases
    for case in [1, 2, 3]:
        print(f"\n{'='*60}")
        print(f"RUNNING CASE {case}")
        print(f"{'='*60}")
        
        results, batteries, controller, T_r = run_battery_simulation(
            case_id=case,
            faulted_bus="Bus 5", 
            fault_type="slg", 
            fault_impedance=0.0
        )
        
        print_final_results(results, batteries, T_r)