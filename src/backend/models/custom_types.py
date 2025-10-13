from sqlalchemy.types import TypeDecorator, String
from decimal import Decimal


class PreciseDecimal(TypeDecorator):
    """
    Custom type for SQLite that stores Decimals as strings
    but automatically converts when reading/writing.
    """
    impl = String  # Internamente usa String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """When SAVE to the bank: Decimal → String"""
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        """When READ from bank: String → Decimal"""
        if value is None:
            return None
        return Decimal(value)