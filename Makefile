SERVICE := two-factor-apache
DESTDIR ?= dist_root
SERVICEDIR ?= /srv/$(SERVICE)

CFLAGS ?= -O3 -fPIC

SHELL = /bin/bash

.PHONY: install

build: listen_unix.o
	$(CC) -ldl -shared $< -o dist_root/srv/two-factor-apache/listen_unix.so

install: build
	mkdir -p $(DESTDIR)$(SERVICEDIR)/data/home $(DESTDIR)$(SERVICEDIR)/sock_dir
