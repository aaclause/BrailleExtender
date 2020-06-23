# coding: utf-8
# documentFormatting.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import gui
import wx

import addonHandler
import braille
import config
import textInfos
from logHandler import log

from .consts import (
	CHOICE_none,
	CHOICE_dot7,
	CHOICE_dot8,
	CHOICE_dots78,
	CHOICE_tags,
	CHOICE_liblouis,
	CHOICE_likeSpeech,
	CHOICE_enabled,
	CHOICE_disabled,
)
from .common import *
from . import brailleRegionHelper

addonHandler.initTranslation()

CHOICES_LABELS = {
	CHOICE_none: _("nothing"),
	CHOICE_liblouis: _("hand over to Liblouis (defined in tables)"),
	CHOICE_dots78: _("dots 7 and 8"),
	CHOICE_dot7: _("dot 7"),
	CHOICE_dot8: _("dot 8"),
	CHOICE_tags: _("tags"),
}

CHOICES_LABELS_ATTRIBUTES = {
	"bold": _("bold"),
	"italic": _("italic"),
	"underline": _("underline"),
	"strikethrough": _("strikethrough"),
	"text-position:sub": _("subscript"),
	"text-position:super": _("superscript"),
	"spellingErrors": _("spelling errors"),
	"grammarError": _("grammar errors"),
}

CHOICES_LABELS_STATES = {
	CHOICE_likeSpeech: _("like speech"),
	CHOICE_enabled: _("enabled"),
	CHOICE_disabled: _("disabled"),
}

ATTRS = config.conf["brailleExtender"]["attributes"].copy().keys()
logTextInfo = False

def getReport(k):
	if k not in config.conf["brailleExtender"]["documentFormatting"]:
		log.error(f"unknown {k} key")
		return False
	return config.conf["brailleExtender"]["documentFormatting"][k]["enabled"]

def setReport(k, v):
	if k not in config.conf["brailleExtender"]["documentFormatting"]:
		log.error(f"unknown {k} key")
		return False
	config.conf["brailleExtender"]["documentFormatting"][k]["enabled"] = v
	return True

setAttributes = lambda e: setReport("attributes", e)
setAlignments = lambda e: setReport("alignments", e)
setIndentation = lambda e: setReport("indentations", e)

def setLevelItemsList(e):
	config.conf["brailleExtender"]["documentFormatting"]["lists"]["showLevelItem"] = e

attributesEnabled = lambda: getReport("attributes")
alignmentsEnabled = lambda: getReport("alignments")
indentationsEnabled = lambda: getReport("indentations")
levelItemsListEnabled = lambda: config.conf["brailleExtender"]["documentFormatting"]["lists"]["showLevelItem"]

