ICON = data/icon_800.png
ICON_SIZE = 128 64 48 32 24 16
ALL_ICONS = $(ICON_SIZE:%=data/icon_%.png)


.PHONY: build

all: build

build: $(ALL_ICONS)

data/icon_%.png:
	convert $(ICON) -resize $(@:data/icon_%.png=%) $@

clean:
	rm -f $(ALL_ICONS)
