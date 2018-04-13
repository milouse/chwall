#!/usr/bin/env python3

import os
import sys
import yaml
import shutil
import hashlib
import requests
import subprocess

# chwall imports
from chwall.utils import BASE_CACHE_PATH


def set_mate_wallpaper(path, config):
    subprocess.run(["gsettings", "set", "org.mate.background",
                    "picture-filename", path])
    subprocess.run(["gsettings", "set", "org.mate.background",
                    "picture-options", "zoom"])
    if "lightdm_wall" in config["general"]:
        ld_path = os.path.expanduser(
            config["general"]["lightdm_wall"])
        shutil.copy(path, ld_path)


def set_wallpaper(path, config):
    set_mate_wallpaper(path, config)


def fetch_wallpaper(collecs):
    if len(collecs["pictures"]) == 0:
        sys.exit(0)
    wp = collecs["data"][collecs["pictures"][0]]
    # screen_config = get_screen_config()
    with open("{}/current_wallpaper".format(BASE_CACHE_PATH), "w") as f:
        f.write(wp["image"])
        f.write("\n{}\n{}".format(wp["copyright"], wp["url"]))
    if wp["local"] is True:
        return wp["image"], wp["image"]
    m = hashlib.md5()
    m.update(wp["image"].encode())
    pic_file = "{}/pictures/{}-{}".format(
        BASE_CACHE_PATH, wp["type"], m.hexdigest())
    if os.path.exists(pic_file):
        return pic_file, wp["image"]
    with open(pic_file, "wb") as f:
        f.write(requests.get(wp["image"]).content)
    return pic_file, wp["image"]


def choose_wallpaper(collecs_file, config):
    with open(collecs_file, "r") as f:
        data = yaml.load(f)
    lp, wp = fetch_wallpaper(data)
    data["pictures"].remove(wp)
    data["history"].append(wp)
    with open(collecs_file, "w") as f:
        yaml.dump(data, f, explicit_start=True,
                  default_flow_style=False)
    set_mate_wallpaper(lp, config)
