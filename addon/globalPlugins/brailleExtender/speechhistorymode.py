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
import wx
import addonHandler
import globalCommands
from logHandler import log

addonHandler.initTranslation()

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

		# Translators: label of a dialog.
		label = _("&Prefix entries with their position in the history")
		self.numberEntries = sHelper.addItem(wx.CheckBox(self, label=label))
		self.numberEntries.SetValue(config.conf["brailleExtender"]["speechHistoryMode"]["numberEntries"])

		# Translators: label of a dialog.
		label = _("&Read entries while browsing history")
		self.speakEntries = sHelper.addItem(wx.CheckBox(self, label=label))
		self.speakEntries.SetValue(config.conf["brailleExtender"]["speechHistoryMode"]["speakEntries"])

	def onSave(self):
		config.conf["brailleExtender"]["speechHistoryMode"]["limit"] = self.limit.Value
		config.conf["brailleExtender"]["speechHistoryMode"]["numberEntries"] = self.numberEntries.IsChecked()
		config.conf["brailleExtender"]["speechHistoryMode"]["speakEntries"] = self.speakEntries.IsChecked()


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
			braille.handler.tetherValues.insert(
				i + 1, ("speech",
				# Translators: The label for a braille setting indicating that braille should be tethered to the speech history.
				_("to speech history")))

if config.conf["brailleExtender"]["speechHistoryMode"]["enabled"] and config.conf["braille"]["autoTether"]:
	config.conf["braille"]["autoTether"] = False
	config.conf["brailleExtender"]["speechHistoryMode"]["enabled"] = False
	braille.handler.setTether("speech")


def showSpeech(index):
	try:
		if braille.handler.getTether() == "speech":
			text = speechList[index]
			if config.conf["brailleExtender"]["speechHistoryMode"]["numberEntries"]:
				size_limit = len(str(config.conf["brailleExtender"]["speechHistoryMode"]["limit"]))
				text = f"#%.{size_limit}d:{text}" % (index+1)
			region = braille.TextRegion(text)
			region.update()
			braille.handler._doNewObject([region])
			if config.conf["brailleExtender"]["speechHistoryMode"]["speakEntries"]:
				speak([speechList[index]], saveString=False)
	except BaseException:
		pass


speechList = []
index = 0

def speak(
	speechSequence,
	symbolLevel=None,
	priority=speech.Spri.NORMAL,
	saveString=True
):
	orig_speak(speechSequence, symbolLevel, priority)
	if not saveString: return
	string = ""
	for i in speechSequence:
		if isinstance(i, str):
			string += i
			if not speechSequence.index(i) == len(speechSequence) - 1:
				string += " "
	global speechList, index
	speechList.append(string)
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
			index -= 1
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
			index += 1
			showSpeech(index)


braille.BrailleBuffer.scrollForward = scrollForward
oldBrailleMessage = braille.handler.message


def newBrailleMessage(*args, **kwargs):
	if braille.handler.getTether() != "speech":
		oldBrailleMessage(*args, **kwargs)


def showSpeechFromRoutingIndex(routingNumber):
	global index
	if not routingNumber:
		api.copyToClip(speechList[index])
		speak([_("Entry copied to clipboard")], saveString=False)
	elif routingNumber == braille.handler.displaySize - 1:
		ui.browseableMessage(speechList[index])
	else:
		direction = routingNumber > braille.handler.displaySize / 2
		if direction:
			index = index - (braille.handler.displaySize - routingNumber) + 1
		else:
			index += routingNumber
		if index < 0:
			index = 0
		if index >= len(speechList):
			index = len(speechList) - 1
	showSpeech(index)


braille.handler.message = newBrailleMessage

# Translators: Reports which position braille is tethered to
# (braille can be tethered automatically or to either focus or review position or speech history).
globalCommands.GlobalCommands.script_braille_toggleTether.__doc__ = _("Toggle tethering of braille between the focus, the review position and the speech history")
