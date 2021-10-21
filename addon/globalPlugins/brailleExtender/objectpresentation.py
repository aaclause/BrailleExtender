# objectpresentation.py
import addonHandler
import braille
import config
import controlTypes
import gui
import queueHandler
import ui
import wx
from logHandler import log

from . import addoncfg
from .common import N_, CHOICE_liblouis, CHOICE_none, ADDON_ORDER_PROPERTIES, IS_CURRENT_NO
from .documentformatting import CHOICES_LABELS, get_report
from .utils import get_output_reason, get_control_type

addonHandler.initTranslation()

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
	"current": _("current labels"),
	"placeholder": _("place-holder"),
	"cellCoordsText": _("cell coordinates text"),
}


def getDefaultOrderProperties(addon=False):
	if addon:
		return ADDON_ORDER_PROPERTIES.split(',')
	else:
		return list(PROPERTIES_ORDER.keys())


def loadOrderProperties():
	global orderProperties
	orderProperties = getOrderPropertiesFromConfig()


def getOrderPropertiesFromConfig():
	defaultOrderProperties = getDefaultOrderProperties()
	orderProperties = config.conf["brailleExtender"]["objectPresentation"][
		"orderProperties"
	].split(",")
	if len(defaultOrderProperties) > len(orderProperties):
		log.error("Missing one or more elements")
		setOrderProperties(defaultOrderProperties, True)
		return defaultOrderProperties
	for e in orderProperties:
		if e not in defaultOrderProperties:
			log.warning(f"Unknown '{e}'")
			setOrderProperties(defaultOrderProperties, True)
			return defaultOrderProperties
	return orderProperties


orderProperties = getDefaultOrderProperties()


def getOrderProperties():
	return orderProperties


def setOrderProperties(newOrder, save=False):
	global orderProperties
	orderProperties = newOrder
	if save:
		config.conf["brailleExtender"]["objectPresentation"][
			"orderProperties"
		] = ",".join(newOrder)


def selectedElementEnabled():
	return (
			config.conf["brailleExtender"]["objectPresentation"]["selectedElement"]
			!= CHOICE_none
	)


def update_NVDAObjectRegion(self):
	obj = self.obj
	presConfig = config.conf["presentation"]
	role = obj.role
	placeholderValue = obj.placeholder
	if placeholderValue and not obj._isTextEmpty:
		placeholderValue = None
	cellInfo = None
	if hasattr(obj, "excelCellInfo"):
		cellInfo = obj.excelCellInfo
	text = getPropertiesBraille(
		name=obj.name,
		role=role,
		roleText=obj.roleTextBraille,
		current=obj.isCurrent,
		placeholder=placeholderValue,
		value=obj.value if not braille.NVDAObjectHasUsefulText(obj) else None,
		states=obj.states,
		description=obj.description if presConfig["reportObjectDescriptions"] else None,
		keyboardShortcut=obj.keyboardShortcut if presConfig["reportKeyboardShortcuts"] else None,
		positionInfo=obj.positionInfo if presConfig["reportObjectPositionInformation"] else None,
		cellCoordsText=obj.cellCoordsText if get_report("tableCellCoords") else None,
		cellInfo=cellInfo
	)
	try:
		if getattr(obj, "columnHeaderText"):
			text += '⣀' + obj.columnHeaderText
	except NotImplementedError:
		pass
	try:
		if getattr(obj, "rowHeaderText"):
			text += '⡀' + obj.rowHeaderText
	except NotImplementedError:
		pass
	if not getattr(obj, "cellCoordsText"):
		coordinates = ""
		try:
			if getattr(obj, "rowNumber"):
				coordinates += N_("r{rowNumber}").format(rowNumber=obj.rowNumber)
		except NotImplementedError:
			pass
		try:
			if getattr(obj, "columnNumber"):
				coordinates += N_("c{columnNumber}").format(columnNumber=obj.columnNumber)
		except NotImplementedError:
			pass
		if coordinates:
			text += ' ' + coordinates
	if role == get_control_type("ROLE_MATH"):
		import mathPres
		mathPres.ensureInit()
		if mathPres.brailleProvider:
			try:
				text += braille.TEXT_SEPARATOR + mathPres.brailleProvider.getBrailleForMathMl(
					obj.mathMl)
			except (NotImplementedError, LookupError):
				pass
	self.rawText = text + self.appendText
	super(braille.NVDAObjectRegion, self).update()


