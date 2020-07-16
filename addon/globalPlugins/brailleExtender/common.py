# coding: utf-8
# common.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import os
import struct

import addonHandler
import globalVars
import languageHandler
from logHandler import log

configDir = "%s/brailleExtender" % globalVars.appArgs.configPath
baseDir = os.path.dirname(__file__)
addonDir = os.path.join(baseDir, "..", "..")
addonName = addonHandler.Addon(addonDir).manifest["name"]
addonSummary = addonHandler.Addon(addonDir).manifest["summary"]
addonVersion = addonHandler.Addon(addonDir).manifest["version"]
addonURL = addonHandler.Addon(addonDir).manifest["url"]
addonGitHubURL = "https://github.com/Andre9642/BrailleExtender/"
addonAuthor = addonHandler.Addon(addonDir).manifest["author"]
addonDesc = addonHandler.Addon(addonDir).manifest["description"]
addonUpdateChannel = addonHandler.Addon(addonDir).manifest["updateChannel"]

lang = languageHandler.getLanguage().split('_')[-1].lower()
punctuationSeparator = ' ' if 'fr' in lang else ''


profilesDir = os.path.join(baseDir, "Profiles")
N_ = lambda s: _(s)
