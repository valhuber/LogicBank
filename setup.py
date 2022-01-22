import io
import os
import re

from setuptools import find_packages, setup

def fpath(name):
    return os.path.join(os.path.dirname(__file__), name)


def read(fname):
    return open(fpath(fname)).read()

find_version = True
if find_version:
    with io.open("logic_bank/rule_bank/rule_bank_setup.py", "rt", encoding="utf8") as f:
        version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)
else:
    version = "0.0"

def desc():
    return read("README.md")


project_urls = {
  'Docs': 'https://github.com/valhuber/logicbank/wiki'
}

setup(
    name="logicbank",
    version=version,
    url="https://github.com/valhuber/logicbank",
    license="BSD",
    author="Val Huber",
    author_email="valjhuber@gmail.com",
    project_urls=project_urls,
    description=(
        "Declare multi-table rules for SQLAlchemy update logic -- "
        "40X more concise, Python for extensibility."
    ),
    long_description=desc(),
    long_description_content_type='text/markdown',
    # packages=find_packages(include=['logic_bank']),
    packages=['logic_bank', 'logic_bank.exec_row_logic', 'logic_bank.exec_trans_logic', 'logic_bank.rule_bank', 'logic_bank.rule_type', 'logic_bank.extensions'],
    package_data={"": ["LICENSE"]},
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=[
        "python-dateutil>=2.3, <3",
        "sqlalchemy>=1.4",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires="~=3.8"
)