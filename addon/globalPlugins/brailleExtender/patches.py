# coding: utf-8
# patches.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2022 André-Abush CLAUSE, released under GPL.
# This file modify some functions from core.
# coding: utf-8

import os
import struct
import sys
import time

import addonHandler
import api
import braille
import brailleInput
import config
import controlTypes
import core
import globalCommands
import inputCore
import keyboardHandler
import louis
import louisHelper
import nvwave
import queueHandler
try:
	import sayAllHandler
except ModuleNotFoundError:
	from speech.sayAll import SayAllHandler as sayAllHandler
import scriptHandler
import speech
import textInfos
import tones
import treeInterceptorHandler
import watchdog
import winUser
from logHandler import log

from . import addoncfg
from . import advancedinput
from . import autoscroll
from . import huc
from . import regionhelper
from . import speechhistorymode
from . import undefinedchars
from .common import baseDir, RC_EMULATE_ARROWS_BEEP, RC_EMULATE_ARROWS_SILENT
from .onehand import process as processOneHandMode
from .utils import getCurrentChar, getSpeechSymbols, getTether, getCharFromValue, getCurrentBrailleTables, get_output_reason, get_control_type

addonHandler.initTranslation()

instanceGP = None

SELECTION_SHAPE = lambda: braille.SELECTION_SHAPE
origFunc = {
	"script_braille_routeTo": globalCommands.GlobalCommands.script_braille_routeTo,
	"update": braille.Region.update,
	"_createTablesString": louis._createTablesString
}

def sayCurrentLine():
	global instanceGP
	if not braille.handler._auto_scroll:
		if getTether() == braille.handler.TETHER_REVIEW:
			if config.conf["brailleExtender"]["speakScroll"] in [addoncfg.CHOICE_focusAndReview, addoncfg.CHOICE_review]:
				scriptHandler.executeScript(globalCommands.commands.script_review_currentLine, None)
			return
		if config.conf["brailleExtender"]["speakScroll"] in [addoncfg.CHOICE_focusAndReview, addoncfg.CHOICE_focus]:
			obj = api.getFocusObject()
			treeInterceptor = obj.treeInterceptor
			if isinstance(treeInterceptor, treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough: obj = treeInterceptor
			try: info = obj.makeTextInfo(textInfos.POSITION_CARET)
			except (NotImplementedError, RuntimeError):
				info = obj.makeTextInfo(textInfos.POSITION_FIRST)
			info.expand(textInfos.UNIT_LINE)
			speech.speakTextInfo(info, unit=textInfos.UNIT_LINE, reason=REASON_CARET)

# globalCommands.GlobalCommands.script_braille_routeTo()
def say_character_under_braille_routing_cursor(gesture):
	if not braille.handler._auto_scroll and scriptHandler.getLastScriptRepeatCount() == 0 and config.conf["brailleExtender"]["speakRoutingTo"]:
		region = braille.handler.buffer
		if region.cursorPos is None: return
		try:
			start = region.brailleToRawPos[braille.handler.buffer.windowStartPos + gesture.routingIndex]
			_, endBraillePos = regionhelper.getBraillePosFromRawPos(region, start)
			end = region.brailleToRawPos[endBraillePos+1]
			ch = region.rawText[start:end]
			if ch:
				speech.speakMessage(getSpeechSymbols(ch))
		except IndexError: pass


def script_braille_routeTo(self, gesture):
	if braille.handler.buffer == braille.handler.mainBuffer and braille.handler.getTether() == "speech":
		return speechhistorymode.showSpeechFromRoutingIndex(gesture.routingIndex)
	if braille.handler._auto_scroll and braille.handler.buffer is braille.handler.mainBuffer:
		braille.handler.toggle_auto_scroll()
	obj = api.getNavigatorObject()
	if (config.conf["brailleExtender"]["routingCursorsEditFields"] in [RC_EMULATE_ARROWS_BEEP, RC_EMULATE_ARROWS_SILENT] and
		braille.handler.buffer is braille.handler.mainBuffer and
		braille.handler.mainBuffer.cursorPos is not None and
		obj.hasFocus and
		obj.role in [get_control_type("ROLE_TERMINAL"), get_control_type("ROLE_EDITABLETEXT")]
	):
		play_beeps = config.conf["brailleExtender"]["routingCursorsEditFields"] == RC_EMULATE_ARROWS_BEEP
		nb = 0
		key = "rightarrow"
		region = braille.handler.mainBuffer
		cur_pos = region.brailleToRawPos[region.cursorPos]
		size = region.brailleToRawPos[-1]
		try:
			new_pos = region.brailleToRawPos[braille.handler.buffer.windowStartPos + gesture.routingIndex]
		except IndexError:
			new_pos = size
		log.debug(f"Moving from position {cur_pos} to position {new_pos}")
		if play_beeps: tones.beep(100, 100)
		if new_pos == 0:
			keyboardHandler.KeyboardInputGesture.fromName("home").send()
		elif new_pos >= size:
			keyboardHandler.KeyboardInputGesture.fromName("end").send()
		else:
			if cur_pos > new_pos:
				key = "leftarrow"
				nb = cur_pos - new_pos
			else:
				nb = new_pos - cur_pos
			i = 0
			gestureKB = keyboardHandler.KeyboardInputGesture.fromName(key)
			while i < nb:
				gestureKB.send()
				i += 1
		if play_beeps: tones.beep(150, 100)
		say_character_under_braille_routing_cursor(gesture)
		return
	try: braille.handler.routeTo(gesture.routingIndex)
	except LookupError: pass
	say_character_under_braille_routing_cursor(gesture)


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
		getCurrentBrailleTables(brf=instanceGP.BRFMode),
		self.rawText,
		typeform=self.rawTextTypeforms,
		mode=mode,
		cursorPos=self.cursorPos
	)
	if (self.parseUndefinedChars
		and config.conf["brailleExtender"]["undefinedCharsRepr"]["method"] != undefinedchars.CHOICE_tableBehaviour
		and len(self.rawText) <= config.conf["brailleExtender"]["undefinedCharsRepr"]["characterLimit"]
	):
		undefinedchars.undefinedCharProcess(self)
	if config.conf["brailleExtender"]["features"]["attributes"] and config.conf["brailleExtender"]["attributes"]["selectedElement"] != addoncfg.CHOICE_none:
		d = {
			addoncfg.CHOICE_dot7: 64,
			addoncfg.CHOICE_dot8: 128,
			addoncfg.CHOICE_dots78: 192
		}
		if config.conf["brailleExtender"]["attributes"]["selectedElement"] in d:
			addDots = d[config.conf["brailleExtender"]["attributes"]["selectedElement"]]
			if hasattr(self, "obj") and self.obj and hasattr(self.obj, "states") and self.obj.states and self.obj.name and get_control_type("STATE_SELECTED") in self.obj.states:
				name = self.obj.name
				if name in self.rawText:
					start = self.rawText.index(name)
					end = start + len(name)-1
					startBraillePos, _ = regionhelper.getBraillePosFromRawPos(self, start)
					_, endBraillePos = regionhelper.getBraillePosFromRawPos(self, end)
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


