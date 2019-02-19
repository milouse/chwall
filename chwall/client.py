#!/usr/bin/env python3

import os
import sys
import time
import yaml
import subprocess


# chwall imports
from chwall.daemon import notify_daemon_if_any
from chwall.utils import BASE_CACHE_PATH, read_config, systemd_file
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper, \
                             ChwallEmptyListError


chwall_commands = ["blacklist", "current", "history", "info", "next",
                   "once", "pending", "previous", "purge", "quit", "systemd"]


def display_wallpaper_info():
    with open("{}/current_wallpaper"
              .format(BASE_CACHE_PATH), "r") as f:
        infos = f.readlines()[1:]
    print("".join(infos))
    with open("{}/last_change".format(BASE_CACHE_PATH), "r") as f:
        try:
            last_change = int(time.time()) - int(f.read().strip())
        except ValueError:
            last_change = -1
    if last_change > 60:
        last_change_m = int(last_change / 60)
        last_change = last_change % 60
        print("Last change: {} minute(s) {}s ago"
              .format(last_change_m, last_change))
    else:
        print("Last change: {}s ago".format(last_change))
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
        display_wallpaper_info()
        return True

    if action == "blacklist":
        blacklist_wallpaper()
        action = "next"
    if action in ["next", "once", "previous"]:
        direction = False
        if action == "previous":
            direction = True
        try:
            pick_wallpaper(config, direction)
            notify_daemon_if_any()
            return True
        except ChwallEmptyListError as e:
            print(e, file=sys.stderr)
            action = "quit"
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
        print("{} seems not to be running"
              .format(sys.argv[0]), file=sys.stderr)
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
