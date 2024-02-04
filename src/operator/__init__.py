"""
Make the environment variables' values that we care about, portable.
"""


from typing import Dict
from pathlib import Path

import os


# TODO: implement import
# __all__ = [

# ]


env: Dict[str, str] = {
    # Environment variables to configure the operator (kopf).
    'OPERATOR_INTERVAL':      os.getenv('OPERATOR_INTERVAL', '60'),
    'OPERATOR_INITIAL_DELAY': os.getenv('OPERATOR_INITIAL_DELAY', '3'),
    'OPERATOR_PRIORITY':      os.getenv('OPERATOR_PRIORITY', '100'),
    'OPERATOR_NAMESPACE':     os.getenv('OPERATOR_NAMESPACE', 'default'),
    'OPERATOR_POD_IP':        os.getenv('OPERATOR_POD_IP', '0.0.0.0'),

    # Environment variables to configure pass.
    'PASS_BINARY':            os.getenv('PASS_BINARY', '/usr/bin/pass'),
    'PASS_DIRECTORY':         str(Path(f'~/.password-store/{os.getenv("PASS_DIRECTORY", "")}').expanduser()),
    'PASS_GPG_PASSPHRASE':    os.getenv('PASS_GPG_PASSPHRASE', ''),
    'PASS_GPG_KEY':           os.getenv('PASS_GPG_KEY', ''),
    'PASS_GPG_KEY_ID':        os.getenv('PASS_GPG_KEY_ID', ''),
    'PASS_GIT_URL':           os.getenv('PASS_GIT_URL', ''),
    'PASS_GIT_BRANCH':        os.getenv('PASS_GIT_BRANCH', 'main')
}