## Process this file with automake to produce Makefile.in
# Copyright 2008, 2010  Jochen Voss <voss@seehuhn.de>

SUBDIRS = doc examples

EXTRA_DIST = wisent.py check1.py check2.py
BUILT_SOURCES = version.py

bin_SCRIPTS = wisent
pkgpython_PYTHON = grammar.py automaton.py scanner.py parser.py	\
	text.py helpers.py template.py version.py

TESTS = check1.py check2.py

version.py: configure.ac Makefile.am
	cd $(srcdir) && \
	echo "# version.py - Wisent version information" >$@ && \
	echo "# (autogenerated by Makefile.am, do not edit)" >>$@ && \
	echo "" >>$@ && \
	echo "PACKAGE=\"@PACKAGE@\"" >>$@ && \
	echo "VERSION=\"@VERSION@\"" >>$@

wisent: wisent.py Makefile.am
	echo "#! /usr/bin/env python" >$@
	echo "# WARNING: automatically generated from $<, do not edit" >>$@
	echo "#" >>$@
	sed -e "1 d" \
	  -e "s;^# FIX PATH$$;sys.path = ['@pkgpythondir@'] + sys.path;" \
	  $< >>$@
	chmod +x wisent

CLEANFILES = wisent
