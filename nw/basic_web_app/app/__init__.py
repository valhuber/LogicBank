import logging
import os
import sys

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA

use_rules = True

if use_rules:
    cwd = os.getcwd()  # eg, /Users/val/python/pycharm/logic-bank/basic_web_app
    required_path_python_rules = cwd  # seeking /Users/val/python/pycharm/logic-bank
    required_path_python_rules = required_path_python_rules.replace("/nw/basic_web_app", "")
    required_path_python_rules = required_path_python_rules.replace("\\nw\\basic_web_app", "")
    required_path_python_rules = required_path_python_rules.replace("\\\\", "\\")  # you cannot be serious

    sys_path = ""
    required_path_present = False
    for each_node in sys.path:
        sys_path += each_node + "\n"
        if each_node == required_path_python_rules:
            required_path_present = True
    print("\n sys.path...\n" + sys_path)
    if not required_path_present:
        print("basic_web_app/app/__init__.py fixing path (so can run from terminal) with: " +
              required_path_python_rules)
        sys.path.append(required_path_python_rules)
        print("sys_path: " + str(sys.path))
    else:
        pass
        print("NOT Fixing path (default PyCharm, set in VSC Launch Config): " +
              required_path_python_rules)

    import nw.db.models as models  # FIXME design prevents circular imports

    from logic_bank.rule_bank import rule_bank_setup
    from nw.logic import declare_logic

"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object("config")
db = SQLA(app)

appbuilder = AppBuilder(app, db.session)

if use_rules:
    rule_bank_setup.setup(db.session, db.engine)
    declare_logic()
    rule_bank_setup.validate(db.session, db.engine)  # checks for cycles, etc

"""
from sqlalchemy.engine import Engine
from sqlalchemy import event

#Only include this for SQLLite constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Will force sqllite contraint foreign keys
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
"""

from . import views
