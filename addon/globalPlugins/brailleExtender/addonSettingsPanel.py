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

class AddonSettingsPanel(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = "Braille Extender"

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		self.autoCheckUpdate = sHelper.addItem(wx.CheckBox(self, label=_("Check for &updates automatically")))
		# Translators: label of a dialog.
		self.autoCheckUpdate.SetValue(config.conf["brailleExtender"]["autoCheckUpdate"])

		# Translators: label of a dialog.
		self.updateChannel = sHelper.addLabeledControl(_("Add-on update channel"), wx.Choice, choices=configBE.updateChannels.values())
		if config.conf["brailleExtender"]["channelUpdate"] in configBE.updateChannels.keys():
			itemToSelect = configBE.updateChannels.keys().index(config.conf["brailleExtender"]['channelUpdate'])
		else: channel = config.conf["brailleExtender"]['channelUpdate'].index(configBE.CHANNELSTABLE)
		self.updateChannel.SetSelection(itemToSelect)

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
		self.rightMarginCells = sHelper.addLabeledControl(_("Right margin on cells")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=config.conf["brailleExtender"]["rightMarginCells_" + configBE.curBD])

		itemToSelect = 0 # temporarily...
		lb = braille.getDisplayList()
		lbl = []
		for l in lb:
			if l[0] == 'noBraille': lbl.append(_('Last known'))
			else: lbl.append(l[1])
		self.brailleDisplay1 = sHelper.addLabeledControl(_("Braille display to load on NVDA+&k"), wx.Choice, choices=lbl)
		self.brailleDisplay2 = sHelper.addLabeledControl(_("Braille display to load on NVDA+SHIFT+k"), wx.Choice, choices=lbl)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.attributesButton = bHelper.addButton(self, wx.NewId(), "%s..." % _("Text &attributes"), wx.DefaultPosition)
		self.attributesButton.Bind(wx.EVT_BUTTON,self.onAttributesButton)
		self.quickLaunchesButton = bHelper.addButton(self, wx.NewId(), "%s..." % _("&Quick launches"), wx.DefaultPosition)
		self.customizeLabelsButton = bHelper.addButton(self, wx.NewId(), "%s..." % _("Customize role &labels"), wx.DefaultPosition)
		self.customizeLabelsButton.Bind(wx.EVT_BUTTON,self.onCustomizeLabelsButton)
		sHelper.addItem(bHelper)

	def onAttributesButton(self, evt):
		attribraDialog = AttribraDlg(self, multiInstanceAllowed=True)
		ret = attribraDialog.ShowModal()

	def onCustomizeLabelsButton(self, evt):
		customizeLabelsDlg = CustomizeLabelsDlg(self, multiInstanceAllowed=True)
		ret = customizeLabelsDlg.ShowModal()

	def postInit(self):
		self.addTextBeforeCheckBox.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["autoCheckUpdate"] = self.autoCheckUpdate.IsChecked()
		config.conf["brailleExtender"]["hourDynamic"] = self.hourDynamic.IsChecked()
		config.conf["brailleExtender"]["rightMarginCells_%s" % configBE.curBD] = self.rightMarginCells.Value

class AttribraDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = _("Attribra")

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

class CustomizeLabelsDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = _("Customize role labels")

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
		except: return -1

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
		super(CustomizeLabelsDlg, self).onOk(evt)
