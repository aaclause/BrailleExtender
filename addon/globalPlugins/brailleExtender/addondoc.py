# coding: utf-8
# addondoc.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2021 André-Abush CLAUSE, released under GPL.

import re

import addonHandler

addonHandler.initTranslation()
import braille
from . import addoncfg
from collections import OrderedDict
import config
import cursorManager
import globalCommands
import ui
import random
from .undefinedchars import CHOICES_LABELS
from . import utils
from .common import addonDesc, addonGitHubURL, addonName, addonSummary, addonURL, addonVersion, punctuationSeparator

def escape(text):
	chars = {"&": "&amp;", '"': "&quot;", "'": "&apos;", "<": "&lt;", ">": "&gt;"}
	return "".join(chars.get(c, c) for c in text)


def initializeRandomChar():
	global chosenChar
	chosenChar = random.choice("#$£€=+()*,;:.?!/\"&")

URLHUC = "https://danielmayr.at/huc/"
chosenChar = None

def getFeaturesDoc():
	undefinedCharsSamples = [
		[_("Character"), "HUC8", _("Hexadecimal"), _("Decimal"), _("Octal"), _("Binary")],
		['👍', "⣭⢤⡙", "⠭1f44d or ⠓1f44d", "⠙128077", "⠕372115", "⠃11111010001001101"],
		['😀', "⣭⡤⣺", "⠭1f600 or ⠓1f600", "⠙128512", "⠕373000", "⠃11111011000000000"],
		['🍑', "⣭⠤⠕", "⠭1f351 or ⠓1f351", "⠙127825", "⠕371521", "⠃11111001101010001"],
		['🌊', "⣭⠤⠺", "⠭1f30a or ⠓1f30a", "⠙127754", "⠕371412", "⠃11111001100001010"]
	]
	for i in range(1, len(undefinedCharsSamples)):
		ch = undefinedCharsSamples[i][0][0]
		undefinedCharsSamples[i][0] = "%s (%s)" % (ch, utils.getSpeechSymbols(ch))

	braillePattern = config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"]

	contextualOption = _("Show punctuation/symbol &name for undefined characters if available").replace('&', '')
	features = {
	_("Speech History Mode"): [
		"<p>",
		_("This mode allows to review the last announcements that have been spoken by NVDA."),
		"<br />",
		_("To enable this mode, you can use the appropriate toggle command or the basic gesture NVDA+Control+t."),
		"<br />",
		_("In this mode, you can use:"),
		"</p><ul>",
			"<li>" + _("the first routing cursor to copy the current announcement to the Clipboard.") + "</li>",
			"<li>" + _("the last routing cursor to show the current announcement in a browseable message.") + "</li>",
			"<li>" + _("the other routing cursors to navigate through history entries.") + "</li>",
		"</ul><p>",
			_('Please note that specific settings are available for this feature under the category "Speech History Mode".'),
		"</p>"
	],
		_("Representation of undefined characters"): [
			"<p>",
			_("The extension allows you to customize how an undefined character should be represented within a braille table. To do so, go to the — Representation of undefined characters — settings. You can choose between the following representations:"),
			"</p><ul>",
			''.join([f"<li>{choice}</li>" for choice in CHOICES_LABELS.values()]),
			"</ul><p>",
			_("You can also combine this option with the “describe the character if possible” setting."),
			"</p><p>",
			_("Notes:"),
			"</p><ul>",
			"<li>" + _("To distinguish the undefined set of characters while maximizing space, the best combination is the usage of the HUC8 representation without checking the “{contextualOption}” option.").format(contextualOption=contextualOption) + "</li>",
			"<li>" + _("To learn more about the HUC representation, see {url}").format(url=f"<br />{URLHUC}") + "</li>",
			"<li>" + _("Keep in mind that definitions in tables and those in your table dictionaries take precedence over character descriptions, which also take precedence over the chosen representation for undefined characters.") + "</li>",
			"</ul>"
		],
		_("Getting Current Character Info"): [
			"<p>",
			_("This feature allows you to obtain various information regarding the character under the cursor using the current input braille table, such as:"),
			"<br />",
			_("the HUC8 and HUC6 representations; the hexadecimal, decimal, octal or binary values; A description of the character if possible; the Unicode braille representation and the braille pattern dots."),
			"</p><p>",
			_("Pressing the defined gesture associated to this function once shows you the information in a flash message and a double-press displays the same information in a virtual NVDA buffer."),
			"<br />",
			_("On supported displays the defined gesture is ⡉+space. No system gestures are defined by default."),
			"</p><p>",
			_("For example, for the '{chosenChar}' character, we will get the following information:").format(chosenChar=chosenChar),
			"<br /><blockquote><pre>" + utils.currentCharDesc(chosenChar, 0) + "</pre></blockquote></p>",
		],
		_("Advanced braille input"): [
			"<p>",
			_("This feature allows you to enter any character from its HUC8 representation or its hexadecimal/decimal/octal/binary value. Moreover, it allows you to develop abbreviations. To use this function, enter the advanced input mode and then enter the desired pattern. Default gestures: NVDA+Windows+i or ⡊+space (on supported displays). Press the same gesture to exit this mode. Alternatively, an option allows you to automatically exit this mode after entering a single pattern. "),
			"</p><p>",
			_("If you want to enter a character from its HUC8 representation, simply enter the HUC8 pattern. Since a HUC8 sequence must fit on 3 or 4 cells, the interpretation will be performed each time 3 or 4 dot combinations are entered. If you wish to enter a character from its hexadecimal, decimal, octal or binary value, do the following:"),
			"</p><ol>",
			"<li>" + _("Enter {braillePattern}").format(braillePattern=braillePattern) + "</li>",
			"<li>" + _("Specify the basis as follows") + f"{punctuationSeparator}:",
			"<ul><li>",
			_("⠭ or ⠓") + f"{punctuationSeparator}: " + _("for a hexadecimal value") + "</li>",
			f"<li>⠙{punctuationSeparator}: " + _("for a decimal value") + "</li>",
			f"<li>⠕{punctuationSeparator}: " + _("for an octal value") + "</li>",
			f"<li>⠃{punctuationSeparator}: " + _("for a binary value") + "</li>",
			"</ul></li>",
			"<li>" + _("Enter the value of the character according to the previously selected basis.") + "</li>",
			"<li>" + _("Press Space to validate.") + "</li>",
			"</ol>",
			"<p>",
			_('For abbreviations, you must first add them in the dialog box — Advanced input mode dictionary —. Then, you just have to enter your abbreviation and press space to expand it. For example, you can define the following abbreviations: "⠎⠺" with "sandwich", "⠋⠛⠋⠗" to "🇫🇷".'),
			"</p><p>",
			_("Here are some examples of sequences to be entered for given characters:"),
			"</p><table>",
			''.join(["<tr>%s</tr>" % (''.join(["<{0}>{1}</{0}>".format("th" if i == 0 else "td", e) for e in l])) for i, l in enumerate(undefinedCharsSamples)]),
			"</table><p>",
			_("Note: the HUC6 input is currently not supported."),
			"</p>",
		],
		_("One-hand mode"): [
			"<p>",
			_("This feature allows you to compose a cell in several steps. This can be activated in the general settings of the extension's preferences or on the fly using NVDA+Windows+h gesture by default (⡂+space on supported displays). Three input methods are available."),
			"<h4>" + _("Method #1: fill a cell in 2 stages on both sides") + "</h4>",
			"<p>",
			_("With this method, type the left side dots, then the right side dots. If one side is empty, type the dots correspondig to the opposite side twice, or type the dots corresponding to the non-empty side in 2 steps."),
			"<br />", _("For example:"),
			"</p><ul>",
			"<li>" + _("For ⠛: press dots 1-2 then dots 4-5.") + "</li>",
			"<li>" + _("For ⠃: press dots 1-2 then dots 1-2, or dot 1 then dot 2.") + "</li>",
			"<li>" + _("For ⠘: press 4-5 then 4-5, or dot 4 then dot 5.") + "</li>",
			"</ul>",
			"<h4>" + _("Method #2: fill a cell in two stages on one side (Space = empty side)") + "</h4>",
			"<p>",
			_("Using this method, you can compose a cell with one hand, regardless of which side of the Braille keyboard you choose. The first step allows you to enter dots 1-2-3-7 and the second one 4-5-6-8. If one side is empty, press space. An empty cell will be obtained by pressing the space key twice."),
			"<br />" + _("For example:"),
			"</p><ul>",
			"<li>" + _("For ⠛: press dots 1-2 then dots 1-2, or dots 4-5 then dots 4-5.") + "</li>",
"<li>" + _("For ⠃: press dots 1-2 then space, or 4-5 then space.") + "</li>",
"<li>" + _("For ⠘: press space then 1-2, or space then dots 4-5.") + "</li>",
			"</ul>",
			"<h4>" + _("Method #3: fill a cell dots by dots (each dot is a toggle, press Space to validate the character)") + "</h4>",
			"<p>",
			_("In this mode, each dot is a toggle. You must press the space key as soon as the cell you have entered is the desired one to input the character. Thus, the more dots are contained in the cell, the more ways you have to enter the character."),
			"<br />" + _("For example, for ⠛, you can compose the cell in the following ways") + ':',
			"</p><ul>",
			"<li>" + _("Dots 1-2, then dots 4-5, then space.") + "</li>",
			"<li>" + _("Dots 1-2-3, then dot 3 (to correct), then dots 4-5, then space.") + "</li>",
			"<li>" + _("Dot 1, then dots 2-4-5, then space.") + "</li>",
			"<li>" + _("Dots 1-2-4, then dot 5, then space.") + "</li>",
			"<li>" + _("Dot 2, then dot 1, then dot 5, then dot 4, and then space.") + "</li>",
			"<li>" + _("Etc.") + "</li>",
			"</ul>"
		]
	}
	out = ""
	for title, desc in features.items():
		out += f"<h3>{title}</h3>{''.join(desc)}"
	return out

class AddonDoc:
	instanceGP = None

	def __init__(self, instanceGP):
		initializeRandomChar()
		if not instanceGP:
			return
		self.instanceGP = instanceGP
		gestures = instanceGP.getGestures()
		manifestDescription = self.getDescFormated(addonDesc)
		doc = f"<h1>{addonSummary} {addonVersion} — " + _("Documentation") + "</h1>"
		doc += f"<p>{manifestDescription}</p>"
		doc += "<h2>" + _("Let's explore some features") + "</h2>"
		doc += getFeaturesDoc()
		doc += "<h2>" + _("Profile gestures") + "</h2>"
		if addoncfg.gesturesFileExists:
			brailleDisplayDriverName = addoncfg.curBD.capitalize()
			profileName = "default"
			doc += ''.join([
				"<p>",
				_("Driver loaded") + f"{punctuationSeparator}: {brailleDisplayDriverName}" + "<br />",
				_("Profile") + f"{punctuationSeparator}: {profileName}",
				"</p>"
			])
			mKB = OrderedDict()
			mNV = OrderedDict()
			mW = OrderedDict()
			for g in addoncfg.iniGestures["globalCommands.GlobalCommands"].keys():
				if "kb:" in g:
					if "+" in g:
						mW[g] = addoncfg.iniGestures["globalCommands.GlobalCommands"][g]
					else:
						mKB[g] = addoncfg.iniGestures["globalCommands.GlobalCommands"][g]
				else:
					mNV[g] = addoncfg.iniGestures["globalCommands.GlobalCommands"][g]
			doc += ("<h3>" + _("Simple keys") + " (%d)</h3>") % len(mKB)
			doc += self.translateLst(mKB)
			doc += ("<h3>" + _("Usual shortcuts") + " (%d)</h3>") % len(mW)
			doc += self.translateLst(mW)
			doc += ("<h3>" + _("Standard NVDA commands") + " (%d)</h3>") % len(mNV)
			doc += self.translateLst(mNV)
			doc += "<h3>{} ({})</h3>".format(
				_("Modifier keys"), len(addoncfg.iniProfile["modifierKeys"])
			)
			doc += self.translateLst(addoncfg.iniProfile["modifierKeys"])
			doc += "<h3>" + _("Quick navigation keys") + "</h3>"
			doc += self.translateLst(
				addoncfg.iniGestures["cursorManager.CursorManager"]
			)
			doc += "<h3>" + _("Rotor feature") + "</h3>"
			doc += self.translateLst(
				{
					k: addoncfg.iniProfile["miscs"][k]
					for k in addoncfg.iniProfile["miscs"]
					if "rotor" in k.lower()
				}
			) + self.translateLst(addoncfg.iniProfile["rotor"])
			doc += ("<h3>" + _("Gadget commands") + " (%d)</h3>") % (
                    len(addoncfg.iniProfile["miscs"]) - 2
			)
			doc += self.translateLst(
				OrderedDict(
					[
						(k, addoncfg.iniProfile["miscs"][k])
						for k in addoncfg.iniProfile["miscs"]
						if k not in ["nextRotor", "priorRotor"]
					]
				)
			)
			doc += "<h3>{} ({})</h3>".format(
				_("Shortcuts defined outside add-on"),
				len(braille.handler.display.gestureMap._map),
			)
			doc += "<ul>"
			for g in braille.handler.display.gestureMap._map:
				doc += ("<li>{}{}: {}{};</li>").format(
					utils.beautifulSht(g),
					punctuationSeparator,
					utils.uncapitalize(
						re.sub(
							"^([A-Z])",
							lambda m: m.group(1).lower(),
							self.getDocScript(
								braille.handler.display.gestureMap._map[g]
							),
						)
					),
					punctuationSeparator,
				)
			doc = re.sub(r"[  ]?;(</li>)$", r".\1", doc)
			doc += "</ul>"

			# list keyboard layouts
			if (
				not instanceGP.noKeyboarLayout()
				and "keyboardLayouts" in addoncfg.iniProfile
			):
				lb = instanceGP.getKeyboardLayouts()
				doc += "<h3>{}</h3>".format(_("Keyboard configurations provided"))
				doc += (
					"<p>"
					+ _("Keyboard configurations are")
					+ punctuationSeparator
					+ "</p><ol>"
				)
				doc += "".join(f"<li>{l}.</li>" for l in lb)
				doc += "</ol>"
		else:
			doc += (
				"<h3>"
				+ _("Warning:")
				+ "</h3><p>"
				+ _("BrailleExtender has no gesture map yet for your braille display.")
				+ "<br />"
				+ _(
					"However, you can still assign your own gestures in the \"Input Gestures\" dialog (under Preferences menu)."
				)
				+ "</p>"
			)
		doc += ("<h2>" + _("Add-on gestures on the system keyboard") + " (%s)</h2>") % (
			len(gestures) - 4
		)
		doc += "<ul>"
		for g in [k for k in gestures if k.lower().startswith("kb:")]:
			if g.lower() not in [
				"kb:volumeup",
				"kb:volumedown",
				"kb:volumemute",
			] and gestures[g] not in ["logFieldsAtCursor"]:
				doc += ("<li>{}{}: {}{};</li>").format(
					utils.getKeysTranslation(g),
					punctuationSeparator,
					re.sub(
						"^([A-Z])",
						lambda m: m.group(1).lower(),
						self.getDocScript(gestures[g]),
					),
					punctuationSeparator,
				)
		doc = re.sub(r"[  ]?;(</li>)$", r".\1", doc)
		doc += "</ul>"
		translators = {
			_("Arabic"): "Ikrami Ahmad",
			_("Chinese (Taiwan)"): "蔡宗豪 Victor Cai <surfer0627@gmail.com>",
			_("Croatian"): "Zvonimir Stanečić <zvonimirek222@yandex.com>",
			_("Danish"): "Daniel Gartmann <dg@danielgartmann.dk>",
			_("English and French"): "Sof <hellosof@gmail.com>, Joseph Lee, André-Abush Clause <dev@andreabc.net>, Oreonan <corentin@progaccess.net>",
			_("German"): "Adriani Botez <adriani.botez@gmail.com>, Karl Eick <hozosch@web.de>, Rene Linke <rene.linke@hamburg.de>, Jürgen Schwingshandl <jbs@b-a-c.at>",
			_("Hebrew"): "Shmuel Naaman <shmuel_naaman@yahoo.com>, Afik Sofer, David Rechtman, Pavel Kaplan",
			_("Italian"): "Simone Dal Maso <simone.dalmaso@gmail.com>, Fabrizio Marini <marini.carlo@fastwebnet.it>",
			_("Persian"): "Mohammadreza Rashad <mohammadreza5712@gmail.com>",
			_("Polish"): "Zvonimir Stanečić <zvonimirek222@yandex.com>, Dorota Krać",
			_("Russian"): "Zvonimir Stanečić <zvonimirek222@yandex.com>, Pavel Kaplan <pavel46@gmail.com>, Artem Plaksin <admin@maniyax.ru>",
			_("Spanish"): "Eric Duarte Quintanilla <https://ericdq.com/>",
			_("Turkish"): "Umut Korkmaz <umutkork@gmail.com>",
			_("Ukrainian"): "VovaMobile",
		}
		doc += (
			"<h2>" + _("Copyrights and acknowledgements") + "</h2>"
			+ (
				"".join(
					[
						"<p>",
						"Copyright (C) 2016-2021 André-Abush Clause ",
						_("and other contributors"),
						":<br />",
						f"<pre>{addonGitHubURL}\n{addonURL}</pre>",
						"</p>",
						"<h3>" + _("Translators") + "</h3><ul>",
					]
				)
			)
		)
		for language, authors in sorted(translators.items()):
			doc += f"<li>{language}{punctuationSeparator}: {escape(authors)}</li>"
		doc += "".join(
			[
				"</ul>",
				"<h3>" + _("Code contributions and other") + "</h3>",
				"<ul>",
				"<li>" + _("Speech mode feature:") + " Emil Hesmyr &lt;emilhe@viken.no&gt;" + "</li>",
				"</ul>",
				"<p>"
				+ _("Code maintenance (cleanup, rewrites, optimizations) thanks to:")
				+ "</p>",
				"<ul>"
					+ "<li>Joseph Lee &lt;joseph.lee22590@gmail.com&gt;</li>"
				+ "</ul>",
				"<p>"
				+ _("Additional third party copyrighted code is included:")
				+ "</p>",
				"<ul>",
				f"<li><em>Attribra</em>{punctuationSeparator}: Copyright (C) 2017 Alberto Zanella &lt;lapostadialberto@gmail.com&gt; → https://github.com/albzan/attribra/</li>",
				"</ul>",
				"<p>"
				+ _("Thanks also to")
				+ punctuationSeparator + ": Daniel Cotto, Daniel Mayr, Dawid Pieper, Corentin, Louis...<br />",
				_("Finally thank you very much for all your feedback and comments.")
				+ " ☺</p>",
			]
		)
		ui.browseableMessage(doc, _("%s's documentation") % addonName, True)

	@staticmethod
	def getDescFormated(txt):
		txt = re.sub(r"\n\* ([^\n]+)(\n|$)", r"\n<li>\1</li>\2", txt)
		txt = re.sub(r"\n\* ([^\n]+)(\n|$)", r"\n<li>\1</li>\2", txt)
		txt = re.sub(r"([^>])\n<li>", r"\1\n<ul><li>", txt)
		txt = re.sub(r"</li>\n([^<]|$)", r"</li></ul>\n\1", txt)
		txt = re.sub(r"</li>$", r"</li></ul>", txt)
		return txt

	def getDocScript(self, n):
		if n == "defaultQuickLaunches":
			n = "quickLaunch"
		doc = None
		if isinstance(n, list):
			n = str(n[-1][-1])
		if n.startswith("kb:"):
			return _(
				"Emulates pressing %s on the system keyboard"
			) % utils.getKeysTranslation(n)
		places = [globalCommands.commands, self.instanceGP, cursorManager.CursorManager]
		for place in places:
			func = getattr(place, ("script_%s" % n), None)
			if func:
				doc = func.__doc__
				break
		return (
			doc
			if doc is not None
			else _("description currently unavailable for this shortcut")
		)

	def translateLst(self, lst):
		doc = "<ul>"
		for g in lst:
			if "kb:" in g and "capsLock" not in g and "insert" not in g:
				if isinstance(lst[g], list):
					doc += "<li>{0}{2}: {1}{2};</li>".format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(lst[g]),
						punctuationSeparator,
					)
				else:
					doc += "<li>{0}{2}: {1}{2};</li>".format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(lst[g]),
						punctuationSeparator,
					)
			elif "kb:" in g:
				gt = _("caps lock") if "capsLock" in g else g
				doc += "<li>{0}{2}: {1}{2};</li>".format(
					gt.replace("kb:", ""),
					utils.beautifulSht(lst[g]),
					punctuationSeparator,
				)
			else:
				if isinstance(lst[g], list):
					doc += "<li>{}{}: {}{};</li>".format(
						utils.beautifulSht(lst[g]),
						punctuationSeparator,
						re.sub(
							"^([A-Z])",
							lambda m: m.group(1).lower(),
							utils.uncapitalize(self.getDocScript(g)),
						),
						punctuationSeparator,
					)
				else:
					doc += "<li>{}{}: {}{};</li>".format(
						utils.beautifulSht(lst[g]),
						punctuationSeparator,
						re.sub(
							"^([A-Z])",
							lambda m: m.group(1).lower(),
							utils.uncapitalize(self.getDocScript(g)),
						),
						punctuationSeparator,
					)
		doc = re.sub(r"[  ]?;(</li>)$", r".\1", doc)
		doc += "</ul>"
		return doc
