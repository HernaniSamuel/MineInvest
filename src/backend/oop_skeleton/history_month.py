from decimal import Decimal
from datetime import date
from typing import List, Dict, Optional

class HistoryMonth:
    """
    Represents a monthly record of all operations performed in a simulation.

    Attributes:
        month_date (date): The month and year this history record refers to.
        operations (List[Dict[str, Optional[Decimal]]]): List of operations performed in this month.
            Each operation is a dictionary with keys:
                - 'type' (str): Type of operation ('contribution', 'withdrawal', 'buy', 'sell', 'dividend').
                - 'value' (Decimal): Amount of the operation.
                - 'ticker' (Optional[str]): Asset ticker for buy, sell, or dividend operations; None otherwise.
        total (Decimal): The net result of all operations added to the previous month's ending balance.
    """

    def __init__(self, month_date: date) -> None:
        self.month_date: date = month_date
        self.operations: List[Dict[str, Optional[Decimal]]] = []
        self.total: Decimal = Decimal(0)

    def reset_month(self) -> None:
        """
        Resets the month by removing all operations except dividends.

        This method is useful to undo changes made during the current month
        while preserving recurring dividend entries.

        Returns:
            None
        """
        self.operations = [op for op in self.operations if op.get('type') == 'dividend']
