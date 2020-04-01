# coding: utf-8
# patchs.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
# This file modify some functions from core.

from __future__ import unicode_literals
import os
import re
import sys
import time
import unicodedata
import struct
import winUser
import nvwave

import api
import appModuleHandler
import braille
import brailleInput
import brailleTables
import characterProcessing
import controlTypes
import config
import core
from . import configBE
import globalCommands
import inputCore
import keyboardHandler
import languageHandler
import louis
import queueHandler
import sayAllHandler
import scriptHandler
import speech
import textInfos
import treeInterceptorHandler
import watchdog
from logHandler import log
import addonHandler
addonHandler.initTranslation()
from . import dictionaries
from . import huc
from .utils import getCurrentChar, getTether, getTextInBraille, getCharFromValue

from .common import *
import louisHelper

instanceGP = None
HUCDotPattern = "12345678-78-12345678"
undefinedCharPattern = huc.cellDescriptionsToUnicodeBraille(HUCDotPattern)

SELECTION_SHAPE = lambda: braille.SELECTION_SHAPE
origFunc = {
	"script_braille_routeTo": globalCommands.GlobalCommands.script_braille_routeTo,
	"update": braille.Region.update,
	"_createTablesString": louis._createTablesString
}

def sayCurrentLine():
	global instanceGP
	if not instanceGP.autoScrollRunning:
		if getTether() == braille.handler.TETHER_REVIEW:
			if config.conf["brailleExtender"]["speakScroll"] in [configBE.CHOICE_focusAndReview, configBE.CHOICE_review]:
				scriptHandler.executeScript(globalCommands.commands.script_review_currentLine, None)
			return
		elif config.conf["brailleExtender"]["speakScroll"] in [configBE.CHOICE_focusAndReview, configBE.CHOICE_focus]:
			obj = api.getFocusObject()
			treeInterceptor = obj.treeInterceptor
			if isinstance(treeInterceptor, treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough: obj = treeInterceptor
			try: info = obj.makeTextInfo(textInfos.POSITION_CARET)
			except (NotImplementedError, RuntimeError):
				info = obj.makeTextInfo(textInfos.POSITION_FIRST)
			info.expand(textInfos.UNIT_LINE)
			speech.speakTextInfo(info, unit=textInfos.UNIT_LINE, reason=controlTypes.REASON_CARET)

def getCurrentBrailleTables(input_=False):
	if instanceGP.BRFMode:
		tables = [
			os.path.join(baseDir, "res", "brf.ctb").encode("UTF-8"),
			os.path.join(brailleTables.TABLES_DIR, "braille-patterns.cti")
		]
	else:
		tables = []
		app = appModuleHandler.getAppModuleForNVDAObject(api.getNavigatorObject())
		if brailleInput.handler._table.fileName == config.conf["braille"]["translationTable"] and app and app.appName != "nvda": tables += dictionaries.dictTables
		if input_: mainTable = os.path.join(brailleTables.TABLES_DIR, brailleInput.handler._table.fileName)
		else: mainTable = os.path.join(brailleTables.TABLES_DIR, config.conf["braille"]["translationTable"])
		tables += [
			mainTable,
			os.path.join(brailleTables.TABLES_DIR, "braille-patterns.cti")
		]
	return tables

# globalCommands.GlobalCommands.script_braille_routeTo()
def script_braille_routeTo(self, gesture):
	obj = obj = api.getNavigatorObject()
	if (config.conf["brailleExtender"]['routingReviewModeWithCursorKeys'] and
			obj.hasFocus and
			braille.handler._cursorPos and
			(obj.role == controlTypes.ROLE_TERMINAL or
			 (obj.role == controlTypes.ROLE_EDITABLETEXT and
			 getTether() == braille.handler.TETHER_REVIEW))):
		speechMode = speech.speechMode
		speech.speechMode = 0
		nb = braille.handler._cursorPos-gesture.routingIndex
		i = 0
		key = "leftarrow" if nb > 0 else "rightarrow"
		while i < abs(nb):
			keyboardHandler.KeyboardInputGesture.fromName(key).send()
			i += 1
		speech.speechMode = speechMode
		speech.speakSpelling(getCurrentChar())
		return
	braille.handler.routeTo(gesture.routingIndex)
	if scriptHandler.getLastScriptRepeatCount() == 0 and config.conf["brailleExtender"]['speakRoutingTo']:
		ch = getCurrentChar()
		if ch: speech.speakSpelling(ch)

# braille.Region.update()
def update(self):
	"""Update this region.
	Subclasses should extend this to update L{rawText}, L{cursorPos}, L{selectionStart} and L{selectionEnd} if necessary.
	The base class method handles translation of L{rawText} into braille, placing the result in L{brailleCells}.
	Typeform information from L{rawTextTypeforms} is used, if any.
	L{rawToBraillePos} and L{brailleToRawPos} are updated according to the translation.
	L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are similarly updated based on L{cursorPos}, L{selectionStart} and L{selectionEnd}, respectively.
	@postcondition: L{brailleCells}, L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are updated and ready for rendering.
	"""
	mode = louis.dotsIO
	if config.conf["braille"]["expandAtCursor"] and self.cursorPos is not None: mode |= louis.compbrlAtCursor
	self.brailleCells, self.brailleToRawPos, self.rawToBraillePos, self.brailleCursorPos = louisHelper.translate(
		getCurrentBrailleTables(),
		self.rawText,
		typeform=self.rawTextTypeforms,
		mode=mode,
		cursorPos=self.cursorPos
	)
	if config.conf["brailleExtender"]["undefinedCharReprMethod"] in [configBE.CHOICE_liblouis, configBE.CHOICE_HUC8, configBE.CHOICE_HUC6, configBE.CHOICE_hex, configBE.CHOICE_dec, configBE.CHOICE_oct, configBE.CHOICE_bin]: undefinedCharProcess(self)
	if self.selectionStart is not None and self.selectionEnd is not None:
		try:
			# Mark the selection.
			self.brailleSelectionStart = self.rawToBraillePos[self.selectionStart]
			if self.selectionEnd >= len(self.rawText):
				self.brailleSelectionEnd = len(self.brailleCells)
			else:
				self.brailleSelectionEnd = self.rawToBraillePos[self.selectionEnd]
			for pos in range(self.brailleSelectionStart, self.brailleSelectionEnd):
				self.brailleCells[pos] |= SELECTION_SHAPE()
		except IndexError: pass
	else:
		if instanceGP and instanceGP.hideDots78:
			self.brailleCells = [(cell & 63) for cell in self.brailleCells]
	if config.conf["brailleExtender"]["readingRightToLeft"]:
		if self.cursorPos is not None:
			self.cursorPos = len(self.brailleCells)-1-self.cursorPos
		self.brailleCells = self.brailleCells[::-1]
		self.brailleToRawPos = self.brailleToRawPos[::-1]
		self.rawToBraillePos = self.rawToBraillePos[::-1]

def setUndefinedChar(t=None):
	if not t or t > CHOICE_HUC6 or t < 0: t = config.conf["brailleExtender"]["undefinedCharReprMethod"]
	if t == 0: return
	c = ["default", "12345678", "123456", '0', config.conf["brailleExtender"]["undefinedCharRepr"], "questionMark", "sign"] + [HUCDotPattern]*7
	v = c[t]
	if v in ["questionMark", "sign"]:
		if v == "questionMark": s = '?'
		else: s = config.conf["brailleExtender"]["undefinedCharRepr"]
		v = huc.unicodeBrailleToDescription(getTextInBraille(s, getCurrentBrailleTables()))
	louis.compileString(getCurrentBrailleTables(), bytes("undefined %s" % v, "ASCII"))


def getDescChar(c, lang="Windows", start='', end=''):
	if lang == "Windows": lang = languageHandler.getLanguage()
	desc = characterProcessing.processSpeechSymbols(lang, c, characterProcessing.SYMLVL_CHAR).strip()
	if not desc or desc == c:
		if config.conf["brailleExtender"]["undefinedCharReprMethod"] in [configBE.CHOICE_HUC6, configBE.CHOICE_HUC8]:
			HUC6 = config.conf["brailleExtender"]["undefinedCharReprMethod"] == configBE.CHOICE_HUC6
			return huc.translate(c, HUC6=HUC6)
		else: return getTextInBraille(''.join(getNotationOrd(c)))
	return start + desc + end

def getLiblouisStyle(c):
	if c < 0x10000: return r"\x%.4x" % c
	elif c <= 0x100000: return r"\y%.5x" % c
	else: return r"\z%.6x" % c

def getNotationOrd(s, notation=None):
	if not notation: notation = config.conf["brailleExtender"]["undefinedCharReprMethod"]
	matches = {
		configBE.CHOICE_bin: bin,
		configBE.CHOICE_oct: oct,
		configBE.CHOICE_dec: lambda s: s,
		configBE.CHOICE_hex: hex,
		configBE.CHOICE_liblouis: getLiblouisStyle,
	}
	fn = matches[notation]
	s = getTextInBraille(''.join(["'%s'" % fn(ord(c)) for c in s]))
	return s

def undefinedCharProcess(self):
	unicodeBrailleRepr = ''.join([chr(10240 + cell) for cell in self.brailleCells])
	allBraillePos = [m.start() for m in re.finditer(undefinedCharPattern, unicodeBrailleRepr)]
	if not allBraillePos: return
	if config.conf["brailleExtender"]["undefinedCharDesc"]:
		start = config.conf["brailleExtender"]["undefinedCharStart"]
		end = config.conf["brailleExtender"]["undefinedCharEnd"]
		if start: start = getTextInBraille(start)
		if end: end = getTextInBraille(end)
		replacements = {braillePos:
			getTextInBraille(
				getDescChar(
					self.rawText[self.brailleToRawPos[braillePos]],
					lang=config.conf["brailleExtender"]["undefinedCharLang"],
					start=start,
					end=end,
				),
				table=[config.conf["brailleExtender"]["undefinedCharBrailleTable"]]
			) for braillePos in allBraillePos}
	elif config.conf["brailleExtender"]["undefinedCharReprMethod"] in [configBE.CHOICE_HUC6, configBE.CHOICE_HUC8]:
		HUC6 = config.conf["brailleExtender"]["undefinedCharReprMethod"] == configBE.CHOICE_HUC6
		replacements = {braillePos: huc.translate(self.rawText[self.brailleToRawPos[braillePos]], HUC6=HUC6) for braillePos in allBraillePos}
	else:
		replacements = {braillePos: getNotationOrd(self.rawText[self.brailleToRawPos[braillePos]]) for braillePos in allBraillePos}
	newBrailleCells = []
	newBrailleToRawPos = []
	newRawToBraillePos = []
	lenBrailleToRawPos = len(self.brailleToRawPos)
	alreadyDone = []
	i = 0
	for iBrailleCells, brailleCells in enumerate(self.brailleCells):
		brailleToRawPos = self.brailleToRawPos[iBrailleCells]
		if iBrailleCells in replacements and not replacements[iBrailleCells].startswith(undefinedCharPattern[0]):
			toAdd = [ord(c)-10240 for c in replacements[iBrailleCells]]
			newBrailleCells += toAdd
			newBrailleToRawPos += [i] * len(toAdd)
			alreadyDone += list(range(iBrailleCells, iBrailleCells+3))
			i += 1
		else:
			if iBrailleCells in alreadyDone: continue
			newBrailleCells.append(self.brailleCells[iBrailleCells])
			newBrailleToRawPos += [i]
			if (iBrailleCells + 1) < lenBrailleToRawPos and self.brailleToRawPos[iBrailleCells+1] != brailleToRawPos:
				i += 1
	pos = -42
	for i, brailleToRawPos in enumerate(newBrailleToRawPos):
		if brailleToRawPos != pos:
			pos = brailleToRawPos
			newRawToBraillePos.append(i)
	self.brailleCells = newBrailleCells
	self.brailleToRawPos = newBrailleToRawPos
	self.rawToBraillePos = newRawToBraillePos
	if self.cursorPos: self.brailleCursorPos = self.rawToBraillePos[self.cursorPos]

#: braille.TextInfoRegion.nextLine()
def nextLine(self):
	try:
		dest = self._readingInfo.copy()
		moved = dest.move(self._getReadingUnit(), 1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try: dest.obj.turnPage()
				except RuntimeError: pass
				else: dest = dest.obj.makeTextInfo(textInfos.POSITION_FIRST)
			else: return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException: pass

#: braille.TextInfoRegion.previousLine()
def previousLine(self, start=False):
	try:
		dest = self._readingInfo.copy()
		dest.collapse()
		if start: unit = self._getReadingUnit()
		else: unit = textInfos.UNIT_CHARACTER
		moved = dest.move(unit, -1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try: dest.obj.turnPage(previous=True)
				except RuntimeError: pass
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_LAST)
					dest.expand(unit)
			else: return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException: pass

#: inputCore.InputManager.executeGesture
def executeGesture(self, gesture):
		"""Perform the action associated with a gesture.
		@param gesture: The gesture to execute.
		@type gesture: L{InputGesture}
		@raise NoInputGestureAction: If there is no action to perform.
		"""
		if watchdog.isAttemptingRecovery:
			# The core is dead, so don't try to perform an action.
			# This lets gestures pass through unhindered where possible,
			# as well as stopping a flood of actions when the core revives.
			raise NoInputGestureAction

		script = gesture.script
		if "brailleDisplayDrivers" in str(type(gesture)):
			if instanceGP.brailleKeyboardLocked and ((hasattr(script, "__func__") and script.__func__.__name__ != "script_toggleLockBrailleKeyboard") or not hasattr(script, "__func__")): return
			if not config.conf["brailleExtender"]['stopSpeechUnknown'] and gesture.script == None: stopSpeech = False
			elif hasattr(script, "__func__") and (script.__func__.__name__ in [
			"script_braille_dots", "script_braille_enter",
			"script_volumePlus", "script_volumeMinus", "script_toggleVolume",
			"script_hourDate",
			"script_ctrl", "script_alt", "script_nvda", "script_win",
			"script_ctrlAlt", "script_ctrlAltWin", "script_ctrlAltWinShift", "script_ctrlAltShift","script_ctrlWin","script_ctrlWinShift","script_ctrlShift","script_altWin","script_altWinShift","script_altShift","script_winShift"]
			or (
				not config.conf["brailleExtender"]['stopSpeechScroll'] and
			script.__func__.__name__ in ["script_braille_scrollBack","script_braille_scrollForward"])):
				stopSpeech = False
			else: stopSpeech = True
		else: stopSpeech = True

		focus = api.getFocusObject()
		if focus.sleepMode is focus.SLEEP_FULL or (focus.sleepMode and not getattr(script, 'allowInSleepMode', False)):
			raise NoInputGestureAction

		wasInSayAll=False
		if gesture.isModifier:
			if not self.lastModifierWasInSayAll:
				wasInSayAll=self.lastModifierWasInSayAll=sayAllHandler.isRunning()
		elif self.lastModifierWasInSayAll:
			wasInSayAll=True
			self.lastModifierWasInSayAll=False
		else:
			wasInSayAll=sayAllHandler.isRunning()
		if wasInSayAll:
			gesture.wasInSayAll=True

		speechEffect = gesture.speechEffectWhenExecuted
		if not stopSpeech: pass
		elif speechEffect == gesture.SPEECHEFFECT_CANCEL:
			queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
		elif speechEffect in (gesture.SPEECHEFFECT_PAUSE, gesture.SPEECHEFFECT_RESUME):
			queueHandler.queueFunction(queueHandler.eventQueue, speech.pauseSpeech, speechEffect == gesture.SPEECHEFFECT_PAUSE)

		if log.isEnabledFor(log.IO) and not gesture.isModifier:
			self._lastInputTime = time.time()
			log.io("Input: %s" % gesture.identifiers[0])

		if self._captureFunc:
			try:
				if self._captureFunc(gesture) is False:
					return
			except BaseException:
				log.error("Error in capture function, disabling", exc_info=True)
				self._captureFunc = None

		if gesture.isModifier:
			raise NoInputGestureAction

		if config.conf["keyboard"]["speakCommandKeys"] and gesture.shouldReportAsCommand:
			queueHandler.queueFunction(queueHandler.eventQueue, speech.speakMessage, gesture.displayName)

		gesture.reportExtra()

		# #2953: if an intercepted command Script (script that sends a gesture) is queued
		# then queue all following gestures (that don't have a script) with a fake script so that they remain in order.
		if not script and scriptHandler._numIncompleteInterceptedCommandScripts:
			script=lambda gesture: gesture.send()


		if script:
			scriptHandler.queueScript(script, gesture)
			return

		raise NoInputGestureAction
#: brailleInput.BrailleInputHandler.sendChars()
def sendChars(self, chars):
	"""Sends the provided unicode characters to the system.
	@param chars: The characters to send to the system.
	"""
	inputs = []
	chars = ''.join(c if ord(c) <= 0xffff else ''.join(chr(x) for x in struct.unpack('>2H', c.encode("utf-16be"))) for c in chars)
	for ch in chars:
		for direction in (0,winUser.KEYEVENTF_KEYUP):
			input = winUser.Input()
			input.type = winUser.INPUT_KEYBOARD
			input.ii.ki = winUser.KeyBdInput()
			input.ii.ki.wScan = ord(ch)
			input.ii.ki.dwFlags = winUser.KEYEVENTF_UNICODE|direction
			inputs.append(input)
	winUser.SendInput(inputs)
	focusObj = api.getFocusObject()
	if keyboardHandler.shouldUseToUnicodeEx(focusObj):
		# #10569: When we use ToUnicodeEx to detect typed characters,
		# emulated keypresses aren't detected.
		# Send TypedCharacter events manually.
		for ch in chars:
			focusObj.event_typedCharacter(ch=ch)

#: brailleInput.BrailleInputHandler.emulateKey()
def emulateKey(self, key, withModifiers=True):
	"""Emulates a key using the keyboard emulation system.
	If emulation fails (e.g. because of an unknown key), a debug warning is logged
	and the system falls back to sending unicode characters.
	@param withModifiers: Whether this key emulation should include the modifiers that are held virtually.
		Note that this method does not take care of clearing L{self.currentModifiers}.
	@type withModifiers: bool
	"""
	if withModifiers:
		# The emulated key should be the last item in the identifier string.
		keys = list(self.currentModifiers)
		keys.append(key)
		gesture = "+".join(keys)
	else:
		gesture = key
	try:
		inputCore.manager.emulateGesture(keyboardHandler.KeyboardInputGesture.fromName(gesture))
		instanceGP.lastShortcutPerformed = gesture
	except BaseException:
		log.debugWarning("Unable to emulate %r, falling back to sending unicode characters"%gesture, exc_info=True)
		self.sendChars(key)

#: brailleInput.BrailleInputHandler.input()
def input_(self, dots):
	"""Handle one cell of braille input.
	"""
	# Insert the newly entered cell into the buffer at the cursor position.
	pos = self.untranslatedStart + self.untranslatedCursorPos
	# Space ends the word.
	endWord = dots == 0
	continue_ = True
	if config.conf["brailleExtender"]["oneHandMode"]:
		continue_, endWord = processOneHandMode(self, dots)
		if not continue_: return
	else:
		self.bufferBraille.insert(pos, dots)
		self.untranslatedCursorPos += 1
	ok = False
	if instanceGP:
		focusObj = api.getFocusObject()
		ok = not self.currentModifiers and (not focusObj.treeInterceptor or focusObj.treeInterceptor.passThrough)
	if instanceGP.advancedInput and ok:
		pos = self.untranslatedStart + self.untranslatedCursorPos
		advancedInputStr = ''.join([chr(cell | 0x2800) for cell in self.bufferBraille[:pos]])
		if advancedInputStr:
			if advancedInputStr[0] in "⠃⠙⠓⠕⠭⡃⡙⡓⡕⡭":
				equiv = {'⠃': 'b', '⠙': 'd', '⠓': 'h', '⠕': 'o', '⠭': 'x', '⡃': 'B', '⡙': 'D', '⡓': 'H', '⡕': 'O', '⡭': 'X'}
				if advancedInputStr[-1] == '⠀':
					text = equiv[advancedInputStr[0]]+louis.backTranslate(getCurrentBrailleTables(True), advancedInputStr[1:-1])[0]
					try:
						char = getCharFromValue(text)
						sendChar(char)
					except BaseException as err:
							speech.speakMessage(repr(err))
							badInput(self)
				else: self._reportUntranslated(pos)
				return
			else:
				res = huc.isValidHUCInput(advancedInputStr)
				if res == huc.HUC_INPUT_INCOMPLETE: return self._reportUntranslated(pos)
				elif res == huc.HUC_INPUT_INVALID: badInput(self)
				else:
					res = huc.backTranslate(advancedInputStr)
					sendChar(res)
		return
	# For uncontracted braille, translate the buffer for each cell added.
	# Any new characters produced are then sent immediately.
	# For contracted braille, translate the buffer only when a word is ended (i.e. a space is typed).
	# This is because later cells can change characters produced by previous cells.
	# For example, in English grade 2, "tg" produces just "tg",
	# but "tgr" produces "together".
	if not self.useContractedForCurrentFocus or endWord:
		if self._translate(endWord):
			if not endWord:
				self.cellsWithText.add(pos)
		elif self.bufferText and not self.useContractedForCurrentFocus:
			# Translators: Reported when translation didn't succeed due to unsupported input.
			speech.speakMessage(_("Unsupported input"))
			self.flushBuffer()
		else:
			# This cell didn't produce any text; e.g. number sign.
			self._reportUntranslated(pos)
	else:
		self._reportUntranslated(pos)

endChar = True
def processOneHandMode(self, dots):
	global endChar
	addSpace = False
	method = config.conf["brailleExtender"]["oneHandMethod"]
	pos = self.untranslatedStart + self.untranslatedCursorPos
	continue_ = True
	endWord = False
	if method == configBE.CHOICE_oneHandMethodSides:
		endChar = not endChar
		if dots == 0:
			endChar = endWord = True
			addSpace = True
	elif method == configBE.CHOICE_oneHandMethodSide:
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
				translatedBufferBrailleDots = huc.unicodeBrailleToDescription(translatedBufferBraille)
			translatedDots = chr(dots | 0x2800)
			translatedDotsBrailleDots = huc.unicodeBrailleToDescription(translatedDots)
			newDots = ""
			for dot in translatedDotsBrailleDots:
				dot = int(dot)
				if dots >= 0 and dot < 9: newDots += equiv[dot]
			newDots = ''.join(sorted(set(newDots)))
			if not newDots: newDots = "0"
			dots = ord(huc.cellDescriptionsToUnicodeBraille(newDots))-0x2800
	elif method == configBE.CHOICE_oneHandMethodDots:
		endChar = dots == 0
		translatedBufferBrailleDots = "0"
		if self.bufferBraille:
			translatedBufferBraille = chr(self.bufferBraille[-1] | 0x2800)
			translatedBufferBrailleDots = huc.unicodeBrailleToDescription(translatedBufferBraille)
		translatedDots = chr(dots | 0x2800)
		translatedDotsBrailleDots = huc.unicodeBrailleToDescription(translatedDots)
		for dot in translatedDotsBrailleDots:
			if dot not in translatedBufferBrailleDots: translatedBufferBrailleDots += dot
			else: translatedBufferBrailleDots = translatedBufferBrailleDots.replace(dot, '')
		if not translatedBufferBrailleDots: translatedBufferBrailleDots = "0"
		newDots = ''.join(sorted(set(translatedBufferBrailleDots)))
		log.info("===> " + newDots)
		dots = ord(huc.cellDescriptionsToUnicodeBraille(newDots))-0x2800
	else:
		speech.speakMessage(_("Unsupported input method"))
		self.flushBuffer()
		return False, False
	if endChar:
		if not self.bufferBraille: self.bufferBraille.insert(pos, 0)
		if method == configBE.CHOICE_oneHandMethodDots:
			self.bufferBraille[-1] = dots
		else: self.bufferBraille[-1] |= dots
		if not endWord: endWord = self.bufferBraille[-1] == 0
		if method == configBE.CHOICE_oneHandMethodDots:
			self.bufferBraille.append(0)
		self.untranslatedCursorPos += 1
		if addSpace:
			self.bufferBraille.append(0)
			self.untranslatedCursorPos += 1
	else:
		continue_ = False
		if self.bufferBraille and method == configBE.CHOICE_oneHandMethodDots: self.bufferBraille[-1] = dots
		else: self.bufferBraille.insert(pos, dots)
		self._reportUntranslated(pos)
	return continue_, endWord

#: brailleInput.BrailleInputHandler._translate()
# reason for patching: possibility to lock modifiers, display modifiers in braille during input, HUC Braille input

def sendChar(char):
	nvwave.playWaveFile(os.path.join(configBE.baseDir, "res/sounds/keyPress.wav"))
	core.callLater(0, brailleInput.handler.sendChars, char)
	core.callLater(100, speech.speakSpelling, char)

def badInput(self):
	nvwave.playWaveFile("waves/textError.wav")
	self.flushBuffer()
	pos = self.untranslatedStart + self.untranslatedCursorPos
	self._reportUntranslated(pos)

def _translate(self, endWord):
	"""Translate buffered braille up to the cursor.
	Any text produced is sent to the system.
	@param endWord: C{True} if this is the end of a word, C{False} otherwise.
	@type endWord: bool
	@return: C{True} if translation produced text, C{False} if not.
	@rtype: bool
	"""
	assert not self.useContractedForCurrentFocus or endWord, "Must only translate contracted at end of word"
	if self.useContractedForCurrentFocus:
		# self.bufferText has been used by _reportContractedCell, so clear it.
		self.bufferText = u""
	oldTextLen = len(self.bufferText)
	pos = self.untranslatedStart + self.untranslatedCursorPos
	data = u"".join([chr(cell | brailleInput.LOUIS_DOTS_IO_START) for cell in self.bufferBraille[:pos]])
	mode = louis.dotsIO | louis.noUndefinedDots
	if (not self.currentFocusIsTextObj or self.currentModifiers) and self._table.contracted:
		mode |=  louis.partialTrans
	self.bufferText = louis.backTranslate(getCurrentBrailleTables(True),
		data, mode=mode)[0]
	newText = self.bufferText[oldTextLen:]
	if newText:
		# New text was generated by the cells just entered.
		if self.useContractedForCurrentFocus or self.currentModifiers:
			# For contracted braille, an entire word is sent at once.
			# Don't speak characters as this is sent.
			# Also, suppress typed characters when emulating a command gesture.
			speech._suppressSpeakTypedCharacters(len(newText))
		else:
			self._uncontSentTime = time.time()
		self.untranslatedStart = pos
		self.untranslatedCursorPos = 0
		if self.currentModifiers or not self.currentFocusIsTextObj:
			if len(newText)>1:
				# Emulation of multiple characters at once is unsupported
				# Clear newText, so this function returns C{False} if not at end of word
				newText = u""
			else:
				self.emulateKey(newText)
		else:
			self.sendChars(newText)

	if endWord or (newText and (not self.currentFocusIsTextObj or self.currentModifiers)):
		# We only need to buffer one word.
		# Clear the previous word (anything before the cursor) from the buffer.
		del self.bufferBraille[:pos]
		self.bufferText = u""
		self.cellsWithText.clear()
		if not instanceGP.modifiersLocked:
			self.currentModifiers.clear()
			instanceGP.clearMessageFlash()
		self.untranslatedStart = 0
		self.untranslatedCursorPos = 0

	if newText or endWord:
		self._updateUntranslated()
		return True

	return False

#: louis._createTablesString()
def _createTablesString(tablesList):
	"""Creates a tables string for liblouis calls"""
	return b",".join([x.encode("mbcs") if isinstance(x, str) else bytes(x) for x in tablesList])

# applying patches
braille.Region.update = update
braille.TextInfoRegion.previousLine = previousLine
braille.TextInfoRegion.nextLine = nextLine
inputCore.InputManager.executeGesture = executeGesture
NoInputGestureAction = inputCore.NoInputGestureAction
brailleInput.BrailleInputHandler._translate = _translate
brailleInput.BrailleInputHandler.emulateKey = emulateKey
brailleInput.BrailleInputHandler.input = input_
brailleInput.BrailleInputHandler.sendChars = sendChars
globalCommands.GlobalCommands.script_braille_routeTo = script_braille_routeTo
louis._createTablesString = _createTablesString
script_braille_routeTo.__doc__ = origFunc["script_braille_routeTo"].__doc__

