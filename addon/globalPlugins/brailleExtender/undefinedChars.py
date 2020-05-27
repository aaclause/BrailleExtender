# coding: utf-8
# undefinedChars.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import codecs
import json
import re
from collections import namedtuple

import wx

import addonHandler
import brailleInput
import brailleTables
import characterProcessing
import config
import gui
import louis

from . import configBE, huc
from .common import *
from .utils import getCurrentBrailleTables, getTextInBraille
from . import brailleRegionHelper

addonHandler.initTranslation()


HUCDotPattern = "12345678-78-12345678"
undefinedCharPattern = huc.cellDescriptionsToUnicodeBraille(HUCDotPattern)

def getHardValue():
	selected = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if selected == configBE.CHOICE_otherDots:
		return config.conf["brailleExtender"]["undefinedCharsRepr"]["hardDotPatternValue"]
	elif selected == configBE.CHOICE_otherSign:
		return config.conf["brailleExtender"]["undefinedCharsRepr"]["hardSignPatternValue"]
	else: return ''


def setUndefinedChar(t=None):
	if not t or t > CHOICE_HUC6 or t < 0: t = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if t == 0: return
	louis.compileString(getCurrentBrailleTables(), bytes(f"undefined {HUCDotPattern}", "ASCII"))


def getExtendedSymbolsForString(s: str, lang) -> dict:
	global extendedSymbols, localesFail
	if not lang in extendedSymbols:
		try:
			extendedSymbols[lang] = getExtendedSymbols(lang)
		except BaseException:
			log.error(f"Unable to load extended symbols for: {lang}")
			localesFail.append(lang)
	if lang in localesFail:
		lang = "en"
		if not lang in localesFail: extendedSymbols[lang] = getExtendedSymbols(lang)
	return {
		c: (d, [(m.start(), m.end()-1) for m in re.finditer(c, s)])
		for c, d in extendedSymbols[lang].items()
		if c in s
	}


def getAlternativeDescChar(c, method):
	if method in [configBE.CHOICE_HUC6, configBE.CHOICE_HUC8]:
		HUC6 = method == configBE.CHOICE_HUC6
		return huc.translate(c, HUC6=HUC6)
	elif method in [configBE.CHOICE_bin, configBE.CHOICE_oct, configBE.CHOICE_dec, configBE.CHOICE_hex]:
		return getTextInBraille("".join(getUnicodeNotation(c)))
	else: return getUndefinedCharSign(method)


def getDescChar(c, lang="Windows", start="", end=""):
	method = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	if lang == "Windows": lang = languageHandler.getLanguage()
	desc = characterProcessing.processSpeechSymbols(lang, c, characterProcessing.SYMLVL_CHAR).replace(' ', '').strip()
	if not desc or desc == c: return getAlternativeDescChar(c, method)
	return f"{start}{desc}{end}"


def getLiblouisStyle(c):
	if not isinstance(c, str): raise ("wrong type")
	if not c or len(c) > 1: raise ValueError(f"Please provide one character only. Received: {c}")
	if c < 0x10000: return r"\x%.4x" % c
	elif c <= 0x100000: return r"\y%.5x" % c
	else: return r"\z%.6x" % c


def getUnicodeNotation(s, notation=None):
	if not isinstance(s, str): raise ("wrong type")
	if not notation:
		notation = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	matches = {
		configBE.CHOICE_bin: bin,
		configBE.CHOICE_oct: oct,
		configBE.CHOICE_dec: lambda s: s,
		configBE.CHOICE_hex: hex,
		configBE.CHOICE_liblouis: getLiblouisStyle,
	}
	if notation not in matches.keys(): raise ValueError(f"Wrong value ({notation})")
	fn = matches[notation]
	return getTextInBraille("".join(["'%s'" % fn(ord(c)) for c in s]))


def getUndefinedCharSign(method):
	if method == configBE.CHOICE_allDots8: return '⣿'
	elif method == configBE.CHOICE_allDots6: return '⠿'
	elif method == configBE.CHOICE_otherDots: return huc.cellDescriptionsToUnicodeBraille(config.conf["brailleExtender"]["undefinedCharsRepr"]["hardDotPatternValue"])
	elif method == configBE.CHOICE_questionMark: return getTextInBraille('?')
	elif method == configBE.CHOICE_otherSign: return getTextInBraille(config.conf["brailleExtender"]["undefinedCharsRepr"]["hardSignPatternValue"])
	else: return '⠀'

