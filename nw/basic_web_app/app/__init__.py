import logging

from flask import Flask
from flask_appbuilder import AppBuilder, SQLA
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.api import ModelRestApi

use_rules = True

if use_rules:
    import logic_bank_utils.util as logic_bank_utils
    (did_fix_path, sys_env_info) = \
        logic_bank_utils.add_python_path(project_dir="LogicBank", my_file=__file__)

    import nw.db.models as models  # FIXME design prevents circular imports

    from nw.logic.rules_bank import declare_logic

    from logic_bank.logic_bank import LogicBank  # activate rules (calls declare_logic)

"""
 Logging configuration
"""

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
logging.getLogger().setLevel(logging.DEBUG)

app = Flask(__name__)
app.config.from_object("config")
db = SQLA(app)

appbuilder = AppBuilder(app, db.session)

create_api = False  # experiment (disabled)

if create_api:
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
