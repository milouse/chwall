#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess

# chwall imports
from chwall.daemon import notify_daemon_if_any, daemon_info, daemonize
from chwall.utils import BASE_CACHE_PATH, read_config, systemd_file
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


chwall_commands = ["blacklist", "current", "detach", "history", "info",
                   "next", "once", "pending", "previous", "purge",
                   "quit", "status", "systemd"]


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
    filtered_cmd.remove("status")
    filtered_cmd.remove("detach")
    print("Usage: {} ( {} )".format(sys.argv[0], " | ".join(filtered_cmd)),
          file=sys.stderr)
    print("       {} ( current | info | status ) [ open ]".format(sys.argv[0]),
          file=sys.stderr)
    print("       {} systemd".format(sys.argv[0]), file=sys.stderr)


def run_client():
    if len(sys.argv) == 1:
        print_help()
        sys.exit(1)
    config = read_config()
    if sys.argv[1] not in chwall_commands:
        print_help()
        sys.exit(1)

    action = sys.argv[1]
    if action == "systemd":
        systemd_file()
        sys.exit(0)
    elif action == "detach":
        if len(sys.argv) < 3:
            sys.exit(1)
        comp = sys.argv[2].strip()
        if comp == "" or comp not in ["app", "icon"]:
            sys.exit(1)
        daemonize()
        cmd = "chwall-{}".format(comp)
        os.execl("/usr/bin/{}".format(cmd), cmd)
        # Subprocess has now replaced current process, thus no need to exit or
        # return from here.
    elif action in ["current", "info", "status"]:
        display_wallpaper_info(config)
        sys.exit(0)

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
            sys.exit(0)
    if action == "quit":
        # 15 == signal.SIGTERM
        return notify_daemon_if_any(15)

    data = {}
    road_map = "{}/roadmap".format(BASE_CACHE_PATH)
    if action == "purge":
        if os.path.exists(road_map):
            os.unlink(road_map)
        sys.exit(0)
    if not os.path.exists(road_map):
        print(_("{progname} seems not to be running")
              .format(progname=sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    with open(road_map, "r") as f:
        data = yaml.load(f)
    if action == "history":
        print("\n".join(data["history"]))
    elif action == "pending":
        print("\n".join(data["pictures"]))
    sys.exit(0)


if __name__ == "__main__":
    run_client()
