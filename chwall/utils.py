import os
import re
import yaml
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


VERSION = "0.3"
BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)


def get_screen_config():
    try:
        n = subprocess.run("xrandr -q | grep '*' | wc -l",
                           check=True, shell=True,
                           stdout=subprocess.PIPE).stdout.decode()
        sp = subprocess.run("xrandr -q | head -n1",
                            check=True, shell=True,
                            stdout=subprocess.PIPE).stdout.decode()
    except subprocess.CalledProcessError:
        return None
    s = re.match(".*, current ([0-9]+) x .*", sp.strip())
    try:
        size = (int(n.strip()), int(s[1]))
    except ValueError:
        return None
    return size


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
        config["general"]["sources"] = ["bing", "natgeo"]
    if "sleep" not in config["general"]:
        config["general"]["sleep"] = 10 * 60
    return config


def systemd_file(write=False):
    # Is it an installed version?
    if os.path.exists("/usr/bin/chwall-daemon"):
        chwall_cmd = "/usr/bin/chwall-daemon"
    else:
        chwall_cmd = "{0}/chwall.py\nWorkingDirectory={0}".format(
            os.path.realpath(
                os.path.join(os.path.dirname(__file__), "..")))
    file_content = """
[Unit]
Description = Simple wallpaper changer
After=network.target

[Service]
Type=forking
ExecStart={command}

[Install]
WantedBy=default.target
""".strip().format(command=chwall_cmd)
    if write is False:
        print(file_content)
        return
    systemd_path = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(systemd_path, exist_ok=True)
    with open("{}/chwall.service".format("systemd_path"), "w") as f:
        f.write(file_content)
