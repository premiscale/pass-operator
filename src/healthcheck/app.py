"""
Extend gunicorn base application. Based on docs

https://docs.gunicorn.org/en/latest/custom.html
"""


import multiprocessing
import gunicorn.app.base as base
import logging

from typing import Optional, Dict, Any
from ipaddress import IPv4Address
from pathlib import Path
from src.healthcheck import app


log = logging.getLogger(__name__)


def automatic_workers_count() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


class StandaloneApplication(base.BaseApplication):
    """
    Custom gunicorn application so we can start this service via the registration service CLI.
    """
    def __init__(self, app, options: Optional[Dict] = None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def __enter__(self) -> 'StandaloneApplication':
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def load_config(self):
        """
        Load a gunicorn config map instead of the traditional config file.
        """
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def start(ip: IPv4Address = IPv4Address('127.0.0.1'), port: int = 8080, workers: int = 0, pid_file: Path = Path('/opt/pass-operator/runtime.pid')) -> None:
    """
    Start the gunicorn app.

    Args:
        ip (IPv4Address): address to listen on.
        port (int): _description_
    """
    if workers == 0:
        workers = automatic_workers_count()

    log.info(f'number of workers: {workers}')

    options = {
        'bind': f'{ip}:{port}',
        'workers': workers,
        'backlog': 512,
        'worker_class': 'sync',
        'worker_connections': 100,
        'timeout': 30,
        'keepalive': 5,
        'spew': False,
        'daemon': False,
        'raw_env': [],
        'pidfile': str(pid_file),
        'umask': 0,
        'user': None,
        'group': None,
        'tmp_upload_dir': None,
        'errorlog': '-',
        'loglevel': 'info',
        'accesslog': '-',
        'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"',
        'proc_name': 'registration'
    }

    log.debug(f'gunicorn config: {options}')

    with StandaloneApplication(app, options) as flask_app:
        flask_app.run()