# coding: utf-8
# objectPresentation.py
import gui
import wx
import addonHandler
import braille
import controlTypes
import config
addonHandler.initTranslation()
from logHandler import log
from .common import *
from .documentFormatting import CHOICES_LABELS

# {name} {value} {statesStr} {roleText} {description} {keyboardShortcut} {positionInfoStr} {positionInfoLevelStr} {rowStr} {columnHeaderText} {columnStr} {currentStr} {placeholder} {cellCoordsTextStr}

orderPresentation = [
	"states",
	"value",
	"name",
	"roleText",
	"description",
	"keyboardShortcut",
	"positionInfo",
	"positionInfoLevel",
	"row",
	"columnHeaderText",
	"column",
	"current",
	"placeholder",
	"cellCoordsText"
]

def getPropertiesBraille(**propertyValues) -> str:
	properties = {}
	positiveStateLabels =braille.positiveStateLabels
	negativeStateLabels = braille.negativeStateLabels
	TEXT_SEPARATOR = braille.TEXT_SEPARATOR
	roleLabels = braille.roleLabels
	name = propertyValues.get("name")
	if name: properties["name"] = name
	states = propertyValues.get("states")
	role = propertyValues.get("role")
	roleText = propertyValues.get('roleText')
	positionInfo = propertyValues.get("positionInfo")
	level = positionInfo.get("level") if positionInfo else None
	cellCoordsText = propertyValues.get('cellCoordsText')
	rowNumber = propertyValues.get("rowNumber")
	columnNumber = propertyValues.get("columnNumber")
	# When fetching row and column span
	# default the values to 1 to make further checks a lot simpler.
	# After all, a table cell that has no rowspan implemented is assumed to span one row.
	rowSpan = propertyValues.get("rowSpan") or 1
	columnSpan = propertyValues.get("columnSpan") or 1
	includeTableCellCoords = propertyValues.get("includeTableCellCoords", True)
	positionInfoLevelStr = None
	if role is not None and not roleText:
		if role == controlTypes.ROLE_HEADING and level:
			# Translators: Displayed in braille for a heading with a level.
			# %s is replaced with the level.
			roleText = N_("h%s") % level
			level = None
		elif role == controlTypes.ROLE_LINK and states and controlTypes.STATE_VISITED in states:
			states = states.copy()
			states.discard(controlTypes.STATE_VISITED)
			# Translators: Displayed in braille for a link which has been visited.
			roleText = N_("vlnk")
		elif (name or cellCoordsText or rowNumber or columnNumber) and role in controlTypes.silentRolesOnFocus:
			roleText = None
		else:
			roleText = roleLabels.get(role, controlTypes.roleLabels[role])
	elif role is None: 
		role = propertyValues.get("_role")
	if roleText: properties["roleText"] = roleText
	value = propertyValues.get("value") if role not in controlTypes.silentValuesForRoles else None
	if value: properties["value"] = value
	if states:
		properties["states"] = ' '.join(controlTypes.processAndLabelStates(role, states, controlTypes.REASON_FOCUS, states, None, positiveStateLabels, negativeStateLabels))
	description = propertyValues.get("description")
	if description: properties["description"] = description
	keyboardShortcut = propertyValues.get("keyboardShortcut")
	if keyboardShortcut: properties["keyboardShortcut"] = keyboardShortcut
	if positionInfo:
		indexInGroup = positionInfo.get("indexInGroup")
		similarItemsInGroup = positionInfo.get("similarItemsInGroup")
		if indexInGroup and similarItemsInGroup:
			# Translators: Brailled to indicate the position of an item in a group of items (such as a list).
			# {number} is replaced with the number of the item in the group.
			# {total} is replaced with the total number of items in the group.
			properties["positionInfo"] = "{number}/{total}".format(
				number=indexInGroup,
				total=similarItemsInGroup
			)
		if level is not None:
			properties["positionInfoLevel"] = N_("lv %s") % positionInfo['level']
	if rowNumber:
		if includeTableCellCoords and not cellCoordsText: 
			if rowSpan > 1:
				# Translators: Displayed in braille for the table cell row numbers when a cell spans multiple rows.
				# Occurences of %s are replaced with the corresponding row numbers.
				properties["row"] = N_("r{rowNumber}-{rowSpan}").format(rowNumber=rowNumber,rowSpan=rowNumber+rowSpan-1)
			else:
				# Translators: Displayed in braille for a table cell row number.
				# %s is replaced with the row number.
				properties["row"] = N_("r{rowNumber}").format(rowNumber=rowNumber)
	if columnNumber:
		properties["columnHeaderText"] = propertyValues.get("columnHeaderText")
		if includeTableCellCoords and not cellCoordsText:
			if columnSpan>1:
				# Translators: Displayed in braille for the table cell column numbers when a cell spans multiple columns.
				# Occurences of %s are replaced with the corresponding column numbers.
				properties["column"] = N_("c{columnNumber}-{columnSpan}").format(columnNumber=columnNumber,columnSpan=columnNumber+columnSpan-1)
			else:
				# Translators: Displayed in braille for a table cell column number.
				# %s is replaced with the column number.
				properties["column"] = N_("c{columnNumber}").format(columnNumber=columnNumber)
	current = propertyValues.get('current', False)
	if current:
		try:
			currentStr = controlTypes.isCurrentLabels[current]
		except KeyError:
			log.debugWarning("Aria-current value not handled: %s"%current)
			currentStr = controlTypes.isCurrentLabels[True]
		properties["current"] = currentStr
	placeholder = propertyValues.get('placeholder', None)
	if placeholder: properties["placeholder"] = placeholder
	cellCoordsTextStr = None
	if includeTableCellCoords and  cellCoordsText:
		properties["cellCoordsText"] = cellCoordsText
	finalStr = []
	for k in orderPresentation:
		if k in properties and properties[k]:
			finalStr.append(properties[k])
	return TEXT_SEPARATOR.join(finalStr)

class SettingsDlg(gui.settingsDialogs.SettingsPanel):
	# Translators: title of a dialog.
	title = N_("Object Presentation")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		choices = list(CHOICES_LABELS.values())
		self.selectedElement = sHelper.addLabeledControl(_("Show selected &elements with"), wx.Choice, choices=choices)
		self.selectedElement.SetSelection(self.getItemToSelect("selectedElement"))

	@staticmethod
	def getItemToSelect(attribute):
		try: idx = list(CHOICES_LABELS.keys()).index(config.conf["brailleExtender"]["attributes"][attribute])
		except BaseException as err:
			log.error(err)
			idx = 0
		return idx

	def onSave(self):
		config.conf["brailleExtender"]["attributes"]["selectedElement"] = list(CHOICES_LABELS.keys())[self.selectedElement.GetSelection()]
