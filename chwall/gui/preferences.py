import os
import pkgutil
from importlib import import_module

from chwall.utils import read_config, write_config, reset_pending_list, \
                         cleanup_cache, ServiceFileManager, BASE_CACHE_PATH

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


def do_for_widget_by_name(name, callback, parent):
    if not callable(callback) or parent is None:
        return

    def _check_in_children(sibling, name, callback):
        if sibling.get_name() == name:
            callback(sibling)
        elif isinstance(sibling, Gtk.Container):
            do_for_widget_by_name(name, callback, sibling)

    parent.foreach(_check_in_children, name, callback)


class ConfigWrapper:
    def __init__(self):
        self.config = read_config()

    def __dir__(self):
        return dir(self.config)

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return repr(self.config)

    def __len__(self):
        return len(self.config)

    def __getitem__(self, key):
        return self.config[key]

    def __setitem__(self, key, value):
        self.config[key] = value

    def __delitem__(self, key):
        del self.config[key]

    def __iter__(self):
        return iter(self.config)

    def __contains__(self, key):
        return key in self.config

    def read_config_opt(self, path, opt, default=None):
        conf = self.config.copy()
        for p in path.split("."):
            conf = conf.get(p, {})
        return conf.get(opt, default)

    def write_config_opt(self, path, opt, value):
        def _browse_and_write_config_opt(config, path, opt, value):
            if path == "":
                # Last element, we can directly put opt in config
                config[opt] = value
                return config
            pe = path.split(".")
            p = pe.pop(0)
            config.setdefault(p, {})
            config[p] = _browse_and_write_config_opt(
                config[p], ".".join(pe), opt, value)
            return config

        self.config = _browse_and_write_config_opt(
            self.config.copy(), path, opt, value)
        self.write()

    def delete_config_opt(self, path, opt):
        def _browse_and_delete_config_opt(config, path, opt):
            if path == "":
                # Last element, we can directly delete put
                if opt in config:
                    del config[opt]
                return config
            pe = path.split(".")
            p = pe.pop(0)
            if p not in config:
                return config
            config[p] = _browse_and_delete_config_opt(
                config[p], ".".join(pe), opt)
            return config

        self.config = _browse_and_delete_config_opt(
            self.config.copy(), path, opt)
        self.write()

    def write(self):
        write_config(self.config)


