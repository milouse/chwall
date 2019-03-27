import pkgutil
from importlib import import_module

from chwall.utils import write_config

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
        self.set_default_size(-1, 600)

        stack = Gtk.Stack()

        genbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
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

        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(_("LightDM shared background path"))
        prefbox.pack_start(label, False, False, 5)
        button = Gtk.FileChooserButton.new(_("Select a file"),
                                           Gtk.FileChooserAction.OPEN)
        if "lightdm_wall" in self.config["general"]:
            button.set_filename(self.config["general"]["lightdm_wall"])

        def update_lightdm_wall(widget):
            self.config["general"]["desktop"] = widget.get_filename()
            write_config(self.config)

        button.connect("file-set", update_lightdm_wall)
        prefbox.pack_end(button, False, False, 5)
        genbox.pack_start(prefbox, False, False, 0)

        stack.add_titled(genbox, "general", _("General"))

        picbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        picbox.set_spacing(10)

        fetcher_package = import_module("chwall.fetcher")
        fp_source = fetcher_package.__path__
        for fd in pkgutil.iter_modules(fp_source):
            fetcher = import_module("chwall.fetcher.{}".format(fd.name))
            if "preferences" not in dir(fetcher):
                continue
            fprefs = fetcher.preferences()
            prefbox = self.make_fetcher_toggle_pref(fd.name, fprefs)
            picbox.pack_start(prefbox, True, True, 0)
            if "options" not in fprefs:
                sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
                picbox.pack_start(sep, False, False, 0)
                continue
            if fd.name not in self.config:
                self.config[fd.name] = {}
            for opt in fprefs["options"]:
                if "widget" not in fprefs["options"][opt]:
                    continue
                options = fprefs["options"][opt]
                prefbox = None
                label = opt.capitalize()
                if "label" in options:
                    label = options["label"]
                if options["widget"] == "select":
                    values = []
                    for v in options["values"]:
                        values.append((str(v), str(v)))
                    prefbox = self.make_select_pref(
                        fd.name, opt, label, values, None,
                        options["type"])
                elif options["widget"] == "text":
                    prefbox = self.make_text_pref(fd.name, opt, label)
                elif options["widget"] == "number":
                    prefbox = self.make_number_pref(fd.name, opt, label)
                elif options["widget"] == "list":
                    values = []
                    if "default" in options:
                        values = options["default"]
                    prefbox = self.make_list_pref(fd.name, opt, label, values)
                if prefbox is not None:
                    picbox.pack_start(prefbox, True, True, 0)
            sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            picbox.pack_start(sep, False, False, 0)

        picscrollbox = Gtk.ScrolledWindow()
        picscrollbox.set_vexpand(True)
        picscrollbox.add(picbox)

        stack.add_titled(picscrollbox, "sources", _("Pictures sources"))

        box = self.get_content_area()
        box.set_spacing(10)
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        prefbox.set_center_widget(stack_switcher)
        box.pack_start(prefbox, False, False, 0)
        box.pack_start(stack, True, True, 0)
        self.show_all()

    def make_fetcher_toggle_pref(self, fetcher, fprefs):
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        fetcher_name = fetcher
        if "name" in fprefs:
            fetcher_name = fprefs["name"]
        label = Gtk.Label()
        label.set_markup("<b>{}</b>".format(fetcher_name))
        prefbox.pack_start(label, False, False, 5)
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
        prefbox.pack_end(button, False, False, 5)
        return prefbox

    def make_prefbox_with_label(self, label):
        prefbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preflabel = Gtk.Label(label)
        prefbox.pack_start(preflabel, False, False, 5)
        return prefbox

    def make_toggle_pref(self, path, opt, label):
        prefbox = self.make_prefbox_with_label(label)
        button = Gtk.Switch()
        if opt in self.config[path]:
            button.set_active(self.config[path][opt])

        def on_toggle_state_set(widget, state):
            self.config[path][opt] = state
            write_config(self.config)

        button.connect("state-set", on_toggle_state_set)
        prefbox.pack_end(button, False, False, 5)
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
        prefbox.pack_end(button, False, False, 5)
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
        prefbox.pack_end(button, True, True, 5)
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
        prefbox.pack_end(button, False, False, 5)
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

        liststore.append([_("New")])
        treeview = Gtk.TreeView(model=liststore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_property("editable", True)

        def update_pref_list(store, storepath, _iter, vals):
            item = store[storepath][0].strip()
            if item == _("New"):
                return False
            vals.append(item)
            # Always return False to continue iterating
            return False

        def on_cell_edited(widget, storepath, text):
            if liststore[storepath][0] == _("New"):
                liststore.append([_("New")])
            if text.strip() == "":
                liststore.remove(liststore.get_iter(storepath))
            else:
                liststore[storepath][0] = text
            vals = []
            liststore.foreach(update_pref_list, vals)
            if len(vals) == 0:
                del self.config[path][opt]
            else:
                self.config[path][opt] = vals
            write_config(self.config)

        renderer_text.connect("edited", on_cell_edited)
        column_text = Gtk.TreeViewColumn(label, renderer_text, text=0)
        treeview.append_column(column_text)
        prefbox.pack_end(treeview, True, True, 0)
        return prefbox
