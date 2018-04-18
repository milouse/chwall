ROOT = /
DEST = $(ROOT)usr

ICON       = data/icon_800.png
ICON_SIZE  = 128 64 48 32 24 16
ICON_PATH  = $(foreach z,$(ICON_SIZE),$(z)x$(z))
ALL_ICONS  = $(ICON_SIZE:%=data/icon_%.png)
DEST_ICONS = $(ICON_PATH:%=$(DEST)/share/icons/hicolor/%/apps/chwall.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(ROOT)usr/lib/python$(PY_VERSION)/site-packages

cut = $(shell echo "$(1)" | cut -dx -f1)

.PHONY: build clean install uninstall

all: build

build: $(ALL_ICONS)

install: build $(DEST_ICONS)
	python setup.py install --root=$(ROOT) --quiet

uninstall:
	rm -rf $(PY_SITE)/chwall
	rm -f $(DEST)/bin/chwall $(DEST)/bin/chwall-daemon
	rm -f $(DEST_ICONS)

$(DEST)/share/icons/hicolor/%/apps/chwall.png:
	install -d -m755 $(@:%/chwall.png=%)
	install -D -m644 data/icon_$(call cut,$(@:$(DEST)/share/icons/hicolor/%/apps/chwall.png=%)).png $@

data/icon_%.png:
	convert $(ICON) -resize $(@:data/icon_%.png=%) $@

clean:
	rm -f $(ALL_ICONS)
	rm -rf build chwall.egg-info
