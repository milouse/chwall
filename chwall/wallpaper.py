import os
import sys
import time
import yaml
import random
import shutil
import hashlib
import requests
import subprocess
from importlib import import_module

# chwall imports
from chwall.utils import BASE_CACHE_PATH, get_screen_config, get_wall_config


class ChwallWallpaperSetError(Exception):
    pass


WAIT_ERROR = 10


def build_wallpapers_list(config):
    print("Fetching pictures addresses…")
    collecs = {}
    for module_name in config["general"]["sources"]:
        try_again = 5
        ll = {}
        m = import_module("chwall.fetcher.{}".format(module_name))

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
            "Error while setting mate picture-filename property")
    err = subprocess.run(["gsettings", "set", "org.mate.background",
                         "picture-options", "zoom"]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting mate picture-options property")


def set_gnome_wallpaper(path):
    if path is None:
        raise ChwallWallpaperSetError("No wallpaper path given")
    err = subprocess.run(["gsettings", "set", "org.gnome.desktop.background",
                         "picture-uri", "file://{}".format(path)]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting gnome background picture-uri property")
    err = subprocess.run(["gsettings", "set", "org.gnome.desktop.background",
                         "picture-options", "zoom"]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting gnome background picture-options property")
    err = subprocess.run(["gsettings", "set", "org.gnome.desktop.screensaver",
                         "picture-uri", "file://{}".format(path)]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting gnome screensaver picture-uri property")
    err = subprocess.run(["gsettings", "set", "org.gnome.desktop.screensaver",
                         "picture-options", "zoom"]).returncode
    if err == 1:
        raise ChwallWallpaperSetError(
            "Error while setting gnome screensaver picture-options property")


def set_nitrogen_wallpaper(path):
    cmd = ["nitrogen", "--set-auto"]
    # screen_info = (scr_number, scr_width, scr_height, scr_ratio)
    screen_info = get_screen_config()
    if screen_info is None:
        screen_info = (1, 0, 0, 1)
    # wall_info = (wall_width, wall_height, wall_ratio)
    wall_info = get_wall_config(path)
    if wall_info is None:
        wall_info = (0, 0, 1)
    ratio_cmp = int(screen_info[3]) - int(wall_info[2])
    if ratio_cmp == 0 or wall_info[2] < 1:
        cmd[1] = "--set-zoom-fill"
    if screen_info[0] > 1 and ratio_cmp != 0:
        err = 0
        for screen_index in range(screen_info[0]):
            head = "--head={}".format(screen_index)
            err += subprocess.run(cmd + [head, path]).returncode
        if err == 0:
            return
        raise ChwallWallpaperSetError(
            "Error while calling nitrogen for multihead display")
    err = subprocess.run(cmd + [path]).returncode
    if err != 0:
        raise ChwallWallpaperSetError(
            "Error while calling nitrogen for single display")


def set_wallpaper(path, config):
    if "desktop" in config["general"]:
        desktop = config["general"]["desktop"]
    else:
        desktop = "gnome"
    method = "set_{}_wallpaper".format(desktop)
    if method in globals():
        globals()[method](path)
    else:
        set_gnome_wallpaper(path)
    if "lightdm_wall" in config["general"]:
        ld_path = os.path.expanduser(
            config["general"]["lightdm_wall"])
        shutil.copy(path, ld_path)
    return path


def fetch_wallpaper(collecs):
    wp = collecs["data"][collecs["pictures"][0]]
    if wp["type"] == "local":
        pic_file = wp["image"]
    else:
        m = hashlib.md5()
        m.update(wp["image"].encode())
        pic_file = "{}/pictures/{}-{}".format(
            BASE_CACHE_PATH, wp["type"], m.hexdigest())
    # screen_config = get_screen_config()
    with open("{}/current_wallpaper".format(BASE_CACHE_PATH), "w") as f:
        f.write(wp["image"])
        f.write("\n{copy}\n{url}\n{source}\n{local_path}".format(
            copy=wp["copyright"], url=wp["url"], source=wp["type"],
            local_path=pic_file))
    if os.path.exists(pic_file):
        return pic_file, wp["image"]
    with open(pic_file, "wb") as f:
        f.write(requests.get(wp["image"]).content)
    if os.path.getsize(pic_file) == 0:
        # Do not keep empty files. It may be caused by a network error or
        # something else, which may be resolved later.
        os.unlink(pic_file)
        return None, None
    return pic_file, wp["image"]


def pick_wallpaper(config, backward=False, guard=False):
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
            # Now we are good to do a fake "forward" move
    if data["pictures"] is None or len(data["pictures"]) == 0:
        # Woops, no picture left. Removing current roadmap.
        os.unlink(road_map)
        if guard is True:
            # Wow, we already try to reload once, it's very bad to be
            # there. Maybe a little network error. Be patient
            return None
        # List is empty. Maybe it was the last picture of the current list?
        # Thus, try again now. Backward is always false because at this point,
        # something went wrong and we should start over.
        return pick_wallpaper(config, False, True)
    lp, wp = fetch_wallpaper(data)
    if lp is None:
        # Something goes wrong, thus do nothing. It may be because of a
        # networking error or something else.
        # In any case, we remove the current roadmap file to force its
        # recomputing the next time pick_wallpaper is called.
        os.unlink(road_map)
        return None
    data["pictures"].remove(wp)
    data["history"].append(wp)
    with open(road_map, "w") as f:
        yaml.dump(data, f, explicit_start=True,
                  default_flow_style=False)
    return set_wallpaper(lp, config)


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


def current_wallpaper_info():
    curwall = []
    # line 0 contains wallpaper uri
    # line 1 contains description
    # line 2 contains remote page in case of remote wallpaper
    # line 3 contains wallpaper type/origin
    # line 4 contains wallpaper local path
    with open("{}/current_wallpaper"
              .format(BASE_CACHE_PATH), "r") as f:
        curwall = f.readlines()
    return {
        "remote-picture-uri": curwall[0].strip(),
        "description": curwall[1].strip(),
        "remote-uri": curwall[2].strip(),
        "type": curwall[3].strip(),
        "local-picture-path": curwall[4].strip()
    }
