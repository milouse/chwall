import threading
import subprocess

from chwall.daemon import notify_daemon_if_any, notify_app_if_any, daemon_info
from chwall.utils import VERSION, read_config, cleanup_cache
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper
from chwall.gui.preferences import PrefDialog

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallGui:
    def __init__(self):
        self.config = read_config()
        self.app = None

    def daemon_info(self):
        return daemon_info(self.config)

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
        def change_wall_thread_target(direction, config):
            pick_wallpaper(config, direction)
            notify_daemon_if_any()
            notify_app_if_any()

        if not threaded:
            change_wall_thread_target(direction, self.config)
        else:
            self.start_in_thread_if_needed(change_wall_thread_target,
                                           direction, self.config)

    def on_blacklist_wallpaper(self, _widget):
        def blacklist_wall_thread_target():
            blacklist_wallpaper()
            self.on_change_wallpaper(None, threaded=False)
        self.start_in_thread_if_needed(blacklist_wall_thread_target)

    def run_chwall_component(self, _widget, component):
        def start_daemon_from_thread(config):
            # At the difference of the daemon itself, it's expected than a
            # service start from inside the app or the icon will immediatly
            # change the current wallpaper.
            pick_wallpaper(config)
            notify_app_if_any()
            # No need to fork, daemon already do that
            subprocess.run(["chwall-daemon"])

        if component == "daemon":
            self.start_in_thread_if_needed(start_daemon_from_thread,
                                           self.config)
        else:
            subprocess.run(["chwall", "detach", component])

    def is_chwall_component_started(self, component):
        retcode = subprocess.run(
            ["pgrep", "-f", "chwall.+{}".format(component)],
            stdout=subprocess.DEVNULL).returncode
        return retcode == 0

    def get_flags_if_app(self):
        if self.app is not None:
            # flags 3 = MODAL | DESTROY_WITH_PARENT
            return 3
        return 0

    def reset_pending_list(self):
        subprocess.run(["chwall", "purge"])

    def on_cleanup_cache(self, _widget):
        deleted = cleanup_cache()
        if deleted < 2:
            message = _("{number} broken cache entry has been removed")
        else:
            message = _("{number} broken cache entries have been removed")
        # flags 3 = MODAL | DESTROY_WITH_PARENT
        dialog = Gtk.MessageDialog(self.app, self.get_flags_if_app(),
                                   Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                                   _("Cache cleanup"))
        dialog.set_icon_name("chwall")
        dialog.format_secondary_text(message.format(number=deleted))
        dialog.run()
        dialog.destroy()

    def show_preferences_dialog(self, widget):
        prefwin = PrefDialog(self.app, self.get_flags_if_app(), self.config)
        prefwin.run()
        prefwin.destroy()

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_icon_name("chwall")
        about_dialog.set_name("Chwall")
        about_dialog.set_website("https://git.deparis.io/chwall/about")
        about_dialog.set_comments(_("Wallpaper Changer"))
        about_dialog.set_version(VERSION)
        about_dialog.set_copyright(_("Chwall is released under the WTFPL"))
        about_dialog.set_license("""
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
        about_dialog.set_logo_icon_name("chwall")
        about_dialog.set_translator_credits(
            _("translator-credits https://translations.umaneti.net/engage/chwall/")  # noqa
        )
        about_dialog.run()
        about_dialog.destroy()

    def kthxbye(self, *args):
        Gtk.main_quit()
