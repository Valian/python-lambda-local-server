import argparse
import asyncio
import hashlib
import importlib
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

from lambda_local.main import load_lib
from lambda_local.context import Context

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


import os
import types
import importlib


def reload_package(package):
    assert(hasattr(package, "__package__"))
    fn = package.__file__
    fn_dir = os.path.dirname(fn) + os.sep
    module_visit = {fn}
    del fn

    def reload_recursive_ex(module):
        importlib.reload(module)

        for module_child in vars(module).values():
            if isinstance(module_child, types.ModuleType):
                fn_child = getattr(module_child, "__file__", None)
                if (fn_child is not None) and fn_child.startswith(fn_dir):
                    if fn_child not in module_visit:
                        # print("reloading:", fn_child, "from", module)
                        module_visit.add(fn_child)
                        reload_recursive_ex(module_child)

    return reload_recursive_ex(package)


def load(directory, module, handler_path):
    file_path = path.join(directory, module)
    file_directory = path.dirname(file_path)
    sys.path.append(file_directory)
    function_file, function_name = path.splitext(handler_path)
    mod = importlib.import_module(function_file)
    reload_package(mod)
    func = getattr(mod, function_name.strip('.'))
    return func


async def parse_request(args, request):
    data = await request.json()
    arn_string = data.get('arn', '')
    version = data.get('version', '')
    event = data.get('event', '{}')
    module = data.get('module', '')
    handler = data.get('file', 'handler.handler')

    if isinstance(event, str):
        event = json.loads(event)

    context = Context(args.timeout, arn_string, version)
    func = load(args.directory, module, handler)
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
            "stackTrace": traceback.format_tb(err[2]),
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


async def run_lambda(args, request):
    func, event, context = await parse_request(args, request)
    request_id = uuid.uuid4()
    result = await async_execute(request_id, func, event, context)
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
    load_lib(PACKAGES_DIR)


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
