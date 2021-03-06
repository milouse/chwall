#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess
from xdg.BaseDirectory import xdg_data_home

# chwall imports
from chwall import __version__
from chwall.daemon import notify_daemon_if_any, daemon_info, daemonize
from chwall.utils import BASE_CACHE_PATH, read_config, \
                         reset_pending_list, ServiceFileManager
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper, \
                             favorite_wallpaper
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
        self.cmd_help("__from_error__")
        sys.exit(1)

    def _parse_argv(self):
        action = None
        opts = []
        for a in self.argv:
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

    def cmd_help(self, *opts):
        out = sys.stdout
        if len(opts) != 0 and opts[0] == "__from_error__":
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

    def cmd_systemd(self, *opts):
        sfm = ServiceFileManager()
        write = False
        if len(opts) != 0 and opts[0] == "write":
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

    def help_options(self):
        self._print_usage("options", "preferences")
        print(_("""
Directly open the chwall preferences window.
"""))

    def cmd_options(self, *opts):
        prefwin = PrefDialog(None, 0)
        prefwin.run()
        prefwin.destroy()

    def help_detach(self):
        self._print_usage("detach [ app | icon ]")
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
        self._print_usage("status [ open ]", "current [ open ]",
                          "info [ open ]")
        print(_("""
Display the current wallpaper information.

If the optional ‘open’ keyword is given, the original resource will be opened,
using the best dedicated tool for it (web browser, picture viewer...).
"""))

    def cmd_status(self, *opts):
        with open("{}/current_wallpaper"
                  .format(BASE_CACHE_PATH), "r") as f:
            infos = f.readlines()[1:]
        print("".join(infos))
        dinfo = daemon_info()
        print(dinfo["last-change-label"])
        if len(opts) != 0 and opts[0] == "open" and len(infos) >= 2:
            url = infos[1].strip()
            if url != "":
                subprocess.run(["gio", "open", url])

    def help_blacklist(self):
        self._print_usage("blacklist")
        print(_("""
Add the current wallpaper to the blacklist to avoid it to be shown ever again
and switch to the next wallpaper.
"""))

    def cmd_blacklist(self, *opts):
        blacklist_wallpaper()
        self.cmd_next()

    def help_favorite(self):
        self._print_usage("favorite")
        print(_("""
Save a copy of the current wallpaper to not forget it and display it again
later.
"""))

    def cmd_favorite(self, *opts):
        favorite_wallpaper(read_config())

    def _pick_wall(self, direction=False):
        if pick_wallpaper(read_config(), direction) is None:
            print(_("Unable to pick wallpaper this time. Please, try again."),
                  file=sys.stderr)
            self.cmd_quit()
        else:
            notify_daemon_if_any()

    def help_next(self):
        self._print_usage("next", "once")
        print(_("""
Switch to the next wallpaper.

This command may be used, even if the daemon is not started to manually change
the wallpaper.
"""))

    def cmd_next(self, *opts):
        self._pick_wall()

    def help_previous(self):
        self._print_usage("previous")
        print(_("""
Switch to the previous wallpaper.
"""))

    def cmd_previous(self, *opts):
        self._pick_wall(True)

    def help_quit(self):
        self._print_usage("quit", "kill")
        print(_("""
Stop the chwall daemon.
"""))

    def cmd_quit(self, *opts):
        # 15 == signal.SIGTERM
        notify_daemon_if_any(15)

    def help_empty(self):
        self._print_usage("empty")
        print(_("""
Empty the current pending list to force chwall to fetch a new wallpapers list
the next time it will change.
"""))

    def cmd_empty(self, *opts):
        reset_pending_list()

    def _road_map(self):
        road_map = "{}/roadmap".format(BASE_CACHE_PATH)
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

    def cmd_history(self, *opts):
        data = self._road_map()
        print("\n".join(data["history"]))

    def help_pending(self):
        self._print_usage("pending")
        print(_("""
Display the next wallpapers, which will be shown in the future. The next one is
at the top of the list.

This command display only the upstream url of each wallpaper.
"""))

    def cmd_pending(self, *opts):
        data = self._road_map()
        print("\n".join(data["pictures"]))


if __name__ == "__main__":
    ChwallClient()
