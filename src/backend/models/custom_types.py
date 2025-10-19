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