def is_current_display_string(current):
	if hasattr(current, "displayString"):
		return current.displayString
	if hasattr(get_control_type("controlTypes"), "isCurrentLabels"):
		try:
			return controlTypes.isCurrentLabels[current]
		except KeyError:
			pass
	log.debugWarning("Aria-current value not handled: %s" % current)
	return ''


def get_roleLabel(role):
	if hasattr(controlTypes, "Role"):
		return getattr(controlTypes.Role, role).displayString
	return controlTypes.roleLabels[role]


def getPropertiesBraille(**propertyValues) -> str:
	properties = {}
	positiveStateLabels = braille.positiveStateLabels
	negativeStateLabels = braille.negativeStateLabels
	TEXT_SEPARATOR = braille.TEXT_SEPARATOR
	roleLabels = braille.roleLabels
	name = propertyValues.get("name")
	if name:
		properties["name"] = name
	description = propertyValues.get("description")
	states = propertyValues.get("states")
	role = propertyValues.get("role")
	roleText = propertyValues.get("roleText")
	roleTextPost = propertyValues.get("roleTextPost")
	positionInfo = propertyValues.get("positionInfo")
	level = positionInfo.get("level") if positionInfo else None
	cellCoordsText = propertyValues.get("cellCoordsText")
	cellInfo = propertyValues.get("cellInfo")
	rowNumber = propertyValues.get("rowNumber")
	columnNumber = propertyValues.get("columnNumber")
	# When fetching row and column span
	# default the values to 1 to make further checks a lot simpler.
	# After all, a table cell that has no rowspan implemented is assumed to span one row.
	rowSpan = propertyValues.get("rowSpan") or 1
	columnSpan = propertyValues.get("columnSpan") or 1
	includeTableCellCoords = get_report("tableCellCoords") and propertyValues.get("includeTableCellCoords", True)
	positionInfoLevelStr = None
	if role is not None and not roleText:
		if role == get_control_type("ROLE_HEADING") and level:
			roleText = N_("h%s") % level
			level = None
		elif (
				role == get_control_type("ROLE_LINK")
				and states
				and get_control_type("STATE_VISITED") in states
		):
			states = states.copy()
			states.discard(get_control_type("STATE_VISITED"))
			roleText = N_("vlnk")
		elif not description and config.conf["brailleExtender"]["documentFormatting"][
			"cellFormula"] and states and get_control_type("STATE_HASFORMULA") in states and cellInfo and hasattr(cellInfo,
																										   "formula") and cellInfo.formula:
			states = states.copy()
			states.discard(get_control_type("STATE_HASFORMULA"))
			description = cellInfo.formula
		elif (
				name or cellCoordsText or rowNumber or columnNumber
		) and role in controlTypes.silentRolesOnFocus:
			roleText = None
		else:
			roleText = roleLabels.get(role, role.displayString)
	elif role is None:
		role = propertyValues.get("_role")
	if roleText and roleTextPost:
		roleText += roleTextPost
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
			states.discard(get_control_type("STATE_SELECTED"))
			states.discard(get_control_type("STATE_SELECTABLE"))
		properties["states"] = " ".join(
			controlTypes.processAndLabelStates(
				role,
				states,
				REASON_FOCUS,
				states,
				None,
				positiveStateLabels,
				negativeStateLabels,
			)
		)
	if description:
		properties["description"] = description
	keyboardShortcut = propertyValues.get("keyboardShortcut")
	if keyboardShortcut:
		properties["keyboardShortcut"] = keyboardShortcut
	if positionInfo:
		indexInGroup = positionInfo.get("indexInGroup")
		similarItemsInGroup = positionInfo.get("similarItemsInGroup")
		if indexInGroup and similarItemsInGroup:
			properties["positionInfo"] = "{number}/{total}".format(
				number=indexInGroup, total=similarItemsInGroup
			)
		if level is not None:
			properties["positionInfoLevel"] = N_(
				"lv %s") % positionInfo["level"]

	rowCoordinate = ""
	columnCoordinate = ""
	columnHeaderText = ""
	if rowNumber:
		if includeTableCellCoords and not cellCoordsText:
			if rowSpan > 1:
				rowCoordinate = N_("r{rowNumber}-{rowSpan}").format(
					rowNumber=rowNumber, rowSpan=rowNumber + rowSpan - 1
				)
			else:
				rowCoordinate = N_("r{rowNumber}").format(
					rowNumber=rowNumber)
	if columnNumber:
		columnHeaderText = propertyValues.get("columnHeaderText")
		if includeTableCellCoords and not cellCoordsText:
			if columnSpan > 1:
				columnCoordinate = N_("c{columnNumber}-{columnSpan}").format(
					columnNumber=columnNumber, columnSpan=columnNumber + columnSpan - 1
				)
			else:
				columnCoordinate = N_("c{columnNumber}").format(
					columnNumber=columnNumber
				)
	if not cellCoordsText and columnHeaderText or rowCoordinate or columnCoordinate:
		includeTableCellCoords = True
		if rowCoordinate and columnCoordinate:
			cellCoordsText = rowCoordinate + columnCoordinate
			if columnHeaderText:
				cellCoordsText += "(%s)" % columnHeaderText
		elif rowCoordinate:
			cellCoordsText = rowCoordinate
		elif columnCoordinate:
			cellCoordsText = columnHeaderText
	isCurrent = propertyValues.get("current", IS_CURRENT_NO)
	if isCurrent != IS_CURRENT_NO:
		properties["current"] = is_current_display_string(isCurrent)
	placeholder = propertyValues.get("placeholder", None)
	if placeholder:
		properties["placeholder"] = placeholder
	if includeTableCellCoords and cellCoordsText:
		properties["cellCoordsText"] = cellCoordsText
	finalStr = []
	for k in orderProperties:
		if k in properties and properties[k]:
			finalStr.append(properties[k])
	return TEXT_SEPARATOR.join(finalStr)


