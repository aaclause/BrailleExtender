# coding: utf-8
# configBE.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os
from cStringIO import StringIO
import globalVars
#from colors import RGB
from collections import OrderedDict

import addonHandler
addonHandler.initTranslation()
import braille
import config
import configobj
if hasattr(configobj, "validate"):
	Validator = configobj.validate.Validator
else: from validate import Validator
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
CHOICE_dot7 = "dot7"
CHOICE_dot8 = "dot8"
CHOICE_dots78 = "dots78"
CHOICE_focus = "focus"
CHOICE_review = "review"
CHOICE_focusAndReview = "focusAndReview"
NOVIEWSAVED = chr(4)

outputMessage = OrderedDict([
	(CHOICE_none,             _("none")),
	(CHOICE_braille,          _("braille only")),
	(CHOICE_speech,           _("speech only")),
	(CHOICE_speechAndBraille, _("both"))
])

attributeChoices = OrderedDict([
	(CHOICE_none,   _("none")),
	(CHOICE_dots78, _("dots 7 and 8")),
	(CHOICE_dot7,   _("dot 7")),
	(CHOICE_dot8,   _("dot 8"))
])

updateChannels = OrderedDict([
	(CHANNEL_stable,  _("stable")),
	(CHANNEL_testing, _("testing")),
	(CHANNEL_dev,     _("development"))
])

focusOrReviewChoices = OrderedDict([
	(CHOICE_none,           _("none")),
	(CHOICE_focus,          _("focus mode")),
	(CHOICE_review,         _("review mode")),
	(CHOICE_focusAndReview, _("both"))
])
curBD = braille.handler.display.name
backupDisplaySize = braille.handler.displaySize
backupRoleLabels = {}
iniGestures = {}
iniProfile = {}
profileFileExists = gesturesFileExists = False
lang = languageHandler.getLanguage().split('_')[-1].lower()
noMessageTimeout = True if 'noMessageTimeout' in config.conf["braille"] else False
sep = ' ' if 'fr' in lang else ''
outputTables = inputTables = None
preTable = []
postTable = []
baseDir = os.path.dirname(__file__).decode("mbcs")
_addonDir = os.path.join(baseDir, "..", "..")
_addonName = addonHandler.Addon(_addonDir).manifest["name"]
_addonVersion = addonHandler.Addon(_addonDir).manifest["version"]
_addonURL = addonHandler.Addon(_addonDir).manifest["url"]
_addonAuthor = addonHandler.Addon(_addonDir).manifest["author"]
_addonDesc = addonHandler.Addon(_addonDir).manifest["description"]

profilesDir = os.path.join(baseDir, "Profiles")
if not os.path.exists(profilesDir): log.error('Profiles\' path not found')
else: log.debug('Profiles\' path (%s) found' % profilesDir)
try:
	import brailleTables
	tables = brailleTables.listTables()
	tablesFN = [t[0] for t in brailleTables.listTables()]
	tablesUFN = [t[0] for t in brailleTables.listTables() if not t.contracted and t.output]
	tablesTR = [t[1] for t in brailleTables.listTables()]
	noUnicodeTable = False
except BaseException:
	noUnicodeTable = True

def getValidBrailleDisplayPrefered():
	l = braille.getDisplayList()
	l.append(("last", _("last known")))
	return l

def getConfspec():
	global curBD
	curBD = braille.handler.display.name
	return {
		"autoCheckUpdate": "boolean(default=True)",
		"updateChannel": "option({CHANNEL_dev}, {CHANNEL_stable}, {CHANNEL_testing}, default={CHANNEL_stable})".format(
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
		"beepsModifiers": "boolean(default=False)",
		"volumeChangeFeedback": "option({CHOICE_none}, {CHOICE_braille}, {CHOICE_speech}, {CHOICE_speechAndBraille}, default={CHOICE_braille})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_braille=CHOICE_braille,
			CHOICE_speech=CHOICE_speech,
			CHOICE_speechAndBraille=CHOICE_speechAndBraille
		),
		"brailleDisplay1": 'string(default="last")',
		"brailleDisplay2": 'string(default="last")',
		"hourDynamic": "boolean(default=True)",
		"leftMarginCells_%s" % curBD: "integer(min=0, default=0, max=80)",
		"rightMarginCells_%s" % curBD: "integer(min=0, default=0, max=80)",
		"reverseScrollBtns": "boolean(default=False)",
		"autoScrollDelay_%s" % curBD: "integer(min=125, default=3000, max=42000)",
		"smartDelayScroll": "boolean(default=False)",
		"ignoreBlankLineScroll": "boolean(default=True)",
		"speakScroll": "option({CHOICE_none}, {CHOICE_focus}, {CHOICE_review}, {CHOICE_focusAndReview}, default={CHOICE_focusAndReview})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_focus=CHOICE_focus,
			CHOICE_review=CHOICE_review,
			CHOICE_focusAndReview=CHOICE_focusAndReview
		),
		"stopSpeechScroll": "boolean(default=False)",
		"stopSpeechUnknown": "boolean(default=True)",
		"speakRoutingTo": "boolean(default=True)",
		"routingReviewModeWithCursorKeys": "boolean(default=False)",
		"inputTableShortcuts": 'string(default="?")',
		"inputTables": 'string(default="%s")' % config.conf["braille"]["inputTable"] + ", unicode-braille.utb",
		"outputTables": "string(default=%s)" % config.conf["braille"]["translationTable"],
		"tabSpace": "boolean(default=False)",
		"tabSize_%s" % curBD: "integer(min=1, default=2, max=42)",
		"preventUndefinedCharHex":  "boolean(default=False)",
		"undefinedCharRepr": "string(default=0)",
		"postTable": 'string(default="None")',
		"viewSaved": "string(default=%s)" % NOVIEWSAVED,
		"reviewModeTerminal": "boolean(default=True)",
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
		"quickLaunches": {},
		"roleLabels": {}
	}

