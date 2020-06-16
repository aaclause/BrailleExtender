# -*- coding: UTF-8 -*-
import subprocess
import time

hashCommit = "unknown"
out = subprocess.check_output(["git", "status", "--porcelain"]).strip().decode()
if not out.strip():
	label = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).strip().decode()
	if len(hashCommit) == 7: hashCommit = label
# Build customizations
# Change this file instead of sconstruct or manifest files, whenever possible.

# Full getext (please don't change)
_ = lambda x : x

# Add-on information variables
addon_info = {
	# for previously unpublished addons, please follow the community guidelines at:
	# https://bitbucket.org/nvdaaddonteam/todo/raw/master/guidelines.txt
	# add-on Name, internal for nvda
	"addon_name": "BrailleExtender",
	# Add-on summary, usually the user visible name of the addon.
	# Translators: Summary for this add-on to be shown on installation and add-on information.
	"addon_summary": _("Braille Extender"),
	# Add-on description
	# Translators: Long description to be shown for this add-on on add-on information from add-ons manager
	"addon_description": [
	_("BrailleExtender is a NVDA add-on that provides various features at braille level. Currently, the following features are implemented"), ":",
	"\n* ", _("reload two favorite braille display with shortcuts"), ".",
	"\n* ", _("automatic review cursor tethering in terminal role like in PuTTY, Powershell, bash, cmd"), ".",
	"\n* ", _("auto scroll"), ".",
	"\n* ", _("switch between several input/output braille tables"), ".",
	"\n* ", _("mark the text with special attributes through dot 7, dot 8 or both"), ".",
	"\n* ", _("use two output braille tables simultaneously"), ".",
	"\n* ", _("display tab signs as spaces"), ".",
	"\n* ", _("reverse forward scroll and back scroll buttons"), ".",
	"\n* ", _("say the current line during text scrolling either in review mode, or in focus mode or both"), ".",
	"\n* ", _("translate text easily in Unicode braille and vice versa. E.g.: z <--> ⠵"), ".",
	"\n* ", _("convert cell description to Unicode braille and vice versa. E.g.: 123 <--> ⠇"), ".",
	"\n* ", _("lock braille keyboard"), ".",
	"\n* ", _("launch an application/URL with gesture"), ".",
	"\n* ", _("braille dictionaries"), ".",
	"\n* ", _("type with one-hand from braille keyboard"), ".",
	"\n* ", _("display undefined characters from braille tables (including emojis) using altenative representations"), ".",
	"\n* ", _("enter any character from braille keyboard (including emojis)"), ".",
	"\n* ", _("and much more!"),
	"\n\n",_("For some braille displays, it extends the braille display commands to provide"), ":",
	"\n* ", _("offer complete gesture maps including function keys, multimedia keys, quick navigation, etc."), ";",
	"\n* ", _("emulate modifier keys, and thus any keyboard shortcut"), ";",
	"\n* ", _("offer several keyboard configurations concerning the possibility to input dots 7 and 8, enter and backspace"), ";",
	"\n* ", _("actions and quick navigation through a rotor"), "."
	],
	# version
	"addon_version": time.strftime("%y.%m.%d:") + hashCommit,
	# Author(s)
	"addon_author": "André-Abush Clause <dev@andreabc.net> " + _("and other contributors"),
	# URL for the add-on documentation support
	"addon_url": "https://andreabc.net/projects/NVDA_addons/BrailleExtender/",
	# Documentation file name
	"addon_docFileName": "readme.html",
	# Minimum NVDA version supported (e.g. "2018.3.0", minor version is optional)
	"addon_minimumNVDAVersion": "2019.3",
	# Last NVDA version supported/tested (e.g. "2018.4.0", ideally more recent than minimum version)
	"addon_lastTestedNVDAVersion": "2020.2",
	# Add-on update channel (default is stable or None)
	"addon_updateChannel": None,
}


import os.path

# Define the python files that are the sources of your add-on.
# You can use glob expressions here, they will be expanded.
pythonSources = [os.path.join("addon", "*.py"),
os.path.join("addon", "globalPlugins", "brailleExtender", "*.py")]


# Files that contain strings for translation. Usually your python sources
i18nSources = pythonSources + ["buildVars.py"]

# Files that will be ignored when building the nvda-addon file
# Paths are relative to the addon directory, not to the root directory of your addon sources.
excludedFiles = []
