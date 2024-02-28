# coding: utf-8
# addoncfg.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2022 André-Abush CLAUSE, released under GPL.

import os

import addonHandler
import braille
import config
import configobj
import globalVars
import inputCore
from logHandler import log

from .common import (addonUpdateChannel, configDir, profilesDir,
	MIN_AUTO_SCROLL_DELAY, DEFAULT_AUTO_SCROLL_DELAY, MAX_AUTO_SCROLL_DELAY, MIN_STEP_DELAY_CHANGE, DEFAULT_STEP_DELAY_CHANGE, MAX_STEP_DELAY_CHANGE,
	RC_NORMAL, RC_EMULATE_ARROWS_BEEP, RC_EMULATE_ARROWS_SILENT)
from .onehand import DOT_BY_DOT, ONE_SIDE, BOTH_SIDES

addonHandler.initTranslation()

Validator = configobj.validate.Validator

CHANNEL_stable = "stable"
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

outputMessage = dict([
	(CHOICE_none,             _("none")),
	(CHOICE_braille,          _("braille only")),
	(CHOICE_speech,           _("speech only")),
	(CHOICE_speechAndBraille, _("both"))
])

attributeChoices = dict([
	(CHOICE_none,   _("none")),
	(CHOICE_dots78, _("dots 7 and 8")),
	(CHOICE_dot7,   _("dot 7")),
	(CHOICE_dot8,   _("dot 8"))
])
attributeChoicesKeys = list(attributeChoices)
attributeChoicesValues = list(attributeChoices.values())

updateChannels = dict([
	(CHANNEL_stable,  _("stable")),
	(CHANNEL_dev,     _("development"))
])

focusOrReviewChoices = dict([
	(CHOICE_none,           _("none")),
	(CHOICE_focus,          _("focus mode")),
	(CHOICE_review,         _("review mode")),
	(CHOICE_focusAndReview, _("both"))
])

routingCursorsEditFields_labels = {
	RC_NORMAL: _("normal (recommended outside Windows consoles, IntelliJ, PyCharm...)"),
	RC_EMULATE_ARROWS_BEEP:   _("alternative, emulate left and right arrow keys with beeps"),
	RC_EMULATE_ARROWS_SILENT: _("alternative, emulate left and right arrow keys silently")
}
curBD = braille.handler.display.name
backupDisplaySize = braille.handler.displaySize

iniGestures = {}
iniProfile = {}
profileFileExists = gesturesFileExists = False

