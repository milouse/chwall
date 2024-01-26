import os
import threading
import subprocess

from chwall import __version__
from chwall.daemon import notify_daemon_if_any, stop_daemon_if_any, \
    notify_app_if_any, daemon_info, save_change_time
from chwall.utils import ServiceFileManager, read_config
from chwall.wallpaper import block_wallpaper, pick_wallpaper, \
    favorite_wallpaper_path, favorite_wallpaper
from chwall.gui.preferences import PrefDialog

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

import gettext  # noqa: E402
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallGui:
    def __init__(self):
        self.sfm = None
        self.component = None
        self.must_autostart = False
        self.current_is_favorite = False
        self.reload_config()

    def init_service_file_manager(self):
        if not self.component:
            return
        self.sfm = ServiceFileManager()
        self.must_autostart = self.sfm.xdg_autostart_file_exists(
            self.component
        )

    def reload_config(self):
        self.config = read_config()

    def main_icon(self):
        mono_icon = self.config["general"].get("mono_icon", False)
        if mono_icon:
            return "chwall_mono"
        return "chwall"

    def daemon_info(self):
        return daemon_info()

    # May be called from as a widget action, hence the variable arguments list
    def stop_daemon(self, *args):
        stop_daemon_if_any()

    def start_in_thread_if_needed(self, function, *args):
        if self.component == "app":
            # Coming from the app, call through an intermediate thread to
            # avoid ugly UI freeze
            t = threading.Thread(target=function, args=args)
            t.daemon = True
            t.start()
        else:
            # Coming from the icon, directly call the daemon to avoid
            # system-tray icon disapearance
            function(*args)

    def on_change_wallpaper(self, _widget, direction=False, block=False):
        def change_wall_thread_target(direction, block):
            if block:
                block_wallpaper()
            pick_wallpaper(self.config, direction)
            save_change_time()
            notify_daemon_if_any()
            notify_app_if_any()

        self.start_in_thread_if_needed(
            change_wall_thread_target, direction, block
        )

    def on_block_wallpaper(self, widget):
        self.on_change_wallpaper(widget, block=True)

    def on_favorite_wallpaper(self, _widget):
        if favorite_wallpaper(self.config):
            self.current_is_favorite = True

    def on_toggle_must_autostart(self, widget):
        if not self.sfm or not self.component:
            return
        self.must_autostart = widget.get_active()
        if self.must_autostart:
            self.sfm.xdg_autostart_file(self.component, True)
        else:
            self.sfm.remove_xdg_autostart_file(self.component)

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
        elif component in ["app", "icon", "indicator"]:
            subprocess.Popen(f"chwall-{component}")

    def is_chwall_component_started(self, component):
        retcode = subprocess.run(
            ["pgrep", "-f", f"chwall.+{component}"],
            stdout=subprocess.DEVNULL).returncode
        return retcode == 0

    # This function may raise a PermissionError
    def is_current_wall_favorite(self, wallinfo):
        fav_path = favorite_wallpaper_path(
            wallinfo["local-picture-path"], self.config)
        self.current_is_favorite = os.path.exists(fav_path)
        return self.current_is_favorite

    def show_preferences_dialog(self, _widget, app=None):
        if isinstance(app, Gtk.Window):
            # flags 3 = MODAL | DESTROY_WITH_PARENT
            flags = 3
        else:
            flags = 0
            app = None  # Mute it
        prefwin = PrefDialog(app, flags)
        prefwin.run()
        prefwin.destroy()
        self.reload_config()

    def show_about_dialog(self, _widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_icon_name("chwall")
        about_dialog.set_logo_icon_name("chwall")
        about_dialog.set_program_name("Chwall")
        about_dialog.set_website("https://git.umaneti.net/chwall/about")
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
        # about_dialog.set_translator_credits(_("translator-credits"))
        about_dialog.run()
        about_dialog.destroy()

    def show_report_a_bug(self, _widget):
        subprocess.Popen(
            ["gio", "open",
             "https://framagit.org/milouse/chwall/issues"])

    def start(self):
        # Install signal handlers
        # SIGTERM = 15
        # SIGINT = 2
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, Gtk.main_quit, None)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, Gtk.main_quit, None)
        Gtk.main()

    def kthxbye(self, *args):
        Gtk.main_quit()
