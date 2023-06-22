"""
Registration service's daemon. Follows the same pattern as the agent.
"""

import logging

from flask import Flask, Response
from http import HTTPStatus
from flask_cors import CORS


app = Flask(__name__)
CORS(app)


log = logging.getLogger(__name__)


@app.get('/healthcheck')
def healthcheck() -> Response:
    """
    Quick healthcheck endpoint.

    Returns:
        dict: an object with schema like

        {
            "status": "OK"
        }
    """
    return Response(
        {
            'status': 'OK'
        },
        status=HTTPStatus.OK,
        mimetype='application/json'
    )