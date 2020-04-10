# coding: utf-8
# undefinedChars.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
from .utils import getCurrentBrailleTables
from . import huc
from . import configBE
from .utils import getTextInBraille
from .common import *
import louis
import config
import characterProcessing
import brailleTables
import brailleInput
from collections import namedtuple
import codecs
import json
import re
import gui
import wx

import addonHandler

addonHandler.initTranslation()


HUCDotPattern = "12345678-78-12345678"
undefinedCharPattern = huc.cellDescriptionsToUnicodeBraille(HUCDotPattern)


def getHardValue():
	selected = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if selected == configBE.CHOICE_otherDots:
		return config.conf["brailleExtender"]["undefinedCharsRepr"][
			"hardDotPatternValue"
		]
	elif selected == configBE.CHOICE_otherSign:
		return config.conf["brailleExtender"]["undefinedCharsRepr"][
			"hardSignPatternValue"
		]
	else:
		return ""


def setUndefinedChar(t=None):
	if not t or t > CHOICE_HUC6 or t < 0:
		t = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if t == 0:
		return
	c = [
		"default",
		"12345678",
		"123456",
		"0",
		config.conf["brailleExtender"]["undefinedCharsRepr"]["hardDotPatternValue"],
		"questionMark",
		"sign",
	] + [HUCDotPattern] * 7
	v = c[t]
	if v in ["questionMark", "sign"]:
		if v == "questionMark":
			s = "?"
		else:
			s = getHardValue()
		v = huc.unicodeBrailleToDescription(
			getTextInBraille(s, getCurrentBrailleTables())
		)
	louis.compileString(getCurrentBrailleTables(),
						bytes("undefined %s" % v, "ASCII"))


def getExtendedSymbolsForString(s: str) -> dict:
	return {
		c: (d, [(m.start(), m.end()) for m in re.finditer(c, s)])
		for c, d in extendedSymbols.items()
		if c in s
	}


def getDescChar(c, lang="Windows", start="", end=""):
	if lang == "Windows":
		lang = languageHandler.getLanguage()
	desc = characterProcessing.processSpeechSymbols(
		lang, c, characterProcessing.SYMLVL_CHAR
	).replace(' ', '').strip()
	if not desc or desc == c:
		if config.conf["brailleExtender"]["undefinedCharsRepr"]["method"] in [
				configBE.CHOICE_HUC6,
				configBE.CHOICE_HUC8,
		]:
			HUC6 = (
				config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
				== configBE.CHOICE_HUC6
			)
			return huc.translate(c, HUC6=HUC6)
		else:
			return getTextInBraille("".join(getUnicodeNotation(c)))
	return f"{start}{desc}{end}"


def getLiblouisStyle(c):
	if c < 0x10000:
		return r"\x%.4x" % c
	elif c <= 0x100000:
		return r"\y%.5x" % c
	else:
		return r"\z%.6x" % c


def getUnicodeNotation(s, notation=None):
	if not notation:
		notation = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	matches = {
		configBE.CHOICE_bin: bin,
		configBE.CHOICE_oct: oct,
		configBE.CHOICE_dec: lambda s: s,
		configBE.CHOICE_hex: hex,
		configBE.CHOICE_liblouis: getLiblouisStyle,
	}
	fn = matches[notation]
	s = getTextInBraille("".join(["'%s'" % fn(ord(c)) for c in s]))
	return s