class ManageOrderProperties(gui.settingsDialogs.SettingsDialog):
	# Translators: title of a dialog.
	title = _("Order Properties")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self.orderProperties = {
			k: PROPERTIES_ORDER[k] for k in getOrderProperties()}
		self.orderPropertiesList = sHelper.addLabeledControl(
			_("Properties"), wx.Choice, choices=self.getProperties()
		)
		self.orderPropertiesList.Bind(
			wx.EVT_CHOICE, self.onOrderPropertiesList)
		self.orderPropertiesList.SetSelection(0)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.moveUpBtn = bHelper.addButton(self, label=_("Move &up"))
		self.moveUpBtn.Bind(wx.EVT_BUTTON, lambda evt: self.move(evt, MOVE_UP))
		self.moveDownBtn = bHelper.addButton(self, label=_("Move &down"))
		self.moveDownBtn.Bind(
			wx.EVT_BUTTON, lambda evt: self.move(evt, MOVE_DOWN))
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

	def onOrderPropertiesList(self, evt=None):
		curPos = self.orderPropertiesList.GetSelection()
		if not curPos:
			self.moveUpBtn.Disable()
			self.moveDownBtn.Enable()
		elif curPos >= len(self.orderProperties) - 1:
			self.moveDownBtn.Disable()
			self.moveUpBtn.Enable()
		else:
			self.moveDownBtn.Enable()
			self.moveUpBtn.Enable()

	def assign(self, evt, name):
		if name == NVDA_ORDER:
			order = self.orderProperties = getDefaultOrderProperties()
		else:
			order = getDefaultOrderProperties(True)
		self.orderProperties = {e: PROPERTIES_ORDER[e] for e in order}
		setOrderProperties(self.getPropertiesKeys())
		self.refresh()
		self.orderPropertiesList.SetSelection(0)
		self.orderPropertiesList.SetFocus()

	def move(self, evt, direction):
		firstPos = self.orderPropertiesList.GetSelection()
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
		self.orderProperties = {e: PROPERTIES_ORDER[e] for e in l}
		setOrderProperties(self.getPropertiesKeys())
		self.refresh()
		self.orderPropertiesList.SetSelection(secondPos)
		directionLabel = _("after") if direction == MOVE_DOWN else _("before")
		queueHandler.queueFunction(
			queueHandler.eventQueue,
			ui.message,
			f"{firstLabel} {directionLabel} {secondLabel}",
		)

	def refresh(self):
		self.orderPropertiesList.SetItems(self.getProperties())
		self.onOrderPropertiesList()

	def getPropertiesKeys(self):
		return list(self.orderProperties.keys())

	def getProperties(self):
		return list(self.orderProperties.values())

	def postInit(self):
		self.onOrderPropertiesList()
		self.orderPropertiesList.SetFocus()

	def onOk(self, evt):
		setOrderProperties(list(self.getPropertiesKeys()), True)
		loadOrderProperties()
		super().onOk(evt)


