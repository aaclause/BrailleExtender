# speechmode.py
# Part of BrailleExtender addon for NVDA
# Copyright 2020 André-Abush CLAUSE, released under GPL.
import braille
import config
import speech
import ui

orig_speak = speech.speak

def report_speech_mode():
	if config.conf["brailleExtender"]["speechMode"]:
		ui.message("Speech mode enabled")
	else:
		ui.message("Speech mode disabled")

def toggle_speech_mode():
	config.conf["brailleExtender"]["speechMode"] = not config.conf["brailleExtender"]["speechMode"]


#: speech.speakMessage
def speak(
	speechSequence,
	symbolLevel=None, 
	priority=speech.Spri.NORMAL,
):
	orig_speak(speechSequence, symbolLevel, priority)
	if config.conf["brailleExtender"]["speechMode"]:
		text = ' '.join([m for m in speechSequence if isinstance(m, str)])
		if text: braille.handler.message(text)

speech.speak = speak
