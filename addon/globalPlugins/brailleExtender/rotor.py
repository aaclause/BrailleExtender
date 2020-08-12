# rotor.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
from collections import namedtuple
import config
import gui
import wx
import inputCore

conf = config.conf["brailleExtender"]["rotor"]

RotorItem = namedtuple("RotorItem", ("id", "name", "browse_mode_only"))

ITEM_DEFAULT = "default"
ITEM_MOVE_IN_TEXT = "moveInText"
ITEM_TEXT_SELECTION = "textSelection"
ITEM_OBJECT = "object"
ITEM_REVIEW = "review"
ITEM_VOLUME = "volume"
ITEM_BRAILLE_TABLE = "brailleTable"
ITEM_LINK = "link"
ITEM_UNVISITED_LINK = "unvisitedLink"
ITEM_VISITED_LINK = "visitedLink"
ITEM_LANDMARK = "landmark"
ITEM_HEADING = "heading"
ITEM_HEADING1 = "heading1"
ITEM_HEADING2 = "heading2"
ITEM_HEADING3 = "heading3"
ITEM_HEADING4 = "heading4"
ITEM_HEADING5 = "heading5"
ITEM_HEADING6 = "heading6"
ITEM_LIST = "list"
ITEM_LIST_ITEM = "listItem"
ITEM_GRAPHIC = "graphic"
ITEM_BLOCK_QUOTE = "blockQuote"
ITEM_BUTTON = "buttons"
ITEM_FORM = "form"
ITEM_EDIT = "edit"
ITEM_RADIO_BUTTON = "radioButton"
ITEM_COMBO_BOX = "comboBox"
ITEM_CHECK_BOX = "checkBox"
ITEM_NOT_LINK_BLOCK = "notLinkBlock"
ITEM_FRAME = "frame"
ITEM_SEPARATOR = "separator"
ITEM_EMBEDDED_OBJECT = "embeddedObject"
ITEM_ANNOTATION = "annotation"
ITEM_ERROR = "error"
ITEM_TABLE = "table"
ITEM_MOVE_IN_TABLE = "moveInTable"

MOVE_UP = 0
MOVE_DOWN = 1

ITEM_LABELS = [
	RotorItem(ITEM_DEFAULT, _("Default"), 0),
	RotorItem(ITEM_MOVE_IN_TEXT, _("Moving in the text"), 0),
	RotorItem(ITEM_TEXT_SELECTION, _("Text selection"), 0),
	RotorItem(ITEM_OBJECT, _("Objects"), 0),
	RotorItem(ITEM_REVIEW, _("Review"), 0),
	RotorItem(ITEM_VOLUME, _("Master volume"), 0),
	RotorItem(ITEM_BRAILLE_TABLE, _("Braille tables"), 0),
	RotorItem(ITEM_LINK, _("Links"), 1),
	RotorItem(ITEM_UNVISITED_LINK, _("Unvisited links"), 1),
	RotorItem(ITEM_VISITED_LINK, _("Visited links"), 1),
	RotorItem(ITEM_LANDMARK, _("Landmarks"), 1),
	RotorItem(ITEM_HEADING, _("Headings"), 1),
	RotorItem(ITEM_HEADING1, _("Level 1 headings"), 1),
	RotorItem(ITEM_HEADING2, _("Level 2 headings"), 1),
	RotorItem(ITEM_HEADING3, _("Level 3 headings"), 1),
	RotorItem(ITEM_HEADING4, _("Level 4 headings"), 1),
	RotorItem(ITEM_HEADING5, _("Level 5 headings"), 1),
	RotorItem(ITEM_HEADING6, _("Level 6 headings"), 1),
	RotorItem(ITEM_LIST, _("Lists"), 1),
	RotorItem(ITEM_LIST_ITEM, _("List items"), 1),
	RotorItem(ITEM_GRAPHIC, _("Graphics"), 1),
	RotorItem(ITEM_BLOCK_QUOTE, _("Block quotes"), 1),
	RotorItem(ITEM_BUTTON, _("Buttons"), 1),
	RotorItem(ITEM_FORM, _("Form fields"), 1),
	RotorItem(ITEM_EDIT, _("Edit fields"), 1),
	RotorItem(ITEM_RADIO_BUTTON, _("Radio buttons"), 1),
	RotorItem(ITEM_COMBO_BOX, _("Combo boxes"), 1),
	RotorItem(ITEM_CHECK_BOX, _("Check boxes"), 1),
	RotorItem(ITEM_NOT_LINK_BLOCK, _("Non-link blocks"), 1),
	RotorItem(ITEM_FRAME, _("Frames"), 1),
	RotorItem(ITEM_SEPARATOR, _("Separators"), 1),
	RotorItem(ITEM_EMBEDDED_OBJECT, _("Embedded objects"), 1),
	RotorItem(ITEM_ANNOTATION, _("Annotations"), 1),
	RotorItem(ITEM_ERROR, _("Errors"), 1),
	RotorItem(ITEM_TABLE, _("Tables"), 1),
	RotorItem(ITEM_MOVE_IN_TABLE, _("Move in table"), 1),
]


class Rotor:

	cur_item_browse_mode = 0
	cur_item_form_mode = 0

	def __init__(self):
		rotorRange = 0
		lastRotorItemInVD = 0


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Rotor")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: label of a dialog.
		label = _("Rotor &items")
		choices = [item.name for item in ITEM_LABELS]
		self.enabled_items = conf["enabledItems"].split(',')
		choices_to_enable = [i for i, item in enumerate(
			ITEM_LABELS) if item.id in self.enabled_items]
		self.rotorItems = sHelper.addLabeledControl(
			label,
			gui.nvdaControls.CustomCheckListBox,
			choices=choices
		)
		self.rotorItems.CheckedItems = choices_to_enable
		label = _("Item order")
		item_order_group = gui.guiHelper.BoxSizerHelper(
			self, sizer=wx.StaticBoxSizer(wx.StaticBox(self, label=label), wx.VERTICAL))
		label = _("Item &list")
		choices = [
			item.name for item in ITEM_LABELS if item.id in self.enabled_items]
		self.order_item = item_order_group.addLabeledControl(
			label, wx.Choice, choices=choices)
		self.order_item.SetSelection(0)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table dictionaries dialog to add new entries.
			label=_("Move &up")
		).Bind(wx.EVT_BUTTON, lambda evt: self.move_to(evt, MOVE_UP))
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table dictionaries dialog to add new entries.
			label=_("Move &down")
		).Bind(wx.EVT_BUTTON, lambda evt: self.move_to(evt, MOVE_DOWN))
		item_order_group.addItem(bHelper)
		sHelper.addItem(item_order_group)

	def move_to(self, evt, direction):
		pass

	def postInit(self):
		self.rotorItems.SetFocus()

	def onSave(self):
		pass
