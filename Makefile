DESTDIR =

datarootdir = $(DESTDIR)/usr/share
bindir = $(DESTDIR)/usr/bin

VERSION = $(shell python -c "from chwall import __version__; print(__version__)")

ICON_SIZE  = 128 64 48 32 24 16
DEST_ICONS = $(foreach z,$(ICON_SIZE),$(datarootdir)/icons/hicolor/$(z)x$(z)/apps/chwall.png) \
	$(foreach z,$(ICON_SIZE),$(datarootdir)/icons/hicolor/$(z)x$(z)/apps/chwall_mono.png)

L10N_LANGS   = fr es
PO_FILES     = $(L10N_LANGS:%=locale/%/LC_MESSAGES/chwall.po)
MO_FILES     = $(PO_FILES:%.po=%.mo)
DEST_MO      = $(L10N_LANGS:%=$(datarootdir)/locale/%/LC_MESSAGES/chwall.mo)
TRANSLATABLE = chwall/gui/*.py chwall/fetcher/*.py chwall/utils.py \
	chwall/wallpaper.py chwall/daemon.py chwall/client.py

.PHONY: build clean install lang package uninstall

.INTERMEDIATE: chwall-app.desktop $(MO_FILES)

build: clean
	python -m build --wheel --no-isolation
	python -m installer --destdir="$(DESTDIR)/" dist/chwall-$(VERSION)-py3-none-any.whl

package: build $(DEST_ICONS) $(DEST_MO) chwall-app.desktop
	install -d -m755 $(datarootdir)/applications
	install -d -m755 $(datarootdir)/licenses/chwall
	install -d -m755 $(datarootdir)/bash-completion/completions
	install -d -m755 $(datarootdir)/zsh/site-functions
	install -D -m644 chwall-app.desktop $(datarootdir)/applications/chwall-app.desktop
	install -D -m644 LICENSE $(datarootdir)/licenses/chwall/LICENSE
	install -D -m644 data/chwall-completions $(datarootdir)/bash-completion/completions/chwall
	install -D -m644 data/_chwall $(datarootdir)/zsh/site-functions/_chwall

install: uninstall package
	update-desktop-database $(datarootdir)/applications
	gtk-update-icon-cache $(datarootdir)/icons/hicolor

clean:
	find $(PWD) -type d -name __pycache__ -print0 | \
		xargs -0r rm -r
	find $(PWD) -type d -empty ! -path "*/.git/*" -print0 | \
		xargs -0r rmdir -p --ignore-fail-on-non-empty
	rm -f $(MO_FILES) chwall-app.desktop
	rm -rf build dist chwall.egg-info

PY_SITE = $(DESTDIR)$(shell python -c "import site; print(site.getsitepackages()[0])")
uninstall:
	rm -rf $(PY_SITE)/chwall $(PY_SITE)/chwall-*.dist-info $(PY_SITE)/chwall-*.egg-info
	rm -rf $(datarootdir)/licenses/chwall
	rm -f $(DEST_ICONS)
	gtk-update-icon-cache $(datarootdir)/icons/hicolor
	rm -f $(DEST_MO)
	rm -f $(datarootdir)/bash-completion/completions/chwall
	rm -f $(datarootdir)/zsh/site-functions/_chwall
	rm -f $(bindir)/chwall $(bindir)/chwall-app $(bindir)/chwall-daemon \
		$(bindir)/chwall-icon $(bindir)/chwall-indicator
	rm -f $(datarootdir)/applications/chwall-app.desktop

chwall-app.desktop: $(MO_FILES)
	CHWALL_LOCALE_DIR=./locale \
		python -B -m chwall.client desktop chwall-app.desktop

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
		--msgid-bugs-address=bugs@depar.is --from-code=UTF-8 \
		--output=locale/chwall.pot $(TRANSLATABLE)
	sed -i -e "s/SOME DESCRIPTIVE TITLE./Chwall Translation Effort/" \
		-e "s|Content-Type: text/plain; charset=CHARSET|Content-Type: text/plain; charset=UTF-8|" \
		-e "s|Copyright (C) YEAR|Copyright (C) 2018-$(shell date +%Y)|" \
		locale/chwall.pot

%.po: locale/chwall.pot
	mkdir -p $(@D)
	[ ! -f $@ ] && \
		msginit -l $(@:locale/%/LC_MESSAGES/chwall.po=%) \
			--no-translator -i $< -o $@ || true
	msgmerge --lang $(@:locale/%/LC_MESSAGES/chwall.po=%) \
		-o $@ $@ $<
	sed -i -e "s|Copyright (C) 2018-[0-9]*|Copyright (C) 2018-$(shell date +%Y)|" \
		-e "s|Id-Version: Chwall [0-9.]*|Id-Version: Chwall $(VERSION)|" \
		$@

locale/%/LC_MESSAGES/chwall.mo: locale/%/LC_MESSAGES/chwall.po
	msgfmt -o $@ $<

$(datarootdir)/locale/%/LC_MESSAGES/chwall.mo: locale/%/LC_MESSAGES/chwall.mo
	install -D -m644 $< $@

lang: $(PO_FILES)

test: $(MO_FILES)
	python -B -m unittest
