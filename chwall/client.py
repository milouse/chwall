#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess


# chwall imports
from chwall.utils import BASE_CACHE_PATH, read_config
from chwall.wallpaper import pick_wallpaper, ChwallEmptyListError


chwall_commands = ["blacklist", "current", "history", "info", "next",
                   "once", "pending", "quit", "systemd"]


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


def print_help():
    filtered_cmd = chwall_commands.copy()
    filtered_cmd.remove("once")
    filtered_cmd.remove("systemd")
    filtered_cmd.remove("info")
    filtered_cmd.remove("current")
    print("Usage: {} [ {} ]".format(sys.argv[0], " | ".join(filtered_cmd)),
          file=sys.stderr)
    print("       {} [ once | systemd ]".format(sys.argv[0]), file=sys.stderr)
    print("       {} [ current | info ] [ open ]".format(sys.argv[0]),
          file=sys.stderr)


def run_client(config):
    if sys.argv[1] == "systemd":
        # Is it an installed version?
        if os.path.exists("/usr/bin/chwall-daemon"):
            chwall_cmd = "/usr/bin/chwall-daemon"
        else:
            chwall_cmd = "{0}/chwall.py\nWorkingDirectory={0}".format(
                os.path.realpath(
                    os.path.join(os.path.dirname(__file__), "..")))
        print("""
[Unit]
Description = Simple wallpaper changer
After=network.target

[Service]
Type=forking
ExecStart={command}

[Install]
WantedBy=default.target
""".strip().format(command=chwall_cmd))
        return True
    action = sys.argv[1]
    if action in ["current", "info"]:
        display_wallpaper_info()
        return True
    if action == "blacklist":
        blacklist_wallpaper()
        action = "next"
    if action in ["next", "once"]:
        try:
            pick_wallpaper(config)
            return True
        except ChwallEmptyListError as e:
            print(e, file=sys.stderr)
            action = "quit"
        except Exception:
            return False
    if action == "quit":
        pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
        if not os.path.exists(pid_file):
            return False
        pid = None
        with open(pid_file, "r") as f:
            pid = f.read().strip()
        print("Kill process {}".format(pid))
        # 15 == signal.SIGTERM
        os.kill(int(pid), 15)
        return True
    data = {}
    road_map = "{}/roadmap".format(BASE_CACHE_PATH)
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
    elif action not in chwall_commands:
        print_help()
        return False
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
