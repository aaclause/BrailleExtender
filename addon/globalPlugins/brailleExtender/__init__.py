# coding: utf-8
# BrailleExtender Addon for NVDA
# This file is covered by the GNU General Public License.
# See the file LICENSE for more details.
# Copyright (C) 2017 André-Abush CLAUSE <dev@andreabc.net>
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
import time
import urllib
import gui
import wx

import addonHandler
addonHandler.initTranslation()
import addonSettingsPanel
import api
import appModuleHandler
import braille
import brailleInput
import brailleTables
import config
import controlTypes
import core
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
import ui
import versionInfo
import virtualBuffers

import configBE
config.conf.spec["brailleExtender"] = configBE.confspec
import utils
from updateCheck import *
import patchs

instanceGP = None
lang = configBE.lang
ATTRS = lambda: config.conf["brailleExtender"]["attributes"].copy()
logTextInfo = False
ROTOR_DEF = 0
ROTOR_MOVE = 1
ROTOR_SELECT = 2
ROTOR_OBJ = 3
ROTOR_REVIEW = 4
ROTOR_TABLES = 5
ROTOR_ERR = 6
ROTOR_RANGE = 1

rotorItems = [
	_('Default'),
	_('Moving in the text'),
	_('Text selection'),
	_('Objects'),
	_('Review'),
	_('Tables'),
	_('Spelling errors')
]
rotorItem = 0
nativeModifiers = True if hasattr(brailleInput.handler, "toggleModifier") else False
HLP_browseModeInfo = ". %s" % _("If pressed twice, presents the information in browse mode")

# ***** Attribra code *****
def attribraEnabled():
	return config.conf["brailleExtender"]["features"]["attributes"]

def decorator(fn, s):
	def _getTypeformFromFormatField(self, field):
		for attr in ATTRS():
			v = attr.split(':')
			k = v[0]
			v = True if len(v) == 1 else v[1]
			if k in field and (field[k] == v or field[k] == '1'):
				if ATTRS()[attr] == configBE.CHOICE_dot7: return 7
				if ATTRS()[attr] == configBE.CHOICE_dot8: return 8
				if ATTRS()[attr] == configBE.CHOICE_dots78: return 78
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
		if not config.conf["braille"]["translationTable"].endswith('.utb') and 'comp8' not in config.conf["braille"]["translationTable"] and config.conf["braille"]["translationTable"] not in ["ru-compbrl.ctb", "he.ctb"]: return
		DOT7 = 64
		DOT8 = 128
		for i, j in enumerate(self.rawTextTypeforms):
			if j == 78: self.brailleCells[i] |= DOT7 | DOT8
			if j == 7: self.brailleCells[i] |= DOT7
			if j == 8: self.brailleCells[i] |= DOT8

	if s == "addTextWithFields": return addTextWithFields_edit
	if s == "update": return update
	if s == "_getTypeformFromFormatField": return _getTypeformFromFormatField
