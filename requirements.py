import hashlib
import shutil
import subprocess
from os import path

import logging

logger = logging.getLogger(__name__)


def get_md5_of_file(filepath):
    try:
        h = hashlib.md5()
        with open(filepath, 'rb') as f:
            h.update(f.read())
        return h.hexdigest()
    except IOError:
        return None


class Requirements:

    CACHE_PATH = "/packages"

    def __init__(self, requirements_path, tag='default'):
        self.tag = tag
        self.requirements_path = requirements_path
        self.cached_requirements_path = path.join(self.CACHE_PATH, f"{self.tag}_requirements.txt")

    @property
    def directory(self):
        return self.get_requirements_directory(self.cached_requirements_path)

    def get_requirements_directory(self, requirements_path):
        md5_hash = get_md5_of_file(requirements_path)
        if md5_hash:
            return path.join(self.CACHE_PATH, md5_hash)
        else:
            return None

    def ensure_installed(self, force_reinstall=False):
        req_dir = self.directory
        if not req_dir or not path.exists(req_dir) or force_reinstall:
            logger.info(f"Updating requirements for tag '{self.tag}'...")
            # If previous requirements exists, let's remove them
            shutil.rmtree(req_dir, ignore_errors=True)
            new_requirements_dir = self.get_requirements_directory(self.requirements_path)
            subprocess.run([
                "pip", "install",
                "-t", new_requirements_dir,
                "-r", self.requirements_path])
            shutil.copy(self.requirements_path, self.cached_requirements_path)
        else:
            logger.info(f"Requirements not changed, skipping update for tag '{self.tag}'...")
