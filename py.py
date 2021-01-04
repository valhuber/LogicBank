#!/usr/bin/env python
# sudo chmod +x py.py
# ./py.py
# in .zshrc: python py.py

import os, sys
import subprocess


def show(cmd: str):
    result_b = subprocess.check_output(cmd, shell=True)
    result = str(result_b)  # b'pyenv 1.2.21\n'
    result = result[2: len(result)-3]
    tab_to = 20 - len(cmd)
    spaces = ' ' * tab_to
    print(f'{cmd}: {spaces}{result}')


def python_status():
    print("\n\nPython Status here, 1.0\n")
    show("pyenv --version")
    show("pyenv global")
    show("pyenv version-name")
    show("virtualenv --version")
    show("python --version")
    print("PYTHONPATH..")
    for p in sys.path:
        print(".." + p)
    print("")


if __name__ == '__main__':
    python_status()
