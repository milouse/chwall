ROOT = /
DEST = $(ROOT)usr

VERSION = $(shell python -c "from chwall.utils import VERSION;print(VERSION)")

ICON       = data/icon_800.png
ICON_SIZE  = 128 64 48 32 24 16
ALL_ICONS  = $(foreach z,$(ICON_SIZE),data/icon_$(z)x$(z).png)
DEST_ICONS = $(foreach z,$(ICON_SIZE),$(DEST)/share/icons/hicolor/$(z)x$(z)/apps/chwall.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(ROOT)usr/lib/python$(PY_VERSION)/site-packages

L10N_LANGS = fr
PO_FILES   = $(L10N_LANGS:%=locale/%/LC_MESSAGES/chwall.po)
MO_FILES   = $(PO_FILES:%.po=%.mo)
DEST_MO    = $(L10N_LANGS:%=$(DEST)/share/locale/%/LC_MESSAGES/chwall.mo)


.PHONY: clean install lang uninstall

install: $(DEST_ICONS) $(DEST_MO)
	python setup.py install --root=$(ROOT)
	install -d -m755 $(DEST)/share/licenses/chwall
	install -d -m755 $(DEST)/share/bash-completion/completions
	install -d -m755 $(DEST)/share/zsh/site-functions
	install -D -m644 LICENSE $(DEST)/share/licenses/chwall/LICENSE
	install -D -m644 data/chwall-completions $(DEST)/share/bash-completion/completions/chwall
	install -D -m644 data/_chwall $(DEST)/share/zsh/site-functions/_chwall
	update-desktop-database

uninstall:
	rm -rf $(PY_SITE)/chwall $(PY_SITE)/chwall-$(VERSION)-py$(PY_VERSION).egg-info
	rm -rf $(DEST)/share/licenses/chwall
	rm -f $(DEST_ICONS)
	rm -f $(DEST_MO)
	rm -f $(DEST)/share/bash-completion/completions/chwall
	rm -f $(DEST)/share/zsh/site-functions/_chwall
	rm -f $(DEST)/bin/chwall $(DEST)/bin/chwall-daemon
	update-desktop-database

$(DEST)/share/icons/hicolor/%/apps/chwall.png: data/icon_%.png
	install -d -m755 $(@:%/chwall.png=%)
	install -D -m644 $< $@

data/icon_%.png:
	convert $(ICON) -resize $(@:data/icon_%.png=%) $@

clean:
	rm -f $(ALL_ICONS)
	rm -f $(MO_FILES)
	rm -rf build chwall.egg-info

locale/chwall.pot:
	mkdir -p locale
	xgettext --language=Python --keyword=_ \
		--copyright-holder="Chwall volunteers" \
		--package-name=Chwall --package-version=$(VERSION) \
		--from-code=UTF-8 --output=locale/chwall.pot chwall/icon.py
	sed -i -e "s/SOME DESCRIPTIVE TITLE./Chwall Translation Effort/" \
		-e "s|Content-Type: text/plain; charset=CHARSET|Content-Type: text/plain; charset=UTF-8|" \
		-e "s|Copyright (C) YEAR|Copyright (C) $(shell date +%Y)|" \
		locale/chwall.pot

%.po: locale/chwall.pot
	mkdir -p $(@D)
	msginit -l $(@:locale/%/LC_MESSAGES/chwall.po=%) \
		--no-translator -i $< -o $@

%.mo: %.po
	msgfmt -o $@ $<

$(DEST_MO): $(MO_FILES)
	install -D -m644 $< $@

lang: $(PO_FILES)