class PrefDialog(Gtk.Dialog):
    def __init__(self, opener, flags):
        self.config = ConfigWrapper()
        super().__init__(_("Preferences"), opener, flags)
        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.set_icon_name("stock-preferences")

        self.sfm = ServiceFileManager()

        stack = Gtk.Stack()
        stack.add_titled(self.make_general_pane(), "general",
                         _("General"))
        stack.add_titled(self.make_sources_pane(), "sources",
                         _("Pictures sources"))
        stack.add_titled(self.make_advanced_pane(), "advanced",
                         _("Advanced"))

        box = self.get_content_area()
        box.set_spacing(10)
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        prefbox.set_center_widget(stack_switcher)
        box.pack_start(prefbox, False, False, 0)
        box.pack_start(stack, True, True, 0)
        self.show_all()

    def add_source_panel(self, fetcher_name, fetcher):
        sourceprefbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sourceprefbox.set_spacing(10)
        fprefs = fetcher.preferences()
        prefbox = self.make_fetcher_toggle_pref(fetcher_name, fprefs)
        sourceprefbox.pack_start(prefbox, False, False, 0)
        if "options" not in fprefs:
            self.make_source_frame(fetcher_name, fprefs, sourceprefbox)
            return
        if fetcher_name not in self.config:
            self.config[fetcher_name] = {}

        def translate_label(label, default):
            if label is not None:
                return label
            if default == "width":
                return _("Wallpaper width")
            elif default == "count":
                return _("Number of item to retrieve")
            elif default == "collections":
                return _("Collections")
            return default.capitalize()

        for opt in fprefs["options"]:
            if "widget" not in fprefs["options"][opt]:
                continue
            options = fprefs["options"][opt]
            prefbox = None
            label = translate_label(options.get("label"), opt)
            defval = options.get("default")
            if options["widget"] == "select":
                values = []
                for v in options["values"]:
                    if isinstance(v, tuple):
                        values.append(v)
                    else:
                        values.append((str(v), str(v)))
                prefbox = self.make_select_pref(
                    fetcher_name, opt, label, values,
                    default=str(defval), coerc=options.get("type"))
            elif options["widget"] == "text":
                prefbox = self.make_text_pref(fetcher_name, opt, label)
            elif options["widget"] == "number":
                prefbox = self.make_number_pref(
                    fetcher_name, opt, label,
                    adj=Gtk.Adjustment(defval or 0, 0, 100000, 1))
            elif options["widget"] == "list":
                prefbox = self.make_list_pref(
                    fetcher_name, opt, label, default=defval)
            elif options["widget"] == "toggle":
                prefbox = self.make_toggle_pref(
                    fetcher_name, opt, label, default=defval)
            if prefbox is not None:
                sourceprefbox.pack_start(prefbox, False, False, 0)
        self.make_source_frame(fetcher_name, fprefs, sourceprefbox)

    def make_source_frame(self, fetcher_name, fprefs, sourceprefbox):
        frame = Gtk.Frame()
        fetcher_label = Gtk.Label()
        cap_name = fetcher_name.capitalize()
        fetcher_label.set_markup(
            "<b>{}</b>".format(fprefs.get("name", cap_name)))
        frame.set_label_widget(fetcher_label)
        sourceprefbox.set_border_width(10)
        frame.add(sourceprefbox)
        self.sources_stack.add_titled(frame, fetcher_name, cap_name)

    def make_fetcher_toggle_pref(self, fetcher, fprefs):
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(label=_("Enable"))
        prefbox.pack_start(label, False, False, 10)
        button = Gtk.Switch()
        button.set_active(fetcher in self.config["general"]["sources"])

        def on_toggle_fetcher_set(widget, state, fetcher):
            if state and fetcher not in self.config["general"]["sources"]:
                self.config["general"]["sources"].append(fetcher)
                self.config.write()
            elif not state and fetcher in self.config["general"]["sources"]:
                self.config["general"]["sources"].remove(fetcher)
                self.config.write()

        button.connect("state-set", on_toggle_fetcher_set, fetcher)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_prefbox_with_label(self, label):
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preflabel = Gtk.Label(label)
        prefbox.pack_start(preflabel, False, False, 10)
        return prefbox

    def make_toggle_pref(self, path, opt, label, **kwargs):
        default = kwargs.get("default")
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Switch()
        current_value = self.config.read_config_opt(path, opt, default)
        if current_value is not None:
            button.set_active(current_value)

        def on_toggle_state_set(widget, state):
            self.config.write_config_opt(path, opt, state)

        button.connect("state-set", on_toggle_state_set)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_select_pref(self, path, opt, label, values, **kwargs):
        default = kwargs.get("default")
        coerc = kwargs.get("coerc")
        callback = kwargs.get("callback")
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.ComboBoxText()
        for key, val in values:
            button.append(key, val)
        if opt in self.config[path]:
            button.set_active_id(str(self.config[path][opt]))
        elif default is not None:
            button.set_active_id(default)

        def on_select_changed(widget):
            val = widget.get_active_id()
            if coerc == "int":
                self.config[path][opt] = int(val)
            else:
                self.config[path][opt] = val
            self.config.write()
            if callback is not None and callable(callback):
                callback(self.config[path][opt])

        button.connect("changed", on_select_changed)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_text_pref(self, path, opt, label, **kwargs):
        default = kwargs.get("default")
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Entry()
        if opt in self.config[path]:
            button.set_text(self.config[path][opt])
        elif default is not None:
            button.set_text(default)

        def on_text_edited(widget, _event):
            self.config[path][opt] = widget.get_text().strip()
            if self.config[path][opt] == "":
                del self.config[path][opt]
            self.config.write()

        button.connect("activate", on_text_edited)
        button.connect("focus-out-event", on_text_edited)
        prefbox.pack_end(button, True, True, 10)
        return prefbox

    def make_number_pref(self, path, opt, label, **kwargs):
        adj = kwargs.get("adj")
        factor = kwargs.get("factor", 1)
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.SpinButton()
        current_value = self.config.read_config_opt(
            path, opt, kwargs.get("default"))
        if adj is not None:
            button.set_adjustment(adj)
        elif current_value is not None:
            button.set_adjustment(Gtk.Adjustment(current_value, 0, 100000, 1))
        button.set_numeric(True)
        button.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

        def on_spin_value_changed(widget):
            new_val = widget.get_value_as_int() * factor
            self.config.write_config_opt(path, opt, new_val)

        button.connect("value-changed", on_spin_value_changed)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_list_pref(self, path, opt, label, **kwargs):
        defaults = kwargs.get("default", [])
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        liststore = Gtk.ListStore(str)
        if opt in self.config[path]:
            for val in self.config[path][opt]:
                liststore.append([val])
        elif defaults is not None:
            if type(defaults).__name__ != "list":
                liststore.append([defaults])
            else:
                for val in defaults:
                    liststore.append([val])
        if len(liststore) == 0:
            # Append an empty value to draw column name
            liststore.append([""])

        def save_model_in_config():
            vals = []
            for row in liststore:
                ts = liststore[row.path][0].strip()
                if ts == "" or ts in vals:
                    continue
                vals.append(ts)
            if len(vals) > 0:
                self.config[path][opt] = vals
            elif opt in self.config[path]:
                del self.config[path][opt]
            self.config.write()

        def on_cell_edited(widget, storepath, text):
            if text.strip() != "":
                liststore[storepath][0] = text
            elif len(liststore) > 1:
                # We do not remove the last empty child.
                liststore.remove(liststore.get_iter(storepath))
            save_model_in_config()

        def on_remove_clicked(_widget):
            s = treeview.get_selection()
            if s is None:
                return
            model, storepaths = s.get_selected_rows()
            for p in storepaths:
                model.remove(model.get_iter(p))
            save_model_in_config()
            if len(liststore) > 0:
                return
            # Always keep at list one empty value
            liststore.append([""])

        def on_add_clicked(_widget):
            if len(liststore) == 1 and liststore[liststore[0].path][0] == "":
                # We are looking at an empty list, thus we override this first
                # item.
                storepath = liststore[0].path
            else:
                storepath = liststore.get_path(liststore.append([""]))
            treeview.set_cursor_on_cell(storepath, column_text,
                                        renderer_text, True)

        treeview = Gtk.TreeView(model=liststore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("editable", True)

        renderer_text.connect("edited", on_cell_edited)
        column_text = Gtk.TreeViewColumn(label, renderer_text, text=0)
        treeview.append_column(column_text)

        listscrollbox = Gtk.ScrolledWindow()
        listscrollbox.add(treeview)
        listscrollbox.set_size_request(-1, 200)
        listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        listbox.pack_start(listscrollbox, True, True, 0)

        control_box = Gtk.ActionBar()
        button = Gtk.Button.new_from_icon_name(
            "list-remove-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        button.set_tooltip_text(_("Remove"))
        button.connect("clicked", on_remove_clicked)
        control_box.pack_start(button)
        button = Gtk.Button.new_from_icon_name(
            "list-add-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        button.set_tooltip_text(_("Add"))
        button.connect("clicked", on_add_clicked)
        control_box.pack_start(button)
        listbox.pack_end(control_box, False, False, 0)

        prefbox.pack_end(listbox, True, True, 0)
        return prefbox

    def make_button_row(self, label, button_label, action, style=None, *opts):
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Button()
        button.set_label(button_label)
        if style is not None:
            button.get_style_context().add_class(style)
        button.connect("clicked", action, *opts)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def shared_wall_option_pref(self):
        def on_update_shared_wall(widget):
            ld_path = widget.get_filename()
            self.config.write_config_opt("general.shared", "path", ld_path)

        prefbox = self.make_prefbox_with_label(
            _("Shared background path"))
        button = Gtk.FileChooserButton.new(
            _("Select a file"), Gtk.FileChooserAction.OPEN)
        ld_path = self.config.read_config_opt("general.shared", "path")
        if ld_path is not None and ld_path != "":
            button.set_filename(ld_path)
        button.connect("file-set", on_update_shared_wall)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_sources_pane(self):
        self.sources_stack = Gtk.Stack()

        fetcher_package = import_module("chwall.fetcher")
        fp_source = fetcher_package.__path__
        for fd in pkgutil.iter_modules(fp_source):
            fetcher = import_module("chwall.fetcher.{}".format(fd.name))
            if "preferences" not in dir(fetcher):
                continue
            self.add_source_panel(fd.name, fetcher)

        sources_switcher = Gtk.StackSidebar()
        sources_switcher.set_stack(self.sources_stack)
        sources_switcher.set_size_request(150, -1)
        sourcesbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sourcesbox.pack_start(sources_switcher, False, False, 5)
        sourcesbox.pack_start(self.sources_stack, True, True, 5)
        return sourcesbox

    def make_general_pane(self):
        genbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        genbox.set_border_width(10)
        genbox.set_spacing(10)

        prefbox = self.make_toggle_pref(
            "general", "notify",
            _("Display notification when wallpaper changes"))
        genbox.pack_start(prefbox, False, False, 0)

        sleep_time = int(self.config["general"]["sleep"] / 60)
        prefbox = self.make_number_pref(
            "general", "sleep", _("Time between each wallpaper change"),
            adj=Gtk.Adjustment(sleep_time, 5, 120, 1), factor=60)
        genbox.pack_start(prefbox, False, False, 0)

        environments = [("gnome", "Gnome, Budgie, …"), ("mate", "Mate"),
                        ("nitrogen", _("Use Nitrogen application"))]
        prefbox = self.make_select_pref(
            "general", "desktop", _("Desktop environment"),
            environments, default="gnome")
        genbox.pack_start(prefbox, False, False, 0)

        prefbox = self.shared_wall_option_pref()
        genbox.pack_start(prefbox, False, False, 0)

        prefbox = self.make_toggle_pref(
            "general.shared", "blur", _("Blur shared background"),
            default=False)
        genbox.pack_start(prefbox, False, False, 0)

        daemonbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        daemonbox.set_border_width(10)
        daemonbox.set_spacing(10)

        if self.sfm.systemd_version is not None:
            prefbox = self.make_prefbox_with_label(
                _("""
You have two options to launch Chwall daemon when your user session starts:
  - with an XDG autostart application file;
  - with a systemd service file (you need to install it first).

If you don't know what to do, XDG autostart should be the safest choice,
as it is the more classical way of doing so.
""").strip())
            daemonbox.pack_start(prefbox, False, False, 0)

        classic_daemon_box = self.make_prefbox_with_label(
            _("Launch Chwall daemon with an XDG autostart file "
              "when your session starts"))
        button = Gtk.Switch()
        button.set_active(self.sfm.xdg_autostart_file_exists())

        def on_toggle_classic_set(widget, state):
            if state:
                self.sfm.xdg_autostart_file(
                    "daemon", _("Chwall daemon"),
                    _("Start Chwall daemon"), True
                )
            else:
                self.sfm.remove_xdg_autostart_file()
            do_for_widget_by_name(
                "systemd-enable",
                lambda w: w.set_sensitive(not state),
                self)

        button.connect("state-set", on_toggle_classic_set)
        classic_daemon_box.pack_end(button, False, False, 10)
        daemonbox.pack_start(classic_daemon_box, False, False, 0)
        classic_daemon_box.set_name("xdg-autostart-install")

        if self.sfm.systemd_version is not None:
            service_installed = self.sfm.systemd_service_file_exists()

            def on_create_systemd_service(widget):
                self.sfm.systemd_service_file(True)
                parent = widget.get_parent()
                parent.set_no_show_all(True)
                parent.hide()

                def _show_systemd_widget(widget):
                    widget.set_no_show_all(False)
                    widget.show_all()

                do_for_widget_by_name(
                    "systemd-enable", _show_systemd_widget,
                    parent.get_parent())
                do_for_widget_by_name(
                    "systemd-remove", _show_systemd_widget, self)

            prefbox = self.make_button_row(
                _("Install the systemd service file before using it "
                  "to start Chwall daemon"),
                _("Create"),
                on_create_systemd_service
            )
            daemonbox.pack_start(prefbox, False, False, 0)
            prefbox.set_name("systemd-install")

            if service_installed:
                prefbox.set_no_show_all(True)

            service_enabled = self.sfm.systemd_service_file_exists(True)
            if service_enabled:
                classic_daemon_box.set_sensitive(False)

            prefbox = self.make_prefbox_with_label(
                _("Launch Chwall daemon with systemd when your "
                  "session starts"))
            enable_systemd_btn = Gtk.Switch()
            enable_systemd_btn.set_active(service_enabled)

            def on_toggle_systemd_state(widget, state):
                self.sfm.systemd_service_toggle(state)
                classic_daemon_box.set_sensitive(not state)

            enable_systemd_btn.connect(
                "state-set", on_toggle_systemd_state)
            prefbox.pack_end(enable_systemd_btn, False, False, 10)
            daemonbox.pack_start(prefbox, False, False, 0)
            prefbox.set_name("systemd-enable")
            prefbox.set_no_show_all(not service_installed)

        framebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        framebox.set_spacing(10)
        framebox.set_border_width(10)

        frame = Gtk.Frame()
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>{}</b>".format(_("Behavior")))
        frame.set_label_widget(frame_label)
        frame.add(genbox)
        framebox.pack_start(frame, False, False, 0)

        frame = Gtk.Frame()
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>{}</b>".format(_("Daemon")))
        frame.set_label_widget(frame_label)
        frame.add(daemonbox)
        framebox.pack_start(frame, False, False, 0)

        return framebox

    def make_advanced_pane(self):
        genbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        genbox.set_border_width(10)
        genbox.set_spacing(10)

        prefbox = self.make_button_row(
            _("Fetch a new wallpapers list the next time wallpaper change"),
            _("Empty current pending list"),
            reset_pending_list
        )
        genbox.pack_start(prefbox, False, False, 0)

        def on_cleanup_cache(widget, update_label, clear_all=False):
            deleted = cleanup_cache(clear_all)
            if deleted == 0:
                return

            message = gettext.ngettext(
                "{number} cache entry has been removed.",
                "{number} cache entries have been removed.",
                deleted
            ).format(number=deleted)

            widget.get_parent().foreach(update_label)

            # flags 3 = MODAL | DESTROY_WITH_PARENT
            dialog = Gtk.MessageDialog(
                self, 3, Gtk.MessageType.INFO, Gtk.ButtonsType.OK,
                _("Cache cleanup")
            )
            dialog.set_icon_name("chwall")
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()

        pic_cache = "{}/pictures".format(BASE_CACHE_PATH)
        broken_files = 0
        if os.path.exists(pic_cache):
            for pic in os.scandir(pic_cache):
                if pic.stat().st_size == 0:
                    broken_files += 1

        label = gettext.ngettext(
                "{number} broken picture currently in cache",
                "{number} broken pictures currently in cache",
                broken_files
        ).format(number=broken_files)

        def _update_broken_label(sibling):
            if isinstance(sibling, Gtk.Label):
                sibling.set_label(
                    gettext.ngettext(
                        "{number} broken picture currently in cache",
                        "{number} broken pictures currently in cache",
                        0
                    ).format(number=0)
                )

        prefbox = self.make_button_row(
            label,
            _("Clear broken pictures"),
            on_cleanup_cache,
            "destructive-action",
            _update_broken_label
        )
        genbox.pack_start(prefbox, False, False, 0)

        cache_total = 0
        if os.path.exists(pic_cache):
            for pic in os.scandir(pic_cache):
                cache_total += pic.stat().st_size
        cache_total = cache_total / 1000
        if cache_total > 1000000:
            cache_size = "{} Go".format(str(round(cache_total/1000000, 2)))
        elif cache_total > 1000:
            cache_size = "{} Mo".format(str(round(cache_total/1000, 2)))
        else:
            cache_size = "{} ko".format(str(round(cache_total, 2)))

        def _update_empty_label(sibling):
            if isinstance(sibling, Gtk.Label):
                sibling.set_label(
                    _("Picture cache use {size}").format(size="0.0 ko")
                )

        prefbox = self.make_button_row(
            _("Picture cache use {size}").format(size=cache_size),
            _("Clear picture cache"),
            on_cleanup_cache,
            "destructive-action",
            _update_empty_label,
            True
        )
        genbox.pack_start(prefbox, False, False, 0)

        sharedbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sharedbox.set_border_width(10)
        sharedbox.set_spacing(10)

        prefbox = self.make_number_pref(
            "general.shared", "blur_radius", _("Blur radius"), default=20)
        sharedbox.pack_start(prefbox, False, False, 0)

        daemonbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        daemonbox.set_border_width(10)
        daemonbox.set_spacing(10)

        prefbox = self.make_text_pref(
            "general", "display", _("X Display in use"), default=":0")
        daemonbox.pack_start(prefbox, False, False, 0)

        def on_remove_systemd_service(widget):
            self.sfm.remove_systemd_service_file()
            widget.get_parent().set_visible(False)
            do_for_widget_by_name(
                "xdg-autostart-install",
                lambda w: w.set_sensitive(True),
                self)

            def _hide_systemd_enable(widget):
                widget.set_no_show_all(True)
                widget.hide()

            do_for_widget_by_name(
                "systemd-enable", _hide_systemd_enable, self)

            def _show_systemd_install(widget):
                widget.set_no_show_all(False)
                widget.show_all()

            do_for_widget_by_name(
                "systemd-install", _show_systemd_install, self)

        prefbox = self.make_button_row(
            _("Remove systemd service file"),
            _("Remove"),
            on_remove_systemd_service,
            "destructive-action"
        )
        daemonbox.pack_start(prefbox, False, False, 0)
        prefbox.set_name("systemd-remove")
        prefbox.set_no_show_all(
            self.sfm.systemd_version is None
            or not self.sfm.systemd_service_file_exists())

        prefbox = self.make_select_pref(
            "general", "log_level", _("Log level"),
            [(level, level)
             for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]],
            default="WARNING")
        daemonbox.pack_start(prefbox, False, False, 0)

        framebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        framebox.set_spacing(10)
        framebox.set_border_width(10)

        frame = Gtk.Frame()
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>{}</b>".format(_("Cache management")))
        frame.set_label_widget(frame_label)
        frame.add(genbox)
        framebox.pack_start(frame, False, False, 0)

        frame = Gtk.Frame()
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>{}</b>".format(_("Shared background")))
        frame.set_label_widget(frame_label)
        frame.add(sharedbox)
        framebox.pack_start(frame, False, False, 0)

        frame = Gtk.Frame()
        frame_label = Gtk.Label()
        frame_label.set_markup("<b>{}</b>".format(_("Daemon")))
        frame.set_label_widget(frame_label)
        frame.add(daemonbox)
        framebox.pack_start(frame, False, False, 0)

        return framebox
