import pkgutil
import subprocess
from importlib import import_module

from chwall.daemon import notify_daemon_if_any, notify_app_if_any, daemon_info
from chwall.utils import VERSION, read_config, write_config, cleanup_cache
from chwall.wallpaper import blacklist_wallpaper, pick_wallpaper

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class ChwallGui:
    def __init__(self):
        self.config = read_config()
        self.app = None

    def on_change_wallpaper(self, widget, direction=False):
        pick_wallpaper(self.config, direction)
        notify_daemon_if_any()
        if self.app is None:
            notify_app_if_any()

    def on_blacklist_wallpaper(self, widget):
        blacklist_wallpaper()
        self.on_change_wallpaper(widget)

    def run_chwall_component(self, _widget, component):
        if component == "daemon":
            # No need to fork, daemon already do that
            subprocess.run(["chwall-daemon"])
        else:
            subprocess.run(["chwall", "detach", component])

    def main_menu(self):
        menu = Gtk.Menu()

        dinfo = daemon_info(self.config)
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

        item = Gtk.SeparatorMenuItem()
        menu.append(item)

        item = Gtk.MenuItem.new_with_label(
            _("Cleanup broken entries in cache"))
        item.connect("activate", self.on_cleanup_cache)
        menu.append(item)

        return menu

    def get_flags_if_app(self):
        if self.app is not None:
            # flags 3 = MODAL | DESTROY_WITH_PARENT
            return 3
        return 0

    def on_cleanup_cache(self, _widget):
        deleted = cleanup_cache()
        if deleted < 2:
            message = _("{number} broken cache entry has been removed")
        else:
            message = _("{number} broken cache entries have been removed")
        # flags 3 = MODAL | DESTROY_WITH_PARENT
        dialog = Gtk.MessageDialog(self.app, self.get_flags_if_app(),
                                   Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                                   _("Cache cleanup"))
        dialog.set_icon_name("chwall")
        dialog.format_secondary_text(message.format(number=deleted))
        dialog.run()
        dialog.destroy()

    def toggle_show_notifications(self, widget, state):
        self.config["general"]["notify"] = state
        write_config(self.config)

    def toggle_activate_fetcher(self, widget, state, fetcher):
        if state and fetcher not in self.config["general"]["sources"]:
            self.config["general"]["sources"].append(fetcher)
            write_config(self.config)
        elif not state and fetcher in self.config["general"]["sources"]:
            self.config["general"]["sources"].remove(fetcher)
            write_config(self.config)

    def update_fetcher_opt(self, *args):
        # Call should be widget, ??, widget_type, fetcher, opt, kind
        print(args)
        largs = list(args)
        widget = largs[0]
        if type(args[1]).__name__ != "str":
            largs.pop(1)
        opts = {
            "widget": largs[1],
            "fetcher": largs[2],
            "opt": largs[3],
            "val": None,
            "kind": None
        }
        if len(largs) > 4:
            opts["kind"] = largs[4]
        print(opts)
        if opts["opt"] is None:
            return
        if opts["widget"] == "select":
            opts["val"] = widget.get_active_id()
        elif opts["widget"] == "number":
            opts["val"] = widget.get_value_as_int()
        elif opts["widget"] == "text":
            opts["val"] = widget.get_text()
        print(opts)
        if opts["val"] is None:
            return
        if opts["kind"] == "int":
            opts["val"] = int(opts["val"])
        if opts["fetcher"] not in self.config:
            self.config[opts["fetcher"]] = {}
        self.config[opts["fetcher"]][opts["opt"]] = opts["val"]
        write_config(self.config)

    def update_sleep_time(self, widget):
        self.config["general"]["sleep"] = widget.get_value_as_int() * 60
        write_config(self.config)

    def update_desktop_env(self, widget):
        self.config["general"]["desktop"] = widget.get_active_id()
        write_config(self.config)

    def update_lightdm_wall(self, widget):
        self.config["general"]["desktop"] = widget.get_filename()
        write_config(self.config)

    def show_preferences_dialog(self, widget):
        prefwin = Gtk.Dialog(
            _("Preferences"), self.app, self.get_flags_if_app(),
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        prefwin.set_icon_name("stock-preferences")

        box = prefwin.get_content_area()
        box.set_spacing(10)

        title = Gtk.Label()
        title.set_markup("<b><big>" + _("General") + "</big></b>")
        box.pack_start(title, False, False, 0)

        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        show_notifications = False
        if "notify" in self.config["general"]:
            show_notifications = self.config["general"]["notify"]
        label = Gtk.Label(_("Display notification when wallpaper changes"))
        prefbox.pack_start(label, False, False, 5)
        button = Gtk.Switch()
        button.set_active(show_notifications)
        button.connect("state-set", self.toggle_show_notifications)
        prefbox.pack_end(button, False, False, 5)
        box.pack_start(prefbox, True, True, 0)

        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(_("Time between each wallpaper change"))
        prefbox.pack_start(label, False, False, 5)
        sleep_time = int(self.config["general"]["sleep"] / 60)
        adj = Gtk.Adjustment(sleep_time, 5, 120, 1, 10, 0)
        button = Gtk.SpinButton()
        button.set_adjustment(adj)
        button.set_numeric(True)
        button.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
        button.connect("value-changed", self.update_sleep_time)
        prefbox.pack_end(button, False, False, 5)
        box.pack_start(prefbox, True, True, 0)

        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(_("Desktop environment"))
        prefbox.pack_start(label, False, False, 5)
        button = Gtk.ComboBoxText()
        button.append("gnome", "Gnome, Budgie, …")
        button.append("mate", "Mate")
        button.append("nitrogen", _("Use Nitrogen application"))
        if "desktop" in self.config["general"]:
            desktop = self.config["general"]["desktop"]
        else:
            desktop = "gnome"
        button.set_active_id(desktop)
        button.connect("changed", self.update_desktop_env)
        prefbox.pack_end(button, False, False, 5)
        box.pack_start(prefbox, True, True, 0)

        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(_("LightDM shared background path"))
        prefbox.pack_start(label, False, False, 5)
        button = Gtk.FileChooserButton.new(_("Select a file"),
                                           Gtk.FileChooserAction.OPEN)
        if "lightdm_wall" in self.config["general"]:
            button.set_filename(self.config["general"]["lightdm_wall"])
        button.connect("file-set", self.update_lightdm_wall)
        prefbox.pack_end(button, False, False, 5)
        box.pack_start(prefbox, True, True, 0)

        title = Gtk.Label()
        title.set_markup("<b><big>" + _("Pictures sources") + "</big></b>")
        box.pack_start(title, False, False, 0)

        activated_fetchers = self.config["general"]["sources"]
        fetcher_package = import_module("chwall.fetcher")
        fp_source = fetcher_package.__path__
        for fd in pkgutil.iter_modules(fp_source):
            fetcher = import_module("chwall.fetcher.{}".format(fd.name))
            if "preferences" not in dir(fetcher):
                continue
            fprefs = fetcher.preferences()
            prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            fetcher_name = fd.name
            if "name" in fprefs:
                fetcher_name = fprefs["name"]
            label = Gtk.Label()
            label.set_markup("<b>{}</b>".format(fetcher_name))
            prefbox.pack_start(label, False, False, 5)
            button = Gtk.Switch()
            button.set_active(fd.name in activated_fetchers)
            button.connect("state-set", self.toggle_activate_fetcher, fd.name)
            prefbox.pack_end(button, False, False, 5)
            box.pack_start(prefbox, True, True, 0)
            if "options" not in fprefs:
                sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
                box.pack_start(sep, False, False, 0)
                continue
            for opt in fprefs["options"]:
                if "widget" not in fprefs["options"][opt]:
                    continue
                prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                label = Gtk.Label(opt)
                prefbox.pack_start(label, False, False, 5)

                curval = None
                if fd.name in self.config and opt in self.config[fd.name]:
                    curval = self.config[fd.name][opt]
                elif "default" in fprefs["options"][opt]:
                    curval = fprefs["options"][opt]["default"]

                if fprefs["options"][opt]["widget"] == "select":
                    button = Gtk.ComboBoxText()
                    for v in fprefs["options"][opt]["values"]:
                        button.append(str(v), str(v))
                    if curval is not None:
                        button.set_active_id(str(curval))
                    button.connect("changed", self.update_fetcher_opt,
                                   "select", fd.name, opt,
                                   fprefs["options"][opt]["type"])
                    prefbox.pack_end(button, False, False, 5)
                elif fprefs["options"][opt]["widget"] == "number":
                    button = Gtk.SpinButton()
                    if curval is None:
                        curval = 0
                    adj = Gtk.Adjustment(curval, 800, 50000, 1, 10, 0)
                    button.set_adjustment(adj)
                    button.set_numeric(True)
                    button.connect("value-changed", self.update_fetcher_opt,
                                   "number", fd.name, opt)
                    prefbox.pack_end(button, False, False, 5)
                elif fprefs["options"][opt]["widget"] == "text":
                    button = Gtk.Entry()
                    if curval is not None:
                        button.set_text(curval)
                    button.connect("activate", self.update_fetcher_opt,
                                   "text", fd.name, opt)
                    button.connect("focus-out-event", self.update_fetcher_opt,
                                   "text", fd.name, opt)
                    prefbox.pack_end(button, True, True, 5)
                box.pack_start(prefbox, True, True, 0)
            sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            box.pack_start(sep, False, False, 0)

        prefwin.show_all()
        prefwin.run()
        prefwin.destroy()

    def show_about_dialog(self, widget):
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_destroy_with_parent(True)
        about_dialog.set_icon_name("chwall")
        about_dialog.set_name("Chwall")
        about_dialog.set_website("https://git.deparis.io/chwall/about")
        about_dialog.set_comments(_("Wallpaper Changer"))
        about_dialog.set_version(VERSION)
        about_dialog.set_copyright(_("Chwall is released under the WTFPL"))
        about_dialog.set_authors(["Étienne Deparis <etienne@depar.is>"])
        about_dialog.set_logo_icon_name("chwall")
        about_dialog.run()
        about_dialog.destroy()

    def kthxbye(self, *args):
        Gtk.main_quit()
