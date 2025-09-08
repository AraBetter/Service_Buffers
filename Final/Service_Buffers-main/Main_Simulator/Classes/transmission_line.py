import math
import cmath
from bus import Bus
from bundle import Bundle
from geometry import Geometry
import pandas as pd

class TransmissionLine:
    """Represents a high-voltage transmission line between two buses."""

    def __init__(self, name: str, bus1, bus2, bundle, geometry, length: float, s_base: float,
                 frequency:float, connection_type="transposed", zero_seq_model="enabled"):
        """
        Initializes a TransmissionLine object.

        Parameters:
        - name (str): Name of the transmission line.
        - bus1 (Bus): First connected bus.
        - bus2 (Bus): Second connected bus.
        - bundle (Bundle): The Bundle object (providing DSL, DSC, resistance).
        - geometry (Geometry): The Geometry object (providing Deq).
        - length (float): Length of the transmission line in miles.
        - s_base (float): System base power in MVA.
        - frequency (float, optional): Operating frequency in Hz (default = 60 Hz).
        """

        # Validation that bus voltages have the same value
        if bus1.base_kv != bus2.base_kv:
            raise ValueError("Buses must have the same voltage rating.")

        self.name = name
        self.bus1 = bus1
        self.bus2 = bus2
        self.bundle = bundle
        self.geometry = geometry
        self.length = length
        self.frequency = frequency

        # Assign base values
        self.s_base = s_base
        self.v_base = bus1.base_kv

        # Calculate base values
        self.z_base_sys, self.y_base_sys = self.calc_base_values()

        # Calculate electrical parameters
        self.r_series = self.calc_resistance()
        self.x_series = self.calc_reactance()
        self.b_shunt = self.calc_bshunt()  # Shunt susceptance calculation
        self.z_series = complex(self.r_series, self.x_series)
        self.z_pu_sys = self.z_series / self.z_base_sys
        self.y_series = self.calc_yseries()  # Updated calculation for y_series
        self.y_pu_sys = 1 / self.z_pu_sys if self.z_pu_sys != 0 else complex(0, 0)
        self.y1_pu = self.y_pu_sys
        self.y2_pu = self.y_pu_sys
        self.b_shunt_pu = self.b_shunt / self.y_base_sys if self.y_base_sys != 0 else complex(0, 0)

        # Compute Y-primitive matrices
        self.yprim = self.calc_yprim()
        self.yprim_pu = self.calc_yprim_pu()

        # Assign all sequence impedances
        if connection_type == "transposed":
            self.z0_pu = self.z_pu_sys  # Balanced case
        elif connection_type == "untransposed":
            r0 = self.r_series
            x0 = self.x_series
            self.z0 = 2.5 * complex(r0, x0)
            self.z0_pu = self.z0 / self.z_base_sys

        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

        self.y0_pu = 1 / self.z0_pu if zero_seq_model == "enabled" else 0
        self.y1_pu = self.y_pu_sys
        self.y2_pu = self.y_pu_sys

    def calc_base_values(self):
        """Calculates the base impedance and base admittance."""
        v_base = self.v_base * 1e3  # Convert kV to V
        z_base = (v_base ** 2) / (self.s_base * 1e6)  # Base impedance in ohms
        y_base = 1 / z_base if z_base != 0 else 0  # Base admittance in Siemens
        return z_base, y_base

    def calc_resistance(self):
        """Calculates the series resistance (Ω)."""
        return (self.bundle.conductor.resistance / self.bundle.num_conductors) * self.length

    def calc_reactance(self):
        """Calculates the series reactance (Ω)."""
        return (2 * math.pi * self.frequency * 2e-7 *
                math.log(self.geometry.Deq / self.bundle.DSL) * 1609.34 * self.length)

    def calc_bshunt(self):
        """Calculates the shunt susceptance (B_shunt) in Siemens."""
        return ((2 * math.pi * self.frequency * (2 * math.pi * 8.854e-12)) /
                math.log(self.geometry.Deq / self.bundle.DSC) * 1609.34 * self.length)

    def calc_yseries(self):
        """Calculates the series admittance (Y_series)."""
        return 1 / self.z_series if self.z_series != 0 else complex(0, 0)

    def calc_yprim(self):
        """Calculates the Y-primitive matrix in Siemens and returns a numerical Pandas DataFrame."""
        yprim_matrix = pd.DataFrame(
            [[self.y_series + (1j * self.b_shunt / 2), -self.y_series],
             [-self.y_series, self.y_series + (1j * self.b_shunt / 2)]],
            index=[self.bus1.name, self.bus2.name],
            columns=[self.bus1.name, self.bus2.name]
        )
        return yprim_matrix

    def calc_yprim_pu(self):
        """Calculates the Y-primitive matrix in per-unit and returns a numerical Pandas DataFrame."""
        yprim_pu_matrix = pd.DataFrame(
            [[self.y_pu_sys + (1j * self.b_shunt_pu / 2), -self.y_pu_sys],
             [-self.y_pu_sys, self.y_pu_sys + (1j * self.b_shunt_pu / 2)]],
            index=[self.bus1.name, self.bus2.name],
            columns=[self.bus1.name, self.bus2.name]
        )
        return yprim_pu_matrix



    def calc_yprim_sequence(self, sequence='positive'):
        """
        Returns the sequence-dependent Y-primitive matrix (per unit).
        Supports: 'positive', 'negative', 'zero'
        """
        if sequence == 'positive':
            Y = self.y1_pu
        elif sequence == 'negative':
            Y = self.y2_pu
        elif sequence == 'zero':
            Y = self.y0_pu
            if Y == 0:
                return pd.DataFrame(
                    [[0.0, 0.0],
                     [0.0, 0.0]],
                    index=[self.bus1.name, self.bus2.name],
                    columns=[self.bus1.name, self.bus2.name]
                )
        else:
            raise ValueError(f"Invalid sequence '{sequence}'. Must be 'positive', 'negative', or 'zero'.")

        # Return Yprim for all valid sequences
        return pd.DataFrame([
            [Y, -Y],
            [-Y, Y]
        ], index=[self.bus1.name, self.bus2.name],
            columns=[self.bus1.name, self.bus2.name])

    def __repr__(self):
        """Returns a detailed string representation of the TransmissionLine object."""
        return (f"""
                    --- Transmission Line Details ---
                    Name: {self.name}
                    Buses: {self.bus1.name} - {self.bus2.name}
                    Bundle: {self.bundle}
                    Geometry: {self.geometry}
                    Length: {self.length} mi
                    Frequency: {self.frequency} Hz
                    
                     """)

                    # --- Base Values ---
                    # s_base: {self.s_base} MVA
                    # v_base: {self.v_base} kV
                    # z_base_sys: {self.z_base_sys:.4f} Ω
                    #
                    # --- Impedance and Admittance Values ---
                    # z_pu_sys: {abs(self.z_pu_sys):.4f} pu
                    # y_pu_sys: {abs(self.y_pu_sys):.4f} pu
                    # b_shunt_pu: {abs(self.b_shunt_pu):.4f} pu
                    #
                    # f"--- Y-Primitive Matrix (Yprim_pu) [Per Unit] ---\n{self.yprim_pu}\n"
                    #
                    # --- Sequence Impedance & Admittance Info ---
                    # Connection Type: {self.connection_type.upper()}
                    # f"Connection Type: {self.connection_type.upper()}"
                    # Y1 (Positive Seq): {abs(self.y1_pu):.4f} pu
                    # Y2 (Negative Seq): {abs(self.y2_pu):.4f} pu
                    # Y0 (Zero Seq):     {abs(self.y0_pu):.4f} pu







                   





