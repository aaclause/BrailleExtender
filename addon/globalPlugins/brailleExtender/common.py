# coding: utf-8
# common.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import os
import sys
import struct

import addonHandler
import globalVars
import languageHandler
from logHandler import log

isPy3 = sys.version_info >= (3, 0)
configDir = "%s/brailleExtender" % globalVars.appArgs.configPath
baseDir = os.path.dirname(__file__)
if not isPy3: baseDir = baseDir.decode("mbcs")
addonDir = os.path.join(baseDir, "..", "..")
addonName = addonHandler.Addon(addonDir).manifest["name"]
addonSummary = addonHandler.Addon(addonDir).manifest["summary"]
addonVersion = addonHandler.Addon(addonDir).manifest["version"]
addonURL = addonHandler.Addon(addonDir).manifest["url"]
addonGitHubURL = "https://github.com/Andre9642/BrailleExtender/"
addonAuthor = addonHandler.Addon(addonDir).manifest["author"]
addonDesc = addonHandler.Addon(addonDir).manifest["description"]
lang = languageHandler.getLanguage().split('_')[-1].lower()
punctuationSeparator = ' ' if 'fr' in lang else ''


profilesDir = os.path.join(baseDir, "Profiles")
if not isPy3:
	def chrPy2(i):
		try: return unichr(i)
		except ValueError: return struct.pack('i', i).decode('utf-32')

	chr = chrPy2

N_ = lambda s: _(s)