class ManageRoleLabels(gui.settingsDialogs.SettingsDialog):
	# Translators: title of a dialog.
	title = _("Role/state labels")

	roleLabels = {}

	def makeSettings(self, settingsSizer):
		self.roleLabels = config.conf["brailleExtender"]["roleLabels"].copy()
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleRoleLabels = sHelper.addItem(wx.CheckBox(self, label=_("Use custom braille &role labels")))
		self.toggleRoleLabels.SetValue(config.conf["brailleExtender"]["features"]["roleLabels"])
		self.categories = sHelper.addLabeledControl(_("Role &category:"), wx.Choice,
													choices=[_("General"), _("Landmark"), _("Positive state"),
															 _("Negative state")])
		self.categories.Bind(wx.EVT_CHOICE, self.onCategories)
		self.categories.SetSelection(0)
		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		self.labels = sHelper2.addLabeledControl(_("&Role:"), wx.Choice,
												 choices=[controlTypes.roleLabels[int(k)] for k in
														  braille.roleLabels.keys()])
		self.labels.Bind(wx.EVT_CHOICE, self.onLabels)
		self.label = sHelper2.addLabeledControl(_("Braille &label"), wx.TextCtrl)
		self.label.Bind(wx.EVT_TEXT, self.onLabel)
		sHelper.addItem(sHelper2)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.resetLabelBtn = bHelper.addButton(self, wx.NewId(), _("&Reset this role label"), wx.DefaultPosition)
		self.resetLabelBtn.Bind(wx.EVT_BUTTON, self.onResetLabelBtn)
		self.resetAllLabelsBtn = bHelper.addButton(self, wx.NewId(), _("Reset all role labels"), wx.DefaultPosition)
		self.resetAllLabelsBtn.Bind(wx.EVT_BUTTON, self.onResetAllLabelsBtn)
		sHelper.addItem(bHelper)
		self.onCategories(None)

	def onCategories(self, event):
		idCategory = self.categories.GetSelection()
		if idCategory == 0:
			labels = [controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()]
		elif idCategory == 1:
			labels = list(braille.landmarkLabels.keys())
		elif idCategory == 2:
			labels = [controlTypes.stateLabels[k] for k in braille.positiveStateLabels.keys()]
		elif idCategory == 3:
			labels = [controlTypes.stateLabels[k] for k in braille.negativeStateLabels.keys()]
		else:
			labels = []
		for iLabel, label in enumerate(labels):
			idLabel = self.getIDFromIndexes(idCategory, iLabel)
			actualLabel = self.getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			labels[iLabel] = "{}: {}".format(labels[iLabel], actualLabel)
			if actualLabel != originalLabel: labels[iLabel] += " (%s)" % originalLabel
		self.labels.SetItems(labels)
		if idCategory > -1 and idCategory < 4: self.labels.SetSelection(0)
		self.onLabels(None)

	def onLabels(self, event):
		idCategory = self.categories.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, self.labels.GetSelection())
		key = "%d:%s" % (idCategory, idLabel)
		if key in self.roleLabels.keys():
			self.label.SetValue(self.roleLabels[key])
		else:
			self.label.SetValue(self.getOriginalLabel(idCategory, idLabel))

	def onLabel(self, evt):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		label = self.label.GetValue()
		if idCategory >= 0 and iLabel >= 0:
			if self.getOriginalLabel(idCategory, idLabel, chr(4)) == label:
				if key in self.roleLabels.keys():
					self.roleLabels.pop(key)
					log.debug("Key %s deleted" % key)
				else:
					log.info("Key %s not present" % key)
			else:
				self.roleLabels[key] = label
			actualLabel = self.getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			if label != originalLabel:
				self.resetLabelBtn.Enable()
			else:
				self.resetLabelBtn.Disable()

	def onResetLabelBtn(self, event):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = self.getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		actualLabel = self.getLabelFromID(idCategory, idLabel)
		originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
		self.label.SetValue(originalLabel)
		self.onLabel(None)
		self.label.SetFocus()

	def onResetAllLabelsBtn(self, event):
		nbCustomizedLabels = len(self.roleLabels)
		if not nbCustomizedLabels:
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("You have no customized role labels."))
			return
		res = gui.messageBox(
			_("You have %d customized role labels defined. Do you want to reset all labels?") % nbCustomizedLabels,
			_("Reset role labels"),
			wx.YES | wx.NO | wx.ICON_INFORMATION)
		if res == wx.YES:
			self.roleLabels = {}
			config.conf["brailleExtender"]["roleLabels"] = {}
			self.onCategories(None)

	def getOriginalLabel(self, idCategory, idLabel, defaultValue=''):
		if "%s:%s" % (idCategory, idLabel) in addoncfg.backupRoleLabels.keys():
			return addoncfg.backupRoleLabels["%s:%s" % (idCategory, idLabel)][1]
		return self.getLabelFromID(idCategory, idLabel)

	@staticmethod
	def getIDFromIndexes(idCategory, idLabel):
		try:
			if idCategory == 0: return list(braille.roleLabels.keys())[idLabel]
			if idCategory == 1: return list(braille.landmarkLabels.keys())[idLabel]
			if idCategory == 2: return list(braille.positiveStateLabels.keys())[idLabel]
			if idCategory == 3: return list(braille.negativeStateLabels.keys())[idLabel]
			raise ValueError("Invalid value for ID category: %d" % idCategory)
		except BaseException:
			return -1

	def getLabelFromID(self, idCategory, idLabel):
		if idCategory == 0: return braille.roleLabels[idLabel]
		if idCategory == 1: return braille.landmarkLabels[idLabel]
		if idCategory == 2: return braille.positiveStateLabels[idLabel]
		if idCategory == 3: return braille.negativeStateLabels[idLabel]
		raise ValueError("Invalid value: %d" % idCategory)

	def postInit(self):
		self.toggleRoleLabels.SetFocus()

	def onOk(self, evt):
		config.conf["brailleExtender"]["features"]["roleLabels"] = self.toggleRoleLabels.IsChecked()
		config.conf["brailleExtender"]["roleLabels"] = self.roleLabels
		addoncfg.discardRoleLabels()
		if config.conf["brailleExtender"]["features"]["roleLabels"]:
			addoncfg.loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())
			super().onOk(evt)


