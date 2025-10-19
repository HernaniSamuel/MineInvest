# Copyright 2025 Hernani Samuel Diniz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


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
