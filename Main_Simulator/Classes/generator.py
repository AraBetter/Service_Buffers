from Classes.bus import Bus
import numpy as np
import pandas as pd

class Generator:
    def __init__(self, name: str, bus: Bus, real_power: float, per_unit: float,
                 x1=None, x2=None, x0=None,
                 system_settings=None, grounding_impedance_ohm=None, is_grounded=True,
                 connection_type="wye"):
        self.name = name
        self.bus = bus  # This should be a Bus object
        self.real_power = real_power  # Real power generation in MW
        self.per_unit = per_unit  # Voltage setpoint in p.u.
        self.Q = None  # Reactive power, to be calculated during power flow
        self.connection_type = connection_type.lower()

        # Initialize reactances (will be overwritten if conditions met)
        self.x1 = None
        self.x2 = None
        self.x0 = None

        # Grounding
        self.is_grounded = is_grounded
        self.Yn = None  # Neutral-to-ground admittance in pu

        # Set PV or Slack Bus behavior
        if self.bus.bus_type not in ["Slack Bus", "PV Bus"]:
            self.bus.bus_type = "PV Bus"
            self.bus.per_unit = self.per_unit

            if not hasattr(self.bus, 'generators'):
                self.bus.generators = []
            self.bus.generators.append(self)
        else:
            print(f"[INFO] Generator '{self.name}' is connected to Slack Bus '{self.bus.name}'. P will be calculated during power flow.")

        # Conversion of x1, x2, x0 from generator base to system base
        if system_settings and x1 is not None and x2 is not None and x0 is not None:
            s_sys = system_settings.base_power

            v_gen = self.bus.base_kv

            # Avoid division by zero by setting s_gen = s_sys for Slack Bus
            if self.bus.bus_type == "Slack Bus" or real_power == 0:
                s_gen = s_sys
            else:
                s_gen = real_power

            base_ratio = (s_sys / s_gen)

            self.x1 = x1 * base_ratio
            self.x2 = x2 * base_ratio
            self.x0 = x0 * base_ratio

            # Neutral grounding admittance (converted to per-unit on system base)
            if is_grounded and grounding_impedance_ohm:
                z_base_gen = (v_gen ** 2) / s_gen
                zn_pu = (grounding_impedance_ohm / z_base_gen) * base_ratio
                self.zn_pu = zn_pu

                self.Yn = 1 / zn_pu
            elif is_grounded:
                self.Yn = float('inf')  # solidly grounded = infinite admittance (short circuit)

    def calc_admittances(self):
        """
        Calculates and stores the positive-, negative-, and zero-sequence admittances (Y1, Y2, Y0)
        from system-base reactances x1, x2, and x0.

        Stores:
            self.Y1, self.Y2, self.Y0: Complex admittances (or None if x is not defined)
        """
        self.Y1 = 1 / (1j * self.x1) if self.x1 else None
        self.Y2 = 1 / (1j * self.x2) if self.x2 else None

        if self.x0 is not None:
            if self.is_grounded and self.Yn not in [None, float('inf')]:
                z0_total = (3 * self.zn_pu) +complex(0, self.x0)
                self.Y0 = 1 / z0_total
            elif self.is_grounded:
                self.Y0 = 1 / complex(0, self.x0)
            else:
                self.Y0 = 0
        else:
            self.Y0 = None

        return {
            'Y1': self.Y1,
            'Y2': self.Y2,
            'Y0': self.Y0
        }


    def calc_yprim_sequence(self, sequence='positive'):
        """
        Returns the sequence Yprim matrix (as 2×2 np.array for pos/neg,
        or scalar shunt value for zero-sequence if grounded and wye-connected).
        """
        self.calc_admittances()

        if sequence == 'positive':
            Y = self.Y1
            if Y is None:
                return None
            return np.array([[Y, -Y], [-Y, Y]], dtype=complex)

        elif sequence == 'negative':
            Y = self.Y2
            if Y is None:
                return None
            return np.array([[Y, -Y], [-Y, Y]], dtype=complex)

        elif sequence == 'zero':
            if self.connection_type != "wye":
                return None  # delta-connected generators don’t contribute to Y0

            if self.Y0 is None:
                return None
            return self.Y0  # already models Z0 + Zn in series

        else:
            raise ValueError(f"Invalid sequence type: '{sequence}'. Choose 'positive', 'negative', or 'zero'.")

    def __repr__(self):
        return (f"Generator(name='{self.name}', bus='{self.bus.name}', "
                f"voltage_setpoint={self.per_unit} p.u., real_power={self.real_power} MW, "
                f"x1={self.x1}, x2={self.x2}, x0={self.x0}, Yn={self.Yn})," f"connection_type='{self.connection_type}', ")
