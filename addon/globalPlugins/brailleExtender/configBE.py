# coding: utf-8
# configBE.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os
import ui
import re
from cStringIO import StringIO
from validate import Validator
import globalVars
from colors import RGB
from collections import OrderedDict

import addonHandler
addonHandler.initTranslation()
import braille
import config
import inputCore
import languageHandler
from logHandler import log

CHANNEL_stable = "stable"
CHANNEL_testing = "testing"
CHANNEL_dev = "dev"

CHOICE_none = "none"
CHOICE_braille = "braille"
CHOICE_speech = "speech"
CHOICE_speechAndBraille = "speechAndBraille"
CHOICE_dots78 = "dots78"
CHOICE_dot7 = "dot7"
CHOICE_dot8 = "dot8"

outputMessage = OrderedDict([
	(CHOICE_none, _("none")),
	(CHOICE_braille, _("braille only")),
	(CHOICE_speech, _("speech only")),
	(CHOICE_speechAndBraille, _("both"))
])

attributeChoices = OrderedDict([
	(CHOICE_none, _("none")),
	(CHOICE_dots78, _("dots 7 and 8")),
	(CHOICE_dot7, _("dot 7")),
	(CHOICE_dot8, _("dot 8"))
])

updateChannels = OrderedDict([
	(CHANNEL_stable, _("stable")),
	(CHANNEL_testing, _("testing")),
	(CHANNEL_dev, _("development"))
])

curBD = braille.handler.display.name
quickLaunches = OrderedDict()
backupDisplaySize = braille.handler.displaySize
backupRoleLabels = {}
iniGestures = {}
iniProfile = {}
profileFileExists = gesturesFileExists = False
lang = languageHandler.getLanguage().split('_')[-1].lower()
noMessageTimeout = True if 'noMessageTimeout' in config.conf["braille"] else False
sep = ' ' if 'fr' in lang else ''
outputTables = inputTables = None
_addonDir = os.path.join(os.path.dirname(__file__), "..", "..").decode("mbcs")
_addonName = addonHandler.Addon(_addonDir).manifest["name"]
_addonVersion = addonHandler.Addon(_addonDir).manifest["version"]
_addonURL = addonHandler.Addon(_addonDir).manifest["url"]
_addonAuthor = addonHandler.Addon(_addonDir).manifest["author"]
_addonDesc = addonHandler.Addon(_addonDir).manifest["description"]
profilesDir = os.path.join(os.path.dirname(__file__), "Profiles").decode('mbcs')
if not os.path.exists(profilesDir): log.error('Profiles\' path not found')
else: log.debug('Profiles\' path (%s) found' % profilesDir)
try:
	import brailleTables
	tablesFN = [t[0] for t in brailleTables.listTables()]
	tablesUFN = [t[0] for t in brailleTables.listTables() if not t.contracted and t.output]
	tablesTR = [t[1] for t in brailleTables.listTables()]
	noUnicodeTable = False
except BaseException:
	noUnicodeTable = True
