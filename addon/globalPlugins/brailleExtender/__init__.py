# coding: utf-8
# BrailleExtender Addon for NVDA
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.
# Copyright (C) 2017 André-Abush CLAUSE <dev@andreabc.net>
#
# Additional third party copyrighted code is included:
#	- *Attribra*: Copyright (C) 2017 Alberto Zanella <lapostadialberto@gmail.com>
#	-> https://github.com/albzan/attribra/

import os
import re
import time
import urllib
from collections import OrderedDict
from configobj import ConfigObj
import gui
from subprocess import Popen
import wx
import addonHandler
addonHandler.initTranslation()
import appModuleHandler
import braille
import brailleInput
import brailleTables
import config
import controlTypes
import core
import cursorManager
import globalCommands
import globalPlugins
import globalPluginHandler
import globalVars
import inputCore
import languageHandler
import scriptHandler
import speech
import treeInterceptorHandler
import virtualBuffers

import ui
import versionInfo
from keyboardHandler import KeyboardInputGesture
from logHandler import log
import configBE
import settings
import utils
import api
instanceGP = None
instanceUP = None
noKC = None
lang = configBE.lang
ATTRS = {}
logTextInfo = False
ROTOR_DEF = 0
ROTOR_WORD = 1
ROTOR_OBJ = 2
ROTOR_ERR = 3

rotorItems = [
	_('Default'),
	_('Words'),
	_('Objects'),
	_('Spelling errors')
]
rotorItem = 0

paramsDL = lambda: {
	"versionProtocole": "1.2",
	"versionAddon": configBE._addonVersion,
	"versionNVDA": versionInfo.version,
	"language": languageHandler.getLanguage(),
	"installed": config.isInstalledCopy(),
	"brailledisplay": config.conf["braille"]["display"],
	}


