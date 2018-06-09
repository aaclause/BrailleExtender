# coding: utf-8
# configBE.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
from os import path as osp
import ui
import re
from cStringIO import StringIO
from configobj import ConfigObj
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

CHOICE_none = 0
CHOICE_braille = 1
CHOICE_speech = 2
CHOICE_speechAndBraille = 3
CHOICE_dot78 = 1
CHOICE_dot7 = 2
CHOICE_dot8 = 3

outputMessage = OrderedDict([
	(CHOICE_none, _("none")),
	(CHOICE_braille, _("braille only")),
	(CHOICE_speech, _("speech only")),
	(CHOICE_speechAndBraille, _("both"))
])

attributeChoices = OrderedDict([
	(CHOICE_none, _("none")),
	(CHOICE_dot78, _("dots 7 and 8")),
	(CHOICE_dot7, _("dot 7")),
	(CHOICE_dot8, _("dot 8"))
])

updateChannels = OrderedDict([
	(CHANNEL_stable, _("stable")),
	(CHANNEL_testing, _("testing")),
	(CHANNEL_dev, _("development"))
])

curBD = braille.handler.display.name
cfgFile = globalVars.appArgs.configPath + '\\BrailleExtender.conf'
cfgFileAttribra = globalVars.appArgs.configPath + '\\attribra-BE.ini'
quickLaunches = OrderedDict()
backupDisplaySize = braille.handler.displaySize
conf = {}
iniGestures = {}
iniProfile = {}
confAttribra = {}
profileFileExists = gesturesFileExists = False
lang = languageHandler.getLanguage().split('_')[-1].lower()
noMessageTimeout = True if 'noMessageTimeout' in config.conf["braille"] else False
sep = ' ' if 'fr' in lang else ''
oTables = iTables = None
_addonDir = osp.join(osp.dirname(__file__), "..", "..").decode("mbcs")
_addonName = addonHandler.Addon(_addonDir).manifest['name']
_addonVersion = addonHandler.Addon(_addonDir).manifest['version']
_addonURL = addonHandler.Addon(_addonDir).manifest['url']
_addonAuthor = addonHandler.Addon(_addonDir).manifest['author']
_addonDesc = addonHandler.Addon(_addonDir).manifest['description']
profilesDir = osp.join(osp.dirname(__file__), "Profiles").decode('mbcs')
if not osp.exists(profilesDir): log.error('Profiles\' path not found')
else: log.debug('Profiles\' path (%s) found' % profilesDir)
begFileAttribra = """# Attribra for BrailleExtender
# Thanks to Alberto Zanella
# -> https://github.com/albzan/attribra/
"""
try:
	import brailleTables
	tablesFN = [t[0] for t in brailleTables.listTables()]
	tablesUFN = [t[0] for t in brailleTables.listTables() if not t.contracted and t.output]
	tablesTR = [t[1] for t in brailleTables.listTables()]
	noUnicodeTable = False
except BaseException:
	noUnicodeTable = True

