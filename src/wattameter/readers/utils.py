import numpy as np


def get_conversion_factor(unit: str) -> float:
    """Get the conversion factor for a given unit."""
    conversion_factors = {
        "uJ": 1e-6,  # microjoules to joules
        "mJ": 1e-3,  # millijoules to joules
        "J": 1.0,  # joules
        "kWh": 3600000.0,  # kilowatt-hours to joules
    }
    return conversion_factors.get(unit, 1.0)