# braille.TextInfoRegion.nextLine()
def nextLine(self):
	dest = self._readingInfo.copy()
	continue_ = True
	while continue_:
		moved = dest.move(self._getReadingUnit(), 1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try: dest.obj.turnPage()
				except RuntimeError as err:
					log.error(err)
					continue_ = False
				else: dest = dest.obj.makeTextInfo(textInfos.POSITION_FIRST)
			else:
				if braille.handler._auto_scroll:
					braille.handler.toggle_auto_scroll()
				return
		if continue_ and config.conf["brailleExtender"]["skipBlankLinesScroll"] or (
			braille.handler._auto_scroll and (
				config.conf["brailleExtender"]["autoScroll"]["ignoreBlankLine"]
				or config.conf["brailleExtender"]["autoScroll"]["adjustToContent"])
		):
			dest_ = dest.copy()
			dest_.expand(textInfos.UNIT_LINE)
			continue_ = not dest_.text.strip()
		else:
			continue_ = False
	dest.collapse()
	self._setCursor(dest)
	queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
	queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)

# braille.TextInfoRegion.previousLine()
def previousLine(self, start=False):
	dest = self._readingInfo.copy()
	dest.collapse()
	if start: unit = self._getReadingUnit()
	else: unit = textInfos.UNIT_CHARACTER
	continue_ = True
	while continue_:
		moved = dest.move(unit, -1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try: dest.obj.turnPage(previous=True)
				except RuntimeError as err:
					log.error(err)
					continue_ = False
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_LAST)
					dest.expand(unit)
			else: return
		if continue_ and config.conf["brailleExtender"]["skipBlankLinesScroll"] or (braille.handler._auto_scroll and config.conf["brailleExtender"]["autoScroll"]["ignoreBlankLine"]):
			dest_ = dest.copy()
			dest_.expand(textInfos.UNIT_LINE)
			continue_ = not dest_.text.strip()
		else:
			continue_ = False
	dest.collapse()
	self._setCursor(dest)
	queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
	queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)


