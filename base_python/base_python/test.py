"""
Example CLI that blocks.
"""


import time

from base_python.alternate.importable import hello


def cli() -> None:
    """
    Print hello over and over again.
    """
    while True:
        print(hello())
        time.sleep(10)


if __name__ == '__main__':
    cli()