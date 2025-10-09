"""
Global T_r configuration module for power system simulation
Generates realistic recovery times based on fault case probabilities
"""

import random

# Global T_r value (in minutes)
_global_t_r = None
_last_case_info = (None, None)

def generate_t_r(force_case=None):
    """Generate T_r based on case probabilities and subcategory distributions"""
    try:
        # Use forced case if provided, otherwise use random selection
        if force_case:
            case = force_case
        else:
            # First, determine which case occurs based on overall probabilities
            case = random.choices(
                ["case_1", "case_2", "case_3"],
                weights=[15.0, 60.0, 25.0]  # Case 1: 15%, Case 2: 60%, Case 3: 25%
            )[0]
        
        t_r_value = None
        subcategory = None
        
        if case == "case_1":
            # Case 1: Generation Loss (Barras de generación)
            subcategory = random.choices(
                ["clearance", "reconfig", "hot_restart", "cold_restart", "transformer"],
                weights=[30.0, 40.0, 25.0, 5.0, 1.5]  # Transformer fault is optional/rare
            )[0]
            global _last_case_info
            _last_case_info = ("Case 1: Generation Loss", subcategory)
            
            if subcategory == "clearance":
                # Solo despeje/aislamiento: 0.08-0.5 s
                t_r_value = random.uniform(0.08/60, 0.5/60)
            elif subcategory == "reconfig":
                # Reconfiguración/redispatch: 2-5 min
                t_r_value = random.uniform(2.0, 5.0)
            elif subcategory == "hot_restart":
                # Hot restart: 30-60 min
                t_r_value = random.uniform(30.0, 60.0)
            elif subcategory == "cold_restart":
                # Warm/Cold restart: 4-24 h
                t_r_value = random.uniform(240, 1440)
            else:  # transformer
                # Falla en trafo elevador: 1-7 días
                t_r_value = random.uniform(1440, 10080)
                
        elif case == "case_2":
            # Case 2: Load Buses Loss (Barras de carga)
            subcategory = random.choices(
                ["transient", "sustained", "repair"],
                weights=[70.0, 25.0, 5.0]
            )[0]
            _last_case_info = ("Case 2: Load Buses Loss", subcategory)
            
            if subcategory == "transient":
                # Transitorias: 0.1-2 s
                t_r_value = random.uniform(0.1/60, 2/60)
            elif subcategory == "sustained":
                # Sostenidas con maniobra: 5-60 min (suggested range)
                t_r_value = random.uniform(5.0, 60.0)
            else:  # repair
                # Reparación de equipo: 2-36 h (suggested range)
                t_r_value = random.uniform(120, 2160)
                
        else:  # case_3
            # Case 3: Communication Loss (Comunicaciones)
            subcategory = random.choices(
                ["transient", "failover", "physical"],
                weights=[60.0, 35.0, 5.0]
            )[0]
            _last_case_info = ("Case 3: Communication Loss", subcategory)
            
            if subcategory == "transient":
                # Transitorias: 2-10 s
                t_r_value = random.uniform(2/60, 10/60)
            elif subcategory == "failover":
                # Failover/reboot: 90s-5 min
                t_r_value = random.uniform(1.5, 5.0)
            else:  # physical
                # Medio físico: 6-24 h
                t_r_value = random.uniform(360, 1440)
        
        # Ensure minimum value and cap at 0.5 min
        if t_r_value is None or t_r_value <= 0:
            t_r_value = 5.0
        elif t_r_value < 0.5:
            t_r_value = random.uniform(10, 20)
            
        print(f"DEBUG t_r_config: Generated T_r = {t_r_value:.3f} minutes for {case}")
        return t_r_value
        
    except Exception as e:
        print(f"ERROR in generate_t_r: {e}")
        return 5.0  # Fallback value

def set_global_t_r(value):
    """Set the global T_r value"""
    global _global_t_r
    _global_t_r = value

def get_global_t_r():
    """Get the current global T_r value"""
    global _global_t_r
    if _global_t_r is None:
        _global_t_r = generate_t_r()
    return _global_t_r

def reset_global_t_r(force_case=None):
    """Generate and set a new global T_r value"""
    global _global_t_r
    _global_t_r = generate_t_r(force_case)
    return _global_t_r

def get_last_case_info():
    """Get the last generated case and subcategory information"""
    global _last_case_info
    return _last_case_info