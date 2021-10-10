# speechhistorymode.py
# Part of BrailleExtender addon for NVDA
# Copyright 2021 Emil Hesmyr, André-Abush Clause, released under GPL.
import braille
import config
import speech
import api
import ui
import versionInfo
import gui
from logHandler import log
class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Speech history mode")

	def makeSettings(self, settingsSizer):

		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: label of a dialog.
		label = _("&Number of last announcements to retain:")
		self.limit = sHelper.addLabeledControl(
			label,
			gui.nvdaControls.SelectOnFocusSpinCtrl,
			min=0,
			initial=config.conf["brailleExtender"]["speechHistoryMode"]["limit"]
		)

	def onSave(self):
		config.conf["brailleExtender"]["speechHistoryMode"]["limit"] = self.limit.Value


if versionInfo.version_year < 2021:
	orig_speak= speech.speak
else:
	orig_speak = speech.speech.speak
speechInList = False
for i in braille.handler.tetherValues:
	if "speech" in i:
		speechInList = True
if not speechInList:
	# the speech option can not be positioned such that the user goes directly
	# from it to "automaticly" when using the NVDA + ctrl + t command. If it
	# is, the braille display does not show the focus propperly until the user
	# either switches to another tether option or moves the focus.
	for i in range(len(braille.handler.tetherValues)):
		if braille.handler.tetherValues[i][0] == braille.handler.TETHER_AUTO:
			braille.handler.tetherValues.insert(i + 1, ("speech", "to speech"))

if config.conf["brailleExtender"]["speechHistoryMode"]["enabled"] and config.conf["braille"][
		"autoTether"]:
	config.conf["braille"]["autoTether"] = False
	config.conf["brailleExtender"]["speechHistoryMode"]["enabled"] = False
	braille.handler.setTether("speech")


def showSpeech(index):
	try:
		if braille.handler.getTether() == "speech":
			region = braille.TextRegion(speechList[index])
			region.update()
			braille.handler._doNewObject([region])
	except BaseException:
		pass


speechList = []
index = 0

def speak(
	speechSequence,
	symbolLevel=None,
	priority=speech.Spri.NORMAL,
):
	orig_speak(speechSequence, symbolLevel, priority)
	string = ""
	for i in speechSequence:
		if isinstance(i, str):
			string += i
			if not speechSequence.index(i) == len(speechSequence) - 1:
				string += " "
	global speechList, index
	speechList.append(string)
	log.info(f"adding {len(speechList)} {string}")
	speechList = speechList[-config.conf["brailleExtender"]["speechHistoryMode"]["limit"]:]
	index = len(speechList) - 1
	showSpeech(index)

if versionInfo.version_year < 2021:
	speech.speak = speak
else:
	speech.speech.speak = speak
oldScrollBack = braille.BrailleBuffer.scrollBack


def scrollBack(self):
	windowRawText = braille.handler.mainBuffer.windowRawText
	oldScrollBack(self)
	if braille.handler.buffer == braille.handler.mainBuffer and braille.handler.getTether(
	) == "speech" and braille.handler.buffer.windowRawText == windowRawText:
		global index
		if index > 0:
			index = index - 1
		showSpeech(index)


braille.BrailleBuffer.scrollBack = scrollBack
oldScrollForward = braille.BrailleBuffer.scrollForward


def scrollForward(self):
	windowRawText = braille.handler.mainBuffer.windowRawText
	oldScrollForward(self)
	if braille.handler.buffer == braille.handler.mainBuffer and braille.handler.getTether(
	) == "speech" and braille.handler.buffer.windowRawText == windowRawText:
		global index
		if not index >= len(speechList) - 1:
			index = index + 1
			showSpeech(index)


braille.BrailleBuffer.scrollForward = scrollForward
oldBrailleMessage = braille.handler.message


def newBrailleMessage(*args, **kwargs):
	if braille.handler.getTether() != "speech":
		oldBrailleMessage(*args, **kwargs)


braille.handler.message = newBrailleMessage
oldRouteTo = braille.TextRegion.routeTo


def newRouteTo(*args, **kwargs):
	if braille.handler.buffer == braille.handler.mainBuffer and braille.handler.getTether() == "speech":
		api.copyToClip(speechList[index])
		return()
	oldRouteTo(*args, **kwargs)


braille.TextRegion.routeTo = newRouteTo
