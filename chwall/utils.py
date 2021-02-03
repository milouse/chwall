import os
import re
import yaml
import logging
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home


BASE_CACHE_PATH = "{}/chwall".format(xdg_cache_home)


def get_screen_config():
    display = read_config()["general"].get("display", ":0")
    try:
        screen_data = subprocess.run(["xrandr", "-q", "-d", display],
                                     check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return (1, 0, 0, 1, display)
    screen_info = screen_data.stdout.decode()
    s = re.match(".*, current ([0-9]+) x ([0-9]+).*", screen_info)
    if s is None:
        width = 0
    else:
        width = int(s[1])
        height = int(s[2])
        ratio = round(width / height, 2)
    return (screen_info.count("*"), width, height, ratio, display)


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


def migrate_config(config):
    if "local" in config:
        if isinstance(config["local"], list):
            config["local"] = {"paths": config["local"]}
        elif "pathes" in config["local"]:
            config["local"] = {"paths": config["local"]["pathes"]}
    if "bing" in config and isinstance(config["bing"], list):
        config["bing"] = {"locales": config["bing"]}
    if "deviantart" in config and isinstance(config["deviantart"], list):
        config["deviantart"] = {"collections": config["deviantart"]}
    ld_path = config["general"].get("lightdm_wall")
    if ld_path is not None and ld_path != "":
        del config["general"]["lightdm_wall"]
        config["general"]["shared"] = {"path": ld_path}
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

    config.setdefault("general", {})
    config["general"].setdefault("sources", ["bing", "natgeo"])
    config["general"].setdefault("sleep", 10 * 60)
    config["general"].setdefault("notify", False)
    config["general"].setdefault(
        "favorites_path", "{}/favorites".format(BASE_CACHE_PATH)
    )
    return migrate_config(config)


def write_config(config):
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    with open(config_file, "w") as f:
        f.write(yaml.dump(config, default_flow_style=False,
                          explicit_start=True))


# This function may be called from a gui app and pass a widget or other stuff
# as arguments
def reset_pending_list(*opts):
    road_map = "{}/roadmap".format(BASE_CACHE_PATH)
    if os.path.exists(road_map):
        os.unlink(road_map)


def cleanup_cache(clear_all=False):
    pic_cache = "{}/pictures".format(BASE_CACHE_PATH)
    if not os.path.exists(pic_cache):
        return 0
    deleted = 0
    for pic in os.scandir(pic_cache):
        if clear_all or pic.stat().st_size == 0:
            os.unlink(pic.path)
            deleted += 1
    return deleted


def get_logger(name):
    if name == "__main__":
        name = "chwall"
    level_str = read_config()["general"].get("log_level", "WARNING")
    level = getattr(logging, level_str.upper(), None)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(name)


def get_binary_path(component, target_type="systemd", arguments=""):
    if component == "client":
        comp = "/usr/bin/chwall"
        module = "chwall.client"
    elif component == "daemon":
        comp = "/usr/bin/chwall-daemon"
        module = "chwall.daemon"
    else:
        comp = "/usr/bin/chwall-{}".format(component)
        module = "chwall.gui." + component
    # Is it an installed version?
    test_env = os.getenv("CHWALL_FAKE_INSTALL", "pass")
    if (test_env == "pass" and os.path.exists(comp)) or test_env == "exists":
        if arguments != "":
            comp += " " + arguments
        return comp
    if arguments != "":
        module += " " + arguments
    if target_type == "xdg":
        workdirkey = "Path"
    else:
        # Systemd is the default
        workdirkey = "WorkingDirectory"
    local_path = os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    return "python -m {0}\n{1}={2}".format(module, workdirkey, local_path)


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
        display = read_config()["general"].get("display", ":0")
        file_content = """\
[Unit]
Description = Simple wallpaper changer
After=network.target

[Service]
Type=simple
Environment=DISPLAY={display}
ExecStart={app_exec}

[Install]
WantedBy=default.target
""".format(display=display, app_exec=get_binary_path("daemon", arguments="-D"))
        if write is False:
            print(file_content, end="")
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

    def xdg_autostart_file(self, component, app_name, app_desc, write=False):
        chwall_cmd = get_binary_path(component, target_type="xdg")
        file_content = """\
[Desktop Entry]
Name={app_name}
Comment={app_desc}
Exec={app_exec}
Icon=chwall
Terminal=false
Type=Application
X-MATE-Autostart-enabled=true
""".format(app_name=app_name, app_desc=app_desc, app_exec=chwall_cmd)
        if component == "daemon":
            file_content += """\
X-GNOME-Autostart-enabled=true
Categories=Utility;
StartupNotify=false
"""
        elif component == "icon":
            file_content += """\
X-GNOME-Autostart-enabled=false
NotShowIn=GNOME
Categories=GTK;TrayIcon;Utility;
"""
        if write is False:
            print(file_content, end="")
            return
        autostart_file = os.path.join(
            self.autostart_dir, "chwall-{}.desktop".format(component))
        if os.path.isfile(autostart_file):
            return
        self.remove_systemd_service_file()
        if not os.path.isdir(self.autostart_dir):
            os.makedirs(self.autostart_dir)
        with open(autostart_file, "w") as f:
            f.write(file_content)

    def xdg_autostart_file_exists(self, component="daemon"):
        autostart_file = os.path.join(
            xdg_config_home, "autostart",
            "chwall-{}.desktop".format(component))
        return os.path.isfile(autostart_file)
