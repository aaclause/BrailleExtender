# settings.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import glob
import hashlib
import os
import json
import gui
import wx
import addonHandler
import braille
import config
import controlTypes
import core
import inputCore
import keyLabels
import queueHandler
import scriptHandler
import ui
addonHandler.initTranslation()

from .brailleTablesExt import SettingsDlg as BrailleTablesDlg
from . import configBE
from . import utils
from .advancedInputMode import SettingsDlg as AdvancedInputModeDlg
from .oneHandMode import SettingsDlg as OneHandModeDlg
from .undefinedChars import SettingsDlg as UndefinedCharsDlg
from .common import *

instanceGP = None
addonSettingsDialogActiveConfigProfile = None
addonSettingsDialogWindowHandle = None

def notImplemented(msg='', style=wx.OK|wx.ICON_INFORMATION):
	if not msg: msg = _("Feature implementation is in progress. Thanks for your patience.")
	gui.messageBox(msg, _("Braille Extender"), wx.OK|wx.ICON_INFORMATION)

class GeneralDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("General")
	bds_k = [k for k, v in configBE.getValidBrailleDisplayPreferred()]
	bds_v = [v for k, v in configBE.getValidBrailleDisplayPreferred()]

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		self.autoCheckUpdate = sHelper.addItem(wx.CheckBox(self, label=_("&Automatically check for Braille Extender updates")))
		self.autoCheckUpdate.SetValue(config.conf["brailleExtender"]["autoCheckUpdate"])

		# Translators: label of a dialog.
		self.updateChannel = sHelper.addLabeledControl(_("Add-on &update channel:"), wx.Choice, choices=list(configBE.updateChannels.values()))
		if config.conf["brailleExtender"]["updateChannel"] in configBE.updateChannels.keys():
			itemToSelect = list(configBE.updateChannels.keys()).index(config.conf["brailleExtender"]["updateChannel"])
		else: itemToSelect = list(config.conf["brailleExtender"]["updateChannel"]).index(configBE.CHANNEL_stable)
		self.updateChannel.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.speakScroll = sHelper.addLabeledControl(_("Say current line while &scrolling in:"), wx.Choice, choices=list(configBE.focusOrReviewChoices.values()))
		self.speakScroll.SetSelection(list(configBE.focusOrReviewChoices.keys()).index(config.conf["brailleExtender"]["speakScroll"]))

		# Translators: label of a dialog.
		self.stopSpeechScroll = sHelper.addItem(wx.CheckBox(self, label=_("Speech &interrupt when scrolling on same line")))
		self.stopSpeechScroll.SetValue(config.conf["brailleExtender"]["stopSpeechScroll"])

		# Translators: label of a dialog.
		self.stopSpeechUnknown = sHelper.addItem(wx.CheckBox(self, label=_("Speech i&nterrupt for unknown gestures")))
		self.stopSpeechUnknown.SetValue(config.conf["brailleExtender"]["stopSpeechUnknown"])

		# Translators: label of a dialog.
		self.speakRoutingTo = sHelper.addItem(wx.CheckBox(self, label=_("Announce character when &routing braille cursor")))
		self.speakRoutingTo.SetValue(config.conf["brailleExtender"]["speakRoutingTo"])

		# Translators: label of a dialog.
		self.routingReviewModeWithCursorKeys = sHelper.addItem(wx.CheckBox(self, label=_("&Use cursor keys to route cursor in review mode")))
		self.routingReviewModeWithCursorKeys.SetValue(config.conf["brailleExtender"]["routingReviewModeWithCursorKeys"])

		# Translators: label of a dialog.
		self.hourDynamic = sHelper.addItem(wx.CheckBox(self, label=_("&Display time and date infinitely")))
		self.hourDynamic.SetValue(config.conf["brailleExtender"]["hourDynamic"])
		self.reviewModeTerminal = sHelper.addItem(wx.CheckBox(self, label=_("Automatically Switch to review mode in &terminal windows (cmd, bash, PuTTY, PowerShell Maxima…)")))
		self.reviewModeTerminal.SetValue(config.conf["brailleExtender"]["reviewModeTerminal"])

		# Translators: label of a dialog.
		self.volumeChangeFeedback = sHelper.addLabeledControl(_("Announce &volume changes:"), wx.Choice, choices=list(configBE.outputMessage.values()))
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in configBE.outputMessage:
			itemToSelect = list(configBE.outputMessage.keys()).index(config.conf["brailleExtender"]["volumeChangeFeedback"])
		else:
			itemToSelect = list(configBE.outputMessage.keys()).index(configBE.CHOICE_braille)
		self.volumeChangeFeedback.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.modifierKeysFeedback = sHelper.addLabeledControl(_("Announce m&odifier key presses:"), wx.Choice, choices=list(configBE.outputMessage.values()))
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in configBE.outputMessage:
			itemToSelect = list(configBE.outputMessage.keys()).index(config.conf["brailleExtender"]["modifierKeysFeedback"])
		else:
			itemToSelect = list(configBE.outputMessage.keys()).index(configBE.CHOICE_braille)
		# Translators: label of a dialog.
		self.beepsModifiers = sHelper.addItem(wx.CheckBox(self, label=_("Play &beeps for modifier keys")))
		self.beepsModifiers.SetValue(config.conf["brailleExtender"]["beepsModifiers"])

		# Translators: label of a dialog.
		self.modifierKeysFeedback.SetSelection(itemToSelect)
		self.rightMarginCells = sHelper.addLabeledControl(_("&Right margin on cells for the active braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=int(config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD]))
		if configBE.gesturesFileExists:
			lb = [k for k in instanceGP.getKeyboardLayouts()]
			# Translators: label of a dialog.
			self.KBMode = sHelper.addLabeledControl(_("Braille &keyboard configuration:"), wx.Choice, choices=lb)
			self.KBMode.SetSelection(configBE.getKeyboardLayout())

		# Translators: label of a dialog.
		self.reverseScrollBtns = sHelper.addItem(wx.CheckBox(self, label=_("&Reverse forward and back scroll buttons")))
		self.reverseScrollBtns.SetValue(config.conf["brailleExtender"]["reverseScrollBtns"])

		# Translators: label of a dialog.
		self.autoScrollDelay = sHelper.addLabeledControl(_("Autoscroll &delay for the active braille display (ms):"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=125, max=42000, initial=int(config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD]))
		self.brailleDisplay1 = sHelper.addLabeledControl(_("Preferred &primary braille display:"), wx.Choice, choices=self.bds_v)
		self.brailleDisplay1.SetSelection(self.bds_k.index(config.conf["brailleExtender"]["brailleDisplay1"]))
		self.brailleDisplay2 = sHelper.addLabeledControl(_("Preferred &secondary braille display:"), wx.Choice, choices=self.bds_v)
		self.brailleDisplay2.SetSelection(self.bds_k.index(config.conf["brailleExtender"]["brailleDisplay2"]))

	def postInit(self): self.autoCheckUpdate.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["autoCheckUpdate"] = self.autoCheckUpdate.IsChecked()
		config.conf["brailleExtender"]["hourDynamic"] = self.hourDynamic.IsChecked()
		config.conf["brailleExtender"]["reviewModeTerminal"] = self.reviewModeTerminal.IsChecked()
		if self.reverseScrollBtns.IsChecked(): instanceGP.reverseScrollBtns()
		else: instanceGP.reverseScrollBtns(None, True)
		config.conf["brailleExtender"]["reverseScrollBtns"] = self.reverseScrollBtns.IsChecked()
		config.conf["brailleExtender"]["stopSpeechScroll"] = self.stopSpeechScroll.IsChecked()
		config.conf["brailleExtender"]["stopSpeechUnknown"] = self.stopSpeechUnknown.IsChecked()
		config.conf["brailleExtender"]["speakRoutingTo"] = self.speakRoutingTo.IsChecked()
		config.conf["brailleExtender"]["routingReviewModeWithCursorKeys"] = self.routingReviewModeWithCursorKeys.IsChecked()

		config.conf["brailleExtender"]["updateChannel"] = list(configBE.updateChannels.keys())[self.updateChannel.GetSelection()]
		config.conf["brailleExtender"]["speakScroll"] = list(configBE.focusOrReviewChoices.keys())[self.speakScroll.GetSelection()]

		config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD] = self.autoScrollDelay.Value
		config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD] = self.rightMarginCells.Value
		config.conf["brailleExtender"]["brailleDisplay1"] = self.bds_k[self.brailleDisplay1.GetSelection()]
		config.conf["brailleExtender"]["brailleDisplay2"] = self.bds_k[self.brailleDisplay2.GetSelection()]
		if configBE.gesturesFileExists:
			config.conf["brailleExtender"]["keyboardLayout_%s" % configBE.curBD] = configBE.iniProfile["keyboardLayouts"].keys()[self.KBMode.GetSelection()]
		config.conf["brailleExtender"]["volumeChangeFeedback"] = list(configBE.outputMessage.keys())[self.volumeChangeFeedback.GetSelection()]
		config.conf["brailleExtender"]["modifierKeysFeedback"] = list(configBE.outputMessage.keys())[self.modifierKeysFeedback.GetSelection()]
		config.conf["brailleExtender"]["beepsModifiers"] = self.beepsModifiers.IsChecked()

class AttribraDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Text attributes")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleAttribra = sHelper.addItem(wx.CheckBox(self, label=_("Indicate text attributes in braille with &Attribra")))
		self.toggleAttribra.SetValue(config.conf["brailleExtender"]["features"]["attributes"])
		self.selectedElement = sHelper.addLabeledControl(_("&Selected elements:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.selectedElement.SetSelection(self.getItemToSelect("selectedElement"))
		self.spellingErrorsAttribute = sHelper.addLabeledControl(_("Spelling &errors:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.spellingErrorsAttribute.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.boldAttribute = sHelper.addLabeledControl(_("&Bold:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.boldAttribute.SetSelection(self.getItemToSelect("bold"))
		self.italicAttribute = sHelper.addLabeledControl(_("&Italic:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.italicAttribute.SetSelection(self.getItemToSelect("italic"))
		self.underlineAttribute = sHelper.addLabeledControl(_("&Underline:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.underlineAttribute.SetSelection(self.getItemToSelect("underline"))
		self.strikethroughAttribute = sHelper.addLabeledControl(_("Strike&through:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.strikethroughAttribute.SetSelection(self.getItemToSelect("strikethrough"))
		self.subAttribute = sHelper.addLabeledControl(_("Su&bscripts:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.subAttribute.SetSelection(self.getItemToSelect("text-position:sub"))
		self.superAttribute = sHelper.addLabeledControl(_("Su&perscripts:"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.superAttribute.SetSelection(self.getItemToSelect("text-position:super"))

	def postInit(self): self.toggleAttribra.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["features"]["attributes"] = self.toggleAttribra.IsChecked()
		config.conf["brailleExtender"]["attributes"]["selectedElement"] = configBE.attributeChoicesKeys[self.selectedElement.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["invalid-spelling"] = configBE.attributeChoicesKeys[self.spellingErrorsAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["bold"] = configBE.attributeChoicesKeys[self.boldAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["italic"] = configBE.attributeChoicesKeys[self.italicAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["underline"] = configBE.attributeChoicesKeys[self.underlineAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["strikethrough"] = configBE.attributeChoicesKeys[self.strikethroughAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:sub"] = configBE.attributeChoicesKeys[self.subAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:super"] = configBE.attributeChoicesKeys[self.superAttribute.GetSelection()]

	@staticmethod
	def getItemToSelect(attribute):
		try: idx = configBE.attributeChoicesKeys.index(config.conf["brailleExtender"]["attributes"][attribute])
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

class RoleLabelsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Role labels")

	roleLabels  = {}

	def makeSettings(self, settingsSizer):
		self.roleLabels = config.conf["brailleExtender"]["roleLabels"].copy()
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleRoleLabels = sHelper.addItem(wx.CheckBox(self, label=_("Use custom braille &role labels")))
		self.toggleRoleLabels.SetValue(config.conf["brailleExtender"]["features"]["roleLabels"])
		self.categories = sHelper.addLabeledControl(_("Role &category:"), wx.Choice, choices=[_("General"), _("Landmark"), _("Positive state"), _("Negative state")])
		self.categories.Bind(wx.EVT_CHOICE, self.onCategories)
		self.categories.SetSelection(0)
		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		self.labels = sHelper2.addLabeledControl(_("&Role:"), wx.Choice, choices=[controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()])
		self.labels.Bind(wx.EVT_CHOICE, self.onLabels)
		self.label = sHelper2.addLabeledControl(_("Braille &label"), wx.TextCtrl)
		self.label.Bind(wx.EVT_TEXT, self.onLabel)
		sHelper.addItem(sHelper2)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.resetLabelBtn = bHelper.addButton(self, wx.NewId(), _("&Reset this role label"), wx.DefaultPosition)
		self.resetLabelBtn.Bind(wx.EVT_BUTTON, self.onResetLabelBtn)
		self.resetAllLabelsBtn = bHelper.addButton(self, wx.NewId(), _("Reset all role labels"), wx.DefaultPosition)
		self.resetAllLabelsBtn.Bind(wx.EVT_BUTTON, self.onResetAllLabelsBtn)
		sHelper.addItem(bHelper)
		self.onCategories(None)

	def onCategories(self, event):
		idCategory = self.categories.GetSelection()
		if idCategory == 0:
			labels = [controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()]
		elif idCategory == 1:
			labels = list(braille.landmarkLabels.keys())
		elif idCategory == 2:
			labels = [controlTypes.stateLabels[k] for k in braille.positiveStateLabels.keys()]
		elif idCategory == 3:
			labels = [controlTypes.stateLabels[k] for k in braille.negativeStateLabels.keys()]
		else: labels = []
		for iLabel, label in enumerate(labels):
			idLabel = self.getIDFromIndexes(idCategory, iLabel)
			actualLabel = self.getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			labels[iLabel] += "%s: %s" % (punctuationSeparator, actualLabel)
			if actualLabel != originalLabel: labels[iLabel] += " (%s)" % originalLabel
		self.labels.SetItems(labels)
		if idCategory > -1 and idCategory < 4: self.labels.SetSelection(0)
		self.onLabels(None)

	def onLabels(self, event):
		idCategory = self.categories.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, self.labels.GetSelection())
		key = "%d:%s" % (idCategory, idLabel)
		if key in self.roleLabels.keys(): self.label.SetValue(self.roleLabels[key])
		else: self.label.SetValue(self.getOriginalLabel(idCategory, idLabel))

	def onLabel(self, evt):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		label = self.label.GetValue()
		if idCategory >= 0 and iLabel >= 0:
			if self.getOriginalLabel(idCategory, idLabel, chr(4)) == label:
				if key in self.roleLabels.keys():
					self.roleLabels.pop(key)
					log.debug("Key %s deleted" % key)
				else: log.info("Key %s not present" % key)
			else: self.roleLabels[key] = label
			actualLabel = self.getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			if label != originalLabel: self.resetLabelBtn.Enable()
			else: self.resetLabelBtn.Disable()

	def onResetLabelBtn(self, event):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		actualLabel = self.getLabelFromID(idCategory, idLabel)
		originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
		self.label.SetValue(originalLabel)
		self.onLabel(None)
		self.label.SetFocus()

	def onResetAllLabelsBtn(self, event):
		nbCustomizedLabels = len(self.roleLabels)
		if not nbCustomizedLabels:
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("You have no customized role labels."))
			return
		res = gui.messageBox(
			_("You have %d customized role labels defined. Do you want to reset all labels?") % nbCustomizedLabels,
			_("Reset role labels"),
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES:
			self.roleLabels = {}
			config.conf["brailleExtender"]["roleLabels"] = {}
			self.onCategories(None)

	def getOriginalLabel(self, idCategory, idLabel, defaultValue = ''):
		if "%s:%s" % (idCategory, idLabel) in configBE.backupRoleLabels.keys():
			return configBE.backupRoleLabels["%s:%s" % (idCategory, idLabel)][1]
		else: return self.getLabelFromID(idCategory, idLabel)
		return defaultValue

	@staticmethod
	def getIDFromIndexes(idCategory, idLabel):
		try:
			if idCategory == 0: return list(braille.roleLabels.keys())[idLabel]
			elif idCategory == 1: return list(braille.landmarkLabels.keys())[idLabel]
			elif idCategory == 2: return list(braille.positiveStateLabels.keys())[idLabel]
			elif idCategory == 3: return list(braille.negativeStateLabels.keys())[idLabel]
			else: raise ValueError("Invalid value for ID category: %d" % idCategory)
		except BaseException: return -1

	def getLabelFromID(self, idCategory, idLabel):
		if idCategory == 0: return braille.roleLabels[idLabel]
		elif idCategory == 1: return braille.landmarkLabels[idLabel]
		elif idCategory == 2: return braille.positiveStateLabels[idLabel]
		elif idCategory == 3: return braille.negativeStateLabels[idLabel]
		else: raise ValueError("Invalid value: %d" % idCategory)

	def postInit(self): self.toggleRoleLabels.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["features"]["roleLabels"] = self.toggleRoleLabels.IsChecked()
		config.conf["brailleExtender"]["roleLabels"] = self.roleLabels
		configBE.discardRoleLabels()
		if config.conf["brailleExtender"]["features"]["roleLabels"]:
			configBE.loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())


class QuickLaunchesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = _("Braille Extender - Quick launches")
	quickLaunchGestures = []
	quickLaunchLocations = []
	captureEnabled = False
	captureLabelBtn = None

	def makeSettings(self, settingsSizer):
		self.quickLaunchGestures = list(config.conf["brailleExtender"]["quickLaunches"].copy().keys())
		self.quickLaunchLocations = list(config.conf["brailleExtender"]["quickLaunches"].copy().values())
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.quickKeys = sHelper.addLabeledControl(_("&Gestures:"), wx.Choice, choices=self.getQuickLaunchList())
		self.quickKeys.SetSelection(0)
		self.quickKeys.Bind(wx.EVT_CHOICE, self.onQuickKeys)
		self.target = sHelper.addLabeledControl(_("&Location (file path, URL or command)"), wx.TextCtrl, value=self.quickLaunchLocations[0] if self.quickLaunchLocations != [] else '')
		self.target.Bind(wx.EVT_TEXT, self.onTarget)
		self.browseBtn = bHelper1.addButton(self, wx.NewId(), _("&Browse..."), wx.DefaultPosition)
		self.removeGestureBtn = bHelper1.addButton(self, wx.NewId(), _("&Remove this gesture"), wx.DefaultPosition)
		self.addGestureBtn = bHelper1.addButton(self, wx.NewId(), _("&Add a quick launch"), wx.DefaultPosition)
		self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowseBtn)
		self.removeGestureBtn.Bind(wx.EVT_BUTTON, self.onRemoveGestureBtn)
		self.addGestureBtn.Bind(wx.EVT_BUTTON, self.onAddGestureBtn)
		sHelper.addItem(bHelper1)

	def postInit(self): self.quickKeys.SetFocus()

	def onOk(self, evt):
		if inputCore.manager._captureFunc:
			inputCore.manager._captureFunc = None
		config.conf["brailleExtender"]["quickLaunches"] = {}
		for gesture, location in zip(self.quickLaunchGestures, self.quickLaunchLocations):
			config.conf["brailleExtender"]["quickLaunches"][gesture] = location
		instanceGP.loadQuickLaunchesGes()
		super().onOk(evt)

	def onCancel(self, evt):
		if inputCore.manager._captureFunc:
			inputCore.manager._captureFunc = None
		super().onCancel(evt)

	def captureNow(self):
		def getCaptured(gesture):
			script = scriptHandler.findScript(gesture)
			if script and hasattr(script, "bypassInputHelp") and script.bypassInputHelp:
				queueHandler.queueFunction(queueHandler.eventQueue, gesture.script, gesture)
				return False
			elif script is not None:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Unable to associate this gesture. Please enter another gesture"))
				return False
			elif gesture.isModifier: return False
			elif gesture.normalizedIdentifiers[0].endswith(":space"):
				inputCore.manager._captureFunc = None
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Out of capture"))
			elif gesture.normalizedIdentifiers[0].startswith("kb") and not gesture.normalizedIdentifiers[0].endswith(":escape"):
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _(f"Please enter a gesture from your {configBE.curBD} braille display. Press space to cancel."))
				return False
			elif not gesture.normalizedIdentifiers[0].endswith(":escape"):
				self.quickLaunchGestures.append(gesture.normalizedIdentifiers[0])
				self.quickLaunchLocations.append('')
				self.quickKeys.SetItems(self.getQuickLaunchList())
				self.quickKeys.SetSelection(len(self.quickLaunchGestures)-1)
				self.onQuickKeys(None)
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("The gesture captured is %s") % utils.beautifulSht(gesture.normalizedIdentifiers[0]))
				inputCore.manager._captureFunc = None
				self.captureEnabled = False
				self.addGestureBtn.SetLabel(self.captureLabelBtn)
				self.target.SetFocus()
			return True
		inputCore.manager._captureFunc = getCaptured

	def getQuickLaunchList(s):
		quickLaunchGesturesKeys = list(s.quickLaunchGestures)
		return ['%s%s: %s' % (utils.beautifulSht(quickLaunchGesturesKeys[i]), punctuationSeparator, v) for i, v in enumerate(s.quickLaunchLocations)]

	def onRemoveGestureBtn(self, event):
		if self.quickKeys.GetSelection() < 0:
			self.askCreateQuickLaunch()
			return
		def askConfirmation():
			choice = gui.messageBox(_("Are you sure you wish to delete this shortcut?"), '%s – %s' % (addonName, _("Remove shortcut")), wx.YES_NO|wx.ICON_QUESTION)
			if choice == wx.YES: confirmed()
		def confirmed():
			i = self.quickKeys.GetSelection()
			g = self.quickLaunchGestures.pop(i)
			self.quickLaunchLocations.pop(i)
			listQuickLaunches = self.getQuickLaunchList()
			self.quickKeys.SetItems(listQuickLaunches)
			if len(listQuickLaunches) > 0: self.quickKeys.SetSelection(i-1 if i > 0 else 0)
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _(f'{g} removed'))
			self.onQuickKeys(None)
		wx.CallAfter(askConfirmation)
		self.quickKeys.SetFocus()

	def onAddGestureBtn(self, event):
		if self.captureEnabled:
			self.captureEnabled = False
			self.addGestureBtn.SetLabel(self.captureLabelBtn)
			return
		self.captureNow()
		queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Please enter the desired gesture for the new quick launch. Press \"space bar\" to cancel"))
		self.captureEnabled=True
		self.captureLabelBtn = self.addGestureBtn.GetLabel()
		self.addGestureBtn.SetLabel(_("Don't add a quick launch"))
		return

	def onTarget(self, event):
		oldS = self.quickKeys.GetSelection()
		if oldS < 0:
			self.target.SetValue('')
			return
		self.quickLaunchLocations[self.quickKeys.GetSelection()] = self.target.GetValue()
		self.quickKeys.SetItems(self.getQuickLaunchList())
		self.quickKeys.SetSelection(oldS)

	def onQuickKeys(self, event):
		if self.quickKeys.GetSelection() < 0:
			self.target.SetValue('')
			return
		if not self.quickKeys.GetStringSelection().strip().startswith(':'):
			self.target.SetValue(self.quickKeys.GetStringSelection().split(': ')[1])
		else: self.target.SetValue('')
		return

	def onBrowseBtn(self, event):
		oldS = self.quickKeys.GetSelection()
		if oldS < 0:
			self.askCreateQuickLaunch()
			return
		dlg = wx.FileDialog(None, _("Choose a file for {0}").format(self.quickLaunchGestures[self.quickKeys.GetSelection()]), "%PROGRAMFILES%", "", "*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return self.quickKeys.SetFocus()
		self.target.SetValue(dlg.GetDirectory() + '\\' + dlg.GetFilename())
		self.quickLaunchLocations[self.quickKeys.GetSelection()] = dlg.GetDirectory() + '\\' + dlg.GetFilename()
		self.quickKeys.SetItems(self.getQuickLaunchList())
		self.quickKeys.SetSelection(oldS)
		dlg.Destroy()
		return self.quickKeys.SetFocus()

	@staticmethod
	def askCreateQuickLaunch():
		gui.messageBox(_("Please create or select a quick launch first"), '%s – %s' % (addonName, _("Error")), wx.OK|wx.ICON_ERROR)

class AddonSettingsDialog(gui.settingsDialogs.MultiCategorySettingsDialog):
	categoryClasses=[
		GeneralDlg,
		AttribraDlg,
		BrailleTablesDlg,
		UndefinedCharsDlg,
		AdvancedInputModeDlg,
		OneHandModeDlg,
		RoleLabelsDlg,
	]

	def __init__(self, parent, initialCategory=None):
		# Translators: title of add-on settings dialog.
		self.title = _("Braille Extender settings")
		super().__init__(parent, initialCategory)

	def makeSettings(self, settingsSizer):
		# Ensure that after the settings dialog is created the name is set correctly
		super().makeSettings(settingsSizer)
		self._doOnCategoryChange()
		global addonSettingsDialogWindowHandle
		addonSettingsDialogWindowHandle = self.GetHandle()

	def _doOnCategoryChange(self):
		global addonSettingsDialogActiveConfigProfile
		addonSettingsDialogActiveConfigProfile = config.conf.profiles[-1].name
		if not addonSettingsDialogActiveConfigProfile:
			# Translators: The profile name for normal configuration
			addonSettingsDialogActiveConfigProfile = _("normal configuration")
		self.SetTitle(self._getDialogTitle())

	def _getDialogTitle(self):
		return "{dialogTitle}: {panelTitle} ({configProfile})".format(
			dialogTitle=self.title,
			panelTitle=self.currentCategory.title,
			configProfile=addonSettingsDialogActiveConfigProfile
		)

	def onCategoryChange(self,evt):
		super().onCategoryChange(evt)
		if evt.Skipped:
			return
		self._doOnCategoryChange()