def loadConf():
	global conf, quickLaunches, gesturesFileExists, iTables, oTables, profileFileExists, iniProfile
	confspec = ConfigObj(StringIO("""
	[general]
		autoCheckUpdate = boolean(default=True)
		channelUpdate = option({CHANNEL_dev}, {CHANNEL_stable}, default={CHANNEL_stable})
		lastCheckUpdate = float(min=0, default=0)
		profile_{CUR_BD} = string(default="default")
		keyboardLayout_{CUR_BD} = string(default={KEYBOARDLAYOUT})
		modifierKeysFeedback = integer(min={CHOICE_none}, max={CHOICE_speechAndBraille}, default={CHOICE_braille})
		volumeChangeFeedback = integer(min={CHOICE_none}, max={CHOICE_speechAndBraille}, default={CHOICE_braille})
		brailleDisplay1 = string(default="noBraille")
		brailleDisplay2 = string(default="noBraille")
		hourDynamic = boolean(default=True)
		leftMarginCells_{CUR_BD} = integer(min=0, default=0, max={MAX_CELLS})
		rightMarginCells_{CUR_BD} = integer(min=0, default=0, max={MAX_CELLS})
		delayScroll_{CUR_BD} = float(min=0, default=3, max={MAX_DELAYSCROLL})
		smartDelayScroll = boolean(default=False)
		reverseScroll = boolean(default=False)
		ignoreBlankLineScroll = boolean(default=True)
		speakScrollReviewMode = boolean(default=True)
		speakScrollFocusMode = boolean(default=False)
		stopSpeechScroll = boolean(default=False)
		stopSpeechUnknown = boolean(default=True)
		speakRoutingTo = boolean(default=True)
		iTableShortcuts = string(default="?")
		iTables = string(default="{ITABLE}")
		oTables = string(default="{OTABLE}")
		quickLaunchGestures_{CUR_BD} = string(default="{QLGESTURES}")
		quickLaunchLocations_{CUR_BD} = string(default="notepad; wordpad; calc; cmd")
		attribra = boolean(default=True)
		tabSpace = boolean(default=False)
		tabSize = integer(min=1, default=2, max=42)
		postTable = string(default="None")
		viewSaved = string(default="None")
	""".format(
		CHANNEL_dev=CHANNEL_dev,
		CHANNEL_stable=CHANNEL_stable,
		CHOICE_none=CHOICE_none,
		CHOICE_braille=CHOICE_braille,
		CHOICE_speech=CHOICE_speech,
		CHOICE_speechAndBraille=CHOICE_speechAndBraille,
		CUR_BD=curBD,
		MAX_BD=42,
		ITABLE=config.conf["braille"]["inputTable"] + ', unicode-braille.utb',
		OTABLE=config.conf["braille"]["translationTable"],
		MAX_CELLS=420,
		MAX_DELAYSCROLL=999,
		MAX_TABLES=420,
		KEYBOARDLAYOUT=iniProfile['keyboardLayouts'].keys()[0] if 'keyboardLayouts' in iniProfile.keys() else None,
		QLGESTURES=iniProfile['miscs']['defaultQuickLaunches'] if 'miscs' in iniProfile.keys() else ''
	)), encoding="UTF-8", list_values=False)
	confspec.initial_comment = ['%s (%s)' % (_addonName, _addonVersion), _addonURL]
	confspec.final_comment = ['End Of File']
	confspec.newlines = "\n"
	conf = ConfigObj(cfgFile, configspec=confspec, indent_type="\t", encoding="UTF-8")
	result = conf.validate(Validator())
	if result is not True:
		log.error('Malformed configuration file')
		return False
	else:
		confspec = ConfigObj(StringIO(""""""), encoding="UTF-8", list_values=False)
		confGen = ('%s\%s\%s\profile.ini' % (profilesDir, curBD, conf["general"]["profile_%s" % curBD]))
		if (curBD != 'noBraille' and osp.exists(confGen)):
			profileFileExists = True
			iniProfile = ConfigObj(confGen, configspec=confspec, indent_type="\t", encoding="UTF-8")
			result = iniProfile.validate(Validator())
			if result is not True:
				log.exception('Malformed configuration file')
				return False
		else:
			if curBD != 'noBraille': log.warn('%s inaccessible' % confGen)
			else: log.debug('No braille display present')
	if (backupDisplaySize-conf["general"]["rightMarginCells_" + curBD] <= backupDisplaySize and conf["general"]["rightMarginCells_" + curBD] > 0):
		braille.handler.displaySize = backupDisplaySize-conf["general"]["rightMarginCells_" + curBD]
	tmp1 = [k.strip() for k in conf["general"]["quickLaunchGestures_%s" % curBD].split(';') if k.strip() != '']
	tmp2 = [k.strip() for k in conf["general"]["quickLaunchLocations_%s" % curBD].split(';') if k.strip() != '']
	for i, gesture in enumerate(tmp1):
		if i >= len(tmp2): break
		quickLaunches[gesture] = tmp2[i]
	if not noUnicodeTable:
		lITables = [table[0] for table in brailleTables.listTables() if table.input]
		lOTables = [table[0] for table in brailleTables.listTables() if table.output]
		iTables = conf["general"]['iTables']
		oTables = conf["general"]['oTables']
		if not isinstance(iTables, list):
			iTables = iTables.replace(', ', ',').split(',')
		if not isinstance(oTables, list):
			oTables = oTables.replace(', ', ',').split(',')
		iTables = [t for t in iTables if t in lITables]
		oTables = [t for t in oTables if t in lOTables]
	return True


def loadGestures():
	if gesturesFileExists:
		if osp.exists(osp.join(profilesDir, "_BrowseMode", config.conf["braille"]["inputTable"] + '.ini')): GLng = config.conf["braille"]["inputTable"]
		else: GLng = 'en-us-comp8.utb'
		gesturesBMPath = osp.join(profilesDir, "_BrowseMode", "common.ini")
		gesturesLangBMPath = osp.join(profilesDir, "_BrowseMode/", GLng + ".ini")
		inputCore.manager.localeGestureMap.load(gesturesBDPath())
		for fn in [gesturesBMPath, gesturesLangBMPath]:
			f = open(fn)
			tmp = [line.strip().replace(' ', '').replace('$', iniProfile["general"]['nameBK']).replace('=', '=br(%s):' % curBD) for line in f if line.strip() and not line.strip().startswith('#') and line.count('=') == 1]
			tmp = {k.split('=')[0]: k.split('=')[1] for k in tmp}
		inputCore.manager.localeGestureMap.update({'browseMode.BrowseModeTreeInterceptor': tmp})


