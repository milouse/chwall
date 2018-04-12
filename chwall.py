#!/usr/bin/env python3

import os
import re
import sys
import time
import yaml
import shutil
import signal
import random
import hashlib
import tempfile
import requests
import subprocess
from xdg.BaseDirectory import xdg_config_home, xdg_cache_home


LIGHTDM_CACHE_PATH = "/var/cache/chwall"
BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)
SYSTEMD_TEMPLATE = """
[Unit]
Description = Simple wallpaper changer

[Service]
ExecStart={command}

[Install]
WantedBy=default.target
""".strip()


def daemon_client():
    if sys.argv[1] == "systemd":
        print(SYSTEMD_TEMPLATE.format(command=sys.argv[0]))
        sys.exit()
    if sys.argv[1] not in [
            "blacklist", "history", "info", "next", "pending"]:
        print("Usage: {} [ history | next | once | pending "
              "| systemd | info [ open ] ]"
              .format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    temp_file = temp_file_path()
    if not temp_file:
        print("{} seems not to be running"
              .format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "info":
        display_wallpaper_info()
        sys.exit()
    action = sys.argv[1]
    if action == "blacklist":
        blacklist_wallpaper()
        action = "next"
    data = {}
    if action == "next":
        choose_wallpaper_wrapper(temp_file)
        sys.exit()
    with open(temp_file, "r") as f:
        data = yaml.load(f)
    if action == "history":
        print("\n".join(data["history"]))
    elif action == "pending":
        print("\n".join(data["pictures"]))
    sys.exit()


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


def display_wallpaper_info():
    with open("{}/current_wallpaper"
              .format(BASE_CACHE_PATH), "r") as f:
        infos = f.readlines()[1:]
    print("".join(infos))
    if len(sys.argv) > 2 and sys.argv[2] == "open" and \
       len(infos) == 2:
        url = infos[1].strip()
        if url != "":
            subprocess.run(["gio", "open", url])


def get_screen_config():
    n = subprocess.run("xrandr -q | grep '*' | wc -l",
                       check=True, shell=True,
                       stdout=subprocess.PIPE).stdout.decode()
    sp = subprocess.run("xrandr -q | head -n1",
                        check=True, shell=True,
                        stdout=subprocess.PIPE).stdout.decode()
    s = re.match(".*, current ([0-9]+) x .*", sp.strip())
    return (n.strip(), s[1])


def open_for_me_only(path, flags):
    return os.open(path, flags, mode=0o600)


def temp_file_path():
    try:
        with open("{}/temp".format(BASE_CACHE_PATH), "r") as f:
            temp_file = f.readline()
    except FileNotFoundError:
        return None
    if os.path.exists(temp_file):
        return temp_file
    return None


def set_mate_wallpaper(path, make_ld_copy=True):
    subprocess.run(["gsettings", "set", "org.mate.background",
                    "picture-filename", path])
    subprocess.run(["gsettings", "set", "org.mate.background",
                    "picture-options", "zoom"])
    if make_ld_copy:
        shutil.copy(path, LIGHTDM_CACHE_PATH)


def choose_wallpaper(collecs):
    if len(collecs["pictures"]) == 0:
        sys.exit(0)
    wp = collecs["data"][collecs["pictures"][0]]
    # screen_config = get_screen_config()
    with open("{}/current_wallpaper".format(BASE_CACHE_PATH),
              "w", opener=open_for_me_only) as f:
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


def choose_wallpaper_wrapper(collecs_file):
    with open(collecs_file, "r") as f:
        data = yaml.load(f)
    lp, wp = choose_wallpaper(data)
    data["pictures"].remove(wp)
    data["history"].append(wp)
    with open(collecs_file, "w") as f:
        yaml.dump(data, f, explicit_start=True,
                  default_flow_style=False)
    set_mate_wallpaper(lp)


def kill_daemon(_signo, _stack_frame):
    sys.exit(0)


def wallpaper_daemon(sleep_time):
    signal.signal(signal.SIGTERM, kill_daemon)
    f = tempfile.mkstemp(suffix="_chwall")
    with open(f[1], "w") as tmp:
        yaml.dump(data, tmp, explicit_start=True,
                  default_flow_style=False)
    os.close(f[0])
    temp_file = f[1]
    del f
    print("Start loop")
    temp_info_file = "{}/temp".format(BASE_CACHE_PATH)
    with open(temp_info_file, "w") as f:
        f.write(temp_file)
    error_code = 0
    try:
        while True:
            choose_wallpaper_wrapper(temp_file)
            time.sleep(sleep_time)
    except (KeyboardInterrupt, SystemExit):
        print("Kthxbye!")
    except Exception as e:
        print("{}: {}".format(type(e).__name__, e), file=sys.stderr)
        error_code = 1
    finally:
        os.unlink(temp_file)
        os.unlink(temp_info_file)
        sys.exit(error_code)


if __name__ == "__main__":
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

    if "lightdm_wall" in config["general"]:
        LIGHTDM_CACHE_PATH = os.path.expanduser(
            config["general"]["lightdm_wall"])

    if "sources" not in config["general"]:
        config["general"]["sources"] = [
            "bing", "unsplash", "nasa", "local"]

    if "sleep" not in config["general"]:
        config["general"]["sleep"] = 10 * 60

    if len(sys.argv) > 1 and sys.argv[1] != "once":
        daemon_client()
    # Daemon client will directly exits when done. Thus if we are here,
    # we only have to set wallpaper once or start the daemon

    # be sure to set the right file as background when starting chwall
    set_mate_wallpaper(LIGHTDM_CACHE_PATH, False)

    data = build_picture_lists(config)

    if len(sys.argv) > 1 and sys.argv[1] == "once":
        wp = choose_wallpaper(data)
        set_mate_wallpaper(wp[0])
    else:
        wallpaper_daemon(config["general"]["sleep"])
