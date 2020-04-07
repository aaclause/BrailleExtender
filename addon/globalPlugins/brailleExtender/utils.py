# coding: utf-8
# utils.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os.path as osp
import re
import api
import braille
import brailleTables
import characterProcessing
import louis
import config
import languageHandler
import ui
import scriptHandler
import speech
import textInfos
from keyboardHandler import KeyboardInputGesture
import addonHandler
addonHandler.initTranslation()
import treeInterceptorHandler
import unicodedata
from .common import *
from . import huc

charToDotsInLouis = hasattr(louis, "charToDots")

# -----------------------------------------------------------------------------
# Thanks to Tim Roberts for the (next) Control Volume code!
# -> https://mail.python.org/pipermail/python-win32/2014-March/013080.html
from comtypes import *
import comtypes.client
from ctypes import POINTER
from ctypes.wintypes import DWORD, BOOL

MMDeviceApiLib = \
	GUID('{2FDAAFA3-7523-4F66-9957-9D5E7FE698F6}')
IID_IMMDevice = \
	GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
IID_IMMDeviceEnumerator = \
	GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
CLSID_MMDeviceEnumerator = \
	GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
IID_IMMDeviceCollection = \
	GUID('{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}')
IID_IAudioEndpointVolume = \
	GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')


class IMMDeviceCollection(IUnknown):
	_iid_ = GUID('{0BD7A1BE-7A1A-44DB-8397-CC5392387B5E}')


class IAudioEndpointVolume(IUnknown):
	_iid_ = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')
	_methods_ = [
		STDMETHOD(HRESULT, 'RegisterControlChangeNotify', []),
		STDMETHOD(HRESULT, 'UnregisterControlChangeNotify', []),
		STDMETHOD(HRESULT, 'GetChannelCount', []),
		COMMETHOD([], HRESULT, 'SetMasterVolumeLevel',
				  (['in'], c_float, 'fLevelDB'),
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'SetMasterVolumeLevelScalar',
				  (['in'], c_float, 'fLevelDB'),
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'GetMasterVolumeLevel',
				  (['out', 'retval'], POINTER(c_float), 'pfLevelDB')
				  ),
		COMMETHOD([], HRESULT, 'GetMasterVolumeLevelScalar',
				  (['out', 'retval'], POINTER(c_float), 'pfLevelDB')
				  ),
		COMMETHOD([], HRESULT, 'SetChannelVolumeLevel',
				  (['in'], DWORD, 'nChannel'),
				  (['in'], c_float, 'fLevelDB'),
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'SetChannelVolumeLevelScalar',
				  (['in'], DWORD, 'nChannel'),
				  (['in'], c_float, 'fLevelDB'),
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'GetChannelVolumeLevel',
				  (['in'], DWORD, 'nChannel'),
				  (['out', 'retval'], POINTER(c_float), 'pfLevelDB')
				  ),
		COMMETHOD([], HRESULT, 'GetChannelVolumeLevelScalar',
				  (['in'], DWORD, 'nChannel'),
				  (['out', 'retval'], POINTER(c_float), 'pfLevelDB')
				  ),
		COMMETHOD([], HRESULT, 'SetMute',
				  (['in'], BOOL, 'bMute'),
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'GetMute',
				  (['out', 'retval'], POINTER(BOOL), 'pbMute')
				  ),
		COMMETHOD([], HRESULT, 'GetVolumeStepInfo',
				  (['out', 'retval'], POINTER(c_float), 'pnStep'),
				  (['out', 'retval'], POINTER(c_float), 'pnStepCount'),
				  ),
		COMMETHOD([], HRESULT, 'VolumeStepUp',
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'VolumeStepDown',
				  (['in'], POINTER(GUID), 'pguidEventContext')
				  ),
		COMMETHOD([], HRESULT, 'QueryHardwareSupport',
				  (['out', 'retval'], POINTER(DWORD), 'pdwHardwareSupportMask')
				  ),
		COMMETHOD([], HRESULT, 'GetVolumeRange',
				  (['out', 'retval'], POINTER(c_float), 'pfMin'),
				  (['out', 'retval'], POINTER(c_float), 'pfMax'),
				  (['out', 'retval'], POINTER(c_float), 'pfIncr')
				  ),

	]


