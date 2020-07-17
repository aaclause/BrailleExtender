# coding: utf-8
# documentFormatting.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import gui
import wx

import addonHandler
import braille
import config
import louis
import textInfos
from collections import namedtuple
from logHandler import log
from .common import (
	N_,
	CHOICE_none,
	CHOICE_dot7,
	CHOICE_dot8,
	CHOICE_dots78,
	CHOICE_tags,
	CHOICE_liblouis,
	CHOICE_likeSpeech,
	CHOICE_enabled,
	CHOICE_disabled,
	TAG_SEPARATOR,
	CHOICE_spacing
)
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

TAG_ATTRIBUTE = namedtuple("TAG_ATTRIBUTE", ("start", "end"))

CHOICES_LABELS_TAGS = {
	"bold": _("bold"),
	"italic": _("italic"),
	"underline": _("underline"),
	"strikethrough": _("strikethrough"),
	"text-position:sub": _("subscript"),
	"text-position:super": _("superscript"),
	"invalid-spelling": _("spelling errors"),
	"invalid-grammar": _("grammar errors"),
	"text-align:center": _("center alignment"),
	"text-align:justified": _("justified alignment"),
	"text-align:left": _("left alignment"),
	"text-align:right": _("right alignment"),
	"text-align:start": _("default alignment"),
}

CHOICES_LABELS_STATES = {
	CHOICE_likeSpeech: _("like speech"),
	CHOICE_enabled: _("enabled"),
	CHOICE_disabled: _("disabled"),
}

logTextInfo = False
conf = config.conf["brailleExtender"]["documentFormatting"]

def get_report(k):
	if k not in conf:
		log.error(f"unknown {k} key")
		return False
	return conf[k]["enabled"]

def get_attributes(k):
	l = [k]
	if ':' in k: k = l.append(k.split(':')[0])
	for e in l:
		if e in conf["attributes"]:
			return conf["attributes"][e]
	return CHOICE_none

def lineNumberEnabled():
	lineNumber = conf["lineNumber"]
	if lineNumber == CHOICE_likeSpeech:
		return config.conf["documentFormatting"]["reportLineNumber"]
	return lineNumber == CHOICE_enabled

def set_report(k, v):
	if k not in conf:
		log.error(f"unknown {k} key")
		return False
	conf[k]["enabled"] = v
	return True

setAttributes = lambda e: set_report("attributes", e)
setAlignments = lambda e: set_report("alignments", e)
setIndentation = lambda e: set_report("indentations", e)

def setLevelItemsList(e):
	conf["lists"]["showLevelItem"] = e

attributesEnabled = lambda: get_report("attributes")
alignmentsEnabled = lambda: get_report("alignments")
indentationsEnabled = lambda: get_report("indentations")
levelItemsListEnabled = lambda: conf["lists"]["showLevelItem"]

def get_liblouis_typeform(typeform):
	typeforms = {
		"bold": louis.bold,
		"italic": louis.italic,
		"underline": louis.underline
	}
	return typeforms[typeform] if typeform in typeforms else louis.plain_text

def get_brlex_typeform(k, v):
	dot7 = 64
	dot8 = 128
	typeform = 0
	method = get_attributes(k)
	if method == CHOICE_dot7: typeform = dot7
	elif method == CHOICE_dot8: typeform = dot8
	elif method == CHOICE_dots78: typeform = dot7 | dot8
	return typeform

def get_typeforms(self, field):
	if not attributesEnabled(): return 0, 0
	l = ["bold", "italic", "underline", "strikethrough", "text-position", "invalid-spelling", "invalid-grammar"]
	liblouis_typeform = louis.plain_text
	brlex_typeform = 0
	for k in l:
		v = field.get(k, False)
		if v:
			if isinstance(v, bool): v = '1'
			method = get_attributes(f"{k}:{v}")
			if method == CHOICE_liblouis:
				liblouis_typeform |= get_liblouis_typeform(k)
			elif method in [CHOICE_dots78, CHOICE_dot7, CHOICE_dot8]:
				brlex_typeform |= get_brlex_typeform(k, v)
	return liblouis_typeform, brlex_typeform

