import os
import re
import yaml
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


VERSION = "0.4.5"
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
    size = size_data.stdout.decode().split("x")
    try:
        width = int(size[0])
        height = int(size[1])
        ratio = round(width / height, 2)
        size_t = (width, height, ratio)
    except ValueError:
        return None
    return size_t


def is_list(obj):
    return type(obj).__name__ == "list"


def migrate_config(config):
    if "local" in config and is_list(config["local"]):
        config["local"] = {"paths": config["local"]}
    if "bing" in config and is_list(config["bing"]):
        config["bing"] = {"locales": config["bing"]}
    if "deviantart" in config and is_list(config["deviantart"]):
        config["deviantart"] = {"collections": config["deviantart"]}
    return config


def read_config():
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f) or {}
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
    return migrate_config(config)


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


def chwall_daemon_binary_path(component="daemon"):
    comp = "/usr/bin/chwall-{}".format(component)
    # Is it an installed version?
    if os.path.exists(comp):
        return comp
    local_path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), ".."))
    local_comp = "{}/chwall.py".format(local_path)
    if component != "daemon":
        local_comp = "{} {}".format(local_comp, component)
    return "{0}\nWorkingDirectory={1}".format(local_comp, local_path)


class ServiceFileManager:
    def __init__(self):
        self.systemd_version = None
        self.detect_systemd()
        self.systemd_base_path = os.path.join(
            xdg_config_home, "systemd", "user")
        self.systemd_service_file_path = os.path.join(
            self.systemd_base_path, "chwall.service")
        self.autostart_dir = os.path.join(xdg_config_home, "autostart")

    def detect_systemd(self):
        try:
            sdata = subprocess.run(["systemctl", "--version"],
                                   check=True, stdout=subprocess.PIPE)
        except subprocess.CalledProcessError:
            return
        except FileNotFoundError:
            return
        self.systemd_version = sdata.stdout.decode().split("\n")[0]

    def systemd_service_file_exists(self, check_enabled=False):
        if check_enabled:
            service_file = os.path.join(
                self.systemd_base_path, "default.target.wants",
                "chwall.service")
            return os.path.exists(service_file)
        return os.path.isfile(self.systemd_service_file_path)

    def systemd_service_file(self, write=False):
        chwall_cmd = chwall_daemon_binary_path()
        file_content = """
[Unit]
Description = Simple wallpaper changer
After=network.target

[Service]
Type=simple
ExecStart={command} -D

[Install]
WantedBy=default.target
""".strip().format(command=chwall_cmd)
        if write is False:
            print(file_content)
            return
        if self.systemd_service_file_exists():
            return
        self.remove_xdg_autostart_file("daemon")
        os.makedirs(self.systemd_base_path, exist_ok=True)
        with open(self.systemd_service_file_path, "w") as f:
            f.write(file_content)
        subprocess.run(["systemctl", "--user", "daemon-reload"])

    def remove_systemd_service_file(self):
        self.systemd_service_toggle(False)
        if self.systemd_service_file_exists():
            os.unlink(self.systemd_service_file_path)
            subprocess.run(["systemctl", "--user", "daemon-reload"])

    def systemd_service_toggle(self, enabled=True):
        already_enabled = self.systemd_service_file_exists(True)
        cond = None
        if not enabled and already_enabled:
            cond = "disable"
        elif enabled and not already_enabled:
            cond = "enable"
        if cond is None:
            return
        subprocess.run(["systemctl", "--user", cond, "chwall.service"])

    def remove_xdg_autostart_file(self, component="daemon"):
        autostart_file = os.path.join(
            self.autostart_dir, "chwall-{}.desktop".format(component))
        file_yet_exists = os.path.isfile(autostart_file)
        if file_yet_exists:
            os.remove(autostart_file)

    def xdg_autostart_file(self, app_name, app_desc, component="daemon"):
        autostart_file = os.path.join(
            self.autostart_dir, "chwall-{}.desktop".format(component))
        if os.path.isfile(autostart_file):
            return
        self.remove_systemd_service_file()
        if not os.path.isdir(self.autostart_dir):
            os.makedirs(self.autostart_dir)
        chwall_cmd = chwall_daemon_binary_path(component)
        file_content = """\
[Desktop Entry]
Name={app_name}
Comment={app_desc}
Exec={app_exec}
Icon=chwall
Terminal=false
Type=Application
X-MATE-Autostart-enabled=true""".format(app_name=app_name,
                                        app_desc=app_desc,
                                        app_exec=chwall_cmd)
        if component == "daemon":
            file_content += """
X-GNOME-Autostart-enabled=true
Categories=Utility;
StartupNotify=false
"""
        elif component == "icon":
            file_content += """
X-GNOME-Autostart-enabled=false
NotShowIn=GNOME
Categories=GTK;TrayIcon;Utility;
"""
        with open(autostart_file, "w") as f:
            f.write(file_content)

    def xdg_autostart_file_exists(self, component="daemon"):
        autostart_file = os.path.join(
            xdg_config_home, "autostart",
            "chwall-{}.desktop".format(component))
        return os.path.isfile(autostart_file)
