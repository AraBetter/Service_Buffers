import numpy as np
from PowerFlowSolver import PowerFlowSolver
from Jacobians import Jacobian

class NewtonRaphson:
    def __init__(self, power_flow_solver):
        self.pfs = power_flow_solver

    def solve(self, tol = 0.001, max_iter = 50):
        iteration = 0
        converged = False

        while iteration < max_iter:
            # --- Recompute mismatch ---
            y = self.pfs.initialize_y()
            Px = self.pfs.calc_Px()
            Qx = self.pfs.calc_Qx()
            yx = self.pfs.calculate_yx(Px, Qx)
            self.pfs.del_y = self.pfs.calculate_power_mismatch(y, yx)
            del_y_trimmed = self.pfs.calculate_trimmed_power_mismatch(self.pfs.del_y)

            # --- Check convergence ---
            if np.max(np.abs(del_y_trimmed)) < tol:
                print(f"Newton-Raphson converged in {iteration} iterations.")
                converged = True
                break

            # --- Recompute the trimmed Jacobian ---
            jac = Jacobian(self.pfs.Circuit, self.pfs.delta, self.pfs.voltage)
            self.pfs.J_trimmed = jac.get_trimmed_jacobian()
            J_trimmed = self.pfs.J_trimmed.to_numpy()

            # --- Solve the linear system for the state corrections ---
            delta_x = np.linalg.solve(J_trimmed, del_y_trimmed)

            # --- Update state variables ---
            bus_order = self.pfs.Circuit.bus_order()
            non_slack = [bus for bus in bus_order if self.pfs.Circuit.buses[bus].bus_type != "Slack Bus"]
            num_delta = len(non_slack)
            delta_angles = delta_x[:num_delta]
            delta_voltages = delta_x[num_delta:]

            angle_index = 0
            voltage_index = 0
            for bus in bus_order:
                if self.pfs.Circuit.buses[bus].bus_type != "Slack Bus":
                    self.pfs.delta[bus] += delta_angles[angle_index]
                    angle_index += 1
                if self.pfs.Circuit.buses[bus].bus_type == "PQ Bus":
                    self.pfs.voltage[bus] += delta_voltages[voltage_index]
                    voltage_index += 1

            print(f"Iteration {iteration}: max trimmed mismatch = {np.max(np.abs(del_y_trimmed)):.6f}")
            iteration += 1

        if not converged:
            print("Newton-Raphson did not converge within the maximum number of iterations.")
        return converged
