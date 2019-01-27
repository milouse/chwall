#!/usr/bin/env python3

import os
import signal
import subprocess
from chwall.utils import VERSION, BASE_CACHE_PATH, read_config
from chwall.wallpaper import pick_wallpaper

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gtk, GLib

import gettext
# Explicit declaration to avoid flake8 fear.
gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallIcon:
    def __init__(self):
        self.config = read_config()
        self.tray = Gtk.StatusIcon()
        self.tray.set_from_icon_name("chwall")
        self.tray.set_tooltip_text("Chwall")
        self.tray.connect("popup-menu", self.display_menu)

    def display_menu(self, _icon, event_button, event_time):
        menu = Gtk.Menu()

        pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
        if os.path.exists(pid_file):
            daemon_state = Gtk.MenuItem.new_with_label(_("Daemon started"))
        else:
            daemon_state = Gtk.MenuItem.new_with_label(_("Daemon stopped"))
        daemon_state.set_sensitive(False)
        menu.append(daemon_state)

        curwall = []
        # line 0 contains wallpaper uri
        # line 1 contains description
        # line 2 contains remote page in case of remote wallpaper
        with open("{}/current_wallpaper"
                  .format(BASE_CACHE_PATH), "r") as f:
            curwall = f.readlines()
        current_wall_info = Gtk.MenuItem.new_with_label(curwall[1].strip())
        current_wall_info.connect("activate", self.open_in_context,
                                  curwall[2].strip())
        menu.append(current_wall_info)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        # next wallpaper
        nextbtn = Gtk.MenuItem.new_with_label(_("Next wallpaper"))
        menu.append(nextbtn)
        nextbtn.connect("activate", self.change_wallpaper)

        # previous wallpaper
        prevbtn = Gtk.MenuItem.new_with_label(_("Previous wallpaper"))
        menu.append(prevbtn)
        prevbtn.connect("activate", self.change_wallpaper, True)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        # report a bug
        reportbug = Gtk.MenuItem.new_with_label(_("Report a bug"))
        menu.append(reportbug)
        reportbug.connect("activate", self.report_a_bug)

        # show about dialog
        about = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ABOUT)
        menu.append(about)
        about.connect("activate", self.show_about_dialog)

        # add quit item
        quit_button = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT)
        quit_button.connect("activate", self.kthxbye)
        menu.append(quit_button)

        menu.show_all()
        menu.popup(None, None, Gtk.StatusIcon.position_menu,
                   self.tray, event_button, event_time)

    def change_wallpaper(self, widget, direction=False):
        pick_wallpaper(self.config, direction)

    def open_in_context(self, widget, wall_url):
        subprocess.Popen(["gio", "open", wall_url])

    def report_a_bug(self, widget):
        subprocess.Popen(
            ["gio", "open",
             "https://framagit.org/milouse/chwall/issues"])

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_icon_name("chwall")
        about_dialog.set_name(_("Chwall"))
        about_dialog.set_website("https://git.deparis.io/chwall/about")
        about_dialog.set_comments(_("Wallpaper Changer"))
        about_dialog.set_version(VERSION)
        about_dialog.set_copyright(_("Chwall is released under the WTFPL"))
        about_dialog.set_authors(["Étienne Deparis <etienne@depar.is>"])
        about_dialog.set_logo_icon_name("chwall")
        about_dialog.run()
        about_dialog.destroy()

    def kthxbye(self, widget, data=None):
        Gtk.main_quit()


def start_icon():
    # Install signal handlers
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM,
                         Gtk.main_quit, None)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,
                         Gtk.main_quit, None)
    ChwallIcon()
    Gtk.main()


if __name__ == "__main__":
    start_icon()
