# coding: utf-8
# settings.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import glob
import hashlib
import os
import json
import gui
import wx
import re
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

from . import configBE
from . import utils
from .common import *
from . import advancedInputMode
from . import undefinedChars

instanceGP = None
def notImplemented(msg='', style=wx.OK|wx.ICON_INFORMATION):
	if not msg: msg = _("The feature implementation is in progress. Thanks for your patience.")
	gui.messageBox(msg, _("Braille Extender"), wx.OK|wx.ICON_INFORMATION)

class GeneralDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("General")
	bds_k = [k for k, v in configBE.getValidBrailleDisplayPrefered()]
	bds_v = [v for k, v in configBE.getValidBrailleDisplayPrefered()]

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		self.autoCheckUpdate = sHelper.addItem(wx.CheckBox(self, label=_("Check for &updates automatically")))
		self.autoCheckUpdate.SetValue(config.conf["brailleExtender"]["autoCheckUpdate"])

		# Translators: label of a dialog.
		self.updateChannel = sHelper.addLabeledControl(_("Add-on update channel"), wx.Choice, choices=list(configBE.updateChannels.values()))
		if config.conf["brailleExtender"]["updateChannel"] in configBE.updateChannels.keys():
			itemToSelect = list(configBE.updateChannels.keys()).index(config.conf["brailleExtender"]["updateChannel"])
		else: itemToSelect = list(config.conf["brailleExtender"]["updateChannel"]).index(configBE.CHANNEL_stable)
		self.updateChannel.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.speakScroll = sHelper.addLabeledControl(_("Say current line while scrolling in"), wx.Choice, choices=list(configBE.focusOrReviewChoices.values()))
		self.speakScroll.SetSelection(list(configBE.focusOrReviewChoices.keys()).index(config.conf["brailleExtender"]["speakScroll"]))

		# Translators: label of a dialog.
		self.stopSpeechScroll = sHelper.addItem(wx.CheckBox(self, label=_("Speech interrupt when scrolling on same line")))
		self.stopSpeechScroll.SetValue(config.conf["brailleExtender"]["stopSpeechScroll"])

		# Translators: label of a dialog.
		self.stopSpeechUnknown = sHelper.addItem(wx.CheckBox(self, label=_("Speech interrupt for unknown gestures")))
		self.stopSpeechUnknown.SetValue(config.conf["brailleExtender"]["stopSpeechUnknown"])

		# Translators: label of a dialog.
		self.speakRoutingTo = sHelper.addItem(wx.CheckBox(self, label=_("Announce the character while moving with routing buttons")))
		self.speakRoutingTo.SetValue(config.conf["brailleExtender"]["speakRoutingTo"])

		# Translators: label of a dialog.
		self.routingReviewModeWithCursorKeys = sHelper.addItem(wx.CheckBox(self, label=_("Use cursor keys to route cursor in review mode")))
		self.routingReviewModeWithCursorKeys.SetValue(config.conf["brailleExtender"]["routingReviewModeWithCursorKeys"])

		# Translators: label of a dialog.
		self.hourDynamic = sHelper.addItem(wx.CheckBox(self, label=_("Display time and date infinitely")))
		self.hourDynamic.SetValue(config.conf["brailleExtender"]["hourDynamic"])
		self.reviewModeTerminal = sHelper.addItem(wx.CheckBox(self, label=_("Automatic review mode for apps with terminal")+" (cmd, bash, PuTTY, PowerShell Maxima…)"))
		self.reviewModeTerminal.SetValue(config.conf["brailleExtender"]["reviewModeTerminal"])

		# Translators: label of a dialog.
		self.volumeChangeFeedback = sHelper.addLabeledControl(_("Feedback for volume change in"), wx.Choice, choices=list(configBE.outputMessage.values()))
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in configBE.outputMessage:
			itemToSelect = list(configBE.outputMessage.keys()).index(config.conf["brailleExtender"]["volumeChangeFeedback"])
		else:
			itemToSelect = list(configBE.outputMessage.keys()).index(configBE.CHOICE_braille)
		self.volumeChangeFeedback.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.modifierKeysFeedback = sHelper.addLabeledControl(_("Feedback for modifier keys in"), wx.Choice, choices=list(configBE.outputMessage.values()))
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in configBE.outputMessage:
			itemToSelect = list(configBE.outputMessage.keys()).index(config.conf["brailleExtender"]["modifierKeysFeedback"])
		else:
			itemToSelect = list(configBE.outputMessage.keys()).index(configBE.CHOICE_braille)
		# Translators: label of a dialog.
		self.beepsModifiers = sHelper.addItem(wx.CheckBox(self, label=_("Play beeps for modifier keys")))
		self.beepsModifiers.SetValue(config.conf["brailleExtender"]["beepsModifiers"])

		# Translators: label of a dialog.
		self.modifierKeysFeedback.SetSelection(itemToSelect)
		self.rightMarginCells = sHelper.addLabeledControl(_("Right margin on cells")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=int(config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD]))
		if configBE.gesturesFileExists:
			lb = [k for k in instanceGP.getKeyboardLayouts()]
			# Translators: label of a dialog.
			self.KBMode = sHelper.addLabeledControl(_("Braille keyboard configuration"), wx.Choice, choices=lb)
			self.KBMode.SetSelection(configBE.getKeyboardLayout())

		# Translators: label of a dialog.
		self.reverseScrollBtns = sHelper.addItem(wx.CheckBox(self, label=_("Reverse forward scroll and back scroll buttons")))
		self.reverseScrollBtns.SetValue(config.conf["brailleExtender"]["reverseScrollBtns"])

		# Translators: label of a dialog.
		self.autoScrollDelay = sHelper.addLabeledControl(_("Autoscroll delay (ms)")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=125, max=42000, initial=int(config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD]))
		self.brailleDisplay1 = sHelper.addLabeledControl(_("First braille display preferred"), wx.Choice, choices=self.bds_v)
		self.brailleDisplay1.SetSelection(self.bds_k.index(config.conf["brailleExtender"]["brailleDisplay1"]))
		self.brailleDisplay2 = sHelper.addLabeledControl(_("Second braille display preferred"), wx.Choice, choices=self.bds_v)
		self.brailleDisplay2.SetSelection(self.bds_k.index(config.conf["brailleExtender"]["brailleDisplay2"]))
		self.oneHandMode = sHelper.addItem(wx.CheckBox(self, label=_("One-handed mode")))
		self.oneHandMode.SetValue(config.conf["brailleExtender"]["oneHandMode"])
		choices = list(configBE.CHOICE_oneHandMethods.values())
		itemToSelect = list(configBE.CHOICE_oneHandMethods.keys()).index(config.conf["brailleExtender"]["oneHandMethod"])
		self.oneHandMethod = sHelper.addLabeledControl(_("One hand mode method"), wx.Choice, choices=choices)
		self.oneHandMethod.SetSelection(itemToSelect)

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
		config.conf["brailleExtender"]["oneHandMode"] = self.oneHandMode.IsChecked()
		config.conf["brailleExtender"]["oneHandMethod"] = list(configBE.CHOICE_oneHandMethods.keys())[self.oneHandMethod.GetSelection()]

class AttribraDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Text attributes")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleAttribra = sHelper.addItem(wx.CheckBox(self, label=_("Enable this feature")))
		self.toggleAttribra.SetValue(config.conf["brailleExtender"]["features"]["attributes"])
		self.spellingErrorsAttribute = sHelper.addLabeledControl(_("Show spelling errors with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.spellingErrorsAttribute.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.boldAttribute = sHelper.addLabeledControl(_("Show bold with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.boldAttribute.SetSelection(self.getItemToSelect("bold"))
		self.italicAttribute = sHelper.addLabeledControl(_("Show italic with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.italicAttribute.SetSelection(self.getItemToSelect("italic"))
		self.underlineAttribute = sHelper.addLabeledControl(_("Show underline with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.underlineAttribute.SetSelection(self.getItemToSelect("underline"))
		self.strikethroughAttribute = sHelper.addLabeledControl(_("Show strikethrough with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.strikethroughAttribute.SetSelection(self.getItemToSelect("strikethrough"))
		self.subAttribute = sHelper.addLabeledControl(_("Show subscript with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.subAttribute.SetSelection(self.getItemToSelect("text-position:sub"))
		self.superAttribute = sHelper.addLabeledControl(_("Show superscript with"), wx.Choice, choices=configBE.attributeChoicesValues)
		self.superAttribute.SetSelection(self.getItemToSelect("text-position:super"))

	def postInit(self): self.toggleAttribra.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["features"]["attributes"] = self.toggleAttribra.IsChecked()
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
		self.toggleRoleLabels = sHelper.addItem(wx.CheckBox(self, label=_("Enable this feature")))
		self.toggleRoleLabels.SetValue(config.conf["brailleExtender"]["features"]["roleLabels"])
		self.categories = sHelper.addLabeledControl(_("Role category"), wx.Choice, choices=[_("General"), _("Landmark"), _("Positive state"), _("Negative state")])
		self.categories.Bind(wx.EVT_CHOICE, self.onCategories)
		self.categories.SetSelection(0)
		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		self.labels = sHelper2.addLabeledControl(_("Role"), wx.Choice, choices=[controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()])
		self.labels.Bind(wx.EVT_CHOICE, self.onLabels)
		self.label = sHelper2.addLabeledControl(_("Actual or new label"), wx.TextCtrl)
		self.label.Bind(wx.EVT_TEXT, self.onLabel)
		sHelper.addItem(sHelper2)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.resetLabelBtn = bHelper.addButton(self, wx.NewId(), "%s..." % _("&Reset this role label"), wx.DefaultPosition)
		self.resetLabelBtn.Bind(wx.EVT_BUTTON, self.onResetLabelBtn)
		self.resetAllLabelsBtn = bHelper.addButton(self, wx.NewId(), "%s..." % _("Reset all role labels"), wx.DefaultPosition)
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
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("You have no customized label."))
			return
		res = gui.messageBox(
			_("Do you want really reset all labels? Currently, you have %d customized labels.") % nbCustomizedLabels,
			_("Confirmation"),
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

class BrailleTablesDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Braille tables")

	def makeSettings(self, settingsSizer):
		self.oTables = set(configBE.outputTables)
		self.iTables = set(configBE.inputTables)
		lt = [_("Use the current input table")]
		for table in configBE.tables:
			if table.output and not table.contracted: lt.append(table[1])
			if config.conf["brailleExtender"]["inputTableShortcuts"] in configBE.tablesUFN:
				iSht = configBE.tablesUFN.index(config.conf["brailleExtender"]["inputTableShortcuts"]) + 1
			else: iSht = 0
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		self.tables = sHelper.addLabeledControl(_("Prefered braille tables")+" (%s)" % _("press F1 for help"), wx.Choice, choices=self.getTablesWithSwitches())
		self.tables.SetSelection(0)
		self.tables.Bind(wx.EVT_CHAR, self.onTables)

		self.inputTableShortcuts = sHelper.addLabeledControl(_("Input braille table for keyboard shortcut keys"), wx.Choice, choices=lt)
		self.inputTableShortcuts.SetSelection(iSht)
		lt = [_('None')]
		for table in configBE.tables:
			if table.output: lt.append(table[1])
		self.postTable = sHelper.addLabeledControl(_("Secondary output table to use"), wx.Choice, choices=lt)
		self.postTable.SetSelection(configBE.tablesFN.index(config.conf["brailleExtender"]["postTable"]) if config.conf["brailleExtender"]["postTable"] in configBE.tablesFN else 0)

		# Translators: label of a dialog.
		self.tabSpace = sHelper.addItem(wx.CheckBox(self, label=_("Display &tab signs as spaces")))
		self.tabSpace.SetValue(config.conf["brailleExtender"]["tabSpace"])

		# Translators: label of a dialog.
		self.tabSize = sHelper.addLabeledControl(_("Number of &space for a tab sign")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=1, max=42, initial=int(config.conf["brailleExtender"]["tabSize_%s" % configBE.curBD]))
		self.customBrailleTablesBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("Alternative and &custom braille tables"), wx.DefaultPosition)
		self.customBrailleTablesBtn.Bind(wx.EVT_BUTTON, self.onCustomBrailleTablesBtn)
		sHelper.addItem(bHelper1)

	def postInit(self): self.tables.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["outputTables"] = ','.join(self.oTables)
		config.conf["brailleExtender"]["inputTables"] = ','.join(self.iTables)
		config.conf["brailleExtender"]["inputTableShortcuts"] = configBE.tablesUFN[self.inputTableShortcuts.GetSelection()-1] if self.inputTableShortcuts.GetSelection()>0 else '?'
		postTableID = self.postTable.GetSelection()
		postTable = "None" if postTableID == 0 else configBE.tablesFN[postTableID]
		config.conf["brailleExtender"]["postTable"] = postTable
		if self.tabSpace.IsChecked() and config.conf["brailleExtender"]["tabSpace"] != self.tabSpace.IsChecked():
			restartRequired = True
		else: restartRequired = False
		config.conf["brailleExtender"]["tabSpace"] = self.tabSpace.IsChecked()
		config.conf["brailleExtender"]["tabSize_%s" % configBE.curBD] = self.tabSize.Value
		if restartRequired:
			res = gui.messageBox(
				_("NVDA must be restarted for some new options to take effect. Do you want restart now?"),
				_("Braille Extender"),
				style=wx.YES_NO|wx.ICON_INFORMATION
			)
			if res == wx.YES: core.restart()

	def getTablesWithSwitches(self):
		out = []
		for i, tbl in enumerate(configBE.tablesTR):
			out.append("%s%s: %s" % (tbl, punctuationSeparator, self.getInSwitchesText(configBE.tablesFN[i])))
		return out

	def getCurrentSelection(self):
		idx = self.tables.GetSelection()
		tbl = configBE.tablesFN[self.tables.GetSelection()]
		return idx, tbl

	def setCurrentSelection(self, tbl, newLoc):
		if newLoc == "io":
			self.iTables.add(tbl)
			self.oTables.add(tbl)
		elif newLoc == "i":
			self.iTables.add(tbl)
			self.oTables.discard(tbl)
		elif newLoc == "o":
			self.oTables.add(tbl)
			self.iTables.discard(tbl)
		elif newLoc == "n":
			self.iTables.discard(tbl)
			self.oTables.discard(tbl)

	def inSwitches(self, tbl):
		inp = tbl in self.iTables
		out = tbl in self.oTables
		return [inp, out]

	def getInSwitchesText(self, tbl):
		inS = self.inSwitches(tbl)
		if all(inS): inSt = _("input and output")
		elif not any(inS): inSt = _("none")
		elif inS[0]: inSt = _("input only")
		elif inS[1]: inSt = _("output only")
		return inSt

	def changeSwitch(self, tbl, direction=1, loop=True):
		dirs = ['n', 'i', 'o', "io"]
		iCurDir = 0
		inS = self.inSwitches(tbl)
		if all(inS): iCurDir = dirs.index("io")
		elif not any(inS): iCurDir = dirs.index('n')
		elif inS[0]: iCurDir = dirs.index('i')
		elif inS[1]: iCurDir = dirs.index('o')

		if len(dirs)-1 == iCurDir and direction == 1 and loop: newDir = dirs[0]
		elif iCurDir == 0 and direction == 0 and loop: newDir = dirs[-1]
		elif iCurDir < len(dirs)-1 and direction == 1: newDir = dirs[iCurDir+1]
		elif iCurDir > 0 and iCurDir < len(dirs) and direction == 0: newDir = dirs[iCurDir-1]
		else: return
		self.setCurrentSelection(tbl, newDir)

	def onCustomBrailleTablesBtn(self, evt):
		customBrailleTablesDlg = CustomBrailleTablesDlg(self, multiInstanceAllowed=True)
		customBrailleTablesDlg.ShowModal()

	def onTables(self, evt):
		keycode = evt.GetKeyCode()
		if keycode in [ord(','), ord(';')]:
			idx, tbl = self.getCurrentSelection()
			if keycode == ord(','):
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "%s" % tbl)
			else:
				ui.browseableMessage('\n'.join([
					_("Table name: %s") % configBE.tablesTR[idx],
					_("File name: %s") % tbl,
					_("In switches: %s") % self.getInSwitchesText(tbl)
					]), _("About this table"), False)
		if keycode == wx.WXK_F1:
			ui.browseableMessage(
				_("In this combo box, all tables are present. Press space bar, left or right arrow keys to include (or not) the selected table in switches")+".\n"+
			_("You can also press 'comma' key to get the file name of the selected table and 'semicolon' key to view miscellaneous infos on the selected table")+".",
			_("Contextual help"), False)
		if keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_SPACE]:
			idx, tbl = self.getCurrentSelection()
			if keycode == wx.WXK_LEFT: self.changeSwitch(tbl, 0, False)
			elif keycode == wx.WXK_RIGHT: self.changeSwitch(tbl, 1, False)
			elif keycode == wx.WXK_SPACE: self.changeSwitch(tbl, 1, True)
			newSwitch = self.getInSwitchesText(tbl)
			self.tables.SetString(self.tables.GetSelection(), "%s%s: %s" % (configBE.tablesTR[idx], punctuationSeparator, newSwitch))
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, "%s" % newSwitch)
			utils.refreshBD()
		else: evt.Skip()


class CustomBrailleTablesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Custom braille tables")
	providedTablesPath = "%s/res/brailleTables.json" % configBE.baseDir
	userTablesPath = "%s/brailleTables.json" % configBE.configDir

	def makeSettings(self, settingsSizer):
		self.providedTables = self.getBrailleTablesFromJSON(self.providedTablesPath)
		self.userTables = self.getBrailleTablesFromJSON(self.userTablesPath)
		wx.CallAfter(notImplemented)
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.inTable = sHelper.addItem(wx.CheckBox(self, label=_("Use a custom table as input table")))
		self.outTable = sHelper.addItem(wx.CheckBox(self, label=_("Use a custom table as output table")))
		self.addBrailleTablesBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("&Add a braille table"), wx.DefaultPosition)
		self.addBrailleTablesBtn.Bind(wx.EVT_BUTTON, self.onAddBrailleTablesBtn)
		sHelper.addItem(bHelper1)

	@staticmethod
	def getBrailleTablesFromJSON(path):
		if not os.path.exists(path):
			path = "%s/%s" % (configBE.baseDir, path)
			if not os.path.exists(path): return {}
		f = open(path, "r")
		return json.load(f)

	def onAddBrailleTablesBtn(self, evt):
		addBrailleTablesDlg = AddBrailleTablesDlg(self, multiInstanceAllowed=True)
		addBrailleTablesDlg.ShowModal()

	def postInit(self): self.inTable.SetFocus()

	def onOk(self, event):
		super(CustomBrailleTablesDlg, self).onOk(evt)


class AddBrailleTablesDlg(gui.settingsDialogs.SettingsDialog):
	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Add a braille table")
	tbl = []

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.name = sHelper.addLabeledControl(_("Display name"), wx.TextCtrl)
		self.description = sHelper.addLabeledControl(_("Description"), wx.TextCtrl, style = wx.TE_MULTILINE|wx.TE_PROCESS_ENTER, size = (360, 90), pos=(-1,-1))
		self.path = sHelper.addLabeledControl(_("Path"), wx.TextCtrl)
		self.browseBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("&Browse"), wx.DefaultPosition)
		self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowseBtn)
		sHelper.addItem(bHelper1)
		self.isContracted = sHelper.addItem(wx.CheckBox(self, label=_("Contracted (grade 2) braille table")))
		# Translators: label of a dialog.
		self.inputOrOutput = sHelper.addLabeledControl(_("Available for"), wx.Choice, choices=[_("Input and output"), _("Input only"), _("Output only")])
		self.inputOrOutput.SetSelection(0)

	def postInit(self): self.name.SetFocus()

	def onBrowseBtn(self, event):
		dlg = wx.FileDialog(None, _("Choose a table file"), "%PROGRAMFILES%", "", "%s (*.ctb, *.cti, *.utb, *.uti)|*.ctb;*.cti;*.utb;*.uti" % _("Liblouis table files"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return self.path.SetFocus()
		self.path.SetValue(dlg.GetDirectory() + '\\' + dlg.GetFilename())
		dlg.Destroy()
		self.path.SetFocus()

	def onOk(self, event):
		path = self.path.GetValue().strip().encode("UTF-8")
		displayName = self.name.GetValue().strip()
		if not displayName:
			gui.messageBox(_("Please specify a display name."), _("Invalid display name"), wx.OK|wx.ICON_ERROR)
			self.name.SetFocus()
			return
		if not os.path.exists(path.decode("UTF-8").encode("mbcs")):
			gui.messageBox(_("The specified path is not valid (%s).") % path.decode("UTF-8"), _("Invalid path"), wx.OK|wx.ICON_ERROR)
			self.path.SetFocus()
			return
		switch_possibleValues = ["both", "input", "output"]
		v = "%s|%s|%s|%s" % (
			switch_possibleValues[self.inputOrOutput.GetSelection()],
			self.isContracted.IsChecked(), path.decode("UTF-8"), displayName
		)
		k = hashlib.md5(path).hexdigest()[:15]
		config.conf["brailleExtender"]["brailleTables"][k] = v
		super(AddBrailleTablesDlg, self).onOk(evt)

	@staticmethod
	def getAvailableBrailleTables():
		out = []
		brailleTablesDir = configBE.brailleTables.TABLES_DIR
		ls = glob.glob(brailleTablesDir+'\\*.ctb')+glob.glob(brailleTablesDir+'\\*.cti')+glob.glob(brailleTablesDir+'\\*.utb')
		for i, e in enumerate(ls):
			e = str(e.split('\\')[-1])
			if e in configBE.tablesFN or e.lower() in configBE.tablesFN: del ls[i]
			else: out.append(e.lower())
		out = sorted(out)
		return out


class QuickLaunchesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Quick launches")
	quickLaunchGestures = []
	quickLaunchLocations = []
	captureEnabled = False
	captureLabelBtn = None

	def makeSettings(self, settingsSizer):
		self.quickLaunchGestures = list(config.conf["brailleExtender"]["quickLaunches"].copy().keys())
		self.quickLaunchLocations = list(config.conf["brailleExtender"]["quickLaunches"].copy().values())
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.quickKeys = sHelper.addLabeledControl(_("&Gestures"), wx.Choice, choices=self.getQuickLaunchList())
		self.quickKeys.SetSelection(0)
		self.quickKeys.Bind(wx.EVT_CHOICE, self.onQuickKeys)
		self.target = sHelper.addLabeledControl(_("Location (file path, URL or command)"), wx.TextCtrl, value=self.quickLaunchLocations[0] if self.quickLaunchLocations != [] else '')
		self.target.Bind(wx.EVT_TEXT, self.onTarget)
		self.browseBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("&Browse"), wx.DefaultPosition)
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
		super(QuickLaunchesDlg, self).onOk(evt)

	def onCancel(self, evt):
		if inputCore.manager._captureFunc:
			inputCore.manager._captureFunc = None
		super(QuickLaunchesDlg, self).onCancel(evt)

	def captureNow(self):
		def getCaptured(gesture):
			script = scriptHandler.findScript(gesture)
			if script and hasattr(script, "bypassInputHelp") and script.bypassInputHelp:
				queueHandler.queueFunction(queueHandler.eventQueue, gesture.script, gesture)
				return False
			elif script is not None:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Unable to associate this gesture. Please enter another, now"))
				return False
			elif gesture.isModifier: return False
			elif gesture.normalizedIdentifiers[0].endswith(":space"):
				inputCore.manager._captureFunc = None
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Out of capture"))
			elif gesture.normalizedIdentifiers[0].startswith("kb") and not gesture.normalizedIdentifiers[0].endswith(":escape"):
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Please enter a gesture from your {NAME_BRAILLE_DISPLAY} braille display. Press space to cancel.".format(NAME_BRAILLE_DISPLAY=configBE.curBD)))
				return False
			elif not gesture.normalizedIdentifiers[0].endswith(":escape"):
				self.quickLaunchGestures.append(gesture.normalizedIdentifiers[0])
				self.quickLaunchLocations.append('')
				self.quickKeys.SetItems(self.getQuickLaunchList())
				self.quickKeys.SetSelection(len(self.quickLaunchGestures)-1)
				self.onQuickKeys(None)
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("OK. The gesture captured is %s") % utils.beautifulSht(gesture.normalizedIdentifiers[0]))
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
			choice = gui.messageBox(_("Are you sure to want to delete this shorcut?"), '%s – %s' % (addonName, _("Confirmation")), wx.YES_NO|wx.ICON_QUESTION)
			if choice == wx.YES: confirmed()
		def confirmed():
			i = self.quickKeys.GetSelection()
			g = self.quickLaunchGestures.pop(i)
			self.quickLaunchLocations.pop(i)
			listQuickLaunches = self.getQuickLaunchList()
			self.quickKeys.SetItems(listQuickLaunches)
			if len(listQuickLaunches) > 0: self.quickKeys.SetSelection(i-1 if i > 0 else 0)
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('{BRAILLEGESTURE} removed'.format(BRAILLEGESTURE=g)))
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


class ProfileEditorDlg(gui.settingsDialogs.SettingsDialog):
	title = "Braille Extender - %s" % _("Profiles editor")
	profilesList = []
	addonGesturesPrfofile = {}
	generalGesturesProfile = {}
	keyLabelsList = sorted([(t[1], t[0]) for t in keyLabels.localizedKeyLabels.items()])+[('f%d' %i, 'f%d' %i) for i in range(1, 13)]

	def makeSettings(self, settingsSizer):
		global profilesDir
		wx.CallAfter(notImplemented)
		if configBE.curBD == 'noBraille':
			self.Destroy()
			wx.CallAfter(gui.messageBox, _("You must have a braille display to editing a profile"), self.title, wx.OK|wx.ICON_ERROR)

		if not os.path.exists(profilesDir):
			self.Destroy()
			wx.CallAfter(gui.messageBox, _("Profiles directory is not present or accessible. Unable to edit profiles"), self.title, wx.OK|wx.ICON_ERROR)

		self.profilesList = self.getListProfiles()

		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		labelText = _("Profile to edit")
		self.profiles = sHelper.addLabeledControl(labelText, wx.Choice, choices=self.profilesList)
		self.profiles.SetSelection(0)
		self.profiles.Bind(wx.EVT_CHOICE, self.onProfiles)

		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		labelText = _('Gestures category')
		categoriesList = [_("Single keys"), _("Modifier keys"), _("Practical shortcuts"), _("NVDA commands"), _("Addon features")]
		self.categories = sHelper2.addLabeledControl(labelText, wx.Choice, choices=categoriesList)
		self.categories.SetSelection(0)
		self.categories.Bind(wx.EVT_CHOICE, self.refreshGestures)
		labelText = _('Gestures list')
		self.gestures = sHelper2.addLabeledControl(labelText, wx.Choice, choices=[])
		self.gestures.Bind(wx.EVT_CHOICE, self.onGesture)

		sHelper.addItem(sHelper2)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		addGestureButtonID = wx.NewId()
		self.addGestureButton = bHelper.addButton(self, addGestureButtonID, _("Add gesture"), wx.DefaultPosition)

		self.removeGestureButton = bHelper.addButton(self, addGestureButtonID, _("Remove this gesture"), wx.DefaultPosition)

		assignGestureButtonID = wx.NewId()
		self.assignGestureButton = bHelper.addButton(self, assignGestureButtonID, _("Assign a braille gesture"), wx.DefaultPosition)

		sHelper.addItem(bHelper)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		removeProfileButtonID = wx.NewId()
		self.removeProfileButton = bHelper.addButton(self, removeProfileButtonID, _("Remove this profile"), wx.DefaultPosition)

		addProfileButtonID = wx.NewId()
		self.addProfileButton = bHelper.addButton(self, addProfileButtonID, _("Add a profile"), wx.DefaultPosition)
		self.addProfileButton.Bind(wx.EVT_BUTTON, self.onAddProfileButton)

		sHelper.addItem(bHelper)

		edHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		labelText = _('Name for the new profile')
		self.newProfileName = edHelper.addLabeledControl(labelText, wx.TextCtrl)
		sHelper.addItem(edHelper)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		validNewProfileNameButtonID = wx.NewId()
		self.validNewProfileNameButton = bHelper.addButton(self, validNewProfileNameButtonID, _('Create'))

		sHelper.addItem(bHelper)

	def postInit(self):
		self.onProfiles()
		self.hideNewProfileSection()
		self.refreshGestures()
		if len(self.profilesList)>0:
			self.profiles.SetSelection(self.profilesList.index(config.conf["brailleExtender"]["profile_%s" % configBE.curBD]))
		self.onProfiles()
		self.refreshGestures()
		self.profiles.SetFocus()

	def refreshGestures(self, evt=None):
		category = self.categories.GetSelection()
		items = []
		ALT = keyLabels.localizedKeyLabels['alt'].capitalize()
		CTRL = keyLabels.localizedKeyLabels['control'].capitalize()
		SHIFT = keyLabels.localizedKeyLabels['shift'].capitalize()
		WIN = keyLabels.localizedKeyLabels['windows'].capitalize()
		if category == 0: items = ["%s%s: %s" % (k[0].capitalize(), punctuationSeparator, self.getBrailleGesture(k[1])) for k in self.keyLabelsList]
		elif category == 1:
			items = [ALT, CTRL, SHIFT, WIN, "NVDA",
			'%s+%s' % (ALT, CTRL),
			'%s+%s' % (ALT, SHIFT),
			'%s+%s' % (ALT, WIN),
			'%s+%s+%s' % (ALT, CTRL, SHIFT),
			'%s+%s+%s+%s' % (ALT, CTRL, SHIFT, WIN),
			'%s+%s+%s' % (ALT, CTRL, WIN),
			'%s+%s' % (CTRL, SHIFT),
			'%s+%s' % (CTRL, WIN),
				'%s+%s+%s' % (CTRL, SHIFT, WIN),
			'%s+%s' % (SHIFT, WIN)
			]
		elif category == 2:
			items = sorted([
				'%s+F4' % ALT,
				'%s+Tab' % ALT,
				'%s+Tab' % SHIFT,
			])
		self.gestures.SetItems(["%s%s: %s" % (item, punctuationSeparator, self.getBrailleGesture("kb:%s" % item)) for item in items])
		self.gestures.SetSelection(0)
		self.gestures.SetSelection(0)
		if category<2:
			self.addGestureButton.Disable()
			self.removeGestureButton.Disable()
		else:
			self.addGestureButton.Enable()
			self.removeGestureButton.Enable()

	def onProfiles(self, evt=None):
		global profilesDir
		if len(self.profilesList) == 0:
			log.info("No profile found for this braille display")
			return
		curProfile = self.profilesList[self.profiles.GetSelection()]
		log.info("Loading %s profile (%s)" % (curProfile, profilesDir))
		gestureProfileDir = os.path.join(profilesDir, curProfile, "profile.ini")
		self.addonGesturesPrfofile = config.ConfigObj(gestureProfileDir, encoding="UTF-8")
		self.generalGesturesProfile = config.ConfigObj(os.path.join(profilesDir, configBE.curBD, curProfile, "gestures.ini"), encoding="UTF-8")
		if self.addonGesturesPrfofile == {}:
			log.info(gestureProfileDir)
			wx.CallAfter(gui.messageBox, _("Unable to load this profile. Malformed or inaccessible file"), self.title, wx.OK|wx.ICON_ERROR)

	@staticmethod
	def getListProfiles():
		global profilesDir
		profilesDir = os.path.join(profilesDir, configBE.curBD)
		res = []
		ls = glob.glob(profilesDir+'\\*')
		for e in ls:
			if os.path.isdir(e) and os.path.exists(os.path.join(e, "profile.ini")): res.append(e.split('\\')[-1])
		return res

	def switchProfile(self, evt=None):
		self.refreshGestures()

	def getBrailleGesture(self, KBGesture):
		if ("globalCommands.GlobalCommands" in self.generalGesturesProfile.keys()
			and "kb:%s" % KBGesture in self.generalGesturesProfile["globalCommands.GlobalCommands"].keys()):
			return utils.beautifulSht(self.generalGesturesProfile["globalCommands.GlobalCommands"]["kb:%s" % KBGesture])
		return _("Undefined")

	def onGesture(self, evt=None):
		gesture = self.gestures.GetSelection()
		gestureName = self.keyLabelsList[gesture][1]

	def onAddProfileButton(self, evt=None):
		if not self.addProfileButton.IsEnabled():
			self.hideNewProfileSection()
			self.addProfileButton.Enable()
		else:
			self.newProfileName.Enable()
			self.validNewProfileNameButton.Enable()
			self.addProfileButton.Disable()

	def hideNewProfileSection(self, evt=None):
		self.validNewProfileNameButton.Disable()
		self.newProfileName.Disable()

class AddonSettingsDialog(gui.settingsDialogs.MultiCategorySettingsDialog):
	categoryClasses=[
		GeneralDlg,
		AttribraDlg,
		BrailleTablesDlg,
		undefinedChars.SettingsDlg,
		advancedInputMode.SettingsDlg,
		RoleLabelsDlg,
	]

	def __init__(self, parent, initialCategory=None):
		# Translators: title of add-on parameters dialog.
		dialogTitle = _("Settings")
		self.title = "%s - %s" % (addonSummary, dialogTitle)
		super(AddonSettingsDialog,self).__init__(parent, initialCategory)
