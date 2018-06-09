# coding: utf-8
# addonSettingsPanel.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import gui
import wx
import braille
import configBE

class AddonSettingsPanel(gui.settingsDialogs.SettingsPanel):
	# Translators: title of a dialog.
	title = configBE._addonName

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		self.autoCheckUpdate = sHelper.addItem(wx.CheckBox(self, label=_("Check for &updates automatically")))
		# Translators: label of a dialog.
		self.autoCheckUpdate.SetValue(configBE.conf["general"]["autoCheckUpdate"])

		# Translators: label of a dialog.
		self.updateChannel = sHelper.addLabeledControl(_("Add-on update channel"), wx.Choice, choices=configBE.updateChannels.values())
		if configBE.conf["general"]["channelUpdate"] in configBE.updateChannels.keys():
			itemToSelect = configBE.updateChannels.keys().index(configBE.conf["general"]['channelUpdate'])
		else: channel = configBE.conf["general"]['channelUpdate'].index(configBE.CHANNELSTABLE)
		self.updateChannel.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.hourDynamic = sHelper.addItem(wx.CheckBox(self, label=_("Display time and date infinitely")))
		self.hourDynamic.SetValue(configBE.conf["general"]["hourDynamic"])

		# Translators: label of a dialog.
		self.volumeChangeFeedback = sHelper.addLabeledControl(_("Feedback for volume change in"), wx.Choice, choices=configBE.outputMessage.values())
		if configBE.conf["general"]["volumeChangeFeedback"] in configBE.outputMessage:
			itemToSelect = configBE.outputMessage.keys().index(configBE.conf["general"]["volumeChangeFeedback"]) 
		else:
			itemToSelect = configBE.outputMessage.keys().index(configBE.CHOICE_braille)
		self.volumeChangeFeedback.SetSelection(itemToSelect)

		# Translators: label of a dialog.
		self.modifierKeysFeedback = sHelper.addLabeledControl(_("Feedback for modifier keys in"), wx.Choice, choices=configBE.outputMessage.values())
		if configBE.conf["general"]["modifierKeysFeedback"] in configBE.outputMessage:
			itemToSelect = configBE.outputMessage.keys().index(configBE.conf["general"]["modifierKeysFeedback"]) 
		else:
			itemToSelect = configBE.outputMessage.keys().index(configBE.CHOICE_braille)

		# Translators: label of a dialog.
		self.modifierKeysFeedback.SetSelection(itemToSelect)
		self.rightMarginCells = sHelper.addLabeledControl(_("Right margin on cells")+" "+_("for the currrent braille display"), gui.nvdaControls.SelectOnFocusSpinCtrl, min=0, max=100, initial=configBE.conf["general"]["rightMarginCells_" + configBE.curBD])

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
		sHelper.addItem(bHelper)

	def onAttributesButton(self, evt):
		attribraDialog = AttribraDlg(self, multiInstanceAllowed=True)
		ret = attribraDialog.ShowModal()

	def postInit(self):
		self.addTextBeforeCheckBox.SetFocus()

	def onSave(self):
		configBE.conf["general"]["autoCheckUpdate"] = self.autoCheckUpdate.IsChecked()
		configBE.conf["general"]["hourDynamic"] = self.hourDynamic.IsChecked()
		configBE.conf["general"]["rightMarginCells_%s" % configBE.curBD] = self.rightMarginCells.Value

class AttribraDlg(gui.settingsDialogs.SettingsDialog):
	title = _("Attribra")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		itemToSelect = 0 # temporarily...
		self.toggleAttribra = sHelper.addItem(wx.CheckBox(self, label=_("Enable Attribra")))
		self.spellingErrorsAttribute = sHelper.addLabeledControl(_("Show spelling errors with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.spellingErrorsAttribute.SetSelection(itemToSelect)
		self.boldAttribute = sHelper.addLabeledControl(_("Show bold with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.boldAttribute.SetSelection(itemToSelect)
		self.italicAttribute = sHelper.addLabeledControl(_("Show italic with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.italicAttribute.SetSelection(itemToSelect)
		self.underlineAttribute = sHelper.addLabeledControl(_("Show underline with"), wx.Choice, choices=configBE.attributeChoices.values())
		self.underlineAttribute.SetSelection(itemToSelect)

	def postInit(self):
		self.toggleAttribra.SetFocus()

	def onOk(self, evt):
		super(AttribraDlg, self).onOk(evt)
