#!/usr/bin/env python3

import os
import html
import signal

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info
from chwall.daemon import notify_daemon_if_any

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
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

        button = Gtk.ToggleButton()
        button.set_image(Gtk.Image.new_from_icon_name(
            "open-menu-symbolic", Gtk.IconSize.BUTTON))
        button.set_tooltip_text(_("Preferences"))
        button.connect("toggled", self.show_main_menu)
        hb.pack_end(button)

        self.app.set_titlebar(hb)

        app_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notif_reset = Gtk.InfoBar()
        self.notif_reset.set_message_type(Gtk.MessageType.WARNING)
        notif_box = self.notif_reset.get_content_area()
        notif_box.add(Gtk.Label(_("Wallpapers list may be built again. It may take a long time if you have a lot of sources enabled. Please be patient.")))  # noqa
        app_box.pack_start(self.notif_reset, False, False, 0)

        self.wallpaper = Gtk.Image()
        app_box.pack_start(self.wallpaper, True, True, 0)

        control_box = Gtk.ActionBar()

        button = Gtk.Button.new_from_icon_name(
            "media-skip-backward-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Previous wallpaper"))
        button.connect("clicked", self.on_change_wallpaper, True)
        control_box.pack_start(button)

        button = Gtk.Button.new()
        self.decorate_play_stop_button(button, True)
        button.connect("clicked", self.on_play_stop_clicked)
        control_box.pack_start(button)

        button = Gtk.Button.new_from_icon_name(
            "media-skip-forward-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Next wallpaper"))
        button.connect("clicked", self.on_change_wallpaper)
        control_box.pack_start(button)

        self.walldesc = Gtk.Label()
        self.walldesc.set_justify(Gtk.Justification.CENTER)
        self.walldesc.set_line_wrap(True)
        control_box.set_center_widget(self.walldesc)

        button = Gtk.Button.new_from_icon_name(
            "edit-delete", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Blacklist"))
        button.connect("clicked", self.on_blacklist_wallpaper)
        control_box.pack_end(button)

        app_box.pack_end(control_box, False, False, 0)

        self.app.add(app_box)

        self.app.show_all()

        self.update_wall_box()
        signal.signal(signal.SIGUSR1, self.update_wall_box)

    def update_wall_box(self, _signo=None, _stack_frame=None):
        self.notif_reset.set_revealed(False)
        self.notif_reset.hide()
        wallinfo = current_wallpaper_info()
        if wallinfo["local-picture-path"] is None:
            self.walldesc.set_markup("<i>{}</i>".format(
                _("Current wallpaper is not managed by Chwall")))
            self.wallpaper.set_from_icon_name(
                "preferences-desktop-wallpaper-symbolic", Gtk.IconSize.DIALOG)
            return

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

    def show_main_menu(self, widget):
        if not widget.get_active():
            return

        menu = Gtk.Menu()

        item = Gtk.MenuItem.new_with_label(
            _("Cleanup broken entries in cache"))
        item.connect("activate", self.on_cleanup_cache)
        menu.append(item)

        sep = Gtk.SeparatorMenuItem()
        menu.append(sep)

        item = Gtk.MenuItem.new_with_label(_("Display notification icon"))
        item.connect("activate", self.run_chwall_component, "icon")
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Preferences"))
        item.connect("activate", self.show_preferences_dialog)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("About Chwall"))
        item.connect("activate", self.show_about_dialog)
        menu.append(item)

        menu.show_all()
        menu.connect("hide", lambda _w, b: b.set_active(False), widget)
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST,
                             Gdk.Gravity.NORTH_WEST, None)

    def decorate_play_stop_button(self, widget, startup=False):
        dinfo = self.daemon_info()
        # At startup we need to draw the real state of the daemon, but later,
        # this function is called *before* the state change, thus it must
        # reflect the future state of the daemon
        if startup:
            current_state = dinfo["daemon-state"]
        elif dinfo["daemon-state"] == "started":
            current_state = "stopped"
        else:
            current_state = "started"
        if current_state == "started":
            widget.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-stop-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
            widget.set_tooltip_text(_("Stop daemon"))
        else:
            widget.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.LARGE_TOOLBAR))
            widget.set_tooltip_text(_("Start daemon"))
        return current_state

    def on_play_stop_clicked(self, widget):
        # When called after a click, this method return the future state. Then
        # we should actually kill the daemon if the *current_state* is
        # *stopped*.
        if self.decorate_play_stop_button(widget) == "stopped":
            # 15 == signal.SIGTERM
            notify_daemon_if_any(15)
            return
        # Else we should start the server
        self.notif_reset.show()
        self.notif_reset.set_revealed(True)
        self.run_chwall_component(widget, "daemon")


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