def decorator(fn, s):
	def _getTypeformFromFormatField(self, field, formatConfig=None):
		for attr in ATTRS:
			v = attr.split(":")
			k = v[0]
			v = True if len(v) == 1 else v[1]
			if k in field and (field[k] == v or field[k] == "1"):
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dot7:
					return 7
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dot8:
					return 8
				if config.conf["brailleExtender"]["attributes"][attr] == CHOICE_dots78:
					return 78
		# if COMPLCOLORS != None:
		# col = field.get("color",False)
		# if col and (col != COMPLCOLORS):
		# return 4
		return 0

	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		conf = formatConfig.copy()
		keysToEnable = [
			"reportColor",
			"reportSpellingErrors",
			# "reportLineNumber",
			"reportLineIndentation",
			"reportParagraphIndentation"
		]
		if attributesEnabled():
			keysToEnable.append("reportFontAttributes")
		if alignmentsEnabled():
			keysToEnable.append("reportAlignment",)
		for keyToEnable in keysToEnable:
			conf[keyToEnable] = True
		textInfo_ = info.getTextWithFields(conf)
		formatField = textInfos.FormatField()
		for field in textInfo_:
			if isinstance(field, textInfos.FieldCommand) and isinstance(
				field.field, textInfos.FormatField
			):
				formatField.update(field.field)
		if logTextInfo:
			log.info(formatField)
		self.formatField = formatField
		fn(self, info, conf, isSelection)

	def update(self):
		fn(self)
		if attributesEnabled():
			DOT7 = 64
			DOT8 = 128
			size = len(self.rawTextTypeforms)
			for i, j in enumerate(self.rawTextTypeforms):
				try:
					start = self.rawToBraillePos[i]
					end = self.rawToBraillePos[
						i + 1 if i + 1 < size else (i if i < size else size - 1)
					]
				except IndexError as e:
					log.debug(e)
					return
				k = start
				for k in range(start, end):
					if j == 78:
						self.brailleCells[k] |= DOT7 | DOT8
					if j == 7:
						self.brailleCells[k] |= DOT7
					if j == 8:
						self.brailleCells[k] |= DOT8
		noAlign = False
		postReplacements = []
		if levelItemsListEnabled() and self and hasattr(self.obj, "currentNVDAObject"):
			curObj = self.obj.currentNVDAObject
			if curObj and hasattr(curObj, "IA2Attributes"):
				IA2Attributes = curObj.IA2Attributes
				tag = IA2Attributes.get("tag")
				if tag == "li":
					s = (int(IA2Attributes["level"])-1)*2 if IA2Attributes.get("level") else 0
					noAlign = True
					postReplacements.append(brailleRegionHelper.BrailleCellReplacement(start=0, insertBefore=('⠀' * s)))
		formatField = self.formatField
		if indentationsEnabled() and not noAlign and formatField.get("left-indent"):
			leftIndent = formatField.get("left-indent").split('.')
			postReplacements.append(brailleRegionHelper.BrailleCellReplacement(start=0, insertBefore=('⠀' * abs(int(leftIndent[0])))))
		elif not noAlign and alignmentsEnabled():
			textAlign = formatField.get("text-align")
			if textAlign and textAlign not in ["start", "left"]:
				textAlign = textAlign.replace("-moz-", "").replace("justified", "justify")
				pct = {
					"justify": 0.25,
					"center": 0.5,
					"right": 0.75,
				}
				displaySize = braille.handler.displaySize
				sizeBrailleCells = len(self.brailleCells) - 1
				start = None
				if textAlign in ["center", "right"] and displaySize - 1 > sizeBrailleCells:
					if textAlign == "center":
						start = int((displaySize - sizeBrailleCells) / 2)
					else:
						start = displaySize - sizeBrailleCells
				elif textAlign == "justify":
					start = 3
				elif textAlign in pct:
					start = int(pct[textAlign] * braille.handler.displaySize) - 1
				else:
					log.warning(f"Unknown text-align {textAlign}")
				if start is not None:
					s = "⠀" * start
					postReplacements.append(brailleRegionHelper.BrailleCellReplacement(start=0, insertBefore=s))
		if postReplacements: brailleRegionHelper.replaceBrailleCells(self, postReplacements)

	if s == "addTextWithFields":
		return addTextWithFields_edit
	if s == "update":
		return update
	if s == "_getTypeformFromFormatField":
		return _getTypeformFromFormatField


