import numpy as np


class SystemSettings:
    def __init__(self, frequency=60, base_power=100):
        """
        Initializes system-wide settings including Ybus, buses, frequency, and base power.

        Parameters:
            ybus (numpy.ndarray): The system admittance matrix.
            bus_list (list): List of Bus objects.
            frequency (float): System frequency in Hz (default: 60 Hz).
            base_power (float): System base power in MVA (default: 100 MVA).
            base_voltage (float): System base voltage in kV (default: 230 kV).
        """

        self.frequency = frequency  # Hz
        self.base_power = base_power  # MVA



    def __repr__(self):
        """Returns a formatted string representation of the SystemSettings object."""
        return (f"SystemSettings(frequency={self.frequency} Hz, base_power={self.base_power} MVA "
                f"num_buses={len(self.buses)})")




