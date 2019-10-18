import os
import pkgutil
from importlib import import_module

from chwall.utils import write_config, ServiceFileManager

import gi
gi.require_version("Gtk", "3.0")  # noqa: E402
from gi.repository import Gtk

import gettext
# Uncomment the following line during development.
# Please, be cautious to NOT commit the following line uncommented.
# gettext.bindtextdomain("chwall", "./locale")
gettext.textdomain("chwall")
_ = gettext.gettext


class PrefDialog(Gtk.Dialog):
    def __init__(self, opener, flags, config):
        self.config = config
        super().__init__(
            _("Preferences"), opener, flags,
            (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_icon_name("stock-preferences")

        stack = Gtk.Stack()
        stack.add_titled(self.make_general_pane(), "general",
                         _("General"))
        stack.add_titled(self.make_sources_pane(), "sources",
                         _("Pictures sources"))

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
                    fetcher_name, opt, label, values, str(defval),
                    options.get("type"))
            elif options["widget"] == "text":
                prefbox = self.make_text_pref(fetcher_name, opt, label)
            elif options["widget"] == "number":
                prefbox = self.make_number_pref(
                    fetcher_name, opt, label,
                    Gtk.Adjustment(defval or 0, 0, 100000, 1))
            elif options["widget"] == "list":
                prefbox = self.make_list_pref(
                    fetcher_name, opt, label, defval or [])
            elif options["widget"] == "toggle":
                prefbox = self.make_toggle_pref(
                    fetcher_name, opt, label, defval)
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
                write_config(self.config)
            elif not state and fetcher in self.config["general"]["sources"]:
                self.config["general"]["sources"].remove(fetcher)
                write_config(self.config)

        button.connect("state-set", on_toggle_fetcher_set, fetcher)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_prefbox_with_label(self, label, tooltip=None):
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preflabel = Gtk.Label(label)
        if tooltip is not None:
            preflabel.set_tooltip_text(tooltip)
        prefbox.pack_start(preflabel, False, False, 10)
        return prefbox

    def make_toggle_pref(self, path, opt, label, default=None):
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Switch()
        if opt in self.config[path]:
            button.set_active(self.config[path][opt])
        elif default is not None:
            button.set_active(default)

        def on_toggle_state_set(widget, state):
            self.config[path][opt] = state
            write_config(self.config)

        button.connect("state-set", on_toggle_state_set)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_select_pref(self, path, opt, label, values,
                         default=None, coerc=None):
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
            write_config(self.config)

        button.connect("changed", on_select_changed)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_text_pref(self, path, opt, label):
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Entry()
        if opt in self.config[path]:
            button.set_text(self.config[path][opt])

        def on_text_edited(widget, _event):
            self.config[path][opt] = widget.get_text().strip()
            if self.config[path][opt] == "":
                del self.config[path][opt]
            write_config(self.config)

        button.connect("activate", on_text_edited)
        button.connect("focus-out-event", on_text_edited)
        prefbox.pack_end(button, True, True, 10)
        return prefbox

    def make_number_pref(self, path, opt, label, adj=None, factor=1):
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.SpinButton()
        if adj is not None:
            button.set_adjustment(adj)
        elif opt in self.config[path]:
            button.set_adjustment(
                Gtk.Adjustment(self.config[path][opt], 0, 100000, 1))
        button.set_numeric(True)
        button.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

        def on_spin_value_changed(widget):
            self.config[path][opt] = widget.get_value_as_int() * factor
            write_config(self.config)

        button.connect("value-changed", on_spin_value_changed)
        prefbox.pack_end(button, False, False, 10)
        return prefbox

    def make_list_pref(self, path, opt, label, defaults=None):
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
            write_config(self.config)

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

    def lightdm_option_pref(self, genbox):
        def update_lightdm_wall(widget):
            self.config["general"]["desktop"] = widget.get_filename()
            write_config(self.config)

        prefbox = self.make_prefbox_with_label(
            _("LightDM shared background path"))
        button = Gtk.FileChooserButton.new(
            _("Select a file"), Gtk.FileChooserAction.OPEN)
        if "lightdm_wall" in self.config["general"]:
            button.set_filename(self.config["general"]["lightdm_wall"])
        button.connect("file-set", update_lightdm_wall)
        prefbox.pack_end(button, False, False, 10)
        genbox.pack_start(prefbox, False, False, 0)

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
            Gtk.Adjustment(sleep_time, 5, 120, 1), 60)
        genbox.pack_start(prefbox, False, False, 0)

        environments = [("gnome", "Gnome, Budgie, …"), ("mate", "Mate"),
                        ("nitrogen", _("Use Nitrogen application"))]
        prefbox = self.make_select_pref(
            "general", "desktop", _("Desktop environment"),
            environments, "gnome")
        genbox.pack_start(prefbox, False, False, 0)

        ldmfound = False
        for bintest in ["/usr/bin/lightdm", "/bin/lightdm", "/sbin/lightdm"]:
            if os.path.exists(bintest):
                ldmfound = True
                break
        if ldmfound:
            self.lightdm_option_pref(genbox)

        daemonbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        daemonbox.set_border_width(10)
        daemonbox.set_spacing(10)

        sfm = ServiceFileManager()

        prefbox = self.make_prefbox_with_label(
            _("Launch Chwall daemon when your session starts"),
            _("This use XDG autostart mechanism"))
        classic_daemon_btn = Gtk.Switch()
        classic_daemon_btn.set_active(sfm.xdg_autostart_file_exists())
        prefbox.pack_end(classic_daemon_btn, False, False, 10)
        daemonbox.pack_start(prefbox, False, False, 0)

        install_systemd_btn = None

        if sfm.systemd_version is not None:
            prefbox = self.make_prefbox_with_label(
                _("Install required service file to use systemd launcher"),
                _("This option must be set to let you manage the "
                  "Chwall daemon with systemd"))
            install_systemd_btn = Gtk.Switch()
            service_installed = sfm.systemd_service_file_exists()
            install_systemd_btn.set_active(service_installed)

            prefbox.pack_end(install_systemd_btn, False, False, 10)
            daemonbox.pack_start(prefbox, False, False, 0)

            prefbox = self.make_prefbox_with_label(
                _("Launch Chwall daemon with systemd when your session "
                  "starts"), sfm.systemd_version)
            enable_systemd_btn = Gtk.Switch()
            enable_systemd_btn.set_active(
                sfm.systemd_service_file_exists(True))

            prefbox.pack_end(enable_systemd_btn, False, False, 10)
            daemonbox.pack_start(prefbox, False, False, 0)

            def on_toggle_install_systemd_state(widget, state):
                if state:
                    sfm.systemd_service_file(True)
                    enable_systemd_btn.set_sensitive(True)
                    classic_daemon_btn.set_sensitive(False)
                else:
                    sfm.remove_systemd_service_file()
                    enable_systemd_btn.set_active(False)
                    enable_systemd_btn.set_sensitive(False)
                    classic_daemon_btn.set_sensitive(True)

            def on_toggle_systemd_state(widget, state):
                sfm.systemd_service_toggle(state)

            install_systemd_btn.connect(
                "state-set", on_toggle_install_systemd_state)
            enable_systemd_btn.connect("state-set", on_toggle_systemd_state)

            if service_installed:
                classic_daemon_btn.set_sensitive(False)
            else:
                enable_systemd_btn.set_sensitive(False)

        def on_toggle_state_set(widget, state):
            if state:
                sfm.xdg_autostart_file(_("Chwall daemon"),
                                       _("Start Chwall daemon"))
            else:
                sfm.remove_xdg_autostart_file()
            if install_systemd_btn is not None:
                install_systemd_btn.set_sensitive(not state)

        classic_daemon_btn.connect("state-set", on_toggle_state_set)

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
