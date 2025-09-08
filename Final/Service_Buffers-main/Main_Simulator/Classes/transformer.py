import cmath
import math
import pandas as pd
import numpy as np

class Transformer:
    """Represents a transformer in a power system network."""

    def __init__(self, name: str, bus1, bus2, power_rating: float, impedance_percent: float,
                 x_over_r_ratio: float, s_base: float,
                 primary_connection_type="wye", secondary_connection_type="wye",
                 grounding_impedance_ohm_bus1=0.0, grounding_impedance_ohm_bus2=0.0,
                 is_grounded_bus1=True, is_grounded_bus2=True):
        """
        Initializes a Transformer object.

        Parameters:
        - name (str): The name of the transformer.
        - bus1 (Bus): The first bus connected to the transformer.
        - bus2 (Bus): The second bus connected to the transformer.
        - power_rating (float): Transformer power rating in MVA.
        - impedance_percent (float): Transformer impedance as a percentage.
        - x_over_r_ratio (float): Transformer X/R ratio.
        """
        self.name = name
        self.bus1 = bus1
        self.bus2 = bus2
        self.power_rating = power_rating  # In MVA
        self.impedance_percent = impedance_percent
        self.x_over_r_ratio = x_over_r_ratio

        # Assign base values
        self.s_base = s_base  # System base power
        self.v_base = bus1.base_kv  # Use bus voltage as base voltage

        # Compute base impedances
        self.z_base_xfmr = self.calc_base_impedance_xfmr()
        self.z_base_sys = self.calc_base_impedance_sys()

        # Compute per-unit impedance on transformer base
        self.z_pu_xfmr = self.calc_pu_impedance_xfmr()

        # Compute impedance in ohms using Euler's formula
        self.zt = self.calc_impedance()

        # Compute per-unit impedance on system base
        self.z_pu_sys = self.calc_pu_impedance_sys()

        # Compute admittances
        self.yt = self.calc_admittance()
        self.y_pu_sys = self.calc_pu_admittance_sys()

        # Compute resistance and reactance
        self.rt = self.zt.real
        self.xt = self.zt.imag
        self.r_pu_sys = self.z_pu_sys.real
        self.x_pu_sys = self.z_pu_sys.imag

        # Compute Y-primitive matrices
        self.yprim = self.calc_yprim()
        self.yprim_pu = self.calc_yprim_pu()

        # Used to compute the yprim sequences
        self.primary_connection_type = primary_connection_type.lower()
        self.secondary_connection_type = secondary_connection_type.lower()
        self.Zn1_ohm = grounding_impedance_ohm_bus1
        self.Zn2_ohm = grounding_impedance_ohm_bus2
        self.is_grounded_bus1 = is_grounded_bus1
        self.is_grounded_bus2 = is_grounded_bus2

        z_base1 = (self.bus1.base_kv ** 2) / s_base
        z_base2 = (self.bus2.base_kv ** 2) / s_base
        self.Yn1 = 1 / (self.Zn1_ohm / z_base1) if self.Zn1_ohm else 0
        self.Yn2 = 1 / (self.Zn2_ohm / z_base2) if self.Zn2_ohm else 0

        # V_base_ratio: ratio of base voltages (LL/LL), used for sequence voltage adjustments
        self.Vbase1 = self.bus1.base_kv  # Primary side base voltage (in kV)
        self.Vbase2 = self.bus2.base_kv  # Secondary side base voltage (in kV)

        # Voltage base scaling factor (accounts for delta-wye transformation)
        if self.Vbase1 and self.Vbase1 != 0:
            self.V_base_ratio = self.Vbase2 / self.Vbase1
        else:
            self.V_base_ratio = 1.0

        # Sequence phase shift in degrees for US convention (used in voltage adjustment)
        if self.primary_connection_type == 'wye' and self.secondary_connection_type == 'delta':
            self.phase_shift_deg = +30
        elif self.primary_connection_type == 'delta' and self.secondary_connection_type == 'wye':
            self.phase_shift_deg = -30
        else:
            self.phase_shift_deg = 0  # No shift for Y–Y or D–D

    def calc_base_impedance_xfmr(self):
        """Calculates the base impedance for the transformer rating."""
        return (self.v_base ** 2) / self.power_rating

    def calc_base_impedance_sys(self):
        """Calculates the base impedance for the system."""
        return (self.v_base ** 2) / self.s_base

    def calc_pu_impedance_xfmr(self):
        """Calculates the transformer's per-unit impedance based on its rating."""
        return self.impedance_percent / 100

    def calc_impedance(self):
        """Calculates the transformer's impedance in ohms using Euler's formula."""
        theta = math.atan(self.x_over_r_ratio)  # Compute angle from X/R ratio
        z_pu_complex = self.z_pu_xfmr * cmath.exp(complex(0, theta))  # Euler’s formula
        return z_pu_complex * self.z_base_xfmr  # Convert to ohms

    def calc_pu_impedance_sys(self):
        """Calculates the transformer's per-unit impedance on the system base."""
        return self.zt / self.z_base_sys  # Uses the complex value of zt

    def calc_admittance(self):
        """Calculates the transformer's admittance in siemens."""
        return 1 / self.zt if abs(self.zt) > 1e-9 else complex(0, 0)

    def calc_pu_admittance_sys(self):
        """Calculates the transformer's per-unit admittance on the system base."""
        return 1 / self.z_pu_sys if abs(self.z_pu_sys) > 1e-9 else complex(0, 0)

    def calc_yprim(self):
        """Calculates the Y-primitive matrix in Siemens and returns a numerical Pandas DataFrame."""
        yprim_matrix = pd.DataFrame(
            [[self.yt, -self.yt],
             [-self.yt, self.yt]],
            index=[self.bus1.name, self.bus2.name],
            columns=[self.bus1.name, self.bus2.name]
        )
        return yprim_matrix

    def calc_yprim_pu(self):
        """Calculates the Y-primitive matrix in per-unit and returns a numerical Pandas DataFrame."""
        yprim_pu_matrix = pd.DataFrame(
            [[self.y_pu_sys, -self.y_pu_sys],
             [-self.y_pu_sys, self.y_pu_sys]],
            index=[self.bus1.name, self.bus2.name],
            columns=[self.bus1.name, self.bus2.name]
        )
        return yprim_pu_matrix


    def calc_yprim_sequence(self, sequence='positive'):
        """
        Returns the 2×2 Yprim matrix for the specified sequence component.
        - Positive and Negative: assumes standard transformer topology, no phase shift applied to Yprim.
        - Zero-sequence: includes only if winding is WYE-connected, and depends on grounding impedance.
        """
        Y = self.y_pu_sys
        conn_primary = self.primary_connection_type
        conn_secondary = self.secondary_connection_type

        if sequence in ['positive', 'negative']:
            # For pos/neg sequence, Yprim is symmetric with no internal phase shift
            return pd.DataFrame([
                [Y, -Y],
                [-Y, Y]
            ], index=[self.bus1.name, self.bus2.name],
                columns=[self.bus1.name, self.bus2.name])

        elif sequence == 'zero':
            Z_series = 1 / Y if Y != 0 else complex('inf')

            if conn_primary == "wye" and self.is_grounded_bus1:
                Zn1 = (1 / self.Yn1) if self.Yn1 else complex('inf')
                Y11 = 1 / (Z_series + Zn1)
            else:
                Y11 = 0

            if conn_secondary == "wye" and self.is_grounded_bus2:
                Zn2 = (1 / self.Yn2) if self.Yn2 else complex('inf')
                Y22 = 1 / (Z_series + Zn2)
            else:
                Y22 = 0

            if (conn_primary == "wye" and conn_secondary == "wye"
                    and self.is_grounded_bus1 and self.is_grounded_bus2):
                Ymutual = -1 / Z_series
            else:
                Ymutual = 0

            return pd.DataFrame([
                [Y11, Ymutual],
                [Ymutual, Y22]
            ], index=[self.bus1.name, self.bus2.name],
                columns=[self.bus1.name, self.bus2.name])


        else:
            raise ValueError(f"Invalid sequence '{sequence}'. Must be 'positive', 'negative', or 'zero'.")

    def adjust_sequence_voltage(self, V_seq, direction="primary_to_secondary"):
        """
        Adjusts sequence voltage across the transformer winding for:
        - Voltage base scaling
        - Sequence phase shift (±30° for Y-Δ or Δ-Y)

        Parameters:
            V_seq (complex): sequence voltage phasor
            direction (str): "primary_to_secondary" or "secondary_to_primary"

        Returns:
            complex: adjusted voltage
        """
        # assert self.V_base_ratio > 0, "Voltage base ratio must be positive"
        # ratio = self.V_base_ratio if direction == "primary_to_secondary" else 1 / self.V_base_ratio
        # shift = self.phase_shift_deg if direction == "primary_to_secondary" else -self.phase_shift_deg
        # return ratio * V_seq * np.exp(1j * np.radians(shift))
        shift = self.phase_shift_deg if direction == "primary_to_secondary" else -self.phase_shift_deg
        return V_seq * np.exp(1j * np.radians(shift))

    def __repr__(self):
        """Returns a string representation of the Transformer object with magnitudes only."""
        return (
            f"--- Transformer Details ---\n"
            f"Name: {self.name}\n"
            f"Power Rating: {self.power_rating} MVA\n"
            f"X/R Ratio: {self.x_over_r_ratio}\n\n"

            # f"--- Base Values ---\n"
            # f"S_base (System Power Base): {self.s_base} MVA\n"
            # f"V_base (Bus Voltage Base): {self.v_base} kV\n"
            # f"Z_base_xfmr: {self.z_base_xfmr:.4f} Ω\n"
            # f"Z_base_sys: {self.z_base_sys:.4f} Ω\n\n"
            #
            #  f"--- Impedance & Admittance Values ---\n"
            # f"Z_pu_xfmr (Per-Unit Transformer Base): {abs(self.z_pu_xfmr):.4f} pu\n"
            # f"Z_t (Impedance in Ohms): {abs(self.zt):.4f} Ω\n"
            # f"Z_pu_sys (Per-Unit System Base): {abs(self.z_pu_sys):.4f} pu\n"
            # f"Y_t (Admittance in Siemens): {abs(self.yt):.4f} S\n"
            # f"Y_pu_sys (Per-Unit Admittance): {abs(self.y_pu_sys):.4f} pu\n\n"
            #
            # f"--- Resistance & Reactance Values ---\n"
            # f"R_t (Resistance in Ohms): {self.rt:.4f} Ω\n"
            # f"X_t (Reactance in Ohms): {self.xt:.4f} Ω\n"
            # f"R_pu_sys (Per-Unit System Resistance): {abs(self.r_pu_sys):.4f} pu\n"
            # f"X_pu_sys (Per-Unit System Reactance): {abs(self.x_pu_sys):.4f} pu\n\n"
            #
            # f"--- Y-Primitive Matrix (Yprim) [Siemens] ---\n{self.yprim}\n\n"
            # f"--- Y-Primitive Matrix (Yprim_pu) [Per Unit] ---\n{self.yprim_pu}\n"
            #
            # f"--- Sequence Network Info ---\n"
            # f"Connection Type: {self.connection_type}\n"
            # f"Bus1 Grounding Impedance: {self.Zn1_ohm:.4f} Ω, Bus2 Grounding Impedance: {self.Zn2_ohm:.4f} Ω\n"
            # f"Bus1 Neutral Admittance (Yn1): {self.Yn1:.6f} pu\n"
            # f"Bus2 Neutral Admittance (Yn2): {self.Yn2:.6f} pu\n\n"
        )



