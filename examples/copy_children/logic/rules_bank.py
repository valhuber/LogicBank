from decimal import Decimal

from logic_bank.exec_row_logic.logic_row import LogicRow
from logic_bank.extensions.rule_extensions import RuleExtension
from logic_bank.logic_bank import Rule
from examples.copy_children.db.models import Project


def declare_logic():

    def clone_project(row: Project, old_row: Project, logic_row: LogicRow):
        if row.project_ is not None and logic_row.nest_level == 0:
            """
            Useful in row event handlers to copy multiple children types to self from copy_from children.

            child-spec := < ‘child-list-name’ | < ‘child-list-name = parent-list-name’ >
            child-list-spec := [child-spec | (child-spec, child-list-spec)]

            Eg. RowEvent on Order
                which = dict(OrderDetailList = None)
                logic_row.copy_children(copy_from=row.parent, which_children=which)

            Eg, test/copy_children:
                child_list_spec = [
                    ("MileStoneList",
                        ["DeliverableList"]  # for each Milestone, get the Deliverables
                    ),
                    "StaffList"
                ]
            """

            child_list_spec = [
                ("MileStoneList",
                    ["DeliverableList"]
                ),
                "StaffList"
            ]

            logic_row.copy_children(copy_from=row.project_,
                                    which_children=child_list_spec)

    Rule.row_event(on_class=Project, calling=clone_project)
