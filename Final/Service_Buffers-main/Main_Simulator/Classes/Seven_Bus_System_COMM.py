"""
Seven Bus System with Communication Fault Analysis
Handles communication failures between generators and the system
Includes random load increase of 5-20% on buses 3, 4, or 5
"""

import sys
import os
import random
import copy
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from Seven_Bus_System import circuit
    from MainSolver import Solver
    from t_r_config import get_global_t_r
except ImportError as e:
    print(f"Warning: Could not import Seven Bus System modules: {e}")
    circuit = None
    Solver = None
    get_global_t_r = lambda: 300

def run_comm_fault_analysis(faulted_bus=None):
    """
    Run communication fault analysis with random load increase
    Increases load by 5-20% randomly on one of buses 3, 4, or 5
    Sets comms_ok = False for communication fault indication
    """
    if circuit is None or Solver is None:
        print("Seven Bus System modules not available")
        return None, False
    
    try:
        # Create a deep copy of the circuit for communication fault analysis
        comm_circuit = copy.deepcopy(circuit)
        
        # Set communication fault flag
        comms_ok = False
        
        # Randomly select a load bus (3, 4, or 5) and increase percentage (5-20%)
        load_buses = [3, 4, 5]
        selected_bus = random.choice(load_buses)
        load_increase_percent = random.uniform(5, 20)  # 5% to 20% increase
        
        # Find and modify the selected load
        for load_name, load_data in comm_circuit.loads.items():
            if load_data['bus'] == f'Bus {selected_bus}':
                original_p = load_data['real_power']
                original_q = load_data['reactive_power']
                
                # Increase load by the random percentage
                new_p = original_p * (1 + load_increase_percent / 100)
                new_q = original_q * (1 + load_increase_percent / 100)
                
                # Update load values
                load_data['real_power'] = new_p
                load_data['reactive_power'] = new_q
                
                print(f"Communication fault: Load at Bus {selected_bus} increased by {load_increase_percent:.1f}%")
                print(f"  P: {original_p:.1f} → {new_p:.1f} MW")
                print(f"  Q: {original_q:.1f} → {new_q:.1f} MVAr")
                break
        
        # Run power flow analysis with modified loads
        solver = Solver(comm_circuit, analysis_mode='pf')
        solver.run()
        
        return comm_circuit, comms_ok
        
    except Exception as e:
        print(f"Error in communication fault analysis: {e}")
        return None, False

if __name__ == "__main__":
    # Test communication fault analysis
    result_circuit, comms_status = run_comm_fault_analysis()
    if result_circuit:
        print("Communication fault analysis completed successfully")
        print(f"Communication status: {comms_status}")
    else:
        print("Communication fault analysis failed")