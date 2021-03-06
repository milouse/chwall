DESTDIR =

prefix = $(DESTDIR)/usr
datarootdir = $(prefix)/share

exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin
libdir = $(exec_prefix)/lib

VERSION = $(shell python setup.py --version)

ICON_SIZE  = 128 64 48 32 24 16
DEST_ICONS = $(foreach z,$(ICON_SIZE),$(datarootdir)/icons/hicolor/$(z)x$(z)/apps/chwall.png) \
	$(foreach z,$(ICON_SIZE),$(datarootdir)/icons/hicolor/$(z)x$(z)/apps/chwall_mono.png)

PY_VERSION = $(shell python -c "import sys;v=sys.version_info;print('{}.{}'.format(v.major, v.minor))")
PY_SITE    = $(libdir)/python$(PY_VERSION)/site-packages

L10N_LANGS   = fr es
PO_FILES     = $(L10N_LANGS:%=locale/%/LC_MESSAGES/chwall.po)
MO_FILES     = $(PO_FILES:%.po=%.mo)
DEST_MO      = $(L10N_LANGS:%=$(datarootdir)/locale/%/LC_MESSAGES/chwall.mo)
TRANSLATABLE = chwall/gui/*.py chwall/fetcher/*.py \
	chwall/wallpaper.py chwall/daemon.py chwall/client.py

.PHONY: clean dist install lang uninstall uplang

.INTERMEDIATE: chwall-app.desktop $(MO_FILES)

dist: $(DEST_ICONS) $(DEST_MO) chwall-app.desktop
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

install: uninstall dist
	update-desktop-database $(datarootdir)/applications
	gtk-update-icon-cache $(datarootdir)/icons/hicolor

clean:
	find . -type d -name __pycache__ | xargs rm -rf
	rm -rf build chwall.egg-info dist

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
	CHWALL_FAKE_INSTALL=exists python -B -m chwall.client desktop chwall-app.desktop ./locale

$(datarootdir)/icons/hicolor/%/apps/chwall.png: data/icon_%.png
	install -d -m755 $(@:%/chwall.png=%)
	install -D -m644 $< $@

$(datarootdir)/icons/hicolor/%/apps/chwall_mono.png: data/icon_mono_%.png
	install -d -m755 $(@:%/chwall_mono.png=%)
	install -D -m644 $< $@

data/icon_%.png:
	convert data/icon_800.png -resize $(@:data/icon_%.png=%) $@

data/icon_mono_%.png:
	convert data/icon_mono_800.png -resize $(@:data/icon_mono_%.png=%) $@

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
	sed -i -e "s|Copyright (C) [0-9]*|Copyright (C) $(shell date +%Y)|" \
		-e "s|Id-Version: Chwall [0-9.]*|Id-Version: Chwall $(VERSION)|" \
		$@
	cp $@ $(@:%~=%) && rm $@

uplang: $(PO_FILES:%=%~)

test: $(MO_FILES)
	python -B -m unittest
