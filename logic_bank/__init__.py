import logging
import sys

# Initialize Logging

logic_logger = logging.getLogger('logic_logger')  # for users
do_engine_logging = False  # TODO move to config file, reconsider level
engine_logger = logging.getLogger('engine_logger')  # for internals

""" configure logging with statements like this in a config file
logic_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
handler.setFormatter(formatter)
logic_logger.addHandler(handler)

if do_engine_logging:
    engine_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(message)s - %(asctime)s - %(name)s - %(levelname)s')
    handler.setFormatter(formatter)
    engine_logger.addHandler(handler)
"""

"""
Design Issues:
    * sqlalchemy base vs. mapped objects
    * rows as dict{}, or sqlalchemy.ext.declarative.api.Base.<thing>
        https://stackoverflow.com/questions/553784/can-you-use-a-string-to-instantiate-a-class
        getattr(sa_row, "attrName")
    * do sqlalchemy joins preserve table identity?
        
Design Notes:
    * exec code: https://www.geeksforgeeks.org/eval-in-python/
"""
