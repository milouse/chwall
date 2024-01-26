#!/usr/bin/env python3

import html
import signal

from chwall.gui.shared import ChwallGui
from chwall.wallpaper import current_wallpaper_info
from chwall.utils import reset_pending_list

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

import gettext  # noqa: E402
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallApp(ChwallGui):
    def __init__(self):
        super().__init__()
        self.component = "app"
        self.app = Gtk.Window(title="Chwall")
        self.app.set_icon_name("chwall")
        self.app.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.app.set_resizable(False)
        self.app.connect("destroy", self.kthxbye)
        self.build_main_window()
        self.update_wall_box()
        signal.signal(signal.SIGUSR1, self.update_wall_box)
        self.start()

    def build_main_window(self):
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
        notif_label = Gtk.Label()
        notif_label.set_text(
            _("Wallpapers list may be built again. It may take a long time "
              "if you have a lot of sources enabled. Please be patient.")
        )
        notif_box.add(notif_label)
        app_box.pack_start(self.notif_reset, False, False, 0)

        self.wallpaper = Gtk.Image()
        app_box.pack_start(self.wallpaper, True, True, 0)

        control_box = Gtk.ActionBar()

        button = Gtk.Button.new_from_icon_name(
            "media-skip-backward-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Previous wallpaper"))
        button.connect("clicked", self.on_change_wallpaper, True)
        control_box.pack_start(button)

        self.daemon_play_pause_button = Gtk.Button.new()
        self.decorate_play_pause_button(True)
        self.daemon_play_pause_button.connect(
            "clicked", self.on_play_pause_clicked)
        control_box.pack_start(self.daemon_play_pause_button)

        button = Gtk.Button.new_from_icon_name(
            "media-skip-forward-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Next wallpaper"))
        button.connect("clicked", self.on_change_wallpaper)
        control_box.pack_start(button)

        button = Gtk.Separator()
        control_box.pack_start(button)

        button = Gtk.Button.new_from_icon_name(
            "media-playback-stop-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Stop daemon and erase pending list"))
        button.connect("clicked", self.on_stop_clicked)
        control_box.pack_start(button)

        button = Gtk.Separator()
        control_box.pack_start(button)

        self.favorite_button = Gtk.Button.new_from_icon_name(
            "bookmark-new", Gtk.IconSize.LARGE_TOOLBAR)
        control_box.pack_start(self.favorite_button)

        self.walldesc = Gtk.Label(
            hexpand=True, halign=Gtk.Align.CENTER,
            justify=Gtk.Justification.CENTER,
            wrap=True, single_line_mode=True
        )
        self.walldesc.set_markup(
            "<a href=\"https://git.umaneti.net/chwall/\">Chwall</a>"
        )
        control_box.set_center_widget(self.walldesc)

        button = Gtk.Button.new_from_icon_name(
            "edit-delete", Gtk.IconSize.LARGE_TOOLBAR)
        button.set_tooltip_text(_("Put on block list"))
        button.connect("clicked", self.on_block_wallpaper)
        control_box.pack_end(button)

        app_box.pack_end(control_box, False, False, 0)
        self.app.add(app_box)

        self.app.show_all()

    def update_wall_box(self, *args):
        self.notif_reset.set_revealed(False)
        self.notif_reset.hide()
        wallinfo = current_wallpaper_info()
        if wallinfo["type"] == "":
            self.walldesc.set_markup("<i>{}</i>".format(
                _("Current wallpaper is not managed by Chwall")))
            self.wallpaper.set_from_icon_name(
                "preferences-desktop-wallpaper-symbolic", Gtk.IconSize.DIALOG)
            self.favorite_button.set_sensitive(False)
            self.favorite_button.set_tooltip_text(
                _("Current wallpaper is not managed by Chwall"))
            return

        try:
            if self.is_current_wall_favorite(wallinfo):
                self.favorite_button.set_sensitive(False)
                self.favorite_button.set_tooltip_text(_("Already a favorite"))
            else:
                self.favorite_button.set_sensitive(True)
                self.favorite_button.set_tooltip_text(_("Save as favorite"))
                self.favorite_button.connect(
                    "clicked", self.on_favorite_wallpaper)
        except PermissionError:
            self.favorite_button.set_sensitive(False)
            self.favorite_button.set_tooltip_text(
                _("Error accessing the favorites folder"))

        label_str = "<a href=\"{link}\">{text}</a>".format(
            link=html.escape(wallinfo["remote-uri"]),
            text=wallinfo["description"].replace("&", "&amp;"))
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
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                wallinfo["local-picture-path"], width, 600, True)
            self.wallpaper.set_from_pixbuf(pixbuf)
        except GLib.Error:
            self.wallpaper.set_from_icon_name(
                "image-missing", Gtk.IconSize.DIALOG)
        self.wallpaper.show()

        self.app.resize(width, size_data[1].height)

    def show_main_menu(self, widget):
        if not widget.get_active():
            return

        menu = Gtk.Menu()

        dinfo = self.daemon_info()
        if dinfo["next-change"] != -1:
            item = Gtk.MenuItem.new_with_label(
                dinfo["next-change-label"])
            item.set_sensitive(False)
            menu.append(item)
            item = Gtk.SeparatorMenuItem()
            menu.append(item)

        item = Gtk.MenuItem.new_with_label(
            _("Display an icon in the system tray"))
        if self.is_chwall_component_started("indicator"):
            item.set_sensitive(False)
        else:
            item.connect("activate", self.run_chwall_component, "indicator")
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("Preferences"))
        item.connect("activate", self.show_preferences_dialog, self.app)
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(_("About Chwall"))
        item.connect("activate", self.show_about_dialog)
        menu.append(item)

        menu.show_all()
        menu.connect("hide", lambda _w, b: b.set_active(False), widget)
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST,
                             Gdk.Gravity.NORTH_WEST, None)

    def decorate_play_pause_button(self, startup=False):
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
            self.daemon_play_pause_button.set_image(
                Gtk.Image.new_from_icon_name("media-playback-pause-symbolic",
                                             Gtk.IconSize.LARGE_TOOLBAR))
            self.daemon_play_pause_button.set_tooltip_text(_("Stop daemon"))
        else:
            self.daemon_play_pause_button.set_image(
                Gtk.Image.new_from_icon_name("media-playback-start-symbolic",
                                             Gtk.IconSize.LARGE_TOOLBAR))
            self.daemon_play_pause_button.set_tooltip_text(_("Start daemon"))
        return current_state

    def on_play_pause_clicked(self, widget):
        # When called after a click, this method return the future state. Then
        # we should actually kill the daemon if the *current_state* is
        # *stopped*.
        if self.decorate_play_pause_button() == "stopped":
            self.stop_daemon()
            return
        # Else we should start the server
        self.notif_reset.show()
        self.notif_reset.set_revealed(True)
        self.run_chwall_component(widget, "daemon")

    def on_stop_clicked(self, _widget):
        self.stop_daemon()
        reset_pending_list()
        self.decorate_play_pause_button(True)

    def on_favorite_wallpaper(self, widget):
        super().on_favorite_wallpaper(widget)
        if self.current_is_favorite:
            self.favorite_button.set_sensitive(False)
            self.favorite_button.set_tooltip_text(_("Already a favorite"))


if __name__ == "__main__":
    ChwallApp()