def saveSettings():
	global conf
	try:
		conf.validate(Validator(), copy=True)
		conf.write()
		log.debug('%s add-on configuration saved' % _addonName)
	except BaseException:
		log.exception('Cannot save Configuration')
	return


def translateRule(E):
	r = []
	for e in E:
		if isinstance(e, RGB):
			r.append('"RGB(%s, %s, %s)"' % (e.red, e.green, e.blue))
		else:
			r.append('"%s"' % e)
	return ', '.join(r)


def saveSettingsAttribra():
	global confAttribra
	try:
		f = open(globalVars.appArgs.configPath + '\\attribra-BE.ini', "w")
		c = begFileAttribra + '\n'
		for k in sorted(confAttribra.keys()):
			c += '[%s]\n' % k
			for kk, v in confAttribra[k].items():
				if kk not in [
					'bold',
					'italic',
					'underline',
						'invalid-spelling']:
					vv = translateRule(v)
				else:
					vv = v[0]
				c += '%s = %s\n' % (kk, vv)
			c += '\n'
		f.write(c)
		f.close()
	except BaseException as e:
		ui.message('Error: ' + str(e))
	return


def gesturesBDPath(a = False):
	l = ['\\'.join([profilesDir, curBD, conf["general"]["profile_%s" % curBD], "gestures.ini"]),
	'\\'.join([profilesDir, curBD, "default", "gestures.ini"])]
	if a: return '; '.join(l)
	for p in l:
		if osp.exists(p): return p
	return '?'



def initGestures():
	global gesturesFileExists, iniGestures
	if profileFileExists and gesturesBDPath() != '?':
		log.debug('Main gestures map found')
		confGen = gesturesBDPath()
		confspec = ConfigObj(StringIO(""""""), encoding="UTF-8", list_values=False)
		iniGestures = ConfigObj(confGen, configspec=confspec, indent_type="\t", encoding="UTF-8")
		result = iniGestures.validate(Validator())
		if result is not True:
			log.exception('Malformed configuration file')
			gesturesFileExists = False
		else:
			gesturesFileExists = True
	else:
		log.warn('No main gestures map (%s) found' % gesturesBDPath(1))
		gesturesFileExists = False
	if gesturesFileExists:
		for g in iniGestures['globalCommands.GlobalCommands']:
			if isinstance(
					iniGestures['globalCommands.GlobalCommands'][g],
					list):
				for h in range(
						len(iniGestures['globalCommands.GlobalCommands'][g])):
					iniGestures[inputCore.normalizeGestureIdentifier(
						str(iniGestures['globalCommands.GlobalCommands'][g][h]))] = g
			elif ('kb:' in g and g not in ['kb:alt', 'kb:control', 'kb:windows', 'kb:control', 'kb:applications'] and 'br(' + curBD + '):' in str(iniGestures['globalCommands.GlobalCommands'][g])):
				iniGestures[inputCore.normalizeGestureIdentifier(str(
					iniGestures['globalCommands.GlobalCommands'][g])).replace('br(' + curBD + '):', '')] = g
	return gesturesFileExists, iniGestures


def loadConfAttribra():
	global confAttribra
	try:
		cfg = ConfigObj(cfgFileAttribra, encoding="UTF-8")
		for app, mapping in cfg.iteritems():
			mappings = {}
			for name, value in mapping.iteritems():
				if isinstance(value, basestring):
					if value.startswith("RGB("):  # it's an RGB Object
						rgbval = value.split("RGB(")[1]
						rgbval = rgbval.split(")")[0]
						rgbval = rgbval.split(",")
						mappings[name] = [
							RGB(int(rgbval[0]), int(rgbval[1]), int(rgbval[2]))]
					else:
						try:
							# if possible adds the value and its int
							mappings[name] = [value, int(value)]
						except ValueError:
							mappings[name] = [value]
				else:
					mappings[name] = value
			confAttribra[app] = mappings
	except IOError:
		log.debugWarning("No Attribra config file found")

loadConf()

if not osp.exists(cfgFileAttribra):
	f = open(globalVars.appArgs.configPath + '\\attribra-BE.ini', "w")
	f.write(begFileAttribra + """

[global]
	bold = 1

[winword]
	invalid-spelling = 1

[eclipse]
	background-color = "rgb(24420045)", "rgb(2550128)"

[firefox]
	color = "RGB(255,0,0)"

[thunderbird]
	invalid-spelling = 1
	""")
	f.close()

if conf["general"]['iTableShortcuts'] not in tablesUFN:
	conf["general"]['iTableShortcuts'] = '?'

def isContractedTable(table):
	if not table in tablesFN: return False
	tablePos = tablesFN.index(table)
	if brailleTables.listTables()[tablePos].contracted: return True
	return False
