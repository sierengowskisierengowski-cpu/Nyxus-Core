# NYXUS · gettext message-catalog Makefile · rev 2026-05-13 r1
# Compiles per-locale .po files into binary .mo files installed at
#   /usr/share/locale/<lang>/LC_MESSAGES/nyxus.mo
# build-iso.sh runs `make -C nyxus-scripts/locale install DESTDIR=...`.
DOMAIN  := nyxus
LOCALES := en es
PREFIX  ?= /usr
DESTDIR ?=
LOCDIR   = $(DESTDIR)$(PREFIX)/share/locale

PO_FILES := $(foreach l,$(LOCALES),$(l)/LC_MESSAGES/$(DOMAIN).po)
MO_FILES := $(PO_FILES:.po=.mo)

.PHONY: all install clean update-pot

all: $(MO_FILES)

%.mo: %.po
	msgfmt --check --statistics -o $@ $<

install: all
	@for l in $(LOCALES); do \
	  install -Dm644 $$l/LC_MESSAGES/$(DOMAIN).mo \
	    $(LOCDIR)/$$l/LC_MESSAGES/$(DOMAIN).mo; \
	done

# Regenerate the .pot template by scanning every nyxus_*.py for _("…").
update-pot:
	xgettext --language=Python --keyword=_ --keyword=N_ \
	         --output=$(DOMAIN).pot --from-code=UTF-8 \
	         --package-name=NYXUS --package-version=2026.05 \
	         ../nyxus_*.py

clean:
	rm -f $(MO_FILES) $(DOMAIN).pot
