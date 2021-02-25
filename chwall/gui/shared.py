import os
import threading
import subprocess

from chwall import __version__
from chwall.daemon import notify_daemon_if_any, notify_app_if_any, daemon_info
from chwall.utils import read_config, cleanup_cache
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper, \
    favorite_wallpaper_path, favorite_wallpaper
from chwall.gui.preferences import PrefDialog

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

import gettext  # noqa: E402
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallGui:
    def __init__(self):
        self.app = None
        self.reload_config()
        # Try to keep cache as clean as possible
        cleanup_cache()

    def reload_config(self):
        self.config = read_config()

    def daemon_info(self):
        return daemon_info()

    # May be called from as a widget action, hence the variable arguments list
    def stop_daemon(self, *opts):
        # 15 == signal.SIGTERM
        notify_daemon_if_any(15)

    def start_in_thread_if_needed(self, function, *args):
        if self.app is None:
            # Coming from the icon, directly call the daemon to avoid
            # system-tray icon disapearance
            function(*args)
        else:
            # Coming from the app, call through an intermediate thread to
            # avoid ugly UI freeze
            t = threading.Thread(target=function, args=args)
            t.daemon = True
            t.start()

    def on_change_wallpaper(self, _widget, direction=False, threaded=True):
        def change_wall_thread_target(direction):
            pick_wallpaper(self.config, direction)
            notify_daemon_if_any()
            notify_app_if_any()

        if not threaded:
            change_wall_thread_target(direction)
        else:
            self.start_in_thread_if_needed(change_wall_thread_target, direction)  # noqa

    def on_blacklist_wallpaper(self, _widget):
        def blacklist_wall_thread_target():
            blacklist_wallpaper()
            self.on_change_wallpaper(None, threaded=False)
        self.start_in_thread_if_needed(blacklist_wall_thread_target)

    def on_favorite_wallpaper(self, _widget):
        if favorite_wallpaper(self.config):
            if self.app is None:
                return
            self.favorite_button.set_sensitive(False)
            self.favorite_button.set_tooltip_text(_("Already a favorite"))

    def run_chwall_component(self, _widget, component):
        def start_daemon_from_thread():
            # At the difference of the daemon itself, it's expected than a
            # service start from inside the app or the icon will immediatly
            # change the current wallpaper.
            pick_wallpaper(self.config)
            notify_app_if_any()
            # No need to fork, daemon already do that
            subprocess.run(["chwall-daemon"])

        if component == "daemon":
            self.start_in_thread_if_needed(start_daemon_from_thread)
        else:
            subprocess.run(["chwall", "detach", component])

    def is_chwall_component_started(self, component):
        retcode = subprocess.run(
            ["pgrep", "-f", "chwall.+{}".format(component)],
            stdout=subprocess.DEVNULL).returncode
        return retcode == 0

    # This function may raise a PermissionError
    def is_current_wall_favorite(self, wallinfo):
        fav_path = favorite_wallpaper_path(
            wallinfo["local-picture-path"], self.config)
        return os.path.exists(fav_path)

    def show_preferences_dialog(self, widget):
        if self.app is None:
            flags = 0
            # flags 3 = MODAL | DESTROY_WITH_PARENT
        else:
            flags = 3
        prefwin = PrefDialog(self.app, flags)
        prefwin.run()
        prefwin.destroy()
        self.reload_config()

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_icon_name("chwall")
        about_dialog.set_logo_icon_name("chwall")
        about_dialog.set_program_name("Chwall")
        about_dialog.set_website("https://git.deparis.io/chwall/about")
        about_dialog.set_comments(_("Wallpaper Changer"))
        about_dialog.set_version(__version__)
        about_dialog.set_copyright(_("Chwall is released under the WTFPL"))
        about_dialog.set_license("""\
http://www.wtfpl.net/about/

DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
Version 2, December 2004

Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>

Everyone is permitted to copy and distribute verbatim or modified
copies of this license document, and changing it is allowed as long
as the name is changed.

TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

0. You just DO WHAT THE FUCK YOU WANT TO.
""")
        about_dialog.set_authors(["Étienne Deparis <etienne@depar.is>"])
        about_dialog.set_translator_credits(
            _("translator-credits https://translations.umaneti.net/engage/chwall/")  # noqa
        )
        about_dialog.run()
        about_dialog.destroy()

    def kthxbye(self, *args):
        Gtk.main_quit()
