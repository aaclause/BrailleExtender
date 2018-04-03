# coding: utf-8
# patchs.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os
import api
import braille
import brailleTables
import controlTypes
import core
import config
import configBE
import globalCommands
import inputCore
import sayAllHandler
import queueHandler
import scriptHandler
import treeInterceptorHandler
import watchdog
import louis
import scriptHandler
import speech
import textInfos
from logHandler import log
import addonHandler

addonHandler.initTranslation()
from utils import getCurrentChar, getLine
instanceGP = None
preTable = []
postTable = []
SELECTION_SHAPE = braille.SELECTION_SHAPE
def script_braille_routeTo(self, gesture):
	braille.handler.routeTo(gesture.routingIndex)
	if configBE.conf['general']['speakRoutingTo']:
		ch = getCurrentChar()
		if ch != "": speech.speakSpelling(ch)

# customize basic functions

# braille.Region.update
def update(self):
	"""Update this region.
	Subclasses should extend this to update L{rawText}, L{cursorPos}, L{selectionStart} and L{selectionEnd} if necessary.
	The base class method handles translation of L{rawText} into braille, placing the result in L{brailleCells}.
	Typeform information from L{rawTextTypeforms} is used, if any.
	L{rawToBraillePos} and L{brailleToRawPos} are updated according to the translation.
	L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are similarly updated based on L{cursorPos}, L{selectionStart} and L{selectionEnd}, respectively.
	@postcondition: L{brailleCells}, L{brailleCursorPos}, L{brailleSelectionStart} and L{brailleSelectionEnd} are updated and ready for rendering.
	"""
	global postTable, preTable
	try:
		mode = louis.dotsIO
		if config.conf["braille"]["expandAtCursor"] and self.cursorPos is not None:
			mode |= louis.compbrlAtCursor
		try:
			text = unicode(self.rawText).replace('\0', '')
			braille, self.brailleToRawPos, self.rawToBraillePos, brailleCursorPos = louis.translate(
				preTable + [
					os.path.join(brailleTables.TABLES_DIR, config.conf["braille"]["translationTable"]),
					os.path.join(
						brailleTables.TABLES_DIR,
						"braille-patterns.cti")
				] + postTable,
				text,
				# liblouis mutates typeform if it is a list.
				typeform=tuple(
					self.rawTextTypeforms) if isinstance(
					self.rawTextTypeforms,
					list) else self.rawTextTypeforms,
				mode=mode, cursorPos=self.cursorPos or 0)
		except BaseException:
			if len(postTable) == 0:
				log.error("Error with update braille function patch, disabling: %s")
				configBE.conf["patch"]["updateBraille"] = False
				configBE.conf["general"]["tabSpace"] = False
				configBE.conf["general"]["postTable"] = "None"
				core.restart()
				return
			log.warning('Unable to translate with secondary table: %s and %s.' % (config.conf["braille"]["translationTable"], postTable))
			postTable = []
			configBE.conf["general"]["postTable"] = "None"
			update(self)
			return
		# liblouis gives us back a character string of cells, so convert it to a list of ints.
		# For some reason, the highest bit is set, so only grab the lower 8
		# bits.
		self.brailleCells = [ord(cell) & 255 for cell in braille]
		# #2466: HACK: liblouis incorrectly truncates trailing spaces from its output in some cases.
		# Detect this and add the spaces to the end of the output.
		if self.rawText and self.rawText[-1] == " ":
			# rawToBraillePos isn't truncated, even though brailleCells is.
			# Use this to figure out how long brailleCells should be and thus
			# how many spaces to add.
			correctCellsLen = self.rawToBraillePos[-1] + 1
			currentCellsLen = len(self.brailleCells)
			if correctCellsLen > currentCellsLen:
				self.brailleCells.extend(
					(0,) * (correctCellsLen - currentCellsLen))
		if self.cursorPos is not None:
			# HACK: The cursorPos returned by liblouis is notoriously buggy (#2947 among other issues).
			# rawToBraillePos is usually accurate.
			try:
				brailleCursorPos = self.rawToBraillePos[self.cursorPos]
			except IndexError:
				pass
		else:
			brailleCursorPos = None
		self.brailleCursorPos = brailleCursorPos
		if self.selectionStart is not None and self.selectionEnd is not None:
			try:
				# Mark the selection.
				self.brailleSelectionStart = self.rawToBraillePos[self.selectionStart]
				if self.selectionEnd >= len(self.rawText):
					self.brailleSelectionEnd = len(self.brailleCells)
				else:
					self.brailleSelectionEnd = self.rawToBraillePos[self.selectionEnd]
				for pos in xrange(
						self.brailleSelectionStart,
						self.brailleSelectionEnd):
					self.brailleCells[pos] |= SELECTION_SHAPE
			except IndexError:
				pass
	except BaseException as e:
		log.error("Error with update braille patch, disabling: %s" % e)
		configBE.conf["patch"]["updateBraille"] = False
		configBE.conf["general"]["tabSpace"] = False
		configBE.conf["general"]["postTable"] = "None"
		core.restart()