confspec = {
	"autoCheckUpdate": "boolean(default=True)",
	"channelUpdate": "option({CHANNEL_dev}, {CHANNEL_stable}, {CHANNEL_testing}, default={CHANNEL_stable})".format(
		CHOICE_none=CHOICE_none,
		CHANNEL_dev=CHANNEL_dev,
		CHANNEL_stable=CHANNEL_stable,
		CHANNEL_testing=CHANNEL_testing
	),
	"lastCheckUpdate": "float(min=0, default=0)",
	"profile_%s" % curBD: 'string(default="default")',
	"keyboardLayout_%s" % curBD: "string(default=\"?\")",
	"modifierKeysFeedback": "option({CHOICE_none}, {CHOICE_braille}, {CHOICE_speech}, {CHOICE_speechAndBraille}, default={CHOICE_braille})".format(
		CHOICE_none=CHOICE_none,
		CHOICE_braille=CHOICE_braille,
		CHOICE_speech=CHOICE_speech,
		CHOICE_speechAndBraille=CHOICE_speechAndBraille
	),
	"volumeChangeFeedback": "option({CHOICE_none}, {CHOICE_braille}, {CHOICE_speech}, {CHOICE_speechAndBraille}, default={CHOICE_braille})".format(
		CHOICE_none=CHOICE_none,
		CHOICE_braille=CHOICE_braille,
		CHOICE_speech=CHOICE_speech,
		CHOICE_speechAndBraille=CHOICE_speechAndBraille
	),
	"brailleDisplay1": 'string(default="noBraille")',
	"brailleDisplay2": 'string(default="noBraille")',
	"hourDynamic": "boolean(default=True)",
	"leftMarginCells_%s" % curBD: "integer(min=0, default=0, max=80)",
	"rightMarginCells_%s" %curBD: "integer(min=0, default=0, max=80)",
	"delayScroll_%s" % curBD: "float(min=0, default=3, max=42)",
	"smartDelayScroll": "boolean(default=False)",
	"reverseScroll": "boolean(default=False)",
	"ignoreBlankLineScroll": "boolean(default=True)",
	"speakScrollReviewMode": "boolean(default=True)",
	"speakScrollFocusMode": "boolean(default=False)",
	"stopSpeechScroll": "boolean(default=False)",
	"stopSpeechUnknown": "boolean(default=True)",
	"speakRoutingTo": "boolean(default=True)",
	"inputTableShortcuts": 'string(default="?")',
	"inputTables": 'string(default="%s")' % config.conf["braille"]["inputTable"] + ", unicode-braille.utb",
	"outputTables": "string(default=%s)" % config.conf["braille"]["translationTable"],
	"quickLaunchGestures_%s" % curBD: "string(default=\"\")",
	"quickLaunchLocations_%s" % curBD: 'string(default="")',
	"tabSpace": "boolean(default=False)",
	"tabSize": "integer(min=1, default=2, max=42)",
	"postTable": 'string(default="None")',
	"viewSaved": 'string(default="None")',
	"features": {
		"attributes": "boolean(default=True)",
		"roleLabels": "boolean(default=True)"
	},
	"attributes": {
		"bold": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_dots78})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_dot7=CHOICE_dot7,
			CHOICE_dot8=CHOICE_dot8,
			CHOICE_dots78=CHOICE_dots78
		),
		"italic": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_none})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_dot7=CHOICE_dot7,
			CHOICE_dot8=CHOICE_dot8,
			CHOICE_dots78=CHOICE_dots78
		),
		"underline": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_none})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_dot7=CHOICE_dot7,
			CHOICE_dot8=CHOICE_dot8,
			CHOICE_dots78=CHOICE_dots78
		),
		"invalid-spelling": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_dots78})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_dot7=CHOICE_dot7,
			CHOICE_dot8=CHOICE_dot8,
			CHOICE_dots78=CHOICE_dots78
		)
	},
	"roleLabels": {}
}

def getLabelFromID(idCategory, idLabel):
	if idCategory == 0: return braille.roleLabels[braille.roleLabels.keys()[int(idLabel)]]
	elif idCategory == 1: return braille.landmarkLabels[idLabel]
	elif idCategory == 2: return braille.positiveStateLabels[int(idLabel)]
	elif idCategory == 3: return braille.negativeStateLabels[int(idLabel)]

def setLabelFromID(idCategory, idLabel, newLabel):
	if idCategory == 0: braille.roleLabels[braille.roleLabels.keys()[int(idLabel)]] = newLabel
	elif idCategory == 1: braille.landmarkLabels[idLabel] = newLabel
	elif idCategory == 2: braille.positiveStateLabels[int(idLabel)] = newLabel
	elif idCategory == 3: braille.negativeStateLabels[int(idLabel)] = newLabel

def loadRoleLabels(roleLabels):
	global backupRoleLabels
	for k, v in roleLabels.items():
		try:
			arg1 = int(k.split(':')[0])
			arg2 = k.split(':')[1]
			backupRoleLabels[k] = (v, getLabelFromID(arg1, arg2))
			setLabelFromID(arg1, arg2, v)
		except BaseException:
			log.error("Error during loading role label `%s`" % k)
			roleLabels.pop(k)
			config.conf["brailleExtender"]["roleLabels"] = roleLabels

def discardRoleLabels():
	global backupRoleLabels
	for k, v in backupRoleLabels.items():
		arg1 = int(k.split(':')[0])
		arg2 = k.split(':')[1]
		setLabelFromID(arg1, arg2, v[1])
	backupRoleLabels = {}

