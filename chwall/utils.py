#!/usr/bin/env python3

import os
import re
import yaml
import random
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


VERSION = "0.1"
BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)


def temp_file_path():
    try:
        with open("{}/temp".format(BASE_CACHE_PATH), "r") as f:
            temp_file = f.readline()
    except FileNotFoundError:
        return None
    if os.path.exists(temp_file):
        return temp_file
    return None


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


def build_picture_lists(config):
    print("Fetching pictures addresses…")

    collecs = {}
    for module_name in config["general"]["sources"]:
        m = __import__(
            "chwall.fetcher.{}".format(module_name),
            globals(), locals(), ['fetch_pictures'], 0)
        collecs.update(m.fetch_pictures(config))
    all_pics = list(collecs.keys())

    try:
        with open("{}/blacklist.yml"
                  .format(BASE_CACHE_PATH), "r") as f:
            blacklist = yaml.load(f) or []
    except FileNotFoundError:
        blacklist = []
    for p in all_pics:
        if p not in blacklist:
            continue
        print("Remove {} as it's in blacklist".format(p))
        all_pics.remove(p)
        collecs.pop(p)
    random.shuffle(all_pics)
    return {"data": collecs, "pictures": all_pics, "history": []}