def getReplacement(text, method=None):
	if not method: method = config.conf["brailleExtender"]["undefinedCharsRepr"]["method"]
	out = {}
	if not text: return ''
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]:
		start = config.conf["brailleExtender"]["undefinedCharsRepr"]["start"]
		end = config.conf["brailleExtender"]["undefinedCharsRepr"]["end"]
		if start: start = getTextInBraille(start)
		if end: end = getTextInBraille(end)
		lang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
		table = [config.conf["brailleExtender"]["undefinedCharsRepr"]["table"]]
		return getTextInBraille(getDescChar(
			text,
			lang=lang,
			start=start,
			end=end
		), table)
	elif method in [configBE.CHOICE_HUC6, configBE.CHOICE_HUC8]:
		HUC6 = method == configBE.CHOICE_HUC6
		return huc.translate(text, HUC6=HUC6)
	elif method in [ configBE.CHOICE_bin, configBE.CHOICE_oct, configBE.CHOICE_dec, configBE.CHOICE_hex,]:
		return getUnicodeNotation(text)
	else:
		return getUndefinedCharSign(method)

def undefinedCharProcess(self):
	Repl = brailleRegionHelper.BrailleCellReplacement
	fullExtendedDesc = config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"]
	startTag = config.conf["brailleExtender"]["undefinedCharsRepr"]["start"]
	endTag = config.conf["brailleExtender"]["undefinedCharsRepr"]["end"]
	if startTag: startTag = getTextInBraille(startTag)
	if endTag: endTag = getTextInBraille(endTag)
	lang = config.conf["brailleExtender"]["undefinedCharsRepr"]["lang"]
	table = [config.conf["brailleExtender"]["undefinedCharsRepr"]["table"]]
	undefinedCharsPos = [e for e in brailleRegionHelper.findBrailleCellsPattern(self, undefinedCharPattern)]
	extendedSymbolsRawText = {}
	if config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"] and config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]:
		extendedSymbolsRawText = getExtendedSymbolsForString(self.rawText, lang)
	replacements = []
	for c, v in extendedSymbolsRawText.items():
		for start, end in v[1]:
			if start in undefinedCharsPos:
				toAdd = f":{len(c)}" if config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"] else ''
				replaceBy = getTextInBraille(f"{startTag}{v[0]}{toAdd}{endTag}", table)
				replacements.append(Repl(
					start,
					start if fullExtendedDesc else end,
					replaceBy=getReplacement(c[0]) if fullExtendedDesc else replaceBy,
					insertBefore=replaceBy if fullExtendedDesc else ''
				))
	replacements = [Repl(pos, replaceBy=getReplacement(self.rawText[pos])) for pos in undefinedCharsPos] + replacements
	if not replacements: return
	brailleRegionHelper.replaceBrailleCells(self, replacements)


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
			_("Use braille table behavior") + "(%s)" % _("no description possible"),
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
		self.undefinedCharDesc = sHelper.addItem(
			wx.CheckBox(self, label=_(
				"&Describe undefined characters if possible"))
		)
		self.undefinedCharDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"]
		)
		self.undefinedCharDesc.Bind(wx.EVT_CHECKBOX, self.onUndefinedCharDesc)
		self.extendedDesc = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Also describe e&xtended characters (e.g.: country flags)")
			)
		)
		self.extendedDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"]
		)
		self.extendedDesc.Bind(wx.EVT_CHECKBOX, self.onExtendedDesc)
		self.fullExtendedDesc = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("&Full extended description")
			)
		)
		self.fullExtendedDesc.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"]
		)
		self.showSize = sHelper.addItem(
			wx.CheckBox(
				self,
				label=_("Show the si&ze taken")
			)
		)
		self.showSize.SetValue(
			config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"]
		)
		self.startTag = sHelper.addLabeledControl(
			_("&Start tag"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["undefinedCharsRepr"]["start"],
		)
		self.endTag = sHelper.addLabeledControl(
			_("&End tag"),
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
			_("&Language"), wx.Choice, choices=values
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
			_("Braille &table"), wx.Choice, choices=values
		)
		self.undefinedCharTable.SetSelection(undefinedCharTableID)
		self.onExtendedDesc()
		self.onUndefinedCharDesc()
		self.onUndefinedCharReprList()

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

	def onUndefinedCharDesc(self, evt=None):
		l = [
			self.undefinedCharReprEdit,
			self.extendedDesc,
			self.fullExtendedDesc,
			self.showSize,
			self.startTag,
			self.endTag,
			self.undefinedCharLang,
			self.undefinedCharTable,
		]
		for e in l:
			if self.undefinedCharDesc.IsChecked():
				e.Enable()
			else:
				e.Disable()

	def onExtendedDesc(self, evt=None):
		if self.extendedDesc.IsChecked():
			self.fullExtendedDesc.Enable()
			self.showSize.Enable()
		else:
			self.fullExtendedDesc.Disable()
			self.showSize.Disable()

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
		config.conf["brailleExtender"]["undefinedCharsRepr"]["desc"] = self.undefinedCharDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["extendedDesc"] = self.extendedDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["fullExtendedDesc"] = self.fullExtendedDesc.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"]["showSize"] = self.showSize.IsChecked()
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"start"
		] = self.startTag.Value
		config.conf["brailleExtender"]["undefinedCharsRepr"][
			"end"
		] = self.endTag.Value
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

extendedSymbols = {}
localesFail = []
