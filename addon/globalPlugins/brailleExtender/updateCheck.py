# coding: utf-8
# updateCheck.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.
from __future__ import unicode_literals
from logHandler import log
import json
import os
import sys
isPy3 = True if sys.version_info >= (3, 0) else False
if isPy3:
	import urllib.parse
	import urllib.request
else: import urllib

import gui
import wx

import addonHandler
import braille
import core
import config
import globalVars
import languageHandler
import versionInfo

from . import configBE
addonHandler.initTranslation()

def paramsDL(): return {
	"versionProtocole": "2.0",
	"versionAddon": configBE._addonVersion,
	"versionNVDA": versionInfo.version,
	"language": languageHandler.getLanguage(),
	"brailledisplay": braille.handler.display.name,
	"channel": config.conf["brailleExtender"]["updateChannel"]
}

urlencode = urllib.parse.urlencode if isPy3 else urllib.urlencode
URLopener = urllib.request.URLopener if isPy3 else urllib.URLopener
urlopen = urllib.request.urlopen if isPy3 else urllib.urlopen



def checkUpdates(sil = False):

	def availableUpdateDialog(version = '', msg = ''):
		res = gui.messageBox(
			(_("New version available, version %s. Do you want download it now?") % version.strip()+('\n%s' % msg)).strip(),
			title,
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES: processUpdate()

	def upToDateDialog(msg = ''):
		gui.messageBox(
			(_("You are up-to-date. %s is the latest version.") % configBE._addonVersion+'\n%s' % msg).strip(),
			title,
			wx.OK|wx.ICON_INFORMATION)

	def errorUpdateDialog():
		res = gui.messageBox(
			_("Oops! There was a problem checking for updates. Please retry later or download and install manually via %s. Do you want open this URL in your browser now?") % configBE._addonURL,
			title,
			wx.YES|wx.NO|wx.ICON_ERROR)
		if res == wx.YES: os.startfile(configBE._addonURL)

	def processUpdate():
		url = configBE._addonURL + "latest?" + urlencode(paramsDL())
		fp = os.path.join(globalVars.appArgs.configPath, "brailleExtender.nvda-addon")
		try:
			dl = URLopener()
			dl.retrieve(url, fp)
			try:
				curAddons = []
				for addon in addonHandler.getAvailableAddons(): curAddons.append(addon)
				bundle = addonHandler.AddonBundle(fp)
				prevAddon = None
				bundleName = bundle.manifest['name']
				for addon in curAddons:
					if not addon.isPendingRemove and bundleName == addon.manifest['name']:
						prevAddon = addon
						break
				if prevAddon: prevAddon.requestRemove()
				addonHandler.installAddonBundle(bundle)
				core.restart()
			except BaseException as e:
				log.error(e)
				os.startfile(fp)
		except BaseException as e:
			log.error(e)
			ui.message(_("Unable to save or download update file. Opening your browser"))
			os.startfile(url)
		return

	title = _("BrailleExtender's Update")
	newUpdate = False
	url = '{0}BrailleExtender.latest?{1}'.format(configBE._addonURL, urlencode(paramsDL()))
	try:
		page = urlopen(url)
		if page.code == 200:
			data = json.load(page)
			if not data["success"]: raise ValueError("Invalid JSON response")
			if not data["upToDate"]: newUpdate = True
			if not newUpdate and sil:
				return log.debug('No update')
			if newUpdate: wx.CallAfter(availableUpdateDialog, data["lastVersion"], data["msg"])
			else: wx.CallAfter(upToDateDialog, data["msg"])
		else: raise ValueError("Invalid server code response: %s" % page.code)
	except BaseException as err:
		log.warning(err)
		if not newUpdate and sil: return
		wx.CallAfter(errorUpdateDialog)
