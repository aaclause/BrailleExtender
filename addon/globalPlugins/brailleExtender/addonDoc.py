# coding: utf-8
# addonDoc.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import re
import addonHandler
addonHandler.initTranslation()
import braille
import configBE
from collections import OrderedDict
import cursorManager
import globalCommands
import utils
import ui
from logHandler import log

instanceGP = None

class AddonDoc():
	def __init__(self, instanceGp):
		global instanceGP
		instanceGP = instanceGp
		gestures = instanceGP.getGestures()
		doc = """
		<h1>{NAME}{DISPLAY}</h1>
		<p>Version {VERSION}<br />
		{AUTHOR}<br />
		{URL}</p>
		<p>{DESC}</p>
		""".format(
			NAME=configBE._addonName,
			DISPLAY=configBE.sep + ': ' + _('%s braille display') % configBE.curBD.capitalize() if configBE.gesturesFileExists else '',
			VERSION=configBE._addonVersion,
			AUTHOR=configBE._addonAuthor.replace(
				'<',
				'&lt;').replace(
				'>',
				'&gt;'),
			URL='<a href="%s">%s</a>' % (configBE._addonURL, configBE._addonURL),
			DESC=self.getDescFormated(configBE._addonDesc))
		doc += '<h2 lang="en">Copyrights and acknowledgements</h2>' + ('\n'.join([
			"<p>",
			_("Copyright (C) 2017 André-Abush Clause, and other contributors:"), "</p>",
			"<ul><li>Mohammadreza Rashad &lt;mohammadreza5712@gmail.com&gt;: " + _("Persian translation") + ";</li>",
			"<li>Zvonimir stanecic &lt;zvonimirek222@yandex.com&gt;: " + _("Polish and Croatian translations") + ".</li></ul>",
			"<p>" + _("Additional third party copyrighted code is included:") + "</p>",
			"""<ul><li><em>Attribra</em>{SEP}: Copyright (C) 2017 Alberto Zanella &lt;lapostadialberto@gmail.com&gt; → <a href="https://github.com/albzan/attribra/">https://github.com/albzan/attribra/</a></li>
		""".format(SEP=configBE.sep), "</ul>",
			"<p>" + _("Thanks also to") + ":</p>",
			"<ul><li>Corentin " + _("for his tests and suggestions with") + " Brailliant;</li>",
			"<li>Louis " + _("for his tests and suggestions with") + " Focus.</li></ul>",
			"<p>" + _("And Thank you very much for all your feedback and comments via email.") + " :)</p>"])
		)
		doc += """
		<div id="changelog"><h2>{lastChanges}</h2>
		<p>{future}{sep}: {toCome}</p>
		<h3>2017.12.28</h3>
		<ul>
			<li>{newf}{sep}: {secTable}{sep};</li>
			<li>{newf}{sep}: {tabSpaces}{sep};</li>
			<li>{newf}{sep}: {sayReviewModeScroll}{sep};</li>
			<li>{best} {profs}. {profile1}{sep};</li>
			<li>{best} {rotor}. {rotor1}{sep};</li>
			<li>{bug} {bug1}{sep};</li>
			<li>{bug} {bug2}.</li>
		</ul>
		<h3>2017.11.11</h3>
		<ul>
			<li>{newt}{sep}: {t1}{sep};</li>
			<li>{newt}{sep}: {t2}{sep};</li>
			<li>{bug} {bug0}{sep};</li>
		</ul>
		<hr />
		</div>
		""".format(
			sep=configBE.sep,
			future=_('Coming soon in the next versions'),
			toCome=_('gesture profiles, finalizing tabs in settings, some shortcuts revisions...'),
			lastChanges=_('Change Log'),
			newf=_('New feature'),
			newt=_('New translation'),
			t1=_('Polish'),
			t2=_('Croatian'),
			bug=_('Fix a bug preventing'),
			bug0=_('scroll with the usual gestures on Brailliant displays'),
			bug1=_('the use of locale gestures'),
			bug2=_('keyboard shortcuts from working as expected when a table is specified'),
			best=_('Improvement concerning'),
			profs=_('profiles'),
			profile1=_('Profiles are now reloaded automatically if braille display changes during execution'),
			rotor=_('the rotor'),
			rotor1=_('New modes') + ': ' + _('review') + ', ' + _('Tables') + ', ' + _('Moving in the text') + ' ' + _('and') + ' ' + _('Text selection'),
			secTable=_('possibility to specify a secondary output braille table'),
			tabSpaces=_('Display tab signs as spaces'),
			sayReviewModeScroll=_('In review mode, say the current line during text scrolling'),
			shortcut=_('keyboard shortcuts on braille display')
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
			doc += ('<h2>' + _('Simple keys') + ' (%s)</h2>') % str(len(mKB))
			doc += self.translateLst(mKB)
			doc += ('<h2>' + _('Usual shortcuts') +
					' (%s)</h2>') % str(len(mW))
			doc += self.translateLst(mW)
			doc += ('<h2>' + _('Standard NVDA commands') +
					' (%s)</h2>') % str(len(mNV))
			doc += self.translateLst(mNV)
			doc += '<h2>{0} ({1})</h2>'.format(_('Modifier keys'),
												len(configBE.iniProfile["modifierKeys"]))
			doc += self.translateLst(configBE.iniProfile["modifierKeys"])
			doc += '<h2>' + _('Quick navigation keys') + '</h2>'
			doc += "<p>" + _('In virtual documents (HTML/PDF/…) you can navigate element type by element type using keyboard. These navigation keys should work with your braille terminal equally.</p><p>In addition to these, there are some specific shortcuts:') + "</p>"
			doc += self.translateLst(
				configBE.iniGestures['cursorManager.CursorManager'])
			doc += '<h2>' + _('Rotor feature') + '</h2>'
			doc += self.translateLst({k: configBE.iniProfile["miscs"][k] for k in configBE.iniProfile["miscs"]
								   if 'rotor' in k.lower()}) + self.translateLst(configBE.iniProfile["rotor"])
			doc += ('<h2>' + _('Gadget commands') +
					' (%s)</h2>') % str(len(configBE.iniProfile["miscs"]) - 2)
			doc += self.translateLst(OrderedDict([(k, configBE.iniProfile["miscs"][k])
											   for k in configBE.iniProfile["miscs"] if k not in ['nextRotor', 'priorRotor']]))
			doc += '<h2>{0} ({1})</h2>'.format(_('Shortcuts defined outside add-on'),
												len(braille.handler.display.gestureMap._map))
			doc += '<ul>'
			for g in braille.handler.display.gestureMap._map:
				doc += ('<li>{0}{1}: {2}{3};</li>').format(
					utils.beautifulSht(g).capitalize(),
					configBE.sep,
					utils.uncapitalize(
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							self.getDocScript(
								braille.handler.display.gestureMap._map[g]))),
					configBE.sep)
			doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
			doc += '</ul>'

			# list keyboard layouts
			if not instanceGP.noKeyboarLayout() and 'keyboardLayouts' in configBE.iniProfile:
				lb = instanceGP.getKeyboardLayouts()
				doc += '<h2>{}</h2>'.format(
					_('Keyboard configurations provided'))
				doc += '<p>{}{}:</p><ol>'.format(
					_('Keyboard configurations are'), configBE.sep)
				for l in lb:
					doc += '<li>{}.</li>'.format(l)
				doc += '</ol>'
		else:
			doc += ('<h2>' + _("Warning:") + '</h2><p>' +
					_("BrailleExtender doesn't seem to support your braille display.") + '<br />' +
					_('However, you can reassign most of these features in the "Command Gestures" dialog in the "Preferences" of NVDA.') + '</p>'
					)
		doc += ('<h2>' + _('Shortcuts on system keyboard specific to the add-on') +
				' (%s)</h2>') % str(len(gestures) - 4)
		doc += '<ul>'
		for g in [k for k in gestures if k.lower().startswith('kb:')]:
			if g.lower() not in [
				'kb:volumeup',
				'kb:volumedown',
					'kb:volumemute'] and gestures[g] not in ['logFieldsAtCursor']:
				doc += ('<li>{0}{1}: {2}{3};</li>').format(
					utils.getKeysTranslation(g),
					configBE.sep,
					re.sub(
						'^([A-Z])',
						lambda m: m.group(1).lower(),
						self.getDocScript(
							gestures[g])),
					configBE.sep)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += '</ul>'
		ui.browseableMessage(doc, _('%s\'s documentation') % configBE._addonName, True)

	@staticmethod
	def getDescFormated(txt):
		txt = re.sub(r'\n\* ([^\n]+)(\n|$)', r'\n<li>\1</li>\2', txt)
		txt = re.sub(r'\n\* ([^\n]+)(\n|$)', r'\n<li>\1</li>\2', txt)
		txt = re.sub(r'([^>])\n<li>', r'\1\n<ul><li>', txt)
		txt = re.sub(r'</li>\n([^<]|$)', r'</li></ul>\n\1', txt)
		txt = re.sub(r'</li>$', r'</li></ul>', txt)
		return txt

	@staticmethod
	def getDocScript(n):
		doc = None
		if isinstance(n, list):
			n = str(n[-1][-1])
		if n.startswith('kb:'):
			return _(
				'Emulates pressing %s on the system keyboard') % utils.getKeysTranslation(n)
		places = [
			'instanceGP.script_',
			'globalCommands.commands.script_',
			'cursorManager.CursorManager.script_']
		for place in places:
			try:
				doc = re.sub(r'\.$', '', eval(''.join([place, n, '.__doc__'])))
				break
			except BaseException as e:
				log.debug(e)
		return doc if doc is not None else _('description currently unavailable for this shortcut')


	def translateLst(self, lst):
		doc = '<ul>'
		for g in lst:
			if 'kb:' in g and 'capsLock' not in g and 'insert' not in g:
				if isinstance(lst[g], list):
					doc += '<li>{0}{2}: {1}{2};</li>'.format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(' / '.join(lst[g]).replace('br(%s):' % configBE.curBD, ''), 1),
						configBE.sep)
				else:
					doc += '<li>{0}{2}: {1}{2};</li>'.format(
						utils.getKeysTranslation(g),
						utils.beautifulSht(str(lst[g])),
						configBE.sep)
			elif 'kb:' in g:
				gt = _('caps lock') if 'capsLock' in g else g
				doc += '<li>{0}{2}: {1}{2};</li>'.format(
					gt.replace(
						'kb:', ''), utils.beautifulSht(
						lst[g]).replace(
						'br(%s):' % configBE.curBD, ''), configBE.sep)
			else:
				if isinstance(lst[g], list):
					doc += '<li>{0}{1}: {2}{3};</li>'.format(
						utils.beautifulSht(
							' / '.join(
								lst[g]).replace(
								'br(%s):' % configBE.curBD,
								''),
							1),
						configBE.sep,
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							utils.uncapitalize(
								self.getDocScript(g))),
						configBE.sep)
				else:
					doc += '<li>{0}{1}: {2}{3};</li>'.format(
						utils.beautifulSht(
							lst[g]).replace(
							'br(%s):' % configBE.curBD,
							''),
						configBE.sep,
						re.sub(
							'^([A-Z])',
							lambda m: m.group(1).lower(),
							utils.uncapitalize(
								self.getDocScript(g))),
						configBE.sep)
		doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
		doc += '</ul>'
		return doc
