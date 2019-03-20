#!/usr/bin/env python3

import os
import html
import signal

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info

import gi
gi.require_version('Gtk', '3.0')  # noqa: E402
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallApp(ChwallGui):
    def __init__(self):
        super().__init__()
        self.app = Gtk.Window(title="Chwall")
        self.app.set_icon_name("chwall")
        self.app.set_resizable(False)
        self.app.connect("destroy", self.kthxbye)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "Chwall"

        button = Gtk.Button.new_from_icon_name(
            "gtk-about", Gtk.IconSize.BUTTON)
        button.set_tooltip_text(_("About"))
        button.connect("clicked", self.show_about_dialog)
        hb.pack_end(button)

        button = Gtk.ToggleButton()
        button.set_image(Gtk.Image.new_from_icon_name(
            "gtk-preferences", Gtk.IconSize.BUTTON))
        button.set_tooltip_text(_("Preferences"))
        button.connect("toggled", self.show_main_menu)
        hb.pack_end(button)

        self.app.set_titlebar(hb)

        app_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.wallpaper = Gtk.Image()
        app_box.add(self.wallpaper)

        control_box = Gtk.ActionBar()

        button = Gtk.Button.new_from_icon_name(
            "gtk-go-back", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Previous wallpaper"))
        button.connect("clicked", self.on_change_wallpaper, True)
        control_box.pack_start(button)

        button = Gtk.Button.new_from_icon_name(
            "gtk-go-forward", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Next wallpaper"))
        button.connect("clicked", self.on_change_wallpaper)
        control_box.pack_start(button)

        self.walldesc = Gtk.Label()
        self.walldesc.set_justify(Gtk.Justification.CENTER)
        self.walldesc.set_line_wrap(True)
        control_box.set_center_widget(self.walldesc)

        button = Gtk.Button.new_from_icon_name(
            "gtk-delete", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Blacklist"))
        button.connect("clicked", self.on_blacklist_wallpaper)
        control_box.pack_end(button)

        app_box.add(control_box)

        self.app.add(app_box)

        self.app.show_all()

        self.update_wall_box()

    def update_wall_box(self):
        wallinfo = current_wallpaper_info()

        label_str = "<a href=\"{link}\">{text}</a>".format(
            link=html.escape(wallinfo["remote-uri"]),
            text=wallinfo["description"])
        self.walldesc.set_markup(label_str)
        self.walldesc.grab_focus()
        # Show it now to reserve correct size
        self.walldesc.show()

        # Now we can use this width to display the wallpaper itself
        size_data = self.app.get_preferred_size()
        # Get `natural_size`
        width = size_data[1].width
        if width < 800:
            width = 800
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            wallinfo["local-picture-path"], width, 600, True)
        self.wallpaper.set_from_pixbuf(pixbuf)
        self.wallpaper.show()

        self.app.resize(width, size_data[1].height)

    def on_change_wallpaper(self, widget, direction=False):
        super().on_change_wallpaper(widget, direction)
        self.update_wall_box()

    def show_main_menu(self, widget):
        if not widget.get_active():
            return

        menu = self.main_menu()

        item = Gtk.MenuItem.new_with_label(_("Display notification icon"))
        item.connect("activate", self.run_chwall_component, "icon")
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Preferences"))
        item.connect("activate", self.show_preferences_dialog)
        menu.append(item)

        menu.show_all()
        menu.connect("hide", lambda _w, b: b.set_active(False), widget)
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST,
                             Gdk.Gravity.NORTH_WEST, None)


def generate_desktop_file(localedir="./locale"):
    lng_attrs = {
        "gname": [],
        "comment": [],
        "next_name": [],
        "prev_name": []
    }
    for lng in os.listdir("locale"):
        if lng in ["chwall.pot", "en"]:
            continue
        glng = gettext.translation(
            "chwall", localedir=localedir,
            languages=[lng])
        glng.install()
        _ = glng.gettext
        lng_attrs["gname"].append(
            "GenericName[{lang}]={key}".format(
                lang=lng, key=_("Wallpaper Changer")))
        lng_attrs["comment"].append(
            "Comment[{lang}]={key}".format(
                lang=lng,
                key=_("Main window of the Chwall wallpaper changer")))
        lng_attrs["next_name"].append(
            "Name[{lang}]={key}".format(
                lang=lng,
                key=_("Next wallpaper")))
        lng_attrs["prev_name"].append(
            "Name[{lang}]={key}".format(
                lang=lng,
                key=_("Previous wallpaper")))
    df_content = ["[Desktop Entry]"]
    df_content.append("Name=Chwall")
    df_content.append("GenericName=Wallpaper Changer")
    for line in lng_attrs["gname"]:
        df_content.append(line)
    for line in lng_attrs["comment"]:
        df_content.append(line)
    df_content = "\n".join(df_content)
    df_content += """
Exec=chwall-app
Icon=chwall
Terminal=false
Type=Application
Categories=GTK;GNOME;Utility;
StartupNotify=false
Actions=Next;Previous;
"""
    actions = ["", "[Desktop Action Next]", "Exec=chwall next",
               "Name=Next wallpaper"]
    for line in lng_attrs["next_name"]:
        actions.append(line)
    actions += ["", "[Desktop Action Previous]", "Exec=chwall previous",
                "Name=Previous wallpaper"]
    for line in lng_attrs["prev_name"]:
        actions.append(line)
    df_content += "\n".join(actions)

    with open("chwall-app.desktop", "w") as f:
        f.write(df_content)


def start_app():
    # Install signal handlers
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM,
                         Gtk.main_quit, None)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,
                         Gtk.main_quit, None)
    ChwallApp()
    Gtk.main()


if __name__ == "__main__":
    start_app()
