# coding: utf-8
# addonSettingsPanel.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import gui
import wx
import addonHandler
import braille
import config
import controlTypes
addonHandler.initTranslation()

import configBE
from logHandler import log

instanceGP = None

def inputTablesNotInSwitch():
	if configBE.inputTables != None:
		return [table[1] for table in configBE.tables if table.input and table[0] not in configBE.inputTables]
	return []

def inputTablesInSwitch():
	if configBE.inputTables != None:
		return [configBE.tablesTR[configBE.tablesFN.index(table)] for table in configBE.inputTables if table.strip() != '']
	return []

def outputTablesNotInSwitch():
	if configBE.outputTables != None:
		return [table[1] for table in configBE.tables if table.output and table[0] not in configBE.outputTables]
	return []

def outputTablesInSwitch():
	if configBE.outputTables != None:
		return [configBE.tablesTR[configBE.tablesFN.index(table)] for table in configBE.outputTables if table != ''] 
	return []

class AddonSettingsPanel(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = "Braille Extender (%s)" % _("%s configuration" % configBE.curBD)

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper2 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.generalBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("&General"), wx.DefaultPosition)
		self.generalBtn.Bind(wx.EVT_BUTTON, self.onGeneralBtn)
		self.preferredBrailleTablesBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _("Prefered braille &tables"), wx.DefaultPosition)
		self.preferredBrailleTablesBtn.Bind(wx.EVT_BUTTON, self.onPreferedBrailleTablesBtn)
		self.attributesBtn = bHelper2.addButton(self, wx.NewId(), "%s..." % _("Text &attributes"), wx.DefaultPosition)
		self.attributesBtn.Bind(wx.EVT_BUTTON, self.onAttributesBtn)
		self.quickLaunchesBtn = bHelper2.addButton(self, wx.NewId(), "%s..." % _("&Quick launches"), wx.DefaultPosition)
		self.quickLaunchesBtn.Bind(wx.EVT_BUTTON, self.onQuickLaunchesBtn)
		self.roleLabelsBtn = bHelper2.addButton(self, wx.NewId(), "%s..." % _("Role &labels"), wx.DefaultPosition)
		self.roleLabelsBtn.Bind(wx.EVT_BUTTON, self.onRoleLabelsBtn)
		sHelper.addItem(bHelper1)
		sHelper.addItem(bHelper2)

	def onSave(self): pass

	def onGeneralBtn(self, evt):
		generalDlg = GeneralDlg(self, multiInstanceAllowed=True)
		generalDlg.ShowModal()

	def onPreferedBrailleTablesBtn(self, evt):
		preferredBrailleTablesDlg = PreferedBrailleTablesDlg(self, multiInstanceAllowed=True)
		preferredBrailleTablesDlg.ShowModal()

	def onAttributesBtn(self, evt):
		attribraDlg = AttribraDlg(self, multiInstanceAllowed=True)
		attribraDlg.ShowModal()

	def onQuickLaunchesBtn(self, evt):
		quickLaunchesDlg = QuickLaunchesDlg(self, multiInstanceAllowed=True)
		quickLaunchesDlg.ShowModal()

	def onRoleLabelsBtn(self, evt):
		roleLabelsDlg = RoleLabelsDlg(self, multiInstanceAllowed=True)
		roleLabelsDlg.ShowModal()

	def postInit(self):
		self.General.SetFocus()


class GeneralDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("General")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		self.autoCheckUpdate = sHelper.addItem(wx.CheckBox(self, label=_("Check for &updates automatically")))
		self.autoCheckUpdate.SetValue(config.conf["brailleExtender"]["autoCheckUpdate"])

		# Translators: label of a dialog.
		self.updateChannel = sHelper.addLabeledControl(_("Add-on update channel"), wx.Choice, choices=configBE.updateChannels.values())
		if config.conf["brailleExtender"]["updateChannel"] in configBE.updateChannels.keys():
			itemToSelect = configBE.updateChannels.keys().index(config.conf["brailleExtender"]["updateChannel"])
		else: itemToSelect = config.conf["brailleExtender"]["updateChannel"].index(configBE.CHANNELSTABLE)
		self.updateChannel.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.speakScroll = sHelper.addLabeledControl(_("Say current line while scrolling in"), wx.Choice, choices=configBE.focusOrReviewChoices.values())
		self.speakScroll.SetSelection(configBE.focusOrReviewChoices.keys().index(config.conf["brailleExtender"]["speakScroll"]))

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
		self.hourDynamic = sHelper.addItem(wx.CheckBox(self, label=_("Display time and date infinitely")))
		self.hourDynamic.SetValue(config.conf["brailleExtender"]["hourDynamic"])

		# Translators: label of a dialog.
		self.volumeChangeFeedback = sHelper.addLabeledControl(_("Feedback for volume change in"), wx.Choice, choices=configBE.outputMessage.values())
		if config.conf["brailleExtender"]["volumeChangeFeedback"] in configBE.outputMessage:
			itemToSelect = configBE.outputMessage.keys().index(config.conf["brailleExtender"]["volumeChangeFeedback"]) 
		else:
			itemToSelect = configBE.outputMessage.keys().index(configBE.CHOICE_braille)
		self.volumeChangeFeedback.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.modifierKeysFeedback = sHelper.addLabeledControl(_("Feedback for modifier keys in"), wx.Choice, choices=configBE.outputMessage.values())
		if config.conf["brailleExtender"]["modifierKeysFeedback"] in configBE.outputMessage:
			itemToSelect = configBE.outputMessage.keys().index(config.conf["brailleExtender"]["modifierKeysFeedback"]) 
		else:
			itemToSelect = configBE.outputMessage.keys().index(configBE.CHOICE_braille)

		# Translators: label of a dialog.
		self.modifierKeysFeedback.SetSelection(itemToSelect)
		self.rightMarginCells = sHelper.addLabeledControl(_("Right margin on cells")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD])

		# Translators: label of a dialog.
		self.reverseScrollBtns = sHelper.addItem(wx.CheckBox(self, label=_("Reverse forward scroll and back scroll buttons")))
		self.reverseScrollBtns.SetValue(config.conf["brailleExtender"]["reverseScrollBtns"])

		# Translators: label of a dialog.
		self.tabSpace = sHelper.addItem(wx.CheckBox(self, label=_("Display tab signs as spaces")))
		self.tabSpace.SetValue(config.conf["brailleExtender"]["tabSpace"])

		# Translators: label of a dialog.
		self.tabSize = sHelper.addLabeledControl(_("Number of space for a tab sign")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=1, max=42, initial=config.conf["brailleExtender"]["tabSize_%s" % configBE.curBD])

		# Translators: label of a dialog.
		self.autoScrollDelay = sHelper.addLabeledControl(_("Autoscroll delay (ms)")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=125, max=42000, initial=config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD])
		self.brailleDisplay1 = sHelper.addLabeledControl(_("First braille display preferred"), wx.Choice, choices=configBE.bds_v)
		self.brailleDisplay1.SetSelection(configBE.bds_k.index(config.conf["brailleExtender"]["brailleDisplay1"]))
		self.brailleDisplay2 = sHelper.addLabeledControl(_("Second braille display preferred"), wx.Choice, choices=configBE.bds_v)
		self.brailleDisplay2.SetSelection(configBE.bds_k.index(config.conf["brailleExtender"]["brailleDisplay2"]))

	def postInit(self):
		self.autoCheckUpdate.SetFocus()

	def onOk(self, evt):
		config.conf["brailleExtender"]["autoCheckUpdate"] = self.autoCheckUpdate.IsChecked()
		config.conf["brailleExtender"]["hourDynamic"] = self.hourDynamic.IsChecked()
		if self.reverseScrollBtns.IsChecked(): instanceGP.reverseScrollBtns()
		else: instanceGP.reverseScrollBtns(None, True)
		config.conf["brailleExtender"]["reverseScrollBtns"] = self.reverseScrollBtns.IsChecked()
		config.conf["brailleExtender"]["tabSpace"] = self.tabSpace.IsChecked()
		config.conf["brailleExtender"]["stopSpeechScroll"] = self.stopSpeechScroll.IsChecked()
		config.conf["brailleExtender"]["stopSpeechUnknown"] = self.stopSpeechUnknown.IsChecked()
		config.conf["brailleExtender"]["speakRoutingTo"] = self.speakRoutingTo.IsChecked()

		config.conf["brailleExtender"]["updateChannel"] = configBE.updateChannels.keys()[self.updateChannel.GetSelection()]
		config.conf["brailleExtender"]["speakScroll"] = configBE.focusOrReviewChoices.keys()[self.speakScroll.GetSelection()]

		config.conf["brailleExtender"]["tabSize_%s" % configBE.curBD] = self.tabSize.Value
		config.conf["brailleExtender"]["autoScrollDelay_%s" % configBE.curBD] = self.autoScrollDelay.Value
		config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD] = self.rightMarginCells.Value
		config.conf["brailleExtender"]["brailleDisplay1"] = configBE.bds_k[self.brailleDisplay1.GetSelection()]
		config.conf["brailleExtender"]["brailleDisplay2"] = configBE.bds_k[self.brailleDisplay2.GetSelection()]
		super(GeneralDlg, self).onOk(evt)


class AttribraDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Attribra")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleAttribra = sHelper.addItem(wx.CheckBox(self, label=_("Enable Attribra")))
		self.toggleAttribra.SetValue(config.conf["brailleExtender"]["features"]["attributes"])
		self.spellingErrorsAttribute = sHelper.addLabeledControl(_("Show spelling errors with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.spellingErrorsAttribute.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.boldAttribute = sHelper.addLabeledControl(_("Show bold with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.boldAttribute.SetSelection(self.getItemToSelect("bold"))
		self.italicAttribute = sHelper.addLabeledControl(_("Show italic with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.italicAttribute.SetSelection(self.getItemToSelect("italic"))
		self.underlineAttribute = sHelper.addLabeledControl(_("Show underline with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.underlineAttribute.SetSelection(self.getItemToSelect("underline"))

	def getItemToSelect(self, attribute):
		try: idx = configBE.attributeChoices.keys().index(config.conf["brailleExtender"]["attributes"][attribute])
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

	def postInit(self):
		self.toggleAttribra.SetFocus()

	def onOk(self, evt):
		config.conf["brailleExtender"]["features"]["attributes"] = self.toggleAttribra.IsChecked()
		config.conf["brailleExtender"]["attributes"]["bold"] = configBE.attributeChoices.keys()[self.boldAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["italic"] = configBE.attributeChoices.keys()[self.italicAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["underline"] = configBE.attributeChoices.keys()[self.underlineAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["invalid-spelling"] = configBE.attributeChoices.keys()[self.spellingErrorsAttribute.GetSelection()]
		super(AttribraDlg, self).onOk(evt)

class RoleLabelsDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Customize role labels")

	def makeSettings(self, settingsSizer):
		self.roleLabels = config.conf["brailleExtender"]["roleLabels"].copy()
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.categories = sHelper.addLabeledControl(_("Role category"), wx.Choice, choices=[_("General"), _("Landmark"), _("Positive state"), _("Negative state")])
		self.categories.Bind(wx.EVT_CHOICE, self.onCategories)
		self.categories.SetSelection(0)
		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		self.labels = sHelper2.addLabeledControl(_("Role"), wx.Choice, choices=[controlTypes.roleLabels[k] for k in braille.roleLabels.keys()])
		self.labels.Bind(wx.EVT_CHOICE, self.onLabels)
		self.label = sHelper2.addLabeledControl(_("Actual or new label"), wx.TextCtrl)
		self.label.Bind(wx.EVT_TEXT, self.onLabel)
		sHelper.addItem(sHelper2)
		self.onCategories(None)

	def onCategories(self, event):
		idCategory = self.categories.GetSelection()
		if idCategory == 0:
			self.labels.SetItems([controlTypes.roleLabels[k] for k in braille.roleLabels.keys()])
		elif idCategory == 1:
			self.labels.SetItems(braille.landmarkLabels.keys())
		elif idCategory == 2:
			self.labels.SetItems([controlTypes.stateLabels[k] for k in braille.positiveStateLabels.keys()])
		elif idCategory == 3:
			self.labels.SetItems([controlTypes.stateLabels[k] for k in braille.negativeStateLabels.keys()])
		else:
			self.labels.SetItems([])
		if idCategory > -1 and idCategory < 4:
			self.labels.SetSelection(0)
		self.onLabels(None)

	def onLabels(self, event):
		idCategory = self.categories.GetSelection()
		idLabel = self.getIDFromIndex(idCategory, self.labels.GetSelection())
		key = "%d:%s" % (idCategory, idLabel)
		if key in self.roleLabels.keys():
			self.label.SetValue(self.roleLabels[key])
			return
		else: self.label.SetValue(self.getLabelFromID())

	def onLabel(self, evt):
		idCategory = self.categories.GetSelection()
		idLabel = self.labels.GetSelection()
		key = "%d:%s" % (idCategory, self.getIDFromIndex(idCategory, idLabel))
		label = self.label.GetValue()
		if idCategory >= 0 and idLabel >= 0:
			if self.getLabelFromID() == label:
				if key in self.roleLabels.keys(): log.info("%s deleted" % self.roleLabels.pop(key))
			else: self.roleLabels[key] = label

	def getIDFromIndex(self, idCategory, idLabel):
		try:
			if idCategory == 0: return braille.roleLabels.keys()[idLabel]
			elif idCategory == 1: return braille.landmarkLabels.keys()[idLabel]
			elif idCategory == 2: return braille.positiveStateLabels.keys()[idLabel]
			elif idCategory == 3: return braille.negativeStateLabels.keys()[idLabel]
			else: return -1
		except BaseException: return -1

	def getLabelFromID(self):
		idCategory = self.categories.GetSelection()
		idLabel = self.labels.GetSelection()
		if idCategory == 0:
			return braille.roleLabels[braille.roleLabels.keys()[idLabel]]
		elif idCategory == 1:
			return braille.landmarkLabels.values()[idLabel]
		elif idCategory == 2:
			return braille.positiveStateLabels[braille.positiveStateLabels.keys()[idLabel]]
		elif idCategory == 3:
			return braille.negativeStateLabels[braille.negativeStateLabels.keys()[idLabel]]

	def postInit(self):
		self.categories.SetFocus()

	def onOk(self, evt):
		config.conf["brailleExtender"]["roleLabels"] = self.roleLabels
		configBE.discardRoleLabels()
		configBE.loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())
		super(RoleLabelsDlg, self).onOk(evt)

class PreferedBrailleTablesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Prefered braille tables")

	def makeSettings(self, settingsSizer):
		self.oTables = configBE.outputTables
		self.iTables = configBE.inputTables
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper2 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.oTablesPresent = sHelper.addLabeledControl(_("&Output braille tables present in the switch"), wx.Choice, choices=outputTablesInSwitch())
		self.oTablesPresent.SetSelection(0)
		self.deleteOutputTableInSwitch = bHelper1.addButton(self, wx.NewId(), _("Remove"), wx.DefaultPosition)
		self.deleteOutputTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteOutputTableInSwitch)
		self.oTablesNotPresent = sHelper.addLabeledControl(_("Output braille tables not present in the switch"), wx.Choice, choices=outputTablesNotInSwitch())
		self.oTablesNotPresent.SetSelection(0)
		self.addOutputTableInSwitch = bHelper1.addButton(self, wx.NewId(), _("Add"), wx.DefaultPosition)
		self.addOutputTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddOutputTableInSwitch)
		sHelper.addItem(bHelper1)

		self.iTablesPresent = sHelper.addLabeledControl(_("&Input braille tables present in the switch"), wx.Choice, choices=inputTablesInSwitch())
		self.iTablesPresent.SetSelection(0)
		self.deleteInputTableInSwitch = bHelper2.addButton(self, wx.NewId(), _("Remove"), wx.DefaultPosition)
		self.deleteInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteInputTableInSwitch)
		self.iTablesNotPresent = sHelper.addLabeledControl(_("Output braille tables not present in the switch"), wx.Choice, choices=inputTablesNotInSwitch())
		self.iTablesNotPresent.SetSelection(0)
		self.addInputTableInSwitch = bHelper2.addButton(self, wx.NewId(), _("Add"), wx.DefaultPosition)
		self.addInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddInputTableInSwitch)

		sHelper.addItem(bHelper2)

	def postInit(self):
		pass

	def onOk(self, evt):
		config.conf["brailleExtender"]["outputTables"] = ','.join(self.oTables)
		config.conf["brailleExtender"]["inputTables"] = ','.join(self.iTables)
		super(PreferedBrailleTablesDlg, self).onOk(evt)

	def onDeleteOutputTableInSwitch(self, event):
		if self.oTablesPresent.GetStringSelection() != '':
			self.oTables.remove(configBE.tablesFN[configBE.tablesTR.index(
				self.oTablesPresent.GetStringSelection())])
			self.oTablesNotPresent.SetItems(outputTablesNotInSwitch())
			self.oTablesNotPresent.SetSelection(0)
			self.oTablesPresent.SetItems(outputTablesInSwitch())
			self.oTablesPresent.SetSelection(0)
			self.oTablesPresent.SetFocus()
		else: ui.message(_(u"You have no output tables present in the switch"))

	def onAddOutputTableInSwitch(self, event):
		if self.oTablesNotPresent.GetStringSelection() != '':
			self.oTables.append(configBE.tablesFN[configBE.tablesTR.index(self.oTablesNotPresent.GetStringSelection())])
			self.oTablesNotPresent.SetItems(outputTablesNotInSwitch())
			self.oTablesNotPresent.SetSelection(0)
			self.oTablesPresent.SetItems(outputTablesInSwitch())
			self.oTablesPresent.SetSelection(0)
			self.oTablesNotPresent.SetFocus()

	def onDeleteInputTableInSwitch(self, event):
		if self.iTablesPresent.GetStringSelection() != '':
			self.iTables.remove(configBE.tablesFN[configBE.tablesTR.index(self.iTablesPresent.GetStringSelection())])
			self.iTablesNotPresent.SetItems(inputTablesNotInSwitch())
			self.iTablesNotPresent.SetSelection(0)
			self.iTablesPresent.SetItems(inputTablesInSwitch())
			self.iTablesPresent.SetSelection(0)
			self.iTablesPresent.SetFocus()
		else:
			ui.message(_(u"You have no input tables present in the switch"))
		return

	def onAddInputTableInSwitch(self, event):
		if self.iTablesNotPresent.GetStringSelection() != '':
			self.iTables.append(configBE.tablesFN[configBE.tablesTR.index(
				self.iTablesNotPresent.GetStringSelection())])
			self.iTablesNotPresent.SetItems(inputTablesNotInSwitch())
			self.iTablesNotPresent.SetSelection(0)
			self.iTablesPresent.SetItems(inputTablesInSwitch())
			self.iTablesPresent.SetSelection(0)
			self.iTablesNotPresent.SetFocus()


class QuickLaunchesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Quick launches")
	quickLaunchGestures = {}

	def makeSettings(self, settingsSizer):
		pass

	def postInit(self):
		pass

	def onOk(self, evt):
		super(QuickLaunchesDlg, self).onOk(evt)

	def captureNow(self):
		def getCaptured(gesture):
			if gesture.isModifier: return False
			if scriptHandler.findScript(gesture) is not None:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Unable to associate this gesture. Please enter another, now"))
				return False
			if gesture.normalizedIdentifiers[0].startswith("kb") and ":escape" not in gesture.normalizedIdentifiers[0]:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("Please enter a gesture from your {NAME_BRAILLE_DISPLAY} braille display. Press Escape to cancel.".format(NAME_BRAILLE_DISPLAY=configBE.curBD)))
				return False
			if ':escape' not in gesture.normalizedIdentifiers[0]:
				self.quickLaunchGestures.append(gesture.normalizedIdentifiers[0].split(':')[1])
				self.quickLaunchLocations.append('')
				self.quickKeys.SetItems(self.getQuickLaunchList())
				self.quickKeys.SetSelection(len(self.quickLaunchGestures)-1)
				self.onQuickKeys(None)
				self.quickKeys.SetFocus()
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("OK. The gesture captured is %s") % gesture.normalizedIdentifiers[0].split(':')[1])
			inputCore.manager._captureFunc = None
