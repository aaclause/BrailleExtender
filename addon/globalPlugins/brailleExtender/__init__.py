# coding: utf-8
# BrailleExtender Addon for NVDA
# This file is covered by the GNU General Public License.
# See the file LICENSE for more details.
# Copyright (C) 2016-2020 André-Abush Clause <dev@andreabc.net>
#
# Additional third party copyrighted code is included:
#  - *Attribra*: Copyright (C) 2017 Alberto Zanella <lapostadialberto@gmail.com>
#  -> https://github.com/albzan/attribra/
from __future__ import unicode_literals
from collections import OrderedDict
from logHandler import log

import os
import re
import subprocess
import sys
import time
import urllib
import gui
import wx

from . import settings

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
from . import patchs
from .common import *

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
	("Heading1", _("Headings at level 1")),
	("Heading2", _("Headings at level 2")),
	("Heading3", _("Headings at level 3")),
	("Heading4", _("Headings at level 4")),
	("Heading5", _("Headings at level 5")),
	("Heading6", _("Headings at level 6")),
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
	("NotLinkBlock", _("Not link blocks")),
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
	autoScrollRunning = False
	autoScrollTimer = None
	modifiers = set()
	_pGestures = OrderedDict()
	rotorGES = {}
	noKC = None
	if not configBE.noUnicodeTable:
		backupInputTable = brailleInput.handler.table
	backupMessageTimeout = None
	backupShowCursor = False
	backupTether = utils.getTether()
	switchedMode = False

	def __init__(self):
		startTime = time.time()
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		patchs.instanceGP = self
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
		delayChecking = 86400 if isPy3 or config.conf["brailleExtender"]["updateChannel"] != configBE.CHANNEL_stable else 604800
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
		if self.autoScrollRunning: self.script_autoScroll(None)
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
		item = self.submenu.Append(wx.ID_ANY, "%s..." % _("&Settings"), _("Opens the addons' settings."))
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

		item = self.submenu.Append(wx.ID_ANY, "%s..." % _("Advanced &input mode dictionary"), _("Advanced input mode configuration"))
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
		item = self.submenu.Append(wx.ID_ANY, "%s..." % _("&Profile editor"), _("Profile editor"))
		gui.mainFrame.sysTrayIcon.Bind(
			wx.EVT_MENU,
			lambda event: wx.CallAfter(gui.mainFrame._popupSettingsDialog, settings.ProfileEditorDlg),
			item
		)
		item = self.submenu.Append(wx.ID_ANY, _("Overview of the current input braille table"), _("Overview of the current input braille table"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, lambda event: self.script_getTableOverview(None), item)
		item = self.submenu.Append(wx.ID_ANY, _("Reload add-on"), _("Reload this add-on."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onReload, item)
		item = self.submenu.Append(wx.ID_ANY, "%s..." % _("&Check for update"), _("Checks if update is available"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onUpdate, item)
		item = self.submenu.Append(wx.ID_ANY, _("&Website"), _("Open addon's website."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onWebsite, item)
		self.submenu_item = gui.mainFrame.sysTrayIcon.menu.InsertMenu(2, wx.ID_ANY, "%s (%s)" % (_("&Braille Extender"), addonVersion), self.submenu)

	def reloadBrailleTables(self):
		self.backup__brailleTableDict = config.conf["braille"]["translationTable"]
		dictionaries.setDictTables()
		dictionaries.notifyInvalidTables()
		if config.conf["brailleExtender"]["tabSpace"]:
			liblouisDef = r"always \t " + ("0-" * configBE.getTabSize()).strip('-')
			if isPy3:
				patchs.louis.compileString(patchs.getCurrentBrailleTables(), bytes(liblouisDef, "ASCII"))
			else: patchs.louis.compileString(patchs.getCurrentBrailleTables(), bytes(liblouisDef))
		patchs.setUndefinedChar()

	@staticmethod
	def onDefaultDictionary(evt):
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryDlg, _("Global dictionary"), "default")

	@staticmethod
	def onTableDictionary(evt):
		outTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		gui.mainFrame._popupSettingsDialog(dictionaries.DictionaryDlg, _("Table dictionary")+(" (%s)" % outTable), "table")

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

	def script_nextRotor(self, gesture):
		global rotorItem
		rotorItem = 0 if rotorItem >= len(rotorItems) - 1 else rotorItem + 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem][1])

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
		else:
			keys = [
				('leftarrow',
				 'rightarrow'),
				('control+leftarrow',
				 'control+rightarrow'),
				('uparrow',
				 'downarrow'),
				('control+uparrow',
				 'control+downarrow'),
				('pageup',
				 'pagedown'),
				('control+home',
				 'control+end')]
			if rotorItems[rotorItem][0] == "textSelection":
				return 'shift+%s' % (keys[rotorRange]
									 [0] if back else keys[rotorRange][1])
			else:
				return keys[rotorRange][0] if back else keys[rotorRange][1]

	def switchSelectionRange(self, previous=False):
		global rotorRange
		if previous: rotorRange = rotorRange - 1 if rotorRange > 0 else 5
		else: rotorRange = rotorRange + 1 if rotorRange < 5 else 0
		ui.message(self.getCurrentSelectionRange())
		return

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
		elif rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.sendComb(self.getCurrentSelectionRange(False), gesture)
		elif rotorItems[rotorItem][0] == "object":
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
				ui.message(_("Not supported here or browse mode not enabled"))
		else: return self.moveTo("next", gesture)
	script_priorRotor.__doc__ = _("Select previous rotor setting")
	script_nextRotor.__doc__ = _("Select next rotor setting")

	def script_priorEltRotor(self, gesture):
		if rotorItems[rotorItem][0] == "default":
			return self.sendComb('leftarrow', gesture)
		elif rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.sendComb(self.getCurrentSelectionRange(False, True), gesture)
		elif rotorItems[rotorItem][0] == "object":
			self.sendComb("nvda+shift+leftarrow", gesture)
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_scrollBack, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+leftarrow', gesture)
		elif rotorItems[rotorItem][0] == "spellingErrors":
			obj = api.getFocusObject()
			if obj.treeInterceptor is not None:
				obj.treeInterceptor.script_previousError(gesture)
			else:
				ui.message(_("Not supported here or browse mode not enabled"))
		else: return self.moveTo("previous", gesture)

	def script_nextSetRotor(self, gesture):
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.switchSelectionRange()
		elif rotorItems[rotorItem][0] == "object":
			self.sendComb('nvda+shift+downarrow', gesture)
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_nextLine, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+downarrow', gesture)
		else:
			return self.sendComb('downarrow', gesture)

	def script_priorSetRotor(self, gesture):
		if rotorItems[rotorItem][0] in ["moveInText", "textSelection"]:
			return self.switchSelectionRange(True)
		elif rotorItems[rotorItem][0] == "object":
			self.sendComb('nvda+shift+uparrow', gesture)
			return
		elif rotorItems[rotorItem][0] == "review":
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_previousLine, gesture)
		elif rotorItems[rotorItem][0] == "moveInTable":
			self.sendComb('control+alt+uparrow', gesture)
		else:
			return self.sendComb('uparrow', gesture)
	script_priorEltRotor.__doc__ = _("Move to previous item depending rotor setting")
	script_nextEltRotor.__doc__ = _("Move to next item depending rotor setting")

	def script_selectElt(self, gesture):
		if rotorItems[rotorItem][0] == "object":
			return self.sendComb('NVDA+enter', gesture)
		else:
			return self.sendComb('enter', gesture)
	script_selectElt.__doc__ = _(
		'Varies depending on rotor setting. Eg: in object mode, it\'s similar to NVDA+enter')

	script_priorSetRotor.__doc__ = _(
		'Move to previous item using rotor setting')
	script_nextSetRotor.__doc__ = _("Move to next item using rotor setting")

	def script_toggleLockBrailleKeyboard(self, gesture):
		self.brailleKeyboardLocked = not self.brailleKeyboardLocked
		ui.message(_("Braille keyboard %s") % (_("locked") if self.brailleKeyboardLocked else _("unlocked")))
	script_toggleLockBrailleKeyboard.__doc__ = _("Lock/unlock braille keyboard")

	def script_toggleDots78(self, gesture):
		self.hideDots78 = not self.hideDots78
		speech.speakMessage(_("Dots 7 and 8: %s") % (_("disabled") if self.hideDots78 else _("enabled")))
		utils.refreshBD()
	script_toggleDots78.__doc__ = _("Hide/show dots 7 and 8")

	def script_toggleBRFMode(self, gesture):
		self.BRFMode = not self.BRFMode
		utils.refreshBD()
		speech.speakMessage(_("BRF mode: %s") % (_("enabled") if self.BRFMode else _("disabled")))
	script_toggleBRFMode.__doc__ = _("Enable/disable BRF mode")

	def script_toggleLockModifiers(self, gesture):
		self.modifiersLocked = not self.modifiersLocked
		ui.message(_("Modifier keys %s") % (_("locked") if self.modifiersLocked else _("unlocked")))
	script_toggleLockModifiers.__doc__ = _("Lock/unlock modifiers keys")

	def script_toggleAttribra(self, gesture):
		config.conf["brailleExtender"]["features"]["attributes"] = not attribraEnabled()
		utils.refreshBD()
		speech.speakMessage('Attribra %s' % (_("enabled") if attribraEnabled() else _("disabled")))
	script_toggleAttribra.__doc__ = _("Enable/disable Attribra")

	def script_toggleSpeechScrollFocusMode(self, gesture):
		choices = configBE.focusOrReviewChoices
		curChoice = config.conf["brailleExtender"]["speakScroll"]
		curChoiceID = list(choices.keys()).index(curChoice)
		newChoiceID = (curChoiceID+1) % len(choices)
		newChoice = list(choices.keys())[newChoiceID]
		config.conf["brailleExtender"]["speakScroll"] = newChoice
		ui.message(list(choices.values())[newChoiceID].capitalize())
	script_toggleSpeechScrollFocusMode.__doc__ = _("Quick access to the \"say current line while scrolling in\" option")

	def script_toggleSpeech(self, gesture):
		if speech.speechMode == 0:
			speech.speechMode = 2
			ui.message(_("Speech on"))
		else:
			speech.speechMode = 0
			ui.message(_("Speech off"))
		return
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
	script_getTableOverview.__doc__ = _("Display an overview of current input braille table")

	def script_translateInBRU(self, gesture):
		tm = time.time()
		t = utils.getTextInBraille('', patchs.getCurrentBrailleTables())
		if not t.strip(): return ui.message(_("No text selection"))
		ui.browseableMessage("<pre>%s</pre>" % t, _("Unicode Braille conversion") + (" (%.2f s)" % (time.time()-tm)), True)
	script_translateInBRU.__doc__ = _("Convert the text selection in unicode braille and display it in a browseable message")

	def script_charsToCellDescriptions(self, gesture):
		tm = time.time()
		t = utils.getTextInBraille('', patchs.getCurrentBrailleTables())
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
		states = [_("disabled"), _("enabled")]
		speech.speakMessage(_("Advanced braille input mode %s") % states[int(self.advancedInput)])
	script_advancedInput.__doc__ = _("Enable/disable the advanced input mode")

	def script_undefinedCharsDesc(self, gesture):
		config.conf["brailleExtender"]["undefinedCharDesc"] = not config.conf["brailleExtender"]["undefinedCharDesc"]
		states = [_("disabled"), _("enabled")]
		speech.speakMessage(_("Description of undefined characters %s") % states[int(config.conf["brailleExtender"]["undefinedCharDesc"])])
		utils.refreshBD()
	script_undefinedCharsDesc.__doc__ = _("Enable/disable description of undefined characters")

	def script_position(self, gesture=None):
		return ui.message('{0}% ({1}/{2})'.format(round(utils.getPositionPercentage(), 2), utils.getPosition()[0], utils.getPosition()[1]))
	script_position.__doc__ = _("Get the cursor position of text")

	def script_hourDate(self, gesture=None):
		if self.autoScrollRunning:
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

	script_hourDate.__doc__ = _("Hour and date with autorefresh")

	@staticmethod
	def showHourDate():
		currentHourDate = time.strftime('%X %x (%a, %W/53, %b)', time.localtime())
		return braille.handler.message(currentHourDate)

	def script_autoScroll(self, gesture, sil=False):
		if self.hourDatePlayed:
			return
		if self.autoScrollRunning:
			self.autoScrollTimer.Stop()
			if not sil:
				speech.speakMessage(_("Autoscroll stopped"))
			config.conf["braille"]["showCursor"] = self.backupShowCursor
		else:
			self.autoScrollTimer = wx.PyTimer(self.autoScroll)
			try: self.autoScrollTimer.Start(int(config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD]))
			except BaseException as e:
				log.error("%s | %s" % (config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD], e))
				ui.message(_("Unable to start autoscroll. More info in NVDA log"))
				return
			self.backupShowCursor = config.conf["braille"]["showCursor"]
			config.conf["braille"]["showCursor"] = False
		self.autoScrollRunning = not self.autoScrollRunning
	script_autoScroll.__doc__ = _("Enable/disable autoscroll")

	def autoScroll(self):
		braille.handler.scrollForward()
		if utils.isLastLine():
			self.script_autoScroll(None)

	def script_volumePlus(s, g):
		keyboardHandler.KeyboardInputGesture.fromName('volumeup').send()
		s = '%3d%%%s' % (utils.getVolume(), utils.translatePercent(utils.getVolume(), braille.handler.displaySize - 4))
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_braille, configBE.CHOICE_speechAndBraille]:
			braille.handler.message(s)
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_speech, configBE.CHOICE_speechAndBraille]:
			speech.speakMessage(str(utils.getVolume()))
		return
	script_volumePlus.__doc__ = _("Increase the master volume")

	@staticmethod
	def clearMessageFlash():
		if config.conf["braille"]["messageTimeout"] != 0:
			if braille.handler.buffer is braille.handler.messageBuffer:
				braille.handler._dismissMessage()
				return

	def script_volumeMinus(s, g):
		keyboardHandler.KeyboardInputGesture.fromName('volumedown').send()
		s = '%3d%%%s' % (utils.getVolume(), utils.translatePercent(utils.getVolume(), braille.handler.displaySize - 4))
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_braille, configBE.CHOICE_speechAndBraille]:
			braille.handler.message(s)
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_speech, configBE.CHOICE_speechAndBraille]:
			speech.speakMessage(str(utils.getVolume()))
		return
	script_volumeMinus.__doc__ = _("Decrease the master volume")

	def script_toggleVolume(s, g):
		keyboardHandler.KeyboardInputGesture.fromName('volumemute').send()
		if config.conf["brailleExtender"]["volumeChangeFeedback"] == configBE.CHOICE_none: return
		if utils.getMute():
			return braille.handler.message(_("Muted sound"))
		else:
			s = _("Unmuted sound (%3d%%)") % utils.getVolume()
			if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_speech, configBE.CHOICE_speechAndBraille]:
				speech.speakMessage(s)
			if config.conf["brailleExtender"]["volumeChangeFeedback"] in [configBE.CHOICE_braille, configBE.CHOICE_speechAndBraille]:
				braille.handler.message(s)

	script_toggleVolume.__doc__ = _("Mute or unmute sound")

	def script_getHelp(self, g):
		from . import addonDoc
		addonDoc.AddonDoc(self)
	script_getHelp.__doc__ = _("Show the %s documentation") % addonName

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
	script_quickLaunch.__doc__ = _("Opens a custom program/file. Go to settings to define them")

	def script_checkUpdate(self, gesture):
		if not globalVars.appArgs.secure:
			checkUpdates()
		return

	script_checkUpdate.__doc__ = _("Check for %s updates, and starts the download if there is one") % addonName

	@staticmethod
	def increaseDelayAutoScroll():
		config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD] += 25

	@staticmethod
	def decreaseDelayAutoScroll():
		if config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD] - 25 >= 25:
			config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD] -= 25

	def script_increaseDelayAutoScroll(self, gesture):
		self.increaseDelayAutoScroll()
		if self.autoScrollRunning:
			self.script_autoScroll(None, True)
			self.script_autoScroll(None)
		else:
			ui.message('%s ms' %
					   config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD])
		return

	def script_decreaseDelayAutoScroll(self, gesture):
		self.decreaseDelayAutoScroll()
		if self.autoScrollRunning:
			self.script_autoScroll(None, True)
			self.script_autoScroll(None)
		else:
			ui.message('%s ms' % config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD])
		return

	script_increaseDelayAutoScroll.__doc__ = _("Increase autoscroll delay")
	script_decreaseDelayAutoScroll.__doc__ = _("Decrease autoscroll delay")

	def script_switchInputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
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

	script_switchInputBrailleTable.__doc__ = _(
		"Switch between his favorite input braille tables")

	def script_switchOutputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(
				_("Please use NVDA 2017.3 minimum for this feature"))
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

	script_switchOutputBrailleTable.__doc__ = _("Switch between his favorite output braille tables")

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

	script_currentBrailleTable.__doc__ = _(
		"Announce the current input and output braille tables")

	def script_brlDescChar(self, gesture):
		utils.currentCharDesc()
	script_brlDescChar.__doc__ = _(
		"Gives the Unicode value of the "
		"character where the cursor is located "
		"and the decimal, binary and octal equivalent.")

	def script_getSpeechOutput(self, gesture):
		out = utils.getSpeechSymbols()
		if scriptHandler.getLastScriptRepeatCount() == 0: braille.handler.message(out)
		else: ui.browseableMessage(out)
	script_getSpeechOutput.__doc__ = _("Show the output speech for selected text in braille. Useful for emojis for example") + HLP_browseModeInfo

	def script_repeatLastShortcut(self, gesture):
		if not self.lastShortcutPerformed:
			ui.message(_("No shortcut performed from a braille display"))
			return
		sht =  self.lastShortcutPerformed
		inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(sht))
	script_repeatLastShortcut.__doc__ = _("Repeat the last shortcut performed from a braille display")

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
		if not sil: ui.message(_("%s reloaded") % addonName)
		return

	@staticmethod
	def onUpdate(evt):
		return checkUpdates()

	@staticmethod
	def onWebsite(evt):
		return os.startfile(addonURL)

	def script_reloadAddon(self, gesture): self.onReload()
	script_reloadAddon.__doc__ = _("Reload %s") % addonName

	def script_reload_brailledisplay1(self, gesture): self.reload_brailledisplay(1)
	script_reload_brailledisplay1.__doc__ = _("Reload the first braille display defined in settings")

	def script_reload_brailledisplay2(self, gesture): self.reload_brailledisplay(2)
	script_reload_brailledisplay2.__doc__ = _("Reload the second braille display defined in settings")

	def reload_brailledisplay(self, n):
		k = "brailleDisplay%s" % (2 if n == 2 else 1)
		if config.conf["brailleExtender"][k] == "last":
			if config.conf["braille"]["display"] == "noBraille":
				return ui.message(_("No braille display specified. No reload to do"))
			else:
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

	@staticmethod
	def callScript(cls, f, gesture):
		for plugin in globalPluginHandler.runningPlugins:
			if plugin.__module__ == cls:
				func = getattr(plugin, f, None)
				if func:
					func(gesture)
					return True
				else:
					return false

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
			config.conf["brailleExtender"]["viewSaved"] = ''.join(chr((c | 0x2800)) for c in braille.handler.mainBuffer.brailleCells)
			ui.message(_("Current braille view saved"))
		else:
			config.conf["brailleExtender"]["viewSaved"] = configBE.NOVIEWSAVED
			ui.message(_("Buffer cleaned"))
	script_saveCurrentBrailleView.__doc__ = _("Save the current braille view. Press twice quickly to clean the buffer")

	def script_showBrailleViewSaved(self, gesture):
		if config.conf["brailleExtender"]["viewSaved"] != configBE.NOVIEWSAVED:
			if scriptHandler.getLastScriptRepeatCount() == 0: braille.handler.message("⣇ %s ⣸" % config.conf["brailleExtender"]["viewSaved"])
			else: ui.browseableMessage(config.conf["brailleExtender"]["viewSaved"], _("View saved"), True)
		else: ui.message(_("Buffer empty"))
	script_showBrailleViewSaved.__doc__ = _("Show the saved braille view through a flash message") + HLP_browseModeInfo

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
	script_addDictionaryEntry.__doc__ = _("Add a entry in braille dictionary")

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
		if self.autoScrollRunning:
			self.autoScrollTimer.Stop()
			config.conf["braille"]["showCursor"] = self.backupShowCursor
		if self.autoTestPlayed: self.autoTestTimer.Stop()
		dictionaries.removeTmpDict()
		advancedInputMode.terminate()
		super(GlobalPlugin, self).terminate()

	def removeMenu(self):
		gui.mainFrame.sysTrayIcon.menu.DestroyItem(self.submenu_item)

	@staticmethod
	def errorMessage(msg):
		wx.CallAfter(gui.messageBox, msg, _("Braille Extender"), wx.OK|wx.ICON_ERROR)

