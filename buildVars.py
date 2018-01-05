# -*- coding: UTF-8 -*-
import time
# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

# Full getext (please don't change)
_ = lambda x : x

# Add-on information variables
addon_info = {
	# for previously unpublished addons, please follow the community guidelines at:
	# https://bitbucket.org/nvdaaddonteam/todo/raw/master/guideLines.txt
	# add-on Name, internal for nvda
	"addon_name" : "BrailleExtender",
	# Add-on summary, usually the user visible name of the addon.
	# Translators: Summary for this add-on to be shown on installation and add-on information.
	"addon_summary" : _("BrailleExtender"),
	# Add-on description
	# Translators: Long description to be shown for this add-on on add-on information from add-ons manager
	"addon_description" : [
	_("BrailleExtender is a NVDA add-on that provides various features at braille level. Currently, the following features are implemented"), ":",
	"\n* ", _("reload two favorite braille display with shortcuts"), ";",
	"\n* ", _("Automatic review cursor tethering for selected apps (default: PuTTY, Powershell, bash, cmd)"), ";",
	"\n* ", _("auto scroll"), ";",
	"\n* ", _("switch between several input/output braille tables"), ";",
	"\n* ", _("define custom rules to mark text with special fields option with braille dots 7 and 8"), ";",
	"\n* ", _("use two output braille tables simultaneously"), ";",
	"\n* ", _("display tab signs as spaces"), ";",
	"\n* ", _("reverse forward scroll and back scroll buttons"), ";",
	"\n* ", _("say the current line during text scrolling, in review mode"), ".",
	"\n\n",_("For some braille displays, it extends the braille display commands to provide"), ":",
	"\n* ", _("access to function keys, multimedia keys, quick navigation"), ";",
	"\n* ", _("emulate modifier keys, and thus any keyboard shortcut"), ";",
	"\n* ", _("offer several keyboard configurations concerning the possibility to input dots 7 and 8, enter and backspace"), ";",
	"\n* ", _("launch an application quickly"), ";",
	"\n* ", _("actions and quick navigation through a rotor"), "."
],
	# version
	"addon_version" : time.strftime('dev-%y.%m.%d-%H%M%S'),
	# Author(s)
	"addon_author" : u"André-Abush Clause <dev@andreabc.net>",
	# URL for the add-on documentation support
	"addon_url" : "https://andreabc.net/projects/NVDA_addons/BrailleExtender/",
	# Documentation file name
	"addon_docFileName" : None,
}

import os.path

# Define the python files that are the ²s of your add-on.
# You can use glob expressions here, they will be expanded.
pythonSources = [os.path.join("addon", "*.py"),
os.path.join("addon", "globalPlugins", "brailleExtender", "*.py")]

# Files that contain strings for translation. Usually your python sources
i18nSources = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
excludedFiles = []
