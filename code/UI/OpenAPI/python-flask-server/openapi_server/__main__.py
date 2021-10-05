#!/usr/bin/env python3

import connexion
import flask
import logging
import signal

from flask_cors import CORS

from openapi_server import encoder

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../ARAX/ARAXQuery")
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../reasoningtool/QuestionAnswering")

def receive_sigchld(signal_number, frame):
    if signal_number == signal.SIGCHLD:
        os.waitpid(-1, os.WNOHANG)

def main():
    app = connexion.App(__name__, specification_dir='./openapi/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'ARAX Translator Reasoner'},
                pythonic_params=True)
    CORS(app.app)
    signal.signal(signal.SIGCHLD, receive_sigchld)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    app.run(port=5001, threaded=True)


if __name__ == '__main__':
    main()
