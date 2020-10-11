import logging
import os
import sys

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.api import ModelRestApi

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

    from logic_bank.logic_bank import LogicBank

"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object("config")
db = SQLA(app)

appbuilder = AppBuilder(app, db.session)
unparsedTables = dict([(name, cls) for name, cls in models.__dict__.items() if isinstance(cls, type)])

for modelName in unparsedTables:
    className = str(unparsedTables[modelName])
    if '.models.' in className and not modelName.startswith('Ab'):
        apiBuildObj = {
            "resource_name": modelName.lower(),
            "datamodel": SQLAInterface(unparsedTables[modelName])
        }
        apiName = modelName + 'ModelApi'
        apiClass = type(apiName, (ModelRestApi,), apiBuildObj)
        print(modelName)
        appbuilder.add_api(apiClass)

if use_rules:
    LogicBank.activate(session=db.session, activator=declare_logic)

from . import views
