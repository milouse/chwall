#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess
from xdg.BaseDirectory import xdg_data_home

# chwall imports
from chwall.daemon import notify_daemon_if_any, daemon_info, daemonize
from chwall.utils import VERSION, BASE_CACHE_PATH, read_config, \
                         ServiceFileManager
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper
from chwall.gui.app import generate_desktop_file
from chwall.gui.preferences import PrefDialog

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


SUBCOMMAND_ALIASES = {
    "preferences": "options",
    "current": "status",
    "info": "status",
    "once": "next"
}


class ChwallClient:
    def __init__(self):
        if len(sys.argv) > 1 and self._run():
            sys.exit()
        self.cmd_help("__from_error__")
        sys.exit(1)

    def _parse_argv(self):
        action = None
        opts = []
        for a in sys.argv[1:]:
            arg = a.lower()
            if arg in ["help", "--help", "-h"]:
                if action == "help":
                    continue
                if action is not None:
                    opts.insert(0, action)
                action = "help"
                continue
            elif arg in ["version", "--version", "-v"]:
                return "version", []
            if action is None:
                action = arg
            else:
                opts.append(arg)
        return action, opts

    def _run(self):
        action, opts = self._parse_argv()
        if action is None:
            return False
        action = SUBCOMMAND_ALIASES.get(action, action)
        if action == "help":
            if len(opts) == 0:
                self.cmd_help()
                return True
            subcmd = SUBCOMMAND_ALIASES.get(opts[0], opts[0])
            action = getattr(self, "help_{}".format(subcmd), None)
            if action is None:
                self.help_generic(subcmd)
                return True
            opts = []
        else:
            action = getattr(self, "cmd_{}".format(action), None)
            if action is None:
                return False
        action(*opts)
        # By default, return success. It's up to each method to exit with error
        # sooner when something goes wrong
        return True

    def cmd_version(self, *opts):
        print(VERSION)

    def help_generic(self, subcmd):
        print(_("Usage: {}").format(sys.argv[0] + " " + subcmd))
        print(_("""
Sadly, no specific help message for this subcommand yet.
"""))

    def cmd_help(self, *opts):
        out = sys.stdout
        if len(opts) != 0 and opts[0] == "__from_error__":
            out = sys.stderr
        print(_("USAGE"), file=out)
        print("       {} <command>".format(sys.argv[0]), file=out)
        print("       {} help [ <command> ]".format(sys.argv[0]), file=out)
        print("", file=out)
        print(_("COMMANDS"), file=out)
        for cmd in dir(self):
            if cmd != "cmd_help" and cmd.startswith("cmd_"):
                print("       " + cmd.split("_")[1], file=out)

    def help_systemd(self):
        print(_("Usage: {}").format(sys.argv[0] + " systemd"))
        print(_("""
Display a systemd service file exemple, which can be used to
automatically start chwall daemon when your user session starts.
"""))

    def cmd_systemd(self, *opts):
        sfm = ServiceFileManager()
        write = False
        if len(opts) != 0 and opts[0] == "write":
            write = True
        sfm.systemd_service_file(write)

    def cmd_desktop(self, *opts):
        out = "print"
        if len(opts) >= 1:
            if opts[0] == "write":
                out = os.path.join(xdg_data_home, "applications",
                                   "chwall-app.desktop")
            else:
                out = opts[0].strip()
        if len(opts) == 2:
            localedir = opts[1]
        else:
            localedir = gettext.bindtextdomain("chwall")
        generate_desktop_file(localedir, out)

    def cmd_options(self, *opts):
        prefwin = PrefDialog(None, 0, read_config())
        prefwin.run()
        prefwin.destroy()

    def help_detach(self):
        print(_("Usage: {}").format(sys.argv[0] + " detach [ app | icon ]"))
        print(_("""
Detach from terminal and start either the main app or the system tray icon.

By default, this command will start the main app if no argument is given.
"""))

    def cmd_detach(self, *opts):
        if len(opts) != 1 or opts[0] == "":
            opts = ["app"]
        elif opts[0] not in ["app", "icon"]:
            sys.exit(1)
        daemonize()
        cmd = "chwall-{}".format(opts[0])
        os.execl("/usr/bin/{}".format(cmd), cmd)

    def help_status(self):
        print(_("Usage: {}").format(sys.argv[0] + " status [ open ]"))
        print(_("""
Display the current wallpaper information.

If the optional `open' keyword is given, the original resource will be opened,
using the best dedicated tool for it (web browser, picture viewer...).
"""))

    def cmd_status(self, *opts):
        with open("{}/current_wallpaper"
                  .format(BASE_CACHE_PATH), "r") as f:
            infos = f.readlines()[1:]
        print("".join(infos))
        dinfo = daemon_info(read_config())
        print(dinfo["last-change-label"])
        if len(opts) != 0 and opts[0] == "open" and len(infos) >= 2:
            url = infos[1].strip()
            if url != "":
                subprocess.run(["gio", "open", url])

    def cmd_blacklist(self, *opts):
        blacklist_wallpaper()
        self.cmd_next()

    def _pick_wall(self, direction=False):
        if pick_wallpaper(read_config(), direction) is None:
            print(_("Unable to pick wallpaper this time. Please, try again."),
                  file=sys.stderr)
            self.cmd_quit()
        else:
            notify_daemon_if_any()

    def cmd_next(self, *opts):
        self._pick_wall()

    def cmd_previous(self, *opts):
        self._pick_wall(True)

    def cmd_quit(self, *opts):
        # 15 == signal.SIGTERM
        notify_daemon_if_any(15)

    def cmd_purge(self, *opts):
        road_map = "{}/roadmap".format(BASE_CACHE_PATH)
        if os.path.exists(road_map):
            os.unlink(road_map)

    def _road_map(self):
        road_map = "{}/roadmap".format(BASE_CACHE_PATH)
        if not os.path.exists(road_map):
            print(_("No roadmap has been created yet"), file=sys.stderr)
            sys.exit(1)
        data = {}
        with open(road_map, "r") as f:
            data = yaml.safe_load(f)
        return data

    def cmd_history(self, *opts):
        data = self._road_map()
        print("\n".join(data["history"]))

    def cmd_pending(self, *opts):
        data = self._road_map()
        print("\n".join(data["pictures"]))


if __name__ == "__main__":
    ChwallClient()
