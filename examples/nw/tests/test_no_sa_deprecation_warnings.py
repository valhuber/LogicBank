import sys, unittest, warnings
import logic_bank_utils.util as logic_bank_utils
from datetime import datetime

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

if  __name__ == '__main__':
    print("\nStarted from cmd line - launch unittest and exit\n")
    sys.argv = [sys.argv[0]]
    unittest.main(module="examples.nw.tests.test_no_sa_deprecation_warnings")
    exit(0)
else:  # failing to find rules
    print("Started from unittest: " + __name__)
    from examples.nw import tests

    tests.copy_gold_over_db()

    import examples.nw.db.models as models

    from examples.nw.logic import session, engine  # opens db, activates rules <--
    # activate rules:   LogicBank.activate(session=session, activator=declare_logic)

    print("\n" + sys_env_info + "\n\n")


class Test(unittest.TestCase):

    """
        Regression test - LogicBank must not call SQLAlchemy APIs deprecated since 1.4/2.0.
        Query.get() (every parent read) and ext.declarative.declarative_base() (every LogicRow) each
        warned on every transaction, flooding client logs.
    """

    def setUp(self):  # banner
        self.started_at = str(datetime.now())
        tests.setUp(file=__file__)

    def tearDown(self):
        tests.tearDown(file=__file__, started_at=self.started_at, engine=engine, session=session)

    def test_run(self):
        new_employee = models.Employee(LastName='Warnings', Salary=100000, WorksFor=1, OnLoan=2, IsCommissioned=0)  # reads 2 parents

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            session.add(new_employee)
            session.commit()

        deprecated = [f"{w.filename.split('LogicBank')[-1]}:{w.lineno} {str(w.message)[:90]}"
                      for w in caught
                      if "logic_bank" in w.filename.replace("\\", "/")
                      and ("Query.get()" in str(w.message) or "declarative_base()" in str(w.message))]
        assert not deprecated, f"LogicBank used deprecated SQLAlchemy APIs: {deprecated}"

        print("\n...no_sa_deprecation_warnings, ran to completion\n\n")
