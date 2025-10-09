#!/usr/bin/env python3
"""
Test rápido para verificar operación de baterías con T_r cortos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Main_Simulator', 'Classes'))
sys.path.append(os.path.dirname(__file__))

from seven_bus_system_battery import run_battery_simulation
from t_r_config import set_global_t_r

def test_short_tr_values():
    """Prueba con diferentes valores cortos de T_r"""
    
    tr_values = [5, 10, 15, 20, 25, 30, 35, 40]  # minutos
    
    for tr_min in tr_values:
        print(f"\n{'='*60}")
        print(f"PRUEBA CON T_r = {tr_min} MINUTOS")
        print(f"{'='*60}")
        
        # Establecer T_r específico
        set_global_t_r(tr_min)
        
        try:
            results, batteries, controller, T_r = run_battery_simulation(
                case_id=2,
                faulted_bus="Bus 3",
                fault_type="slg",
                fault_impedance=0.0
            )
            
            # Verificar si las baterías entraron en operación
            battery_operated = False
            for bus_name, battery in batteries.items():
                if results["battery_power"][bus_name]:
                    max_power = max([abs(p["P"]) for p in results["battery_power"][bus_name]])
                    if max_power > 0.1:  # MW
                        battery_operated = True
                        print(f"✓ {bus_name}: Máxima potencia = {max_power:.1f} MW")
                    else:
                        print(f"✗ {bus_name}: No operó (máx = {max_power:.3f} MW)")
            
            if battery_operated:
                print(f"✓ RESULTADO: Baterías operaron correctamente con T_r = {tr_min} min")
            else:
                print(f"✗ RESULTADO: Baterías NO operaron con T_r = {tr_min} min")
                
        except Exception as e:
            print(f"✗ ERROR con T_r = {tr_min} min: {e}")

if __name__ == "__main__":
    print("PRUEBA DE OPERACIÓN CON T_r CORTOS")
    print("Verificando que las baterías entren en operación inmediatamente")
    test_short_tr_values()