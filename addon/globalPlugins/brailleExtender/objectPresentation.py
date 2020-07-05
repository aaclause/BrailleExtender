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
import queueHandler
import ui
from .common import *
from .documentFormatting import CHOICES_LABELS
from .consts import CHOICE_liblouis, CHOICE_none

MOVE_UP = 0
MOVE_DOWN = 1

NVDA_ORDER = 0
ADDON_ORDER = 1
PROPERTIES_ORDER = {
	"name": _("name"),
	"value": _("value"),
	"states": _("state"),
	"roleText": _("role text"),
	"description": _("description"),
	"keyboardShortcut": _("keyboard shortcut"),
	"positionInfo": _("position info"),
	"positionInfoLevel": _("position info level"),
	"row": _("row text"),
	"columnHeaderText": _("column header text"),
	"column": _("column text"),
	"current": _("current labels"),
	"placeholder": _("place-holder"),
	"cellCoordsText": _("cell coordinates text"),
}


def getDefaultPropertiesOrder(addon=False):
	if addon:
		return "states,value,name,roleText,description,keyboardShortcut,positionInfo,positionInfoLevel,row,columnHeaderText,column,current,placeholder,cellCoordsText".split(
			","
		)
	else:
		return list(PROPERTIES_ORDER.keys())


def loadpropertiesOrder():
	global propertiesOrder
	propertiesOrder = getPropertiesOrderFromConfig()


def getPropertiesOrderFromConfig():
	defaultPropertiesOrder = getDefaultPropertiesOrder()
	propertiesOrder = config.conf["brailleExtender"]["objectPresentation"][
		"propertiesOrder"
	].split(",")
	if len(defaultPropertiesOrder) != len(propertiesOrder):
		log.error("Missing one or more elements")
		return defaultPropertiesOrder
	for e in propertiesOrder:
		if e not in defaultPropertiesOrder:
			log.error(f"Unknown '{e}'")
			return defaultPropertiesOrder
	return propertiesOrder


propertiesOrder = getDefaultPropertiesOrder()


def getPropertiesOrder():
	return propertiesOrder


def setPropertiesOrder(newOrder, save=False):
	global propertiesOrder
	propertiesOrder = newOrder
	if save:
		config.conf["brailleExtender"]["objectPresentation"][
			"propertiesOrder"
		] = ",".join(newOrder)


def selectedElementEnabled():
	return (
		config.conf["brailleExtender"]["objectPresentation"]["selectedElement"]
		!= CHOICE_none
	)


