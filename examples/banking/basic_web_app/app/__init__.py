import logging
import os
import sys

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA

from logic_bank.logic_bank import LogicBank

use_rules = True

if use_rules:  # need logic_bank on path... add if not present
    import logic_bank_utils.util as logic_bank_utils
    (did_fix_path, sys_env_info) = \
        logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

    print("app/__init__ - sys_env_info:\n" + sys_env_info)
    from logic_bank.rule_bank import rule_bank_setup
    from examples.banking.logic.rules_bank import activate_basic_rules

"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
from examples.banking.basic_web_app import config as config
my_config = config
print("config.db_dir?? " + config.db_dir)
app.config.from_object("config")
db = SQLA(app)

appbuilder = AppBuilder(app, db.session)

if use_rules:
    LogicBank.activate(session=db.session, activator=activate_basic_rules)

from . import views
