#!/usr/bin/env python3

import os
import subprocess
from xdg.BaseDirectory import xdg_config_home

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
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

        dinfo = self.daemon_info()
        daemon_state_btn = Gtk.MenuItem.new_with_label(
            dinfo["daemon-state-label"])
        daemon_state_btn.set_sensitive(False)
        menu.append(daemon_state_btn)

        if dinfo["next-change-label"] is None:
            run_btn = Gtk.MenuItem.new_with_label(_("Start daemon"))
            run_btn.connect("activate", self.run_chwall_component, "daemon")
            menu.append(run_btn)
        else:
            next_change_btn = Gtk.MenuItem.new_with_label(
                dinfo["next-change-label"])
            next_change_btn.set_sensitive(False)
            menu.append(next_change_btn)

        wallinfo = current_wallpaper_info()
        if wallinfo["type"] == "local":
            curlabel = wallinfo["local-picture-path"]
        else:
            curlabel = wallinfo["description"]
        current_wall_info = Gtk.MenuItem.new_with_label(curlabel)
        current_wall_info.connect("activate", self.open_in_context,
                                  wallinfo["remote-uri"])
        menu.append(current_wall_info)

        item = Gtk.SeparatorMenuItem()
        menu.append(item)

        # next wallpaper
        nextbtn = Gtk.MenuItem.new_with_label(_("Next wallpaper"))
        nextbtn.connect("activate", self.on_change_wallpaper)
        menu.append(nextbtn)

        # previous wallpaper
        prevbtn = Gtk.MenuItem.new_with_label(_("Previous wallpaper"))
        prevbtn.connect("activate", self.on_change_wallpaper, True)
        menu.append(prevbtn)

        # previous wallpaper
        blackbtn = Gtk.MenuItem.new_with_label(_("Blacklist"))
        blackbtn.connect("activate", self.on_blacklist_wallpaper)
        menu.append(blackbtn)

        item = Gtk.MenuItem.new_with_label(
            _("Cleanup broken entries in cache"))
        item.connect("activate", self.on_cleanup_cache)
        menu.append(item)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        item = Gtk.MenuItem.new_with_label(_("Open main window"))
        item.connect("activate", self.run_chwall_component, "app")
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
Categories=GTK;TrayIcon;
X-MATE-Autostart-enabled=true
X-GNOME-Autostart-enabled=false
StartupNotify=false
""".format("Chwall", _("Wallpaper Changer")))
        elif file_yet_exists and not self.must_autostart:
            os.remove(self.autostart_file)

    def report_a_bug(self, widget):
        subprocess.Popen(
            ["gio", "open",
             "https://framagit.org/milouse/chwall/issues"])


def start_icon():
    # Install signal handlers
    # SIGTERM = 15
    # SIGINT = 2
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 15, Gtk.main_quit, None)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, 2, Gtk.main_quit, None)
    ChwallIcon()
    Gtk.main()


if __name__ == "__main__":
    start_icon()
