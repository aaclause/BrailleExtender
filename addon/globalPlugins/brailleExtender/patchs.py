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

import api
import appModuleHandler
import braille
import brailleInput
import brailleTables
import controlTypes
import config
import core
import globalCommands
import inputCore
import keyboardHandler
import louis
import louisHelper
import nvwave
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

from . import advancedInputMode
from . import brailleRegionHelper
from . import configBE
from . import dictionaries
from . import huc
from .objectPresentation import getPropertiesBraille, selectedElementEnabled
from . import undefinedChars
from .oneHandMode import process as processOneHandMode
from .utils import getCurrentChar, getSpeechSymbols, getTether, getCharFromValue, getCurrentBrailleTables
from .common import *

instanceGP = None

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
	try: braille.handler.routeTo(gesture.routingIndex)
	except LookupError: pass
	if scriptHandler.getLastScriptRepeatCount() == 0 and config.conf["brailleExtender"]["speakRoutingTo"]:
		region = braille.handler.buffer
		if region.cursorPos is None: return
		try:
			start = region.brailleToRawPos[braille.handler.buffer.windowStartPos + gesture.routingIndex]
			_, endBraillePos = brailleRegionHelper.getBraillePosFromRawPos(region, start)
			end = region.brailleToRawPos[endBraillePos+1]
			ch = region.rawText[start:end]
			if ch:
				speech.speakMessage(getSpeechSymbols(ch))
		except IndexError: pass

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
	if config.conf["brailleExtender"]["advanced"]["fixCursorPositions"]:
		pattern = r"([^\ufe00-\ufe0f])[\ufe00-\ufe0f]\u20E3?"
		matches = re.finditer(pattern, self.rawText)
		posToRemove = []
		for match in matches:
			posToRemove += list(range(match.start() + 1, match.end()))
		self.rawText = re.sub(pattern, r"\1", self.rawText)
		if isinstance(self.cursorPos, int):
			adjustCursor = len(list(filter(lambda e: e<=self.cursorPos, posToRemove)))
			self.cursorPos -= adjustCursor
		if isinstance(self.selectionStart, int):
			adjustCursor = len(list(filter(lambda e: e<=self.selectionStart, posToRemove)))
			self.selectionStart -= adjustCursor
		if isinstance(self.selectionEnd, int):
			adjustCursor = len(list(filter(lambda e: e<=self.selectionEnd, posToRemove)))
			self.selectionEnd -= adjustCursor
	mode = louis.dotsIO
	if config.conf["braille"]["expandAtCursor"] and self.cursorPos is not None: mode |= louis.compbrlAtCursor
	self.brailleCells, self.brailleToRawPos, self.rawToBraillePos, self.brailleCursorPos = louisHelper.translate(
		getCurrentBrailleTables(brf=False if instanceGP else False),
		self.rawText,
		typeform=self.rawTextTypeforms,
		mode=mode,
		cursorPos=self.cursorPos
	)
	if self.parseUndefinedChars == True and config.conf["brailleExtender"]["undefinedCharsRepr"]["method"] != undefinedChars.CHOICE_tableBehaviour:
		undefinedChars.undefinedCharProcess(self)
	if selectedElementEnabled():
		d = {
			configBE.CHOICE_dot7: 64,
			configBE.CHOICE_dot8: 128,
			configBE.CHOICE_dots78: 192
		}
		if config.conf["brailleExtender"]["objectPresentation"]["selectedElement"] in d:
			addDots = d[config.conf["brailleExtender"]["objectPresentation"]["selectedElement"]]
			if hasattr(self, "obj") and self.obj and hasattr(self.obj, "states") and self.obj.states and self.obj.name and controlTypes.STATE_SELECTED in self.obj.states:
				name = self.obj.name
				if name in self.rawText:
					start = self.rawText.index(name)
					end = start + len(name)-1
					startBraillePos, _ = brailleRegionHelper.getBraillePosFromRawPos(self, start)
					_, endBraillePos = brailleRegionHelper.getBraillePosFromRawPos(self, end)
					self.brailleCells = [cell | addDots if startBraillePos <= pos <= endBraillePos else cell for pos, cell in enumerate(self.brailleCells)]
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
	if config.conf["brailleExtender"]["oneHandedMode"]["enabled"]:
		continue_, endWord = processOneHandMode(self, dots)
		if not continue_: return
	else:
		self.bufferBraille.insert(pos, dots)
		self.untranslatedCursorPos += 1
	ok = False
	if instanceGP:
		focusObj = api.getFocusObject()
		ok = not self.currentModifiers and (not focusObj.treeInterceptor or focusObj.treeInterceptor.passThrough)
	if instanceGP and instanceGP.advancedInput and ok:
		pos = self.untranslatedStart + self.untranslatedCursorPos
		advancedInputStr = ''.join([chr(cell | 0x2800) for cell in self.bufferBraille[:pos]])
		if advancedInputStr:
			res = ''
			abreviations = advancedInputMode.getReplacements([advancedInputStr])
			startUnicodeValue = "⠃⠙⠓⠕⠭⡃⡙⡓⡕⡭"
			if not abreviations and advancedInputStr[0] in startUnicodeValue: advancedInputStr = config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"] + advancedInputStr
			lenEscapeSign = len(config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"])
			if advancedInputStr == config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"] or (advancedInputStr.startswith(config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"]) and len(advancedInputStr) > lenEscapeSign and advancedInputStr[lenEscapeSign] in startUnicodeValue):
				equiv = {'⠃': 'b', '⠙': 'd', '⠓': 'h', '⠕': 'o', '⠭': 'x', '⡃': 'B', '⡙': 'D', '⡓': 'H', '⡕': 'O', '⡭': 'X'}
				if advancedInputStr[-1] == '⠀':
					text = equiv[advancedInputStr[1]] + louis.backTranslate(getCurrentBrailleTables(True, brf=instanceGP.BRFMode), advancedInputStr[2:-1])[0]
					try:
						res = getCharFromValue(text)
						sendChar(res)
					except BaseException as err:
							speech.speakMessage(repr(err))
							return badInput(self)
				else: self._reportUntranslated(pos)
			elif abreviations:
				if len(abreviations) == 1:
					res = abreviations[0].replaceBy
					sendChar(res)
				else: return self._reportUntranslated(pos)
			else:
				res = huc.isValidHUCInput(advancedInputStr)
				if res == huc.HUC_INPUT_INCOMPLETE: return self._reportUntranslated(pos)
				elif res == huc.HUC_INPUT_INVALID: return badInput(self)
				else:
					res = huc.backTranslate(advancedInputStr)
					sendChar(res)
			if res and config.conf["brailleExtender"]["advancedInputMode"]["stopAfterOneChar"]:
				instanceGP.advancedInput = False
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

#: brailleInput.BrailleInputHandler._translate()
# reason for patching: possibility to lock modifiers, display modifiers in braille during input, HUC Braille input

def sendChar(char):
	nvwave.playWaveFile(os.path.join(configBE.baseDir, "res/sounds/keyPress.wav"))
	core.callLater(0, brailleInput.handler.sendChars, char)
	if len(char) == 1:
		core.callLater(100, speech.speakSpelling, char)
	else: core.callLater(100, speech.speakMessage, char)

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
	self.bufferText = louis.backTranslate(getCurrentBrailleTables(True, brf=instanceGP.BRFMode),
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
	return b",".join([x.encode(sys.getfilesystemencoding()) if isinstance(x, str) else bytes(x) for x in tablesList])

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
braille.getPropertiesBraille = getPropertiesBraille

# This variable tells if braille region should parse undefined characters
braille.Region.parseUndefinedChars = True