class IMMDevice(IUnknown):
	_iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
	_methods_ = [
		COMMETHOD([], HRESULT, 'Activate',
				  (['in'], POINTER(GUID), 'iid'),
				  (['in'], DWORD, 'dwClsCtx'),
				  (['in'], POINTER(DWORD), 'pActivationParans'),
				  (['out', 'retval'], POINTER(POINTER(IAudioEndpointVolume)), 'ppInterface')
				  ),
		STDMETHOD(HRESULT, 'OpenPropertyStore', []),
		STDMETHOD(HRESULT, 'GetId', []),
		STDMETHOD(HRESULT, 'GetState', [])
	]


class IMMDeviceEnumerator(comtypes.IUnknown):
	_iid_ = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')

	_methods_ = [
		COMMETHOD([], HRESULT, 'EnumAudioEndpoints',
				  (['in'], DWORD, 'dataFlow'),
				  (['in'], DWORD, 'dwStateMask'),
				  (['out', 'retval'], POINTER(POINTER(IMMDeviceCollection)), 'ppDevices')
				  ),
		COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
				  (['in'], DWORD, 'dataFlow'),
				  (['in'], DWORD, 'role'),
				  (['out', 'retval'], POINTER(POINTER(IMMDevice)), 'ppDevices')
				  )
	]


enumerator = comtypes.CoCreateInstance(
	CLSID_MMDeviceEnumerator,
	IMMDeviceEnumerator,
	comtypes.CLSCTX_INPROC_SERVER
)
# -----------------------------------------------------------------------------


def getMute():
	endpoint = enumerator.GetDefaultAudioEndpoint(0, 1)
	volume = endpoint.Activate(IID_IAudioEndpointVolume, comtypes.CLSCTX_INPROC_SERVER, None)
	return volume.GetMute()


def getVolume():
	endpoint = enumerator.GetDefaultAudioEndpoint(0, 1)
	volume = endpoint.Activate(IID_IAudioEndpointVolume, comtypes.CLSCTX_INPROC_SERVER, None)
	return int(round(volume.GetMasterVolumeLevelScalar() * 100))


def bkToChar(dots, inTable=-1):
	if inTable == -1: inTable = config.conf["braille"]["inputTable"]
	char = chr(dots | 0x8000)
	text = louis.backTranslate(
		[osp.join(r"louis\tables", inTable),
		 "braille-patterns.cti"],
		char, mode=louis.dotsIO)
	chars = text[0]
	if len(chars) == 1 and chars.isupper():
		chars = 'shift+' + chars.lower()
	return chars if chars != ' ' else 'space'


def reload_brailledisplay(bd_name):
	try:
		if braille.handler.setDisplayByName(bd_name):
			speech.speakMessage(_("Reload successful"))
			return True
	except (RuntimeError): pass
	ui.message(_("Reload failed"))
	return False

def currentCharDesc():
	ch = getCurrentChar()
	if not ch: return ui.message(_("Not a character"))
	c = ord(ch)
	if c:
		try: descChar = unicodedata.name(ch)
		except ValueError: descChar = _("unknown")
		HUCrepr = " (%s, %s)" % (huc.translate(ch, False), huc.translate(ch, True))
		s = '%c%s: %s; %s; %s; %s; %s [%s]' % (ch, HUCrepr, hex(c), c, oct(c), bin(c), descChar, unicodedata.category(ch))
		if scriptHandler.getLastScriptRepeatCount() == 0: ui.message(s)
		elif scriptHandler.getLastScriptRepeatCount() == 1:
			brch = getTextInBraille(ch)
			ui.browseableMessage("%s\n%s (%s)" % (s, brch, huc.unicodeBrailleToDescription(brch)), r'\x%d (%s) - Char info' % (c, ch))
	else: ui.message(_("Not a character"))

def getCurrentChar():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
		obj = treeInterceptor
	try:
		info = obj.makeTextInfo(textInfos.POSITION_CARET)
		info.expand(textInfos.UNIT_CHARACTER)
		s = info.text
		return s
	except (TypeError, NotImplementedError): pass
	return ''

