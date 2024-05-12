"""
Helper interface with common methods for managing the operator installation and making API calls.
"""


from textwrap import dedent
from importlib import resources
from subprocess import Popen, PIPE
from dataclasses import dataclass
from humps import camelize

import yaml
import logging


log = logging.getLogger(__name__)


@dataclass
class CommandOutput:
    stdout: str
    stderr: str
    returnCode: int


def run(command: str, split: str | None = None, shell=False, timeout: float = 5) -> CommandOutput:
    """
    Run a command and return the output, error, and return code.

    Args:
        command (str): shell command to run as a string.
        split (str, optional): character to split the command by. Defaults to None.
        shell (bool, optional): whether to run the command in a shell. Defaults to False.

    Returns:
        CommandOutput: output, error, and return code.
    """
    cmd = dedent(command).lstrip().rstrip().split(split)

    with Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True, shell=shell, encoding='utf-8') as p:
        stdout, stderr = p.communicate(timeout=timeout) # blocking
        return CommandOutput(stdout.rstrip(), stderr.rstrip(), p.returncode)


def load_data(file: str, dtype: str = 'crd') -> dict:
    """
    Load a YAML file into a dictionary.

    Args:
        file (str): The path to the YAML file.
        dtype (str): The type of data to load. Defaults to 'crd'.

    Returns:
        dict: The dictionary representation of the YAML file.
    """
    with resources.open_text(f'tests.data.{dtype}', f'{file}.yaml') as f:
        manifest = yaml.load(f, Loader=yaml.Loader)
        camelized_manifest = camelize(manifest)

        # We undo the camelization of the 'metadata' field to ensure that users' cases and capitalization are respected.
        camelized_manifest['spec']['encryptedData'] = manifest['spec']['encryptedData']

        return camelized_manifest