def getPropertiesBraille(**propertyValues) -> str:
	properties = {}
	positiveStateLabels = braille.positiveStateLabels
	negativeStateLabels = braille.negativeStateLabels
	TEXT_SEPARATOR = braille.TEXT_SEPARATOR
	roleLabels = braille.roleLabels
	name = propertyValues.get("name")
	if name:
		properties["name"] = name
	states = propertyValues.get("states")
	role = propertyValues.get("role")
	roleText = propertyValues.get("roleText")
	positionInfo = propertyValues.get("positionInfo")
	level = positionInfo.get("level") if positionInfo else None
	cellCoordsText = propertyValues.get("cellCoordsText")
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
		elif (
			role == controlTypes.ROLE_LINK
			and states
			and controlTypes.STATE_VISITED in states
		):
			states = states.copy()
			states.discard(controlTypes.STATE_VISITED)
			# Translators: Displayed in braille for a link which has been visited.
			roleText = N_("vlnk")
		elif (
			name or cellCoordsText or rowNumber or columnNumber
		) and role in controlTypes.silentRolesOnFocus:
			roleText = None
		else:
			roleText = roleLabels.get(role, controlTypes.roleLabels[role])
	elif role is None:
		role = propertyValues.get("_role")
	if roleText:
		properties["roleText"] = roleText
	value = (
		propertyValues.get("value")
		if role not in controlTypes.silentValuesForRoles
		else None
	)
	if value:
		properties["value"] = value
	if states:
		if name and selectedElementEnabled():
			states = states.copy()
			states.discard(controlTypes.STATE_SELECTED)
			states.discard(controlTypes.STATE_SELECTABLE)
		properties["states"] = " ".join(
			controlTypes.processAndLabelStates(
				role,
				states,
				controlTypes.REASON_FOCUS,
				states,
				None,
				positiveStateLabels,
				negativeStateLabels,
			)
		)
	description = propertyValues.get("description")
	if description:
		properties["description"] = description
	keyboardShortcut = propertyValues.get("keyboardShortcut")
	if keyboardShortcut:
		properties["keyboardShortcut"] = keyboardShortcut
	if positionInfo:
		indexInGroup = positionInfo.get("indexInGroup")
		similarItemsInGroup = positionInfo.get("similarItemsInGroup")
		if indexInGroup and similarItemsInGroup:
			# Translators: Brailled to indicate the position of an item in a group of items (such as a list).
			# {number} is replaced with the number of the item in the group.
			# {total} is replaced with the total number of items in the group.
			properties["positionInfo"] = "{number}/{total}".format(
				number=indexInGroup, total=similarItemsInGroup
			)
		if level is not None:
			properties["positionInfoLevel"] = N_("lv %s") % positionInfo["level"]
	if rowNumber:
		if includeTableCellCoords and not cellCoordsText:
			if rowSpan > 1:
				# Translators: Displayed in braille for the table cell row numbers when a cell spans multiple rows.
				# Occurences of %s are replaced with the corresponding row numbers.
				properties["row"] = N_("r{rowNumber}-{rowSpan}").format(
					rowNumber=rowNumber, rowSpan=rowNumber + rowSpan - 1
				)
			else:
				# Translators: Displayed in braille for a table cell row number.
				# %s is replaced with the row number.
				properties["row"] = N_("r{rowNumber}").format(rowNumber=rowNumber)
	if columnNumber:
		properties["columnHeaderText"] = propertyValues.get("columnHeaderText")
		if includeTableCellCoords and not cellCoordsText:
			if columnSpan > 1:
				# Translators: Displayed in braille for the table cell column numbers when a cell spans multiple columns.
				# Occurences of %s are replaced with the corresponding column numbers.
				properties["column"] = N_("c{columnNumber}-{columnSpan}").format(
					columnNumber=columnNumber, columnSpan=columnNumber + columnSpan - 1
				)
			else:
				# Translators: Displayed in braille for a table cell column number.
				# %s is replaced with the column number.
				properties["column"] = N_("c{columnNumber}").format(
					columnNumber=columnNumber
				)
	current = propertyValues.get("current", False)
	if current:
		try:
			currentStr = controlTypes.isCurrentLabels[current]
		except KeyError:
			log.debugWarning("Aria-current value not handled: %s" % current)
			currentStr = controlTypes.isCurrentLabels[True]
		properties["current"] = currentStr
	placeholder = propertyValues.get("placeholder", None)
	if placeholder:
		properties["placeholder"] = placeholder
	cellCoordsTextStr = None
	if includeTableCellCoords and cellCoordsText:
		properties["cellCoordsText"] = cellCoordsText
	finalStr = []
	for k in propertiesOrder:
		if k in properties and properties[k]:
			finalStr.append(properties[k])
	return TEXT_SEPARATOR.join(finalStr)


