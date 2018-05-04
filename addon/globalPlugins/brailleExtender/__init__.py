# coding: utf-8
# BrailleExtender Addon for NVDA
# This file is covered by the GNU General Public License.
# See the file LICENSE for more details.
# Copyright (C) 2017 André-Abush CLAUSE <dev@andreabc.net>
#
# Additional third party copyrighted code is included:
#	- *Attribra*: Copyright (C) 2017 Alberto Zanella <lapostadialberto@gmail.com>
#	-> https://github.com/albzan/attribra/
from __future__ import unicode_literals
import os
import re
import urllib
from collections import OrderedDict
import wx
import gui
import subprocess

import addonHandler
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
import time
import virtualBuffers
import ui
import configBE
import settings
import patchs
import utils
import versionInfo
from configobj import ConfigObj
from logHandler import log

addonHandler.initTranslation()
instanceGP = None
instanceUP = None
lang = configBE.lang
ATTRS = {}
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


def paramsDL(): return {
	"versionProtocole": "1.4",
	"versionAddon": configBE._addonVersion,
	"versionNVDA": versionInfo.version,
	"language": languageHandler.getLanguage(),
	"installed": config.isInstalledCopy(),
	"brailledisplay": braille.handler.display.name,
	"channel": configBE.conf['general']['channelUpdate']
}

