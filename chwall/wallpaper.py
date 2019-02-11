#!/usr/bin/env python3

import os
import sys
import time
import yaml
import random
import shutil
import hashlib
import requests
import subprocess

# chwall imports
from chwall.utils import BASE_CACHE_PATH


class ChwallEmptyListError(Exception):
    pass


class ChwallWallpaperSetError(Exception):
    pass


WAIT_ERROR = 10


def build_wallpapers_list(config):
    print("Fetching pictures addresses…")
    collecs = {}
    for module_name in config["general"]["sources"]:
        try_again = 5
        ll = {}
        m = __import__(
            "chwall.fetcher.{}".format(module_name),
            globals(), locals(), ['fetch_pictures'], 0)
        while try_again > 0:
            try:
                ll = m.fetch_pictures(config)
                try_again = 0
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.HTTPError,
                    requests.exceptions.Timeout) as e:
                print("Catch {error} exception while retrieving "
                      "images from {module}. Wait {time} seconds "
                      "before retrying.".format(
                        error=type(e).__name__, module=module_name,
                        time=WAIT_ERROR),
                      file=sys.stderr)
                try_again -= 1
                try:
                    time.sleep(WAIT_ERROR)
                except KeyboardInterrupt:
                    print("Retry NOW to connect to {}"
                          .format(module_name))
            except KeyboardInterrupt:
                print("Switch to next picture provider or exit")
                try_again = 0
        collecs.update(ll)
    return collecs


def filter_wallpapers_list(collecs):
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
    return (all_pics, collecs)


def write_roadmap(data):
    all_pics = data[0]
    random.shuffle(all_pics)
    road_map = {"data": data[1], "pictures": all_pics, "history": []}
    with open("{}/roadmap".format(BASE_CACHE_PATH), "w") as f:
        yaml.dump(road_map, f, explicit_start=True, default_flow_style=False)


def build_roadmap(config):
    write_roadmap(filter_wallpapers_list(build_wallpapers_list(config)))


def set_mate_wallpaper(path):
    if path is None:
        raise ChwallWallpaperSetError("No wallpaper path given")
    err = subprocess.run(["gsettings", "set", "org.mate.background",
                         "picture-filename", path]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting picture-filename property")
    err = subprocess.run(["gsettings", "set", "org.mate.background",
                         "picture-options", "zoom"]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting picture-options property")


def set_wallpaper(path, config):
    set_mate_wallpaper(path)
    if "lightdm_wall" in config["general"]:
        ld_path = os.path.expanduser(
            config["general"]["lightdm_wall"])
        shutil.copy(path, ld_path)


def fetch_wallpaper(collecs):
    if collecs["pictures"] is None or len(collecs["pictures"]) == 0:
        raise ChwallEmptyListError("No wallpaper in list")
    wp = collecs["data"][collecs["pictures"][0]]
    # screen_config = get_screen_config()
    with open("{}/current_wallpaper".format(BASE_CACHE_PATH), "w") as f:
        f.write(wp["image"])
        f.write("\n{copy}\n{url}\n{source}".format(
            copy=wp["copyright"], url=wp["url"], source=wp["type"]))
    if wp["type"] == "local":
        return wp["image"], wp["image"]
    m = hashlib.md5()
    m.update(wp["image"].encode())
    pic_file = "{}/pictures/{}-{}".format(
        BASE_CACHE_PATH, wp["type"], m.hexdigest())
    if os.path.exists(pic_file):
        return pic_file, wp["image"]
    with open(pic_file, "wb") as f:
        f.write(requests.get(wp["image"]).content)
    if os.path.getsize(pic_file) == 0:
        # Do not keep empty files. It may be caused by a network error or
        # something else, which may be resolved later.
        os.unlink(pic_file)
        raise ChwallEmptyListError("Wallpaper file was empty")
    return pic_file, wp["image"]


def pick_wallpaper(config, backward=False, guard=0):
    road_map = "{}/roadmap".format(BASE_CACHE_PATH)
    if not os.path.exists(road_map):
        build_roadmap(config)
    with open(road_map, "r") as f:
        data = yaml.load(f)
    if backward is True:
        # Current wallpaper is the last of the history array. Thus we should go
        # back two times
        if len(data["history"]) >= 1:
            # Current wall
            data["pictures"].insert(0, data["history"].pop())
            # Previous one
            data["pictures"].insert(0, data["history"].pop())
    try:
        lp, wp = fetch_wallpaper(data)
    except ChwallEmptyListError as err:
        # Try again with a fresh road_map
        os.unlink(road_map)
        guard += 1
        if guard == 3:
            # Something goes wrong, reraise and abort
            raise ChwallEmptyListError(err)
        build_roadmap(config)
        # Backward is always false because at this point, something went wrong
        # and we should start over.
        return pick_wallpaper(config, False, guard)
    data["pictures"].remove(wp)
    data["history"].append(wp)
    with open(road_map, "w") as f:
        yaml.dump(data, f, explicit_start=True,
                  default_flow_style=False)
    set_wallpaper(lp, config)


def blacklist_wallpaper():
    try:
        with open("{}/blacklist.yml"
                  .format(BASE_CACHE_PATH), "r") as f:
            blacklist = yaml.load(f) or []
    except FileNotFoundError:
        blacklist = []
    with open("{}/current_wallpaper"
              .format(BASE_CACHE_PATH), "r") as f:
        blacklist.append(f.readlines()[0].strip())
    with open("{}/blacklist.yml"
              .format(BASE_CACHE_PATH), "w") as f:
        yaml.dump(blacklist, f, explicit_start=True,
                  default_flow_style=False)
