# BrailleExtender Addon for NVDA
# This file is covered by the GNU General Public License.
# See the file LICENSE for more details.
# Copyright (C) 2016-2020 André-Abush Clause <dev@andreabc.net>
#
# Additional third party copyrighted code is included:
#  - *Attribra*: Copyright (C) 2017 Alberto Zanella <lapostadialberto@gmail.com>
#  -> https://github.com/albzan/attribra/

from collections import OrderedDict
from logHandler import log

import os
import re
import subprocess
import time
import gui
import wx

import addonHandler
addonHandler.initTranslation()
import api
import appModuleHandler
import braille
import brailleInput
import brailleTables
import config
import controlTypes
import cursorManager
import globalCommands
import globalPluginHandler
import globalVars
import inputCore
import keyboardHandler
import keyLabels
import languageHandler
import scriptHandler
import speech
import treeInterceptorHandler
import tones
import ui
import versionInfo
import virtualBuffers
from . import configBE
config.conf.spec["brailleExtender"] = configBE.getConfspec()
from . import utils
from .updateCheck import *
from . import advancedInputMode
from . import dictionaries
from . import huc
from . import patches
from . import settings
from .common import *
from . import undefinedChars

instanceGP = None
lang = configBE.lang
ATTRS = config.conf["brailleExtender"]["attributes"].copy().keys()
logTextInfo = False
rotorItems = [
	("default", _("Default")),
	("moveInText", _("Moving in the text")),
	("textSelection", _("Text selection")),
	("object", _("Objects")),
	("review", _("Review")),
	("Link", _("Links")),
	("UnvisitedLink", _("Unvisited links")),
	("VisitedLink", _("Visited links")),
	("Landmark", _("Landmarks")),
	("Heading", _("Headings")),
	("Heading1", _("Level 1 headings")),
	("Heading2", _("Level 2 headings")),
	("Heading3", _("Level 3 headings")),
	("Heading4", _("Level 4 headings")),
	("Heading5", _("Level 5 headings")),
	("Heading6", _("Level 6 headings")),
	("List", _("Lists")),
	("ListItem", _("List items")),
	("Graphic", _("Graphics")),
	("BlockQuote", _("Block quotes")),
	("Button", _("Buttons")),
	("FormField", _("Form fields")),
	("Edit", _("Edit fields")),
	("RadioButton", _("Radio buttons")),
	("ComboBox", _("Combo boxes")),
	("CheckBox", _("Check boxes")),
	("NotLinkBlock", _("Non-link blocks")),
	("Frame", _("Frames")),
	("Separator", _("Separators")),
	("EmbeddedObject", _("Embedded objects")),
	("Annotation", _("Annotations")),
	("Error", _("Spelling errors")),
	("Table", _("Tables")),
	("moveInTable", _("Move in table")),
]
rotorItem = 0
rotorRange = 0
lastRotorItemInVD = 0
lastRotorItemInVDSaved = True
HLP_browseModeInfo = ". %s" % _("If pressed twice, presents the information in browse mode")

# ***** Attribra code *****
def attribraEnabled():
	if instanceGP and instanceGP.BRFMode: return False
	return config.conf["brailleExtender"]["features"]["attributes"]

def decorator(fn, s):
	def _getTypeformFromFormatField(self, field, formatConfig=None):
		for attr in ATTRS:
			v = attr.split(':')
			k = v[0]
			v = True if len(v) == 1 else v[1]
			if k in field and (field[k] == v or field[k] == '1'):
				if config.conf["brailleExtender"]["attributes"][attr] == configBE.CHOICE_dot7: return 7
				if config.conf["brailleExtender"]["attributes"][attr] == configBE.CHOICE_dot8: return 8
				if config.conf["brailleExtender"]["attributes"][attr] == configBE.CHOICE_dots78: return 78
		# if COMPLCOLORS != None:
			# col = field.get("color",False)
			# if col and (col != COMPLCOLORS):
				# return 4
		return 0

	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		conf = formatConfig.copy()
		if attribraEnabled():
			conf["reportFontAttributes"] = True
			conf["reportColor"] = True
			conf["reportSpellingErrors"] = True
			if logTextInfo: log.info(info.getTextWithFields(conf))
		fn(self, info, conf, isSelection)

	def update(self):
		fn(self)
		if not attribraEnabled(): return
		DOT7 = 64
		DOT8 = 128
		size = len(self.rawTextTypeforms)
		for i, j in enumerate(self.rawTextTypeforms):
			try:
				start = self.rawToBraillePos[i]
				end = self.rawToBraillePos[i+1 if i+1 < size else (i if i<size else size-1)]
			except IndexError as e:
				log.debug(e)
				return
			k = start
			for k in range(start, end):
				if j == 78: self.brailleCells[k] |= DOT7 | DOT8
				if j == 7: self.brailleCells[k] |= DOT7
				if j == 8: self.brailleCells[k] |= DOT8

	if s == "addTextWithFields": return addTextWithFields_edit
	if s == "update": return update
	if s == "_getTypeformFromFormatField": return _getTypeformFromFormatField