def checkUpdates(sil = False):

	def availableUpdateDialog(version = '', msg = ''):
		res = gui.messageBox(
			(_("New version available, version %s. Do you want download it now?") % version.strip()+('\n%s' % msg)).strip(),
			title,
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES: processUpdate()

	def unavailableUpdateDialog(msg = ''):
		gui.messageBox(
			(_("You are up-to-date. %s is the latest version.") % configBE._addonVersion+'\n%s' % msg).strip(),
			title,
			wx.OK|wx.ICON_INFORMATION)

	def errorUpdateDialog():
		gui.messageBox(
			_("Oops! There was a problem checking for updates. Please retry later or go to manually at")+'\n%s' % configBE._addonURL,
			title,
			wx.OK|wx.ICON_ERROR)

	def processUpdate():
		url = configBE._addonURL + "latest?" + urllib.urlencode(paramsDL())
		fp = os.path.join(globalVars.appArgs.configPath, "brailleExtender.nvda-addon")
		try:
			dl = urllib.URLopener()
			dl.retrieve(url, fp)
			try:
				curAddons = []
				for addon in addonHandler.getAvailableAddons():
					curAddons.append(addon)
				bundle = addonHandler.AddonBundle(fp)
				prevAddon = None
				bundleName = bundle.manifest['name']
				for addon in curAddons:
					if not addon.isPendingRemove and bundleName == addon.manifest['name']:
						prevAddon = addon
						break
				if prevAddon:
					prevAddon.requestRemove()
				addonHandler.installAddonBundle(bundle)
				core.restart()
			except BaseException as e:
				log.error(e)
				os.startfile(fp)
		except BaseException as e:
			log.error(e)
			ui.message(_("Unable to save or download update file. Opening your browser"))
			os.startfile(url)
		return

	title = _("BrailleExtender's Update")
	newUpdate = False
	url = '{0}BrailleExtender.latest?{1}'.format(configBE._addonURL, urllib.urlencode(paramsDL()))
	msg = ""
	version = ""
	try:
		page = urllib.urlopen(url)
		pageContent = page.read().strip()
		if (page.code == 200 and len(pageContent) < 700):
			version = re.sub('\n(.+)$', '\1', pageContent).strip().replace('\r','').replace('','')
			msg = re.findall(r'msg: ?(.+)$', pageContent)
			msg = msg[0].strip() if len(msg) == 1 else ''
			if version != configBE._addonVersion: newUpdate = True
		if not newUpdate and sil:
			log.debug('No update')
			return
		if newUpdate: wx.CallAfter(availableUpdateDialog, version, msg)
		else: wx.CallAfter(unavailableUpdateDialog, msg)
	except BaseException, e:
		log.debug(e)
		if not newUpdate and sil: return
		wx.CallAfter(errorUpdateDialog)

# ***** Attribra code *****
def decorator(fn, s):
	def _getTypeformFromFormatField(self, field):
		# convention: to mark we put 4 (bold for liblouis)
		for attr, value in ATTRS.iteritems():
			fval = field.get(attr, False)
			if fval in value:
				return 4
		# if COMPLCOLORS != None:
			# col = field.get("color",False)
			# if col and (col != COMPLCOLORS):
				# return 4
		return 0

	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		conf = formatConfig.copy()
		if configBE.conf['general']['attribra']:
			conf["reportFontAttributes"] = True
			conf["reportColor"] = True
			conf["reportSpellingErrors"] = True
			if logTextInfo: log.info(info.getTextWithFields(conf))
		fn(self, info, conf, isSelection)

	def update(self):
		fn(self)
		if instanceGP.hideDots78:
			for i, j in enumerate(self.brailleCells): self.brailleCells[i] &= 63
		if not configBE.conf['general']['attribra']: return
		if not config.conf["braille"]["translationTable"].endswith('.utb') and 'comp8' not in config.conf["braille"]["translationTable"] and 'ru-compbrl.ctb' not in config.conf["braille"]["translationTable"]: return
		DOT7 = 64
		DOT8 = 128
		for i, j in enumerate(self.rawTextTypeforms):
			if j == 4: self.brailleCells[i] |= DOT7 | DOT8

	if s == "addTextWithFields": return addTextWithFields_edit
	if s == "update": return update
	if s == "_getTypeformFromFormatField": return _getTypeformFromFormatField

def populateAttrs(pid):
		if (len(configBE.confAttribra) == 0): return
		global ATTRS  # We are changing the global variable
		appname = appModuleHandler.getAppNameFromProcessID(pid)
		if (appname in configBE.confAttribra):
			ATTRS = configBE.confAttribra[appname]
		elif ("global" in configBE.confAttribra):
			ATTRS = configBE.confAttribra["global"]
		else:
			ATTRS = {}
# *************************


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = configBE._addonName
	hourDatePlayed = False
	autoScrollRunning = False
	brailleKeyboardLocked = False
	hideDots78 = False
	modifiersLocked = False
	hourDateTimer = None
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
	instanceST = None
	currentPid = ""
	nativeModifiers = True if hasattr(brailleInput.handler, "toggleModifier") else False

	def __init__(self):
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		global instanceGP
		instanceGP = self
		patchs.instanceGP = instanceGP
		settings.instanceGP = instanceGP
		log.debug('! New instance of GlobalPlugin: {0}'.format(id(instanceGP)))
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		self.createMenu()
		if not globalVars.appArgs.secure and configBE.conf['general']['autoCheckUpdate'] and time.time() - configBE.conf['general']['lastCheckUpdate'] > 86400:
			checkUpdates(True)
			configBE.conf['general']['lastCheckUpdate'] = time.time()

		configBE.loadConfAttribra()  # parse configuration
		self.backup__addTextWithFields = braille.TextInfoRegion._addTextWithFields
		self.backup__update = braille.TextInfoRegion.update
		self.backup__getTypeformFromFormatField = braille.TextInfoRegion._getTypeformFromFormatField
		if len(configBE.confAttribra) > 0:  # If no cfg then do not replace functions
			braille.TextInfoRegion._addTextWithFields = decorator(braille.TextInfoRegion._addTextWithFields, "addTextWithFields")
			braille.TextInfoRegion.update = decorator(braille.TextInfoRegion.update, "update")
			braille.TextInfoRegion._getTypeformFromFormatField = decorator(braille.TextInfoRegion._getTypeformFromFormatField, "_getTypeformFromFormatField")
		if configBE.conf['general']['reverseScroll']:
			self.reverseScrollBtns()
		return

	def event_gainFocus(self, obj, nextHandler):
		if self.hourDatePlayed:
			self.script_hourDate(None)
		if self.autoScrollRunning:
			self.script_autoScroll(None)

		pid = obj.processID
		if self.currentPid != pid:
			populateAttrs(pid)
			self.currentPid = pid
			if obj.appModule.appName in configBE.reviewModeApps and not self.switchedMode:
				if not hasattr(braille.handler, "TETHER_AUTO"):
					self.backupTether = braille.handler.tether
					braille.handler.tether = braille.handler.TETHER_REVIEW
				else:
					if config.conf["braille"]["autoTether"]:
						self.backupTether = braille.handler.TETHER_AUTO
						config.conf["braille"]["autoTether"] = False
					else:
						self.backupTether = braille.handler.tether
					braille.handler.setTether(braille.handler.TETHER_REVIEW, auto=False)
					braille.handler.handleReviewMove(shouldAutoTether=False)
				self.switchedMode = True
			elif self.switchedMode and obj.appModule.appName not in configBE.reviewModeApps: self.restorReviewCursorTethering()

		if braille.handler is not None and configBE.curBD != braille.handler.display.name:
			configBE.curBD = braille.handler.display.name
			self.onReload(None, 1)
		nextHandler()
		return

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

	def createMenu(self):
		self.NVDAMenu = gui.mainFrame.sysTrayIcon.menu
		menu = wx.Menu()
		self.brailleExtenderMenu = self.NVDAMenu.AppendSubMenu(menu, '%s (%s)' % (configBE._addonName, configBE._addonVersion), _('%s menu' % configBE._addonName))

		item = menu.Append(wx.ID_ANY, _("Documentation"), _("Opens the addon's documentation."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDoc, item)
		item = menu.Append(wx.ID_ANY, _("Settings..."), _("Opens the addon's settings."))
		gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onSettings, item)
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

	def gesturesInit(self):
		# rotor gestures
		if 'rotor' in configBE.iniProfile.keys():
			for k in configBE.iniProfile["rotor"]:
				if isinstance(configBE.iniProfile["rotor"][k], list):
					for l in configBE.iniProfile["rotor"][k]:
						self.rotorGES['br(%s):%s' % (configBE.curBD, l)] = k
				else:
					self.rotorGES['br(%s):%s' %(configBE.curBD, configBE.iniProfile["rotor"][k])] = k
			log.debug(self.rotorGES)
		else:
			log.debug('No rotor gestures for this profile')

		# keyboard layout gestures
		gK = OrderedDict()
		try:
			cK = configBE.iniProfile['keyboardLayouts'][configBE.conf['general']['keyboardLayout_%s' % configBE.curBD]] if configBE.conf['general']['keyboardLayout_%s' % configBE.curBD] and configBE.conf['general']['keyboardLayout_%s' % configBE.curBD] in configBE.iniProfile['keyboardLayouts'] is not None else configBE.iniProfile['keyboardLayouts'].keys()[0]
			for k in cK:
				if k in ['enter', 'backspace']:
					if isinstance(cK[k], list):
						for l in cK[k]:
							gK[inputCore.normalizeGestureIdentifier('br(%s):%s' %(configBE.curBD, l))] = 'kb:%s' % k
					else:
						gK['kb:%s' % k] = inputCore.normalizeGestureIdentifier('br(%s):%s' % (configBE.curBD, cK[k]))
				elif k in ['braille_dots', 'braille_enter', 'braille_translate']:
					if isinstance(cK[k], list):
						for i in range(len(cK[k])):
							if ':' not in cK[k][i]:
								cK[k][i] = inputCore.normalizeGestureIdentifier('br(%s):%s' % (configBE.curBD, cK[k][i]))
					else:
						if ':' not in cK[k]:
							cK[k] = 'br(%s):%s' %(configBE.curBD, cK[k])
					gK[k] = cK[k]
			inputCore.manager.localeGestureMap.update({'globalCommands.GlobalCommands': gK})
			self.noKC = False
			log.debug('Keyboard conf found, loading layout `%s`' %configBE.conf['general']['keyboardLayout_' + configBE.curBD])
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
			"br(" + configBE.curBD + "):routing": "cancelShortcut",
			#: arrow keys
			"br(" + configBE.curBD + "):up": "end_combKeys",
			"br(" + configBE.curBD + "):down": "end_combKeys",
			"br(" + configBE.curBD + "):left": "end_combKeys",
			"br(" + configBE.curBD + "):right": "end_combKeys",
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
							self._pGestures[inputCore.normalizeGestureIdentifier('br(%s):%s' % (configBE.curBD, gesture))] = k
				else:
					self._pGestures[inputCore.normalizeGestureIdentifier('br(%s):%s' % (configBE.curBD, v))] = k
		self.bindGestures(self._pGestures)
		self.bindGestures({'br(%s):%s' % (configBE.curBD, k): "quickLaunch" for k in configBE.quickLaunches.keys()})
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
		if rotorItem >= len(rotorItems) - 1:
			rotorItem = 0
		else:
			rotorItem += 1
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
		if previous:
			ROTOR_RANGE = ROTOR_RANGE - 1 if ROTOR_RANGE > 0 else 5
		else:
			ROTOR_RANGE = ROTOR_RANGE + 1 if ROTOR_RANGE < 5 else 0
		ui.message(self.getCurrentSelectionRange())
		return

	def script_nextEltRotor(self, gesture):
		if rotorItem == ROTOR_DEF:
			return self.sendComb('rightarrow', gesture)
		elif rotorItem in [ROTOR_MOVE, ROTOR_SELECT]:
			return self.sendComb(self.getCurrentSelectionRange(False), gesture)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+rightarrow', gesture)
			self.showBrailleObj()
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
			self.showBrailleObj()
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
			self.showBrailleObj()
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
			self.showBrailleObj()
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
		configBE.conf['general']['attribra'] = not configBE.conf['general']['attribra']
		self.refreshBD()
		speech.speakMessage('Attribra %s' % (_('enabled') if configBE.conf['general']['attribra'] else _('disabled')))
	script_toggleAttribra.__doc__ = _('Enable/disable Attribra')

	def script_toggleSpeechScrollFocusMode(self, gesture):
		configBE.conf['general']['speakScrollFocusMode'] = not configBE.conf['general']['speakScrollFocusMode']
		ui.message(_('Speech %s while scrolling') % (_('enabled') if configBE.conf['general']['speakScrollFocusMode'] else _('disabled')))
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
			if configBE.conf['general']['hourDynamic']:
				if configBE.noMessageTimeout:
					self.backupMessageTimeout = config.conf["braille"]["noMessageTimeout"]
					config.conf["braille"]["noMessageTimeout"] = True
			self.showHourDate()
			if configBE.conf['general']['hourDynamic']:
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
				configBE.conf['general']['delayScroll_' + configBE.curBD] * 1000)
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
		if configBE.conf['general']['reportVolumeBraille']:
			braille.handler.message(s)
		if configBE.conf['general']['reportVolumeSpeech']:
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
		if configBE.conf['general']['reportVolumeBraille']:
			braille.handler.message(s)
		if configBE.conf['general']['reportVolumeSpeech']:
			speech.speakMessage(str(utils.getVolume()))
		return
	script_volumeMinus.__doc__ = _('Decrease the master volume')

	def script_toggleVolume(s, g):
		keyboardHandler.KeyboardInputGesture.fromName('volumemute').send()
		if utils.getMute() and configBE.conf['general']['reportVolumeBraille']:
			return braille.handler.message(_('Muted sound'))
		s = _('Unmuted sound (%3d%%)') % utils.getVolume()
		if configBE.conf['general']['reportVolumeSpeech']:
			speech.speakMessage(s)
		if configBE.conf['general']['reportVolumeBraille']:
			braille.handler.message(s)
		return
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
							t.append(utils.beautifulSht(' / '.join(configBE.iniProfile['keyboardLayouts'][layout][lk]), 1) + configBE.sep + ': ' + func.__doc__)
						else:
							t.append(utils.beautifulSht(str(configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + func.__doc__)
					else:
						if isinstance(
								configBE.iniProfile['keyboardLayouts'][layout][lk], list):
							t.append(
								utils.beautifulSht(
									' / '.join(
										configBE.iniProfile['keyboardLayouts'][layout][lk]),
									1) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
						else:
							t.append(utils.beautifulSht(str(
								configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
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
	script_quickLaunch.__doc__ = _(
		'Opens a custom program/file. Go to settings to define them')

	def script_checkUpdate(self, gesture):
		if not globalVars.appArgs.secure:
			checkUpdates()
		return

	script_checkUpdate.__doc__ = _(
		'Check for %s updates, and starts the download if there is one') % configBE._addonName

	@staticmethod
	def increaseDelayAutoScroll():
		configBE.conf['general']['delayScroll_' + configBE.curBD] += 0.25

	@staticmethod
	def decreaseDelayAutoScroll():
		if configBE.conf['general']['delayScroll_' +
									configBE.curBD] - 0.25 >= 0.25:
			configBE.conf['general']['delayScroll_' + configBE.curBD] -= 0.25

	def script_increaseDelayAutoScroll(self, gesture):
		self.increaseDelayAutoScroll()
		if self.autoScrollRunning:
			self.script_autoScroll(None, True)
			self.script_autoScroll(None)
		else:
			ui.message('%s s' %
					   configBE.conf['general']['delayScroll_' + configBE.curBD])
		return

	def script_decreaseDelayAutoScroll(self, gesture):
		self.decreaseDelayAutoScroll()
		if self.autoScrollRunning:
			self.script_autoScroll(None, True)
			self.script_autoScroll(None)
		else:
			ui.message('%s s' % configBE.conf['general']['delayScroll_' + configBE.curBD])
		return

	script_increaseDelayAutoScroll.__doc__ = _('Increase autoscroll delay')
	script_decreaseDelayAutoScroll.__doc__ = _('Decrease autoscroll delay')

	def script_switchInputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.iTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["inputTable"] in configBE.iTables:
			configBE.iTables.append(config.conf["braille"]["inputTable"])
		tid = configBE.iTables.index(config.conf["braille"]["inputTable"])
		nID = tid + 1 if tid + 1 < len(configBE.iTables) else 0
		brailleInput.handler.table = brailleTables.listTables(
		)[configBE.tablesFN.index(configBE.iTables[nID])]
		ui.message(_('Input: %s') % brailleInput.handler.table.displayName)
		return

	script_switchInputBrailleTable.__doc__ = _(
		"Switch between his favorite input braille tables")

	def script_switchOutputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(
				_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.oTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["translationTable"] in configBE.oTables:
			configBE.oTables.append(config.conf["braille"]["translationTable"])
		tid = configBE.oTables.index(
			config.conf["braille"]["translationTable"])
		nID = tid + 1 if tid + 1 < len(configBE.oTables) else 0
		config.conf["braille"]["translationTable"] = configBE.oTables[nID]
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
		if sv:
			configBE.saveSettings()
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		self._pGestures=OrderedDict()
		configBE.quickLaunches = OrderedDict()
		configBE.loadConfAttribra()
		configBE.loadConf()
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		if configBE.conf['general']['reverseScroll']:
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

	def script_reloadAddon(self, gesture):
		return self.onReload()
	script_reloadAddon.__doc__ = _('Reload %s') % configBE._addonName

	def script_reload_brailledisplay(self, gesture):
		if hasattr(gesture, 'id'):
			ui.message(_('Please use the keyboard for this feature'))
			return
		i = 2 if 'shift' in gesture.normalizedIdentifiers[0] else 1
		if configBE.conf['general']['brailleDisplay' + str(i)] == 'noBraille':
			if config.conf["braille"]["display"] == 'noBraille':
				return ui.message(
					_('No braille display specified. No reload to do'))
			else:
				utils.reload_brailledisplay(config.conf["braille"]["display"])
				configBE.curBD = braille.handler.display.name
		elif config.conf["braille"]["display"] != "auto":
			utils.reload_brailledisplay(
				configBE.conf['general']['brailleDisplay' + str(i)])
			configBE.curBD = configBE.conf['general']['brailleDisplay' +
													  str(i)]
		else:
			speech.speakMessage(_("Profile reloaded"))
			configBE.curBD = braille.handler.display.name
		self.refreshBD()
		return self.onReload(None, True)

	script_reload_brailledisplay.__doc__ = _(
		'Reload the driver of an favorite or last braille display. Practical if the braille display is not plugged immediately or that the latter is disconnected and then reconnected')

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
				_tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g])).replace(
					'br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
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
			if configBE.conf['general']['iTableShortcuts'] != '?':
				self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots, configBE.conf['general']['iTableShortcuts']), gesture)
			else:
				self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots), gesture)
		self.clearModifiers()

	def sendComb(self, sht, gesture):
		if ((configBE.conf['general']['iTableShortcuts'] != '?' and configBE.isContractedTable(configBE.conf['general']['iTableShortcuts']))
			or (configBE.conf['general']['iTableShortcuts'] == '?' and configBE.isContractedTable(brailleInput.handler.table.fileName))
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
		if self.nativeModifiers:
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
					except:
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
		if configBE.conf['general']['feedbackModifiersKeysInBraille']:
			braille.handler.message('%s...' % s)
		if configBE.conf['general']['feedbackModifiersKeysInSpeech']:
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

	def onSettings(self, event):
		settings.Settings()

	def script_logFieldsAtCursor(self, gesture):
		global logTextInfo
		logTextInfo = not logTextInfo
		msg = ["stop", "start"]
		ui.message("debug textInfo " + msg[logTextInfo])

	__gestures = OrderedDict()
	__gestures["kb:NVDA+control+shift+a"] = "logFieldsAtCursor"
	__gestures["kb:shift+NVDA+i"] = "switchInputBrailleTable"
	__gestures["kb:shift+NVDA+p"] = "currentBrailleTable"
	__gestures["kb:shift+NVDA+u"] = "switchOutputBrailleTable"
	__gestures["kb:shift+NVDA+y"] = "autoScroll"
	__gestures["kb:nvda+k"] = "reload_brailledisplay"
	__gestures["kb:nvda+shift+k"] = "reload_brailledisplay"
	__gestures["kb:nvda+windows+k"] = "reloadAddon"
	__gestures["kb:volumeMute"] = "toggleVolume"
	__gestures["kb:volumeUp"] = "volumePlus"
	__gestures["kb:volumeDown"] = "volumeMinus"
	__gestures["kb:nvda+alt+u"] = "translateInBRU"
	__gestures["kb:nvda+alt+i"] = "translateInCellDescription"
	__gestures["kb:nvda+alt+y"] = "getTableOverview"
	__gestures["kb:nvda+shift+j"] = "toggleAttribra"

	def terminate(self):
		braille.TextInfoRegion._addTextWithFields = self.backup__addTextWithFields
		braille.TextInfoRegion.update = self.backup__update
		braille.TextInfoRegion._getTypeformFromFormatField = self.backup__getTypeformFromFormatField
		self.restorReviewCursorTethering()
		if self.instanceST is not None:
			self.instanceST.onClose(None)
		if instanceUP is not None:
			instanceUP.onClose(None)
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
		configBE.saveSettings()
		super(GlobalPlugin, self).terminate()

	def removeMenu(self):
		if hasattr(self, "brailleExtenderMenu"): self.NVDAMenu.RemoveItem(self.brailleExtenderMenu)
