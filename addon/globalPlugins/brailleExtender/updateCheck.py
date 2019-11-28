# coding: utf-8
# updateCheck.py
# Part of BrailleExtender addon for NVDA
# Copyright 2019 André-Abush Clause, released under GPL.
from __future__ import unicode_literals
from logHandler import log
import json
import os
import sys
import time
import threading
import tones
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
import ui
import versionInfo

addonHandler.initTranslation()

baseDir = os.path.dirname(__file__)
if not isPy3: baseDir = baseDir.decode("mbcs")
_addonDir = os.path.join(baseDir, "..", "..")
addonInfos = addonHandler.Addon(_addonDir).manifest
sectionName = "brailleExtender"
checkInProgress = False

def paramsDL(): return {
	"protocoleVersion": "3",
	"addonVersion": addonInfos["version"],
	"NVDAVersion": versionInfo.version,
	"channel": config.conf[sectionName]["updateChannel"],
	"language": languageHandler.getLanguage(),
	"brailledisplay": braille.handler.display.name,
}

urlencode = urllib.parse.urlencode if isPy3 else urllib.urlencode
URLopener = urllib.request.URLopener if isPy3 else urllib.URLopener
urlopen = urllib.request.urlopen if isPy3 else urllib.urlopen

def checkUpdates(sil = False):

	global checkInProgress

	def availableUpdateDialog(version = '', msg = ''):
		global checkInProgress
		checkInProgress = True
		res = gui.messageBox(
			(_("New version available, version %s. Do you want to download it now?") % version.strip()+('\n%s' % msg)).strip(),
			title,
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES:
			processUpdate()
		checkInProgress = False

	def upToDateDialog(msg = ''):
		global checkInProgress
		checkInProgress = True
		res = gui.messageBox(
			(_("You are up-to-date. %s is the latest version.") % addonInfos["version"]+'\n%s' % msg).strip(),
			title,
			wx.OK|wx.ICON_INFORMATION)
		if res: checkInProgress = False

	def errorUpdateDialog():
		global checkInProgress
		checkInProgress = True
		res = gui.messageBox(
			_("Oops! There was a problem downloading for update. Please retry later or download and install manually via %s. Do you want to open this URL in your browser now?") % addonInfos["url"],
			title,
			wx.YES|wx.NO|wx.ICON_ERROR)
		if res == wx.YES: os.startfile(addonInfos["url"])
		checkInProgress = False

	def processUpdate():
		url = addonInfos["url"];
		if url.endswith('/'): url = url[0:-1]
		url = "%s.nvda-addon?%s" % (url, urlencode(paramsDL()))
		fp = os.path.join(globalVars.appArgs.configPath, "%s.nvda-addon" % sectionName)
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
			return wx.CallAfter(errorUpdateDialog)

	if checkInProgress: return ui.message(_("An update check dialog is already running!"))
	title = _("{addonName}'s update").format(addonName=addonInfos["name"])
	newUpdate = False
	url = addonInfos["url"];
	if url.endswith('/'): url = url[0:-1]
	url = "%s.json?%s" % (url, urlencode(paramsDL()))
	try:
		page = urlopen(url)
		if page.code == 200:
			data = json.load(page)
			if not data["success"]: raise ValueError("Invalid JSON response")
			if not data["upToDate"]: newUpdate = True
			if not newUpdate and sil:
				return log.debug("No update")
			if newUpdate: wx.CallAfter(availableUpdateDialog, data["lastVersions"][config.conf[sectionName]["updateChannel"]], data["msg"])
			else: wx.CallAfter(upToDateDialog, data["msg"])
		else: raise ValueError("Invalid server code response: %s" % page.code)
	except BaseException as err:
		log.warning(err)
		if not newUpdate and sil: return
		wx.CallAfter(errorUpdateDialog)


class UpdateCheck(threading.Thread):

	shouldStop = False

	def run(self):
		if globalVars.appArgs.secure: return self.stop()
		checkingForced = False
		delayChecking = 86400 if config.conf[sectionName]["updateChannel"] != "stable" else 604800
		while not self.shouldStop:
			if not checkInProgress and config.conf[sectionName]["autoCheckUpdate"]:
				if config.conf[sectionName]["lastNVDAVersion"] != versionInfo.version:
					config.conf[sectionName]["lastNVDAVersion"] = versionInfo.version
					checkingForced = True
				if checkingForced or (time.time() - config.conf[sectionName]["lastCheckUpdate"]) > delayChecking:
					log.info("Checking update... Forced: %s" % ("yes" if checkingForced else "no"))
					checkUpdates(True)
					config.conf[sectionName]["lastCheckUpdate"] = time.time()
				checkingForced = False
			time.sleep(0.2)

	def stop(self):
		self.shouldStop = True
