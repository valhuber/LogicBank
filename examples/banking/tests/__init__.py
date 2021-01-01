import os
from shutil import copyfile
from logic_bank.util import prt


def setup_db():
    """ copy db/database-gold.db over db/database.db"""
    print("\n" + prt("restoring database-gold\n"))

    basedir = os.path.abspath(os.path.dirname(__file__))
    basedir = os.path.dirname(basedir)

    print("\n********************************\n"
          "  IMPORTANT - create database.db from database-gold.db in " + basedir + "/nw/db/\n" +
          "            - from -- " + prt("") +
          "\n********************************")

    nw_loc = os.path.join(basedir, "db/database.db")
    nw_source = os.path.join(basedir, "db/database-gold.db")
    copyfile(src=nw_source, dst=nw_loc)