def sayCurrentLine():
	global instanceGP
	if (configBE.conf['general']['speakScroll'] or configBE.conf['general']['alwaysSpeakScroll']) and not instanceGP.autoScrollRunning:
		if braille.handler.tether == braille.handler.TETHER_REVIEW:
			scriptHandler.executeScript(globalCommands.commands.script_review_currentLine, None)
		elif configBE.conf['general']['alwaysSpeakScroll']:
			obj = api.getFocusObject()
			treeInterceptor = obj.treeInterceptor
			if isinstance(treeInterceptor, treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough:
				obj = treeInterceptor
			try:
				info = obj.makeTextInfo(textInfos.POSITION_CARET)
			except (NotImplementedError, RuntimeError):
				info = obj.makeTextInfo(textInfos.POSITION_FIRST)
			info.expand(textInfos.UNIT_LINE)
			speech.speakTextInfo(info, unit=textInfos.UNIT_LINE, reason=controlTypes.REASON_CARET)

# braille.TextInfoRegion.nextLine()
def nextLine(self):
	try:
		dest = self._readingInfo.copy()
		moved = dest.move(self._getReadingUnit(), 1)
		if not moved:
			if self.allowPageTurns and isinstance(
					dest.obj, textInfos.DocumentWithPageTurns):
				try:
					dest.obj.turnPage()
				except RuntimeError:
					pass
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_FIRST)
			else:  # no page turn support
				return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException as e: pass

# braille.TextInfoRegion.previousLine()
def previousLine(self, start=False):
	try:
		dest = self._readingInfo.copy()
		dest.collapse()
		if start:
			unit = self._getReadingUnit()
		else:
			# If the end of the reading unit is desired, move to the last
			# character.
			unit = textInfos.UNIT_CHARACTER
		moved = dest.move(unit, -1)
		if not moved:
			if self.allowPageTurns and isinstance(
					dest.obj, textInfos.DocumentWithPageTurns):
				try:
					dest.obj.turnPage(previous=True)
				except RuntimeError:
					pass
				else:
					dest = dest.obj.makeTextInfo(textInfos.POSITION_LAST)
					dest.expand(unit)
			else:  # no page turn support
				return
		dest.collapse()
		self._setCursor(dest)
		queueHandler.queueFunction(queueHandler.eventQueue, speech.cancelSpeech)
		queueHandler.queueFunction(queueHandler.eventQueue, sayCurrentLine)
	except BaseException as e: pass

def createTabFile(f, c):
	try:
		f = open(f, "w")
		f.write(c)
		f.close()
		return True
	except BaseException as e:
		log.error('Error while creating tab file (%s)' % e)
		return False


braille.TextInfoRegion.previousLine = previousLine
braille.TextInfoRegion.nextLine = nextLine

postTableValid = True if configBE.conf['general']['postTable'] in configBE.tablesFN else False

if postTableValid:
	postTable.append(
		os.path.join(
			brailleTables.TABLES_DIR,
			configBE.conf['general']['postTable']))
	log.info('Secondary table enabled: %s' %
			 configBE.conf['general']['postTable'])
else:
	if configBE.conf['general']['postTable'] != "None":
		log.error('Invalid secondary table')

tabFile = os.path.join(os.path.dirname(__file__), "", "tab.cti").decode("mbcs")
defTab = 'space \\t ' + \
	('0-' * configBE.conf['general']['tabSize'])[:-1] + '\n'

if configBE.conf['general']['tabSpace'] and not os.path.exists(tabFile):
	log.info('File not found, creating tab file')
	createTabFile(tabFile, defTab)

if configBE.conf['general']['tabSpace'] and os.path.exists(tabFile):
	f = open(tabFile, "r")
	if f.read() != defTab:
		log.debug('Difference, creating tab file...')
		if createTabFile(tabFile, defTab):
			preTable.append(tabFile)
	else:
		preTable.append(tabFile)
		log.debug('Tab as spaces enabled')
	f.close()
else:
	log.debug('Tab as spaces disabled')

if configBE.conf["patch"]["updateBraille"]:
	braille.Region.update = update
else:
	log.info('Update braille function patch disabled')

script_braille_routeTo.__doc__ = _("Routes the cursor to or activates the object under this braille cell")
globalCommands.GlobalCommands.script_braille_routeTo = script_braille_routeTo

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
		if 'brailleDisplayDrivers' in str(type(gesture)):
			if not configBE.conf['general']['stopSpeechUnknown'] and gesture.script == None: stopSpeech = False
			elif hasattr(script, "__func__") and (script.__func__.func_name in [
			'script_braille_dots','script_braille_enter',
			'script_volumePlus','script_volumeMinus','script_toggleVolume',
			'script_ctrl','script_alt','script_nvda','script_win',
			'script_ctrlAlt','script_ctrlAltWin','script_ctrlAltWinShift','script_ctrlAltShift','script_ctrlWin','script_ctrlWinShift','script_ctrlShift','script_altWin','script_altWinShift','script_altShift','script_winShift']
			or (
				not configBE.conf['general']['stopSpeechScroll'] and 
			script.__func__.func_name in ['script_braille_scrollBack','script_braille_scrollForward'])):
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
			log.io("Input: %s" % gesture.identifiers[0])

		if self._captureFunc:
			try:
				if self._captureFunc(gesture) is False:
					return
			except:
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

inputCore.InputManager.executeGesture = executeGesture
NoInputGestureAction = inputCore.NoInputGestureAction
