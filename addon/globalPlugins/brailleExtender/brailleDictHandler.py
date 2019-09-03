# coding: utf-8
# brailleDictHandler.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2019 André-Abush CLAUSE, released under GPL.
from __future__ import unicode_literals
import gui
import wx
import os.path
import sys

import addonHandler
addonHandler.initTranslation()

import config
import louis
from . import configBE
from collections import namedtuple

isPy3 = True if sys.version_info >= (3, 0) else False

BrailleDictEntry = namedtuple("BrailleDictEntry", ("opcode", "textPattern", "braillePattern", "direction", "comment"))
OPCODE_SIGN = "sign"
OPCODE_MATH = "math"
OPCODE_REPLACE = "replace"
OPCODE_LABELS = {
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_SIGN: _("Sign"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_MATH: _("Math"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_REPLACE: _("Replace"),
}
OPCODE_LABELS_ORDERING = (OPCODE_SIGN, OPCODE_MATH, OPCODE_REPLACE)

DIRECTION_BOTH = "both"
DIRECTION_BACKWARD = "nofor"
DIRECTION_FORWARD = "noback"
DIRECTION_LABELS = {
	DIRECTION_BOTH: _("Both (input and output)"),
	DIRECTION_BACKWARD: _("Backward (input only)"),
	DIRECTION_FORWARD: _("Forward (output only)")
}
DIRECTION_LABELS_ORDERING = (DIRECTION_BOTH, DIRECTION_FORWARD, DIRECTION_BACKWARD)

dictTables = []
invalidDictTables = set()

def checkTable(path):
	global invalidDictTables
	try:
		louis.checkTable([path])
		return True
	except RuntimeError: invalidDictTables.add(path)
	return False

def getValidPathsDict():
	types = ["default", "table", "tmp"]
	paths = [getPathDict(type_) for type_ in types]
	valid = lambda path: os.path.exists(path) and os.path.isfile(path) and checkTable(path)
	return [path for path in paths if valid(path)]

def getPathDict(type_):
	if type_ == "table": path = os.path.join(configBE.configDir, "brailleDicts", config.conf["braille"]["translationTable"])
	elif type_ == "tmp": path = os.path.join(configBE.configDir, "brailleDicts", "tmp")
	else: path = os.path.join(configBE.configDir, "brailleDicts", "default")
	return "%s.cti" % path

def getDictionary(type_):
	path = getPathDict(type_)
	if not os.path.exists(path): return False, []
	out = []
	with open(path, "rb") as f:
		for line in f:
			line = line.decode("UTF-8")
			line = line.replace(" ", "	").replace("		", "	").replace("		", "	").strip().split("	", 4)
			if line[0].lower().strip() not in [DIRECTION_BACKWARD, DIRECTION_FORWARD]: line.insert(0, DIRECTION_BOTH)
			if len(line) < 4: continue
			if len(line) == 4: line.append("")
			out.append(BrailleDictEntry(line[1], line[2], line[3], line[0], ' '.join(line[4:]).replace("	", " ")))
	return True, out

def saveDict(type_, dict_):
	path = getPathDict(type_)
	f = open(path, "wb")
	for entry in dict_:
		direction = entry.direction if entry.direction != "both" else ''
		line = ("%s	%s	%s	%s	%s" % (direction, entry.opcode, entry.textPattern, entry.braillePattern, entry.comment)).strip()+"\n"
		f.write(line.encode("UTF-8"))
	f.write('\n'.encode("UTF-8"))
	f.close()
	return True

def setDictTables():
	global dictTables
	invalidDictTables.clear()
	dictTables = getValidPathsDict()
	if hasattr(louis.liblouis, "lou_free"): louis.liblouis.lou_free()
	else: return False
	return True

def notifyInvalidTables():
	if invalidDictTables:
		dicts = {
			getPathDict("default"): "default",
			getPathDict("table"): "table",
			getPathDict("tmp"): "tmp"
		}
		msg = _("One or more errors are present in dictionaries tables. Concerned dictionaries: %s. As a result, these dictionaries are not loaded." % ", ".join([dicts[path] for path in invalidDictTables if path in dicts]))
		wx.CallAfter(gui.messageBox, msg, _("Braille Extender"), wx.OK|wx.ICON_ERROR)

def removeTmpDict():
	path = getPathDict("tmp")
	if os.path.exists(path): os.remove(path)

setDictTables()
notifyInvalidTables()