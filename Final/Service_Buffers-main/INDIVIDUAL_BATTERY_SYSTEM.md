# Sistema Individual de Baterías - Documentación

## Resumen de Cambios Implementados

El sistema de baterías ha sido modificado para operar de manera **completamente individual**, donde cada batería responde específicamente a las condiciones de su propio bus, en lugar de actuar colectivamente.

## Arquitectura del Sistema Individual

### Configuración de Baterías por Bus

| Bus | Capacidad | Potencia Máx | Carga Local | Función Principal |
|-----|-----------|--------------|-------------|-------------------|
| Bus 3 | 240 MWh | 110 MW | 110 MW | Soporte directo carga local |
| Bus 4 | 220 MWh | 100 MW | 100 MW | Soporte directo carga local |
| Bus 5 | 220 MWh | 100 MW | 100 MW | Soporte directo carga local |

### Lógica de Control Individual

#### 1. **Batería del Bus Fallado**
- **Modo**: PV (Voltaje-Potencia fija)
- **Acción**: Suministra potencia para soportar la carga local completa
- **Prioridad**: Máxima - actúa inmediatamente
- **Límite**: Hasta su capacidad máxima (Pmax)

#### 2. **Baterías de Buses No Fallados**
- **Modo**: DROOP (Respuesta proporcional)
- **Acción**: Solo actúan si su voltaje local < 0.85 pu
- **Respuesta**: Proporcional al déficit de voltaje en su propio bus
- **Límite**: Escalado por disponibilidad de SOC individual

## Modificaciones Implementadas

### 1. **BatteryController** (`battery_controller.py`)

```python
def program_bess(self, case_id, sim_state, Vm, faulted_bus=None):
    for b in self._active_bess():
        bus_voltage = Vm.get(b.bus_name, 1.0)
        is_faulted_bus = (faulted_bus == b.bus_name)
        
        if is_faulted_bus:
            # Batería del bus fallado: modo PV
            b.mode = "PV"
            P_local = self._loads_at(b.bus_name)
            b.Pref_MW = min(b.Pmax, P_local)
        else:
            # Otras baterías: solo si voltaje bajo
            if bus_voltage >= self.V_MIN_SERVICE:
                b.Pref_MW = 0.0  # No actúa
            else:
                # Respuesta proporcional individual
                voltage_deficit = max(0, 0.95 - bus_voltage)
                power_support = voltage_deficit * b.Pmax * factor
                b.Pref_MW = min(b.Pmax, power_support)
```

**Cambios Clave**:
- ✅ Parámetro `faulted_bus` para identificar bus específico
- ✅ Control individual por batería según su bus
- ✅ Umbral de voltaje individual (0.85 pu)
- ✅ Factores de respuesta específicos por caso

### 2. **Battery Class** (`Battery.py`)

```python
def compute_PQ(self, V_bus: complex) -> tuple[float, float]:
    # Lógica individual por batería
    soc_factor = max(0.1, (self.soc - 0.1) / 0.85)
    available_power = self.Pmax * soc_factor
    
    if self.mode == "PV":
        # Soporte directo para carga local
        P = min(available_power, self.Pref_MW)
    else:  # DROOP
        # Respuesta individual al voltaje local
        voltage_deficit = max(0, self.V_ref_pu - Vm)
        P = min(available_power, voltage_deficit * available_power * 2.0)
```

**Cambios Clave**:
- ✅ Factor SOC individual para disponibilidad de potencia
- ✅ Protecciones individuales por batería (SOC < 12%)
- ✅ Carga local específica por bus
- ✅ Método `get_individual_status()` para análisis detallado

### 3. **Simulación Principal** (`seven_bus_system_battery.py`)

```python
# Control individual en la aplicación de inyecciones
for bus_name, battery in batteries.items():
    is_faulted_bus = (faulted_bus == bus_name)
    bus_voltage = V_complex_dict.get(bus_name, 1+0j)
    
    if is_faulted_bus and sim_state == "discharge":
        # Máxima potencia para bus fallado
        P = min(battery.Pmax, local_load)
    elif not is_faulted_bus and abs(bus_voltage) >= 0.85:
        # Escalado por déficit de voltaje individual
        P = P * max(0, (0.95 - abs(bus_voltage)) / 0.1)
```

