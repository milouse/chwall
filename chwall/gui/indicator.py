#!/usr/bin/env python3

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info
from chwall.utils import open_externally

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402
gi.require_version("AppIndicator3", "0.1")
from gi.repository import AppIndicator3 as appindicator  # noqa: E402

import gettext  # noqa: E402
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallIndicator(ChwallGui):
    def __init__(self):
        super().__init__()
        self.component = "indicator"
        self.tray = appindicator.Indicator.new(
            "chwall_indicator", self.main_icon(),
            appindicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.tray.set_title("Chwall")
        self.build_main_menu()
        self.tray.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.start()

    def build_main_menu(self):
        menu = Gtk.Menu()

        item = Gtk.MenuItem()
        wallinfo = current_wallpaper_info()
        if wallinfo["type"] == "":
            item.set_label(
                _("Current wallpaper is not managed by Chwall"))
            item.set_sensitive(False)
        else:
            if wallinfo["type"] == "local":
                item.set_label(wallinfo["local-picture-path"])
            else:
                item.set_label(wallinfo["description"])
            item.connect(
                "activate",
                lambda _w, url: open_externally(url),
                wallinfo["remote-uri"]
            )
        menu.append(item)

        daemon_submenu = Gtk.Menu()
        item = Gtk.MenuItem()
        item.set_sensitive(False)
        daemon_submenu.append(item)
        daemon_submenu.append(Gtk.MenuItem())

        item = Gtk.MenuItem()
        item.set_label(_("Daemon status"))
        item.set_submenu(daemon_submenu)
        item.connect(
            "activate", self.open_daemon_submenu, daemon_submenu
        )
        menu.append(item)

        item = Gtk.SeparatorMenuItem()
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Next wallpaper"))
        item.connect("activate", self.on_change_wallpaper)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Previous wallpaper"))
        item.connect("activate", self.on_change_wallpaper, True)
        menu.append(item)

        if wallinfo["type"] != "":
            item = Gtk.MenuItem.new_with_label(_("Save as favorite"))
            try:
                if self.is_current_wall_favorite(wallinfo):
                    item.set_tooltip_text(_("Already a favorite"))
                    item.set_sensitive(False)
                else:
                    item.connect("activate", self.on_favorite_wallpaper)
            except PermissionError:
                item.set_tooltip_text(
                    _("Error accessing the favorites folder"))
                item.set_sensitive(False)
            menu.append(item)

            item = Gtk.MenuItem.new_with_label(_("Put on block list"))
            item.connect("activate", self.on_block_wallpaper)
            menu.append(item)

        item = Gtk.SeparatorMenuItem()
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Open main window"))
        if self.is_chwall_component_started("app"):
            item.set_sensitive(False)
        else:
            item.connect("activate", self.run_chwall_component, "app")
        menu.append(item)

        item = Gtk.CheckMenuItem.new_with_label(_("Always display this icon"))
        item.set_active(self.must_autostart)
        menu.append(item)
        item.connect("toggled", self.on_toggle_must_autostart)

        item = Gtk.MenuItem.new_with_label(_("Preferences"))
        item.connect("activate", self.show_preferences_dialog)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Report a bug"))
        item.connect("activate", self.show_report_a_bug)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("About Chwall"))
        item.connect("activate", self.show_about_dialog)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Quit"))
        item.connect("activate", self.kthxbye)
        menu.append(item)

        menu.show_all()
        self.tray.set_menu(menu)

    def open_daemon_submenu(self, _widget, menu):
        self.reload_config()
        dinfo = self.daemon_info()
        children = menu.get_children()
        daemon_state_label = dinfo["daemon-state-label"]
        if dinfo["next-change"] == -1:
            children[1].set_label(_("Start daemon"))
            children[1].connect(
                "activate", self.run_chwall_component, "daemon"
            )
        else:
            children[1].set_label(_("Stop daemon"))
            children[1].connect("activate", self.stop_daemon)
            daemon_state_label += " - " + dinfo["next-change-label"]

        children[0].set_label(daemon_state_label)

    def show_preferences_dialog(self, *opts):
        super().show_preferences_dialog(*opts)
        self.build_main_menu()
        self.tray.set_icon_full(self.main_icon(), "Chwall Icon")

    def on_change_wallpaper(self, widget, direction=False, block=False):
        super().on_change_wallpaper(widget, direction, block)
        self.build_main_menu()

    def on_favorite_wallpaper(self, widget):
        super().on_favorite_wallpaper(widget)
        self.build_main_menu()


if __name__ == "__main__":
    ChwallIndicator()
