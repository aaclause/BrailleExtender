# coding: utf-8
# common.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import os

import addonHandler
import globalVars
import languageHandler

configDir = "%s/brailleExtender" % globalVars.appArgs.configPath
baseDir = os.path.dirname(__file__)
addonDir = os.path.join(baseDir, "..", "..")
addonName = addonHandler.Addon(addonDir).manifest["name"]
addonSummary = addonHandler.Addon(addonDir).manifest["summary"]
addonVersion = addonHandler.Addon(addonDir).manifest["version"]
addonURL = addonHandler.Addon(addonDir).manifest["url"]
addonGitHubURL = "https://github.com/aaclause/BrailleExtender/"
addonAuthor = addonHandler.Addon(addonDir).manifest["author"]
addonDesc = addonHandler.Addon(addonDir).manifest["description"]
addonUpdateChannel = addonHandler.Addon(addonDir).manifest["updateChannel"]

lang = languageHandler.getLanguage().split('_')[-1].lower()
punctuationSeparator = ' ' if 'fr' in lang else ''


profilesDir = os.path.join(baseDir, "Profiles")

REPLACE_TEXT = 0
INSERT_AFTER = 1
INSERT_BEFORE = 2

# auto scroll
DEFAULT_AUTO_SCROLL_DELAY = 3000
MIN_AUTO_SCROLL_DELAY = 200
MAX_AUTO_SCROLL_DELAY = 42000
DEFAULT_STEP_DELAY_CHANGE = 100
MIN_STEP_DELAY_CHANGE = 25
MAX_STEP_DELAY_CHANGE = 7000

# Routing cursors behavior in edit fields
RC_NORMAL = "normal"
RC_EMULATE_ARROWS_BEEP = "arrows_beeps"
RC_EMULATE_ARROWS_SILENT = "arrows_silent"