# inputCore.InputManager.executeGesture
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
# brailleInput.BrailleInputHandler.sendChars()
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

# brailleInput.BrailleInputHandler.emulateKey()
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

# brailleInput.BrailleInputHandler.input()
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
			abreviations = advancedinput.getReplacements([advancedInputStr])
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
					res = abreviations[0].replacement
					sendChar(res)
				else: return self._reportUntranslated(pos)
			else:
				res = huc.isValidHUCInput(advancedInputStr)
				if res == huc.HUC_INPUT_INCOMPLETE: return self._reportUntranslated(pos)
				if res == huc.HUC_INPUT_INVALID: return badInput(self)
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
		elif self.bufferText and not self.useContractedForCurrentFocus and self._table.contracted:
			# Translators: Reported when translation didn't succeed due to unsupported input.
			speech.speakMessage(_("Unsupported input"))
			self.flushBuffer()
		else:
			# This cell didn't produce any text; e.g. number sign.
			self._reportUntranslated(pos)
	else:
		self._reportUntranslated(pos)

# brailleInput.BrailleInputHandler._translate()
# reason for patching: possibility to lock modifiers, display modifiers in braille during input, HUC Braille input

def sendChar(char):
	nvwave.playWaveFile(os.path.join(baseDir, "res/sounds/keyPress.wav"))
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
		self.bufferText = ""
	oldTextLen = len(self.bufferText)
	pos = self.untranslatedStart + self.untranslatedCursorPos
	data = "".join([chr(cell | brailleInput.LOUIS_DOTS_IO_START) for cell in self.bufferBraille[:pos]])
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
				newText = ""
			else:
				self.emulateKey(newText)
		else:
			if config.conf["brailleExtender"]["smartCapsLock"] and winUser.getKeyState(winUser.VK_CAPITAL)&1:
				tmp = []
				for ch in newText:
					if ch.islower():
						tmp.append(ch.upper())
					else:
						tmp.append(ch.lower())
				newText = ''.join(tmp)
			self.sendChars(newText)

	if endWord or (newText and (not self.currentFocusIsTextObj or self.currentModifiers)):
		# We only need to buffer one word.
		# Clear the previous word (anything before the cursor) from the buffer.
		del self.bufferBraille[:pos]
		self.bufferText = ""
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

# louis._createTablesString()
def _createTablesString(tablesList):
	"""Creates a tables string for liblouis calls"""
	return b",".join([x.encode(sys.getfilesystemencoding()) if isinstance(x, str) else bytes(x) for x in tablesList])


def _displayWithCursor(self):
	if not self._cells:
		return
	cells = list(self._cells)
	if self._cursorPos is not None and self._cursorBlinkUp and not self._auto_scroll:
		if self.getTether() == self.TETHER_FOCUS:
			cells[self._cursorPos] |= config.conf["braille"]["cursorShapeFocus"]
		else:
			cells[self._cursorPos] |= config.conf["braille"]["cursorShapeReview"]
	self._writeCells(cells)

origGetTether = braille.BrailleHandler.getTether

def getTetherWithRoleTerminal(self):
	if config.conf["brailleExtender"]["speechHistoryMode"]["enabled"]:
		return speechhistorymode.TETHER_SPEECH
	role = None
	obj = api.getNavigatorObject()
	if obj:
		role = api.getNavigatorObject().role
	if (
		config.conf["brailleExtender"]["reviewModeTerminal"] 
		and role == controlTypes.ROLE_TERMINAL
	):
		return braille.handler.TETHER_REVIEW
	return origGetTether(self)


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

# This variable tells if braille region should parse undefined characters
braille.Region.parseUndefinedChars = True

braille.BrailleHandler.AutoScroll = autoscroll.AutoScroll
braille.BrailleHandler._auto_scroll = None
braille.BrailleHandler.get_auto_scroll_delay = autoscroll.get_auto_scroll_delay
braille.BrailleHandler.get_dynamic_auto_scroll_delay = autoscroll.get_dynamic_auto_scroll_delay
braille.BrailleHandler.decrease_auto_scroll_delay = autoscroll.decrease_auto_scroll_delay
braille.BrailleHandler.increase_auto_scroll_delay = autoscroll.increase_auto_scroll_delay
braille.BrailleHandler.report_auto_scroll_delay = autoscroll.report_auto_scroll_delay
braille.BrailleHandler.toggle_auto_scroll = autoscroll.toggle_auto_scroll
braille.BrailleHandler._displayWithCursor = _displayWithCursor

REASON_CARET = get_output_reason("CARET")
braille.BrailleHandler.getTether = getTetherWithRoleTerminal
