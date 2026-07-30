LOCAL_PELICAN := $(CURDIR)/.venv/bin/pelican
MNE_PELICAN := /Users/molfesepj/micromamba/envs/mne/bin/pelican

ifneq ($(wildcard $(LOCAL_PELICAN)),)
PELICAN ?= $(LOCAL_PELICAN)
else ifneq ($(wildcard $(MNE_PELICAN)),)
PELICAN ?= $(MNE_PELICAN)
else
PELICAN ?= pelican
endif
PELICANOPTS ?=

BASEDIR := $(CURDIR)
INPUTDIR := $(BASEDIR)/content
OUTPUTDIR := $(BASEDIR)/output
CONFFILE := $(BASEDIR)/pelicanconf.py
PUBLISHCONF := $(BASEDIR)/publishconf.py

.PHONY: help build clean rebuild serve publish

help:
	@echo "make build    Build the development site"
	@echo "make serve    Build, watch, and serve at http://127.0.0.1:8000"
	@echo "make publish  Build production site for https://fmrif.nimh.nih.gov"
	@echo "make clean    Remove generated output"

build:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

clean:
	rm -rf "$(OUTPUTDIR)"

rebuild: clean build

serve:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" -r -l $(PELICANOPTS)

publish:
	"$(PELICAN)" "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(PUBLISHCONF)" $(PELICANOPTS)
