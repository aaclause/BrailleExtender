# coding: utf-8
# textAttributes.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import gui
import wx

import addonHandler
import config

from .consts import CHOICE_none, CHOICE_dot7, CHOICE_dot8, CHOICE_dots78, CHOICE_tags

addonHandler.initTranslation()

CHOICES_LABELS = {
	CHOICE_none: _("none"),
	CHOICE_dots78: _("dots 7 and 8"),
	CHOICE_dot7: _("dot 7"),
	CHOICE_dot8: _("dot 8"),
	CHOICE_tags: _("tags")
}

ATTRS = config.conf["brailleExtender"]["attributes"].copy().keys()
logTextInfo = False

def featureEnabled():
	return config.conf["brailleExtender"]["attributes"]["enabled"]

def decorator(fn, s):
	def _getTypeformFromFormatField(self, field, formatConfig=None):
		for attr in ATTRS:
			v = attr.split(':')
			k = v[0]
			v = True if len(v) == 1 else v[1]
			if k in field and (field[k] == v or field[k] == '1'):
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dot7: return 7
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dot8: return 8
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dots78: return 78
		# if COMPLCOLORS != None:
			# col = field.get("color",False)
			# if col and (col != COMPLCOLORS):
				# return 4
		return 0

	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		conf = formatConfig.copy()
		if featureEnabled():
			conf["reportFontAttributes"] = True
			conf["reportColor"] = True
			conf["reportSpellingErrors"] = True
			if logTextInfo: log.info(info.getTextWithFields(conf))
		fn(self, info, conf, isSelection)

	def update(self):
		fn(self)
		if not featureEnabled(): return
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


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Text attributes")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		choices = list(CHOICES_LABELS.values())
		self.featureEnabled = sHelper.addItem(wx.CheckBox(self, label=_("&Enable this feature")))
		self.featureEnabled.SetValue(config.conf["brailleExtender"]["attributes"]["enabled"])
		self.selectedElement = sHelper.addLabeledControl(_("Show selected elements with"), wx.Choice, choices=choices)
		self.selectedElement.SetSelection(self.getItemToSelect("selectedElement"))
		self.spellingErrorsAttribute = sHelper.addLabeledControl(_("Show spelling errors with"), wx.Choice, choices=choices)
		self.spellingErrorsAttribute.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.boldAttribute = sHelper.addLabeledControl(_("Show bold with"), wx.Choice, choices=choices)
		self.boldAttribute.SetSelection(self.getItemToSelect("bold"))
		self.italicAttribute = sHelper.addLabeledControl(_("Show italic with"), wx.Choice, choices=choices)
		self.italicAttribute.SetSelection(self.getItemToSelect("italic"))
		self.underlineAttribute = sHelper.addLabeledControl(_("Show underline with"), wx.Choice, choices=choices)
		self.underlineAttribute.SetSelection(self.getItemToSelect("underline"))
		self.strikethroughAttribute = sHelper.addLabeledControl(_("Show strikethrough with"), wx.Choice, choices=choices)
		self.strikethroughAttribute.SetSelection(self.getItemToSelect("strikethrough"))
		self.subAttribute = sHelper.addLabeledControl(_("Show subscript with"), wx.Choice, choices=choices)
		self.subAttribute.SetSelection(self.getItemToSelect("text-position:sub"))
		self.superAttribute = sHelper.addLabeledControl(_("Show superscript with"), wx.Choice, choices=choices)
		self.superAttribute.SetSelection(self.getItemToSelect("text-position:super"))

	def postInit(self): self.featureEnabled.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["attributes"]["enabled"] = self.featureEnabled.IsChecked()
		config.conf["brailleExtender"]["attributes"]["selectedElement"] = list(CHOICES_LABELS.keys())[self.selectedElement.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["invalid-spelling"] = list(CHOICES_LABELS.keys())[self.spellingErrorsAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["bold"] = list(CHOICES_LABELS.keys())[self.boldAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["italic"] = list(CHOICES_LABELS.keys())[self.italicAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["underline"] = list(CHOICES_LABELS.keys())[self.underlineAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["strikethrough"] = list(CHOICES_LABELS.keys())[self.strikethroughAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:sub"] = list(CHOICES_LABELS.keys())[self.subAttribute.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:super"] = list(CHOICES_LABELS.keys())[self.superAttribute.GetSelection()]

	@staticmethod
	def getItemToSelect(attribute):
		try: idx = list(CHOICES_LABELS.keys()).index(config.conf["brailleExtender"]["attributes"][attribute])
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx
