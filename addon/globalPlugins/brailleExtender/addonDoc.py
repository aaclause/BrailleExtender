# coding: utf-8
# addonDoc.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import re
import addonHandler
addonHandler.initTranslation()
import braille
from . import configBE
from collections import OrderedDict
import cursorManager
import globalCommands
import ui
from . import utils
from .common import *

class AddonDoc:

	instanceGP = None

	def __init__(self, instanceGP):
		if not instanceGP: return
		self.instanceGP = instanceGP
		gestures = instanceGP.getGestures()
		doc = """
		<h1>{NAME}{DISPLAY}{PROFILE}</h1>
		<p>Version {VERSION}<br />
		<p>{DESC}</p>
		""".format(
			NAME=addonName,
			DISPLAY=punctuationSeparator + ': ' + _('%s braille display') % configBE.curBD.capitalize() if configBE.gesturesFileExists else '',
			PROFILE = ", "+_("profile loaded: %s") % "default",
			VERSION=addonVersion,
			DESC=self.getDescFormated(addonDesc)
		)
		if configBE.gesturesFileExists:
			mKB = OrderedDict()
			mNV = OrderedDict()
			mW = OrderedDict()
			for g in configBE.iniGestures['globalCommands.GlobalCommands'].keys(
			):
				if 'kb:' in g:
					if '+' in g:
						mW[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
					else:
						mKB[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
				else:
					mNV[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
			doc += ("<h2>" + _("Simple keys") + " (%d)</h2>") % len(mKB)
			doc += self.translateLst(mKB)
			doc += ("<h2>" + _("Usual shortcuts") + " (%d)</h2>") % len(mW)
			doc += self.translateLst(mW)
			doc += ("<h2>" + _("Standard NVDA commands") + " (%d)</h2>") % len(mNV)
			doc += self.translateLst(mNV)
			doc += "<h2>{0} ({1})</h2>".format(_("Modifier keys"), len(configBE.iniProfile["modifierKeys"]))
			doc += self.translateLst(configBE.iniProfile["modifierKeys"])
			doc += "<h2>" + _("Quick navigation keys") + "</h2>"
			doc += self.translateLst(configBE.iniGestures['cursorManager.CursorManager'])
			doc += "<h2>" + _("Rotor feature") + "</h2>"
			doc += self.translateLst({k: configBE.iniProfile["miscs"][k] for k in configBE.iniProfile["miscs"] if "rotor" in k.lower()}) + self.translateLst(configBE.iniProfile["rotor"])
			doc += ("<h2>" + _("Gadget commands") + " (%d)</h2>") % (len(configBE.iniProfile["miscs"]) - 2)
			doc += self.translateLst(OrderedDict([(k, configBE.iniProfile["miscs"][k]) for k in configBE.iniProfile["miscs"] if k not in ['nextRotor', 'priorRotor']]))
			doc += "<h2>{0} ({1})</h2>".format(_("Shortcuts defined outside add-on"), len(braille.handler.display.gestureMap._map))
			doc += "<ul>"
			for g in braille.handler.display.gestureMap._map:
				doc += ("<li>{0}{1}: {2}{3};</li>").format(
					utils.beautifulSht(g),
					punctuationSeparator,
					utils.uncapitalize(
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							self.getDocScript(
								braille.handler.display.gestureMap._map[g]))),
					punctuationSeparator)
			doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
			doc += "</ul>"

			# list keyboard layouts
			if not instanceGP.noKeyboarLayout() and 'keyboardLayouts' in configBE.iniProfile:
				lb = instanceGP.getKeyboardLayouts()
				doc += '<h2>{}</h2>'.format(
					_('Keyboard configurations provided'))
				doc += '<p>{}{}:</p><ol>'.format(
					_('Keyboard configurations are'), punctuationSeparator)
				for l in lb:
					doc += '<li>{}.</li>'.format(l)
				doc += '</ol>'
		else:
			doc += (
				"<h2>" + _("Warning:") + "</h2><p>" +
				_("BrailleExtender has no gesture map yet for your braille display.") + "<br />" +
				_("However, you can still assign your own gestures in the \"Input Gestures\" dialog (under Preferences menu).") + "</p>"
			)
		doc += ("<h2>" + _("Add-on gestures on the system keyboard") +
				" (%s)</h2>") % (len(gestures) - 4)
		doc += "<ul>"
		for g in [k for k in gestures if k.lower().startswith('kb:')]:
			if g.lower() not in [
				"kb:volumeup",
				"kb:volumedown",
					"kb:volumemute"] and gestures[g] not in ["logFieldsAtCursor"]:
				doc += ("<li>{0}{1}: {2}{3};</li>").format(
					utils.getKeysTranslation(g),
					punctuationSeparator,
					re.sub(
						"^([A-Z])",
						lambda m: m.group(1).lower(),
						self.getDocScript(gestures[g])
					),
					punctuationSeparator
				)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += "</ul>"
		translators = {
			_("Arabic"): "Ikrami Ahmad",
			_("Croatian"): "Zvonimir Stanečić <zvonimirek222@yandex.com>",
			_("Danish"): "Daniel Gartmann <dg@danielgartmann.dk>",
			_("German"): "Adriani Botez <adriani.botez@gmail.com>, Karl Eick, Jürgen Schwingshandl <jbs@b-a-c.at>",
			_("Hebrew"): "Shmuel Naaman <shmuel_naaman@yahoo.com>, Afik Sofer, David Rechtman, Pavel Kaplan",
			_("Persian"): "Mohammadreza Rashad <mohammadreza5712@gmail.com>",
			_("Polish"): "Zvonimir Stanečić, Dorota Krać",
			_("Russian"): "Zvonimir Stanečić, Pavel Kaplan <pavel46@gmail.com>",
		}
		doc += "<h2>" + _("Copyrights and acknowledgements") + "</h2>" + (''.join([
			"<p>",
			"Copyright (C) 2016-2020 André-Abush Clause ", _("and other contributors"),
			":<br />",
			"<pre>%s\n%s</pre>" % (addonURL, addonGitHubURL),
			"</p>",
			"<h3>" + _("Translators") + "</h3><ul>"
		]))
		for language, authors in translators.items():
			doc += f"<li>{language}{punctuationSeparator}: {authors}</li>"
		doc += ''.join([
			"</ul>",
			"<h3>" + _("Code contributions and other")+"</h3><p>" + _("Additional third party copyrighted code is included:") + "</p>",
			"""<ul><li><em>Attribra</em>{SEP}: Copyright (C) 2017 Alberto Zanella &lt;lapostadialberto@gmail.com&gt; → <a href="https://github.com/albzan/attribra/">https://github.com/albzan/attribra/</a></li>
		""".format(SEP=punctuationSeparator), "</ul>",
			"<p>" + _("Thanks also to") + punctuationSeparator +": ",
			"Daniel Cotto, Corentin, Louis.</p>",
			"<p>" + _("And thank you very much for all your feedback and comments.") + " ☺</p>"
		])
		ui.browseableMessage(doc, _("%s\'s documentation") % addonName, True)

	@staticmethod
	def getDescFormated(txt):
		txt = re.sub(r'\n\* ([^\n]+)(\n|$)', r'\n<li>\1</li>\2', txt)
		txt = re.sub(r'\n\* ([^\n]+)(\n|$)', r'\n<li>\1</li>\2', txt)
		txt = re.sub(r'([^>])\n<li>', r'\1\n<ul><li>', txt)
		txt = re.sub(r'</li>\n([^<]|$)', r'</li></ul>\n\1', txt)
		txt = re.sub(r'</li>$', r'</li></ul>', txt)
		return txt

	def getDocScript(self, n):
		if n == "defaultQuickLaunches": n = "quickLaunch"
		doc = None
		if isinstance(n, list):
			n = str(n[-1][-1])
		if n.startswith('kb:'): return _("Emulates pressing %s on the system keyboard") % utils.getKeysTranslation(n)
		places = [globalCommands.commands, self.instanceGP, cursorManager.CursorManager]
		for place in places:
			func = getattr(place, ('script_%s' % n), None)
			if func:
				doc = func.__doc__
				break
		return doc if doc is not None else _("description currently unavailable for this shortcut")


	def translateLst(self, lst):
		doc = '<ul>'
		for g in lst:
			if 'kb:' in g and 'capsLock' not in g and 'insert' not in g:
				if isinstance(lst[g], list):
					doc += '<li>{0}{2}: {1}{2};</li>'.format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(lst[g]),
						punctuationSeparator)
				else:
					doc += '<li>{0}{2}: {1}{2};</li>'.format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(lst[g]),
						punctuationSeparator)
			elif 'kb:' in g:
				gt = _('caps lock') if 'capsLock' in g else g
				doc += '<li>{0}{2}: {1}{2};</li>'.format(
					gt.replace(
						'kb:', ''), utils.beautifulSht(lst[g]), punctuationSeparator)
			else:
				if isinstance(lst[g], list):
					doc += '<li>{0}{1}: {2}{3};</li>'.format(utils.beautifulSht(lst[g]),
						punctuationSeparator,
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							utils.uncapitalize(
								self.getDocScript(g))),
						punctuationSeparator)
				else:
					doc += '<li>{0}{1}: {2}{3};</li>'.format(
						utils.beautifulSht(
							lst[g]), punctuationSeparator,
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							utils.uncapitalize(
								self.getDocScript(g))),
						punctuationSeparator)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += "</ul>"
		return doc