class ManageAttributes(wx.Dialog):
	def __init__(
		self,
		parent=None,
		# Translators: title of a dialog.
		title=_("Customize attributes"),
	):
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		choices = list(CHOICES_LABELS.values())
		self.spellingErrors = sHelper.addLabeledControl(
			_("Show &spelling errors with"), wx.Choice, choices=choices
		)
		self.spellingErrors.SetSelection(self.getItemToSelect("invalid-spelling"))
		self.grammarError = sHelper.addLabeledControl(
			_("Show &grammar errors with"), wx.Choice, choices=choices
		)
		self.grammarError.SetSelection(self.getItemToSelect("invalid-grammar"))
		self.bold = sHelper.addLabeledControl(
			_("Show b&old with"), wx.Choice, choices=choices
		)
		self.bold.SetSelection(self.getItemToSelect("bold"))
		self.italic = sHelper.addLabeledControl(
			_("Show &italic with"), wx.Choice, choices=choices
		)
		self.italic.SetSelection(self.getItemToSelect("italic"))
		self.underline = sHelper.addLabeledControl(
			_("Show &underline with"), wx.Choice, choices=choices
		)
		self.underline.SetSelection(self.getItemToSelect("underline"))
		self.strikethrough = sHelper.addLabeledControl(
			_("Show stri&kethrough with"), wx.Choice, choices=choices
		)
		self.strikethrough.SetSelection(self.getItemToSelect("strikethrough"))
		self.sub = sHelper.addLabeledControl(
			_("Show su&bscript with"), wx.Choice, choices=choices
		)
		self.sub.SetSelection(self.getItemToSelect("text-position:sub"))
		self.super = sHelper.addLabeledControl(
			_("Show su&perscript with"), wx.Choice, choices=choices
		)
		self.super.SetSelection(self.getItemToSelect("text-position:super"))

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.tagsBtn = bHelper.addButton(self, label="%s..." % _("Manage &tags"))
		self.tagsBtn.Bind(wx.EVT_BUTTON, self.onTagsBtn)
		sHelper.addItem(bHelper)
		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.spellingErrors.SetFocus()

	def onTagsBtn(self, evt=None):
		manageTags = ManageTags(self)
		manageTags.ShowModal()
		self.tagsBtn.SetFocus()

	@staticmethod
	def getItemToSelect(attribute):
		try:
			idx = list(CHOICES_LABELS.keys()).index(
				config.conf["brailleExtender"]["attributes"][attribute]
			)
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

	def onOk(self, evt):
		config.conf["brailleExtender"]["attributes"]["invalid-spelling"] = list(
			CHOICES_LABELS.keys()
		)[self.spellingErrors.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["invalid-grammar"] = list(
			CHOICES_LABELS.keys()
		)[self.grammarError.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["bold"] = list(
			CHOICES_LABELS.keys()
		)[self.bold.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["italic"] = list(
			CHOICES_LABELS.keys()
		)[self.italic.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["underline"] = list(
			CHOICES_LABELS.keys()
		)[self.underline.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["strikethrough"] = list(
			CHOICES_LABELS.keys()
		)[self.strikethrough.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:sub"] = list(
			CHOICES_LABELS.keys()
		)[self.sub.GetSelection()]
		config.conf["brailleExtender"]["attributes"]["text-position:super"] = list(
			CHOICES_LABELS.keys()
		)[self.super.GetSelection()]
		self.Destroy()


class ManageTags(wx.Dialog):
	def __init__(
		self,
		parent=None,
		# Translators: title of a dialog.
		title=_("Customize attribute tags"),
	):
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		choices = list(CHOICES_LABELS_ATTRIBUTES.values())
		self.attributes = sHelper.addLabeledControl(
			_("&Attributes"), wx.Choice, choices=choices
		)
		self.attributes.SetSelection(0)
		self.startTag = sHelper.addLabeledControl(_("&Start tag"), wx.TextCtrl)
		self.endTag = sHelper.addLabeledControl(_("&End tag"), wx.TextCtrl)

		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.attributes.SetFocus()

	def onOk(self, evt):
		self.Destroy()


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = N_("Document formatting")
	panelDescription = _(
		"The following options control the types of document formatting reported by NVDA in braille only."
	)

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		sHelper.addItem(wx.StaticText(self, label=self.panelDescription))

		label = _("Info to &report")
		choices = [
			N_("Font attributes"),
			N_("Alignment"),
			_("Indentation"),
			_("Level of items in a nested list")
		]
		self.reportInfo = sHelper.addLabeledControl(label, gui.nvdaControls.CustomCheckListBox, choices=choices)
		states = (
			attributesEnabled(),
			alignmentsEnabled(),
			indentationsEnabled(),
			levelItemsListEnabled()
		)
		self.reportInfo.CheckedItems = [i for i, state in enumerate(states) if state]
		self.reportInfo.SetSelection(0)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.attributesBtn = bHelper.addButton(
			self, label="%s..." % _("Manage &attributes")
		)
		self.attributesBtn.Bind(wx.EVT_BUTTON, self.onAttributesBtn)
		self.alignmentsBtn = bHelper.addButton(
			self, label="%s..." % _("Manage a&lignments")
		)
		self.indentationBtn = bHelper.addButton(
			self, label="%s..." % _("Manage &indentations")
		)
		sHelper.addItem(bHelper)

	def onAttributesBtn(self, evt=None):
		manageAttributes = ManageAttributes(self)
		manageAttributes.ShowModal()
		self.attributesBtn.SetFocus()

	def postInit(self):
		self.reportFontAttributes.SetFocus()

	def onSave(self):
		checkedItems = self.reportInfo.CheckedItems
		reportAttributes = 0 in checkedItems
		reportAlignments = 1 in checkedItems
		reportIndentations = 2 in checkedItems
		reportLevelItemsList = 3 in checkedItems

		setAttributes(reportAttributes)
		setAlignments(reportAlignments)
		setIndentation(reportIndentations)
		setLevelItemsList(reportLevelItemsList)
