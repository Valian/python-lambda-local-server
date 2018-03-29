import argparse
import asyncio
import hashlib
import json
import shutil
import subprocess
import sys

import traceback
import timeit
import uuid

import logging

import math
from functools import partial

from aiohttp import web
from os import path

from lambda_local.main import load_lib, load
from lambda_local.context import Context
from lambda_local.event import read_event

SOURCES_DIR = "/src"
SOURCES_REQUIREMENTS_NAME = path.join(SOURCES_DIR, "requirements.txt")
PACKAGES_DIR = "/packages"
PACKAGES_REQUIREMENTS_PATH = path.join(PACKAGES_DIR, "requirements.txt")

logger = logging.getLogger('lambda')


def jsonify(data, status_code=200):
    return web.Response(
        text=json.dumps(data),
        headers={'Content-Type': 'application/json'},
        status=status_code)


async def parse_request(args, request_id, request):
    data = await request.json()
    arn_string = data.get('arn', '')
    version = data.get('version', '')
    event = data.get('event', {})
    handler_file = data.get('file', "handler.py")
    handler_name = data.get('handler', 'handler')

    handler_path = path.join(args.directory, handler_file)
    event = read_event(event)
    context = Context(args.timeout, arn_string, version)
    func = load(request_id, handler_path, handler_name)
    return func, event, context


async def execute(func, event, context):
    loop = asyncio.get_event_loop()
    try:
        future = loop.run_in_executor(None, func, event, context)
        result = await asyncio.wait_for(future, context.timeout)
    except asyncio.TimeoutError as e:
        result = e
    except Exception:
        err = sys.exc_info()
        result = json.dumps({
            "errorMessage": str(err[1]),
            "stackTrace": str(traceback.extract_tb(err[2])),
            "errorType": err[0].__name__
        }, indent=4, separators=(',', ': '))
    return result


async def async_execute(request_id, func, event, context):
    logger.info("Event: {}".format(event))
    logger.info("START RequestId: {}".format(request_id))

    start_time = timeit.default_timer()
    result = await execute(func, event, context)
    end_time = timeit.default_timer()

    logger.info("END RequestId: {}".format(request_id))

    output_func = logger.error if type(result) is Exception else logger.info
    output_func(f"RESULT:\n{result}")
    duration = (end_time - start_time) * 1000
    billed_duration = math.ceil(duration / 100) * 100
    logger.info(
        f"REPORT RequestId: {request_id}\t"
        f"Duration: {duration:.2f} ms\t"
        f"Billed Duration: {billed_duration:.2f} ms")
    return result


async def index(args, request):
    request_id = uuid.uuid4()
    func, event, context = await parse_request(args, request_id, request)
    result = await async_execute(request_id, func, event, context)
    return jsonify(data=result)


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
    load_lib(PACKAGES_DIR)


def init_logging(args):
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    logging.getLogger('aiohttp').setLevel(logging.WARN)


def create_app(args):
    app = web.Application()
    app.router.add_post('/', partial(index, args))
    return app


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t', '--timeout', type=int,
        default=6, help="Default timeout for function")
    parser.add_argument(
        '-d', '--directory', default=SOURCES_DIR,
        help="Directory inside container with a source code")
    parser.add_argument(
        '-r', '--requirements', type=str, default=SOURCES_REQUIREMENTS_NAME)
    parser.add_argument(
        '-f', '--handler_file', type=str, default="handler.py")
    parser.add_argument(
        '--handler_func', type=str, default="handler")
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
