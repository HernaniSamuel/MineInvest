"""Custom exceptions for the investment simulator."""


class SimulationAlreadyExistsError(Exception):
    """Raised when trying to create a simulation with a duplicate name"""
    pass


class InsufficientFundsError(Exception):
    """Raised when attempting to withdraw more than available balance."""
    pass


class InvalidAmountError(Exception):
    """Raised when amount has invalid format or value."""
    pass


class SimulationNotFoundError(Exception):
    """Raised when simulation ID does not exist."""
    pass


class InsufficientPositionError(Exception):
    """Raised when trying to sell more than owned."""
    pass


class PriceUnavailableError(Exception):
    """Raised when price data not available for date."""
    pass


class AssetNotFoundError(Exception):
    """Raised when asset ticker invalid."""
    pass
