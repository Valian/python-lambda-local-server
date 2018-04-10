import argparse
import asyncio
import json
import sys
import os

import logging

from functools import partial

from aiohttp import web
from os import path

from requirements import Requirements

SOURCES_DIR = "/var/task"
SOURCES_REQUIREMENTS_NAME = path.join(SOURCES_DIR, "requirements.txt")
LAMBDA_USER_ID = 496

logger = logging.getLogger('lambda')


def demote(user_uid, user_gid):
    os.setgid(user_gid)
    os.setuid(user_uid)


def jsonify(data, status_code=200):
    return web.Response(
        text=json.dumps(data),
        headers={'Content-Type': 'application/json'},
        status=status_code)


async def parse_request(request):
    data = await request.json()
    arn_string = data.get('arn', '')
    version = data.get('version', '')
    event = data.get('event', '{}')
    module = data.get('module', '')
    handler = data.get('file', 'handler.handler')

    if isinstance(event, str):
        event = json.loads(event)

    return handler, event


async def async_execute(handler, event, requirements):
    process = await asyncio.create_subprocess_exec(
        "python", "bootstrap.py", handler, json.dumps(event),
        cwd='/var/runtime/awslambda/',
        env={**os.environ, 'PYTHONPATH': requirements.directory},
        preexec_fn=partial(demote, LAMBDA_USER_ID, LAMBDA_USER_ID),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if stdout:
        stdout = json.loads(stdout.decode('utf-8'))
    if stderr:
        stderr = stderr.decode('utf-8')
    return {'stdout': stdout, 'stderr': stderr}


async def run_lambda(requirements, request):
    handler, event = await parse_request(request)
    result = await async_execute(handler, event, requirements)
    return jsonify(data=result)


async def index(request):
    return web.FileResponse('./index.html')


def init_logging(args):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    logging.getLogger('aiohttp').setLevel(logging.WARN)


def create_app(requirements):
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/', partial(run_lambda, requirements))
    return app


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--timeout', type=float,
        default=6, help="Default timeout for function")
    parser.add_argument(
        '-d', '--directory', default=SOURCES_DIR,
        help="Directory inside container with a source code")
    parser.add_argument(
        '-r', '--requirements', type=str, default=SOURCES_REQUIREMENTS_NAME)
    parser.add_argument(
        '--force', action='store_true', default=False)
    return parser.parse_args()


def install_requirements(requirements_file_path):
    req = Requirements(requirements_file_path)
    req.ensure_installed()
    return req


def main():
    args = get_args()
    init_logging(args)
    requirements = install_requirements(path.join(args.directory, args.requirements))
    app = create_app(requirements)
    host = '0.0.0.0'
    port = 8080
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    exit(main())