noMessageTimeout = True if 'noMessageTimeout' in config.conf["braille"] else False
outputTables = inputTables = None
preTable = []
postTable = []
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
		"lastNVDAVersion": 'string(default="unknown")',
		"updateChannel": f"option({CHANNEL_dev}, {CHANNEL_stable}, default={addonUpdateChannel})",
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
		"autoScroll": {
			"delay_%s" % curBD: f"integer(min={MIN_AUTO_SCROLL_DELAY}, default={DEFAULT_AUTO_SCROLL_DELAY}, max={MAX_AUTO_SCROLL_DELAY})",
			"stepDelayChange": f"integer(min={MIN_STEP_DELAY_CHANGE}, default={DEFAULT_STEP_DELAY_CHANGE}, max={MAX_STEP_DELAY_CHANGE})",
			"adjustToContent": "boolean(default=False)",
			"ignoreBlankLine": "boolean(default=True)",
		},
		"skipBlankLinesScroll": "boolean(default=False)",
		"speakScroll": "option({CHOICE_none}, {CHOICE_focus}, {CHOICE_review}, {CHOICE_focusAndReview}, default={CHOICE_focusAndReview})".format(
			CHOICE_none=CHOICE_none,
			CHOICE_focus=CHOICE_focus,
			CHOICE_review=CHOICE_review,
			CHOICE_focusAndReview=CHOICE_focusAndReview
		),
		"smartCapsLock": "boolean(default=True)",
		"stopSpeechScroll": "boolean(default=False)",
		"stopSpeechUnknown": "boolean(default=True)",
		"speakRoutingTo": "boolean(default=True)",
		"routingCursorsEditFields": f"option({RC_NORMAL}, {RC_EMULATE_ARROWS_BEEP}, {RC_EMULATE_ARROWS_SILENT}, default={RC_NORMAL})",
		"speechHistoryMode": {
			"enabled": "boolean(default=False)",
			"limit": "integer(min=0, default=50)",
			"numberEntries": "boolean(default=True)",
			"speakEntries": "boolean(default=True)",
			"backup_tetherTo": 'string(default="focus")',
			"backup_autoTether": "boolean(default=True)",
		},
		"inputTableShortcuts": 'string(default="?")',
		"inputTables": 'string(default="%s")' % config.conf["braille"]["inputTable"] + ", unicode-braille.utb",
		"outputTables": "string(default=%s)" % config.conf["braille"]["translationTable"],
		"tabSpace": "boolean(default=False)",
		f"tabSize_{curBD}": "integer(min=1, default=2, max=42)",
		"undefinedCharsRepr": {
			"method": f"integer(min=0, default=8)",
			"hardSignPatternValue": "string(default=??)",
			"hardDotPatternValue": "string(default=6-12345678)",
			"desc": "boolean(default=True)",
			"extendedDesc": "boolean(default=True)",
			"fullExtendedDesc": "boolean(default=False)",
			"showSize": "boolean(default=True)",
			"start": "string(default=[)",
			"end": "string(default=])",
			"lang": "string(default=Windows)",
			"table": "string(default=current)",
			"characterLimit": "integer(min=0, default=2048)",
		},
		"postTable": 'string(default="None")',
		"viewSaved": "string(default=%s)" % NOVIEWSAVED,
		"reviewModeTerminal": "boolean(default=True)",
		"features": {
			"attributes": "boolean(default=True)",
			"roleLabels": "boolean(default=False)"
		},
		"attributes": {
			"selectedElement": f"option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_dots78})",
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
			"strikethrough": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_none})".format(
				CHOICE_none=CHOICE_none,
				CHOICE_dot7=CHOICE_dot7,
				CHOICE_dot8=CHOICE_dot8,
				CHOICE_dots78=CHOICE_dots78
			),
			"text-position:sub": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_none})".format(
				CHOICE_none=CHOICE_none,
				CHOICE_dot7=CHOICE_dot7,
				CHOICE_dot8=CHOICE_dot8,
				CHOICE_dots78=CHOICE_dots78
			),
			"text-position:super": "option({CHOICE_none}, {CHOICE_dot7}, {CHOICE_dot8}, {CHOICE_dots78}, default={CHOICE_none})".format(
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
		"brailleTables": {},
		"advancedInputMode": {
			"stopAfterOneChar": "boolean(default=True)",
			"escapeSignUnicodeValue": "string(default=⠼)",
		},
		"oneHandedMode": {
			"enabled": "boolean(default=False)",
			"inputMethod": f"option({DOT_BY_DOT}, {BOTH_SIDES}, {ONE_SIDE}, default={ONE_SIDE})",
		},
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


def loadConf():
	global curBD, gesturesFileExists, profileFileExists, iniProfile
	curBD = braille.handler.display.name
	try: brlextConf = config.conf["brailleExtender"].copy()
	except configobj.validate.VdtValueError:
		config.conf["brailleExtender"]["updateChannel"] = "dev"
		brlextConf = config.conf["brailleExtender"].copy()
	if "profile_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["profile_%s" % curBD] = "default"
	if "tabSize_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["tabSize_%s" % curBD] = 2
	if "leftMarginCells__%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["leftMarginCells_%s" % curBD] = 0
	if "rightMarginCells_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["rightMarginCells_%s" % curBD] = 0
	if "autoScrollDelay_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["autoScrollDelay_%s" % curBD] = 3000
	if "keyboardLayout_%s" % curBD not in brlextConf.keys():
		config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] = "?"
	confGen = (r"%s\%s\%s\profile.ini" % (profilesDir, curBD, config.conf["brailleExtender"]["profile_%s" % curBD]))
	if (curBD != "noBraille" and os.path.exists(confGen)):
		profileFileExists = True
		confspec = config.ConfigObj("", encoding="UTF-8", list_values=False)
		iniProfile = config.ConfigObj(confGen, configspec=confspec, indent_type="\t", encoding="UTF-8")
		result = iniProfile.validate(Validator())
		if result is not True:
			log.exception("Malformed configuration file")
			return False
	else:
		if curBD != "noBraille": log.warn("%s inaccessible" % confGen)
		else: log.debug("No braille display present")

	limitCellsRight = int(config.conf["brailleExtender"]["rightMarginCells_%s" % curBD])
	if (backupDisplaySize-limitCellsRight <= backupDisplaySize and limitCellsRight > 0):
		braille.handler.displaySize = backupDisplaySize-limitCellsRight
	if not noUnicodeTable: loadPreferedTables()
	if config.conf["brailleExtender"]["inputTableShortcuts"] not in tablesUFN: config.conf["brailleExtender"]["inputTableShortcuts"] = '?'
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
	if a: return "; ".join(l)
	for p in l:
		if os.path.exists(p): return p
	return '?'

def initGestures():
	global gesturesFileExists, iniGestures
	if profileFileExists and gesturesBDPath() != '?':
		log.debug('Main gestures map found')
		confGen = gesturesBDPath()
		confspec = config.ConfigObj("", encoding="UTF-8", list_values=False)
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

def getKeyboardLayout():
	if (config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] is not None
	and config.conf["brailleExtender"]["keyboardLayout_%s" % curBD] in iniProfile['keyboardLayouts'].keys()):
		return iniProfile['keyboardLayouts'].keys().index(config.conf["brailleExtender"]["keyboardLayout_%s" % curBD])
	return 0

def getCustomBrailleTables():
	return [config.conf["brailleExtender"]["brailleTables"][k].split('|', 3) for k in config.conf["brailleExtender"]["brailleTables"]]

def getTabSize():
	size = config.conf["brailleExtender"]["tabSize_%s" % curBD]
	if size < 0: size = 2
	return size

# remove old config files
cfgFile = globalVars.appArgs.configPath + r"\BrailleExtender.conf"
cfgFileAttribra = globalVars.appArgs.configPath + r"\attribra-BE.ini"
if os.path.exists(cfgFile): os.remove(cfgFile)
if os.path.exists(cfgFileAttribra): os.remove(cfgFileAttribra)

if not os.path.exists(configDir): os.mkdir(configDir)
if not os.path.exists(os.path.join(configDir, "brailleDicts")): os.mkdir(os.path.join(configDir, "brailleDicts"))
