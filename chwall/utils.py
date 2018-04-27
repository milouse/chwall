#!/usr/bin/env python3

import os
import re
import yaml
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


VERSION = "0.1"
BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)


def get_screen_config():
    n = subprocess.run("xrandr -q | grep '*' | wc -l",
                       check=True, shell=True,
                       stdout=subprocess.PIPE).stdout.decode()
    sp = subprocess.run("xrandr -q | head -n1",
                        check=True, shell=True,
                        stdout=subprocess.PIPE).stdout.decode()
    s = re.match(".*, current ([0-9]+) x .*", sp.strip())
    return (n.strip(), s[1])


def read_config():
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    try:
        with open(config_file, "r") as f:
            config = yaml.load(f) or {}
    except FileNotFoundError:
        config = {}
    pic_cache = "{}/pictures".format(BASE_CACHE_PATH)
    if not os.path.exists(pic_cache):
        os.makedirs(pic_cache)
    if "general" not in config:
        config["general"] = {}
    if "sources" not in config["general"]:
        config["general"]["sources"] = [
            "bing", "unsplash", "nasa", "local"]
    if "sleep" not in config["general"]:
        config["general"]["sleep"] = 10 * 60
    return config
