import os
import re
import yaml
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


VERSION = "0.3"
BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)


def get_screen_config():
    try:
        screen_data = subprocess.run(["xrandr", "-q", "-d", ":0"],
                                     check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return None
    screen_info = screen_data.stdout.decode()
    s = re.match(".*, current ([0-9]+) x ([0-9]+).*", screen_info)
    if s is None:
        width = 0
    else:
        width = int(s[1])
        height = int(s[2])
        ratio = round(width / height, 2)
    return (screen_info.count("*"), width, height, ratio)


def get_wall_config(path):
    try:
        size_data = subprocess.run(["identify", "-format", "%wx%h", path],
                                   check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return None
    size = size_data.stdout.decode().split('x')
    try:
        width = int(size[0])
        height = int(size[1])
        ratio = round(width / height, 2)
        size_t = (width, height, ratio)
    except ValueError:
        return None
    return size_t


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
    if "notify" not in config["general"]:
        config["general"]["notify"] = False
    return config


def write_config(config):
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    with open(config_file, "w") as f:
        f.write(yaml.dump(config, default_flow_style=False,
                          explicit_start=True))


def cleanup_cache():
    pic_cache = "{}/pictures".format(BASE_CACHE_PATH)
    if not os.path.exists(pic_cache):
        return 0
    try:
        files_data = subprocess.run(
            ["find", pic_cache, "-type", "f", "-size", "0"],
            check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return 0
    empty_files = files_data.stdout.decode().strip()
    if empty_files == "":
        return 0
    for ref in empty_files.split("\n"):
        os.unlink(ref.strip())
    return len(empty_files)


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
