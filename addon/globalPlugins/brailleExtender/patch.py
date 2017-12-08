# coding: utf-8
import braille
import config
import configBE
import globalCommands
import louis
import scriptHandler
import speech
import textInfos
import addonHandler
addonHandler.initTranslation()
instanceGP = None

# customize basic functions
def sayCurrentLine():
	global instanceGP
	if configBE.conf['general']['speakScroll'] and not instanceGP.autoScrollRunning:
		try:
			scriptHandler.executeScript(globalCommands.commands.script_review_currentLine, None)
			ui.message(unicode(self.rawText).replace('\0',''))
		except:
			pass

# braille.TextInfoRegion.nextLine()
def nextLine(self):
	dest = self._readingInfo.copy()
	moved = dest.move(self._getReadingUnit(), 1)
	if not moved:
		if self.allowPageTurns and isinstance(dest.obj,textInfos.DocumentWithPageTurns):
			try:
				dest.obj.turnPage()
			except RuntimeError:
				pass
			else:
				dest=dest.obj.makeTextInfo(textInfos.POSITION_FIRST)
		else: # no page turn support
			return
	dest.collapse()
	self._setCursor(dest)
	sayCurrentLine()

# braille.TextInfoRegion.previousLine()
def previousLine(self, start=False):
	dest = self._readingInfo.copy()
	dest.collapse()
	if start:
		unit = self._getReadingUnit()
	else:
		# If the end of the reading unit is desired, move to the last character.
		unit = textInfos.UNIT_CHARACTER
	moved = dest.move(unit, -1)
	if not moved:
		if self.allowPageTurns and isinstance(dest.obj,textInfos.DocumentWithPageTurns):
			try:
				dest.obj.turnPage(previous=True)
			except RuntimeError:
				pass
			else:
				dest=dest.obj.makeTextInfo(textInfos.POSITION_LAST)
				dest.expand(unit)
		else: # no page turn support
			return
	dest.collapse()
	self._setCursor(dest)
	sayCurrentLine()

braille.TextInfoRegion.previousLine = previousLine
braille.TextInfoRegion.nextLine = nextLine
