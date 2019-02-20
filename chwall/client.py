#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess

# chwall imports
from chwall.daemon import notify_daemon_if_any, daemon_info
from chwall.utils import BASE_CACHE_PATH, read_config, systemd_file
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


chwall_commands = ["blacklist", "current", "history", "info", "next",
                   "once", "pending", "previous", "purge", "quit", "systemd"]


def display_wallpaper_info(config):
    with open("{}/current_wallpaper"
              .format(BASE_CACHE_PATH), "r") as f:
        infos = f.readlines()[1:]
    print("".join(infos))
    dinfo = daemon_info(config)
    print(dinfo["last-change-label"])
    if len(sys.argv) > 2 and sys.argv[2] == "open" and \
       len(infos) >= 2:
        url = infos[1].strip()
        if url != "":
            subprocess.run(["gio", "open", url])


def print_help():
    filtered_cmd = chwall_commands.copy()
    filtered_cmd.remove("systemd")
    filtered_cmd.remove("info")
    filtered_cmd.remove("current")
    print("Usage: {} ( {} )".format(sys.argv[0], " | ".join(filtered_cmd)),
          file=sys.stderr)
    print("       {} ( current | info ) [ open ]".format(sys.argv[0]),
          file=sys.stderr)
    print("       {} systemd".format(sys.argv[0]), file=sys.stderr)


def run_client(config):
    if sys.argv[1] not in chwall_commands:
        print_help()
        return False
    action = sys.argv[1]
    if action == "systemd":
        systemd_file()
        return True
    elif action in ["current", "info"]:
        display_wallpaper_info(config)
        return True

    if action == "blacklist":
        blacklist_wallpaper()
        action = "next"
    if action in ["next", "once", "previous"]:
        direction = False
        if action == "previous":
            direction = True
        if pick_wallpaper(config, direction) is None:
            print(_("Unable to pick wallpaper this time. Please, try again."),
                  file=sys.stderr)
            action = "quit"
        else:
            notify_daemon_if_any()
            return True
    if action == "quit":
        # 15 == signal.SIGTERM
        return notify_daemon_if_any(15)

    data = {}
    road_map = "{}/roadmap".format(BASE_CACHE_PATH)
    if action == "purge":
        if os.path.exists(road_map):
            os.unlink(road_map)
        return True
    if not os.path.exists(road_map):
        print(_("{progname} seems not to be running")
              .format(progname=sys.argv[0]), file=sys.stderr)
        return False
    with open(road_map, "r") as f:
        data = yaml.load(f)
    if action == "history":
        print("\n".join(data["history"]))
    elif action == "pending":
        print("\n".join(data["pictures"]))
    return True


def client():
    if len(sys.argv) == 1:
        print_help()
        return 1
    config = read_config()
    if run_client(config):
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(client())
