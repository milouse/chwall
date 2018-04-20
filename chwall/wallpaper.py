#!/usr/bin/env python3

import os
import yaml
import random
import shutil
import hashlib
import requests
import subprocess

# chwall imports
from chwall.utils import BASE_CACHE_PATH


def build_wallpapers_list(config):
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


def set_mate_wallpaper(path, config):
    if path is None:
        return False
    err = []
    err.append(
        subprocess.run(["gsettings", "set", "org.mate.background",
                        "picture-filename", path]).returncode)
    err.append(
        subprocess.run(["gsettings", "set", "org.mate.background",
                        "picture-options", "zoom"]).returncode)
    if "lightdm_wall" in config["general"]:
        ld_path = os.path.expanduser(
            config["general"]["lightdm_wall"])
        shutil.copy(path, ld_path)
    return 1 not in err


def set_wallpaper(path, config):
    return set_mate_wallpaper(path, config)


def fetch_wallpaper(collecs):
    if len(collecs["pictures"]) == 0:
        return None, None
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
    if lp is None:
        return False
    data["pictures"].remove(wp)
    data["history"].append(wp)
    with open(collecs_file, "w") as f:
        yaml.dump(data, f, explicit_start=True,
                  default_flow_style=False)
    return set_mate_wallpaper(lp, config)
