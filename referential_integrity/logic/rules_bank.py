from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.allocate import Allocate
from logic_bank.logic_bank import Rule
from referential_integrity.db.models import Parent, Child


def declare_logic():

    Rule.parent_check(validate=Child, error_msg="no parent", enable=True)
