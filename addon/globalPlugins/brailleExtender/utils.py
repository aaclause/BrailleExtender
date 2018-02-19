# coding: utf-8
# utils.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os.path as osp
import re
import api
import braille
import brailleTables
import louis
import config
import ui
import scriptHandler
import speech
import textInfos
from keyboardHandler import KeyboardInputGesture
import addonHandler
addonHandler.initTranslation()
import treeInterceptorHandler

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
	char = unichr(dots | 0x8000)
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
			speech.speakMessage(_("%s device reloaded") % bd_name.capitalize())
			return True
		else: ui.message(_("No %s display found") % bd_name.capitalize())
	except BaseException: ui.message(_("No %s display found") % bd_name.capitalize())
	return False

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
	except BaseException:
		pass
	return ''

def currentCharDesc():
	ch = getCurrentChar()
	c = ord(ch)
	if c != '':
		s = '%c: %s; %s; %s; %s'% (ch, hex(c), c, oct(c), bin(c))
		if scriptHandler.getLastScriptRepeatCount() == 0: ui.message(s)
		elif (scriptHandler.getLastScriptRepeatCount() == 1):
			brch = getTextInBraille(ch)
			ui.browseableMessage('%s\n%s (%s)' % (s, brch, unicodeBrailleToDescription(brch)), r'\x%d - Char info' % c)
		else:
			api.copyToClip(s)
			ui.message('"{0}" copied to clipboard.'.format(s))
	else: ui.message(_('Not a character.'))

def getTextSelection():
	obj = api.getFocusObject()
	treeInterceptor=obj.treeInterceptor
	if isinstance(treeInterceptor,treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough:
		obj=treeInterceptor
	try: info=obj.makeTextInfo(textInfos.POSITION_SELECTION)
	except (RuntimeError, NotImplementedError): info=None
	if not info or info.isCollapsed: return ''
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
def getTextInBraille(t = ''):
	
	if t == '':
		t = getTextSelection()
		t = t.replace('\r','')
	if t.strip() != '':
		t = t.split('\n')
		for i, l in enumerate(t):
			t[i] = louis.translateString([os.path.join(brailleTables.TABLES_DIR, config.conf["braille"]["translationTable"])], l, None, louis.dotsIO)
		t = '\n'.join(t)
		nt = ""
		for i, ch in enumerate(t):
			if ch == '\r': continue
			if ch != '\n': nt += unichr(ord(ch)-0x8000+0x2800)
			else: nt += '\n'
		return nt
	else: return ''

def getDescriptionBrailleCell(ch):
	"""
	Return a description of an unicode braille char
	:param ch: the unicode braille character to describe
		must be between 0x2800 and 0x2999 included
	:type ch: str
	:return: the list of dots describing the braille cell
	:rtype: str
	
	:Example: "d" -> "145"
	"""
	res = ""
	if len(ch) != 1: raise ValueError("Param size can only be one char (currently: %d)" % len(ch))
	p = ord(ch)
	if p >= 0x2800 and p <= 0x2999: p -= 0x2800
	if p > 255: raise ValueError(r"It is not an unicode braille (%d)" % p)
	dots ={1:1, 2:2, 4:3, 8:4,16:5,32:6,64:7, 128:8}
	i = 1
	while p != 0:
		if p - (128 / i) >= 0:
			res += str(dots[(128/i)])
			p -= (128 / i)
		i *= 2
	return res[::-1] if len(res) > 0 else '0'

def getTableOverview(tbl = ''):
	"""
	Return an overview of a input braille table.
	:param tbl: the braille table to use (default: the current input braille table).
	:type tbl: str
	:return: an overview of braille table in the form of a textual table
	:rtype: str
	"""
	t = ""
	available = ""
	i = 0x2800
	j = 1
	while i<0x2800+256:
		text = louis.backTranslate([osp.join(r"louis\tables", config.conf["braille"]["inputTable"]), "braille-patterns.cti"], unichr(i), mode=louis.ucBrl)
		if not re.match(r'^\\.+/$', text[0]):
			t += '%s%.3d  %4s  %8s        %s' % (('\n' if i != 0x2800 else ' No  Char      Dots  Braille\n'), j, text[0], unicodeBrailleToDescription(unichr(i)), unichr(i))
			j += 1
		else:
			available += unichr(i)
		i += 1
	nbAvailable = len(available)
	if nbAvailable>1:
		t += '\n'+_("Available combinations")+" (%d): %s" % (nbAvailable, available)
	elif nbAvailable == 1:
		t += '\n'+_("One combination available")+": %s" % available
	return t

def unicodeBrailleToDescription(t, sep = '-'):
	nt = ""
	for i, ch in enumerate(t):
		if ch == '\n':
			nt += '\n'
			continue
		nt += '%s%s' %(sep if i != 0 else '', getDescriptionBrailleCell(ch))
	nt = nt.replace('\n'+sep, '\n')
	return nt

def beautifulSht(t, r=0, curBD=config.conf["braille"]["display"]):
	t = re.sub('^[^:,/ ]+:', '', t)
	if r:
		t = re.sub(r'([^ ;,;|/]+)', lambda m: beautifulSht(m.group(1)), t)
	t = t.replace('br(' + curBD + '):', '').replace('b10', 'b0')
	if not r:
		t = '+'.join(sorted(t.split('+')))
	l = ['B', 'C', 'D', 'Dot']
	for r in l:
		t = re.sub(
			'([^a-zA-Z]|^)' +
			r.lower() +
			'([^a-zA-Z]|$)',
			lambda m: m.group(1) +
			r +
			m.group(2),
			t)
		t = re.sub(
			'(' + r + '[0-9](?:\+|$)){2,}',
			lambda m: '{0}_({1})'.format(
				r,
				m.group(0).replace(
					r,
					'')),
			t)
		t = t.replace('+)', ')+')
		t = t.replace('braillespacebar', 'space')
		t = re.sub('([^A-Za-z]|^)space', r'\1' + _('space'), t)
		t = t.replace('leftshiftkey', _('left SHIFT'))
		t = t.replace('rightshiftkey', _('right SHIFT'))
		t = t.replace('leftgdfbutton', _('left selector'))
		t = t.replace('rightgdfbutton', _('right selector'))
		t = t.replace('Dot', _('Dot'))
	return t


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
