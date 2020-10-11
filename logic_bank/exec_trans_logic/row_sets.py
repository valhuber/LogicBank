from __future__ import annotations
from typing import List, TypeVar, Dict

from sqlalchemy.engine import base
from sqlalchemy.ext.declarative import declarative_base

from logic_bank.exec_row_logic.logic_row import LogicRow


class RowSets():
    """
    Sets of rows used in transaction
        * processed_rows: Dict of all the logic_rows processed in this transaction, by row instance (no dups)
            Used to drive commit events/constraints
        * submitted_rows: set of rows submitted by client
            Used to avoid adjusting altered rows

    Presumes that sqlalchemy returns same instance for multiple queries.
    """

    def __init__(self):
        self.processed_rows = {}  # type: Dict[base, 'LogicRow']
        self.submitted_row = set()

    def add_processed(self, logic_row: 'LogicRow'):
        """
        Denote row processed, for later commit events/constraints
        """
        if logic_row.row not in self.processed_rows:
            self.processed_rows[logic_row.row] = logic_row

    def add_submitted(self, row: base):
        self.submitted_row.add(row)

    def is_submitted(self, row: base) -> bool:
        result = row in self.submitted_row
        return result

    def remove_submitted(self, logic_row: LogicRow):
        if logic_row.row in self.submitted_row:
            self.submitted_row.remove(logic_row.row)

