# coding: utf-8
# textAttributes.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import gui
import wx

import addonHandler
import braille
import config
import textInfos
from logHandler import log

from .consts import CHOICE_none, CHOICE_dot7, CHOICE_dot8, CHOICE_dots78, CHOICE_tags, CHOICE_liblouis, CHOICE_likeSpeech, CHOICE_enabled, CHOICE_disabled
from .common import *
from . import brailleRegionHelper
addonHandler.initTranslation()

CHOICES_LABELS = {
	CHOICE_none: _("Nothing"),
	CHOICE_liblouis: _("Hand over to Liblouis (defined in tables)"),
	CHOICE_dots78: _("dots 7 and 8"),
	CHOICE_dot7: _("dot 7"),
	CHOICE_dot8: _("dot 8"),
	CHOICE_tags: _("tags")
}

CHOICES_LABELS_ATTRIBUTES = {
	"selectedElement": _("selected elements"),
	"spellingErrors": _("spelling errors"),
	"bold": _("bold"),
	"italic": _("italic"),
	"underline": _("underline"),
	"strikethrough": _("strikethrough"),
	"text-position:sub": _("subscript"),
	"text-position:super": _("superscript")
}

CHOICES_LABELS_STATES = {
	CHOICE_likeSpeech: _("like speech"),
	CHOICE_enabled: _("enabled"),
	CHOICE_disabled: _("disabled")
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
			keysToEnable = ["reportFontAttributes", "reportColor", "reportSpellingErrors", "reportAlignment", 
			#"reportLineNumber",
			"reportLineIndentation", "reportParagraphIndentation"]
			for keyToEnable in keysToEnable:
				conf[keyToEnable] = True
		textInfo_ = info.getTextWithFields(conf)
		formatField = textInfos.FormatField()
		for field in textInfo_:
			if isinstance(field,textInfos.FieldCommand) and isinstance(field.field,textInfos.FormatField):
				formatField.update(field.field)
		if logTextInfo: log.info(formatField)
		self.formatField = formatField
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
		formatField = self.formatField
		textAlign = formatField.get("text-align")
		if textAlign and textAlign not in ["start", "left"]:
			textAlign = textAlign.replace("-moz-", "")
			pct = {
				"justified": 0.25,
				"justify": 0.25,
				"center": 0.5,
				"right": 0.75,
			}
			displaySize = braille.handler.displaySize
			sizeBrailleCells = len(self.brailleCells)-1
			start = None
			if textAlign in ["center", "right"] and displaySize-1 > sizeBrailleCells:
				if textAlign == "center":
					start = int((displaySize-sizeBrailleCells)/2)
				else: start = displaySize-sizeBrailleCells
			elif textAlign in pct:
				start = int(pct[textAlign] * braille.handler.displaySize)-1
			else:
				log.warning(f"Unknown text-align {textAlign}")
			if start is not None:
				s = '⠀' * start
				repl = brailleRegionHelper.BrailleCellReplacement(start=0, insertBefore=s)
				brailleRegionHelper.replaceBrailleCells(self, [repl])

	if s == "addTextWithFields": return addTextWithFields_edit
	if s == "update": return update
	if s == "_getTypeformFromFormatField": return _getTypeformFromFormatField

class ManageTags(wx.Dialog):

	def __init__(
		self,
		parent=None,
		# Translators: title of a dialog.
		title=_("Manage tags")
	):
		super(ManageTags, self).__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		choices = list(CHOICES_LABELS_ATTRIBUTES.values())
		self.attributes = sHelper.addLabeledControl(_("Attributes"), wx.Choice, choices=choices)
		self.attributes.SetSelection(0)
		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK|wx.CANCEL))
		mainSizer.Add(sHelper.sizer,border=20,flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON,self.onOk,id=wx.ID_OK)
		self.attributes.SetFocus()

	def onOk(self, evt): pass


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = N_("Document formatting")
	panelDescription = _("The following options control the types of document formatting reported by NVDA in braille only.")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		sHelper.addItem(wx.StaticText(self, label=self.panelDescription))
		choices = list(CHOICES_LABELS.values())
		self.featureEnabled = sHelper.addItem(wx.CheckBox(self, label=N_("Font attrib&utes")))
		self.featureEnabled.SetValue(config.conf["brailleExtender"]["attributes"]["enabled"])
		self.featureEnabled.Bind(wx.EVT_CHECKBOX, self.onFeatureEnabled)
		self.spellingErrors = sHelper.addLabeledControl(_("Show &spelling errors with"), wx.Choice, choices=choices)
		self.spellingErrors.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.bold = sHelper.addLabeledControl(_("Show b&old with"), wx.Choice, choices=choices)
		self.bold.SetSelection(self.getItemToSelect("bold"))
		self.italic = sHelper.addLabeledControl(_("Show &italic with"), wx.Choice, choices=choices)
		self.italic.SetSelection(self.getItemToSelect("italic"))
		self.underline = sHelper.addLabeledControl(_("Show &underline with"), wx.Choice, choices=choices)
		self.underline.SetSelection(self.getItemToSelect("underline"))
		self.strikethrough = sHelper.addLabeledControl(_("Show stri&kethrough with"), wx.Choice, choices=choices)
		self.strikethrough.SetSelection(self.getItemToSelect("strikethrough"))
		self.sub = sHelper.addLabeledControl(_("Show su&bscript with"), wx.Choice, choices=choices)
		self.sub.SetSelection(self.getItemToSelect("text-position:sub"))
		self.super = sHelper.addLabeledControl(_("Show su&perscript with"), wx.Choice, choices=choices)
		self.super.SetSelection(self.getItemToSelect("text-position:super"))
		self.tagsBtn = bHelper.addButton(self, label="%s..." % _("Manage &Tags"))
		sHelper.addItem(bHelper)
		self.tagsBtn.Bind(wx.EVT_BUTTON, self.onTagsBtn)
		self.onFeatureEnabled()

	def postInit(self): self.featureEnabled.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["attributes"]["enabled"] = self.featureEnabled.IsChecked()
		config.conf["brailleExtender"]["attributes"]["invalid-spelling"] = list(CHOICES_LABELS.keys())[self.spellingErrors.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["bold"] = list(CHOICES_LABELS.keys())[self.bold.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["italic"] = list(CHOICES_LABELS.keys())[self.italic.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["underline"] = list(CHOICES_LABELS.keys())[self.underline.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["strikethrough"] = list(CHOICES_LABELS.keys())[self.strikethrough.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:sub"] = list(CHOICES_LABELS.keys())[self.sub.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:super"] = list(CHOICES_LABELS.keys())[self.super.GetSelection()]

	def onTagsBtn(self, evt=None):
		manageTags = ManageTags(self)
		manageTags.ShowModal()
		manageTags.Destroy()
		self.tagsBtn.SetFocus()

	@staticmethod
	def getItemToSelect(attribute):
		try: idx = list(CHOICES_LABELS.keys()).index(config.conf["brailleExtender"]["attributes"][attribute])
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

	def onFeatureEnabled(self, evt=None):
		l = [
			self.spellingErrors,
			self.bold,
			self.italic,
			self.underline,
			self.strikethrough,
			self.sub,
			self.super
		]
		for e in l:
			if self.featureEnabled.IsChecked(): e.Enable()
			else: e.Disable()
		if evt: evt.Skip()
