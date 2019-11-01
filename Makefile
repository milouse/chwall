DESTDIR =

prefix = $(DESTDIR)/usr
datarootdir = $(prefix)/share

exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin
libdir = $(exec_prefix)/lib

VERSION = $(shell python -c "from chwall.utils import VERSION;print(VERSION)")

ICON       = data/icon_800.png
ICON_SIZE  = 128 64 48 32 24 16
DEST_ICONS = $(foreach z,$(ICON_SIZE),$(datarootdir)/icons/hicolor/$(z)x$(z)/apps/chwall.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(libdir)/python$(PY_VERSION)/site-packages

L10N_LANGS   = fr es
PO_FILES     = $(L10N_LANGS:%=locale/%/LC_MESSAGES/chwall.po)
MO_FILES     = $(PO_FILES:%.po=%.mo)
DEST_MO      = $(L10N_LANGS:%=$(datarootdir)/locale/%/LC_MESSAGES/chwall.mo)
TRANSLATABLE = chwall/gui/*.py chwall/fetcher/*.py \
	chwall/wallpaper.py chwall/daemon.py chwall/client.py

.PHONY: dist install lang uninstall uplang

.INTERMEDIATE: chwall-app.desktop $(MO_FILES)

dist: $(DEST_ICONS) $(DEST_MO) chwall-app.desktop
	rm -rf $(PY_SITE)/chwall-*-py$(PY_VERSION).egg-info
	python setup.py install --root=$(DESTDIR)/
	rm -rf build chwall.egg-info
	install -d -m755 $(datarootdir)/applications
	install -d -m755 $(datarootdir)/licenses/chwall
	install -d -m755 $(datarootdir)/bash-completion/completions
	install -d -m755 $(datarootdir)/zsh/site-functions
	install -D -m644 chwall-app.desktop $(datarootdir)/applications/chwall-app.desktop
	install -D -m644 LICENSE $(datarootdir)/licenses/chwall/LICENSE
	install -D -m644 data/chwall-completions $(datarootdir)/bash-completion/completions/chwall
	install -D -m644 data/_chwall $(datarootdir)/zsh/site-functions/_chwall

install: dist
	update-desktop-database $(datarootdir)/applications
	gtk-update-icon-cache $(datarootdir)/icons/hicolor

uninstall:
	rm -rf $(PY_SITE)/chwall $(PY_SITE)/chwall-*-py$(PY_VERSION).egg-info
	rm -rf $(datarootdir)/licenses/chwall
	rm -f $(DEST_ICONS)
	gtk-update-icon-cache $(datarootdir)/icons/hicolor
	rm -f $(DEST_MO)
	rm -f $(datarootdir)/bash-completion/completions/chwall
	rm -f $(datarootdir)/zsh/site-functions/_chwall
	rm -f $(bindir)/chwall $(bindir)/chwall-daemon $(bindir)/chwall-icon $(bindir)/chwall-app
	rm -f $(datarootdir)/applications/chwall-app.desktop

chwall-app.desktop: $(MO_FILES)
	python -m chwall.client desktop chwall-app.desktop ./locale

$(datarootdir)/icons/hicolor/%/apps/chwall.png: data/icon_%.png
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

$(datarootdir)/locale/%/LC_MESSAGES/chwall.mo: locale/%/LC_MESSAGES/chwall.mo
	install -D -m644 $< $@

lang: $(PO_FILES)

%.po~:
	msgmerge --lang $(@:locale/%/LC_MESSAGES/chwall.po~=%) \
		-o $@ $(@:%~=%) locale/chwall.pot
	cp $@ $(@:%~=%) && rm $@

uplang: $(PO_FILES:%=%~)
