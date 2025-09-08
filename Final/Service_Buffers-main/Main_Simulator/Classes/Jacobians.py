import numpy as np
import pandas as pd

class Jacobian:
    def __init__(self, circuit, delta, voltage):
        """
        Initializes the Jacobian computation with the given circuit data,
        current voltage angles (delta) and magnitudes (voltage).
        """
        self.circuit = circuit
        self.delta = delta
        self.voltage = voltage

    def calculate_J1(self):
        """Calculates J1: ∂P/∂δ for all buses."""
        bus_order = self.circuit.bus_order()
        n = len(bus_order)
        J1 = np.zeros((n, n))
        for k, bus_k in enumerate(bus_order):
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            for j, bus_j in enumerate(bus_order):
                V_j = self.voltage[bus_j]
                δ_j = self.delta[bus_j]
                Y_kj = self.circuit.ybus.at[bus_k, bus_j]
                θ_kj = np.angle(Y_kj)
                if k != j:
                    # Off-diagonal: J1[k, j] = V_k * V_j * |Y_kj| * sin(δ_k - δ_j - θ_kj)
                    J1[k, j] = V_k * V_j * abs(Y_kj) * np.sin(δ_k - δ_j - θ_kj)
                else:
                    # Diagonal: J1[k, k] = -V_k * Σ (over n ≠ k) [V_n * |Y_kn| * sin(δ_k - δ_n - θ_kn)]
                    J1[k, j] = -V_k * sum(
                        self.voltage[bus_m] * abs(self.circuit.ybus.at[bus_k, bus_m]) *
                        np.sin(δ_k - self.delta[bus_m] - np.angle(self.circuit.ybus.at[bus_k, bus_m]))
                        for m, bus_m in enumerate(bus_order) if m != k
                    )
        J1_df = pd.DataFrame(J1, index=bus_order, columns=bus_order)
        print("\n[DEBUG] J1 (∂P/∂δ):")
        print(J1_df)
        return J1

    def calculate_J2(self):
        """Calculates J2: ∂P/∂V for all buses."""
        bus_order = self.circuit.bus_order()
        n = len(bus_order)
        J2 = np.zeros((n, n))
        for k, bus_k in enumerate(bus_order):
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            for j, bus_j in enumerate(bus_order):
                δ_j = self.delta[bus_j]
                Y_kj = self.circuit.ybus.at[bus_k, bus_j]
                θ_kj = np.angle(Y_kj)
                if k != j:
                    # Off-diagonal: J2[k, j] = V_k * |Y_kj| * cos(δ_k - δ_j - θ_kj)
                    J2[k, j] = V_k * abs(Y_kj) * np.cos(δ_k - δ_j - θ_kj)
                else:
                    # Diagonal: includes self-admittance and contributions from all buses
                    Y_kk = self.circuit.ybus.at[bus_k, bus_k]
                    θ_kk = np.angle(Y_kk)
                    diag_term = V_k * abs(Y_kk) * np.cos(θ_kk)
                    sum_term = sum(
                        abs(self.circuit.ybus.at[bus_k, bus_m]) * self.voltage[bus_m] *
                        np.cos(δ_k - self.delta[bus_m] - np.angle(self.circuit.ybus.at[bus_k, bus_m]))
                        for m, bus_m in enumerate(bus_order)
                    )
                    J2[k, j] = diag_term + sum_term
        J2_df = pd.DataFrame(J2, index=bus_order, columns=bus_order)
        print("\n[DEBUG] J2 (∂P/∂V):")
        print(J2_df)
        return J2

    def calculate_J3(self):
        """Calculates J3: ∂Q/∂δ for all buses."""
        bus_order = self.circuit.bus_order()
        n = len(bus_order)
        J3 = np.zeros((n, n))
        for k, bus_k in enumerate(bus_order):
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            for j, bus_j in enumerate(bus_order):
                V_j = self.voltage[bus_j]
                δ_j = self.delta[bus_j]
                Y_kj = self.circuit.ybus.at[bus_k, bus_j]
                θ_kj = np.angle(Y_kj)
                if k != j:
                    # Off-diagonal: J3[k, j] = -V_k * V_j * |Y_kj| * cos(δ_k - δ_j - θ_kj)
                    J3[k, j] = -V_k * V_j * abs(Y_kj) * np.cos(δ_k - δ_j - θ_kj)
                else:
                    # Diagonal: sum contributions from all other buses
                    sum_term = sum(
                        abs(self.circuit.ybus.at[bus_k, bus_m]) * self.voltage[bus_m] *
                        np.cos(δ_k - self.delta[bus_m] - np.angle(self.circuit.ybus.at[bus_k, bus_m]))
                        for m, bus_m in enumerate(bus_order) if m != k
                    )
                    J3[k, j] = V_k * sum_term
        J3_df = pd.DataFrame(J3, index=bus_order, columns=bus_order)
        print("\n[DEBUG] J3 (∂Q/∂δ):")
        print(J3_df)
        return J3

    def calculate_J4(self):
        """Calculates J4: ∂Q/∂V for all buses."""
        bus_order = self.circuit.bus_order()
        n = len(bus_order)
        J4 = np.zeros((n, n))
        for k, bus_k in enumerate(bus_order):
            V_k = self.voltage[bus_k]
            δ_k = self.delta[bus_k]
            for j, bus_j in enumerate(bus_order):
                Y_kj = self.circuit.ybus.at[bus_k, bus_j]
                θ_kj = np.angle(Y_kj)
                if k != j:
                    # Off-diagonal: J4[k, j] = V_k * |Y_kj| * sin(δ_k - δ_j - θ_kj)
                    J4[k, j] = V_k * abs(Y_kj) * np.sin(δ_k - self.delta[bus_j] - θ_kj)
                else:
                    # Diagonal: includes self-admittance and contributions from all buses
                    Y_kk = self.circuit.ybus.at[bus_k, bus_k]
                    θ_kk = np.angle(Y_kk)
                    diag_term = -V_k * abs(Y_kk) * np.sin(θ_kk)
                    sum_term = sum(
                        abs(self.circuit.ybus.at[bus_k, bus_m]) * self.voltage[bus_m] *
                        np.sin(δ_k - self.delta[bus_m] - np.angle(self.circuit.ybus.at[bus_k, bus_m]))
                        for m, bus_m in enumerate(bus_order)
                    )
                    J4[k, j] = diag_term + sum_term
        J4_df = pd.DataFrame(J4, index=bus_order, columns=bus_order)
        print("\n[DEBUG] J4 (∂Q/∂V):")
        print(J4_df)
        return J4

    def construct_jacobian(self, J1, J2, J3, J4):
        """Constructs the full Jacobian matrix by stacking the submatrices."""
        top = np.hstack((J1, J2))
        bottom = np.hstack((J3, J4))
        J = np.vstack((top, bottom))

        bus_order = self.circuit.bus_order()
        labels = [f"{b}" for b in bus_order]
        full_index = labels + labels
        full_columns = bus_order + bus_order

        J_df = pd.DataFrame(J, index=full_index, columns=full_columns)
        print("\n[DEBUG] Full Jacobian Matrix:")
        print(J_df)
        print(f"[DEBUG] Full Jacobian shape = {J.shape}")
        return J_df

    def get_full_jacobian(self):
        """Computes and returns the full Jacobian matrix."""
        J1 = self.calculate_J1()
        J2 = self.calculate_J2()
        J3 = self.calculate_J3()
        J4 = self.calculate_J4()
        J_df = self.construct_jacobian(J1, J2, J3, J4)
        return J_df

    def get_trimmed_jacobian(self):
        # 1) Get the full Jacobian (as a DataFrame) and bus order.
        J_full = self.get_full_jacobian()  # DataFrame with row and column labels
        bus_order = self.circuit.bus_order()
        n = len(bus_order)

        # 2) Get the full row and column labels (each of length 2n).
        full_row_labels = list(J_full.index)
        full_col_labels = list(J_full.columns)

        # 3) Determine which rows and columns to remove based on bus type.
        rows_to_remove = set()
        cols_to_remove = set()
        for i, bus_name in enumerate(bus_order):
            bus_type = self.circuit.buses[bus_name].bus_type
            if bus_type == "Slack Bus":
                # Remove both P (row i) and Q (row i+n)
                rows_to_remove.add(i)
                rows_to_remove.add(i + n)
                # Remove both δ (col i) and V (col i+n)
                cols_to_remove.add(i)
                cols_to_remove.add(i + n)
            elif bus_type == "PV Bus":
                # Remove only the Q equation (row i+n) and the V variable (col i+n)
                rows_to_remove.add(i + n)
                cols_to_remove.add(i + n)
            # PQ Bus: keep all rows and columns

        # 4) Build lists of rows and columns to keep.
        rows_to_keep = [r for r in range(2 * n) if r not in rows_to_remove]
        cols_to_keep = [c for c in range(2 * n) if c not in cols_to_remove]

        # 5) Extract the trimmed submatrix.
        J_trimmed_array = J_full.values[np.ix_(rows_to_keep, cols_to_keep)]

        # 6) Create new labels from the original labels for the remaining indices.
        new_row_labels = [full_row_labels[r] for r in rows_to_keep]
        new_col_labels = [full_col_labels[c] for c in cols_to_keep]

        # 7) Build and return the trimmed DataFrame.
        J_trimmed_df = pd.DataFrame(J_trimmed_array, index=new_row_labels, columns=new_col_labels)
        print("\n[DEBUG] Trimmed Jacobian Matrix:")
        print(J_trimmed_df)
        print(f"[DEBUG] Trimmed Jacobian shape = {J_trimmed_df.shape}")
        return J_trimmed_df