def undefinedCharProcess(self):
	extendedSymbolsRawText = {}
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]:
		extendedSymbolsRawText = getExtendedSymbolsForString(self.rawText)
	unicodeBrailleRepr = "".join([chr(10240 + cell)
								  for cell in self.brailleCells])
	allBraillePos = [
		m.start() for m in re.finditer(undefinedCharPattern, unicodeBrailleRepr)
	]
	allExtendedPos = {}
	for c, v in extendedSymbolsRawText.items():
		for start, end in v[1]:
			allExtendedPos[start] = end
	if not allBraillePos:
		return
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]:
		start = config.conf["brailleExtender"]["undefinedCharsRepr"]["start"]
		end = config.conf["brailleExtender"]["undefinedCharsRepr"]["end"]
		if start:
			start = getTextInBraille(start)
		if end:
			end = getTextInBraille(end)
		replacements = {
			braillePos: getTextInBraille(
				(
					getDescChar(
						self.rawText[
							self.brailleToRawPos[braillePos]: allExtendedPos[
								self.brailleToRawPos[braillePos]
							]
						],
						lang=config.conf["brailleExtender"]["undefinedCharsRepr"][
							"lang"
						],
						start=start,
						end=f":{allExtendedPos[self.brailleToRawPos[braillePos]] - self.brailleToRawPos[braillePos]}{end}"
						+ getDescChar(
							self.rawText[self.brailleToRawPos[braillePos]],
							lang=config.conf["brailleExtender"]["undefinedCharsRepr"][
								"lang"
							],
							start=start,
							end=end,
						),
					)
				)
				if self.brailleToRawPos[braillePos] in allExtendedPos
				else getDescChar(
					self.rawText[self.brailleToRawPos[braillePos]],
					lang=config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"],
					start=start,
					end=end,
				),
				table=[config.conf["brailleExtender"]
					   ["undefinedCharsRepr"]["table"]],
			)
			for braillePos in allBraillePos
		}
	elif config.conf["brailleExtender"]["undefinedCharsRepr"]["method"] in [
			configBE.CHOICE_HUC6,
			configBE.CHOICE_HUC8,
	]:
		HUC6 = (
			config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
			== configBE.CHOICE_HUC6
		)
		replacements = {
			braillePos: huc.translate(
				self.rawText[self.brailleToRawPos[braillePos]], HUC6=HUC6
			)
			for braillePos in allBraillePos
		}
	else:
		replacements = {
			braillePos: getUnicodeNotation(
				self.rawText[self.brailleToRawPos[braillePos]]
			)
			for braillePos in allBraillePos
		}
	newBrailleCells = []
	newBrailleToRawPos = []
	newRawToBraillePos = []
	lenBrailleToRawPos = len(self.brailleToRawPos)
	alreadyDone = []
	i = 0
	for iBrailleCells, brailleCells in enumerate(self.brailleCells):
		brailleToRawPos = self.brailleToRawPos[iBrailleCells]
		if iBrailleCells in replacements and not replacements[iBrailleCells].startswith(
				undefinedCharPattern[0]
		):
			toAdd = [ord(c) - 10240 for c in replacements[iBrailleCells]]
			newBrailleCells += toAdd
			newBrailleToRawPos += [i] * len(toAdd)
			alreadyDone += list(range(iBrailleCells, iBrailleCells + 3))
			i += 1
		else:
			if iBrailleCells in alreadyDone:
				continue
			newBrailleCells.append(self.brailleCells[iBrailleCells])
			newBrailleToRawPos += [i]
			if (iBrailleCells + 1) < lenBrailleToRawPos and self.brailleToRawPos[
					iBrailleCells + 1
			] != brailleToRawPos:
				i += 1
	pos = -42
	for i, brailleToRawPos in enumerate(newBrailleToRawPos):
		if brailleToRawPos != pos:
			pos = brailleToRawPos
			newRawToBraillePos.append(i)
	self.brailleCells = newBrailleCells
	self.brailleToRawPos = newBrailleToRawPos
	self.rawToBraillePos = newRawToBraillePos
	if self.cursorPos:
		self.brailleCursorPos = self.rawToBraillePos[self.cursorPos]


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Representation of undefined characters")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		label = _("Representation &method")
		dotPatternSample = "6-12345678"
		signPatternSample = "??"
		choices = [
			_("Use braille table behavior"),
			_("Dots 1-8 (⣿)"),
			_("Dots 1-6 (⠿)"),
			_("Empty cell (⠀)"),
			_(f"Other dot pattern (e.g.: {dotPatternSample})"),
			_("Question mark (depending output table)"),
			_(f"Other sign/pattern (e.g.: {signPatternSample})"),
			_("Hexadecimal, Liblouis style"),
			_("Hexadecimal, HUC8"),
			_("Hexadecimal, HUC6"),
			_("Hexadecimal"),
			_("Decimal"),
			_("Octal"),
			_("Binary"),
		]
		self.undefinedCharReprList = sHelper.addLabeledControl(
			label, wx.Choice, choices=choices
		)
		self.undefinedCharReprList.SetSelection(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
		)
		self.undefinedCharReprList.Bind(
			wx.EVT_CHOICE, self.onUndefinedCharReprList)
		# Translators: label of a dialog.
		self.undefinedCharReprEdit = sHelper.addLabeledControl(
			_("Specify another pattern"), wx.TextCtrl, value=self.getHardValue()
		)
		self.onUndefinedCharReprList()
		self.undefinedCharDesc = sHelper.addItem(
			wx.CheckBox(self, label=_(
				"Describe undefined characters if possible"))
		)
		self.undefinedCharDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]
		)
		self.undefinedCharDesc.Bind(wx.EVT_CHECKBOX, self.onUndefinedCharDesc)
		self.undefinedCharExtendedDesc = sHelper.addItem(
			wx.CheckBox(
				self, label=_(
					"Also describe extended characters (e.g.: country flags)")
			)
		)
		self.undefinedCharExtendedDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]
		)
		self.undefinedCharStart = sHelper.addLabeledControl(
			_("Start tag"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["undefinedCharsRepr"]["start"],
		)
		self.undefinedCharEnd = sHelper.addLabeledControl(
			_("End tag"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["undefinedCharsRepr"]["end"],
		)
		values = [lang[1] for lang in languageHandler.getAvailableLanguages()]
		keys = [lang[0] for lang in languageHandler.getAvailableLanguages()]
		undefinedCharLang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
		if not undefinedCharLang in keys:
			undefinedCharLang = keys[-1]
		undefinedCharLangID = keys.index(undefinedCharLang)
		self.undefinedCharLang = sHelper.addLabeledControl(
			_("Language"), wx.Choice, choices=values
		)
		self.undefinedCharLang.SetSelection(undefinedCharLangID)
		values = [_("Use the current output table")] + [
			table.displayName for table in configBE.tables if table.output
		]
		keys = ["current"] + [
			table.fileName for table in configBE.tables if table.output
		]
		undefinedCharTable = config.conf["brailleExtender"]["undefinedCharsRepr"][
			"table"
		]
		if undefinedCharTable not in configBE.tablesFN + ["current"]:
			undefinedCharTable = "current"
		undefinedCharTableID = keys.index(undefinedCharTable)
		self.undefinedCharTable = sHelper.addLabeledControl(
			_("Braille table"), wx.Choice, choices=values
		)
		self.undefinedCharTable.SetSelection(undefinedCharTableID)

	def getHardValue(self):
		selected = self.undefinedCharReprList.GetSelection()
		if selected == configBE.CHOICE_otherDots:
			return config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardDotPatternValue"
			]
		elif selected == configBE.CHOICE_otherSign:
			return config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardSignPatternValue"
			]
		else:
			return ""

	def onUndefinedCharDesc(self, evt):
		l = [
			self.undefinedCharReprEdit,
			self.undefinedCharExtendedDesc,
			self.undefinedCharStart,
			self.undefinedCharEnd,
			self.undefinedCharLang,
			self.undefinedCharTable,
		]
		for e in l:
			if self.undefinedCharDesc.IsChecked():
				e.Enable()
			else:
				e.Disable()

	def onUndefinedCharReprList(self, evt=None):
		selected = self.undefinedCharReprList.GetSelection()
		if selected in [configBE.CHOICE_otherDots, configBE.CHOICE_otherSign]:
			self.undefinedCharReprEdit.Enable()
		else:
			self.undefinedCharReprEdit.Disable()
		self.undefinedCharReprEdit.SetValue(self.getHardValue())

	def postInit(self):
		self.undefinedCharDesc.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"method"
		] = self.undefinedCharReprList.GetSelection()
		repr_ = self.undefinedCharReprEdit.Value
		if self.undefinedCharReprList.GetSelection() == configBE.CHOICE_otherDots:
			repr_ = re.sub("[^0-8\-]", "", repr_).strip("-")
			repr_ = re.sub("\-+", "-", repr_)
			config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardDotPatternValue"
			] = repr_
		else:
			config.conf["brailleExtender"]["undefinedCharsRepr"][
				"hardSignPatternValue"
			] = repr_
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"desc"
		] = self.undefinedCharDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"extendedDesc"
		] = self.undefinedCharExtendedDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"start"
		] = self.undefinedCharStart.Value
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"end"
		] = self.undefinedCharEnd.Value
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"lang"
		] = languageHandler.getAvailableLanguages()[
			self.undefinedCharLang.GetSelection()
		][
			0
		]
		undefinedCharTable = self.undefinedCharTable.GetSelection()
		keys = ["current"] + [
			table.fileName for table in configBE.tables if table.output
		]
		config.conf["brailleExtender"]["undefinedCharsRepr"]["table"] = keys[
			undefinedCharTable
		]


def getExtendedSymbols(locale):
	if locale == "Windows":
		locale = languageHandler.getLanguage()
	try:
		b, u = characterProcessing._getSpeechSymbolsForLocale(locale)
	except LookupError:
		b, u = characterProcessing._getSpeechSymbolsForLocale(
			locale.split("_")[0])
	a = {
		k.strip(): v.replacement.replace(' ', '').strip()
		for k, v in b.symbols.items()
		if len(k) > 1
	}
	a.update(
		{
			k.strip(): v.replacement.replace(' ', '').strip()
			for k, v in u.symbols.items()
			if len(k) > 1
		}
	)
	return a


try:
	extendedSymbols = getExtendedSymbols(
		config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
	)
except BaseException as err:
	extendedSymbols = {}
	log.error(
		f"Unable to load extended symbols for %s: %s"
		% (config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"], err)
	)
