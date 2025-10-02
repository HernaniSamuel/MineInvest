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


from typing import List
from datetime import date
from simulation import Simulation


class SavedSimulations:
    """
    Manages all saved simulations in the system.

    This class acts as a centralized repository for Simulation instances,
    providing methods to create, delete, and potentially list all simulations.
    It separates simulation management from simulation state logic,
    allowing each Simulation to handle its own operations independently.

    Attributes:
        simulations_list (List[Simulation]): The list of all saved simulations.
    """

    def __init__(self) -> None:
        """Initializes the SavedSimulations manager with an empty list of simulations."""

        self.simulations_list: List[Simulation] = []

    def create_simulation(self, name: str, start_date: date, base_currency: str) -> Simulation:
        """
        Creates a new Simulation instance and adds it to the saved simulations list.

        Args:
            name (str): The name of the simulation.
            start_date (date): The start date of the simulation.
            base_currency (str): The base currency for the simulation.

        Returns:
            Simulation: The newly created Simulation object.
        """
        pass

    def delete_simulation(self, simulation_id: int) -> None:
        """
        Deletes a Simulation from the saved simulations list.

        Args:
            simulation_id (int): The id of the simulation to remove it from list and database.

        Raises:
            ValueError: If the simulation id is not found in the database.

        Returns:
            None
        """
        pass
