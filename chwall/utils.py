import os
import re
import yaml
import hashlib
import logging
import subprocess
from xdg.BaseDirectory import xdg_cache_home, xdg_config_home

import gettext  # noqa: E402
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


BASE_CACHE_PATH = f"{xdg_cache_home}/chwall"


def get_screen_config():
    display = read_config()["general"].get("display", ":0")
    try:
        screen_data = subprocess.run(
            ["xrandr", "-q", "-d", display],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError:
        return (1, 0, 0, 1, display)
    screen_info = screen_data.stdout
    s = re.match(".*, current ([0-9]+) x ([0-9]+).*", screen_info)
    if s is None:
        return (1, 0, 0, 1, display)
    width = int(s[1])
    height = int(s[2])
    ratio = round(width / height, 2)
    return (screen_info.count("*"), width, height, ratio, display)


def get_wall_config(path):
    try:
        size_data = subprocess.run(
            ["identify", "-format", "%wx%h", path],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError:
        return
    size = size_data.stdout.split("x")
    try:
        width = int(size[0])
        height = int(size[1])
        ratio = round(width / height, 2)
        size_t = (width, height, ratio)
    except ValueError:
        return
    return size_t


def migrate_systemd_service_files():
    sfm = ServiceFileManager()
    # Detect old deprecated enabled service
    old_enabled_service_file = os.path.join(
        sfm.systemd_base_path, "default.target.wants", "chwall.service"
    )
    if not os.path.exists(old_enabled_service_file):
        return
    # Disable old service
    subprocess.run(
        ["systemctl", "--user", "disable", "chwall.service"]
    )
    # Enable directly the new timer
    sfm.systemd_service_file(write=True, force=True)
    subprocess.run(
        ["systemctl", "--user", "enable", "chwall.timer", "--now"]
    )


def migrate_block_list_files():
    old_block_list_file = f"{BASE_CACHE_PATH}/blacklist.yml"
    if not os.path.exists(old_block_list_file):
        # Nothing to do
        return
    block_list = []
    block_list_file = f"{BASE_CACHE_PATH}/block_list.yml"
    if os.path.exists(block_list_file):
        with open(block_list_file, "r") as f:
            block_list = yaml.safe_load(f) or []
    with open(old_block_list_file, "r") as f:
        block_list += yaml.safe_load(f) or []
    block_list = list(set(block_list))
    with open(block_list_file, "w") as f:
        yaml.dump(block_list, f, explicit_start=True,
                  default_flow_style=False)
    os.unlink(old_block_list_file)


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
    if config["general"].get("desktop") == "nitrogen":
        config["general"]["desktop"] = "feh"
    migrate_block_list_files()
    migrate_systemd_service_files()
    return config


def read_config():
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    pic_cache = f"{BASE_CACHE_PATH}/pictures"
    if not os.path.exists(pic_cache):
        os.makedirs(pic_cache)

    config.setdefault("general", {})
    config["general"].setdefault("sources", ["bing"])
    config["general"].setdefault("sleep", 10 * 60)
    config["general"].setdefault("notify", False)
    config["general"].setdefault(
        "favorites_path", f"{BASE_CACHE_PATH}/favorites"
    )
    return migrate_config(config)


def write_config(config):
    config_file = os.path.join(xdg_config_home, "chwall.yml")
    with open(config_file, "w") as f:
        f.write(yaml.dump(config, default_flow_style=False,
                          explicit_start=True))


# This function may be called from a gui app and pass a widget or other stuff
# as arguments
def reset_pending_list(*args):
    road_map = f"{BASE_CACHE_PATH}/roadmap"
    if os.path.exists(road_map):
        os.unlink(road_map)


def is_broken_picture(picture):
    common_sums = [
        # reddit broken picture
        "35a0932c61e09a8c1cad9eec75b67a03602056463ed210310d2a09cf0b002ed5"
    ]
    check = hashlib.sha256()
    with open(picture, "rb") as f:
        check.update(f.read())
    return check.hexdigest() in common_sums


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
        comp = f"/usr/bin/chwall-{component}"
        module = f"chwall.gui.{component}"
    # Is it an installed version?
    force_native_path = os.getenv("CHWALL_NATIVE_PATH", None)
    if os.path.exists(comp) or force_native_path:
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
    return f"python -m {module}\n{workdirkey}={local_path}"


def detect_systemd():
    try:
        sdata = subprocess.run(
            ["systemctl", "--version"],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError:
        return
    except FileNotFoundError:
        return
    return sdata.stdout.split("\n")[0]


def open_externally(url):
    if url.startswith("http"):
        browser_cmd = read_config()["general"].get(
            "web_browser_cmd", "gio open \"{url}\""
        ).format(url=url)
        subprocess.Popen(browser_cmd, shell=True)
    else:
        subprocess.Popen(["gio", "open", url])


class ServiceFileManager:
    def __init__(self):
        self.systemd_version = detect_systemd()
        self.systemd_base_path = os.path.join(
            xdg_config_home, "systemd", "user")
        self.systemd_service_file_path = os.path.join(
            self.systemd_base_path, "chwall.service")
        self.systemd_timer_file_path = os.path.join(
            self.systemd_base_path, "chwall.timer")
        self.autostart_dir = os.path.join(xdg_config_home, "autostart")

    def service_file_status(self):
        status = {
            "enabled": False,
            "type": "xdg"
        }
        if self.systemd_service_file_exists():
            status["type"] = "systemd"
            status["enabled"] = self.systemd_service_file_exists(True)
        else:
            status["enabled"] = self.xdg_autostart_file_exists()
        return status

    def systemd_service_file_exists(self, check_enabled=False):
        if check_enabled:
            timer_file = os.path.join(
                self.systemd_base_path, "timers.target.wants", "chwall.timer"
            )
            return os.path.exists(timer_file)
        return os.path.isfile(self.systemd_service_file_path) and \
            os.path.isfile(self.systemd_timer_file_path)

    def systemd_service_file(self, write=False, force=False):
        config = read_config()
        display = config["general"].get("display", ":0")
        app_exec = get_binary_path("client", arguments="next no_restart")
        file_content = f"""\
[Unit]
Description=Simple wallpaper changer
After=network.target

[Service]
Type=simple
Environment=DISPLAY={display}
ExecStart={app_exec}

[Install]
WantedBy=default.target
"""
        sleep_time = int(config["general"]["sleep"])
        timer_content = f"""\
[Unit]
Description=Change wallpaper every {sleep_time} seconds
After=network.target

[Timer]
OnActiveSec={sleep_time}
OnUnitActiveSec={sleep_time}

[Install]
WantedBy=timers.target
"""
        if write is False:
            print("Service file:")
            print(file_content, end="")
            print("\nTimer file:")
            print(timer_content, end="")
            return
        if not force and self.systemd_service_file_exists():
            return
        self.remove_xdg_autostart_file("daemon")
        os.makedirs(self.systemd_base_path, exist_ok=True)
        with open(self.systemd_service_file_path, "w") as f:
            f.write(file_content)
        with open(self.systemd_timer_file_path, "w") as f:
            f.write(timer_content)
        subprocess.run(["systemctl", "--user", "daemon-reload"])

    def remove_systemd_service_file(self):
        self.systemd_service_toggle(False)
        if self.systemd_service_file_exists():
            os.unlink(self.systemd_service_file_path)
            os.unlink(self.systemd_timer_file_path)
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
        subprocess.run(["systemctl", "--user", cond, "chwall.timer"])

    def remove_xdg_autostart_file(self, component="daemon"):
        autostart_file = os.path.join(
            self.autostart_dir, f"chwall-{component}.desktop"
        )
        file_yet_exists = os.path.isfile(autostart_file)
        if file_yet_exists:
            os.remove(autostart_file)

    def _xdg_autostart_for_daemon(self, write=False):
        chwall_cmd = get_binary_path("daemon", target_type="xdg")
        app_name = _("Chwall Daemon")
        app_desc = _("Start Chwall Daemon")
        file_content = f"""\
[Desktop Entry]
Name={app_name}
Comment={app_desc}
Exec={chwall_cmd}
Icon=chwall
Terminal=false
Type=Application
X-MATE-Autostart-enabled=true
X-GNOME-Autostart-enabled=true
Categories=Utility;
StartupNotify=false
"""
        if write:
            self.remove_systemd_service_file()
        return file_content

    def _xdg_autostart_for_icon(self, component):
        chwall_cmd = get_binary_path(component, target_type="xdg")
        app_desc = _("Wallpaper Changer")
        return f"""\
[Desktop Entry]
Name=Chwall
Comment={app_desc}
Exec={chwall_cmd}
Icon=chwall
Terminal=false
Type=Application
X-MATE-Autostart-enabled=true
X-GNOME-Autostart-enabled=false
NotShowIn=GNOME;Pantheon;
Categories=GTK;TrayIcon;Utility;
"""

    def xdg_autostart_file(self, component, write=False):
        if component == "daemon":
            file_content = self._xdg_autostart_for_daemon(write)
        else:
            file_content = self._xdg_autostart_for_icon(component)

        if write is False:
            print(file_content, end="")
            return

        autostart_file = os.path.join(
            self.autostart_dir, f"chwall-{component}.desktop"
        )
        if os.path.isfile(autostart_file):
            return
        elif not os.path.isdir(self.autostart_dir):
            os.makedirs(self.autostart_dir)

        with open(autostart_file, "w") as f:
            f.write(file_content)

    def xdg_autostart_file_exists(self, component="daemon"):
        autostart_file = os.path.join(
            xdg_config_home, "autostart",
            f"chwall-{component}.desktop"
        )
        return os.path.isfile(autostart_file)

    def _build_translations_for_desktop_file(self, localedir):
        lang_attrs = {
            "gname": [],
            "comment": [],
            "next_name": [],
            "previous_name": [],
            "favorite_name": [],
            "block_name": []
        }
        for lang in sorted(os.listdir(localedir)):
            if lang in ["chwall.pot", "en"]:
                continue
            domain_file = os.path.join(
                localedir, lang, "LC_MESSAGES", "chwall.mo"
            )
            if not os.path.exists(domain_file):
                continue
            glng = gettext.translation(
                "chwall", localedir=localedir, languages=[lang]
            )
            glng.install()
            _ = glng.gettext
            label = _("Wallpaper Changer")
            lang_attrs["gname"].append(f"GenericName[{lang}]={label}")
            label = _("Main window of the Chwall wallpaper changer")
            lang_attrs["comment"].append(f"Comment[{lang}]={label}")
            label = _("Next wallpaper")
            lang_attrs["next_name"].append(f"Name[{lang}]={label}")
            label = _("Previous wallpaper")
            lang_attrs["previous_name"].append(f"Name[{lang}]={label}")
            label = _("Save as favorite")
            lang_attrs["favorite_name"].append(f"Name[{lang}]={label}")
            label = _("Put on block list")
            lang_attrs["block_name"].append(f"Name[{lang}]={label}")
        return lang_attrs

    def _build_action_block(self, name, lang_attrs):
        label = name.capitalize()
        block_cmd = get_binary_path("client", "xdg", name)
        block = [f"""

[Desktop Action {label}]
Exec={block_cmd}
Name={label} wallpaper"""]
        for line in lang_attrs[name + "_name"]:
            block.append(line)
        return "\n".join(block)

    def generate_desktop_file(self, localedir="./locale",
                              out="chwall-app.desktop"):
        df_content = ["[Desktop Entry]", "Name=Chwall",
                      "GenericName=Wallpaper Changer"]
        lang_attrs = self._build_translations_for_desktop_file(localedir)
        for line in lang_attrs["gname"]:
            df_content.append(line)
        df_content.append(
            "Comment=Main window of the Chwall wallpaper changer"
        )
        for line in lang_attrs["comment"]:
            df_content.append(line)
        df_content = "\n".join(df_content)
        app_exec = get_binary_path("app", "xdg")
        df_content += f"""
Exec={app_exec}
Icon=chwall
Terminal=false
Type=Application
Categories=GTK;GNOME;Utility;
StartupNotify=false
Actions=Next;Previous;Favorite;Block;"""
        df_content += self._build_action_block("next", lang_attrs)
        df_content += self._build_action_block("previous", lang_attrs)
        df_content += self._build_action_block("favorite", lang_attrs)
        df_content += self._build_action_block("block", lang_attrs)

        if out == "print":
            print(df_content)
        else:
            with open(out, "w") as f:
                f.write(df_content)