class ManagePropertiesOrder(wx.Dialog):
	def __init__(
		self,
		parent=None,
		# Translators: title of a dialog.
		title=_("Manage properties order"),
	):
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self.propertiesOrder = {k: PROPERTIES_ORDER[k] for k in getPropertiesOrder()}
		self.propertiesOrderList = sHelper.addLabeledControl(
			_("Properties"), wx.Choice, choices=self.getProperties()
		)
		self.propertiesOrderList.Bind(wx.EVT_CHOICE, self.onPropertiesOrderList)
		self.propertiesOrderList.SetSelection(0)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.moveUpBtn = bHelper.addButton(self, label=_("Move &up"))
		self.moveUpBtn.Bind(wx.EVT_BUTTON, lambda evt: self.move(evt, MOVE_UP))
		self.moveDownBtn = bHelper.addButton(self, label=_("Move &down"))
		self.moveDownBtn.Bind(wx.EVT_BUTTON, lambda evt: self.move(evt, MOVE_DOWN))
		sHelper.addItem(bHelper)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.resetNVDAOrder = bHelper.addButton(
			self, label=_("Reset to the default &NVDA order")
		)
		self.resetNVDAOrder.Bind(
			wx.EVT_BUTTON, lambda evt: self.assign(evt, NVDA_ORDER)
		)
		self.resetAddonOrder = bHelper.addButton(
			self, label=_("Reset to the &default add-on order")
		)
		self.resetAddonOrder.Bind(
			wx.EVT_BUTTON, lambda evt: self.assign(evt, ADDON_ORDER)
		)
		sHelper.addItem(bHelper)

		sHelper.addDialogDismissButtons(self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.onPropertiesOrderList()
		self.propertiesOrderList.SetFocus()

	def onPropertiesOrderList(self, evt=None):
		curPos = self.propertiesOrderList.GetSelection()
		if not curPos:
			self.moveUpBtn.Disable()
			self.moveDownBtn.Enable()
		elif curPos >= len(self.propertiesOrder) - 1:
			self.moveDownBtn.Disable()
			self.moveUpBtn.Enable()
		else:
			self.moveDownBtn.Enable()
			self.moveUpBtn.Enable()

	def assign(self, evt, name):
		if name == NVDA_ORDER:
			order = self.propertiesOrder = getDefaultPropertiesOrder()
		else:
			order = getDefaultPropertiesOrder(True)
		self.propertiesOrder = {e: PROPERTIES_ORDER[e] for e in order}
		setPropertiesOrder(self.getPropertiesKeys())
		self.refresh()
		self.propertiesOrderList.SetSelection(0)
		self.propertiesOrderList.SetFocus()

	def move(self, evt, direction):
		firstPos = self.propertiesOrderList.GetSelection()
		secondPos = firstPos + (1 if direction == MOVE_DOWN else -1)
		if secondPos < 0 or secondPos > len(self.getProperties()) - 1:
			return
		toReplace = {
			self.getPropertiesKeys()[firstPos]: self.getPropertiesKeys()[secondPos],
			self.getPropertiesKeys()[secondPos]: self.getPropertiesKeys()[firstPos],
		}
		firstLabel = self.getProperties()[firstPos]
		secondLabel = self.getProperties()[secondPos]
		l = [
			k if not k in toReplace else toReplace[k] for k in self.getPropertiesKeys()
		]
		self.propertiesOrder = {e: PROPERTIES_ORDER[e] for e in l}
		setPropertiesOrder(self.getPropertiesKeys())
		self.refresh()
		self.propertiesOrderList.SetSelection(secondPos)
		directionLabel = _("after") if direction == MOVE_DOWN else _("before")
		queueHandler.queueFunction(
			queueHandler.eventQueue,
			ui.message,
			f"{firstLabel} {directionLabel} {secondLabel}",
		)

	def refresh(self):
		self.propertiesOrderList.SetItems(self.getProperties())
		self.onPropertiesOrderList()
		self.propertiesOrderList.SetFocus()

	def getPropertiesKeys(self):
		return list(self.propertiesOrder.keys())

	def getProperties(self):
		return list(self.propertiesOrder.values())

	def onOk(self, evt):
		setPropertiesOrder(list(self.getPropertiesKeys()), True)
		self.Destroy()


class SettingsDlg(gui.settingsDialogs.SettingsPanel):
	# Translators: title of a dialog.
	title = N_("Object Presentation")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.choices = {k: v for k, v in CHOICES_LABELS.items() if k != CHOICE_liblouis}
		try:
			itemToSelect = list(self.choices.keys()).index(
				config.conf["brailleExtender"]["objectPresentation"]["selectedElement"]
			)
		except IndexError:
			itemToSelect = 0
		self.selectedElement = sHelper.addLabeledControl(
			_("Show selected &elements with"),
			wx.Choice,
			choices=list(self.choices.values()),
		)
		self.selectedElement.SetSelection(itemToSelect)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.propertiesOrderBtn = bHelper.addButton(
			self, label="%s..." % _("Manage properties &order")
		)
		self.propertiesOrderBtn.Bind(wx.EVT_BUTTON, self.onPropertiesOrderBtn)
		sHelper.addItem(bHelper)

	def onPropertiesOrderBtn(self, evt):
		managePropertiesOrder = ManagePropertiesOrder(self)
		managePropertiesOrder.ShowModal()
		managePropertiesOrder.Destroy()
		loadpropertiesOrder()
		self.propertiesOrderBtn.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["objectPresentation"]["selectedElement"] = list(
			self.choices.keys()
		)[self.selectedElement.GetSelection()]
