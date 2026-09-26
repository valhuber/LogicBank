import sys, unittest
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.partial_composite_fk_unparent.tests.test_partial_composite_fk_unparent")
    exit(0)
else:
    print("Started from unittest: " + __name__)
    import sqlalchemy
    from sqlalchemy.orm import sessionmaker
    from logic_bank.logic_bank import Rule, LogicBank
    from logic_bank.util import ConstraintException
    from examples.partial_composite_fk_unparent.db.models import MenuOption, Base

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):
    """
    Regression test for GitHub issue #34
    (https://github.com/valhuber/LogicBank/issues/34): Aggregate._fk_is_null
    (rule_type/aggregate.py) required EVERY column of a composite FK to be
    null before treating a child as parentless. With a composite key, only the
    column that actually points at the parent gets cleared - the others (here,
    `app`) are the child's own data and stay set. The partially-null key was
    then misread as "FK references a parent that can't be found", and
    adjust_from_updated_reparented_child raised ConstraintException on the
    UPDATE that clears the FK - even though the identical partially-null key
    is accepted on INSERT (_is_foreign_key_null / _get_parent_logic_row both
    already use "any column null", not "all").

    Fixed by flipping _fk_is_null to the same any-null test. See
    system/LogicBank-Internal-Dev/partial-composite-fk-unparent-issue-34.md.
    """

    def setUp(self):
        self.started_at = str(datetime.now())
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _activate(self):
        def declare_logic():
            Rule.count(derive=MenuOption.sub_count, as_count_of=MenuOption,
                       child_role_name='ChildList')

        session = sessionmaker(bind=self.engine)()
        LogicBank.activate(session=session, activator=declare_logic)
        return session

    def test_insert_with_partially_null_composite_fk_is_accepted(self):
        session = self._activate()

        session.add(MenuOption(app='A', id='P'))
        session.commit()

        # a top-level option: app is set, parent_id is null - already worked
        # before the fix (INSERT uses the any-null test), kept here as baseline
        session.add(MenuOption(app='A', id='R'))
        session.commit()  # previously and still: accepted

        print("\n...test_insert_with_partially_null_composite_fk_is_accepted ran to completion\n\n")

    def test_clearing_composite_fk_does_not_raise(self):
        """
        The actual regression: clearing parent_id on an existing child (it
        becomes a top-level option) previously raised ConstraintException
        instead of adjusting the parent's sub_count down to 0.
        """
        session = self._activate()

        parent = MenuOption(app='A', id='P')
        session.add(parent)
        session.commit()

        child = MenuOption(app='A', id='C', parent_id='P')
        session.add(child)
        session.commit()
        session.refresh(parent)
        self.assertEqual(parent.sub_count, 1, "Expected sub_count = 1 after insert")

        session.refresh(child)
        child.parent_id = None  # the option becomes a top-level one
        try:
            session.commit()  # previously: ConstraintException
        except ConstraintException as exception:
            self.fail(f"Unexpected ConstraintException clearing a composite FK: {exception}")

        session.refresh(parent)
        self.assertEqual(parent.sub_count, 0,
                         "Expected sub_count adjusted to 0 after clearing the FK")

        print("\n...test_clearing_composite_fk_does_not_raise ran to completion\n\n")


if __name__ == '__main__':
    unittest.main()