# *************************


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = configBE._addonName
	brailleKeyboardLocked = False
	hideDots78 = False
	modifiersLocked = False
	hourDatePlayed = False
	hourDateTimer = None
	autoScrollRunning = False
	autoScrollTimer = None
	modifiers = set()
	_tGestures = OrderedDict()
	_pGestures = OrderedDict()
	rotorGES = {}
	noKC = None
	if not configBE.noUnicodeTable:
		backupInputTable = brailleInput.handler.table
	backupMessageTimeout = None
	backupShowCursor = False
	backupTether = braille.handler.tether
	switchedMode = False

	def __init__(self):
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		patchs.instanceGP = self
		addonSettingsPanel.instanceGP = self
		configBE.loadConf()
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		if not globalVars.appArgs.secure and config.conf["brailleExtender"]['autoCheckUpdate'] and time.time() - config.conf["brailleExtender"]['lastCheckUpdate'] > 86400:
			checkUpdates(True)
			config.conf["brailleExtender"]['lastCheckUpdate'] = time.time()
		self.backup__addTextWithFields = braille.TextInfoRegion._addTextWithFields
		self.backup__update = braille.TextInfoRegion.update
		self.backup__getTypeformFromFormatField = braille.TextInfoRegion._getTypeformFromFormatField
		braille.TextInfoRegion._addTextWithFields = decorator(braille.TextInfoRegion._addTextWithFields, "addTextWithFields")
		braille.TextInfoRegion.update = decorator(braille.TextInfoRegion.update, "update")
		braille.TextInfoRegion._getTypeformFromFormatField = decorator(braille.TextInfoRegion._getTypeformFromFormatField, "_getTypeformFromFormatField")
		if config.conf["brailleExtender"]["reverseScrollBtns"]:
			self.reverseScrollBtns()
		if hasattr(gui.settingsDialogs, "SettingsPanel"):
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.append(addonSettingsPanel.AddonSettingsPanel)
		self.createMenu()

	def event_gainFocus(self, obj, nextHandler):
		if self.hourDatePlayed: self.script_hourDate(None)
		if self.autoScrollRunning: self.script_autoScroll(None)
		if self.autoTestPlayed: self.script_autoTest(None)
		if braille.handler is not None and configBE.curBD != braille.handler.display.name:
			configBE.curBD = braille.handler.display.name
			self.onReload(None, 1)
		nextHandler()
		return

	def createMenu(self):
		self.NVDAMenu = gui.mainFrame.sysTrayIcon.preferencesMenu
		menu = wx.Menu()
		self.brailleExtenderMenu = self.NVDAMenu.AppendSubMenu(menu, '%s (%s)' % (configBE._addonName, configBE._addonVersion), _('%s menu' % configBE._addonName))

		item = menu.Append(wx.ID_ANY, _("Documentation"), _("Opens the addon's documentation."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDoc, item)
		#item = menu.Append(wx.ID_ANY, _("Settings..."), _("Opens the addon's settings."))
		#gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettings, item)
		item = menu.Append(wx.ID_ANY, _(u"Profiles &editor..."), _(u"Edit the current profile gestures or create a new one (modifier keys, etc.)."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onProfilesEditor, item)
		item = menu.Append(wx.ID_ANY, _("Overview of the current input braille table"), _("Overview of the current input braille table"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onGetTableOverview, item)
		item = menu.Append(wx.ID_ANY, _("Reload add-on"), _("Reload this add-on."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onReload, item)
		item = menu.Append(wx.ID_ANY, _("&Check for update..."), _("Checks if update is available"))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onUpdate, item)
		item = menu.Append(wx.ID_ANY, _("&Website"), _("Open addon's website."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onWebsite, item)

	def getGestureWithBrailleIdentifier(self, gesture = ''):
		return ('br(%s):' % configBE.curBD if ':' not in gesture else '')+gesture

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
			log.debug('No rotor gestures for this profile')

		# keyboard layout gestures
		gK = OrderedDict()
		try:
			cK = configBE.iniProfile['keyboardLayouts'][config.conf["brailleExtender"]['keyboardLayout_%s' % configBE.curBD]] if config.conf["brailleExtender"]['keyboardLayout_%s' % configBE.curBD] and config.conf["brailleExtender"]['keyboardLayout_%s' % configBE.curBD] in configBE.iniProfile['keyboardLayouts'] is not None else configBE.iniProfile['keyboardLayouts'].keys()[0]
			for k in cK:
				if k in ['enter', 'backspace']:
					if isinstance(cK[k], list):
						for l in cK[k]:
							gK[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(l))] = 'kb:%s' % k
					else:
						gK['kb:%s' % k] = inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(cK[k]))
				elif k in ['braille_dots', 'braille_enter', 'braille_translate']:
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
			log.debug('Keyboard conf found, loading layout `%s`' %config.conf["brailleExtender"]['keyboardLayout_' + configBE.curBD])
		except BaseException:
			log.debug('No keyboard conf found')
			self.noKC = True
		# Hack for NVDARemote
		if 'fr' in lang:
			nvdaremote_gestures = u"abcdefghijklmnopqrstuvwxyz0123456789²)=^$ù*<,;:!"
		else:
			nvdaremote_gestures = u"abcdefghijklmnopqrstuvwxyz0123456789`-=[];'\\,./"
		nvdaremote_gestures2 = ["escape","home","end","pageup","pagedown","backspace","leftarrow","rightarrow","uparrow","downarrow","enter","delete","space","ACCENT CIRCONFLEXE"]
		self._tGestures = {
			"bk:dots": "end_combKeysChar",
			"br(%s):routing" % configBE.curBD: "cancelShortcut",
			#: arrow keys
			"br(%s):up" % configBE.curBD: "end_combKeys",
			"br(%s):down" % configBE.curBD: "end_combKeys",
			"br(%s):left" % configBE.curBD: "end_combKeys",
			"br(%s):right" % configBE.curBD: "end_combKeys",
		}
		for k in nvdaremote_gestures:
			self._tGestures['kb:%s' % k] = "end_combKeysChar"
		for k in range(0, 13):
			self._tGestures['kb:f%s' % k] = "end_combKeysChar"
		for k in nvdaremote_gestures2:
			self._tGestures['kb:%s' % k] = "end_combKeysChar"
		if configBE.gesturesFileExists:
			for g in configBE.iniGestures['globalCommands.GlobalCommands']:
				if isinstance(configBE.iniGestures['globalCommands.GlobalCommands'][g], list):
					for h in range(len(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
						self._tGestures[inputCore.normalizeGestureIdentifier(configBE.iniGestures['globalCommands.GlobalCommands'][g][h])] = "end_combKeys"
				elif ('kb:' in g and g.lower() not in ['kb:alt', 'kb:control', 'kb:windows', 'kb:control', 'kb:applications']):
					self._tGestures[inputCore.normalizeGestureIdentifier(configBE.iniGestures['globalCommands.GlobalCommands'][g])] = "end_combKeys"
			self._pGestures = OrderedDict()
			for k, v in (configBE.iniProfile["modifierKeys"].items() + [k for k in configBE.iniProfile["miscs"].items() if k[0] != 'defaultQuickLaunches']):
				if isinstance(v, list):
					for i, gesture in enumerate(v):
						if k != 'shortcutsOn':
							self._pGestures[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(gesture))] = k
				else:
					self._pGestures[inputCore.normalizeGestureIdentifier(self.getGestureWithBrailleIdentifier(v))] = k
		self.bindGestures(self._pGestures)
		self.bindGestures({self.getGestureWithBrailleIdentifier(k): "quickLaunch" for k in configBE.quickLaunches.keys()})
		return

	def bindRotorGES(self):
		for k in self.rotorGES:
			try: self.removeGestureBinding(k)
			except BaseException: pass
		if rotorItem == ROTOR_DEF:
			return
		if rotorItem in [
				ROTOR_OBJ,
				ROTOR_REVIEW,
				ROTOR_SELECT,
				ROTOR_MOVE,
				ROTOR_TABLES]:
			self.bindGestures(self.rotorGES)
		else:
			for k in self.rotorGES:
				if self.rotorGES[k] not in [
						'selectElt', 'nextSetRotor', 'priorSetRotor']:
					self.bindGestures({k: self.rotorGES[k]})

	@staticmethod
	def showBrailleObj():
		s = []
		obj = api.getNavigatorObject()
		s.append(controlTypes.roleLabels[obj.role])
		if obj.name:
			s.append(obj.name)
		if obj.value:
			s.append(obj.value)
		if obj.roleText:
			s.append(obj.roleText)
		if obj.description:
			s.append(obj.description)
		if obj.keyboardShortcut:
			s.append('=> ' + api.getNavigatorObject().keyboardShortcut)
		if obj.location:
			s.append('[%s]' % (', '.join([str(k) for k in obj.location])))
		if s != []:
			braille.handler.message(' '.join(s))
		return

	def script_priorRotor(self, gesture):
		global rotorItem
		if rotorItem > 0:
			rotorItem -= 1
		else:
			rotorItem = len(rotorItems) - 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem])

	def script_nextRotor(self, gesture):
		global rotorItem
		rotorItem = 0 if rotorItem >= len(rotorItems) - 1 else rotorItem + 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem])

	@staticmethod
	def getCurrentSelectionRange(pretty=True, back=False):
		if pretty:
			labels = [
				_('Character'),
				_('Word'),
				_('Line'),
				_('Paragraph'),
				_('Page'),
				_('Document')]
			return labels[ROTOR_RANGE]
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
			if rotorItem == ROTOR_SELECT:
				return 'shift+%s' % (keys[ROTOR_RANGE]
									 [0] if back else keys[ROTOR_RANGE][1])
			else:
				return keys[ROTOR_RANGE][0] if back else keys[ROTOR_RANGE][1]

	def switchSelectionRange(self, previous=False):
		global ROTOR_RANGE
		if previous: ROTOR_RANGE = ROTOR_RANGE - 1 if ROTOR_RANGE > 0 else 5
		else: ROTOR_RANGE = ROTOR_RANGE + 1 if ROTOR_RANGE < 5 else 0
		ui.message(self.getCurrentSelectionRange())
		return

	def script_nextEltRotor(self, gesture):
		if rotorItem == ROTOR_DEF: return self.sendComb('rightarrow', gesture)
		elif rotorItem in [ROTOR_MOVE, ROTOR_SELECT]:
			return self.sendComb(self.getCurrentSelectionRange(False), gesture)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+rightarrow', gesture)
			# self.showBrailleObj()
		elif rotorItem == ROTOR_REVIEW:
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_scrollForward, gesture)
		elif rotorItem == ROTOR_TABLES:
			self.sendComb('control+alt+rightarrow', gesture)
		elif rotorItem == ROTOR_ERR:
			obj = api.getFocusObject()
			if obj.treeInterceptor is not None:
				obj.treeInterceptor.script_nextError(gesture)
			else:
				ui.message(_('Not supported here or browse mode not enabled'))
		else:
			return ui.message(_('Not implemented yet'))
	script_priorRotor.__doc__ = _('Select previous rotor setting')
	script_nextRotor.__doc__ = _('Select next rotor setting')

	def script_priorEltRotor(self, gesture):
		if rotorItem == ROTOR_DEF:
			return self.sendComb('leftarrow', gesture)
		elif rotorItem in [ROTOR_MOVE, ROTOR_SELECT]:
			return self.sendComb(
				self.getCurrentSelectionRange(
					False, True), gesture)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+leftarrow', gesture)
			# self.showBrailleObj()
		elif rotorItem == ROTOR_REVIEW:
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_scrollBack, gesture)
		elif rotorItem == ROTOR_TABLES:
			self.sendComb('control+alt+leftarrow', gesture)
		elif rotorItem == ROTOR_ERR:
			obj = api.getFocusObject()
			if obj.treeInterceptor is not None:
				obj.treeInterceptor.script_previousError(gesture)
			else:
				ui.message(_('Not supported here or browse mode not enabled'))
		else:
			return ui.message('Not implemented yet')

	def script_nextSetRotor(self, gesture):
		if rotorItem in [ROTOR_MOVE, ROTOR_SELECT]:
			return self.switchSelectionRange()
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+downarrow', gesture)
			# self.showBrailleObj()
		elif rotorItem == ROTOR_REVIEW:
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_nextLine, gesture)
		elif rotorItem == ROTOR_TABLES:
			self.sendComb('control+alt+downarrow', gesture)
		else:
			return self.sendComb('downarrow', gesture)

	def script_priorSetRotor(self, gesture):
		if rotorItem in [ROTOR_MOVE, ROTOR_SELECT]:
			return self.switchSelectionRange(True)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+uparrow', gesture)
			# self.showBrailleObj()
			return
		elif rotorItem == ROTOR_REVIEW:
			scriptHandler.executeScript(
				globalCommands.commands.script_braille_previousLine, gesture)
		elif rotorItem == ROTOR_TABLES:
			self.sendComb('control+alt+uparrow', gesture)
		else:
			return self.sendComb('uparrow', gesture)
	script_priorEltRotor.__doc__ = _(
		'Move to previous item depending rotor setting')
	script_nextEltRotor.__doc__ = _(
		'Move to next item depending rotor setting')

	def script_selectElt(self, gesture):
		if rotorItem == ROTOR_OBJ:
			return self.sendComb('NVDA+enter', gesture)
		else:
			return self.sendComb('enter', gesture)
	script_selectElt.__doc__ = _(
		'Varies depending on rotor setting. Eg: in object mode, it\'s similar to NVDA+enter')

	script_priorSetRotor.__doc__ = _(
		'Move to previous item using rotor setting')
	script_nextSetRotor.__doc__ = _('Move to next item using rotor setting')

	def script_toggleLockBrailleKeyboard(self, gesture):
		self.brailleKeyboardLocked = not self.brailleKeyboardLocked
		ui.message(_('Braille keyboard %s') % (_('locked') if self.brailleKeyboardLocked else _('unlocked')))
	script_toggleLockBrailleKeyboard.__doc__ = _('Lock/unlock braille keyboard')

	def script_toggleDots78(self, gesture):
		self.hideDots78 = not self.hideDots78
		speech.speakMessage(_('Dots 7 and 8: %s') % (_('disabled') if self.hideDots78 else _('enabled')))
		self.refreshBD()
	script_toggleDots78.__doc__ = _('Hide/show dots 7 and 8')

	def script_toggleLockModifiers(self, gesture):
		self.modifiersLocked = not self.modifiersLocked
		ui.message(_('Modifier keys %s') % (_('locked') if self.modifiersLocked else _('unlocked')))
	script_toggleLockModifiers.__doc__ = _('Lock/unlock modifiers keys')

	def script_toggleAttribra(self, gesture):
		config.conf["brailleExtender"]["features"]["attributes"] = not attribraEnabled()
		self.refreshBD()
		speech.speakMessage('Attribra %s' % (_('enabled') if attribraEnabled() else _('disabled')))
	script_toggleAttribra.__doc__ = _('Enable/disable Attribra')

	def script_toggleSpeechScrollFocusMode(self, gesture):
		config.conf["brailleExtender"]['speakScrollFocusMode'] = not config.conf["brailleExtender"]['speakScrollFocusMode']
		ui.message(_('Speech %s while scrolling') % (_('enabled') if config.conf["brailleExtender"]['speakScrollFocusMode'] else _('disabled')))
	script_toggleSpeechScrollFocusMode.__doc__ = _('Enable/disable speech while scrolling in focus mode')

	def script_toggleSpeech(self, gesture):
		if speech.speechMode == 0:
			speech.speechMode = 2
			ui.message(_('Speech on'))
		else:
			speech.speechMode = 0
			ui.message(_('Speech off'))
		return
	script_toggleSpeech.__doc__ = _('Toggle speech on or off')

	def script_reportExtraInfos(self, gesture):
		obj = api.getNavigatorObject()
		msg = []
		if obj.name: msg.append(obj.name)
		if obj.description: msg.append(obj.description)
		if obj.value: msg.append(obj.value)
		if len(msg) == 0: return ui.message(_("No extra info for this element"))
		if scriptHandler.getLastScriptRepeatCount() == 0: ui.message((configBE.sep+': ').join(msg))
		else: ui.browseableMessage(('\n').join(msg))
	# Translators: Input help mode message for report extra infos command.
	script_reportExtraInfos.__doc__ = _("Reports some extra infos for the current element. For example, the URL on a link")+HLP_browseModeInfo

	def script_getTableOverview(self, gesture):
		inTable = brailleInput.handler.table.displayName
		ouTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		grade = [_('uncontracted'), _('contracted')]
		t = (_(' Input table')+': %s\n'+_('Output table')+': %s\n\n') % (inTable+' (%s)' % (brailleInput.handler.table.fileName), ouTable+' (%s)' % (config.conf["braille"]["translationTable"]))
		t += utils.getTableOverview()
		ui.browseableMessage('<pre>%s</pre>' % t, _('Table overview (%s)' % brailleInput.handler.table.displayName), True)
	script_getTableOverview.__doc__ = _('Display an overview of current input braille table')

	def script_translateInBRU(self, gesture):
		t = utils.getTextInBraille()
		if t.strip() == "": return ui.message(_('No text selection'))
		ui.browseableMessage('<pre>%s</pre>' % t, _('BFU conversion'), True)
	script_translateInBRU.__doc__ = _('Convert the text selection in unicode braille and display it in a browseable message')

	def script_translateInCellDescription(self, gesture):
		t = utils.getTextInBraille()
		t = utils.unicodeBrailleToDescription(t)
		if t.strip() == "": return ui.message(_('No text selection'))
		ui.browseableMessage(t)
	script_translateInCellDescription.__doc__ = _('Convert text selection in braille cell descriptions and display it in a browseable message')

	def script_position(self, gesture=None):
		return ui.message('{0}% ({1}/{2})'.format(round(utils.getPositionPercentage(), 2), utils.getPosition()[0], utils.getPosition()[1]))
	script_position.__doc__ = _('Get the cursor position of text')

	def script_hourDate(self, gesture=None):
		if self.autoScrollRunning:
			return
		if self.hourDatePlayed:
			self.hourDateTimer.Stop()
			self.clearMessageFlash()
			if configBE.noMessageTimeout:
				config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
		else:
			if config.conf["brailleExtender"]['hourDynamic']:
				if configBE.noMessageTimeout:
					self.backupMessageTimeout = config.conf["braille"]["noMessageTimeout"]
					config.conf["braille"]["noMessageTimeout"] = True
			self.showHourDate()
			if config.conf["brailleExtender"]['hourDynamic']:
				self.hourDateTimer = wx.PyTimer(self.showHourDate)
				time.sleep(1.02 - round(time.time() - int(time.time()), 3))
				self.showHourDate()
				self.hourDateTimer.Start(1000)
			else:
				return
		self.hourDatePlayed = not self.hourDatePlayed
		return

	script_hourDate.__doc__ = _('Hour and date with autorefresh')

	@staticmethod
	def showHourDate():
		currentHourDate = time.strftime('%X %x (%a, %W/53, %b)', time.localtime())
		return braille.handler.message(currentHourDate.decode('mbcs'))

	def script_autoScroll(self, gesture, sil=False):
		if self.hourDatePlayed:
			return
		if self.autoScrollRunning:
			self.autoScrollTimer.Stop()
			if not sil:
				speech.speakMessage(_('Autoscroll stopped'))
			config.conf["braille"]["showCursor"] = self.backupShowCursor
		else:
			self.backupShowCursor = config.conf["braille"]["showCursor"]
			config.conf["braille"]["showCursor"] = False
			self.autoScrollTimer = wx.PyTimer(self.autoScroll)
			self.autoScrollTimer.Start(
				config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD])
		self.autoScrollRunning = not self.autoScrollRunning
		return
	script_autoScroll.__doc__ = _('Enable/disable autoscroll')

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
	script_volumePlus.__doc__ = _('Increase the master volume')

	@staticmethod
	def refreshBD():
		obj = api.getFocusObject()
		if obj.treeInterceptor is not None:
			ti = treeInterceptorHandler.update(obj)
			if not ti.passThrough:
				braille.handler.handleGainFocus(ti)
		else:
			braille.handler.handleGainFocus(api.getFocusObject())

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
	script_volumeMinus.__doc__ = _('Decrease the master volume')

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

	script_toggleVolume.__doc__ = _('Mute or unmute sound')

	def script_getHelp(s, g):
		import addonDoc
		addonDoc.AddonDoc(s)
	script_getHelp.__doc__ = _(
		'Show the %s documentation') % configBE._addonName

	def noKeyboarLayout(self):
		return self.noKC

	def getKeyboardLayouts(self):
		if not self.noKC and 'keyboardLayouts' in configBE.iniProfile:
			for layout in configBE.iniProfile['keyboardLayouts']:
				t = []
				for lk in configBE.iniProfile['keyboardLayouts'][layout]:
					if lk in ['braille_dots', 'braille_enter', 'braille_translate']:
						scriptName = 'script_%s' % lk
						func = getattr(globalCommands.GlobalCommands, scriptName, None)
						if isinstance(configBE.iniProfile['keyboardLayouts'][layout][lk], list):
							t.append(utils.beautifulSht(configBE.iniProfile['keyboardLayouts'][layout][lk]) + configBE.sep + ': ' + func.__doc__)
						else:
							t.append(utils.beautifulSht(configBE.iniProfile['keyboardLayouts'][layout][lk]) + configBE.sep + ': ' + func.__doc__)
					else:
						if isinstance(
								configBE.iniProfile['keyboardLayouts'][layout][lk], list):
							t.append(utils.beautifulSht(configBE.iniProfile['keyboardLayouts'][layout][lk]) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
						else:
							t.append(utils.beautifulSht(configBE.iniProfile['keyboardLayouts'][layout][lk]) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
				yield ((configBE.sep + '; ').join(t))

	def getGestures(s):
		return s.__gestures

	def script_quickLaunch(self, gesture):
		if gesture.id not in configBE.quickLaunches.keys():
			gesture.id = gesture.normalizedIdentifiers[0].split(':')[1]
			if gesture.id not in configBE.quickLaunches.keys():
				log.info(configBE.quickLaunches)
				ui.message('Target for %s not defined.' % gesture.id)
				return
		try:
			return subprocess.Popen(configBE.quickLaunches[gesture.id])
		except BaseException:
			try:
				os.startfile(configBE.quickLaunches[gesture.id])
			except BaseException:
				ui.message(_("No such file or directory"))
			return
	script_quickLaunch.__doc__ = _('Opens a custom program/file. Go to settings to define them')

	def script_checkUpdate(self, gesture):
		if not globalVars.appArgs.secure:
			checkUpdates()
		return

	script_checkUpdate.__doc__ = _(
		'Check for %s updates, and starts the download if there is one') % configBE._addonName

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

	script_increaseDelayAutoScroll.__doc__ = _('Increase autoscroll delay')
	script_decreaseDelayAutoScroll.__doc__ = _('Decrease autoscroll delay')

	def script_switchInputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.inputTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["inputTable"] in configBE.inputTables:
			configBE.inputTables.append(config.conf["braille"]["inputTable"])
		tid = configBE.inputTables.index(config.conf["braille"]["inputTable"])
		nID = tid + 1 if tid + 1 < len(configBE.inputTables) else 0
		brailleInput.handler.table = brailleTables.listTables(
		)[configBE.tablesFN.index(configBE.inputTables[nID])]
		ui.message(_('Input: %s') % brailleInput.handler.table.displayName)
		return

	script_switchInputBrailleTable.__doc__ = _(
		"Switch between his favorite input braille tables")

	def script_switchOutputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(
				_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.outputTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["translationTable"] in configBE.outputTables:
			configBE.outputTables.append(config.conf["braille"]["translationTable"])
		tid = configBE.outputTables.index(
			config.conf["braille"]["translationTable"])
		nID = tid + 1 if tid + 1 < len(configBE.outputTables) else 0
		config.conf["braille"]["translationTable"] = configBE.outputTables[nID]
		self.refreshBD()
		ui.message(_('Output: %s') % configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])])
		return

	script_switchOutputBrailleTable.__doc__ = _("Switch between his favorite output braille tables")

	def script_currentBrailleTable(self, gesture):
		inTable = brailleInput.handler.table.displayName
		ouTable = configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])]
		if ouTable == inTable:
			braille.handler.message(_('I⣿O:{I}').format(I=inTable, O=ouTable))
			speech.speakMessage(_('Input and output: {I}.').format(I=inTable, O=ouTable))
		else:
			braille.handler.message(_('I:{I} ⣿ O: {O}').format(I=inTable, O=ouTable))
			speech.speakMessage(_('Input: {I}; Output: {O}').format(I=inTable, O=ouTable))
		return

	script_currentBrailleTable.__doc__ = _(
		"Announce the current input and output braille tables")

	def script_brlDescChar(self, gesture):
		utils.currentCharDesc()
	script_brlDescChar.__doc__ = _(
		"Gives the Unicode value of the "
		"character where the cursor is located "
		"and the decimal, binary and octal equivalent.")

	def onDoc(self, evt):
		return self.script_getHelp(None)

	def onReload(self, evt=None, sil=False, sv=False):
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		self._pGestures=OrderedDict()
		configBE.quickLaunches = OrderedDict()
		configBE.loadConf()
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		if config.conf["brailleExtender"]["reverseScrollBtns"]:
			self.reverseScrollBtns()
		if not sil:
			ui.message(_('%s reloaded') % configBE._addonName)
		return

	@staticmethod
	def onUpdate(evt):
		return checkUpdates()

	def onGetTableOverview(self, evt):
		self.script_getTableOverview(None)

	@staticmethod
	def onWebsite(evt):
		return os.startfile(configBE._addonURL)

	def script_reloadAddon(self, gesture): self.onReload()
	script_reloadAddon.__doc__ = _('Reload %s') % configBE._addonName

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
		elif config.conf["braille"]["display"] != "auto":
			utils.reload_brailledisplay(config.conf["brailleExtender"][k])
			configBE.curBD = config.conf["brailleExtender"][k]
		else:
			speech.speakMessage(_("Profile reloaded"))
			configBE.curBD = braille.handler.display.name
		self.refreshBD()
		return self.onReload(None, True)


	def clearModifiers(self, forced = False):
		if self.modifiersLocked and not forced: return
		self.modifiers.clear()
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		self.bindGestures(self._pGestures)
		self.gesturesInit()

	@staticmethod
	def sendCombKeys(sendKS, send=True):
		if send:
			log.debug("Sending " + sendKS)
			if not sendKS == "":
				inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(sendKS))
		return

	def script_end_combKeys(self, gesture):
		_tmpGesture = {
			'up': 'uparrow',
			'down': 'downarrow',
			'left': 'leftarrow',
			'right': 'rightarrow',
		}
		for g in configBE.iniGestures['globalCommands.GlobalCommands']:
			if isinstance(
					configBE.iniGestures['globalCommands.GlobalCommands'][g],
					list):
				for h in range(
						len(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
					_tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g][h])).replace(
						'br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
			elif ('kb:' in g and g not in ['kb:alt', 'kb:ctrl', 'kb:windows', 'kb:control', 'kb:applications'] and 'br(' + configBE.curBD + '):' in str(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
				_tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g])).replace('br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
			gId = inputCore.normalizeGestureIdentifier(
				'br(' + configBE.curBD + '):' + str(gesture.id)).replace('br(' + configBE.curBD + '):', '')
		sht = self.getActualModifiers(False) + _tmpGesture[gId]
		if gId not in _tmpGesture:
			return ui.message("Unknown " + gId)
		self.clearModifiers()
		self.clearMessageFlash()
		return self.sendComb(sht, gesture)

	def script_end_combKeysChar(self, gesture):
		self.clearMessageFlash()
		if not hasattr(gesture, 'id'):
			ch = gesture.normalizedIdentifiers[0].split(':')[1]
			self.sendComb(self.getActualModifiers(False) + ch, gesture)
		else:
			if config.conf["brailleExtender"]['inputTableShortcuts'] != '?':
				self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots, config.conf["brailleExtender"]['inputTableShortcuts']), gesture)
			else:
				self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots), gesture)
		self.clearModifiers()

	def sendComb(self, sht, gesture):
		if ((config.conf["brailleExtender"]['inputTableShortcuts'] != '?' and configBE.isContractedTable(config.conf["brailleExtender"]['inputTableShortcuts']))
			or (config.conf["brailleExtender"]['inputTableShortcuts'] == '?' and configBE.isContractedTable(brailleInput.handler.table.fileName))
		):
			ui.message(_('You should specify a braille table for shortcuts when you work with a contracted input. Please go in the settings'))
			return
		NVDASht = self.sendCombKeysNVDA(sht, gesture)
		if not NVDASht and 'nvda' not in sht.lower():
			try:
				return self.sendCombKeys(sht, gesture)
			except BaseException as e:
					log.error(e)
					return ui.message(_('Unable to send %s') % sht)
		elif not NVDASht:  # and 'nvda' in sht.lower()
			return ui.message(_('%s is not part of a NVDA commands') % sht)

	def sendCombKeysNVDA(self, sht, gesture):
		if nativeModifiers:
			inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(sht))
			return True
		focus = api.getFocusObject()
		obj = api.getNavigatorObject()
		sht = '+'.join(sorted(sht.split('+')))
		shts = ['kb:%s' % sht, 'kb(%s):%s' % (config.conf["keyboard"]["keyboardLayout"], sht)]
		# Global gplugin level
		for p in globalPluginHandler.runningPlugins:
			for g in p._gestureMap:
				if inputCore.normalizeGestureIdentifier(g).lower() in shts:
					scriptName = p._gestureMap[g].__func__.func_name
					func = getattr(p, scriptName, None)
					if func:
						func(gesture)
						return True

		# App module level.
		for g in focus.appModule._gestureMap:
			if inputCore.normalizeGestureIdentifier(g).lower() in shts:
				scriptName = p._gestureMap[g].__func__.func_name
				func = getattr(p, scriptName, None)
				if func:
					func(gesture)
					return True

		# Tree interceptor level.
		if focus.treeInterceptor is not None and focus.treeInterceptor.isReady and not focus.treeInterceptor.passThrough:
			treeInterceptor = focus.treeInterceptor
			for k in treeInterceptor._gestureMap:
				if k.lower() in shts:
					scriptName = treeInterceptor._gestureMap[k].__func__.func_name
					func = getattr(treeInterceptor, scriptName, None)
					if func:
						func(gesture)
						return True

		# NVDAObject level
		for g in obj._gestureMap:
			if inputCore.normalizeGestureIdentifier(g).lower() in shts:
				scriptName = obj._gestureMap[g].__func__.func_name
				func = getattr(obj, scriptName, None)
				if func:
					try:
						func(gesture)
						return True
					except BaseException:
						CursorManager = cursorManager.CursorManager()
						CursorManager.makeTextInfo = obj.makeTextInfo
						for g in CursorManager._CursorManager__gestures:
							if inputCore.normalizeGestureIdentifier(g).lower() in shts:
								scriptName = 'script_%s' % CursorManager._CursorManager__gestures[g]
								func = getattr(CursorManager, scriptName, None)
								if func:
									func(gesture)
									return True

		# Global Commands level.
		for g in globalCommands.commands._gestureMap:
			if inputCore.normalizeGestureIdentifier(g).lower() in shts:
				scriptName = globalCommands.commands._gestureMap[g].__func__.func_name
				func = getattr(globalCommands.commands, scriptName, None)
				if func:
					func(gesture)
					return True
		return False

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

	def initCombKeys(self):
		if len(self.modifiers) == 1: self.bindGestures(self._tGestures)
	def getActualModifiers(self, short=True):
		if len(self.modifiers) == 0:
			return self.script_cancelShortcut(None)
		s = ""
		t = {
			'windows': _('WIN'),
			'control': _('CTRL'),
			'shift': _('SHIFT'),
			'alt': _('ALT'),
			'nvda': 'NVDA'}
		for k in self.modifiers:
			s += t[k] + '+' if short else k + '+'
		if not short:
			return s
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in [configBE.CHOICE_braille, configBE.CHOICE_speechAndBraille]:
			braille.handler.message('%s...' % s)
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in [configBE.CHOICE_speech, configBE.CHOICE_speechAndBraille]:
			speech.speakMessage(keyLabels.getKeyCombinationLabel('+'.join([m for m in self.modifiers])))

	def toggleModifier(self, modifier):
		if modifier.lower() not in ["alt","control","nvda","shift","windows"]:
			return
		if modifier not in self.modifiers: self.modifiers.add(modifier)
		else: self.modifiers.discard(modifier)
		if len(self.modifiers) == 0: self.clearModifiers(True)

	def script_ctrl(self, gesture=None, sil=True):
		self.toggleModifier("control")
		if sil: self.getActualModifiers()
		return self.initCombKeys()

	def script_nvda(self, gesture=None):
		self.toggleModifier("nvda")
		self.getActualModifiers()
		return self.initCombKeys()

	def script_alt(self, gesture=None, sil=True):
		self.toggleModifier("alt")
		if sil: self.getActualModifiers()
		return self.initCombKeys()

	def script_win(self, gesture=None, sil=True):
		self.toggleModifier("windows")
		if sil: self.getActualModifiers()
		return self.initCombKeys()

	def script_shift(self, gesture=None, sil=True):
		self.toggleModifier("shift")
		if sil: self.getActualModifiers()
		return self.initCombKeys()

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
		ui.message(_("Keyboard shortcut cancelled"))
		return
	script_nvda.bypassInputHelp = True
	script_alt.bypassInputHelp = True
	script_ctrl.bypassInputHelp = True
	script_cancelShortcut.bypassInputHelp = True
	script_end_combKeys.bypassInputHelp = True
	script_end_combKeysChar.bypassInputHelp = True

	# /* docstrings for modifier keys */
	def docModKeys(k): return _('Emulate pressing down ') + '+'.join(
		[utils.getKeysTranslation(l) for l in k.split('+')]) + _(' on the system keyboard')
	script_ctrl.__doc__ = docModKeys('control')
	script_alt.__doc__ = docModKeys('ALT')
	script_win.__doc__ = docModKeys('windows')
	script_shift.__doc__ = docModKeys('SHIFT')
	script_nvda.__doc__ = docModKeys('NVDA')
	script_altShift.__doc__ = docModKeys('ALT+SHIFT')
	script_ctrlShift.__doc__ = docModKeys('control+SHIFT')
	script_ctrlAlt.__doc__ = docModKeys('control+ALT')
	script_ctrlAltShift.__doc__ = docModKeys('control+ALT+SHIFT')
	script_ctrlWin.__doc__ = docModKeys('control+windows')
	script_altWin.__doc__ = docModKeys('ALT+windows')
	script_winShift.__doc__ = docModKeys('Windows+Shift')
	script_altWinShift.__doc__ = docModKeys('ALT+Windows+Shift')
	script_ctrlWinShift.__doc__ = docModKeys('control+Windows+SHIFT')
	script_ctrlAltWin.__doc__ = docModKeys('control+ALT+Windows')
	script_ctrlAltWinShift.__doc__ = docModKeys('control+ALT+Windows+SHIFT')

	def script_braille_scrollBack(self, gesture):
		braille.handler.scrollBack()
	script_braille_scrollBack.bypassInputHelp = True

	def script_braille_scrollForward(self, gesture):
		braille.handler.scrollForward()
	script_braille_scrollForward.bypassInputHelp = True

	def reverseScrollBtns(self, gesture=None, cancel=False):
		if cancel:
			scbtns = [inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollForward'] + \
				[inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollBack']
		else:
			scbtns = [inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollBack'] + \
				[inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollForward']
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

	@staticmethod
	def inProcess():
		ui.browseableMessage('Feature in process.')

	def onProfilesEditor(self, evt):
		import profilesEditor
		gui.mainFrame._popupSettingsDialog(profilesEditor.ProfilesEditor)

	def script_logFieldsAtCursor(self, gesture):
		global logTextInfo
		logTextInfo = not logTextInfo
		msg = ["stop", "start"]
		ui.message("debug textInfo " + msg[logTextInfo])

	def script_saveCurrentBrailleView(self, gesture):
		if scriptHandler.getLastScriptRepeatCount() == 0:
			config.conf["brailleExtender"]['viewSaved'] = braille.handler.mainBuffer.rawText
			ui.message(_('Current braille view saved'))
		else:
			config.conf["brailleExtender"]['viewSaved'] = None
			ui.message(_('Saved view cleaned'))
	script_saveCurrentBrailleView.__doc__ = _('Save the current braille view. Press twice quickly to clean the buffer')

	def script_showBrailleViewSaved(self, gesture):
		if config.conf["brailleExtender"]['viewSaved']:
			if scriptHandler.getLastScriptRepeatCount() == 0: braille.handler.message("⣇ %s ⣸" % config.conf["brailleExtender"]['viewSaved'])
			else: ui.browseableMessage("<pre>%s\n=======\n%s" % (utils.getTextInBraille(config.conf["brailleExtender"]['viewSaved']), config.conf["brailleExtender"]['viewSaved']), _('View saved'), True)
		else: ui.message(_('No saved view'))
	script_showBrailleViewSaved.__doc__ = _('Show the saved braille view through a flash message.')+HLP_browseModeInfo

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
			braille.handler.message('%s' % (self.autoTest_tests[self.autoTest_type][self.autoTest_charPtr]*braille.handler.displaySize))
		else:
			braille.handler.message('%s%s' % (' '*self.autoTest_cellPtr, self.autoTest_tests[self.autoTest_type][self.autoTest_charPtr]))
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
		speech.speakMessage('%d ms' % self.autoTestInterval)

	def script_autoTestIncrease(self, gesture):
		if self.autoTestInterval-125 < 125: return
		self.autoTestInterval -= 125
		self.autoTestTimer.Stop()
		self.autoTestTimer.Start(self.autoTestInterval)
		speech.speakMessage('%d ms' % self.autoTestInterval)

	def script_autoTestPrior(self, gesture):
		if self.autoTest_type > 0: self.autoTest_type -= 1
		else: self.autoTest_type = len(self.autoTest_tests)-1
		self.autoTest_charPtr = self.autoTest_cellPtr = 0
		self.showAutoTest()
		speech.speakMessage(_('Auto test type %d' % self.autoTest_type))

	def script_autoTestNext(self, gesture):
		if self.autoTest_type+1 < len(self.autoTest_tests): self.autoTest_type += 1
		else: self.autoTest_type = 0
		self.autoTest_charPtr = self.autoTest_cellPtr = 0
		self.showAutoTest()
		speech.speakMessage(_('Auto test type %d' % self.autoTest_type))

	def script_autoTest(self, gesture):
		if self.autoTestPlayed:
			self.autoTestTimer.Stop()
			for k in self.autoTest_gestures:
				try: self.removeGestureBinding(k)
				except BaseException: pass
			self.autoTest_charPtr = self.autoTest_cellPtr = 0
			self.clearMessageFlash()
			speech.speakMessage(_('Auto test stopped'))
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
	script_autoTest.__doc__ = _('Auto test')
	# end of section autoTest

	__gestures = OrderedDict()
	__gestures["kb:NVDA+control+shift+a"] = "logFieldsAtCursor"
	__gestures["kb:shift+NVDA+p"] = "currentBrailleTable"
	__gestures["kb:shift+NVDA+i"] = "switchInputBrailleTable"
	__gestures["kb:shift+NVDA+u"] = "switchOutputBrailleTable"
	__gestures["kb:shift+NVDA+y"] = "autoScroll"
	__gestures["kb:nvda+k"] = "reload_brailledisplay1"
	__gestures["kb:nvda+shift+k"] = "reload_brailledisplay2"
	__gestures["kb:nvda+windows+k"] = "reloadAddon"
	__gestures["kb:volumeMute"] = "toggleVolume"
	__gestures["kb:volumeUp"] = "volumePlus"
	__gestures["kb:volumeDown"] = "volumeMinus"
	__gestures["kb:nvda+alt+u"] = "translateInBRU"
	__gestures["kb:nvda+alt+i"] = "translateInCellDescription"
	__gestures["kb:nvda+alt+y"] = "getTableOverview"
	__gestures["kb:nvda+shift+j"] = "toggleAttribra"

	def terminate(self):
		if hasattr(gui.settingsDialogs, "SettingsPanel"):
			gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(addonSettingsPanel.AddonSettingsPanel)
		braille.TextInfoRegion._addTextWithFields = self.backup__addTextWithFields
		braille.TextInfoRegion.update = self.backup__update
		braille.TextInfoRegion._getTypeformFromFormatField = self.backup__getTypeformFromFormatField
		self.removeMenu()
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
		super(GlobalPlugin, self).terminate()

	def removeMenu(self):
		if hasattr(self, "brailleExtenderMenu"): self.NVDAMenu.RemoveItem(self.brailleExtenderMenu)
