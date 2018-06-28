# coding: utf-8
# updateCheck.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.
from __future__ import unicode_literals
from logHandler import log

import os
import re
import urllib
import gui
import wx

import addonHandler
import braille
import config
import globalVars
import languageHandler
import versionInfo

import configBE
addonHandler.initTranslation()

def paramsDL(): return {
	"versionProtocole": "1.4",
	"versionAddon": configBE._addonVersion,
	"versionNVDA": versionInfo.version,
	"language": languageHandler.getLanguage(),
	"installed": config.isInstalledCopy(),
	"brailledisplay": braille.handler.display.name,
	"channel": config.conf["brailleExtender"]['channelUpdate']
}


def checkUpdates(sil = False):

	def availableUpdateDialog(version = '', msg = ''):
		res = gui.messageBox(
			(_("New version available, version %s. Do you want download it now?") % version.strip()+('\n%s' % msg)).strip(),
			title,
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES: processUpdate()

	def unavailableUpdateDialog(msg = ''):
		gui.messageBox(
			(_("You are up-to-date. %s is the latest version.") % configBE._addonVersion+'\n%s' % msg).strip(),
			title,
			wx.OK|wx.ICON_INFORMATION)

	def errorUpdateDialog():
		gui.messageBox(
			_("Oops! There was a problem checking for updates. Please retry later or go to manually at")+'\n%s' % configBE._addonURL,
			title,
			wx.OK|wx.ICON_ERROR)

	def processUpdate():
		url = configBE._addonURL + "latest?" + urllib.urlencode(paramsDL())
		fp = os.path.join(globalVars.appArgs.configPath, "brailleExtender.nvda-addon")
		try:
			dl = urllib.URLopener()
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
	url = '{0}BrailleExtender.latest?{1}'.format(configBE._addonURL, urllib.urlencode(paramsDL()))
	msg = ""
	version = ""
	try:
		page = urllib.urlopen(url)
		pageContent = page.read().strip()
		if (page.code == 200 and len(pageContent) < 700):
			version = re.sub('\n(.+)$', '\1', pageContent).strip().replace('\r','').replace('','')
			msg = re.findall(r'msg: ?(.+)$', pageContent)
			msg = msg[0].strip() if len(msg) == 1 else ''
			if version != configBE._addonVersion: newUpdate = True
		if not newUpdate and sil:
			log.debug('No update')
			return
		if newUpdate: wx.CallAfter(availableUpdateDialog, version, msg)
		else: wx.CallAfter(unavailableUpdateDialog, msg)
	except BaseException, e:
		log.debug(e)
		if not newUpdate and sil: return
		wx.CallAfter(errorUpdateDialog)