def loadConf():
	global quickLaunches, gesturesFileExists, inputTables, outputTables, profileFileExists, iniProfile
	confGen = (r"%s\%s\%s\profile.ini" % (profilesDir, curBD, config.conf["brailleExtender"]["profile_%s" % curBD]))
	if (curBD != "noBraille" and os.path.exists(confGen)):
		profileFileExists = True
		confspec = config.ConfigObj(StringIO(""""""), encoding="UTF-8", list_values=False)
		iniProfile = config.ConfigObj(confGen, configspec=confspec, indent_type="\t", encoding="UTF-8")
		result = iniProfile.validate(Validator())
		if result is not True:
			log.exception("Malformed configuration file")
			return False
	else:
		if curBD != "noBraille": log.warn("%s inaccessible" % confGen)
		else: log.debug("No braille display present")

	if (backupDisplaySize-config.conf["brailleExtender"]["rightMarginCells_" + curBD] <= backupDisplaySize and config.conf["brailleExtender"]["rightMarginCells_%s" % curBD] > 0):
		braille.handler.displaySize = backupDisplaySize-config.conf["brailleExtender"]["rightMarginCells_%s" % curBD]
	tmp1 = [k.strip() for k in config.conf["brailleExtender"]["quickLaunchGestures_%s" % curBD].split(';') if k.strip() != ""]
	tmp2 = [k.strip() for k in config.conf["brailleExtender"]["quickLaunchLocations_%s" % curBD].split(';') if k.strip() != ""]
	for i, gesture in enumerate(tmp1):
		if i >= len(tmp2): break
		quickLaunches[gesture] = tmp2[i]
	if not noUnicodeTable:
		listInputTables = [table[0] for table in brailleTables.listTables() if table.input]
		listOutputTables = [table[0] for table in brailleTables.listTables() if table.output]
		inputTables = config.conf["brailleExtender"]["inputTables"]
		outputTables = config.conf["brailleExtender"]["outputTables"]
		if not isinstance(inputTables, list):
			inputTables = inputTables.replace(', ', ',').split(',')
		if not isinstance(outputTables, list):
			outputTables = outputTables.replace(', ', ',').split(',')
		inputTables = [t for t in inputTables if t in listInputTables]
		outputTables = [t for t in outputTables if t in listOutputTables]
	if config.conf["brailleExtender"]["inputTableShortcuts"] not in tablesUFN:
		config.conf["brailleExtender"]["inputTableShortcuts"] = '?'
	loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())
	return True

def loadGestures():
	if gesturesFileExists:
		if os.path.exists(os.path.join(profilesDir, "_BrowseMode", config.conf["braille"]["inputTable"] + '.ini')): GLng = config.conf["braille"]["inputTable"]
		else: GLng = 'en-us-comp8.utb'
		gesturesBMPath = os.path.join(profilesDir, "_BrowseMode", "common.ini")
		gesturesLangBMPath = os.path.join(profilesDir, "_BrowseMode/", GLng + ".ini")
		inputCore.manager.localeGestureMap.load(gesturesBDPath())
		for fn in [gesturesBMPath, gesturesLangBMPath]:
			f = open(fn)
			tmp = [line.strip().replace(' ', '').replace('$', iniProfile["general"]["nameBK"]).replace('=', '=br(%s):' % curBD) for line in f if line.strip() and not line.strip().startswith('#') and line.count('=') == 1]
			tmp = {k.split('=')[0]: k.split('=')[1] for k in tmp}
		inputCore.manager.localeGestureMap.update({'browseMode.BrowseModeTreeInterceptor': tmp})

def gesturesBDPath(a = False):
	l = ['\\'.join([profilesDir, curBD, config.conf["brailleExtender"]["profile_%s" % curBD], "gestures.ini"]),
	'\\'.join([profilesDir, curBD, "default", "gestures.ini"])]
	if a: return '; '.join(l)
	for p in l:
		if os.path.exists(p): return p
	return '?'

def initGestures():
	global gesturesFileExists, iniGestures
	if profileFileExists and gesturesBDPath() != '?':
		log.debug('Main gestures map found')
		confGen = gesturesBDPath()
		confspec = config.ConfigObj(StringIO(""""""), encoding="UTF-8", list_values=False)
		iniGestures = config.ConfigObj(confGen, configspec=confspec, indent_type="\t", encoding="UTF-8")
		result = iniGestures.validate(Validator())
		if result is not True:
			log.exception("Malformed configuration file")
			gesturesFileExists = False
		else: gesturesFileExists = True
	else:
		log.warn('No main gestures map (%s) found' % gesturesBDPath(1))
		gesturesFileExists = False
	if gesturesFileExists:
		for g in iniGestures["globalCommands.GlobalCommands"]:
			if isinstance(
					iniGestures["globalCommands.GlobalCommands"][g],
					list):
				for h in range(
						len(iniGestures["globalCommands.GlobalCommands"][g])):
					iniGestures[inputCore.normalizeGestureIdentifier(
						str(iniGestures["globalCommands.GlobalCommands"][g][h]))] = g
			elif ('kb:' in g and g not in ["kb:alt', 'kb:control', 'kb:windows', 'kb:control', 'kb:applications"] and 'br(' + curBD + '):' in str(iniGestures["globalCommands.GlobalCommands"][g])):
				iniGestures[inputCore.normalizeGestureIdentifier(str(
					iniGestures["globalCommands.GlobalCommands"][g])).replace('br(' + curBD + '):', '')] = g
	return gesturesFileExists, iniGestures

def isContractedTable(table):
	if not table in tablesFN: return False
	tablePos = tablesFN.index(table)
	if brailleTables.listTables()[tablePos].contracted: return True
	return False

# remove old config files
cfgFile = globalVars.appArgs.configPath + r"\BrailleExtender.conf"
cfgFileAttribra = globalVars.appArgs.configPath + r"\attribra-BE.ini"
if os.path.exists(cfgFile): os.remove(cfgFile)
if os.path.exists(cfgFileAttribra): os.remove(cfgFileAttribra)