def getTextSelection():
	obj = api.getFocusObject()
	treeInterceptor=obj.treeInterceptor
	if isinstance(treeInterceptor,treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough:
		obj=treeInterceptor
	try: info=obj.makeTextInfo(textInfos.POSITION_SELECTION)
	except (RuntimeError, NotImplementedError): info=None
	if not info or info.isCollapsed:
		obj = api.getNavigatorObject()
		text = obj.name
		return "%s" % text if text else ''
	else: return info.text

def getKeysTranslation(n):
	o = n
	n = n.lower()
	nk = 'NVDA+' if 'nvda+' in n else ''
	if not 'br(' in n:
		n = n.replace('kb:', '').replace('nvda+', '')
		try:
			n = KeyboardInputGesture.fromName(n).displayName
			n = re.sub('([^a-zA-Z]|^)f([0-9])', r'\1F\2', n)
		except BaseException:
			return o
		return nk + n

def getTextInBraille(t=None, table=[]):
	if not isinstance(table, list): raise TypeError("Wrong type for table parameter: %s" % repr(table))
	if not t: t = getTextSelection()
	if not t.strip(): return ''
	if not table or "current" in table:
		currentTable = os.path.join(brailleTables.TABLES_DIR, config.conf["braille"]["translationTable"])
		if "current" in table: table[table.index("current")] = currentTable
		else: table.append(currentTable)
	nt = []
	res = ''
	t = t.split("\n")
	for l in t:
		l = l.rstrip()
		if not l: res = ''
		else: res = ''.join([chr(ord(ch)-0x8000+0x2800) for ch in louis.translateString(table, l, mode=louis.dotsIO)])
		nt.append(res)
	return '\n'.join(nt)

def combinationDesign(dots, noDot = '⠤'):
	out = ""
	i = 1
	while i < 9:
		out += str(i) if str(i) in dots else noDot
		i += 1
	return out

def getTableOverview(tbl = ''):
	"""
	Return an overview of a input braille table.
	:param tbl: the braille table to use (default: the current input braille table).
	:type tbl: str
	:return: an overview of braille table in the form of a textual table
	:rtype: str
	"""
	t = ""
	tmp = {}
	available = ""
	i = 0x2800
	while i<0x2800+256:
		text = louis.backTranslate([osp.join(r"louis\tables", config.conf["braille"]["inputTable"]), "braille-patterns.cti"], chr(i), mode=louis.ucBrl)
		if i != 0x2800:
			t = 'Input              Output\n'
		if not re.match(r'^\\.+/$', text[0]):
			tmp['%s' % text[0] if text[0] != '' else '?'] = '%s       %-7s' % (
			'%s (%s)' % (chr(i), combinationDesign(huc.unicodeBrailleToDescription(chr(i)))),
			'%s%-8s' % (text[0].rstrip('\x00'), '%s' % (' (%-10s)' % str(hex(ord(text[0]))) if len(text[0]) == 1 else '' if text[0] != '' else '#ERROR'))
			)
		else:
			available += chr(i)
		i += 1
	t += '\n'.join(tmp[k] for k in sorted(tmp))
	nbAvailable = len(available)
	if nbAvailable>1:
		t += '\n'+_("Available combinations")+" (%d): %s" % (nbAvailable, available)
	elif nbAvailable == 1:
		t += '\n'+_("One combination available")+": %s" % available
	return t

def beautifulSht(t, curBD="noBraille", model=True, sep=" / "):
	if isinstance(t, list): t = ' '.join(t)
	t = t.replace(',', ' ')
	t = t.replace(';',' ')
	t = t.replace('  ',' ')
	reps = {
		"b10": "b0",
		"braillespacebar": "space",
		"space": _('space'),
		"leftshiftkey": _("left SHIFT"),
		"rightshiftkey": _("right SHIFT"),
		"leftgdfbutton": _("left selector"),
		"rightgdfbutton": _("right selector"),
		"dot": _("dot")
	}
	mdl = ''
	pattern = r"^.+\.([^)]+)\).+$"
	t = t.replace(';', ',')
	out = []
	for gesture in t.split(' '):
		if not gesture.strip(): continue
		mdl = ''
		if re.match(pattern, gesture): mdl = re.sub(pattern, r'\1', gesture)
		gesture = re.sub(r'.+:', '', gesture)
		gesture = '+'.join(sorted(gesture.split('+')))
		for rep in reps:
			gesture = re.sub("(\+|^)%s([0-9]\+|$)" % rep, r"\1%s\2" % reps[rep], gesture)
			gesture = re.sub("(\+|^)%s([0-9]\+|$)" % rep, r"\1%s\2" % reps[rep], gesture)
		out.append(_('{gesture} on {brailleDisplay}').format(gesture=gesture, brailleDisplay=mdl) if mdl != '' else gesture)
	return out if not sep else sep.join(out)

def getText():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(
			treeInterceptor,
			'TextInfo') and not treeInterceptor.passThrough:
		obj = treeInterceptor
	try:
		info = obj.makeTextInfo(textInfos.POSITION_ALL)
		return info.text
	except BaseException:
		pass
	return None


def getTextCarret():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough: obj = treeInterceptor
	try:
		p1 = obj.makeTextInfo(textInfos.POSITION_ALL)
		p2 = obj.makeTextInfo(textInfos.POSITION_CARET)
		p1.setEndPoint(p2, "endToStart")
		try: return p1.text
		except BaseException: return None
	except BaseException: pass
	return None


def getLine():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough: obj = treeInterceptor
	try:
		info = obj.makeTextInfo(textInfos.POSITION_CARET)
		info.expand(textInfos.UNIT_LINE)
		s = info.text
		return s
	except BaseException: pass
	return None

def isLastLine():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
		obj = treeInterceptor
	try:
		p1 = obj.makeTextInfo(textInfos.POSITION_CARET)
		p1.expand(textInfos.UNIT_LINE)
		p2 = obj.makeTextInfo(textInfos.POSITION_LAST)
		if p1.compareEndPoints(p2, "endToEnd") == 1: return True
	except BaseException: return True
	return False

def isEnd():
	obj = api.getFocusObject()
	treeInterceptor = obj.treeInterceptor
	if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
		obj = treeInterceptor
	try:
		p1 = obj.makeTextInfo(textInfos.POSITION_CARET)
		p2 = obj.makeTextInfo(textInfos.POSITION_LAST)
		if p1.compareEndPoints(p2, "startToEnd") == 0: return True
	except BaseException: pass
	return False

def getPositionPercentage():
	try:
		total = len(getText())
		if total != 0:
			return float(len(getTextCarret())) / float(total) * 100
		else:
			return 100
	except BaseException:
		ui.message(_('No text'))
	return 100


def getPosition():
	try:
		total = len(getText())
		return (len(getTextCarret()), total)
	except BaseException:
		ui.message(_('Not text'))


def uncapitalize(s): return s[:1].lower() + s[1:] if s else ''


translatePercent = lambda p, q = braille.handler.displaySize - 4: u'⣦%s⣴' % ''.join(
	[u'⢼' if k <= int(float(p) / 100. * float(q - 2)) - 1 else u'⠤' for k in range(q - 2)])

def refreshBD():
	obj = api.getFocusObject()
	if obj.treeInterceptor is not None:
		ti = treeInterceptorHandler.update(obj)
		if not ti.passThrough:
			braille.handler.handleGainFocus(ti)
	else:
		braille.handler.handleGainFocus(api.getFocusObject())

def getSpeechSymbols(text = None):
	if not text: text = getTextSelection()
	if not text: return ui.message(_("No text selected"))
	locale = languageHandler.getLanguage()
	return characterProcessing.processSpeechSymbols(locale, text, characterProcessing.SYMLVL_CHAR).strip()

def getTether():
	if hasattr(braille.handler, "getTether"):
		return braille.handler.getTether()
	else: return braille.handler.tether


def getCharFromValue(s):
	if not isinstance(s, str if isPy3 else (str, unicode)): raise TypeError("Wrong type")
	if not s or len(s) < 2: raise ValueError("Wrong value")
	supportedBases = {'b': 2, 'd': 10, 'h': 16, 'o': 8, 'x': 16}
	base, n = s[0].lower(), s[1:]
	if base not in supportedBases.keys(): raise ValueError("Wrong base (%s)" % base)
	b = supportedBases[base]
	n = int(n, b)
	return chr(n)

def getExtendedSymbols(locale):
	if locale == "Windows": locale = languageHandler.getLanguage()
	try:
		b, u = characterProcessing._getSpeechSymbolsForLocale(locale)
	except LookupError:
		b, u = characterProcessing._getSpeechSymbolsForLocale(locale.split('_')[0])
	a = {k: v.replacement.replace("  ", " ") for k, v in b.symbols.items() if len(k) > 1}
	a.update({k: v.replacement.replace("  ", " ") for k, v in u.symbols.items() if len(k) > 1})
	return a