# *************************


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = addonName
	brailleKeyboardLocked = False
	lastShortcutPerformed = None
	hideDots78 = False
	BRFMode = False
	advancedInput = False
	modifiersLocked = False
	hourDatePlayed = False
	hourDateTimer = None
	modifiers = set()
	_pGestures = OrderedDict()
	rotorGES = {}
	noKC = None
	if not configBE.noUnicodeTable:
		backupInputTable = brailleInput.handler.table
	backupMessageTimeout = None
	backupTether = utils.getTether()
	switchedMode = False

	def __init__(self):
		startTime = time.time()
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		patches.instanceGP = self
		self.reloadBrailleTables()
		settings.instanceGP = self
		configBE.loadConf()
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		checkingForced = False
		if config.conf["brailleExtender"]["lastNVDAVersion"] != updateCheck.versionInfo.version:
			config.conf["brailleExtender"]["lastNVDAVersion"] = updateCheck.versionInfo.version
			checkingForced = True
		delayChecking = 86400 if config.conf["brailleExtender"]["updateChannel"] != configBE.CHANNEL_stable else 604800
		if not globalVars.appArgs.secure and config.conf["brailleExtender"]["autoCheckUpdate"] and (checkingForced or (time.time() - config.conf["brailleExtender"]["lastCheckUpdate"]) > delayChecking):
			checkUpdates(True)
			config.conf["brailleExtender"]["lastCheckUpdate"] = time.time()
		self.backup__addTextWithFields = braille.TextInfoRegion._addTextWithFields
		self.backup__update = braille.TextInfoRegion.update
		self.backup__getTypeformFromFormatField = braille.TextInfoRegion._getTypeformFromFormatField
		self.backup__brailleTableDict = config.conf["braille"]["translationTable"]
		braille.TextInfoRegion._addTextWithFields = decorator(braille.TextInfoRegion._addTextWithFields, "addTextWithFields")
		braille.TextInfoRegion.update = decorator(braille.TextInfoRegion.update, "update")
		braille.TextInfoRegion._getTypeformFromFormatField = decorator(braille.TextInfoRegion._getTypeformFromFormatField, "_getTypeformFromFormatField")
		if config.conf["brailleExtender"]["reverseScrollBtns"]: self.reverseScrollBtns()
		self.createMenu()
		advancedInputMode.initialize()
		log.info(f"{addonName} {addonVersion} loaded ({round(time.time()-startTime, 2)}s)")

	def event_gainFocus(self, obj, nextHandler):
		global rotorItem, lastRotorItemInVD, lastRotorItemInVDSaved
		isVirtualBuff = obj is not None and isinstance(obj.treeInterceptor, virtualBuffers.VirtualBuffer)
		if lastRotorItemInVDSaved and isVirtualBuff:
			rotorItem = lastRotorItemInVD
			self.bindRotorGES()
			lastRotorItemInVDSaved = False
		elif not lastRotorItemInVDSaved and not isVirtualBuff:
			lastRotorItemInVD = rotorItem
			lastRotorItemInVDSaved = True
			rotorItem = 0
			self.bindRotorGES()

		if config.conf["brailleExtender"]["reviewModeTerminal"]:
			if not self.switchedMode and obj.role == controlTypes.ROLE_TERMINAL and obj.hasFocus:
				if not hasattr(braille.handler, "TETHER_AUTO"):
					self.backupTether = utils.getTether()
					braille.handler.tether = braille.handler.TETHER_REVIEW
				else:
					if config.conf["braille"]["autoTether"]:
						self.backupTether = braille.handler.TETHER_AUTO
						config.conf["braille"]["autoTether"] = False
					else:
						self.backupTether = utils.getTether()
					braille.handler.setTether(braille.handler.TETHER_REVIEW, auto=False)
					braille.handler.handleReviewMove(shouldAutoTether=False)
				self.switchedMode = True
			elif self.switchedMode and obj.role != controlTypes.ROLE_TERMINAL: self.restorReviewCursorTethering()

		if "tabSize_%s" % configBE.curBD not in config.conf["brailleExtender"].copy().keys(): self.onReload(None, 1)
		if self.hourDatePlayed: self.script_hourDate(None)
		if braille.handler._auto_scroll:
			braille.handler.toggle_auto_scroll()
		if self.autoTestPlayed: self.script_autoTest(None)
		if braille.handler is not None and configBE.curBD != braille.handler.display.name:
			configBE.curBD = braille.handler.display.name
			self.onReload(None, 1)

		if self.backup__brailleTableDict != config.conf["braille"]["translationTable"]: self.reloadBrailleTables()

		nextHandler()
		return

	def createMenu(self):
		self.submenu = wx.Menu()
		item = self.submenu.Append(wx.ID_ANY, _("Docu&mentation"), _("Opens the addon's documentation."))
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			lambda event: self.script_getHelp(None),
			item
		)
		item = self.submenu.Append(wx.ID_ANY, _("&Settings..."), _("Opens the addons' settings."))
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			lambda event: wx.CallAfter(gui.mainFrame._popupSettingsDialog, settings.AddonSettingsDialog),
			item
		)
		dictionariesMenu = wx.Menu()
		self.submenu.AppendSubMenu(dictionariesMenu, _("Table &dictionaries"), _("'Braille dictionaries' menu"))
		item = dictionariesMenu.Append(wx.ID_ANY, _("&Global dictionary"), _("A dialog where you can set global dictionary by adding dictionary entries to the list."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDefaultDictionary, item)
		item = dictionariesMenu.Append(wx.ID_ANY, _("&Table dictionary"), _("A dialog where you can set table-specific dictionary by adding dictionary entries to the list."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onTableDictionary, item)
		item = dictionariesMenu.Append(wx.ID_ANY, _("Te&mporary dictionary"), _("A dialog where you can set temporary dictionary by adding dictionary entries to the list."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onTemporaryDictionary, item)

		item = self.submenu.Append(wx.ID_ANY, _("Advanced &input mode dictionary..."), _("Advanced input mode configuration"))
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			lambda event: gui.mainFrame._popupSettingsDialog(advancedInputMode.AdvancedInputModeDlg),
			item
		)
		item = self.submenu.Append(wx.ID_ANY, "%s..." % _("&Quick launches"), _("Quick launches configuration"))
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			lambda event: wx.CallAfter(gui.mainFrame._popupSettingsDialog, settings.QuickLaunchesDlg),
			item
		)
		item = self.submenu.Append(wx.ID_ANY, _("Braille input table &overview"), _("Overview of the current input braille table"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, lambda event: self.script_getTableOverview(None), item)
		item = self.submenu.Append(wx.ID_ANY, _("&Reload add-on"), _("Reload this add-on."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onReload, item)
		item = self.submenu.Append(wx.ID_ANY, _("Check for &update..."), _("Checks if Braille Extender update is available"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onUpdate, item)
		item = self.submenu.Append(wx.ID_ANY, _("&Website"), _("Open addon's website."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onWebsite, item)
		item = self.submenu.Append(wx.ID_ANY, _("Get the latest template &translation file (.pot)"), _("Opens the URL to download the latest Portable Object Template file of the add-on"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_pot_file, item)
		self.submenu_item = gui.mainFrame.sysTrayIcon.menu.InsertMenu(2, wx.ID_ANY, "%s (%s)" % (_("&Braille Extender"), addonVersion), self.submenu)

	def reloadBrailleTables(self):
		self.backup__brailleTableDict = config.conf["braille"]["translationTable"]
		dictionaries.setDictTables()
		dictionaries.notifyInvalidTables()
		if config.conf["brailleExtender"]["tabSpace"]:
			liblouisDef = r"always \t " + ("0-" * configBE.getTabSize()).strip('-')
			patches.louis.compileString(patches.getCurrentBrailleTables(), bytes(liblouisDef, "ASCII"))
		undefinedChars.setUndefinedChar()

	@staticmethod
	def onDefaultDictionary(evt):
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryDlg, _("Global dictionary"), "default")

	@staticmethod
	def onTableDictionary(evt):
		outTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryDlg, _("Table dictionary ({})").format(outTable), "table")

	@staticmethod
	def onTemporaryDictionary(evt):
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryDlg, _("Temporary dictionary"), "tmp")

	def restorReviewCursorTethering(self):
		if not self.switchedMode: return
		if not hasattr(braille.handler, "TETHER_AUTO"):
			braille.handler.tether = self.backupTether
		else:
			if self.backupTether == braille.handler.TETHER_AUTO:
				config.conf["braille"]["autoTether"] = True
				config.conf["braille"]["tetherTo"] = braille.handler.TETHER_FOCUS
			else:
				config.conf["braille"]["autoTether"] = False
				braille.handler.setTether(self.backupTether, auto=False)
				if self.backupTether == braille.handler.TETHER_REVIEW:
					braille.handler.handleReviewMove(shouldAutoTether=False)
				else:
					focus = api.getFocusObject()
					if focus.treeInterceptor and not focus.treeInterceptor.passThrough:
						braille.handler.handleGainFocus(focus.treeInterceptor,shouldAutoTether=False)
					else:
						braille.handler.handleGainFocus(focus,shouldAutoTether=False)
		self.switchedMode = False

	def getGestureWithBrailleIdentifier(self, gesture = ''):
		return ("br(%s):" % configBE.curBD if ':' not in gesture else '')+gesture

	def gesturesInit(self):
		# rotor gestures
		if 'rotor' in configBE.iniProfile.keys():
			for k in configBE.iniProfile["rotor"]:
				if isinstance(configBE.iniProfile["rotor"][k], list):
					for l in configBE.iniProfile["rotor"][k]:
						self.rotorGES[self.getGestureWithBrailleIdentifier(l)] = k
				else:
					self.rotorGES[self.getGestureWithBrailleIdentifier(configBE.iniProfile["rotor"][k])] = k
			log.debug(self.rotorGES)
		else:
			log.debug("No rotor gestures for this profile")

		# keyboard layout gestures
		gK = OrderedDict()
		try:
			cK = configBE.iniProfile["keyboardLayouts"][config.conf["brailleExtender"]["keyboardLayout_%s" % configBE.curBD]] if config.conf["brailleExtender"]["keyboardLayout_%s" % configBE.curBD] and config.conf["brailleExtender"]["keyboardLayout_%s" % configBE.curBD] in configBE.iniProfile["keyboardLayouts"] is not None else configBE.iniProfile["keyboardLayouts"].keys()[0]
			for k in cK:
				if k in ["enter", "backspace"]:
					if isinstance(cK[k], list):
						for l in cK[k]:
							gK[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(l))] = 'kb:%s' % k
					else:
						gK['kb:%s' % k] = inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(cK[k]))
				elif k in ["braille_dots", "braille_enter", "braille_translate"]:
					if isinstance(cK[k], list):
						for i in range(len(cK[k])):
							if ':' not in cK[k][i]:
								cK[k][i] = inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(cK[k][i]))
					else:
						if ':' not in cK[k]:
							cK[k] = self.getGestureWithBrailleIdentifier(cK[k])
					gK[k] = cK[k]
			inputCore.manager.localeGestureMap.update({'globalCommands.GlobalCommands': gK})
			self.noKC = False
			log.debug("Keyboard conf found, loading layout `%s`" % config.conf["brailleExtender"]["keyboardLayout_%s" % configBE.curBD])
		except BaseException:
			log.debug("No keyboard conf found")
			self.noKC = True
		if configBE.gesturesFileExists:
			self._pGestures = OrderedDict()
			for k, v in (configBE.iniProfile["modifierKeys"].items() + [k for k in configBE.iniProfile["miscs"].items() if k[0] != 'defaultQuickLaunches']):
				if isinstance(v, list):
					for i, gesture in enumerate(v):
						self._pGestures[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(gesture))] = k
				else:
					self._pGestures[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(v))] = k
		self.bindGestures(self._pGestures)
		self.loadQuickLaunchesGes()

	def loadQuickLaunchesGes(self):
		self.bindGestures({k: "quickLaunch" for k in config.conf["brailleExtender"]["quickLaunches"].copy().keys() if '(%s' % configBE.curBD in k})

	def bindRotorGES(self):
		for k in self.rotorGES:
			try: self.removeGestureBinding(k)
			except BaseException: pass
		if rotorItems[rotorItem][0] == "default": return
		if rotorItems[rotorItem][0] in ["object", "review", "textSelection", "moveInText", "moveInTable"]:
			self.bindGestures(self.rotorGES)
		else:
			for k in self.rotorGES:
				if self.rotorGES[k] not in ["selectElt", "nextSetRotor", "priorSetRotor"]:
					self.bindGestures({k: self.rotorGES[k]})

	def script_priorRotor(self, gesture):
		global rotorItem
		if rotorItem > 0:
			rotorItem -= 1
		else:
			rotorItem = len(rotorItems) - 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem][1])
	script_priorRotor.__doc__ = _("Switches to the previous rotor setting")

	def script_nextRotor(self, gesture):
		global rotorItem
		rotorItem = 0 if rotorItem >= len(rotorItems) - 1 else rotorItem + 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem][1])
	script_nextRotor.__doc__ = _("Switches to the next rotor setting")

	@staticmethod
	def getCurrentSelectionRange(pretty=True, back=False):
		if pretty:
			labels = [
				_("Character"),
				_("Word"),
				_("Line"),
				_("Paragraph"),
				_("Page"),
				_("Document")]
			return labels[rotorRange]
		keys = [
			('leftarrow', 'rightarrow'),
			('control+leftarrow', 'control+rightarrow'),
			('uparrow', 'downarrow'),
			('control+uparrow', 'control+downarrow'),
			('pageup', 'pagedown'),
			('control+home', 'control+end')]
		if rotorItems[rotorItem][0] == "textSelection":
			return "shift+%s" % (keys[rotorRange][0] if back else keys[rotorRange][1])
		return keys[rotorRange][0] if back else keys[rotorRange][1]

	def switchSelectionRange(self, previous=False):
		global rotorRange
		if previous: rotorRange = rotorRange - 1 if rotorRange > 0 else 5
		else: rotorRange = rotorRange + 1 if rotorRange < 5 else 0
		ui.message(self.getCurrentSelectionRange())

	@staticmethod
	def moveTo(direction, gesture = None):
		global rotorItem
		obj = api.getFocusObject()
		if obj.treeInterceptor is not None:
			func = getattr(obj.treeInterceptor, "script_%s%s" % (direction, rotorItems[rotorItem][0]), None)
			if func: return func(gesture)
		ui.message(_("Not available here"))

	def script_nextEltRotor(self, gesture):
		if rotorItems[rotorItem][0] == "default": return self.sendComb('rightarrow', gesture)
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.sendComb(self.getCurrentSelectionRange(False), gesture)
		if rotorItems[rotorItem][0] == "object":
			self.sendComb('nvda+shift+rightarrow', gesture)
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_scrollForward, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+rightarrow', gesture)
		elif rotorItems[rotorItem][0] == "spellingErrors":
			obj = api.getFocusObject()
			if obj.treeInterceptor is not None:
				obj.treeInterceptor.script_nextError(gesture)
			else:
				ui.message(_("Not supported here or not in browse mode"))
		else: return self.moveTo("next", gesture)
	script_nextEltRotor.__doc__ = _("Moves to the next item based on rotor setting")

	def script_priorEltRotor(self, gesture):
		if rotorItems[rotorItem][0] == "default":
			return self.sendComb('leftarrow', gesture)
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.sendComb(self.getCurrentSelectionRange(False, True), gesture)
		if rotorItems[rotorItem][0] == "object":
			return self.sendComb("nvda+shift+leftarrow", gesture)
		if rotorItems[rotorItem][0] == "review":
			return scriptHandler.executeScript(
				globalCommands.commands.script_braille_scrollBack, gesture)
		if rotorItems[rotorItem][0] == "moveInTable":
			return self.sendComb('control+alt+leftarrow', gesture)
		if rotorItems[rotorItem][0] == "spellingErrors":
			obj = api.getFocusObject()
			if obj.treeInterceptor is not None:
				obj.treeInterceptor.script_previousError(gesture)
			else:
				ui.message(_("Not supported here or not in browse mode"))
		else: return self.moveTo("previous", gesture)
	script_priorEltRotor.__doc__ = _("Moves to the previous item based on rotor setting")

	def script_nextSetRotor(self, gesture):
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.switchSelectionRange()
		if rotorItems[rotorItem][0] == "object":
			self.sendComb('nvda+shift+downarrow', gesture)
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_nextLine, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+downarrow', gesture)
		else:
			return self.sendComb('downarrow', gesture)
	script_nextSetRotor.__doc__ = _("Moves to the next item based on rotor setting")

	def script_priorSetRotor(self, gesture):
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			self.switchSelectionRange(True)
		elif rotorItems[rotorItem][0] == "object":
			self.sendComb('nvda+shift+uparrow', gesture)
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_previousLine, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+uparrow', gesture)
		else:
			self.sendComb('uparrow', gesture)
	script_priorSetRotor.__doc__ = _("Moves to the previous item based on rotor setting")

	def script_selectElt(self, gesture):
		if rotorItems[rotorItem][0] == "object":
			self.sendComb('NVDA+enter', gesture)
		self.sendComb('enter', gesture)
	script_selectElt.__doc__ = _("Selects the item under the braille cursor e.g. doing default action if moving by objects")

	def script_toggleLockBrailleKeyboard(self, gesture):
		self.brailleKeyboardLocked = not self.brailleKeyboardLocked
		if self.brailleKeyboardLocked:
			ui.message(_("Braille keyboard locked"))
		else:
			ui.message(_("Braille keyboard unlocked"))
	script_toggleLockBrailleKeyboard.__doc__ = _("Toggles braille keyboard lock")

	def script_toggleOneHandMode(self, gesture):
		config.conf["brailleExtender"]["oneHandedMode"]["enabled"] = not config.conf["brailleExtender"]["oneHandedMode"]["enabled"]
		if config.conf["brailleExtender"]["oneHandedMode"]["enabled"]:
			ui.message(_("One-handed mode enabled"))
		else:
			ui.message(_("One handed mode disabled"))
	script_toggleOneHandMode.__doc__ = _("Toggles one-handed mode")

	def script_toggleDots78(self, gesture):
		self.hideDots78 = not self.hideDots78
		if self.hideDots78:
			speech.speakMessage(_("Dots 7 and 8 disabled"))
		else:
			speech.speakMessage(_("Dots 7 and 8 enabled"))
		utils.refreshBD()
	script_toggleDots78.__doc__ = _("Toggles showing or hiding dots 7 and 8")

	def script_toggleBRFMode(self, gesture):
		self.BRFMode = not self.BRFMode
		utils.refreshBD()
		if self.BRFMode:
			speech.speakMessage(_("BRF mode enabled"))
		else:
			speech.speakMessage(_("BRF mode disabled"))
	script_toggleBRFMode.__doc__ = _("Toggles BRF mode")

	def script_toggleLockModifiers(self, gesture):
		self.modifiersLocked = not self.modifiersLocked
		if self.modifiersLocked:
			ui.message(_("Modifier keys locked"))
		else:
			ui.message(_("Modifier keys unlocked"))
	script_toggleLockModifiers.__doc__ = _("Toggles locking modifier keys when using braille input")

	def script_toggleAttribra(self, gesture):
		config.conf["brailleExtender"]["features"]["attributes"] = not attribraEnabled()
		utils.refreshBD()
		if config.conf["brailleExtender"]["features"]["attributes"]:
			speech.speakMessage("Attribra enabled")
		else:
			speech.speakMessage("Attribra disabled")
	script_toggleAttribra.__doc__ = _("Toggles Attribra")

	def script_toggleSpeechScrollFocusMode(self, gesture):
		choices = configBE.focusOrReviewChoices
		curChoice = config.conf["brailleExtender"]["speakScroll"]
		curChoiceID = list(choices.keys()).index(curChoice)
		newChoiceID = (curChoiceID+1) % len(choices)
		newChoice = list(choices.keys())[newChoiceID]
		config.conf["brailleExtender"]["speakScroll"] = newChoice
		ui.message(list(choices.values())[newChoiceID].capitalize())
	script_toggleSpeechScrollFocusMode.__doc__ = _("Toggles between say current line while scrolling options between none, focus mode, review mode, or both")

	def script_toggleSpeech(self, gesture):
		if speech.speechMode == speech.speechMode_off:
			speech.speechMode = speech.speechMode_talk
			ui.message(_("Speech on"))
		else:
			speech.speechMode = speech.speechMode_off
			ui.message(_("Speech off"))
	script_toggleSpeech.__doc__ = _("Toggle speech on or off")

	def script_reportExtraInfos(self, gesture):
		obj = api.getNavigatorObject()
		msg = []
		if obj.name: msg.append(obj.name)
		if obj.description: msg.append(obj.description)
		if obj.value: msg.append(obj.value)
		if len(msg) == 0: return ui.message(_("No extra info for this element"))
		if scriptHandler.getLastScriptRepeatCount() == 0: ui.message((punctuationSeparator+": ").join(msg))
		else: ui.browseableMessage(('\n').join(msg))
	# Translators: Input help mode message for report extra infos command.
	script_reportExtraInfos.__doc__ = _("Reports some extra infos for the current element. For example, the URL on a link") + HLP_browseModeInfo

	def script_getTableOverview(self, gesture):
		inTable = brailleInput.handler.table.displayName
		ouTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		t = (_(" Input table")+": %s\n"+_("Output table")+": %s\n\n") % (inTable+' (%s)' % (brailleInput.handler.table.fileName), ouTable+' (%s)' % (config.conf["braille"]["translationTable"]))
		t += utils.getTableOverview()
		ui.browseableMessage("<pre>%s</pre>" % t, _("Table overview (%s)" % brailleInput.handler.table.displayName), True)
	script_getTableOverview.__doc__ = _("Shows an overview of current input braille table in a browseable message")

	def script_translateInBRU(self, gesture):
		tm = time.time()
		t = utils.getTextInBraille('', patches.getCurrentBrailleTables())
		if not t.strip(): return ui.message(_("No text selection"))
		ui.browseableMessage("<pre>%s</pre>" % t, _("Unicode Braille conversion") + (" (%.2f s)" % (time.time()-tm)), True)
	script_translateInBRU.__doc__ = _("Convert the text selection in unicode braille and display it in a browseable message")

	def script_charsToCellDescriptions(self, gesture):
		tm = time.time()
		t = utils.getTextInBraille('', patches.getCurrentBrailleTables())
		t = huc.unicodeBrailleToDescription(t)
		if not t.strip(): return ui.message(_("No text selection"))
		ui.browseableMessage(t, _("Braille Unicode to cell descriptions")+(" (%.2f s)" % (time.time()-tm)))
	script_charsToCellDescriptions.__doc__ = _("Convert text selection in braille cell descriptions and display it in a browseable message")

	def script_cellDescriptionsToChars(self, gesture):
		tm = time.time()
		t = utils.getTextSelection()
		if not t.strip(): return ui.message(_("No text selection"))
		t = huc.cellDescriptionsToUnicodeBraille(t)
		ui.browseableMessage(t, _("Cell descriptions to braille Unicode")+(" (%.2f s)" % (time.time()-tm)))
	script_cellDescriptionsToChars.__doc__ = _("Braille cell description to Unicode Braille. E.g.: in a edit field type '125-24-0-1-123-123'. Then select this text and execute this command")

	def script_advancedInput(self, gesture):
		self.advancedInput = not self.advancedInput
		if self.advancedInput:
			speech.speakMessage(_("Advanced braille input mode enabled"))
		else:
			speech.speakMessage(_("Advanced braille input mode disabled"))
	script_advancedInput.__doc__ = _("Toggles advanced input mode")

	def script_undefinedCharsDesc(self, gesture):
		config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"] = not config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]
		if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]:
			speech.speakMessage(_("Describe undefined characters enabled"))
		else:
			speech.speakMessage(_("Describe undefined characters disabled"))
		utils.refreshBD()
	script_undefinedCharsDesc.__doc__ = _("Toggles description of undefined characters")

	def script_position(self, gesture=None):
		curpos, total = utils.getTextPosition()
		if total:
			percentage = round((curpos / total * 100), 2)
			ui.message(f"{percentage}% ({curpos}/{total})")
		else:
			ui.message(_("No text"))
	script_position.__doc__ = _("Reports the cursor position of text under the braille cursor")

	def script_hourDate(self, gesture=None):
		if braille.handler._auto_scroll:
			return
		if self.hourDatePlayed:
			self.hourDateTimer.Stop()
			self.clearMessageFlash()
			if configBE.noMessageTimeout:
				config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
		else:
			if config.conf["brailleExtender"]["hourDynamic"]:
				if configBE.noMessageTimeout:
					self.backupMessageTimeout = config.conf["braille"]["noMessageTimeout"]
					config.conf["braille"]["noMessageTimeout"] = True
			self.showHourDate()
			if config.conf["brailleExtender"]["hourDynamic"]:
				self.hourDateTimer = wx.PyTimer(self.showHourDate)
				time.sleep(1.02 - round(time.time() - int(time.time()), 3))
				self.showHourDate()
				self.hourDateTimer.Start(1000)
			else:
				return
		self.hourDatePlayed = not self.hourDatePlayed
		return
	script_hourDate.__doc__ = _("Shows hour and date changes automatically on a braille display")

	@staticmethod
	def showHourDate():
		currentHourDate = time.strftime('%X %x (%a, %W/53, %b)', time.localtime())
		return braille.handler.message(currentHourDate)

	def script_autoScroll(self, gesture):
		braille.handler.toggle_auto_scroll()
	script_autoScroll.__doc__ = _("Toggles automatic braille scroll")

	def script_volumePlus(self, gesture):
		keyboardHandler.KeyboardInputGesture.fromName('volumeup').send()
		utils.report_volume_level()
	script_volumePlus.__doc__ = _("Increases the master volume")

	def script_volumeMinus(self, gesture):
		keyboardHandler.KeyboardInputGesture.fromName('volumedown').send()
		utils.report_volume_level()
	script_volumeMinus.__doc__ = _("Decreases the master volume")

	def script_toggleVolume(self, gesture):
		keyboardHandler.KeyboardInputGesture.fromName('volumemute').send()
		utils.report_volume_level()
	script_toggleVolume.__doc__ = _("Toggles sound mute")

	@staticmethod
	def clearMessageFlash():
		if config.conf["braille"]["messageTimeout"] != 0:
			if braille.handler.buffer is braille.handler.messageBuffer:
				braille.handler._dismissMessage()

	def script_getHelp(self, g):
		from . import addonDoc
		addonDoc.AddonDoc(self)
	script_getHelp.__doc__ = _("Shows the Braille Extender documentation")

	def noKeyboarLayout(self):
		return self.noKC

	def getKeyboardLayouts(self):
		if not self.noKC and "keyboardLayouts" in configBE.iniProfile:
			for layout in configBE.iniProfile["keyboardLayouts"]:
				t = []
				for lk in configBE.iniProfile["keyboardLayouts"][layout]:
					if lk in ["braille_dots", "braille_enter", "braille_translate"]:
						scriptName = 'script_%s' % lk
						func = getattr(globalCommands.GlobalCommands, scriptName, None)
						if isinstance(configBE.iniProfile["keyboardLayouts"][layout][lk], list):
							t.append(utils.beautifulSht(configBE.iniProfile["keyboardLayouts"][layout][lk]) + punctuationSeparator + ": " + func.__doc__)
						else:
							t.append(utils.beautifulSht(configBE.iniProfile["keyboardLayouts"][layout][lk]) + punctuationSeparator + ": " + func.__doc__)
					else:
						if isinstance(
								configBE.iniProfile["keyboardLayouts"][layout][lk], list):
							t.append(utils.beautifulSht(configBE.iniProfile["keyboardLayouts"][layout][lk]) + punctuationSeparator + ": " + utils.getKeysTranslation(lk))
						else:
							t.append(utils.beautifulSht(configBE.iniProfile["keyboardLayouts"][layout][lk]) + punctuationSeparator + ": " + utils.getKeysTranslation(lk))
				yield ((punctuationSeparator + '; ').join(t))

	def getGestures(s): return s.__gestures

	def script_quickLaunch(self, gesture):
		g = gesture.normalizedIdentifiers[0]
		quickLaunches = config.conf["brailleExtender"]["quickLaunches"].copy()
		if g not in quickLaunches.keys():
			ui.message('Target for %s not defined.' % gesture.id)
			return
		try: return subprocess.Popen(quickLaunches[g])
		except BaseException:
			try:
				os.startfile(quickLaunches[g])
			except BaseException:
				ui.message(_("No such file or directory"))
			return
	script_quickLaunch.__doc__ = _("Opens a custom program/file. Go to Braille Extender settings to define them")

	def script_checkUpdate(self, gesture):
		if not globalVars.appArgs.secure:
			checkUpdates()
		return
	script_checkUpdate.__doc__ = _("Checks for Braille Extender updates")

	def script_increaseDelayAutoScroll(self, gesture):
		braille.handler.increase_auto_scroll_delay()
		if not braille.handler._auto_scroll:
			braille.handler.report_auto_scroll_delay()
	script_increaseDelayAutoScroll.__doc__ = _("Increases braille autoscroll delay")

	def script_decreaseDelayAutoScroll(self, gesture):
		braille.handler.decrease_auto_scroll_delay()
		if not braille.handler._auto_scroll:
			braille.handler.report_auto_scroll_delay()
	script_decreaseDelayAutoScroll.__doc__ = _("Decreases braille autoscroll delay")

	def script_switchInputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("NVDA 2017.3 or later is required to use this feature"))
		if len(configBE.inputTables) < 2:
			return ui.message(_("You must choose at least two tables for this feature. Please fill in the settings"))
		if not config.conf["braille"]["inputTable"] in configBE.inputTables:
			configBE.inputTables.append(config.conf["braille"]["inputTable"])
		tid = configBE.inputTables.index(config.conf["braille"]["inputTable"])
		nID = tid + 1 if tid + 1 < len(configBE.inputTables) else 0
		brailleInput.handler.table = brailleTables.listTables(
		)[configBE.tablesFN.index(configBE.inputTables[nID])]
		ui.message(_("Input: %s") % brailleInput.handler.table.displayName)
		return
	script_switchInputBrailleTable.__doc__ = _("Switches between configured braille input tables")

	def script_switchOutputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("NVDA 2017.3 or later is required to use this feature"))
		if len(configBE.outputTables) < 2:
			return ui.message(_("You must choose at least two tables for this feature. Please fill in the settings"))
		if not config.conf["braille"]["translationTable"] in configBE.outputTables:
			configBE.outputTables.append(config.conf["braille"]["translationTable"])
		tid = configBE.outputTables.index(
			config.conf["braille"]["translationTable"])
		nID = tid + 1 if tid + 1 < len(configBE.outputTables) else 0
		config.conf["braille"]["translationTable"] = configBE.outputTables[nID]
		utils.refreshBD()
		dictionaries.setDictTables()
		ui.message(_("Output: %s") % configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])])
		return
	script_switchOutputBrailleTable.__doc__ = _("Switches between configured braille input tables")

	def script_currentBrailleTable(self, gesture):
		inTable = brailleInput.handler.table.displayName
		ouTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		if ouTable == inTable:
			braille.handler.message(_("I⣿O:{I}").format(I=inTable, O=ouTable))
			speech.speakMessage(_("Input and output: {I}.").format(I=inTable, O=ouTable))
		else:
			braille.handler.message(_("I:{I} ⣿ O: {O}").format(I=inTable, O=ouTable))
			speech.speakMessage(_("Input: {I}; Output: {O}").format(I=inTable, O=ouTable))
		return
	script_currentBrailleTable.__doc__ = _("Reports the current braille input and output tables")

	def script_brlDescChar(self, gesture):
		utils.currentCharDesc()
	script_brlDescChar.__doc__ = _("Reports the Unicode value of the character where the cursor is located and the decimal, binary and octal values")

	def script_getSpeechOutput(self, gesture):
		out = utils.getSpeechSymbols()
		if scriptHandler.getLastScriptRepeatCount() == 0: braille.handler.message(out)
		else: ui.browseableMessage(out)
	script_getSpeechOutput.__doc__ = _("Shows the output speech for selected text in braille, useful for emojis for example") + HLP_browseModeInfo

	def script_repeatLastShortcut(self, gesture):
		if not self.lastShortcutPerformed:
			ui.message(_("No shortcut performed from a braille display"))
			return
		sht =  self.lastShortcutPerformed
		inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(sht))
	script_repeatLastShortcut.__doc__ = _("Repeats the last shortcut performed from a braille display")

	def onReload(self, evt=None, sil=False, sv=False):
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		self._pGestures=OrderedDict()
		configBE.quickLaunches = OrderedDict()
		config.conf.spec["brailleExtender"] = configBE.getConfspec()
		configBE.loadConf()
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		if config.conf["brailleExtender"]["reverseScrollBtns"]:
			self.reverseScrollBtns()
		if not sil: ui.message(_("Braille Extender reloaded"))
		return

	@staticmethod
	def onUpdate(evt):
		return checkUpdates()

	@staticmethod
	def onWebsite(evt):
		return os.startfile(addonURL)

	@staticmethod
	def on_pot_file(evt):
		return os.startfile(f"{addonURL}/pot")


	def script_reloadAddon(self, gesture): self.onReload()
	script_reloadAddon.__doc__ = _("Reloads Braille Extender")

	def script_reload_brailledisplay1(self, gesture): self.reload_brailledisplay(1)
	script_reload_brailledisplay1.__doc__ = _("Reloads the primary braille display defined in settings")

	def script_reload_brailledisplay2(self, gesture): self.reload_brailledisplay(2)
	script_reload_brailledisplay2.__doc__ = _("Reloads the secondary braille display defined in settings")

	def reload_brailledisplay(self, n):
		k = "brailleDisplay%s" % (2 if n == 2 else 1)
		if config.conf["brailleExtender"][k] == "last":
			if config.conf["braille"]["display"] == "noBraille":
				return ui.message(_("No braille display specified. No reload to do"))
			utils.reload_brailledisplay(config.conf["braille"]["display"])
			configBE.curBD = braille.handler.display.name
			utils.refreshBD()
		else:
			utils.reload_brailledisplay(config.conf["brailleExtender"][k])
			configBE.curBD = config.conf["brailleExtender"][k]
			utils.refreshBD()
		return self.onReload(None, True)


	def clearModifiers(self, forced = False):
		if self.modifiersLocked and not forced: return
		brailleInput.handler.currentModifiers.clear()


	def sendComb(self, sht, gesture = None):
		inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(sht))

	def getActualModifiers(self, short=True):
		modifiers = brailleInput.handler.currentModifiers
		if len(modifiers) == 0:
			return self.script_cancelShortcut(None)
		s = ""
		t = {
			"windows": _("WIN"),
			"control": _("CTRL"),
			"shift": _("SHIFT"),
			"alt": _("ALT"),
			"nvda": "NVDA"}
		for k in modifiers:
			s += t[k] + '+' if short else k + '+'
		if not short:
			return s
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in [configBE.CHOICE_braille, configBE.CHOICE_speechAndBraille]:
			braille.handler.message('%s...' % s)
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in [configBE.CHOICE_speech, configBE.CHOICE_speechAndBraille]:
			speech.speakMessage(keyLabels.getKeyCombinationLabel('+'.join([m for m in self.modifiers])))

	def toggleModifier(self, modifier, beep = True):
		if modifier.lower() not in ["alt","control","nvda","shift","windows"]:
			return
		modifiers = brailleInput.handler.currentModifiers
		if modifier not in modifiers:
			modifiers.add(modifier)
			if beep and config.conf["brailleExtender"]["beepsModifiers"]: tones.beep(275, 50)
		else:
			modifiers.discard(modifier)
			if beep and config.conf["brailleExtender"]["beepsModifiers"]: tones.beep(100, 100 if len(modifiers) > 0 else 200)
		if len(modifiers) == 0: self.clearModifiers(True)

	def script_ctrl(self, gesture=None, sil=True):
		self.toggleModifier("control", sil)
		if sil: self.getActualModifiers()
		return

	def script_nvda(self, gesture=None):
		self.toggleModifier("nvda")
		self.getActualModifiers()
		return

	def script_alt(self, gesture=None, sil=True):
		self.toggleModifier("alt", sil)
		if sil: self.getActualModifiers()
		return

	def script_win(self, gesture=None, sil=True):
		self.toggleModifier("windows", sil)
		if sil: self.getActualModifiers()
		return

	def script_shift(self, gesture=None, sil=True):
		self.toggleModifier("shift", sil)
		if sil: self.getActualModifiers()
		return

	def script_ctrlWin(self, gesture):
		self.script_ctrl(None, False)
		return self.script_win(None)

	def script_altWin(self, gesture):
		self.script_alt(None, False)
		return self.script_win(None)

	def script_winShift(self, gesture):
		self.script_shift(None, False)
		return self.script_win(None)

	def script_ctrlShift(self, gesture):
		self.script_ctrl(None, False)
		return self.script_shift(None)

	def script_ctrlWinShift(self, gesture):
		self.script_ctrl(None, False)
		self.script_shift(None, False)
		return self.script_win(None)

	def script_altShift(self, gesture):
		self.script_alt(None, False)
		return self.script_shift()

	def script_altWinShift(self, gesture):
		self.script_alt(None, False)
		self.script_shift(None, False)
		return self.script_win()

	def script_ctrlAlt(self, gesture):
		self.script_ctrl(None, False)
		return self.script_alt()

	def script_ctrlAltWin(self, gesture):
		self.script_ctrl(None, False)
		self.script_alt(None, False)
		return self.script_win()

	def script_ctrlAltShift(self, gesture):
		self.script_ctrl(None, False)
		self.script_alt(None, False)
		return self.script_shift()

	def script_ctrlAltWinShift(self, gesture):
		self.script_ctrl(None, False)
		self.script_alt(None, False)
		self.script_shift(None, False)
		return self.script_win()

	def script_cancelShortcut(self, g):
		self.clearModifiers()
		self.clearMessageFlash()
		if not config.conf["brailleExtender"]["beepsModifiers"]:
			ui.message(_("Keyboard shortcut cancelled"))
		return
	script_nvda.bypassInputHelp = True
	script_alt.bypassInputHelp = True
	script_ctrl.bypassInputHelp = True
	script_cancelShortcut.bypassInputHelp = True

	# /* docstrings for modifier keys */
	def docModKeys(k): return _("Emulate pressing down ") + '+'.join(
		[utils.getKeysTranslation(l) for l in k.split('+')]) + _(" on the system keyboard")
	script_ctrl.__doc__ = docModKeys("control")
	script_alt.__doc__ = docModKeys("ALT")
	script_win.__doc__ = docModKeys("windows")
	script_shift.__doc__ = docModKeys("SHIFT")
	script_nvda.__doc__ = docModKeys("NVDA")
	script_altShift.__doc__ = docModKeys("ALT+SHIFT")
	script_ctrlShift.__doc__ = docModKeys("control+SHIFT")
	script_ctrlAlt.__doc__ = docModKeys("control+ALT")
	script_ctrlAltShift.__doc__ = docModKeys("control+ALT+SHIFT")
	script_ctrlWin.__doc__ = docModKeys("control+windows")
	script_altWin.__doc__ = docModKeys("ALT+windows")
	script_winShift.__doc__ = docModKeys("Windows+Shift")
	script_altWinShift.__doc__ = docModKeys("ALT+Windows+Shift")
	script_ctrlWinShift.__doc__ = docModKeys("control+Windows+SHIFT")
	script_ctrlAltWin.__doc__ = docModKeys("control+ALT+Windows")
	script_ctrlAltWinShift.__doc__ = docModKeys("control+ALT+Windows+SHIFT")

	def script_braille_scrollBack(self, gesture):
		braille.handler.scrollBack()
	script_braille_scrollBack.bypassInputHelp = True

	def script_braille_scrollForward(self, gesture):
		braille.handler.scrollForward()
	script_braille_scrollForward.bypassInputHelp = True

	def reverseScrollBtns(self, gesture=None, cancel=False):
		keyBraille = globalCommands.SCRCAT_BRAILLE
		if cancel:
			scbtns = [inputCore.manager.getAllGestureMappings()[keyBraille][g].gestures for g in inputCore.manager.getAllGestureMappings()[keyBraille] if inputCore.manager.getAllGestureMappings()[keyBraille][g].scriptName == 'braille_scrollForward'] + \
				[inputCore.manager.getAllGestureMappings()[keyBraille][g].gestures for g in inputCore.manager.getAllGestureMappings()[keyBraille] if inputCore.manager.getAllGestureMappings()[keyBraille][g].scriptName == 'braille_scrollBack']
		else:
			scbtns = [inputCore.manager.getAllGestureMappings()[keyBraille][g].gestures for g in inputCore.manager.getAllGestureMappings()[keyBraille] if inputCore.manager.getAllGestureMappings()[keyBraille][g].scriptName == 'braille_scrollBack'] + \
				[inputCore.manager.getAllGestureMappings()[keyBraille][g].gestures for g in inputCore.manager.getAllGestureMappings()[keyBraille] if inputCore.manager.getAllGestureMappings()[keyBraille][g].scriptName == 'braille_scrollForward']
		for k in scbtns[0]:
			if k.lower() not in [
				'br(freedomscientific):leftwizwheelup',
					'br(freedomscientific):leftwizwheeldown']:
				self.__gestures[k] = "braille_scrollForward"
		for k in scbtns[1]:
			if k.lower() not in [
				'br(freedomscientific):leftwizwheelup',
					'br(freedomscientific):leftwizwheeldown']:
				self.__gestures[k] = "braille_scrollBack"
		self.bindGestures(self.__gestures)
		return

	def script_logFieldsAtCursor(self, gesture):
		global logTextInfo
		logTextInfo = not logTextInfo
		msg = ["stop", "start"]
		ui.message("debug textInfo " + msg[logTextInfo])

	def script_saveCurrentBrailleView(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 0:
			config.conf["brailleExtender"]["viewSaved"] = ''.join(chr(c | 0x2800) for c in braille.handler.mainBuffer.brailleCells)
			ui.message(_("Current braille view saved"))
		else:
			config.conf["brailleExtender"]["viewSaved"] = configBE.NOVIEWSAVED
			ui.message(_("Buffer cleaned"))
	script_saveCurrentBrailleView.__doc__ = _("Saves the current braille view. Press twice quickly to clean the buffer")

	def script_showBrailleViewSaved(self, gesture):
		if config.conf["brailleExtender"]["viewSaved"] != configBE.NOVIEWSAVED:
			if scriptHandler.getLastScriptRepeatCount() == 0: braille.handler.message("⣇ %s ⣸" % config.conf["brailleExtender"]["viewSaved"])
			else: ui.browseableMessage(config.conf["brailleExtender"]["viewSaved"], _("View saved"), True)
		else: ui.message(_("Buffer empty"))
	script_showBrailleViewSaved.__doc__ = _("Shows the saved braille view through a flash message") + HLP_browseModeInfo

	# section autoTest
	autoTestPlayed = False
	autoTestTimer = None
	autoTestInterval = 1000
	autoTest_tests = ['⠁⠂⠄⡀⠈⠐⠠⢀', '⠉⠒⠤⣀ ⣀⣤⣶⣿⠿⠛⠉ ', '⡇⢸', '⣿']
	autoTest_gestures = {
		"kb:escape": "autoTest",
		"kb:q": "autoTest",
		"kb:space": "autoTestPause",
		"kb:p": "autoTestPause",
		"kb:r": "autoTestPause",
		"kb:s": "autoTestPause",
		"kb:j": "autoTestPrior",
		"kb:leftarrow": "autoTestPrior",
		"kb:rightarrow": "autoTestNext",
		"kb:k": "autoTestNext",
		"kb:uparrow": "autoTestIncrease",
		"kb:i": "autoTestIncrease",
		"kb:downarrow": "autoTestDecrease",
		"kb:o": "autoTestDecrease",
	}

	autoTest_type = 0
	autoTest_cellPtr = 0
	autoTest_charPtr = 0
	autoTest_pause = False
	autoTest_RTL = False

	def script_autoTestPause(self, gesture):
		if self.autoTest_charPtr > 0: self.autoTest_charPtr -= 1
		else: self.autoTest_charPtr = len(self.autoTest_tests[self.autoTest_type])-1
		self.autoTest_pause = not self.autoTest_pause
		msg = _("Pause") if self.autoTest_pause else _("Resume",)
		speech.speakMessage(msg)

	def showAutoTest(self):
		if self.autoTest_type == 1:
			braille.handler.message("%s" % (self.autoTest_tests[self.autoTest_type][self.autoTest_charPtr]*braille.handler.displaySize))
		else:
			braille.handler.message("%s%s" % (' '*self.autoTest_cellPtr, self.autoTest_tests[self.autoTest_type][self.autoTest_charPtr]))
		if self.autoTest_pause: return
		if self.autoTest_RTL:
			if self.autoTest_charPtr == 0:
				if self.autoTest_cellPtr == 0 or self.autoTest_type == 1: self.autoTest_RTL = False
				else:
					self.autoTest_cellPtr -= 1
					self.autoTest_charPtr = len(self.autoTest_tests[self.autoTest_type])-1
			else: self.autoTest_charPtr -= 1
		else:
			if self.autoTest_charPtr+1 == len(self.autoTest_tests[self.autoTest_type]):
				if self.autoTest_cellPtr+1 == braille.handler.displaySize or self.autoTest_type == 1: self.autoTest_RTL = True
				else:
					self.autoTest_cellPtr += 1
					self.autoTest_charPtr = 0
			else: self.autoTest_charPtr += 1

	def script_autoTestDecrease(self, gesture):
		self.autoTestInterval += 125
		self.autoTestTimer.Stop()
		self.autoTestTimer.Start(self.autoTestInterval)
		speech.speakMessage("%d ms" % self.autoTestInterval)

	def script_autoTestIncrease(self, gesture):
		if self.autoTestInterval-125 < 125: return
		self.autoTestInterval -= 125
		self.autoTestTimer.Stop()
		self.autoTestTimer.Start(self.autoTestInterval)
		speech.speakMessage("%d ms" % self.autoTestInterval)

	def script_autoTestPrior(self, gesture):
		if self.autoTest_type > 0: self.autoTest_type -= 1
		else: self.autoTest_type = len(self.autoTest_tests)-1
		self.autoTest_charPtr = self.autoTest_cellPtr = 0
		self.showAutoTest()
		speech.speakMessage(_("Auto test type %d" % self.autoTest_type))

	def script_autoTestNext(self, gesture):
		if self.autoTest_type+1 < len(self.autoTest_tests): self.autoTest_type += 1
		else: self.autoTest_type = 0
		self.autoTest_charPtr = self.autoTest_cellPtr = 0
		self.showAutoTest()
		speech.speakMessage(_("Auto test type %d" % self.autoTest_type))

	def script_autoTest(self, gesture):
		if self.autoTestPlayed:
			self.autoTestTimer.Stop()
			for k in self.autoTest_gestures:
				try: self.removeGestureBinding(k)
				except BaseException: pass
			self.autoTest_charPtr = self.autoTest_cellPtr = 0
			self.clearMessageFlash()
			speech.speakMessage(_("Auto test stopped"))
			if configBE.noMessageTimeout: config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
		else:
			if configBE.noMessageTimeout:
				self.backupMessageTimeout = config.conf["braille"]["noMessageTimeout"]
				config.conf["braille"]["noMessageTimeout"] = True
			self.showAutoTest()
			self.autoTestTimer = wx.PyTimer(self.showAutoTest)
			self.bindGestures(self.autoTest_gestures)
			self.autoTestTimer.Start(self.autoTestInterval)
			speech.speakMessage(_("Auto test started. Use the up and down arrow keys to change speed. Use the left and right arrow keys to change test type. Use space key to pause or resume the test. Use escape key to quit"))
		self.autoTestPlayed = not self.autoTestPlayed
	script_autoTest.__doc__ = _("Auto test")
	# end of section autoTest

	def script_addDictionaryEntry(self, gesture):
		curChar = utils.getCurrentChar()
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryEntryDlg, title=_("Add dictionary entry or see a dictionary"), textPattern=curChar, specifyDict=True)
	script_addDictionaryEntry.__doc__ = _("Adds an entry in braille dictionary")

	def script_toggle_blank_line_scroll(self, gesture):
		config.conf["brailleExtender"]["skipBlankLineScroll"] = not config.conf["brailleExtender"]["skipBlankLineScroll"]
		if config.conf["brailleExtender"]["skipBlankLineScroll"]:
			ui.message(_("Skip blank line while scrolling enabled"))
		else:
			ui.message(_("Skip blank line while scrolling disabled"))
	script_toggle_blank_line_scroll.__doc__ = _("Toggle blank line while scrolling")

	__gestures = OrderedDict()
	__gestures["kb:NVDA+control+shift+a"] = "logFieldsAtCursor"
	__gestures["kb:shift+NVDA+p"] = "currentBrailleTable"
	__gestures["kb:shift+NVDA+i"] = "switchInputBrailleTable"
	__gestures["kb:shift+NVDA+u"] = "switchOutputBrailleTable"
	__gestures["kb:shift+NVDA+y"] = "autoScroll"
	__gestures["kb:nvda+k"] = "reload_brailledisplay1"
	__gestures["kb:nvda+shift+k"] = "reload_brailledisplay2"
	__gestures["kb:nvda+alt+h"] = "toggleDots78"
	__gestures["kb:nvda+alt+f"] = "toggleBRFMode"
	__gestures["kb:nvda+windows+i"] = "advancedInput"
	__gestures["kb:nvda+windows+u"] = "undefinedCharsDesc"
	__gestures["kb:nvda+windows+h"] = "toggleOneHandMode"
	__gestures["kb:nvda+windows+k"] = "reloadAddon"
	__gestures["kb:volumeMute"] = "toggleVolume"
	__gestures["kb:volumeUp"] = "volumePlus"
	__gestures["kb:volumeDown"] = "volumeMinus"
	__gestures["kb:nvda+alt+u"] = "translateInBRU"
	__gestures["kb:nvda+alt+i"] = "charsToCellDescriptions"
	__gestures["kb:nvda+alt+o"] = "cellDescriptionsToChars"
	__gestures["kb:nvda+alt+y"] = "addDictionaryEntry"
	__gestures["kb:nvda+shift+j"] = "toggleAttribra"

	def terminate(self):
		braille.TextInfoRegion._addTextWithFields = self.backup__addTextWithFields
		braille.TextInfoRegion.update = self.backup__update
		braille.TextInfoRegion._getTypeformFromFormatField = self.backup__getTypeformFromFormatField
		self.removeMenu()
		self.restorReviewCursorTethering()
		configBE.discardRoleLabels()
		if configBE.noUnicodeTable:
			brailleInput.handler.table = self.backupInputTable
		if self.hourDatePlayed:
			self.hourDateTimer.Stop()
			if configBE.noMessageTimeout:
				config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
		if braille.handler._auto_scroll:
			braille.handler.toggle_auto_scroll()
		if self.autoTestPlayed: self.autoTestTimer.Stop()
		dictionaries.removeTmpDict()
		advancedInputMode.terminate()
		super().terminate()

	def removeMenu(self):
		gui.mainFrame.sysTrayIcon.menu.DestroyItem(self.submenu_item)

	@staticmethod
	def errorMessage(msg):
		wx.CallAfter(gui.messageBox, msg, _("Braille Extender"), wx.OK|wx.ICON_ERROR)
