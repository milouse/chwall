#!/usr/bin/env python3

import subprocess

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info
from chwall.utils import ServiceFileManager

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

import gettext  # noqa: E402
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
        self.sfm = ServiceFileManager()
        self.must_autostart = self.sfm.xdg_autostart_file_exists("icon")

    def display_menu(self, _icon, event_button, event_time):
        dinfo = self.daemon_info()
        daemon_state_label = dinfo["daemon-state-label"]
        if dinfo["next-change"] == -1:
            run_btn = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_MEDIA_PLAY)
            run_btn.set_label(_("Start daemon"))
            run_btn.connect("activate", self.run_chwall_component, "daemon")
        else:
            run_btn = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_MEDIA_PAUSE)
            run_btn.set_label(_("Stop daemon"))
            run_btn.connect("activate", self.stop_daemon)
            daemon_state_label += " - " + dinfo["next-change-label"]

        daemon_state_btn = Gtk.MenuItem.new_with_label(daemon_state_label)
        daemon_state_btn.set_sensitive(False)

        menu = Gtk.Menu()
        menu.append(daemon_state_btn)
        menu.append(run_btn)

        current_wall_info = Gtk.MenuItem()
        wallinfo = current_wallpaper_info()
        if wallinfo["remote-uri"] is None:
            current_wall_info.set_label(
                _("Current wallpaper is not managed by Chwall"))
            current_wall_info.set_sensitive(False)
        else:
            if wallinfo["type"] == "local":
                current_wall_info.set_label(wallinfo["local-picture-path"])
            else:
                current_wall_info.set_label(wallinfo["description"])
            current_wall_info.connect("activate", self.open_in_context,
                                      wallinfo["remote-uri"])
        menu.append(current_wall_info)

        item = Gtk.SeparatorMenuItem()
        menu.append(item)

        # next wallpaper
        nextbtn = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_GO_FORWARD)
        nextbtn.set_label(_("Next wallpaper"))
        # nextbtn = Gtk.MenuItem.new_with_label(_("Next wallpaper"))
        nextbtn.connect("activate", self.on_change_wallpaper)
        menu.append(nextbtn)

        # previous wallpaper
        prevbtn = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_GO_BACK)
        prevbtn.set_label(_("Previous wallpaper"))
        # prevbtn = Gtk.MenuItem.new_with_label(_("Previous wallpaper"))
        prevbtn.connect("activate", self.on_change_wallpaper, True)
        menu.append(prevbtn)

        # favorite wallpaper
        favbtn = Gtk.ImageMenuItem.new_with_label(_("Save as favorite"))
        favbtn.set_image(Gtk.Image.new_from_icon_name(
            "bookmark-new", Gtk.IconSize.MENU))
        favbtn.connect("activate", self.on_favorite_wallpaper)
        menu.append(favbtn)

        # blacklist wallpaper
        blackbtn = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_DELETE)
        blackbtn.set_label(_("Blacklist"))
        # blackbtn = Gtk.MenuItem.new_with_label(_("Blacklist"))
        blackbtn.connect("activate", self.on_blacklist_wallpaper)
        menu.append(blackbtn)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        item = Gtk.MenuItem.new_with_label(_("Open main window"))
        if self.is_chwall_component_started("app"):
            item.set_sensitive(False)
        else:
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
        about.set_label(_("About Chwall"))
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
        if self.must_autostart:
            self.sfm.xdg_autostart_file(
                "icon", "Chwall", _("Wallpaper Changer"), True
            )
        else:
            self.sfm.remove_xdg_autostart_file("icon")

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
