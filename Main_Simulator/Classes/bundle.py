import math
from Classes.conductor import Conductor

class Bundle:

    def __init__(self, name: str, num_conductors: int, spacing: float, conductor: Conductor):
        """
        Initializes a Bundle object.

        Parameters:
        - name (str): Name of the bundle.
        - num_conductors (int): Number of subconductors in the bundle (1-4).
        - spacing (float): Spacing between adjacent subconductors (ft).
        - conductor (Conductor): The conductor object containing GMR and radius.
        """
        if num_conductors not in [1, 2, 3, 4]:
            raise ValueError("Number of conductors must be 1, 2, 3, or 4.")

        self.name = name
        self.num_conductors = num_conductors
        self.spacing = spacing
        self.conductor = conductor  # Conductor instance providing GMR & radius

        # Compute DSL and DSC
        self.DSL = self.calc_DSL()
        self.DSC = self.calc_DSC()

    def calc_DSL(self):
        """Calculates the Geometric Mean Radius Equivalent (DSL) based on the number of conductors."""
        if self.num_conductors == 1:
            return self.conductor.GMR  # DSL = GMRc for single conductor
        elif self.num_conductors == 2:
            return math.sqrt(self.conductor.GMR * self.spacing)  # DSL = sqrt(GMRc * d)
        elif self.num_conductors == 3:
            return (self.conductor.GMR * (self.spacing ** 2)) ** (1/3)  # DSL = ³√(GMRc * d²)
        elif self.num_conductors == 4:
            return 1.091 * (self.conductor.GMR * (self.spacing ** 3)) ** (1/4)  # DSL = 1.091 * ⁴√(GMRc * d^3)

    def calc_DSC(self):
        """Calculates the Equivalent Radius (DSC) based on the number of conductors."""
        if self.num_conductors == 1:
            return self.conductor.radius  # DSC = rc for single conductor
        elif self.num_conductors == 2:
            return math.sqrt(self.conductor.radius * self.spacing)  # DSC = sqrt(rc * d)
        elif self.num_conductors == 3:
            return (self.conductor.radius * (self.spacing ** 2)) ** (1/3)  # DSC = ³√(rc * d²)
        elif self.num_conductors == 4:
            return 1.091 * (self.conductor.radius * (self.spacing ** 3)) ** (1/4)  # DSC = 1.091 * ⁴√(rc * d^3)

    def __repr__(self):
        """Returns a detailed string representation of the Bundle object."""
        return (f"Bundle(name='{self.name}', num_conductors={self.num_conductors}, spacing={self.spacing} ft, "
                f"DSL={self.DSL:.4f} ft, DSC={self.DSC:.4f} ft, conductor={self.conductor.name})")



