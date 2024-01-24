#!/usr/bin/env python3

import os
import sys
import json
import time
import yaml
import pkgutil
from importlib import import_module
from xdg.BaseDirectory import xdg_data_home

# chwall imports
from chwall import __version__
from chwall.daemon import notify_daemon_if_any, stop_daemon_if_any, \
                          daemon_info, daemonize
from chwall.utils import BASE_CACHE_PATH, read_config, \
                         reset_pending_list, open_externally, \
                         ServiceFileManager
from chwall.wallpaper import block_wallpaper, pick_wallpaper, \
                             favorite_wallpaper, current_wallpaper_info
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
    "once": "next",
    "kill": "quit"
}


class ChwallClient:
    def __init__(self, opts=sys.argv[1:]):
        self.argv = opts
        if len(self.argv) > 0 and self._run():
            sys.exit()
        self.cmd_help(stderr=True)
        sys.exit(1)

    def _parse_argv(self):
        action = None
        args = []
        for a in self.argv:
            arg = a.lower()
            if arg in ["help", "--help", "-h"]:
                if action == "help":
                    continue
                if action is not None:
                    args.insert(0, action)
                action = "help"
                continue
            elif arg in ["version", "--version", "-v"]:
                return "version", []
            if action is None:
                action = arg
            else:
                args.append(arg)
        return action, args

    def _run(self):
        action, args = self._parse_argv()
        if action is None:
            return False
        action = SUBCOMMAND_ALIASES.get(action, action)
        if action == "help":
            if len(args) == 0:
                self.cmd_help()
                return True
            subcmd = SUBCOMMAND_ALIASES.get(args[0], args[0])
            action = getattr(self, f"help_{subcmd}", None)
            if action is None:
                self.help_generic(subcmd)
                return True
            args = []
        else:
            action = getattr(self, f"cmd_{action}", None)
            if action is None:
                return False
        action(*args)
        # By default, return success. It's up to each method to exit with error
        # sooner when something goes wrong
        return True

    def cmd_version(self):
        print(__version__)

    def _print_usage(self, *subcmd):
        label = _("Usage:")
        print(" ".join([label, "chwall", subcmd[0]]))
        if len(subcmd) < 2:
            return
        pad = len(label)
        or_word = (_("or") + " ").rjust(pad)
        for other in subcmd[1:]:
            print(" ".join([or_word, "chwall", other]))

    def help_generic(self, subcmd):
        self._print_usage(subcmd)
        print(_("""
Sadly, no specific help message for this subcommand yet.
"""))

    def cmd_help(self, stderr=False):
        out = sys.stdout
        if stderr:
            out = sys.stderr
        print(_("USAGE"), file=out)
        print("       chwall <command>", file=out)
        print("       chwall help [ <command> ]\n", file=out)
        print(_("COMMANDS"), file=out)
        for cmd in dir(self):
            if cmd != "cmd_help" and cmd.startswith("cmd_"):
                print("       " + cmd.split("_")[1], file=out)

    def help_systemd(self):
        self._print_usage("systemd [ write ]")
        print(_("""
Display a systemd service file exemple, which can be used to
automatically start chwall daemon when your user session starts.

If ‘write’ is passed as second parameter, the resulting systemd service file
will be saved in .config/systemd/user/
"""))

    def cmd_systemd(self, subcmd="print"):
        sfm = ServiceFileManager()
        write = False
        if subcmd == "write":
            write = True
        sfm.systemd_service_file(write)

    def help_desktop(self):
        self._print_usage("desktop [ write ]")
        print(_("""
Display a launcher file example for your desktop, which can be used to start
chwall main app from your desktop applications menu.

If ‘write’ is passed as second parameter, the resulting desktop file
will be saved in .local/share/applications/
"""))

    def cmd_desktop(self, out="print", localedir=None):
        if out == "write":
            out = os.path.join(
                xdg_data_home, "applications", "chwall-app.desktop"
            )
        elif out != "print":
            out = out.strip()
        if localedir is None:
            localedir = gettext.bindtextdomain("chwall")
        generate_desktop_file(localedir, out)

    def help_options(self):
        self._print_usage("options", "preferences")
        print(_("""
Directly open the chwall preferences window.
"""))

    def cmd_options(self):
        prefwin = PrefDialog(None, 0)
        prefwin.run()
        prefwin.destroy()

    def help_detach(self):
        self._print_usage("detach [ app | icon | indicator ]")
        print(_("""
Detach from terminal and start either the main app, the system tray icon or the
app indicator.

By default, this command will start the main app if no argument is given.
"""))

    def cmd_detach(self, program="app"):
        if program not in ["app", "icon", "indicator"]:
            sys.exit(1)
        daemonize()
        cmd = f"chwall-{program}"
        os.execl(f"/usr/bin/{cmd}", cmd)

    def help_status(self):
        self._print_usage("status [ open ]", "current [ open ]",
                          "info [ open ]")
        print(_("""
Display the current wallpaper information.

If the optional ‘open’ keyword is given, the original resource will be opened,
using the best dedicated tool for it (web browser, picture viewer...).
"""))

    def cmd_status(self, subcmd="print"):
        wallinfo = current_wallpaper_info()
        if wallinfo["type"] == "":
            print(_("Current wallpaper is not managed by Chwall"))
            return
        if wallinfo["type"] == "local":
            print(" ".join([
                _("Local wallpaper"),
                wallinfo["local-picture-path"]
            ]))
        else:
            print(wallinfo["description"])
            print(wallinfo["remote-uri"])
        dinfo = daemon_info()
        print(dinfo["last-change-label"])
        if len(wallinfo) < 2 or subcmd != "open":
            return
        open_externally(wallinfo["remote-uri"])

    def help_block(self):
        self._print_usage("block")
        print(_("""
Add the current wallpaper on the block list to avoid it to be shown ever again
and switch to the next wallpaper.
"""))

    def cmd_block(self):
        block_wallpaper()
        self.cmd_next()

    def help_favorite(self):
        self._print_usage("favorite")
        print(_("""
Save a copy of the current wallpaper to not forget it and display it again
later.
"""))

    def cmd_favorite(self):
        favorite_wallpaper(read_config())

    def _pick_wall(self, direction=False):
        if pick_wallpaper(read_config(), direction) is None:
            print(_("Unable to pick wallpaper this time. Please, try again."),
                  file=sys.stderr)
            self.cmd_quit()
        else:
            notify_daemon_if_any()

    def help_next(self):
        self._print_usage("next [ savetime ]", "once [ savetime ]")
        print(_("""
Switch to the next wallpaper.

This command may be used, even if the daemon is not started to manually change
the wallpaper.

If the optional ‘savetime’ keyword is given, the current time will be stored as
the last time the wallpaper was changed (as if it was done by the daemon).
"""))

    def cmd_next(self, subcmd="pass"):
        self._pick_wall()
        if subcmd != "savetime":
            return
        with open(f"{BASE_CACHE_PATH}/last_change", "w") as f:
            f.write(str(int(time.time())))

    def help_previous(self):
        self._print_usage("previous")
        print(_("""
Switch to the previous wallpaper.
"""))

    def cmd_previous(self):
        self._pick_wall(True)

    def help_quit(self):
        self._print_usage("quit", "kill")
        print(_("""
Stop the chwall daemon.
"""))

    def cmd_quit(self):
        stop_daemon_if_any()

    def help_empty(self):
        self._print_usage("empty")
        print(_("""
Empty the current pending list to force chwall to fetch a new wallpapers list
the next time it will change.
"""))

    def cmd_empty(self):
        reset_pending_list()

    def _road_map(self):
        road_map = f"{BASE_CACHE_PATH}/roadmap"
        if not os.path.exists(road_map):
            print(_("No roadmap has been created yet"), file=sys.stderr)
            sys.exit(1)
        data = {}
        with open(road_map, "r") as f:
            data = yaml.safe_load(f)
        return data

    def help_history(self):
        self._print_usage("history")
        print(_("""
Display the last displayed wallpapers. The most recent one is at the bottom.

This command display only the upstream url of each wallpaper.
"""))

    def cmd_history(self):
        data = self._road_map()
        print("\n".join(data["history"]))

    def help_pending(self):
        self._print_usage("pending")
        print(_("""
Display the next wallpapers, which will be shown in the future. The next one is
at the top of the list.

This command display only the upstream url of each wallpaper.
"""))

    def cmd_pending(self):
        data = self._road_map()
        print("\n".join(data["pictures"]))

    def cmd_fetcher(self, *subcmd):
        subcmd = list(subcmd)
        if len(subcmd) == 0:
            fetcher = "_list_"
        else:
            fetcher = subcmd.pop(0)
        fetcher_package = import_module("chwall.fetcher")
        fp_source = fetcher_package.__path__
        fetchers_list = []
        for fd in pkgutil.iter_modules(fp_source):
            fetcher_mod = import_module(f"chwall.fetcher.{fd.name}")
            if "preferences" not in dir(fetcher_mod):
                continue
            fetchers_list.append(fd.name)
        if fetcher == "_list_" or fetcher not in fetchers_list:
            for name in fetchers_list:
                print(name)
            return
        fetcher_mod = import_module(f"chwall.fetcher.{fetcher}")
        if len(subcmd) == 0:
            print(json.dumps(fetcher_mod.preferences()))
            return
        # Last args must be the json configuration for the fetcher.
        # Simplify the user work by wrapping ourselve the given data into a
        # named dictionary
        config = {fetcher: json.loads(subcmd[0])}
        results = fetcher_mod.fetch_pictures(config)
        print(json.dumps(results))


if __name__ == "__main__":
    ChwallClient()
