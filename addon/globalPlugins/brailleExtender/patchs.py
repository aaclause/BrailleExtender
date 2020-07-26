# coding: utf-8
# patchs.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
# This file modify some functions from core.

from .common import *
from .utils import getCurrentChar, getSpeechSymbols, getTether, getCharFromValue, getCurrentBrailleTables
from .oneHandMode import process as processOneHandMode
from . import undefinedChars
from .objectPresentation import getPropertiesBraille, selectedElementEnabled
from .documentFormatting import getFormatFieldBraille, alignmentsEnabled, attributesEnabled
from . import huc
from . import dictionaries
from . import configBE
from . import brailleRegionHelper
from . import advancedInputMode
import os
import sys
import time
import struct
import winUser

import api
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


instanceGP = None


def SELECTION_SHAPE(): return braille.SELECTION_SHAPE


origFunc = {
	"script_braille_routeTo": globalCommands.GlobalCommands.script_braille_routeTo,
	"update": braille.Region.update,
	"_createTablesString": louis._createTablesString,
	"update_TextInfoRegion": braille.TextInfoRegion.update,
}


def sayCurrentLine():
	global instanceGP
	if not instanceGP.autoScrollRunning:
		if getTether() == braille.handler.TETHER_REVIEW:
			if config.conf["brailleExtender"]["speakScroll"] in [configBE.CHOICE_focusAndReview, configBE.CHOICE_review]:
				scriptHandler.executeScript(
					globalCommands.commands.script_review_currentLine, None)
			return
		elif config.conf["brailleExtender"]["speakScroll"] in [configBE.CHOICE_focusAndReview, configBE.CHOICE_focus]:
			obj = api.getFocusObject()
			treeInterceptor = obj.treeInterceptor
			if isinstance(treeInterceptor, treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough:
				obj = treeInterceptor
			try:
				info = obj.makeTextInfo(textInfos.POSITION_CARET)
			except (NotImplementedError, RuntimeError):
				info = obj.makeTextInfo(textInfos.POSITION_FIRST)
			info.expand(textInfos.UNIT_LINE)
			speech.speakTextInfo(info, unit=textInfos.UNIT_LINE,
								 reason=controlTypes.REASON_CARET)

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
	try:
		braille.handler.routeTo(gesture.routingIndex)
	except LookupError:
		pass
	if scriptHandler.getLastScriptRepeatCount() == 0 and config.conf["brailleExtender"]["speakRoutingTo"]:
		region = braille.handler.buffer
		if region.cursorPos is None:
			return
		try:
			start = region.brailleToRawPos[braille.handler.buffer.windowStartPos +
										   gesture.routingIndex]
			_, endBraillePos = brailleRegionHelper.getBraillePosFromRawPos(
				region, start)
			end = region.brailleToRawPos[endBraillePos+1]
			ch = region.rawText[start:end]
			if ch:
				speech.speakMessage(getSpeechSymbols(ch))
		except IndexError:
			pass

# braille.Region.update()


def update_region(self):
	"""Update this region.
	Subclasses should extend this to update L{rawText}, L{cursorPos}, L{selectionStart} and L{selectionEnd} if necessary.
	The base class method handles translation of L{rawText} into braille, placing the result in L{brailleCells}.
	Typeform information from L{rawTextTypeforms} is used, if any.
	L{rawToBraillePos} and L{brailleToRawPos} are updated according to the translation.
	L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are similarly updated based on L{cursorPos}, L{selectionStart} and L{selectionEnd}, respectively.
	@postcondition: L{brailleCells}, L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are updated and ready for rendering.
	"""
	mode = louis.dotsIO
	if config.conf["braille"]["expandAtCursor"] and self.cursorPos is not None:
		mode |= louis.compbrlAtCursor
	self.brailleCells, self.brailleToRawPos, self.rawToBraillePos, self.brailleCursorPos = louisHelper.translate(
		getCurrentBrailleTables(brf=False if instanceGP else False),
		self.rawText,
		typeform=self.rawTextTypeforms,
		mode=mode,
		cursorPos=self.cursorPos
	)
	if self.parseUndefinedChars and config.conf["brailleExtender"]["undefinedCharsRepr"]["method"] != undefinedChars.CHOICE_tableBehaviour:
		undefinedChars.undefinedCharProcess(self)
	if selectedElementEnabled():
		d = {
			configBE.CHOICE_dot7: 64,
			configBE.CHOICE_dot8: 128,
			configBE.CHOICE_dots78: 192
		}
		if config.conf["brailleExtender"]["objectPresentation"]["selectedElement"] in d:
			addDots = d[config.conf["brailleExtender"]
						["objectPresentation"]["selectedElement"]]
			if hasattr(self, "obj") and self.obj and hasattr(self.obj, "states") and self.obj.states and self.obj.name and controlTypes.STATE_SELECTED in self.obj.states:
				name = self.obj.name
				if name in self.rawText:
					start = self.rawText.index(name)
					end = start + len(name)-1
					startBraillePos, _ = brailleRegionHelper.getBraillePosFromRawPos(
						self, start)
					_, endBraillePos = brailleRegionHelper.getBraillePosFromRawPos(
						self, end)
					self.brailleCells = [cell | addDots if startBraillePos <= pos <=
										 endBraillePos else cell for pos, cell in enumerate(self.brailleCells)]
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
		except IndexError:
			pass
	else:
		if instanceGP and instanceGP.hideDots78:
			self.brailleCells = [(cell & 63) for cell in self.brailleCells]


def update_TextInfoRegion(self):
	TEXT_SEPARATOR = ' '
	formatConfig = config.conf["documentFormatting"]
	unit = self._getReadingUnit()
	self.rawText = ""
	self.rawTextTypeforms = []
	self.brlex_typeforms = {}
	self._len_brlex_typeforms = 0
	self.cursorPos = None
	# The output includes text representing fields which isn't part of the real content in the control.
	# Therefore, maintain a map of positions in the output to positions in the content.
	self._rawToContentPos = []
	self._currentContentPos = 0
	self.selectionStart = self.selectionEnd = None
	self._isFormatFieldAtStart = True
	self._skipFieldsNotAtStartOfNode = False
	self._endsWithField = False

	# Selection has priority over cursor.
	# HACK: Some TextInfos only support UNIT_LINE properly if they are based on POSITION_CARET,
	# and copying the TextInfo breaks this ability.
	# So use the original TextInfo for line and a copy for cursor/selection.
	self._readingInfo = readingInfo = self._getSelection()
	sel = readingInfo.copy()
	if not sel.isCollapsed:
		# There is a selection.
		if self.obj.isTextSelectionAnchoredAtStart:
			# The end of the range is exclusive, so make it inclusive first.
			readingInfo.move(textInfos.UNIT_CHARACTER, -1, "end")
		# Collapse the selection to the unanchored end.
		readingInfo.collapse(end=self.obj.isTextSelectionAnchoredAtStart)
		# Get the reading unit at the selection.
		readingInfo.expand(unit)
		# Restrict the selection to the reading unit.
		if sel.compareEndPoints(readingInfo, "startToStart") < 0:
			sel.setEndPoint(readingInfo, "startToStart")
		if sel.compareEndPoints(readingInfo, "endToEnd") > 0:
			sel.setEndPoint(readingInfo, "endToEnd")
	else:
		# There is a cursor.
		# Get the reading unit at the cursor.
		readingInfo.expand(unit)

	# Not all text APIs support offsets, so we can't always get the offset of the selection relative to the start of the reading unit.
	# Therefore, grab the reading unit in three parts.
	# First, the chunk from the start of the reading unit to the start of the selection.
	chunk = readingInfo.copy()
	chunk.collapse()
	chunk.setEndPoint(sel, "endToStart")
	self._addTextWithFields(chunk, formatConfig)
	# If the user is entering braille, place any untranslated braille before the selection.
	# Import late to avoid circular import.
	import brailleInput
	text = brailleInput.handler.untranslatedBraille
	if text:
		rawInputIndStart = len(self.rawText)
		# _addFieldText adds text to self.rawText and updates other state accordingly.
		self._addFieldText(braille.INPUT_START_IND + text +
						   braille.INPUT_END_IND, None, separate=False)
		rawInputIndEnd = len(self.rawText)
	else:
		rawInputIndStart = None
	# Now, the selection itself.
	self._addTextWithFields(sel, formatConfig, isSelection=True)
	# Finally, get the chunk from the end of the selection to the end of the reading unit.
	chunk.setEndPoint(readingInfo, "endToEnd")
	chunk.setEndPoint(sel, "startToEnd")
	self._addTextWithFields(chunk, formatConfig)

	# Strip line ending characters.
	self.rawText = self.rawText.rstrip("\r\n\0\v\f")
	rawTextLen = len(self.rawText)
	if rawTextLen < len(self._rawToContentPos):
		# The stripped text is shorter than the original.
		self._currentContentPos = self._rawToContentPos[rawTextLen]
		del self.rawTextTypeforms[rawTextLen:]
		# Trimming _rawToContentPos doesn't matter,
		# because we'll only ever ask for indexes valid in rawText.
		#del self._rawToContentPos[rawTextLen:]
	if rawTextLen == 0 or not self._endsWithField:
		# There is no text left after stripping line ending characters,
		# or the last item added can be navigated with a cursor.
		# Add a space in case the cursor is at the end of the reading unit.
		self.rawText += ' '
		rawTextLen += 1
		self.rawTextTypeforms.append(louis.plain_text)
		self._rawToContentPos.append(self._currentContentPos)
	if self.cursorPos is not None and self.cursorPos >= rawTextLen:
		self.cursorPos = rawTextLen - 1
	# The selection end doesn't have to be checked, Region.update() makes sure brailleSelectionEnd is valid.

	# If this is not the start of the object, hide all previous regions.
	start = readingInfo.obj.makeTextInfo(textInfos.POSITION_FIRST)
	self.hidePreviousRegions = (
		start.compareEndPoints(readingInfo, "startToStart") < 0)
	# Don't touch focusToHardLeft if it is already true
	# For example, it can be set to True in getFocusContextRegions when this region represents the first new focus ancestor
	# Alternatively, BrailleHandler._doNewObject can set this to True when this region represents the focus object and the focus ancestry didn't change
	if not self.focusToHardLeft:
		# If this is a multiline control, position it at the absolute left of the display when focused.
		self.focusToHardLeft = self._isMultiline()
	super(braille.TextInfoRegion, self).update()

	if rawInputIndStart is not None:
		assert rawInputIndEnd is not None, "rawInputIndStart set but rawInputIndEnd isn't"
		# These are the start and end of the untranslated input area,
		# including the start and end indicators.
		self._brailleInputIndStart = self.rawToBraillePos[rawInputIndStart]
		self._brailleInputIndEnd = self.rawToBraillePos[rawInputIndEnd]
		# These are the start and end of the actual untranslated input, excluding indicators.
		self._brailleInputStart = self._brailleInputIndStart + \
			len(braille.INPUT_START_IND)
		self._brailleInputEnd = self._brailleInputIndEnd - \
			len(braille.INPUT_END_IND)
		self.brailleCursorPos = self._brailleInputStart + \
			brailleInput.handler.untranslatedCursorPos
	else:
		self._brailleInputIndStart = None

#: braille.TextInfoRegion._addTextWithFields


def _addTextWithFields(self, info, formatConfig, isSelection=False):
	TEXT_SEPARATOR = ' '
	shouldMoveCursorToFirstContent = not isSelection and self.cursorPos is not None
	ctrlFields = []
	typeform = louis.plain_text
	formatFieldAttributesCache = getattr(
		info.obj, "_brailleFormatFieldAttributesCache", {})
	# When true, we are inside a clickable field, and should therefore not report any more new clickable fields
	inClickable = False
	for command in info.getTextWithFields(formatConfig=formatConfig):
		if isinstance(command, str):
			# Text should break a run of clickables
			inClickable = False
			self._isFormatFieldAtStart = False
			if not command:
				continue
			if self._endsWithField:
				# The last item added was a field,
				# so add a space before the content.
				#self.rawText += TEXT_SEPARATOR
				# self.rawTextTypeforms.append(louis.plain_text)
				self._rawToContentPos.append(self._currentContentPos)
			if isSelection and self.selectionStart is None:
				# This is where the content begins.
				self.selectionStart = len(self.rawText)
			elif shouldMoveCursorToFirstContent:
				# This is the first piece of content after the cursor.
				# Position the cursor here, as it may currently be positioned on control field text.
				self.cursorPos = len(self.rawText)
				shouldMoveCursorToFirstContent = False
			self.rawText += command
			commandLen = len(command)
			self.rawTextTypeforms.extend((typeform,) * commandLen)
			endPos = self._currentContentPos + commandLen
			self._rawToContentPos.extend(
				range(self._currentContentPos, endPos))
			self._currentContentPos = endPos
			if isSelection:
				# The last time this is set will be the end of the content.
				self.selectionEnd = len(self.rawText)
			self._endsWithField = False
		elif isinstance(command, textInfos.FieldCommand):
			cmd = command.command
			field = command.field
			if cmd == "formatChange":
				typeform, brlex_typeform = self._getTypeformFromFormatField(
					field, formatConfig)
				text = getFormatFieldBraille(
					field, formatFieldAttributesCache, self._isFormatFieldAtStart, formatConfig)
				if text:
					self._addFieldText(text, self._currentContentPos, False)
				self._len_brlex_typeforms += self._rawToContentPos.count(
					self._currentContentPos)
				self.brlex_typeforms[self._len_brlex_typeforms +
									 self._currentContentPos] = brlex_typeform
				if not text:
					continue
			elif cmd == "controlStart":
				if self._skipFieldsNotAtStartOfNode and not field.get("_startOfNode"):
					text = None
				else:
					textList = []
					if not inClickable and formatConfig['reportClickable']:
						states = field.get('states')
						if states and controlTypes.STATE_CLICKABLE in states:
							# We have entered an outer most clickable or entered a new clickable after exiting a previous one
							# Report it if there is nothing else interesting about the field
							field._presCat = presCat = field.getPresentationCategory(
								ctrlFields, formatConfig)
							if not presCat or presCat is field.PRESCAT_LAYOUT:
								textList.append(
									braille.positiveStateLabels[controlTypes.STATE_CLICKABLE])
							inClickable = True
					text = info.getControlFieldBraille(
						field, ctrlFields, True, formatConfig)
					if text:
						textList.append(text)
					text = " ".join(textList)
				# Place this field on a stack so we can access it for controlEnd.
				ctrlFields.append(field)
				if not text:
					continue
				if getattr(field, "_presCat") == field.PRESCAT_MARKER:
					# In this case, the field text is what the user cares about,
					# not the actual content.
					fieldStart = len(self.rawText)
					if fieldStart > 0:
						# There'll be a space before the field text.
						fieldStart += 1
					if isSelection and self.selectionStart is None:
						self.selectionStart = fieldStart
					elif shouldMoveCursorToFirstContent:
						self.cursorPos = fieldStart
						shouldMoveCursorToFirstContent = False
				# Map this field text to the start of the field's content.
				self._addFieldText(text, self._currentContentPos)
			elif cmd == "controlEnd":
				# Exiting a controlField should break a run of clickables
				inClickable = False
				field = ctrlFields.pop()
				text = info.getControlFieldBraille(
					field, ctrlFields, False, formatConfig)
				if not text:
					continue
				# Map this field text to the end of the field's content.
				self._addFieldText(text, self._currentContentPos - 1)
			self._endsWithField = True
	if isSelection and self.selectionStart is None:
		# There is no selection. This is a cursor.
		self.cursorPos = len(self.rawText)
	if not self._skipFieldsNotAtStartOfNode:
		# We only render fields that aren't at the start of their nodes for the first part of the reading unit.
		# Otherwise, we'll render fields that have already been rendered.
		self._skipFieldsNotAtStartOfNode = True
	info.obj._brailleFormatFieldAttributesCache = formatFieldAttributesCache

#: braille.TextInfoRegion.nextLine()


def nextLine(self):
	try:
		dest = self._readingInfo.copy()
		moved = dest.move(self._getReadingUnit(), 1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try:
					dest.obj.turnPage()
				except RuntimeError:
					pass
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_FIRST)
			else:
				return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(
			queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException:
		pass

#: braille.TextInfoRegion.previousLine()


def previousLine(self, start=False):
	try:
		dest = self._readingInfo.copy()
		dest.collapse()
		if start:
			unit = self._getReadingUnit()
		else:
			unit = textInfos.UNIT_CHARACTER
		moved = dest.move(unit, -1)
		if not moved:
			if self.allowPageTurns and isinstance(dest.obj, textInfos.DocumentWithPageTurns):
				try:
					dest.obj.turnPage(previous=True)
				except RuntimeError:
					pass
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_LAST)
					dest.expand(unit)
			else:
				return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(
			queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException:
		pass

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
		if instanceGP.brailleKeyboardLocked and ((hasattr(script, "__func__") and script.__func__.__name__ != "script_toggleLockBrailleKeyboard") or not hasattr(script, "__func__")):
			return
		if not config.conf["brailleExtender"]['stopSpeechUnknown'] and gesture.script == None:
			stopSpeech = False
		elif hasattr(script, "__func__") and (script.__func__.__name__ in [
			"script_braille_dots", "script_braille_enter",
			"script_volumePlus", "script_volumeMinus", "script_toggleVolume",
			"script_hourDate",
			"script_ctrl", "script_alt", "script_nvda", "script_win",
			"script_ctrlAlt", "script_ctrlAltWin", "script_ctrlAltWinShift", "script_ctrlAltShift", "script_ctrlWin", "script_ctrlWinShift", "script_ctrlShift", "script_altWin", "script_altWinShift", "script_altShift", "script_winShift"]
				or (
				not config.conf["brailleExtender"]['stopSpeechScroll'] and
				script.__func__.__name__ in ["script_braille_scrollBack", "script_braille_scrollForward"])):
			stopSpeech = False
		else:
			stopSpeech = True
	else:
		stopSpeech = True

	focus = api.getFocusObject()
	if focus.sleepMode is focus.SLEEP_FULL or (focus.sleepMode and not getattr(script, 'allowInSleepMode', False)):
		raise NoInputGestureAction

	wasInSayAll = False
	if gesture.isModifier:
		if not self.lastModifierWasInSayAll:
			wasInSayAll = self.lastModifierWasInSayAll = sayAllHandler.isRunning()
	elif self.lastModifierWasInSayAll:
		wasInSayAll = True
		self.lastModifierWasInSayAll = False
	else:
		wasInSayAll = sayAllHandler.isRunning()
	if wasInSayAll:
		gesture.wasInSayAll = True

	speechEffect = gesture.speechEffectWhenExecuted
	if not stopSpeech:
		pass
	elif speechEffect == gesture.SPEECHEFFECT_CANCEL:
		queueHandler.queueFunction(
			queueHandler.eventQueue, speech.cancelSpeech)
	elif speechEffect in (gesture.SPEECHEFFECT_PAUSE, gesture.SPEECHEFFECT_RESUME):
		queueHandler.queueFunction(
			queueHandler.eventQueue, speech.pauseSpeech, speechEffect == gesture.SPEECHEFFECT_PAUSE)

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
		queueHandler.queueFunction(
			queueHandler.eventQueue, speech.speakMessage, gesture.displayName)

	gesture.reportExtra()

	# #2953: if an intercepted command Script (script that sends a gesture) is queued
	# then queue all following gestures (that don't have a script) with a fake script so that they remain in order.
	if not script and scriptHandler._numIncompleteInterceptedCommandScripts:
		def script(gesture): return gesture.send()

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
	chars = ''.join(c if ord(c) <= 0xffff else ''.join(
			chr(x) for x in struct.unpack('>2H', c.encode("utf-16be"))) for c in chars)
	for ch in chars:
		for direction in (0, winUser.KEYEVENTF_KEYUP):
			input = winUser.Input()
			input.type = winUser.INPUT_KEYBOARD
			input.ii.ki = winUser.KeyBdInput()
			input.ii.ki.wScan = ord(ch)
			input.ii.ki.dwFlags = winUser.KEYEVENTF_UNICODE | direction
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
		inputCore.manager.emulateGesture(
			keyboardHandler.KeyboardInputGesture.fromName(gesture))
		instanceGP.lastShortcutPerformed = gesture
	except BaseException:
		log.debugWarning(
			"Unable to emulate %r, falling back to sending unicode characters" % gesture, exc_info=True)
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
		if not continue_:
			return
	else:
		self.bufferBraille.insert(pos, dots)
		self.untranslatedCursorPos += 1
	ok = False
	if instanceGP:
		focusObj = api.getFocusObject()
		ok = not self.currentModifiers and (
			not focusObj.treeInterceptor or focusObj.treeInterceptor.passThrough)
	if instanceGP and instanceGP.advancedInput and ok:
		pos = self.untranslatedStart + self.untranslatedCursorPos
		advancedInputStr = ''.join([chr(cell | 0x2800)
									for cell in self.bufferBraille[:pos]])
		if advancedInputStr:
			res = ''
			abreviations = advancedInputMode.getReplacements(
				[advancedInputStr])
			startUnicodeValue = "⠃⠙⠓⠕⠭⡃⡙⡓⡕⡭"
			if not abreviations and advancedInputStr[0] in startUnicodeValue:
				advancedInputStr = config.conf["brailleExtender"][
					"advancedInputMode"]["escapeSignUnicodeValue"] + advancedInputStr
			lenEscapeSign = len(
				config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"])
			if advancedInputStr == config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"] or (advancedInputStr.startswith(config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"]) and len(advancedInputStr) > lenEscapeSign and advancedInputStr[lenEscapeSign] in startUnicodeValue):
				equiv = {'⠃': 'b', '⠙': 'd', '⠓': 'h', '⠕': 'o', '⠭': 'x',
						 '⡃': 'B', '⡙': 'D', '⡓': 'H', '⡕': 'O', '⡭': 'X'}
				if advancedInputStr[-1] == '⠀':
					text = equiv[advancedInputStr[1]] + louis.backTranslate(
						getCurrentBrailleTables(True, brf=instanceGP.BRFMode), advancedInputStr[2:-1])[0]
					try:
						res = getCharFromValue(text)
						sendChar(res)
					except BaseException as err:
						speech.speakMessage(repr(err))
						return badInput(self)
				else:
					self._reportUntranslated(pos)
			elif abreviations:
				if len(abreviations) == 1:
					res = abreviations[0].replaceBy
					sendChar(res)
				else:
					return self._reportUntranslated(pos)
			else:
				res = huc.isValidHUCInput(advancedInputStr)
				if res == huc.HUC_INPUT_INCOMPLETE:
					return self._reportUntranslated(pos)
				elif res == huc.HUC_INPUT_INVALID:
					return badInput(self)
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
	nvwave.playWaveFile(os.path.join(
		configBE.baseDir, "res/sounds/keyPress.wav"))
	core.callLater(0, brailleInput.handler.sendChars, char)
	if len(char) == 1:
		core.callLater(100, speech.speakSpelling, char)
	else:
		core.callLater(100, speech.speakMessage, char)


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
	data = u"".join([chr(cell | brailleInput.LOUIS_DOTS_IO_START)
					 for cell in self.bufferBraille[:pos]])
	mode = louis.dotsIO | louis.noUndefinedDots
	if (not self.currentFocusIsTextObj or self.currentModifiers) and self._table.contracted:
		mode |= louis.partialTrans
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
			if len(newText) > 1:
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
braille.getFormatFieldBraille = getFormatFieldBraille
braille.Region.update = update_region
braille.TextInfoRegion._addTextWithFields = _addTextWithFields
braille.TextInfoRegion.update = update_TextInfoRegion
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

braille.Region.brlex_typeforms = {}
braille.Region._len_brlex_typeforms = 0
