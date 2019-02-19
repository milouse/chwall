#!/usr/bin/env python3

import os
import time
import signal
import subprocess
from xdg.BaseDirectory import xdg_config_home
from chwall.daemon import notify_daemon_if_any
from chwall.utils import VERSION, BASE_CACHE_PATH, read_config
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gtk, GLib

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


DAEMON_STATE = {
    "started": _("Daemon started"),
    "stopped": _("Daemon stopped"),
    "started_absent": _("Daemon started (service file not found)"),
    "stopped_absent": _("Daemon stopped (service file not found)"),
    "started_disabled": _("Daemon started, but disabled"),
    "stopped_disabled": _("Daemon stopped and disabled")
}


class ChwallIcon:
    def __init__(self):
        self.config = read_config()
        self.tray = Gtk.StatusIcon()
        self.tray.set_from_icon_name("chwall")
        self.tray.set_tooltip_text("Chwall")
        self.tray.connect("popup-menu", self.display_menu)
        self.autostart_file = os.path.join(xdg_config_home, "autostart",
                                           "chwall-icon.desktop")
        self.must_autostart = os.path.isfile(self.autostart_file)

    def display_menu(self, _icon, event_button, event_time):
        menu = Gtk.Menu()

        next_change_label = None
        daemon_state = []
        pid_file = "{}/chwall_pid".format(BASE_CACHE_PATH)
        if os.path.exists(pid_file):
            daemon_state.append("started")
            with open("{}/last_change".format(BASE_CACHE_PATH), "r") as f:
                try:
                    last_change = int(time.time()) - int(f.read().strip())
                except ValueError:
                    last_change = -1
            sleep_time = self.config['general']['sleep']
            next_change = sleep_time - last_change
            if next_change > 60:
                next_change_m = int(next_change / 60)
                next_change_s = next_change % 60
                min_str = _("minute")
                if next_change > 120:
                    min_str = _("minutes")
                next_change_label = _("Next change in {minute_number} "
                                      "{minute_label} {second_number}s")
                next_change_label = next_change_label.format(
                    minute_number=next_change_m, minute_label=min_str,
                    second_number=next_change_s)
            else:
                next_change_label = (_("Next change in {second_number}s")
                                     .format(next_change))
        else:
            daemon_state.append("stopped")

        systemd_path = os.path.expanduser("~/.config/systemd/user")
        if not os.path.exists("{}/chwall.service".format(systemd_path)):
            daemon_state.append("absent")
        elif not os.path.exists("{}/default.target.wants/chwall.service"
                                .format(systemd_path)):
            daemon_state.append("disabled")

        daemon_state_label = DAEMON_STATE["_".join(daemon_state)]
        daemon_state_btn = Gtk.MenuItem.new_with_label(daemon_state_label)
        daemon_state_btn.set_sensitive(False)
        menu.append(daemon_state_btn)

        if next_change_label is not None:
            next_change_btn = Gtk.MenuItem.new_with_label(next_change_label)
            next_change_btn.set_sensitive(False)
            menu.append(next_change_btn)

        curwall = []
        # line 0 contains wallpaper uri
        # line 1 contains description
        # line 2 contains remote page in case of remote wallpaper
        with open("{}/current_wallpaper"
                  .format(BASE_CACHE_PATH), "r") as f:
            curwall = f.readlines()
        source = curwall[3].strip()
        uri = curwall[2].strip()
        if source == "local":
            curlabel = uri
        else:
            curlabel = "{copy} ({source})".format(
                copy=curwall[1].strip(), source=source)
        current_wall_info = Gtk.MenuItem.new_with_label(curlabel)
        current_wall_info.connect("activate", self.open_in_context, uri)
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

        # Launch at session start
        asbtn = Gtk.CheckMenuItem(_("Always display this icon"))
        asbtn.set_active(self.must_autostart)
        menu.append(asbtn)
        asbtn.connect("toggled", self.toggle_must_autostart)

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
        notify_daemon_if_any()

    def blacklist_wallpaper(self, widget):
        blacklist_wallpaper()
        self.change_wallpaper(widget)

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
