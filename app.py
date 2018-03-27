import asyncio
import hashlib
import shutil
import subprocess
from aiohttp import web
from os import path, rmdir

from shutil import copy

PACKAGES_DIR = "/packages"


async def index(request):
    process = await asyncio.create_subprocess_exec(
        "python-lambda-local", "-l", PACKAGES_DIR, "-f", "handler", "handler.py", "event.json",
        cwd='/src',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    body = ''
    if stdout:
        body += stdout.decode('utf-8')
    if stderr:
        body += stderr.decode('utf-8')
    return web.Response(text=body)


def get_md5_of_file(path):
    try:
        hash = hashlib.md5()
        with open(path, 'rb') as f:
            hash.update(f.read())
        return hash.hexdigest()
    except IOError:
        return ''


def install_requirements(requirements_path="/src/requirements.txt", force=False):
    previous_requirements_path = path.join(PACKAGES_DIR, 'requirements.txt')
    current_md5 = get_md5_of_file(requirements_path)
    previous_md5 = get_md5_of_file(previous_requirements_path)
    if current_md5 != previous_md5 or force:
        print("Updating requirements...")
        shutil.rmtree(PACKAGES_DIR, ignore_errors=True)
        subprocess.run(["pip", "install", "-t", PACKAGES_DIR, "-r", requirements_path])
        shutil.copy(requirements_path, previous_requirements_path)
    else:
        print("Requirements not changed, skipping update...")


def create_app():
    app = web.Application()
    app.router.add_get('/', index)
    return app


def main():
    install_requirements()
    app = create_app()
    host = '0.0.0.0'
    port = 8080
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    exit(main())

