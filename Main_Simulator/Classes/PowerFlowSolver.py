import numpy as np
import pandas as pd

from Classes.Circuit import Circuit
from system_setting import SystemSettings
from Jacobians import Jacobian


class PowerFlowSolver:
    def __init__(self, solver: int, circuit: Circuit, do_one_iteration: bool = False):
        self.solver = solver
        self.Circuit = circuit
        self.Circuit.calc_ybus()

        # ✅ Verify the bus classifications before proceeding
        print("\n[DEBUG] Bus Type Classification (Used in PowerFlowSolver):")
        for bus_name, bus in self.Circuit.buses.items():
            print(f"  - {bus_name}: {bus.bus_type}")

        self.flat_start()

        # Solve Method
        self.initialize_x()
        y = self.initialize_y()


        #Real Power
        Px = self.calc_Px()
        Px = {bus: float(Px[bus]) for bus in Px}


        #Reactive Power
        Qx = self.calc_Qx()
        Qx = {bus: float(Qx[bus]) for bus in Qx}

        #Mistmatch
        yx = self.calculate_yx(Px, Qx)
        self.del_y = self.calculate_power_mismatch(y, yx)
        self.del_y_trimmed = self.calculate_trimmed_power_mismatch(self.del_y)

        # Compute Jacobian for first iteration
        jacobian_instance = Jacobian(self.Circuit, self.delta, self.voltage)
        self.J = jacobian_instance.get_full_jacobian()
        self.J_trimmed = jacobian_instance.get_trimmed_jacobian()

    def flat_start(self):
        """Initializes flat start with delta=0 and voltage=1 p.u."""
        self.delta = {bus: 0 for bus in self.Circuit.bus_order()}
        self.voltage = {bus: 1 for bus in self.Circuit.bus_order()}

    def initialize_x(self):
        """Constructs state variable vector x (delta and voltage magnitudes)."""
        delta_vector = np.array(list(self.delta.values()))
        voltage_vector = np.array(list(self.voltage.values()))
        print("[DEBUG] delta:", self.delta)
        print("[DEBUG] voltage:", self.voltage)

        x = np.concatenate((delta_vector, voltage_vector))

        # Debugging output
        print(f"[DEBUG] x initialized with shape {x.shape}")

        return x

    def initialize_y(self):
        """Initializes y vector by extracting per-unit real and reactive power values, excluding Slack and PV buses."""

        # Extract per-unit real and reactive power values
        real_power_vector = np.array(list(self.Circuit.real_power_vector().values())) /(self.Circuit.get_base_power())
        reactive_power_vector = np.array(list(self.Circuit.reactive_power_vector().values())) / (self.Circuit.get_base_power())

        # Initialize y vectors
        y_real = []
        y_reactive = []

        for bus in self.Circuit.bus_order():
            if self.Circuit.bus_type[bus] != "Slack Bus":
                y_real.append(real_power_vector[self.Circuit.bus_order().index(bus)])

        for bus in self.Circuit.bus_order():
            if self.Circuit.bus_type[bus] not in ["Slack Bus", "PV Bus"]:
                y_reactive.append(reactive_power_vector[self.Circuit.bus_order().index(bus)])

        y = np.concatenate((y_real,y_reactive))

        print("\n--- INITIALIZED y (Specified Power Vector) ---")
        for i, val in enumerate(y):
            print(f"y[{i}] = {val:.6f}")
        print(f"[DEBUG] y shape = {y.shape}\n")
        return y

    def calculate_yx(self, Px, Qx):
        """
        Calculates the expected power injection vector yx = [P, Q] for all buses,
        using explicitly provided Px and Qx dictionaries. Assumes all buses are included.
        """
        yx_P = [Px[bus] for bus in self.Circuit.bus_order()]
        yx_Q = [Qx[bus] for bus in self.Circuit.bus_order()]

        yx = np.concatenate((yx_P, yx_Q))

        print("\n--- CALCULATED yx (Injected Power Vector) ---")
        for i, val in enumerate(yx):
            print(f"yx[{i}] = {val:.6f}")
        print(f"[DEBUG] yx shape = {yx.shape}\n")

        return yx

    def calculate_power_mismatch(self, y, yx):
        y = np.array(y)
        yx = np.array(yx)
        del_y = y - yx
        print("\n--- MISMATCH Vector Δy = y - yx ---")
        for i, val in enumerate(del_y):
            print(f"Δy[{i}] = {val:.6f}")
        print(f"[DEBUG] del_y shape = {del_y.shape}\n")

        return del_y

    def calculate_trimmed_power_mismatch(self, full_del_y):
        bus_order = self.Circuit.bus_order()
        n = len(bus_order)

        # For P mismatch: for each bus i that is not a Slack bus, keep full_del_y[i].
        trimmed_p_indices = [i for i, bus in enumerate(bus_order)
                             if self.Circuit.buses[bus].bus_type == "PQ Bus" or self.Circuit.buses[
                                 bus].bus_type == "PV Bus"]

        # For Q mismatch: for each bus i that is a PQ bus, keep full_del_y[i+n].
        trimmed_q_indices = [i + n for i, bus in enumerate(bus_order)
                             if self.Circuit.buses[bus].bus_type == "PQ Bus"]

        # Combine the indices: first the P mismatches, then the Q mismatches.
        indices_to_keep = trimmed_p_indices + trimmed_q_indices
        del_y_trimmed = full_del_y[indices_to_keep]

        print("\n[DEBUG] Trimmed mismatch vector Δy_trimmed:")
        for idx, val in enumerate(del_y_trimmed):
            print(f"Δy_trimmed[{idx}] = {val:.6f}")
        print(f"[DEBUG] Trimmed mismatch shape = {del_y_trimmed.shape}\n")

        return del_y_trimmed

    def calc_Px(self):
        """Computes real power (P) injections using polar form."""
        Px = {}
        bus_order = self.Circuit.bus_order()

        for bus_k in bus_order:
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            P_k = 0.0

            for bus_n in bus_order:
                V_n = self.voltage[bus_n]
                δ_n = self.delta[bus_n]
                Y_kn = self.Circuit.ybus.at[bus_k, bus_n]
                θ_kn = np.angle(Y_kn)

                P_k += V_k * V_n * abs(Y_kn) * np.cos(δ_k - δ_n - θ_kn)

            Px[bus_k] = P_k

        return Px

    def calc_Qx(self):
        """Computes reactive power (Q) injections using polar form."""
        Qx = {}
        bus_order = self.Circuit.bus_order()

        for bus_k in bus_order:
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            Q_k = 0.0

            for bus_n in bus_order:
                V_n = self.voltage[bus_n]
                δ_n = self.delta[bus_n]
                Y_kn = self.Circuit.ybus.at[bus_k, bus_n]
                θ_kn = np.angle(Y_kn)

                Q_k += V_k * V_n * abs(Y_kn) * np.sin(δ_k - δ_n - θ_kn)

            Qx[bus_k] = Q_k

        return Qx


    def calculate_delta_x(self):
        if not hasattr(self, 'del_y'):
            raise ValueError("Mismatch vector Δy has not been computed.")
        J = self.construct_jacobian(self.J1, self.J2, self.J3, self.J4)
        delta_x = np.linalg.solve(J, self.del_y)
        return delta_x

    def update_angles_voltages(self):
        delta_x = self.calculate_delta_x()

        num_angles = len([bus for bus in self.Circuit.bus_order() if self.Circuit.bus_type[bus] != 'Slack Bus'])
        delta_angles = delta_x[:num_angles]
        delta_voltages = delta_x [num_angles:]

        angle_index = 0
        voltage_index = 0

        for bus in self.Circuit.bus_order():
            if self.Circuit.bus_type[bus] != 'Slack Bus':
                self.delta[bus] += delta_angles[angle_index]
                angle_index += 1
            if self.Circuit.bus_type[bus] not in ['Slack Bus', 'PV Bus']:
                self.voltage[bus] += delta_voltages[voltage_index]
                voltage_index += 1
        print(self.delta)