**Cambios Clave**:
- ✅ Inyección individual por batería según estado de su bus
- ✅ Análisis detallado de rendimiento individual
- ✅ Logging con identificación de bus fallado
- ✅ Estadísticas individuales de energía y utilización

## Comportamiento por Casos

### **Case 1: Pérdida de Generación**
- **Bus Fallado**: Bus 1 o Bus 7 (generadores)
- **Respuesta**: Todas las baterías contribuyen según su voltaje local
- **Modo**: DROOP para todas las baterías
- **Coordinación**: Cada batería responde independientemente

### **Case 2: Pérdida de Bus de Carga**
- **Bus Fallado**: Bus 3, 4, o 5 (con carga)
- **Respuesta**: Solo la batería del bus fallado actúa como principal
- **Modo**: PV para batería fallada, DROOP para otras (si voltaje bajo)
- **Aislamiento**: Máxima independencia entre baterías

### **Case 3: Pérdida de Comunicaciones**
- **Bus Fallado**: Cualquier bus con aumento de carga
- **Respuesta**: Cada batería según su voltaje local individual
- **Modo**: DROOP para todas, respuesta proporcional
- **Distribución**: No hay reparto equitativo, cada una según necesidad local

## Protecciones Individuales

### **Límites por SOC Individual**
```python
def soc_update_discharge(self, dt_h: float, P_MW: float):
    # Protección individual por batería
    if self.soc <= 0.12:
        self.is_active = False  # Desconectar solo esta batería
    
    # Potencia limitada por SOC individual
    actual_power = min(P_MW, self.Pmax * (self.soc - 0.1) / 0.85)
```

### **Reactivación Individual**
```python
def soc_update_charge(self, dt_h: float, P_MW: float):
    # Reactivar batería individual cuando SOC se recupera
    if self.soc >= 0.15 and not self.is_active:
        self.is_active = True
```

## Ventajas del Sistema Individual

### ✅ **Independencia Operativa**
- Cada batería opera según condiciones locales de su bus
- No hay dependencia entre baterías
- Falla de una batería no afecta a las otras

### ✅ **Respuesta Específica**
- La batería del bus fallado actúa como soporte principal
- Otras baterías solo actúan si realmente necesario
- Evita sobrecompensación innecesaria

### ✅ **Protecciones Individuales**
- Límites SOC específicos por batería
- Desconexión/reconexión individual
- Preservación de vida útil individual

### ✅ **Análisis Detallado**
- Rendimiento individual por batería
- Utilización específica por bus
- Identificación de batería más/menos utilizada

## Pruebas y Validación

El archivo `test_individual_batteries.py` incluye:

1. **Prueba de Respuesta Individual**: Verifica que solo la batería del bus fallado actúe como principal
2. **Prueba de Coordinación**: Valida respuesta colectiva en pérdida de generación
3. **Prueba de Límites SOC**: Confirma protecciones individuales

### Ejecutar Pruebas
```bash
python test_individual_batteries.py
```

## Resultados Esperados

### **Falla en Bus 3**
- ✅ Batería Bus 3: Modo PV, suministra 110 MW
- ✅ Batería Bus 4: Modo DROOP, actúa solo si V < 0.85 pu
- ✅ Batería Bus 5: Modo DROOP, actúa solo si V < 0.85 pu

### **Falla en Bus 4**
- ✅ Batería Bus 4: Modo PV, suministra 100 MW
- ✅ Batería Bus 3: Modo DROOP, actúa solo si V < 0.85 pu
- ✅ Batería Bus 5: Modo DROOP, actúa solo si V < 0.85 pu

### **Falla en Bus 5**
- ✅ Batería Bus 5: Modo PV, suministra 100 MW
- ✅ Batería Bus 3: Modo DROOP, actúa solo si V < 0.85 pu
- ✅ Batería Bus 4: Modo DROOP, actúa solo si V < 0.85 pu

## Conclusión

El sistema ahora opera con **completa independencia entre baterías**, donde cada una responde específicamente a las condiciones de su propio bus. Esto proporciona:

- **Mayor precisión** en la respuesta a fallas
- **Mejor utilización** de recursos individuales
- **Protección mejorada** de cada batería
- **Análisis detallado** del rendimiento individual

La implementación asegura que cuando falla un bus específico, solo la batería de ese bus se ve directamente afectada y debe soportar su carga local, mientras las otras baterías mantienen su operación normal a menos que sus propias condiciones locales lo requieran.