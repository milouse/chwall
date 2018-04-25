ROOT = /
DEST = $(ROOT)usr

VERSION = $(shell python -c "from chwall.utils import VERSION;print(VERSION)")

ICON       = data/icon_800.png
ICON_SIZE  = 128 64 48 32 24 16
ICON_PATH  = $(foreach z,$(ICON_SIZE),$(z)x$(z))
ALL_ICONS  = $(ICON_SIZE:%=data/icon_%.png)
DEST_ICONS = $(ICON_PATH:%=$(DEST)/share/icons/hicolor/%/apps/chwall.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(ROOT)usr/lib/python$(PY_VERSION)/site-packages

cut = $(shell echo "$(1)" | cut -dx -f1)

.PHONY: clean install uninstall

install:
	python setup.py install --root=$(ROOT)
	install -d -m755 $(DEST)/share/licenses/chwall
	install -d -m755 $(DEST)/share/bash-completion/completions
	install -d -m755 $(DEST)/share/zsh/site-functions
	install -D -m644 LICENSE $(DEST)/share/licenses/chwall/LICENSE
	install -D -m644 data/chwall-completions $(DEST)/share/bash-completion/completions/chwall
	install -D -m644 data/_chwall $(DEST)/share/zsh/site-functions/_chwall

uninstall:
	rm -rf $(PY_SITE)/chwall $(PY_SITE)/chwall-$(VERSION)-py$(PY_VERSION).egg-info
	rm -rf $(DEST)/share/licenses/chwall
	rm -f $(DEST)/share/bash-completion/completions/chwall
	rm -f $(DEST)/share/zsh/site-functions/_chwall
	rm -f $(DEST)/bin/chwall $(DEST)/bin/chwall-daemon

$(DEST)/share/icons/hicolor/%/apps/chwall.png:
	install -d -m755 $(@:%/chwall.png=%)
	install -D -m644 data/icon_$(call cut,$(@:$(DEST)/share/icons/hicolor/%/apps/chwall.png=%)).png $@

data/icon_%.png:
	convert $(ICON) -resize $(@:data/icon_%.png=%) $@

clean:
	rm -f $(ALL_ICONS)
	rm -rf build chwall.egg-info