def loadPreferedTables():
	global inputTables, outputTables
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

def getLabelFromID(idCategory, idLabel):
	if idCategory == 0: return braille.roleLabels[int(idLabel)]
	elif idCategory == 1: return braille.landmarkLabels[idLabel]
	elif idCategory == 2: return braille.positiveStateLabels[int(idLabel)]
	elif idCategory == 3: return braille.negativeStateLabels[int(idLabel)]

def setLabelFromID(idCategory, idLabel, newLabel):
	if idCategory == 0: braille.roleLabels[int(idLabel)] = newLabel
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
		except BaseException as err:
			log.error("Error during loading role label `%s` (%s)" % (k, err))
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
	global curBD, gesturesFileExists, profileFileExists, iniProfile
	curBD = braille.handler.display.name
	brlextConf = config.conf["brailleExtender"].copy()
	if "profile_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["profile_%s" % curBD] = "default"
	if "tabSize_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["tabSize_%s" % curBD] = 2
	if "leftMarginCells__%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["leftMarginCells_%s" % curBD] = 0
	if "rightMarginCells__%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["rightMarginCells_%s" % curBD] = 0
	if "autoScrollDelay_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["autoScrollDelay_%s" % curBD] = 3000
	if "keyboardLayout_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] = "?"
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
	if not noUnicodeTable: loadPreferedTables()
	if config.conf["brailleExtender"]["inputTableShortcuts"] not in tablesUFN: config.conf["brailleExtender"]["inputTableShortcuts"] = '?'
	if config.conf["brailleExtender"]["features"]["roleLabels"]:
		loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())
	return True

def loadGestures():
	if gesturesFileExists:
		if os.path.exists(os.path.join(profilesDir, "_BrowseMode", config.conf["braille"]["inputTable"] + ".ini")): GLng = config.conf["braille"]["inputTable"]
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
		if curBD != "noBraille": log.warn('No main gestures map (%s) found' % gesturesBDPath(1))
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

def loadPostTable():
	global postTable
	postTable = []
	postTableValid = True if config.conf["brailleExtender"]["postTable"] in tablesFN else False
	if postTableValid:
		postTable.append(os.path.join(brailleTables.TABLES_DIR, config.conf["brailleExtender"]["postTable"]))
		log.debug('Secondary table enabled: %s' % config.conf["brailleExtender"]["postTable"])
	else:
		if config.conf["brailleExtender"]["postTable"] != "None":
			log.error("Invalid secondary table")
	tableChangesFile = os.path.join(baseDir, "", "undefinedChar.cti")
	defUndefinedChar = "undefined %s\n" % config.conf["brailleExtender"]["undefinedCharRepr"]
	if config.conf["brailleExtender"]["preventUndefinedCharHex"] and not os.path.exists(tableChangesFile):
		log.debug("File not found, creating undefined char file")
		createTableChangesFile(tableChangesFile, defUndefinedChar)
	if config.conf["brailleExtender"]["preventUndefinedCharHex"] and os.path.exists(tableChangesFile):
		f = open(tableChangesFile, "r")
		if f.read() != defUndefinedChar:
			log.debug("Difference, creating undefined char file...")
			if createTableChangesFile(tableChangesFile, defUndefinedChar):
				postTable.append(tableChangesFile)
		else:
			postTable.append(tableChangesFile)
		f.close()


def createTableChangesFile(f, c):
	try:
		f = open(f, "w")
		f.write(c)
		f.close()
		return True
	except BaseException as e:
		log.error('Error while creating tab file (%s)' % e)
		return False

def loadPreTable():
	global preTable
	preTable = []
	tableChangesFile = os.path.join(baseDir, "", "changes.cti")
	defTab = 'space \\t ' + \
		('0-' * config.conf["brailleExtender"]["tabSize_%s" % curBD])[:-1] + '\n'
	if config.conf["brailleExtender"]['tabSpace'] and not os.path.exists(tableChangesFile):
		log.debug("File not found, creating table changes file")
		createTableChangesFile(tableChangesFile, defTab)
	if config.conf["brailleExtender"]['tabSpace'] and os.path.exists(tableChangesFile):
		f = open(tableChangesFile, "r")
		if f.read() != defTab:
			log.debug('Difference, creating tab file...')
			if createTableChangesFile(tableChangesFile, defTab):
				preTable.append(tableChangesFile)
		else:
			preTable.append(tableChangesFile)
			log.debug('Tab as spaces enabled')
		f.close()
	else: log.debug('Tab as spaces disabled')

def getKeyboardLayout():
	if (config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] is not None
	and config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] in iniProfile['keyboardLayouts'].keys()):
		return iniProfile['keyboardLayouts'].keys().index(config.conf["brailleExtender"]["keyboardLayout_%s" % curBD])
	else: return 0


# remove old config files
cfgFile = globalVars.appArgs.configPath + r"\BrailleExtender.conf"
cfgFileAttribra = globalVars.appArgs.configPath + r"\attribra-BE.ini"
if os.path.exists(cfgFile): os.remove(cfgFile)
if os.path.exists(cfgFileAttribra): os.remove(cfgFileAttribra)
