from decimal import Decimal
import logging, sys, os
from shutil import copyfile

import sqlalchemy

from logic_bank_utils import util as logic_bank_utils

(did_fix_path, sys_env_info) = \
    logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)
print("\n" + did_fix_path + "\n\n" + sys_env_info + "\n\n")

from logic_bank.logic_bank import LogicBank
from logic_bank.util import row_prt, prt
from logic_bank.exec_row_logic.logic_row import LogicRow

import examples.copy_children.db.models as models

def copy_db_from_gold():
    """ copy db/database-gold.db over db/database.db"""
    print("\n" + prt("restoring database-gold\n"))

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - create database.db from database-gold.db in " + basedir + "/payment_allocation/db/\n" +
          "            - from -- " + prt("") +
          "\n********************************")

    db_loc = os.path.join(basedir, "db/database.db")
    db_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=db_source, dst=db_loc)

def setup_logging():
    logic_logger = logging.getLogger('logic_logger')  # for debugging user logic
    logic_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    logic_logger.addHandler(handler)

    do_engine_logging = False
    engine_logger = logging.getLogger('engine_logger')  # for internals
    if do_engine_logging:
        engine_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
        handler.setFormatter(formatter)
        engine_logger.addHandler(handler)

setup_logging()
copy_db_from_gold()

basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(basedir)

db_loc = os.path.join(basedir, "db/database.db")

conn_string = "sqlite:///" + db_loc
engine = sqlalchemy.create_engine(conn_string, echo=False)  # sqlalchemy sqls...

session_maker = sqlalchemy.orm.sessionmaker()
session_maker.configure(bind=engine)
session = session_maker()

from examples.copy_children.logic.rules_bank import declare_logic
LogicBank.activate(session=session, activator=declare_logic)


"""
    Test 1 - clone Project 1
"""

new_project = models.Project(project_id=1, name="Clone")  # project_id (fk, not id) triggers clone

session.add(new_project)
session.commit()

print("\nadd_project, update completed\n\n")

assert len(new_project.StaffList)==3, f'Expected 3 Staff, got {len(new_project.StaffList)}'
assert len(new_project.MileStoneList)==4, f'Expected 4 MileStones, got {len(new_project.MileStoneList)}'

assert new_project.staff_count == 3, f'Expected derived staff_count 3, got {new_project.staff_count == 3}'

for each_milestone in new_project.MileStoneList:
    assert len(each_milestone.DeliverableList) > 0, f'Expected Deliverables, got {len(each_milestone.DeliverableList)}'

print("\nadd_project, ran to completion\n\n")
