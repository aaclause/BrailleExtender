# coding: utf-8
# oneHandMode.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import gui
import wx
import addonHandler
addonHandler.initTranslation()
import config
from .utils import unicodeBrailleToDescription, descriptionToUnicodeBraille

CHOICE_oneHandMethodSides = 0
CHOICE_oneHandMethodSide = 1
CHOICE_oneHandMethodDots = 2

CHOICE_oneHandMethods = dict([
	(CHOICE_oneHandMethodSides, _("Fill a cell in two stages on both sides")),
	(CHOICE_oneHandMethodSide, _("Fill a cell in two stages on one side (space = empty side)")),
	(CHOICE_oneHandMethodDots,  _("Fill a cell dots by dots (each dot is a toggle, press space to validate the character)"))
])

endChar = True

def process(self, dots):
	global endChar
	addSpace = False
	method = config.conf["brailleExtender"]["oneHandMethod"]
	pos = self.untranslatedStart + self.untranslatedCursorPos
	continue_ = True
	endWord = False
	if method == CHOICE_oneHandMethodSides:
		endChar = not endChar
		if dots == 0:
			endChar = endWord = True
			addSpace = True
	elif method == CHOICE_oneHandMethodSide:
		endChar = not endChar
		if endChar: equiv = "045645688"
		else:
			equiv = "012312377"
			if dots == 0:
				endChar = endWord = True
				addSpace = True
		if dots != 0:
			translatedBufferBrailleDots = 0
			if self.bufferBraille:
				translatedBufferBraille = chr(self.bufferBraille[-1] | 0x2800)
				translatedBufferBrailleDots = unicodeBrailleToDescription(translatedBufferBraille)
			translatedDots = chr(dots | 0x2800)
			translatedDotsBrailleDots = unicodeBrailleToDescription(translatedDots)
			newDots = ""
			for dot in translatedDotsBrailleDots:
				dot = int(dot)
				if dots >= 0 and dot < 9: newDots += equiv[dot]
			newDots = ''.join(sorted(set(newDots)))
			if not newDots: newDots = "0"
			dots = ord(descriptionToUnicodeBraille(newDots))-0x2800
	elif method == CHOICE_oneHandMethodDots:
		endChar = dots == 0
		translatedBufferBrailleDots = "0"
		if self.bufferBraille:
			translatedBufferBraille = chr(self.bufferBraille[-1] | 0x2800)
			translatedBufferBrailleDots = unicodeBrailleToDescription(translatedBufferBraille)
		translatedDots = chr(dots | 0x2800)
		translatedDotsBrailleDots = unicodeBrailleToDescription(translatedDots)
		for dot in translatedDotsBrailleDots:
			if dot not in translatedBufferBrailleDots: translatedBufferBrailleDots += dot
			else: translatedBufferBrailleDots = translatedBufferBrailleDots.replace(dot, '')
		if not translatedBufferBrailleDots: translatedBufferBrailleDots = "0"
		newDots = ''.join(sorted(set(translatedBufferBrailleDots)))
		dots = ord(descriptionToUnicodeBraille(newDots))-0x2800
	else:
		speech.speakMessage(_("Unsupported input method"))
		self.flushBuffer()
		return False, False
	if endChar:
		if not self.bufferBraille: self.bufferBraille.insert(pos, 0)
		if method == CHOICE_oneHandMethodDots:
			self.bufferBraille[-1] = dots
		else: self.bufferBraille[-1] |= dots
		if not endWord: endWord = self.bufferBraille[-1] == 0
		if method == CHOICE_oneHandMethodDots:
			self.bufferBraille.append(0)
		self.untranslatedCursorPos += 1
		if addSpace:
			self.bufferBraille.append(0)
			self.untranslatedCursorPos += 1
	else:
		continue_ = False
		if self.bufferBraille and method == CHOICE_oneHandMethodDots: self.bufferBraille[-1] = dots
		else: self.bufferBraille.insert(pos, dots)
		self._reportUntranslated(pos)
	return continue_, endWord

class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("One-hand mode")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.oneHandMode = sHelper.addItem(wx.CheckBox(self, label=_("Enable this feature")))
		self.oneHandMode.SetValue(config.conf["brailleExtender"]["oneHandMode"])
		self.oneHandMode.Bind(wx.EVT_CHECKBOX, self.onOneHandMode)
		choices = list(CHOICE_oneHandMethods.values())
		itemToSelect = list(CHOICE_oneHandMethods.keys()).index(config.conf["brailleExtender"]["oneHandMethod"])
		self.oneHandMethod = sHelper.addLabeledControl(_("Input method"), wx.Choice, choices=choices)
		self.oneHandMethod.SetSelection(itemToSelect)
		self.onOneHandMode(None)

	def onOneHandMode(self, evt):
		if self.oneHandMode.IsChecked(): self.oneHandMethod.Enable()
		else: self.oneHandMethod.Disable()

	def onSave(self):
		config.conf["brailleExtender"]["oneHandMode"] = self.oneHandMode.IsChecked()
		config.conf["brailleExtender"]["oneHandMethod"] = list(CHOICE_oneHandMethods.keys())[self.oneHandMethod.GetSelection()]
