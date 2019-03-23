ROOT = /
DEST = $(ROOT)usr

VERSION = $(shell python -c "from chwall.utils import VERSION;print(VERSION)")

ICON       = data/icon_800.png
ICON_SIZE  = 128 64 48 32 24 16
DEST_ICONS = $(foreach z,$(ICON_SIZE),$(DEST)/share/icons/hicolor/$(z)x$(z)/apps/chwall.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(ROOT)usr/lib/python$(PY_VERSION)/site-packages

L10N_LANGS   = fr es
PO_FILES     = $(L10N_LANGS:%=locale/%/LC_MESSAGES/chwall.po)
MO_FILES     = $(PO_FILES:%.po=%.mo)
DEST_MO      = $(L10N_LANGS:%=$(DEST)/share/locale/%/LC_MESSAGES/chwall.mo)
TRANSLATABLE = chwall/gui/shared.py chwall/gui/icon.py chwall/gui/app.py chwall/daemon.py chwall/client.py


.PHONY: dist install lang uninstall uplang

.INTERMEDIATE: chwall-app.desktop

dist: $(DEST_ICONS) $(DEST_MO) chwall-app.desktop
	python setup.py install --root=$(ROOT)
	@rm -rf build chwall.egg-info
	install -d -m755 $(DEST)/share/applications
	install -d -m755 $(DEST)/share/licenses/chwall
	install -d -m755 $(DEST)/share/bash-completion/completions
	install -d -m755 $(DEST)/share/zsh/site-functions
	install -D -m644 chwall-app.desktop $(DEST)/share/applications/chwall-app.desktop
	install -D -m644 LICENSE $(DEST)/share/licenses/chwall/LICENSE
	install -D -m644 data/chwall-completions $(DEST)/share/bash-completion/completions/chwall
	install -D -m644 data/_chwall $(DEST)/share/zsh/site-functions/_chwall

install: dist
	@update-desktop-database $(DEST)/share/applications
	@gtk-update-icon-cache $(DEST)/share/icons/hicolor

uninstall:
	rm -rf $(PY_SITE)/chwall $(PY_SITE)/chwall-$(VERSION)-py$(PY_VERSION).egg-info
	rm -rf $(DEST)/share/licenses/chwall
	rm -f $(DEST_ICONS)
	@gtk-update-icon-cache $(DEST)/share/icons/hicolor
	rm -f $(DEST_MO)
	rm -f $(DEST)/share/bash-completion/completions/chwall
	rm -f $(DEST)/share/zsh/site-functions/_chwall
	rm -f $(DEST)/bin/chwall $(DEST)/bin/chwall-daemon $(DEST)/bin/chwall-icon $(DEST)/bin/chwall-app
	rm -f $(DEST)/share/applications/chwall-app.desktop

chwall-app.desktop:
	python chwall.py desktop $(DEST)/share/locale

$(DEST)/share/icons/hicolor/%/apps/chwall.png: data/icon_%.png
	install -d -m755 $(@:%/chwall.png=%)
	install -D -m644 $< $@

data/icon_%.png:
	convert $(ICON) -resize $(@:data/icon_%.png=%) $@

locale/chwall.pot:
	mkdir -p locale
	xgettext --language=Python --keyword=_ \
		--copyright-holder="Chwall volunteers" \
		--package-name=Chwall --package-version=$(VERSION) \
		--from-code=UTF-8 --output=locale/chwall.pot $(TRANSLATABLE)
	sed -i -e "s/SOME DESCRIPTIVE TITLE./Chwall Translation Effort/" \
		-e "s|Content-Type: text/plain; charset=CHARSET|Content-Type: text/plain; charset=UTF-8|" \
		-e "s|Copyright (C) YEAR|Copyright (C) $(shell date +%Y)|" \
		locale/chwall.pot

%.po: locale/chwall.pot
	mkdir -p $(@D)
	msginit -l $(@:locale/%/LC_MESSAGES/chwall.po=%) \
		--no-translator -i $< -o $@

locale/%/LC_MESSAGES/chwall.mo: locale/%/LC_MESSAGES/chwall.po
	msgfmt -o $@ $<

$(DEST)/share/locale/%/LC_MESSAGES/chwall.mo: locale/%/LC_MESSAGES/chwall.mo
	install -D -m644 $< $@

lang: $(PO_FILES)

%.po~:
	msgmerge --lang $(@:locale/%/LC_MESSAGES/chwall.po~=%) \
		-o $@ $(@:%~=%) locale/chwall.pot
	@cp $@ $(@:%~=%) && rm $@

uplang: $(PO_FILES:%=%~)
