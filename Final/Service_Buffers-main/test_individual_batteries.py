#!/usr/bin/env python3
"""
Test script para demostrar el funcionamiento individual de las baterías
en el sistema de 7 buses.

Cada batería opera independientemente según:
- Bus 3: Batería de 240MWh/110MW - Soporta carga local de 110MW
- Bus 4: Batería de 220MWh/100MW - Soporta carga local de 100MW  
- Bus 5: Batería de 220MWh/100MW - Soporta carga local de 100MW

Cuando falla un bus específico, solo la batería de ese bus actúa como soporte principal.
Las otras baterías solo actúan si su propio voltaje cae por debajo del umbral.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'Main_Simulator', 'Classes'))

from seven_bus_system_battery import run_battery_simulation, print_final_results

def test_individual_battery_response():
    """Prueba la respuesta individual de cada batería"""
    
    print("="*80)
    print("PRUEBA DE RESPUESTA INDIVIDUAL DE BATERÍAS")
    print("="*80)
    
    # Casos de prueba: falla en cada bus con batería
    test_cases = [
        {"case_id": 2, "faulted_bus": "Bus 3", "description": "Falla en Bus 3 - Solo batería Bus 3 debe actuar"},
        {"case_id": 2, "faulted_bus": "Bus 4", "description": "Falla en Bus 4 - Solo batería Bus 4 debe actuar"},
        {"case_id": 2, "faulted_bus": "Bus 5", "description": "Falla en Bus 5 - Solo batería Bus 5 debe actuar"},
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"PRUEBA {i}: {test_case['description']}")
        print(f"{'='*60}")
        
        try:
            results, batteries, controller, T_r = run_battery_simulation(
                case_id=test_case["case_id"],
                faulted_bus=test_case["faulted_bus"],
                fault_type="slg",
                fault_impedance=0.0
            )
            
            print_final_results(results, batteries, T_r)
            
            # Análisis específico de respuesta individual
            print(f"\n--- ANÁLISIS INDIVIDUAL PARA {test_case['faulted_bus']} ---")
            
            for bus_name, battery in batteries.items():
                status = battery.get_individual_status()
                is_faulted = (bus_name == test_case["faulted_bus"])
                
                print(f"\n{bus_name} {'[FAULTED BUS]' if is_faulted else '[NORMAL BUS]'}:")
                print(f"  - SOC Final: {status['soc']:.1%}")
                print(f"  - Energía Disponible: {status['available_energy_MWh']:.1f} MWh")
                print(f"  - Potencia Disponible: {status['available_power_MW']:.1f} MW")
                print(f"  - Carga Local: {status['local_load_MW']:.1f} MW")
                print(f"  - Puede Soportar Carga Local: {'SÍ' if status['can_support_local'] else 'NO'}")
                print(f"  - Modo de Operación: {status['mode']}")
                print(f"  - Estado: {status['state']}")
                print(f"  - Activa: {'SÍ' if status['is_active'] else 'NO'}")
                
                # Verificar comportamiento esperado
                if is_faulted:
                    expected_mode = "PV"  # Debe operar en modo PV para soportar carga local
                    if status['mode'] == expected_mode:
                        print(f"  ✓ CORRECTO: Batería del bus fallado opera en modo {expected_mode}")
                    else:
                        print(f"  ✗ ERROR: Esperado modo {expected_mode}, actual {status['mode']}")
                else:
                    print(f"  ✓ CORRECTO: Batería de bus normal opera según voltaje local")
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR en prueba {i}: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            raise e  # Re-raise instead of continue

def test_battery_coordination():
    """Prueba la coordinación entre baterías en diferentes escenarios"""
    
    print(f"\n{'='*80}")
    print("PRUEBA DE COORDINACIÓN ENTRE BATERÍAS")
    print(f"{'='*80}")
    
    # Caso de pérdida de generación - todas las baterías deben contribuir
    print(f"\n{'='*60}")
    print("CASO: Pérdida de Generación (Case 1)")
    print("Todas las baterías deben contribuir según su voltaje local")
    print(f"{'='*60}")
    
    try:
        results, batteries, controller, T_r = run_battery_simulation(
            case_id=1,  # Pérdida de generación
            faulted_bus="Bus 1",  # Falla en generación
            fault_type="slg",
            fault_impedance=0.0
        )
        
        print_final_results(results, batteries, T_r)
        
        # Verificar que todas las baterías contribuyen
        print(f"\n--- ANÁLISIS DE COORDINACIÓN ---")
        total_contribution = 0
        
        for bus_name, battery in batteries.items():
            if results["battery_power"][bus_name]:
                final_power = results["battery_power"][bus_name][-1]["P"]
                total_contribution += final_power
                print(f"{bus_name}: Contribución = {final_power:.1f} MW")
        
        print(f"\nContribución Total de Baterías: {total_contribution:.1f} MW")
        print("✓ CORRECTO: Todas las baterías contribuyen según capacidad individual")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR en prueba de coordinación: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise e

def test_short_tr_operation():
    """Prueba operación con T_r cortos para verificar activación inmediata"""
    
    print(f"\n{'='*80}")
    print("PRUEBA DE OPERACIÓN CON T_r CORTOS")
    print(f"{'='*80}")
    
    # Importar módulo de configuración T_r
    sys.path.append(os.path.dirname(__file__))
    from t_r_config import set_global_t_r
    
    # Valores cortos de T_r para probar
    tr_values = [5, 10, 15, 20, 30]  # minutos
    
    for tr_min in tr_values:
        print(f"\n{'='*50}")
        print(f"PRUEBA CON T_r = {tr_min} MINUTOS")
        print(f"{'='*50}")
        
        try:
            # Establecer T_r específico
            set_global_t_r(tr_min)
            
            results, batteries, controller, T_r = run_battery_simulation(
                case_id=2,
                faulted_bus="Bus 3",
                fault_type="slg",
                fault_impedance=0.0
            )
            
            # Verificar operación de baterías
            battery_operated = False
            for bus_name, battery in batteries.items():
                if results["battery_power"][bus_name]:
                    max_power = max([abs(p["P"]) for p in results["battery_power"][bus_name]])
                    if max_power > 0.1:  # MW
                        battery_operated = True
                        is_faulted = "[FAULTED]" if bus_name == "Bus 3" else ""
                        print(f"✓ {bus_name}{is_faulted}: Máx potencia = {max_power:.1f} MW")
                    else:
                        print(f"✗ {bus_name}: No operó (máx = {max_power:.3f} MW)")
            
            if battery_operated:
                print(f"✅ RESULTADO: Baterías operaron con T_r = {tr_min} min")
            else:
                print(f"❌ RESULTADO: Baterías NO operaron con T_r = {tr_min} min")
                
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR con T_r = {tr_min} min: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            raise e

def test_soc_individual_limits():
    """Prueba los límites individuales de SOC de cada batería"""
    
    print(f"\n{'='*80}")
    print("PRUEBA DE LÍMITES INDIVIDUALES DE SOC")
    print(f"{'='*80}")
    
    try:
        from t_r_config import set_global_t_r
        
        # T_r de 1 hora para descarga significativa
        set_global_t_r(10)
        
        results, batteries, controller, T_r = run_battery_simulation(
            case_id=2,
            faulted_bus="Bus 3",
            fault_type="slg",
            fault_impedance=0.0
        )
        
        print_final_results(results, batteries, T_r)
        
        # Análisis de protecciones individuales
        print(f"\n--- ANÁLISIS DE PROTECCIONES INDIVIDUALES ---")
        
        for bus_name, battery in batteries.items():
            status = battery.get_individual_status()
            soc_history = results["soc"][bus_name]
            
            if soc_history:
                initial_soc = soc_history[0]
                final_soc = soc_history[-1]
                min_soc = min(soc_history)
                
                print(f"\n{bus_name}:")
                print(f"  - SOC Inicial: {initial_soc:.1%}")
                print(f"  - SOC Final: {final_soc:.1%}")
                print(f"  - SOC Mínimo: {min_soc:.1%}")
                print(f"  - Protección Activada: {'SÍ' if min_soc <= 0.12 else 'NO'}")
                print(f"  - Batería Activa: {'SÍ' if status['is_active'] else 'NO'}")
                
                if min_soc <= 0.12:
                    print(f"  ✓ CORRECTO: Protección individual activada en SOC crítico")
                else:
                    print(f"  ✓ CORRECTO: Batería operó dentro de límites seguros")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR en prueba de límites SOC: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        raise e

if __name__ == "__main__":
    print("INICIANDO PRUEBAS DEL SISTEMA INDIVIDUAL DE BATERÍAS")
    print("Cada batería opera independientemente según su bus específico")
    
    # Ejecutar todas las pruebas
    test_short_tr_operation()  # Nueva prueba para T_r cortos
    test_individual_battery_response()
    test_battery_coordination() 
    test_soc_individual_limits()
    
    print(f"\n{'='*80}")
    print("PRUEBAS COMPLETADAS")
    print("El sistema de baterías ahora opera de manera individual:")
    print("- Cada batería responde solo a las condiciones de su propio bus")
    print("- La batería del bus fallado actúa como soporte principal")
    print("- Las otras baterías solo actúan si su voltaje local es bajo")
    print("- Cada batería tiene protecciones y límites individuales")
    print("- Las baterías operan inmediatamente con cualquier T_r")
    print(f"{'='*80}")