def decorator(fn, s):
	def _getTypeformFromFormatField(self, field, formatConfig=None):
		return get_typeforms(self, field)

	def addTextWithFields_edit(self, info, formatConfig, isSelection=False):
		formatConfig_ = formatConfig.copy()
		keysToEnable = [
			"reportColor",
			"reportSpellingErrors",
			"reportLineIndentation",
			"reportParagraphIndentation"
		]
		if lineNumberEnabled():
			keysToEnable.append("reportLineNumber")
		if attributesEnabled():
			keysToEnable.append("reportFontAttributes")
		if alignmentsEnabled():
			keysToEnable.append("reportAlignment",)
		for keyToEnable in keysToEnable:
			formatConfig_[keyToEnable] = True
		textInfo_ = info.getTextWithFields(formatConfig_)
		formatField = textInfos.FormatField()
		for field in textInfo_:
			if isinstance(field, textInfos.FieldCommand) and isinstance(
				field.field, textInfos.FormatField
			):
				formatField.update(field.field)
		if logTextInfo:
			log.info(formatField)
		self.formatField = formatField
		fn(self, info, formatConfig_, isSelection)

	def update(self):
		fn(self)
		postReplacements = []
		if attributesEnabled():
			pass#/postReplacements += get_typeformss(self)
		noAlign = False
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
			if textAlign and get_method_alignment(textAlign) == CHOICE_spacing and textAlign not in ["start", "left"]:
				textAlign = normalizeTextAlign(textAlign)
				pct = {
					"justified": 0.25,
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
				elif textAlign == "justified":
					start = 3
				elif textAlign in pct:
					start = int(pct[textAlign] * braille.handler.displaySize) - 1
				else:
					log.error(f"Unknown text-align {textAlign}")
				if start is not None:
					s = "⠀" * start
					postReplacements.append(brailleRegionHelper.BrailleCellReplacement(start=0, insertBefore=s))
		if postReplacements: brailleRegionHelper.replaceBrailleCells(self, postReplacements)
		if any(self.brlex_typeforms):
			brlex_typeforms = self.brlex_typeforms
			lastTypeform = 0
			for pos in range(len(self.rawText)):
				if pos in brlex_typeforms:
					lastTypeform = brlex_typeforms[pos]
				if lastTypeform:
					p = self._rawToContentPos.index(pos) if hasattr(self, "_rawToContentPos") and self._rawToContentPos else pos
					start, end = brailleRegionHelper.getBraillePosFromRawPos(self, p)
					for pos_ in range(start, end+1):
						self.brailleCells[pos_] |= lastTypeform
		self.brlex_typeforms = {}
	if s == "addTextWithFields":
		return addTextWithFields_edit
	if s == "update":
		return update
	if s == "_getTypeformFromFormatField":
		return _getTypeformFromFormatField

_tags = {}

def load_tags():
	global _tags
	tags = conf["tags"].copy()
	for k, v in tags.items():
		if len(v.split(TAG_SEPARATOR)) == 2:
			v_ = v.split(TAG_SEPARATOR)
			_tags[k] = TAG_ATTRIBUTE(v_[0], v_[1])

def save_tags(newTags):
		tags = {k: f"{v.start}{TAG_SEPARATOR}{v.end}" for k, v in newTags.items()}
		conf["tags"] = tags

def get_tags(k, tags=None):
	if not tags: tags = _tags
	if not tags: return None
	if k in tags:
		return tags[k]
	elif ':' in k and k.split(':')[0] in tags: return tags[k.split(':')[0]]
	return None

def getFormatFieldBraille(field, fieldCache, isAtStart, formatConfig):
	"""Generates the braille text for the given format field.
	@param field: The format field to examine.
	@type field: {str : str, ...}
	@param fieldCache: The format field of the previous run; i.e. the cached format field.
	@type fieldCache: {str : str, ...}
	@param isAtStart: True if this format field precedes any text in the line/paragraph.
	This is useful to restrict display of information which should only appear at the start of the line/paragraph;
	e.g. the line number or line prefix (list bullet/number).
	@type isAtStart: bool
	@param formatConfig: The formatting config.
	@type formatConfig: {str : bool, ...}
	"""
	TEXT_SEPARATOR= ''
	textList = []
	align = None
	if alignmentsEnabled():
		textAlign = normalizeTextAlign(field.get("text-align"))
		old_textAlign = normalizeTextAlign(fieldCache.get("text-align"))
		if textAlign and textAlign != old_textAlign:
			tag = get_tags(f"text-align:{textAlign}")
			if tag: align = tag.start
	if isAtStart:
		if formatConfig["reportLineNumber"]:
			lineNumber = field.get("line-number")
			if lineNumber:
				textList.append("%s" % lineNumber)
		linePrefix = field.get("line-prefix")
		if linePrefix:
			textList.append(linePrefix)
		if formatConfig["reportHeadings"]:
			headingLevel=field.get('heading-level')
			if headingLevel:
				# Translators: Displayed in braille for a heading with a level.
				# %s is replaced with the level.
				textList.append(_("h%s")%headingLevel)
	if formatConfig["reportLinks"]:
		link=field.get("link")
		oldLink=fieldCache.get("link")
		if link and link != oldLink:
			textList.append(braille.roleLabels[controlTypes.ROLE_LINK])

	start_tag_list = []
	end_tag_list = []
	if attributesEnabled():
		tags = [tag for tag in [
			"bold",
			"italic",
			"underline",
			"strikethrough",
			"text-position:sub",
			"text-position:super",
			"invalid-spelling",
			"invalid-grammar"
		] if get_attributes(tag) == CHOICE_tags]
		for name_tag in tags:
			name_field = name_tag.split(':')[0]
			value_field = name_tag.split(':', 1)[1] if ':' in name_tag else None
			field_value = field.get(name_field)
			old_field_value = fieldCache.get(name_field)
			tag = get_tags(f"{name_field}:{field_value}")
			old_tag = get_tags(f"{name_field}:{old_field_value}")
			if value_field != old_field_value and old_tag and old_field_value:
				if old_field_value != field_value: end_tag_list.append(old_tag.end)
			if field_value and tag and field_value != value_field and field_value != old_field_value:
				start_tag_list.append(tag.start)
	fieldCache.clear()
	fieldCache.update(field)
	return (TEXT_SEPARATOR.join([x for x in textList if x]), ''.join(start_tag_list), ''.join(end_tag_list[::-1]), align)

def normalizeTextAlign(desc):
	if not desc or not isinstance(desc, str): return None
	desc = desc.replace("-moz-", "").replace("justify", "justified")
	return desc

def get_method_alignment(desc):
	sect = conf["alignments"]
	if desc in sect: return sect[desc]
	return None

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
		sHelper.addItem(bHelper)
		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.spellingErrors.SetFocus()

	@staticmethod
	def getItemToSelect(attribute):
		try:
			idx = list(CHOICES_LABELS.keys()).index(
				conf["attributes"][attribute]
			)
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

	def onOk(self, evt):
		conf["attributes"]["invalid-spelling"] = list(
			CHOICES_LABELS.keys()
		)[self.spellingErrors.GetSelection()]
		conf["attributes"]["invalid-grammar"] = list(
			CHOICES_LABELS.keys()
		)[self.grammarError.GetSelection()]
		conf["attributes"]["bold"] = list(
			CHOICES_LABELS.keys()
		)[self.bold.GetSelection()]
		conf["attributes"]["italic"] = list(
			CHOICES_LABELS.keys()
		)[self.italic.GetSelection()]
		conf["attributes"]["underline"] = list(
			CHOICES_LABELS.keys()
		)[self.underline.GetSelection()]
		conf["attributes"]["strikethrough"] = list(
			CHOICES_LABELS.keys()
		)[self.strikethrough.GetSelection()]
		conf["attributes"]["text-position:sub"] = list(
			CHOICES_LABELS.keys()
		)[self.sub.GetSelection()]
		conf["attributes"]["text-position:super"] = list(
			CHOICES_LABELS.keys()
		)[self.super.GetSelection()]
		self.Destroy()


class ManageTags(wx.Dialog):

	def __init__(
		self,
		parent=None,
		# Translators: title of a dialog.
		title=_("Customize formatting tags"),
	):
		self.tags = _tags.copy()
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		choices = list(CHOICES_LABELS_TAGS.values())
		self.formatting = sHelper.addLabeledControl(
			_("&Formatting"), wx.Choice, choices=choices
		)
		self.formatting.SetSelection(0)
		self.formatting.Bind(wx.EVT_CHOICE, self.onFormatting)
		self.startTag = sHelper.addLabeledControl(_("&Start tag"), wx.TextCtrl)
		self.startTag.Bind(wx.EVT_TEXT, self.onTags)

		self.endTag = sHelper.addLabeledControl(_("&End tag"), wx.TextCtrl)
		self.endTag.Bind(wx.EVT_TEXT, self.onTags)
		self.onTags()

		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.formatting.SetFocus()

	def get_key_attribute(self):
		l = list(CHOICES_LABELS_TAGS.keys())
		selection = self.formatting.GetSelection()
		return l[selection] if selection < len(l) else 0

	def onTags(self, evt=None):
		k = self.get_key_attribute()
		self.tags[k] = self.startTag.GetValue()
		tag = TAG_ATTRIBUTE(
			self.startTag.GetValue(),
			self.endTag.GetValue()
		)
		self.tags[k] = tag

	def onFormatting(self, evt=None):
		k = self.get_key_attribute()
		tag = get_tags(k, self.tags)
		self.startTag.SetValue(tag.start)
		self.endTag.SetValue(tag.end)
		if "text-align" in k: self.endTag.Disable()
		else: self.endTag.Enable()

	def onOk(self, evt):
		save_tags(self.tags)
		load_tags()
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
		choices = list(CHOICES_LABELS_STATES.values())
		self.reportLineNumber = sHelper.addLabeledControl(
			_("Report line &number"), wx.Choice, choices=choices
		)
		keys = list(CHOICES_LABELS_STATES.keys())
		self.reportLineNumber.SetSelection(keys.index(conf["lineNumber"]))
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.attributesBtn = bHelper.addButton(
			self, label="%s..." % _("Representation of &attributes")
		)
		self.attributesBtn.Bind(wx.EVT_BUTTON, self.onAttributesBtn)
		self.alignmentsBtn = bHelper.addButton(
			self, label="%s..." % _("Representation of a&lignments")
		)
		self.indentationBtn = bHelper.addButton(
			self, label="%s..." % _("Representation of &indentations")
		)
		self.tagsBtn = bHelper.addButton(self, label="%s..." % _("Customize &tags"))
		self.tagsBtn.Bind(wx.EVT_BUTTON, self.onTagsBtn)
		sHelper.addItem(bHelper)

	def onAttributesBtn(self, evt=None):
		manageAttributes = ManageAttributes(self)
		manageAttributes.ShowModal()
		self.attributesBtn.SetFocus()

	def onTagsBtn(self, evt=None):
		manageTags = ManageTags(self)
		manageTags.ShowModal()
		self.tagsBtn.SetFocus()

	def postInit(self):
		self.reportFontAttributes.SetFocus()

	def onSave(self):
		checkedItems = self.reportInfo.CheckedItems
		reportAttributes = 0 in checkedItems
		reportAlignments = 1 in checkedItems
		reportIndentations = 2 in checkedItems
		reportLevelItemsList = 3 in checkedItems
		lineNumber = list(CHOICES_LABELS_STATES.keys())[self.reportLineNumber.GetSelection()]
		conf["lineNumber"] = lineNumber
		setAttributes(reportAttributes)
		setAlignments(reportAlignments)
		setIndentation(reportIndentations)
		setLevelItemsList(reportLevelItemsList)
