# common.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import os

import addonHandler
import controlTypes
import globalVars
import languageHandler

def get_is_current_no():
	if hasattr(controlTypes, "IsCurrent"):
		return controlTypes.IsCurrent.NO
	return False

IS_CURRENT_NO = get_is_current_no()

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

N_ = lambda s: _(s)

CHOICE_none = "none"

# text attributes
CHOICE_liblouis = "liblouis"
CHOICE_dot7 = "dot7"
CHOICE_dot8 = "dot8"
CHOICE_dots78 = "dots78"
CHOICE_tags = "tags"
CHOICE_spacing = "spacing"
TAG_SEPARATOR = chr(5)
CHOICE_likeSpeech = '0'
CHOICE_enabled = '1'
CHOICE_disabled = '2'

REPLACE_TEXT = 0
INSERT_AFTER = 1
INSERT_BEFORE = 2

ADDON_ORDER_PROPERTIES = "states,cellCoordsText,value,name,roleText,description,keyboardShortcut,positionInfo,positionInfoLevel,current,placeholder"

ROLE_LABEL = 0
FORMATTING_LABEL = 1

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

# speech history mode
SHM_ACTION_COPY_CLIPBOARD = "copyToClip"
SHM_ACTION_QUICK_NAV = "quickNav"
