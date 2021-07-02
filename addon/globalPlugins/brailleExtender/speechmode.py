# speechmode.py
# Part of BrailleExtender addon for NVDA
# Copyright 2021 Emil Hesmyr, released under GPL.
import braille
import config
import speech
import api
import ui

orig_speak = speech.speak

if not ("speech", "to speech") in braille.handler.tetherValues:
	# the speech option can not be positioned such that the user goes directly
	# from it to "automaticly" when using the NVDA + ctrl + t command. If it
	# is, the braille display does not show the focus propperly until the user
	# either switches to another tether option or moves the focus.
	for i in range(len(braille.handler.tetherValues)):
		if braille.handler.tetherValues[i][0] == "auto":
			braille.handler.tetherValues.insert(i + 1, ("speech", "to speech"))


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
#: speech.speakMessage


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
	speechList.append(string)
	global index
	index = len(speechList) - 1
	showSpeech(index)


speech.speak = speak
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
	if braille.handler.getTether != "speech":
		oldBrailleMessage(*args, **kwargs)


braille.handler.message = newBrailleMessage
oldRouteTo = braille.TextRegion.routeTo


def newRouteTo(*args, **kwargs):
	if braille.handler.buffer == braille.handler.mainBuffer and braille.handler.getTether() == "speech":
		api.copyToClip(speechList[index])
		return()
	oldRouteTo(*args, **kwargs)


braille.TextRegion.routeTo = newRouteTo
