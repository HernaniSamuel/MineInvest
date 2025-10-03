"""Custom exceptions for the investment simulator."""


class SimulationAlreadyExistsError(Exception):
    """Raised when trying to create a simulation with a duplicate name"""
    pass