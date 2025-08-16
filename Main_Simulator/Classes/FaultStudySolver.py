import numpy as np

from Classes.Circuit import Circuit
from Classes.generator import Generator

class FaultStudySolver:
    def __init__(self, circuit:Circuit, faulted_bus:str, fault_type='3ph', fault_impedance:float=0.0):
        self.circuit = circuit
        self.faulted_bus = faulted_bus
        self.fault_type = fault_type.lower()
        self.fault_impedance = fault_impedance
        self.fault_current = None
        self.voltages = {}
        self.phase_voltages = {}

    def run(self):
        if self.fault_type == '3ph':
            return self.run_3ph_fault()
        elif self.fault_type == 'slg':
            return self.run_slg_fault()
        elif self.fault_type == 'll':
            return self.run_ll_fault()
        elif self.fault_type == 'dlg':
            return self.run_dlg_fault()
        else:
            raise ValueError(f"Unsupported fault type: {self.fault_type}")

    def run_3ph_fault(self):
        '''
        system base in the setting: Q of Generator1 = 100 Mvar, Q of Generator2 is 200 Mvar
        pu S = sqrt(Q**2 + P**2)
        '''

        # For fault study, we use the augmented positive-sequence Ybus.
        Ybus_positive_df = self.circuit.calc_ybus_positive()
        Ybus_positive = Ybus_positive_df.values

        Zbus = np.linalg.inv(Ybus_positive)

        # Determine the index corresponding to the faulted bus.
        bus_order = list(Ybus_positive_df.index)
        try:
            n = bus_order.index(self.faulted_bus)
        except ValueError:
            raise ValueError(f"Faulted bus '{self.faulted_bus}' not found in the augmented Ybus.")


        # Calculate fault current (V_F is 1.0 p.u. pre-fault voltage)
        V_F = 1.0
        Z_nn = Zbus[n, n] + self.fault_impedance # add fault impedance in series with the bus driving point
        I_complex = V_F / Z_nn
        I_mag = np.abs(I_complex)
        I_ang = np.degrees(np.angle(I_complex))
        if I_ang > 180:
            I_ang -= 360
        self.fault_current = (I_mag, I_ang)  # ⬅️ store tuple, fully formatted

        # Calculate post-fault bus voltages; at the faulted bus, E_n becomes 0.
        raw_voltages = {}
        for k, node in enumerate(bus_order):
            E_k_complex = (1 - (Zbus[k, n] / Z_nn)) * V_F
            magnitude = np.abs(E_k_complex)
            angle_deg = np.degrees(np.angle(E_k_complex))
            raw_voltages[node] = (magnitude, angle_deg)

        # Dynamically find the slack bus
        slack_bus = None
        for name, bus in self.circuit.buses.items():
            if bus.bus_type == "Slack Bus":
                slack_bus = name
                break

        if slack_bus is None:
            raise ValueError("No Slack Bus defined in the circuit.")

        # Normalize all angles so that Slack Bus has angle 0°
        ref_angle = raw_voltages[slack_bus][1]
        # for node, (mag, ang) in raw_voltages.items():
        #     self.voltages[node] = (mag, ang - ref_angle)
        self.voltages = {node: (mag, ang - ref_angle) for node, (mag, ang) in raw_voltages.items()}

        # updates: result should use voltage magnitude and degree
        return self.fault_current, self.voltages  # where fault_current = (magnitude, angle)

    def run_slg_fault(self):
        Y1 = self.circuit.calc_ybus_positive()
        Y2 = self.circuit.calc_ybus_negative()
        Y0 = self.circuit.calc_ybus_zero()

        Z1 = np.linalg.inv(Y1.values)
        Z2 = np.linalg.inv(Y2.values)
        Z0 = np.linalg.inv(Y0.values)

        bus_order = list(Y1.index)
        n = bus_order.index(self.faulted_bus)

        Vf = 1.0
        Z_eq = Z1[n, n] + Z2[n, n] + Z0[n, n] + 3 * self.fault_impedance
        # total 3‑sequence current
        If = 3 * Vf / Z_eq
        # each sequence current is one third of that
        Iseq = Vf / Z_eq

        # Sequence fault currents (at faulted bus only)
        I0 = I1 = I2 = Iseq
        self.seq_fault_current = (I0, I1, I2)

        # Store fault current in polar form
        self.fault_current = (np.abs(If), np.degrees(np.angle(If)))

        # Sequence voltages at all buses
        slack_bus = next(name for name, bus in self.circuit.buses.items() if bus.bus_type == "Slack Bus")
        slack_idx = bus_order.index(slack_bus)
        V1_slack = 1 + 0j  # Prefault positive-sequence voltage at slack

        V1 = np.array([V1_slack - Z1[k, n] * I1 for k in range(len(bus_order))])
        V2 = np.array([-Z2[k, n] * I2 for k in range(len(bus_order))])
        V0 = np.array([-Z0[k, n] * I0 for k in range(len(bus_order))])

        self.seq_voltages = {
            bus_order[k]: (V0[k], V1[k], V2[k]) for k in range(len(bus_order))
        }

        # Enforce boundary condition: V0 + V1 + V2 = 0 at the faulted bus
        V1[n] = V1_slack - Z1[n, n] * I1
        V2[n] = - Z2[n, n] * I2
        V0[n] = - (V1[n] + V2[n])

        self.seq_voltages = {
            bus_order[k]: (V0[k], V1[k], V2[k])
            for k in range(len(bus_order))
        }

        # Track buses that have already been adjusted
        adjusted_buses = set()

        print("\n--- Adjusting Sequence Voltages Across Transformers ---")
        for transformer in self.circuit.transformers.values():
            b1 = transformer.bus1.name
            b2 = transformer.bus2.name

            if b1 in bus_order and b2 in bus_order:
                i = bus_order.index(b1)
                j = bus_order.index(b2)

                if b2 not in adjusted_buses:
                    old_V1, old_V2, old_V0 = V1[j], V2[j], V0[j]

                    V1[j] = transformer.adjust_sequence_voltage(V1[j], direction="primary_to_secondary")
                    V2[j] = transformer.adjust_sequence_voltage(V2[j], direction="primary_to_secondary")
                    V0[j] = transformer.adjust_sequence_voltage(V0[j], direction="primary_to_secondary")

                    adjusted_buses.add(b2)

                    print(f"Adjusted {b2} via {transformer.name} (Δ→Y):")
                    print(f"    V1: {old_V1:.4f} → {V1[j]:.4f}")
                    print(f"    V2: {old_V2:.4f} → {V2[j]:.4f}")
                    print(f"    V0: {old_V0:.4f} → {V0[j]:.4f}")

        # Convert sequence voltages to phase voltages
        a = np.exp(1j * 2 * np.pi / 3)
        A = np.array([
            [1, 1, 1],
            [1, a ** 2, a],
            [1, a, a ** 2]
        ])
        V_012 = np.vstack([V0, V1, V2])
        V_abc = A @ V_012

        # Enforce V_a = 0 at the faulted bus for bolted SLG
        # V_abc[0, n] = 0.0

        self.phase_voltages = {
            bus_order[k]: (
                (np.abs(V_abc[0, k]), np.degrees(np.angle(V_abc[0, k]))),  # Va
                (np.abs(V_abc[1, k]), np.degrees(np.angle(V_abc[1, k]))),  # Vb
                (np.abs(V_abc[2, k]), np.degrees(np.angle(V_abc[2, k]))),  # Vc
            )
            for k in range(len(bus_order))
        }

        print(
            f"{transformer.name}: V_base_ratio = {transformer.V_base_ratio:.4f}, phase_shift = {transformer.phase_shift_deg}°")

        # --- Phase Fault Currents ---
        I_012 = np.array([I0, I1, I2])
        I_abc = A @ I_012
        self.phase_fault_current = {
            'Ia': (np.abs(I_abc[0]), np.degrees(np.angle(I_abc[0]))),
            'Ib': (np.abs(I_abc[1]), np.degrees(np.angle(I_abc[1]))),
            'Ic': (np.abs(I_abc[2]), np.degrees(np.angle(I_abc[2]))),
        }

        # --- Per-unit Voltage Magnitude and Angle for Reporting ---
        Va = V0 + V1 + V2
        raw_voltages = {
            bus_order[k]: (np.abs(Va[k]), np.degrees(np.angle(Va[k])))
            for k in range(len(bus_order))
        }

        ref_angle = raw_voltages[slack_bus][1]
        self.voltages = {
            bus: (mag, ang - ref_angle) for bus, (mag, ang) in raw_voltages.items()
        }

        return self.fault_current, self.voltages

    def run_ll_fault(self):
        """Line-to-Line (LL) fault"""
        # Build sequence Ybus and invert to get Zbus for pos & neg
        Y1 = self.circuit.calc_ybus_positive()
        Y2 = self.circuit.calc_ybus_negative()
        Z1 = np.linalg.inv(Y1.values)
        Z2 = np.linalg.inv(Y2.values)

        # Find faulted‐bus index
        bus_order = list(Y1.index)
        n = bus_order.index(self.faulted_bus)

        # Pre-fault voltage
        Vf = 1.0

        # Equivalent driving‐point impedance: positive + negative sequence in series, plus fault‑impedance
        Z_eq = Z1[n, n] + Z2[n, n] + self.fault_impedance

        # Sequence currents: I1 = Vf/Z_eq, I2 = –I1, I0 = 0
        I1 = Vf / Z_eq
        I2 = -I1
        I0 = 0 + 0j

        # Store sequence fault currents
        self.seq_fault_current = (I0, I1, I2)

        # Also store total phase‐fault current (magnitude & angle) for reporting
        I_mag = np.abs(I1)
        I_ang = np.degrees(np.angle(I1))
        if I_ang > 180:
            I_ang -= 360
        self.fault_current = (I_mag, I_ang)

        # Compute sequence voltages at every bus
        V1 = np.array([1 - Z1[k, n] * I1 for k in range(len(bus_order))], dtype=complex)
        V2 = np.array([-Z2[k, n] * I2 for k in range(len(bus_order))], dtype=complex)
        V0 = np.zeros(len(bus_order), dtype=complex)

        V2[n] = 0 + 0j
        V0[n] = 0 + 0j
        V1[n] = Vf - Z1[n, n] * I1

        self.seq_voltages = {
            bus_order[k]: (V0[k], V1[k], V2[k])
            for k in range(len(bus_order))
        }

        # Transform to phase voltages & phase currents
        a = np.exp(1j * 2 * np.pi / 3)
        A = np.array([[1, 1, 1],
                      [1, a ** 2, a],
                      [1, a, a ** 2]], dtype=complex)

        V012 = np.vstack([V0, V1, V2])  # shape (3, N)
        Vabc = A @ V012  # shape (3, N)
        I012 = np.array([I0, I1, I2])  # shape (3,)
        Iabc = A @ I012  # shape (3,)

        self.phase_voltages = {
            bus_order[k]: (
                (abs(Vabc[0, k]), np.degrees(np.angle(Vabc[0, k]))),
                (abs(Vabc[1, k]), np.degrees(np.angle(Vabc[1, k]))),
                (abs(Vabc[2, k]), np.degrees(np.angle(Vabc[2, k]))),
            )
            for k in range(len(bus_order))
        }

        self.phase_fault_current = {
            'Ia': (abs(Iabc[0]), np.degrees(np.angle(Iabc[0]))),
            'Ib': (abs(Iabc[1]), np.degrees(np.angle(Iabc[1]))),
            'Ic': (abs(Iabc[2]), np.degrees(np.angle(Iabc[2]))),
        }

        Ib_cplx = Iabc[1]
        mag_B = np.abs(Ib_cplx)
        ang_B = np.degrees(np.angle(Ib_cplx))
        if ang_B > 180:
            ang_B -= 360
        self.fault_current = (mag_B, ang_B)

        # Normalize phase‐voltages so slack bus angle = 0°
        slack_bus = next(name for name, b in self.circuit.buses.items() if b.bus_type == "Slack Bus")
        ref_ang = self.phase_voltages[slack_bus][0][1]  # Va angle at slack
        self.voltages = {
            bus: (Va_mag, Va_ang - ref_ang)
            for bus, ((Va_mag, Va_ang), _, _) in self.phase_voltages.items()
        }

        return self.fault_current, self.voltages

    def run_dlg_fault(self):
        """Double Line-to-Ground fault"""
        # Build sequence Ybus and invert to get Zbus for pos/neg/zero
        Y1 = self.circuit.calc_ybus_positive()
        Y2 = self.circuit.calc_ybus_negative()
        Y0 = self.circuit.calc_ybus_zero()
        Z1 = np.linalg.inv(Y1.values)
        Z2 = np.linalg.inv(Y2.values)
        Z0 = np.linalg.inv(Y0.values)

        # Find faulted‐bus index
        bus_order = list(Y1.index)
        n = bus_order.index(self.faulted_bus)

        # Pre-fault voltage
        Vf = 1.0

        # Equivalent driving‐point impedance: all three seq nets in series, plus 3·Zf for the ground connection
        Z_eq = Z1[n, n] + Z2[n, n] + Z0[n, n] + 3 * self.fault_impedance

        # All three sequence currents equal I_f = 3·Vf / Z_eq
        I_f = 3 * Vf / Z_eq
        I0 = I1 = I2 = I_f

        # Store sequence fault currents
        self.seq_fault_current = (I0, I1, I2)

        # Also store total phase‐fault current (magnitude & angle) for reporting
        I_mag = np.abs(I_f)
        I_ang = np.degrees(np.angle(I_f))
        if I_ang > 180:
            I_ang -= 360
        self.fault_current = (I_mag, I_ang)

        # Compute sequence voltages at every bus
        N = len(bus_order)
        V1 = np.array([1.0 - Z1[k, n] * I1 for k in range(N)])
        V2 = np.array([-Z2[k, n] * I2 for k in range(N)])
        V0 = np.array([-Z0[k, n] * I0 for k in range(N)])

        self.seq_voltages = {
            bus_order[k]: (V0[k], V1[k], V2[k])
            for k in range(N)
        }

        # Transform to phase quantities
        a = np.exp(1j * 2 * np.pi / 3)
        A = np.array([[1, 1, 1],
                      [1, a ** 2, a],
                      [1, a, a ** 2]])

        V012 = np.vstack([V0, V1, V2])
        Vabc = A @ V012
        self.phase_voltages = {
            bus_order[k]: (
                (abs(Vabc[0, k]), np.degrees(np.angle(Vabc[0, k]))),
                (abs(Vabc[1, k]), np.degrees(np.angle(Vabc[1, k]))),
                (abs(Vabc[2, k]), np.degrees(np.angle(Vabc[2, k]))),
            )
            for k in range(N)
        }

        I012 = np.array([I0, I1, I2])
        Iabc = A @ I012
        self.phase_fault_current = {
            'Ia': (abs(Iabc[0]), np.degrees(np.angle(Iabc[0]))),
            'Ib': (abs(Iabc[1]), np.degrees(np.angle(Iabc[1]))),
            'Ic': (abs(Iabc[2]), np.degrees(np.angle(Iabc[2]))),
        }

        # Normalize phase‐voltages to slack reference
        slack = next(b for b, obj in self.circuit.buses.items() if obj.bus_type == "Slack Bus")
        ref_ang = self.phase_voltages[slack][0][1]
        self.voltages = {
            bus: (mag, ang - ref_ang)
            for bus, (Va, Vb, Vc) in self.phase_voltages.items()
            for mag, ang in [Va]
        }

        return self.fault_current, self.voltages


    def __repr__(self):
        return f"FaultStudySolver(faulted_bus='{self.faulted_bus}', fault_type='{self.fault_type}')"



