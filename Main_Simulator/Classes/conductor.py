class Conductor:
    def __init__(self, name:str, diam:float, GMR:float, resistance:float, ampacity:float):
        self.name = name
        self.diam = diam # Normally given in inches
        self.GMR = GMR # Geometric Mean Radius, feet
        self.resistance = resistance #ohms/mile
        self.ampacity = ampacity
        self.radius = self.calc_radius()  # Compute the radius in feet

    def calc_radius(self):
        """Calculates the radius of the conductor in feet using the given formula."""
        return self.diam / 24  # Formula: radius (feet) = diameter (inches) / 24

    def __repr__(self):
        """Returns a string representation of the Conductor object."""
        return (f"Conductor(name='{self.name}', diam={self.diam} in, GMR={self.GMR} ft, "
                f"resistance={self.resistance} Ω/mi, ampacity={self.ampacity} A)")

