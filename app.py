import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys
import os

import traceback
import uuid

import logging

from functools import partial

from aiohttp import web
from os import path


SOURCES_DIR = "/var/task"
SOURCES_REQUIREMENTS_NAME = path.join(SOURCES_DIR, "requirements.txt")
PACKAGES_DIR = "/packages"
PACKAGES_REQUIREMENTS_PATH = path.join(PACKAGES_DIR, "requirements.txt")
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


async def parse_request(args, request):
    data = await request.json()
    arn_string = data.get('arn', '')
    version = data.get('version', '')
    event = data.get('event', '{}')
    module = data.get('module', '')
    handler = data.get('file', 'handler.handler')

    if isinstance(event, str):
        event = json.loads(event)

    return handler, event


async def async_execute(handler, event):
    process = await asyncio.create_subprocess_exec(
        "python", "bootstrap.py", handler, json.dumps(event),
        cwd='/var/runtime/awslambda/',
        env={**os.environ, 'PYTHONPATH': PACKAGES_DIR},
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


async def run_lambda(args, request):
    handler, event = await parse_request(args, request)
    result = await async_execute(handler, event)
    return jsonify(data=result)


async def index(request):
    return web.FileResponse('./index.html')


def get_md5_of_file(path):
    try:
        hash = hashlib.md5()
        with open(path, 'rb') as f:
            hash.update(f.read())
        return hash.hexdigest()
    except IOError:
        return ''


def install_requirements(args, force=False):
    requirements_path = path.join(args.directory, args.requirements)
    previous_requirements_path = PACKAGES_REQUIREMENTS_PATH
    current_md5 = get_md5_of_file(requirements_path)
    previous_md5 = get_md5_of_file(previous_requirements_path)
    if current_md5 != previous_md5 or force:
        logger.info("Updating requirements...")
        shutil.rmtree(PACKAGES_DIR, ignore_errors=True)
        subprocess.run(["pip", "install", "-t", PACKAGES_DIR, "-r", requirements_path])
        shutil.copy(requirements_path, previous_requirements_path)
    else:
        logger.info("Requirements not changed, skipping update...")


def init_logging(args):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    logging.getLogger('aiohttp').setLevel(logging.WARN)


def create_app(args):
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/', partial(run_lambda, args))
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


def main():
    args = get_args()
    init_logging(args)
    install_requirements(args)
    app = create_app(args)
    host = '0.0.0.0'
    port = 8080
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    exit(main())
