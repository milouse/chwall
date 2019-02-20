#!/usr/bin/env python3

import os
import signal
import subprocess
from xdg.BaseDirectory import xdg_config_home

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gtk, GLib

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallIcon(ChwallGui):
    def __init__(self):
        super().__init__()
        self.tray = Gtk.StatusIcon()
        self.tray.set_from_icon_name("chwall")
        self.tray.set_tooltip_text("Chwall")
        self.tray.connect("popup-menu", self.display_menu)
        self.autostart_file = os.path.join(xdg_config_home, "autostart",
                                           "chwall-icon.desktop")
        self.must_autostart = os.path.isfile(self.autostart_file)

    def display_menu(self, _icon, event_button, event_time):
        menu = Gtk.Menu()

        self.append_daemon_info(menu)

        wallinfo = current_wallpaper_info()
        if wallinfo["type"] == "local":
            curlabel = wallinfo["local-picture-path"]
        else:
            curlabel = "{copy} ({source})".format(
                copy=wallinfo["description"], source=wallinfo["type"])
        current_wall_info = Gtk.MenuItem.new_with_label(curlabel)
        current_wall_info.connect("activate", self.open_in_context,
                                  wallinfo["remote-uri"])
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

        # previous wallpaper
        blackbtn = Gtk.MenuItem.new_with_label(_("Blacklist"))
        menu.append(blackbtn)
        blackbtn.connect("activate", self.blacklist_wallpaper)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        item = Gtk.MenuItem.new_with_label(_("Open main window"))
        item.connect("activate", self.run_chwall_component, "gtk")
        menu.append(item)

        # Launch at session start
        asbtn = Gtk.CheckMenuItem.new_with_label(_("Always display this icon"))
        asbtn.set_active(self.must_autostart)
        menu.append(asbtn)
        asbtn.connect("toggled", self.toggle_must_autostart)

        prefs = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_PREFERENCES)
        prefs.connect("activate", self.show_preferences_dialog)
        menu.append(prefs)

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

    def open_in_context(self, widget, wall_url):
        subprocess.Popen(["gio", "open", wall_url])

    def toggle_must_autostart(self, widget):
        self.must_autostart = widget.get_active()
        autostart_dir = os.path.join(xdg_config_home, "autostart")
        if not os.path.isdir(autostart_dir):
            os.makedirs(autostart_dir)
        file_yet_exists = os.path.isfile(self.autostart_file)
        if not file_yet_exists and self.must_autostart:
            with open(self.autostart_file, "w") as f:
                f.write("""\
[Desktop Entry]
Name={}
Comment={}
Exec=chwall-icon
Icon=chwall
Terminal=false
Type=Application
X-MATE-Autostart-enabled=true
X-GNOME-Autostart-Delay=20
StartupNotify=false
""".format(_("Chwall"), _("Wallpaper Changer")))
        elif file_yet_exists and not self.must_autostart:
            os.remove(self.autostart_file)

    def report_a_bug(self, widget):
        subprocess.Popen(
            ["gio", "open",
             "https://framagit.org/milouse/chwall/issues"])


def start_icon():
    # Install signal handlers
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM,
                         Gtk.main_quit, None)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,
                         Gtk.main_quit, None)
    ChwallIcon().show()


if __name__ == "__main__":
    start_icon()