class SettingsDlg(gui.settingsDialogs.SettingsPanel):
	# Translators: title of a dialog.
	title = N_("Object Presentation")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.choices = {k: v for k, v in CHOICES_LABELS.items()
						if k != CHOICE_liblouis}
		try:
			itemToSelect = list(self.choices.keys()).index(
				config.conf["brailleExtender"]["objectPresentation"]["selectedElement"]
			)
		except IndexError:
			itemToSelect = 0
		self.selectedElement = sHelper.addLabeledControl(
			_("Selected &elements:"),
			wx.Choice,
			choices=list(self.choices.values()),
		)
		self.selectedElement.SetSelection(itemToSelect)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.orderPropertiesBtn = bHelper.addButton(
			self, label="&Order Properties..."
		)
		self.orderPropertiesBtn.Bind(wx.EVT_BUTTON, self.onOrderPropertiesBtn)

		self.roleLabelsBtn = bHelper.addButton(
			self, label=_("&Role/state labels...")
		)
		self.roleLabelsBtn.Bind(wx.EVT_BUTTON, self.onRoleLabelsBtn)

		sHelper.addItem(bHelper)

	def onOrderPropertiesBtn(self, evt):
		manageOrderProperties = ManageOrderProperties(self)
		manageOrderProperties.ShowModal()
		manageOrderProperties.Destroy()
		self.orderPropertiesBtn.SetFocus()

	def onRoleLabelsBtn(self, evt):
		manageRoleLabels = ManageRoleLabels(self)
		manageRoleLabels.ShowModal()
		self.roleLabelsBtn.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["objectPresentation"]["selectedElement"] = list(
			self.choices.keys()
		)[self.selectedElement.GetSelection()]

REASON_FOCUS = get_output_reason("FOCUS")