def decorator(fn, str):
	def _getTypeformFromFormatField(self, field):
		#convention: to mark we put 4 (bold for liblouis)
		for attr,value in ATTRS.iteritems():
			fval = field.get(attr,False)
			if fval in value:
				return 4
		# if COMPLCOLORS != None:
			# col = field.get("color",False)
			# if col and (col != COMPLCOLORS):
				# return 4
		return 0
	
	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		conf = formatConfig.copy()
		conf["reportFontAttributes"]=True
		conf["reportColor"]=True
		conf["reportSpellingErrors"]=True
		if logTextInfo:
			log.info(info.getTextWithFields(conf))
		fn(self, info, conf, isSelection)

	def update(self):
		fn(self)
		DOT7 = 64
		DOT8 = 128
		for i in xrange(0,len(self.rawTextTypeforms)):
			if self.rawTextTypeforms[i] == 4:
				self.brailleCells[i] |= DOT7 | DOT8

	if str == "addTextWithFields":
		return addTextWithFields_edit
	if str == "update":
		return update
	if str == "_getTypeformFromFormatField":
		return _getTypeformFromFormatField

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = configBE._addonName
	hourDatePlayed = False
	autoScrollRunning = False
	modifiers = {
		'control': False,
		'alt'	 : False,
		'windows': False,
		'shift'	 : False,
		'nvda'	 : False,
	}
	_tGestures = OrderedDict()
	_pGestures = OrderedDict()
	rotorGES = {}

	if not configBE.noUnicodeTable:
		backupInputTable = brailleInput.handler.table
	backupMessageTimeout = None
	backupShowCursor = False
	backupTether = braille.handler.tether
	switchedMode = False
	instanceST = None
	currentPid = ""

	def __init__(self):
		super(globalPluginHandler.GlobalPlugin, self).__init__()
		global instanceGP
		instanceGP = self
		log.debug('! New instance of GlobalPlugin: {0}'.format(id(instanceGP)))
		configBE.initGestures()
		configBE.loadGestures()
		self.gesturesInit()
		if not self.createMenu():
			log.error(u'Impossible to create menu')
		if not globalVars.appArgs.secure and configBE.conf['general']['autoCheckUpdate'] and time.time()-configBE.conf['general']['lastCheckUpdate'] > 172800:
			CheckUpdates(True)
			configBE.conf['general']['lastCheckUpdate'] = time.time()
		if configBE.conf['general']['attribra']:
			configBE.loadConfAttribra() #parse configuration
			if len(configBE.confAttribra) > 0: #If no cfg then do not replace functions
				braille.TextInfoRegion._addTextWithFields = decorator(braille.TextInfoRegion._addTextWithFields,"addTextWithFields")
				braille.TextInfoRegion.update = decorator(braille.TextInfoRegion.update,"update")
				braille.TextInfoRegion._getTypeformFromFormatField = decorator(braille.TextInfoRegion._getTypeformFromFormatField,"_getTypeformFromFormatField")					
		if configBE.conf['general']['reverseScroll']:
			self.reverseScrollBtns()
		return

	def event_gainFocus(self, obj, nextHandler):
		if self.hourDatePlayed:
			self.script_hourDate(None)
		if self.autoScrollRunning:
			self.script_autoScroll(None)
		if obj.appModule.appName in configBE.reviewModeApps and not self.switchedMode:
			self.backupTether = braille.handler.tether
			self.switchedMode = True
			braille.handler.tether = braille.handler.TETHER_REVIEW
		elif self.switchedMode and obj.appModule.appName not in configBE.reviewModeApps:
			braille.handler.tether = self.backupTether
			self.switchedMode = False
		nextHandler()
		pid = obj.processID
		if self.currentPid != pid:
			self.populateAttrs(pid)
			self.currentPid = pid

	def populateAttrs(self,pid):
		if (len(configBE.confAttribra) == 0): return
		global ATTRS #We are changing the global variable
		appname = appModuleHandler.getAppNameFromProcessID(pid)
		if (appname in configBE.confAttribra):
			ATTRS = configBE.confAttribra[appname]
		elif ("global" in configBE.confAttribra):
			ATTRS = configBE.confAttribra["global"]
		else: ATTRS = {}

	def createMenu(self):
		try:
			self.menu = wx.Menu()
			self.item = self.menu.Append(
				wx.ID_ANY,
				_("Documentation"),
				_("Opens the addon's documentation.")
			)
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDoc, self.item)
			self.item = self.menu.Append(
				wx.ID_ANY,
				_("Settings..."),
				_("Opens the addon's settings.")
			)
			gui.mainFrame.sysTrayIcon.Bind(
				wx.EVT_MENU, self.onSettings, self.item)
			self.item = self.menu.Append(
				wx.ID_ANY,
				_("Reload add-on"),
				_("Reload this add-on.")
			)
			gui.mainFrame.sysTrayIcon.Bind(
				wx.EVT_MENU, self.onReload, self.item)
			self.item = self.menu.Append(
				wx.ID_ANY,
				_("&Check for update..."),
				_("Checks if update is available")
			)
			gui.mainFrame.sysTrayIcon.Bind(
				wx.EVT_MENU,
				self.onUpdate,
				self.item
			)
			self.item = self.menu.Append(
				wx.ID_ANY,
				_("&Website"),
				_("Open addon's website.")
			)
			gui.mainFrame.sysTrayIcon.Bind(
				wx.EVT_MENU, self.onWebsite, self.item)
			self.menu = gui.mainFrame.sysTrayIcon.menu.InsertMenu(
				2,
				wx.ID_ANY,
				'%s (%s)' % (configBE._addonName, configBE._addonVersion),
				self.menu
			)
			return True
		except BaseException:
			return False

	def terminate(self):
		super(GlobalPlugin, self).terminate()
		if self.instanceST != None:
			self.instanceST.onClose(None)
		if instanceUP != None:
			instanceUP.onClose(None)
		inputCore.manager.localeGestureMap.clear()
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
		return configBE.saveSettings()

	def removeMenu(self):
		try:
			if self.menu is not None:
				gui.mainFrame.sysTrayIcon.menu.RemoveItem(self.menu)
			return True
		except wx.PyDeadObjectError:
			return False

	def gesturesInit(self):
		global noKC
		if 'rotor' in configBE.iniProfile.keys():
			for k in configBE.iniProfile["rotor"]:
				if list == type(configBE.iniProfile["rotor"][k]):
					for l in configBE.iniProfile["rotor"][k]:
						self.rotorGES['br('+configBE.curBD+'):'+l] = k
				else:
					self.rotorGES['br('+configBE.curBD+'):'+configBE.iniProfile["rotor"][k]] = k
			log.debug(self.rotorGES)
		else:
			log.debug('No rotor gestures for this profile')

		gK = OrderedDict()
		try:
			cK = configBE.iniProfile['keyboardLayouts'][configBE.conf['general']['keyboardLayout_' + configBE.curBD]] if configBE.conf['general']['keyboardLayout_' + configBE.curBD] and configBE.conf['general']['keyboardLayout_' + configBE.curBD] in configBE.iniProfile['keyboardLayouts'] != None else configBE.iniProfile['keyboardLayouts'].keys()[0]
			for k in cK:
				if k in ['enter', 'backspace']:
					if isinstance(cK[k], list):
						for l in cK[k]:
							gK[inputCore.normalizeGestureIdentifier(
								'br(' + configBE.curBD + '):' + l)] = 'kb:' + k
					else:
						gK['kb:' + k] = inputCore.normalizeGestureIdentifier(
							'br(' + configBE.curBD + '):' + cK[k])
				elif k in ['braille_dots','braille_enter','braille_translate']:
					if isinstance(cK[k], list):
						for i in range(len(cK[k])):
							if ':' not in cK[k][i]:
								cK[k][i] = inputCore.normalizeGestureIdentifier(
									str('br(' + configBE.curBD + '):') + str(cK[k][i]))
					else:
						if ':' not in cK[k]:
							cK[k] = str('br(' + configBE.curBD + '):') + str(cK[k])
					gK[k] = cK[k]
			inputCore.manager.localeGestureMap.update({'globalCommands.GlobalCommands': gK})
			noKC = False
			log.debug('Keyboard conf found, loading layout `%s`' %configBE.conf['general']['keyboardLayout_' + configBE.curBD])
		except BaseException:
			log.debug('No keyboard conf found')
			noKC = True
		# for NVDA remote
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
						self._tGestures[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g][h]))] = "end_combKeys"
				elif ('kb:' in g and g.lower() not in ['kb:alt', 'kb:control', 'kb:windows', 'kb:control', 'kb:applications']):
					self._tGestures[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g]))] = "end_combKeys"
			self._pGestures = {}
			for k, v in configBE.iniProfile["modifierKeys"].items()+configBE.iniProfile["miscs"].items():
				if isinstance(v, list):
					for i in range(len(v)):
						if k == 'shortcutsOn':
							pass
						else:
							self._pGestures[inputCore.normalizeGestureIdentifier('br(' + configBE.curBD + '):' + v[i])] = k
				else:
					self._pGestures[inputCore.normalizeGestureIdentifier('br(' + configBE.curBD + '):' + v)] = k
			self.bindGestures(self._pGestures)
		return

	def bindRotorGES(self):
		for k in self.rotorGES:
				try:
					self.removeGestureBinding(k)
				except:
					pass
		if rotorItem == ROTOR_DEF:
			return
		if rotorItem == ROTOR_OBJ:
			self.bindGestures(self.rotorGES)
		else:
			for k in self.rotorGES:
				if self.rotorGES[k] not in ['selectElt','nextSetRotor','priorSetRotor']:
					self.bindGestures({k: self.rotorGES[k]})


	def showBrailleObj(self):
		s=[]
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
			s.append('=> '+api.getNavigatorObject().keyboardShortcut)
		if obj.location:
			s.append('[%s]' %(', '.join([str(k) for k in obj.location])))
		if s!= []:
			braille.handler.message(' '.join(s))
		return

	def script_priorRotor(self, gesture):
		global rotorItem
		if rotorItem > 0:
			rotorItem -= 1
		else:
			rotorItem = len(rotorItems)-1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem])

	def script_nextRotor(self, gesture):
		global rotorItem
		if rotorItem >= len(rotorItems)-1:
			rotorItem = 0
		else:
			rotorItem += 1
		self.bindRotorGES()
		return ui.message(rotorItems[rotorItem])

	def script_nextEltRotor(self, gesture):
		if rotorItem == ROTOR_DEF:
			return self.sendComb('rightarrow', gesture)
		elif rotorItem == ROTOR_WORD:
			return self.sendComb('control+rightarrow', gesture)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+rightarrow', gesture)
			self.showBrailleObj()
		elif rotorItem == ROTOR_ERR:
			obj = api.getFocusObject()
			if obj.treeInterceptor != None:
				obj.treeInterceptor.script_nextError(gesture)
			else:
				ui.message(_('Not supported here or browse mode not enabled'))
		else:
			return ui.message(_('Not implemented yet'))
	script_priorRotor.__doc__ = _('Select previous rotor setting')
	script_nextRotor.__doc__ = _('Select next rotor setting')

	def script_priorEltRotor(self,gesture):
		if rotorItem == ROTOR_DEF:
			return self.sendComb('leftarrow', gesture)
		elif rotorItem == ROTOR_WORD:
			return self.sendComb('control+leftarrow', gesture)
		elif rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+leftarrow', gesture)
			self.showBrailleObj()
		elif rotorItem == ROTOR_ERR:
			obj = api.getFocusObject()
			if obj.treeInterceptor != None:
				obj.treeInterceptor.script_previousError(gesture)
			else:
				ui.message(_('Not supported here or browse mode not enabled'))
		else:
			return ui.message('Not implemented yet')

	def script_nextSetRotor(self,gesture):
		if rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+downarrow', gesture)
			self.showBrailleObj()
		else:
			return self.sendComb('downarrow', gesture)
	def script_priorSetRotor(self,gesture):
		if rotorItem == ROTOR_OBJ:
			self.sendComb('nvda+shift+uparrow', gesture)
			self.showBrailleObj()
			return
		else:
			return self.sendComb('uparrow', gesture)
	script_priorEltRotor.__doc__ = _('Move to previous item depending rotor setting')
	script_nextEltRotor.__doc__ = _('Move to next item depending rotor setting')

	def script_selectElt(self,gesture):
		if rotorItem == ROTOR_OBJ:
			return self.sendComb('NVDA+enter', gesture)
		else:
			return self.sendComb('enter', gesture)
	script_selectElt.__doc__ = _('Varies depending on rotor setting. Eg: in object mode, it\'s similar to NVDA+enter')

	script_priorSetRotor.__doc__ = _('Move to previous item using rotor setting')
	script_nextSetRotor.__doc__ = _('Move to next item using rotor setting')

	def script_toggleSpeech(self, gesture):
		if speech.speechMode == 0:
			speech.speechMode = 2
			ui.message(_('Speech on'))
		else:
			speech.speechMode = 0
			ui.message(_('Speech off'))
		return
	script_toggleSpeech.__doc__ = _('Toggle speech on or off')

	def script_position(self, gesture=None):
		return ui.message('{0}% ({1}/{2})'.format(round(utils.getPositionPercentage(),2), utils.getPosition()[0], utils.getPosition()[1]))
	script_position.__doc__=_('Get the cursor position of text')

	def script_hourDate(self, gesture = None):
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

	def showHourDate(self):
		currentHourDate = time.strftime(u'%X %x (%a, %W/53, %b)', time.localtime())
		return braille.handler.message(currentHourDate.decode('mbcs'))

	def script_autoScroll(self, gesture, sil = False):
		if self.hourDatePlayed:
			return
		if self.autoScrollRunning:
			self.autoScrollTimer.Stop()
			if not sil:
				ui.message(_(u'Autoscroll stopped'))
			config.conf["braille"]["showCursor"] = self.backupShowCursor
		else:
			self.backupShowCursor = config.conf["braille"]["showCursor"]
			config.conf["braille"]["showCursor"] = False
			self.autoScrollTimer = wx.PyTimer(self.autoScroll)
			self.autoScrollTimer.Start(configBE.conf['general']['delayScroll_' + configBE.curBD] * 1000)
		self.autoScrollRunning = not self.autoScrollRunning
		return

	script_autoScroll.__doc__ = _('Enable/disable autoscroll')

	def autoScroll(self):
		return braille.handler.scrollForward()

	def script_volumePlus(s, g):
		KeyboardInputGesture.fromName('volumeup').send()
		s = '%3d%%%s' %(utils.getVolume(), utils.translatePercent(utils.getVolume(), braille.handler.displaySize-4))
		braille.handler.message(s) if configBE.conf['general']['reportVolumeBraille'] else None
		speech.speakMessage(str(utils.getVolume())) if configBE.conf['general']['reportVolumeSpeech'] else None
		return
	script_volumePlus.__doc__ = _('Increase the master volume')
	def refreshBD(self):
		obj = api.getFocusObject()
		if obj.treeInterceptor != None:
			ti = treeInterceptorHandler.update(obj)
			if not ti.passThrough:
				braille.handler.handleGainFocus(ti)
		else:
			braille.handler.handleGainFocus(api.getFocusObject())
	def clearMessageFlash(self):
		if config.conf["braille"]["messageTimeout"] != 0:
			braille.handler.message("?")
			braille.handler.routeTo(1)
			return

	def script_volumeMinus(s, g):
		KeyboardInputGesture.fromName('volumedown').send()
		s = '%3d%%%s' %(utils.getVolume(), utils.translatePercent(utils.getVolume(), braille.handler.displaySize-4))
		braille.handler.message(s) if configBE.conf['general']['reportVolumeBraille'] else None
		speech.speakMessage(str(utils.getVolume())) if configBE.conf['general']['reportVolumeSpeech'] else None
		return

	script_volumeMinus.__doc__ = _('Decrease the master volume')

	def script_toggleVolume(s, g):
		KeyboardInputGesture.fromName('volumemute').send()
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
		return s.getDoc()
	script_getHelp.__doc__ = _('Show the %s documentation') % configBE._addonName

	def getKeyboardLayouts(self):
		i = 0
		lb = []
		if not noKC and 'keyboardLayouts' in configBE.iniProfile:
			for layout in configBE.iniProfile['keyboardLayouts']:
				t = []
				for lk in configBE.iniProfile['keyboardLayouts'][layout]:
					if lk in ['braille_dots','braille_enter','braille_translate']:
						if isinstance(configBE.iniProfile['keyboardLayouts'][layout][lk], list):
							t.append(utils.beautifulSht(
								' / '.join(configBE.iniProfile['keyboardLayouts'][layout][lk]), 1) + configBE.sep + ': ' + eval('globalCommands.GlobalCommands.script_'+lk+'.__doc__'))
						else:
							t.append(utils.beautifulSht(
								str(configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + eval('globalCommands.GlobalCommands.script_'+lk+'.__doc__'))
					else:
						if isinstance(configBE.iniProfile['keyboardLayouts'][layout][lk], list):
							t.append(utils.beautifulSht(
								' / '.join(configBE.iniProfile['keyboardLayouts'][layout][lk]), 1) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
						else:
							t.append(utils.beautifulSht(
								str(configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
				lb.append((configBE.sep + '; ').join(t))
		return lb

	def getDocScript(s, n):
		doc = None
		if type(n) == list:
			n = str(n[-1][-1])
		if n.startswith('kb:'):
			return _('Emulates pressing %s on the system keyboard') % utils.getKeysTranslation(n)
		places = ['s.script_','globalCommands.commands.script_','cursorManager.CursorManager.script_']
		for place in places:
			try:
				doc = re.sub(r'\.$', '', eval(''.join([place, n, '.__doc__'])))
				break
			except BaseException:
				pass
		return doc if doc != None else _('description currently unavailable for this shortcut')

	def translateLst(s, lst):
		doc = u'<ul>'
		for g in lst:
			if 'kb:' in g and 'capsLock' not in g and 'insert' not in g:
				if isinstance(lst[g], list):
					doc += u'<li>{0}{2}: {1}{2};</li>'.format(
					utils.getKeysTranslation(g),
					utils.beautifulSht(' / '.join(lst[g]).replace('br(' + configBE.curBD + '):', ''), 1),
					configBE.sep)
				else:
					doc += u'<li>{0}{2}: {1}{2};</li>'.format(
					utils.getKeysTranslation(g),
					utils.beautifulSht(str(lst[g])),
					configBE.sep)
			elif 'kb:' in g:
				gt = _(u'caps lock') if 'capsLock' in g else g
				doc += u'<li>{0}{2}: {1}{2};</li>'.format(
				gt.replace('kb:',''),
				utils.beautifulSht(lst[g]).replace('br(' + configBE.curBD + '):',''),
				configBE.sep)
			else:
				if isinstance(lst[g], list):
					doc += u'<li>{0}{1}: {2}{3};</li>'.format(utils.beautifulSht(' / '.join(lst[g]).replace('br(' + configBE.curBD + '):',''),1),configBE.sep, re.sub('^([A-Z])', lambda m: m.group(1).lower(), utils.uncapitalize(s.getDocScript(g))), configBE.sep)
				else:
					doc += u'<li>{0}{1}: {2}{3};</li>'.format(utils.beautifulSht(lst[g]).replace('br(' + configBE.curBD + '):',''),configBE.sep, re.sub('^([A-Z])',lambda m: m.group(1).lower(), utils.uncapitalize(s.getDocScript(g))), configBE.sep)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += u'</ul>'
		return doc

	def getDoc(s):
		doc = u"""
		<h1>{NAME}{DISPLAY}</h1>
		<p>Version {VERSION}<br />
		{AUTHOR}<br />
		{URL}</p>
		<pre>{DESC}</pre>
		""".format(
			NAME=configBE._addonName,
			DISPLAY=configBE.sep+': '+_('%s braille display') % configBE.curBD.capitalize() if configBE.gesturesFileExists else '',
			VERSION=configBE._addonVersion,
			AUTHOR=configBE._addonAuthor.replace('<', '&lt;').replace('>','&gt;'),
			URL='<a href="' +configBE._addonURL +'">' +configBE._addonURL +'</a>',
			DESC=configBE._addonDesc
		)
		doc += '<h2 lang="en">Copyrights and acknowledgements</h2>'+('\n'.join([
			"<p>",
			_(u"Copyright (C) 2017 André-Abush Clause, and other contributors:"),"</p>",
			"<ul><li>Mohammadreza Rashad &lt;mohammadreza5712@gmail.com&gt;: "+_("Persian translation")+";</li>",
			"<li>Zvonimir stanecic &lt;zvonimirek222@yandex.com&gt;: "+_("Polish and Croatian translations")+".</li></ul>",
			"<p>"+_(u"Additional third party copyrighted code is included:")+"</p>",
			u"""<ul><li><em>Attribra</em>{SEP}: Copyright (C) 2017 Alberto Zanella &lt;lapostadialberto@gmail.com&gt; → <a href="https://github.com/albzan/attribra/">https://github.com/albzan/attribra/</a></li>
		""".format(SEP=configBE.sep),u"</ul>",
		"<p>"+_("Thanks also to")+":</p>",
		"<ul><li>Corentin "+_("for his tests and suggestions with")+" Brailliant;</li>",
		"<li>Louis "+_("for his tests and suggestions with")+" Focus.</li></ul>",
		"<p>"+_("And Thank you very much for all your feedback and comments via email.")+" :)</p>"])
		)
		doc += """
		<div lang="en"><h2>Last changes</h2>
		<p>Coming soon: gesture profiles, other rotor functions, finalizing tabs in settings, some shortcuts revisions...</p>
		<ul>
			<li>translations in polish and croatian. Thanks to Zvonimir stanecic!</li>
			<li>Bug fix concerning scroll gestures with Brailliant display;</li>
			<li>NVDARemote support (partially).</li>
		</ul>
		</ul>
		</div>
		"""
		if configBE.gesturesFileExists:
			mKB = OrderedDict()
			mNV = OrderedDict()
			mW = OrderedDict()
			for g in configBE.iniGestures['globalCommands.GlobalCommands'].keys():
				if 'kb:' in g:
					if '+' in g:
						mW[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
					else:
						mKB[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
				else:
					mNV[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
			doc += ('<h2>' + _('Simple keys') +' (%s)</h2>') % str(len(mKB))
			doc += s.translateLst(mKB)
			doc += ('<h2>' + _('Usual shortcuts') +' (%s)</h2>') % str(len(mW))
			doc += s.translateLst(mW)
			doc += ('<h2>' + _('Standard NVDA commands') +' (%s)</h2>') % str(len(mNV))
			doc += s.translateLst(mNV)
			doc += '<h2>{0} ({1})</h2>'.format(_('Modifier keys'), len(configBE.iniProfile["modifierKeys"]))
			doc += s.translateLst(configBE.iniProfile["modifierKeys"])
			doc += '<h2>' + _('Quick navigation keys') + '</h2>'
			doc += "<p>"+_(u'In virtual documents (HTML/PDF/…) you can navigate element type by element type using keyboard. These navigation keys should work with your braille terminal equally.</p><p>In addition to these, there are some specific shortcuts:')+"</p>"
			doc += s.translateLst(configBE.iniGestures['cursorManager.CursorManager'])
			doc += '<h2>'+_('Rotor feature')+'</h2>'
			doc += s.translateLst({k: configBE.iniProfile["miscs"][k] for k in configBE.iniProfile["miscs"] if 'rotor' in k.lower()})+s.translateLst(configBE.iniProfile["rotor"])
			doc += ('<h2>' + _('Gadget commands') +' (%s)</h2>') % str(len(configBE.iniProfile["miscs"])-2)
			doc += s.translateLst(OrderedDict([(k, configBE.iniProfile["miscs"][k]) for k in configBE.iniProfile["miscs"] if k not in ['nextRotor','priorRotor']]))
			doc += u'<h2>{0} ({1})</h2>'.format(_('Shortcuts defined outside add-on'), len(braille.handler.display.gestureMap._map))
			doc += '<ul>'
			for g in braille.handler.display.gestureMap._map:
				doc += (u'<li>{0}{1}: {2}{3};</li>').format(utils.beautifulSht(g).capitalize(), configBE.sep, utils.uncapitalize(re.sub('^([A-Z])', lambda m: m.group(1).lower(), s.getDocScript(braille.handler.display.gestureMap._map[g]))), configBE.sep)
			doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
			doc += '</ul>'

			# list keyboard layouts
			if not noKC and 'keyboardLayouts' in configBE.iniProfile:
				lb = s.getKeyboardLayouts()
				doc += '<h2>{}</h2>'.format(_('Keyboard configurations provided'))
				doc += u'<p>{}{}:</p><ol>'.format(_('Keyboard configurations are'), configBE.sep)
				for l in lb:
					doc += u'<li>{}.</li>'.format(l)
				doc += '</ol>'
		else:
			doc += ('<h2>'+_(u"Warning:")+'</h2><p>'+
				_(u"BrailleExtender doesn't seem to support your braille display.")+'<br />'+
				_(u'However, you can reassign most of these features in the "Command Gestures" dialog in the "Preferences" of NVDA.')+'</p>'
			)
		doc += ('<h2>' + _('Shortcuts on system keyboard specific to the add-on') +' (%s)</h2>') % str(len(s.__gestures)-4)
		doc += '<ul>'
		for g in [k for k in s.__gestures if k.lower().startswith('kb:')]:
			if g.lower() not in ['kb:volumeup','kb:volumedown','kb:volumemute'] and s.__gestures[g] not in ['logFieldsAtCursor']:
				doc += (u'<li>{0}{1}: {2}{3};</li>').format(utils.getKeysTranslation(g), configBE.sep, re.sub('^([A-Z])', lambda m: m.group(1).lower(), s.getDocScript(s.__gestures[g])), configBE.sep)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += '</ul>'
		return ui.browseableMessage(
			doc, _(u'%s\'s documentation') %
			configBE._addonName, True)

	def script_quickLaunch(self, gesture):
		if gesture.id not in configBE.quickLaunch:
			configBE.quickLaunch.append(gesture.id)
			configBE.quickLaunchS.append('')
			return ui.message(gesture.id+' added')
		try:
			return Popen(configBE.quickLaunchS[configBE.quickLaunch.index('+'.join(sorted((gesture.id).lower().split('+'))))].strip())
		except BaseException:
			return ui.message(_("No such file or directory"))
	script_quickLaunch.__doc__=_('Opens a custom program/file. Go to settings to define them')

	def script_checkUpdate(self, gesture):
		if not globalVars.appArgs.secure:
			CheckUpdates()
		return

	script_checkUpdate.__doc__ = _('Check for %s updates, and starts the download if there is one') % configBE._addonName

	def increaseDelayAutoScroll(self):
		configBE.conf['general']['delayScroll_' + configBE.curBD]+=0.25

	def decreaseDelayAutoScroll(self):
		if configBE.conf['general']['delayScroll_' + configBE.curBD]-0.25 >= 0.25:
			configBE.conf['general']['delayScroll_' + configBE.curBD] -= 0.25

	def script_increaseDelayAutoScroll(self, gesture):
		self.increaseDelayAutoScroll()
		if self.autoScrollRunning:
			self.script_autoScroll(None, True)
			self.script_autoScroll(None)
		else:
			ui.message('%s s' % configBE.conf['general']['delayScroll_' + configBE.curBD])
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

	def script_switchKeyboardLayout(self, gesture):
		self.clearGestureBindings()
		ls = configBE.iniProfile['keyboardLayouts'].keys()
		kid = ls.index(configBE.conf['general']['keyboardLayout_'+configBE.curBD]) if configBE.conf['general']['keyboardLayout_'+configBE.curBD] in ls else 0
		nId = ls[kid+1] if kid+1 < len(ls) else ls[0]
		configBE.conf['general']['keyboardLayout_' + configBE.curBD] = nId
		ui.message(_("Configuration {0} ({1})").format(str(ls.index(nId)+1), self.getKeyboardLayouts()[ls.index(nId)]))
		configBE.saveSettings()
		return self.onReload(None, True)

	script_switchKeyboardLayout.__doc__ = _("Switch between different braille keyboard configurations.")

	def script_switchInputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.iTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["inputTable"] in configBE.iTables:
			configBE.iTables.append(config.conf["braille"]["inputTable"])
		tid = configBE.iTables.index(config.conf["braille"]["inputTable"])
		nID = tid+1 if tid+1<len(configBE.iTables) else 0
		brailleInput.handler.table = brailleTables.listTables()[configBE.tablesFN.index(configBE.iTables[nID])]
		return ui.message(brailleInput.handler.table.displayName)
	
	script_switchInputBrailleTable.__doc__ = _("Switch between his favorite input braille tables")
	
	def script_switchOutputBrailleTable(self, gesture):
		if configBE.noUnicodeTable:
			return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
		if len(configBE.oTables) < 2:
			return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
		if not config.conf["braille"]["translationTable"] in configBE.oTables:
			configBE.oTables.append(config.conf["braille"]["translationTable"])
		tid = configBE.oTables.index(config.conf["braille"]["translationTable"])
		nID = tid+1 if tid+1<len(configBE.oTables) else 0
		config.conf["braille"]["translationTable"] = configBE.oTables[nID]
		self.refreshBD()
		return ui.message(configBE.tablesTR[configBE.tablesFN.index(config.conf["braille"]["translationTable"])])

	script_switchOutputBrailleTable.__doc__ = _("Switch between his favorite output braille tables")
	
	def script_brlDescChar(self, gesture):
		utils.currentCharDesc()
	script_brlDescChar.__doc__ = _(
		"Gives the Unicode value of the "
		"character where the cursor is located "
		"and the decimal, binary and octal equivalent.")

	def script_showConstructST(self, gesture):
		configBE.conf['general']['showConstructST'] = not configBE.conf['general']['showConstructST']
		return ui.message("%s" % (_('Turn on') if configBE.conf['general']['showConstructST'] else _('Turn off')))

	script_showConstructST.__doc__ = _('Turn on/off the assistance shortcuts.')

	def onDoc(self, evt):
		return self.getDoc()

	def onReload(self, evt=None, sil=False, sv=False):
		inputCore.manager.localeGestureMap.clear()
		if sv:
			configBE.saveSettings()
		configBE.checkConfigPath()
		configBE.initGestures()
		configBE.loadConf()
		configBE.loadGestures()
		self.gesturesInit()
		configBE.loadConfAttribra()
		if configBE.conf['general']['reverseScroll']:
			self.reverseScrollBtns()
		if not sil:
			ui.message(_('%s reloaded') % configBE._addonName)
		return

	def onUpdate(self, evt):
		return CheckUpdates()

	def script_about(self, gesture):
		return self.onAbout(None)
	script_about.__doc__ = _('Show the "about" window')

	def onWebsite(self, evt):
		return os.startfile(configBE._addonURL)

	def script_reloadAddon(self, gesture):
		return self.onReload()
	script_reloadAddon.__doc__ = _('Reload %s') % configBE._addonName

	def script_reload_brailledisplay(self, gesture):
		if hasattr(gesture, 'id'):
			ui.message(_(u'Please use the keyboard for this feature'))
			return
		i = 2 if 'shift' in gesture.normalizedIdentifiers[0] else 1
		if configBE.conf['general']['brailleDisplay'+str(i)] == 'noBraille':
			if config.conf["braille"]["display"] == 'noBraille':
				return ui.message(_('No braille display specified. No reload to do')) 
			else:
				utils.reload_brailledisplay(config.conf["braille"]["display"])
				configBE.curBD = config.conf["braille"]["display"]
		else:
			utils.reload_brailledisplay(configBE.conf['general']['brailleDisplay'+str(i)])
			configBE.curBD = configBE.conf['general']['brailleDisplay'+str(i)]
		self.refreshBD()
		return self.onReload(None, True)

	script_reload_brailledisplay.__doc__ = _('Reload the driver of an favorite or last braille display. Practical if the braille display is not plugged immediately or that the latter is disconnected and then reconnected')

	def shortcutInProgress(self):
		for k in self.modifiers:
			if self.modifiers[k]:
				return True
		return False

	def lenModifiers(self):
		return len([k for k in self.modifiers if self.modifiers[k]])

	def clearModifiers(self):
		self.modifiers = {k: False for k in self.modifiers}
		self.clearGestureBindings()
		self.bindGestures(self.__gestures)
		return self.bindGestures(self._pGestures)

	def sendCombKeys(self, sendKS, send=True):
		if send:
			log.debug("Sending " + sendKS)
			KeyboardInputGesture.fromName(sendKS).send() if not sendKS == "" else None
		return

	def script_end_combKeys(self, gesture):
		_tmpGesture = {
			'up': 'uparrow',
			'down': 'downarrow',
			'left': 'leftarrow',
			'right': 'rightarrow',
		}
		for g in configBE.iniGestures['globalCommands.GlobalCommands']:
			if isinstance(configBE.iniGestures['globalCommands.GlobalCommands'][g], list):
				for h in range(
						len(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
					_tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g][h])).replace(
						'br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
			elif ('kb:' in g and g not in ['kb:alt', 'kb:ctrl', 'kb:windows', 'kb:control', 'kb:applications'] and 'br(' + configBE.curBD + '):' in str(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
				_tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g])).replace('br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
			gId = inputCore.normalizeGestureIdentifier('br(' + configBE.curBD + '):' + str(gesture.id)).replace('br(' + configBE.curBD + '):', '')
		sht = self.getActualModifiers(False) +_tmpGesture[gId]
		if not gId in _tmpGesture:
			return ui.message("Unknown " + gId)
		self.clearModifiers()
		self.clearMessageFlash()
		return self.sendComb(sht, gesture)

	def script_end_combKeysChar(self, gesture):
		self.clearMessageFlash()
		if not hasattr(gesture, 'id'):
			ch = gesture.normalizedIdentifiers[0].split(':')[1]
			#if ch.isupper:
				#ch = 'shift+%s'% ch
			self.sendComb(self.getActualModifiers(False) + ch, gesture)
		else:
			self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots, brailleTables.listTables()[configBE.conf['general']['iTableSht']][0], gesture) if not configBE.noUnicodeTable and configBE.conf['general']['iTableSht'] > - 1 and configBE.conf['general']['iTableSht'] < len(brailleTables.listTables()) else self.getActualModifiers(False) + utils.bkToChar(gesture.dots), gesture)
		self.clearModifiers()

	def sendComb(self, sht, gesture):
		NVDASht = self.sendCombKeysNVDA(sht, gesture)
		if not NVDASht and not 'nvda' in sht.lower():
			try:
				return self.sendCombKeys(sht)
			except BaseException:
				return ui.message(_('Unable to send %s') % sht)
		elif not NVDASht: # and 'nvda' in sht.lower()
			return ui.message(_(u'%s is not part of a NVDA commands') % sht)

	def sendCombKeysNVDA(self, sht, gesture):
		# to improve + not finished
		if 'kb:' not in sht:
			sht = 'kb:' + sht
		shtO = sht
		add = '+nvda' if 'nvda+' in sht else ''
		sht = '+'.join(sorted((inputCore.normalizeGestureIdentifier(sht.replace('nvda+','')).replace('kb:','') +add).split('+')))

		# Gesture specific scriptable object.
		obj = gesture.scriptableObject
		log.debug(gesture)
		if obj:
			ui.message('Gesture specific scriptable object present:')
			log.debug(obj)
		"""
		obj = gesture.scriptableObject
		if obj:
			func = _getObjScript(obj, gesture, globalMapScripts)
			if func:
				return func
		"""

		# Global plugin level
		shtPlugins = {p: eval('globalPlugins.'+p+'.GlobalPlugin._GlobalPlugin__gestures') for p in globalPlugins.__dict__.keys() if not p.startswith('_') and hasattr(eval('globalPlugins.'+p+'.GlobalPlugin'),'_GlobalPlugin__gestures')}
		for k in shtPlugins:
			shtPlugins[k] = {re.sub(':(.+)$',lambda m: inputCore.normalizeGestureIdentifier(m.group(0)), g.lower().replace(' ','')): shtPlugins[k][g] for g in shtPlugins[k] if g.lower().startswith('kb:')}
		for p in shtPlugins.keys():
			if 'kb:'+sht in shtPlugins[p]:
				if self.callScript('globalPlugins.%s' % p, 'script_%s' % shtPlugins[p]['kb:'+sht], gesture):
					return True

		# App module level.
		focus = api.getFocusObject()
		app = focus.appModule
		for k in focus.appModule._gestureMap:
			ui.message(k)
			pass
			if app and cls=='AppModule' and module==app.__module__:
				func = getattr(app, "script_%s" % scriptName, None)
				if func:
					func(gesture)
					return True

		# Tree interceptor level.
		try:
			obj = api.getFocusObject()
			if obj.treeInterceptor != None:
				obj = obj.treeInterceptor
				gesS=obj._CursorManager__gestures.values()+obj._BrowseModeDocumentTreeInterceptor__gestures.values()+obj._BrowseModeTreeInterceptor__gestures.values()
				gesO = [re.sub(':(.+)$',lambda m: m.group(0), g) for g in obj._CursorManager__gestures.keys()+obj._BrowseModeDocumentTreeInterceptor__gestures.keys()+obj._BrowseModeTreeInterceptor__gestures.keys()]
				gesN = [re.sub(':(.+)$',lambda m: inputCore.normalizeGestureIdentifier(m.group(0)), g) for g in gesO]
				script = gesS[gesN.index('kb:'+sht)]
				eval('obj.script_'+script+'(gesture)')
				return True
			else:
				gesO = [re.sub(':(.+)$',lambda m: m.group(0), g) for g in cursorManager.CursorManager._CursorManager__gestures]
				gesN = [re.sub(':(.+)$',lambda m: inputCore.normalizeGestureIdentifier(m.group(0)), g) for g in cursorManager.CursorManager._CursorManager__gestures]
				if 'kb:'+sht in gesN:
					a=cursorManager.CursorManager()
					a.makeTextInfo = obj.makeTextInfo
					script = a._CursorManager__gestures[gesO[gesN.index('kb:'+sht)]]
					eval('a.script_'+script+'(gesture)')
					return True
		except BaseException, e:
			pass
		"""
		treeInterceptor = focus.treeInterceptor
		if treeInterceptor and treeInterceptor.isReady:
			func = getattr(treeInterceptor , "script_%s" % scriptName, None)
			# We are no keyboard input
			return func
		"""

		# NVDAObject level.
		log.debug(dir(focus))
		""" TODO !
		func = getattr(focus, "script_%s" % scriptName, None)
		if func:
			return func
		for obj in reversed(api.getFocusAncestors()):
			func = getattr(obj, "script_%s" % scriptName, None)
			if func and getattr(func, 'canPropagate', False):
				return func
			"""

		# Global Commands level.
		layouts = ['','(laptop)','(desktop)']
		places = ['globalCommands.commands._gestureMap']
		for layout in layouts:
			for place in places:
				try:
					tSht = eval('scriptHandler.getScriptName(%s[\'kb%s:%s\'])' % (place, layout, sht))
					func = getattr(globalCommands.commands, "script_%s" % tSht, None)
					if func:
						func(gesture)
						return True
				except:
					pass
		return False

	def callScript(self,cls, f, gesture):
		for plugin in globalPluginHandler.runningPlugins:
			if plugin.__module__ == cls:
				func = getattr(plugin, f)
				if func:
					func(gesture)
					return True
				else:
					return false

	def initCombKeys(self):
		self.bindGestures(self._tGestures) if self.lenModifiers() == 1 else None

	def getActualModifiers(self, short=True):
		if self.lenModifiers() == 0:
			return self.script_cancelShortcut(None)
		s = ""
		t = {'windows': _('WIN'),'control': _('CTRL'),'shift': _('SHIFT'),'alt': _('ALT'),'nvda': 'NVDA'}
		for k in [k for k in self.modifiers if self.modifiers[k]]:
			s += t[k] + '+' if short else k + '+'
		if not short:
			return s
		if configBE.conf['general']['showConstructST']:
			return braille.handler.message(u'%s...' % s)
		
	def script_ctrl(self, gesture = None, sil=True):
		self.modifiers["control"] = not self.modifiers["control"]
		self.getActualModifiers() if sil else None
		return self.initCombKeys()

	def script_nvda(self, gesture = None):
		self.modifiers["nvda"] = not self.modifiers["nvda"]
		self.getActualModifiers()
		return self.initCombKeys()
	def script_alt(self, gesture = None, sil=True):
		self.modifiers["alt"] = not self.modifiers["alt"]
		self.getActualModifiers() if sil else None
		return self.initCombKeys()

	def script_win(self, gesture = None, sil=True):
		self.modifiers["windows"] = not self.modifiers["windows"]
		self.getActualModifiers() if sil else None
		return self.initCombKeys()

	def script_shift(self, gesture = None, sil=True):
		self.modifiers["shift"] = not self.modifiers["shift"]
		self.getActualModifiers() if sil else None
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
	docModKeys = lambda k: _('Emulate pressing down ')+'+'.join([utils.getKeysTranslation(l) for l in k.split('+')])+_(' on the system keyboard')
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

	def reverseScrollBtns(self, gesture = None, cancel = False):
		if cancel:
			scbtns = [inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollForward']+[inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollBack']
		else:
			scbtns = [inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollBack']+[inputCore.manager.getAllGestureMappings()['Braille'][g].gestures for g in inputCore.manager.getAllGestureMappings()['Braille'] if inputCore.manager.getAllGestureMappings()['Braille'][g].scriptName == 'braille_scrollForward']
		for k in scbtns[0]:
			if k.lower() not in ['br(freedomscientific):leftwizwheelup','br(freedomscientific):leftwizwheeldown']:
				self.__gestures[k] = "braille_scrollForward"
		for k in scbtns[1]:
			if k.lower() not in ['br(freedomscientific):leftwizwheelup','br(freedomscientific):leftwizwheeldown']:
				self.__gestures[k] = "braille_scrollBack"
		self.bindGestures(self.__gestures)
		return

	def onSettings(self, event):
		settings.Settings(configBE.curBD, configBE.reviewModeApps, configBE.noUnicodeTable, noKC, configBE.gesturesFileExists, configBE.iniProfile, configBE.quickLaunch, configBE.quickLaunchS, instanceGP, self.getKeyboardLayouts(), configBE.backupDisplaySize, configBE.iTables, configBE.oTables)

	def script_logFieldsAtCursor(self, gesture) :
		global logTextInfo
		logTextInfo = not logTextInfo
		msg = ["stop","start"]
		ui.message("debug textInfo "+msg[logTextInfo])
		
	__gestures = OrderedDict()
	__gestures["kb:NVDA+control+shift+a"] = "logFieldsAtCursor"
	__gestures["kb:shift+NVDA+i"] = "switchInputBrailleTable"
	__gestures["kb:shift+NVDA+u"] = "switchOutputBrailleTable"
	__gestures["kb:shift+NVDA+y"] = "autoScroll"
	__gestures["kb:nvda+k"] = "reload_brailledisplay"
	__gestures["kb:nvda+shift+k"] = "reload_brailledisplay"
	__gestures["kb:nvda+windows+k"] = "reloadAddon"
	__gestures["kb:volumeMute" ]= "toggleVolume"
	__gestures["kb:volumeUp"] = "volumePlus"
	__gestures["kb:volumeDown"] = "volumeMinus"
				
class CheckUpdates(wx.Dialog):
	def __init__(self, sil = False):
		global instanceUP
		if instanceUP != None:
			return
		instanceUP = self
		title = _('{0} update').format(configBE._addonName)
		newUpdate = False
		url = '{0}BrailleExtender.latest?{1}'.format(configBE._addonURL, urllib.urlencode(paramsDL()))
		try:
			page = urllib.urlopen(url)
			pageContent = page.read().strip()
			if (page.code == 200 and pageContent.replace('_', '-') != configBE._addonVersion and len(pageContent) < 20):
				newUpdate = True
				msg = _("New version available, version %s. Do you want download it now?") % pageContent.strip()
			else:
				msg = _("You are up-to-date. %s is the latest version.") % configBE._addonVersion
		except BaseException:
			msg = _("Oops! There was a problem checking for updates. Please retry later.")
		if not newUpdate and sil:
			return
		wx.Dialog.__init__(self, None, title=_("BrailleExtender's Update"))
		self.msg = wx.StaticText(self, -1, label=msg)
		if newUpdate:
			self.yesBTN = wx.Button(self, wx.ID_YES, label=_("&Yes"))
			self.noBTN = wx.Button(self, label=_("&No"), id=wx.ID_CLOSE)
			self.yesBTN.Bind(wx.EVT_BUTTON, self.onYes)
			self.noBTN.Bind(wx.EVT_BUTTON, self.onClose)
		else:
			self.okBTN = wx.Button(self, label=_("OK"), id=wx.ID_CLOSE)
			self.okBTN.Bind(wx.EVT_BUTTON, self.onClose)
		self.EscapeId = wx.ID_CLOSE
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Show(True)
		return

	def onYes(self, event):
		global instanceUP
		self.Destroy()
		url = configBE._addonURL + "latest?" + urllib.urlencode(paramsDL())
		fp = os.path.join(config.getUserDefaultConfigPath(), "brailleExtender.nvda-addon")
		try:
			dl=urllib.URLopener()
			dl.retrieve(url, fp)
			try:
				curAddons=[]
				for addon in addonHandler.getAvailableAddons():
					curAddons.append(addon)
				bundle=addonHandler.AddonBundle(fp)
				prevAddon=None
				bundleName=bundle.manifest['name']
				for addon in curAddons:
					if not addon.isPendingRemove and bundleName==addon.manifest['name']:
						prevAddon=addon
						break
				if prevAddon:
					prevAddon.requestRemove()
				addonHandler.installAddonBundle(bundle)
				self.Destroy()
				instanceUP = None
				core.restart()
			except BaseException as e:
				log.error(e)
				os.startfile(fp)
		except BaseException as e:
			log.error(e)
			ui.message(_('Unable to save or download update file. Opening your browser'))
			os.startfile(url)
		self.Destroy()
		instanceUP = None
		return

	def onClose(self, event):
		global instanceUP
		try:
			self.Destroy()
		except:
			pass
		instanceUP = None
		return
