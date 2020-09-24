# brailleTablesExt.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import codecs
import json
import os
import gui
import wx

import addonHandler
import config
from collections import namedtuple
from itertools import permutations
from typing import Optional, List, Tuple
from brailleTables import listTables
from logHandler import log
from . import configBE
from .common import addonName, baseDir, configDir

addonHandler.initTranslation()

POSITION_CURRENT = "c"
POSITION_PREVIOUS = "p"
POSITION_NEXT = "n"
POSITIONS = [POSITION_CURRENT, POSITION_PREVIOUS, POSITION_NEXT]

USABLE_INPUT = 0
USABLE_OUTPUT = 1
USABLE_BOTH = 2
USABLE_LIST = [USABLE_INPUT, USABLE_OUTPUT, USABLE_BOTH]

USABLE_LIST_LABELS = {
	USABLE_INPUT: _("input only"),
	USABLE_OUTPUT: _("output only"),
	USABLE_BOTH: _("input and output")
}
GroupTables = namedtuple("GroupTables", (
	"name", "members", "usableIn"))

conf = config.conf["brailleExtender"]["tables"]

def listContractedTables(tables=None):
	return [table for table in (
		tables or listTables()) if table.contracted]


def listUncontractedTables(tables=None):
	return [table for table in (
		tables or listTables()) if not table.contracted]


def listInputTables(tables=None):
	return [
		table for table in (tables or listTables()) if table.input]


listUncontractedInputTables = listInputTables(listUncontractedTables())


def listOutputTables(tables=None):
	return [
		table for table in (tables or listTables()) if table.output]


def listTablesFileName(tables=None):
	return [
		table.fileName for table in (tables or listTables())]


def listTablesDisplayName(tables=None):
	return [
		table.displayName for table in (tables or listTables())]


def fileName2displayName(l):
	allTablesFileName = listTablesFileName()
	o = []
	for e in l:
		if e in allTablesFileName:
			o.append(allTablesFileName.index(e))
	return [listTables()[e].displayName for e in o]


def listTablesIndexes(l, tables):
	if not tables:
		tables = listTables()
	tables = listTablesFileName(tables)
	return [tables.index(e) for e in l if e in tables]


def getPreferredTables() -> Tuple[List[str]]:
	allInputTablesFileName = listTablesFileName(listInputTables())
	allOutputTablesFileName = listTablesFileName(listOutputTables())
	preferredInputTablesFileName = conf["preferredInput"].split(
		'|')
	preferredOutputTablesFileName = conf["preferredOutput"].split(
		'|')
	inputTables = [
		fn for fn in preferredInputTablesFileName if fn in allInputTablesFileName]
	outputTables = [
		fn for fn in preferredOutputTablesFileName if fn in allOutputTablesFileName]
	return inputTables, outputTables


def getPreferredTablesIndexes() -> List[int]:
	preferredInputTables, preferredOutputTables = getPreferredTables()
	inputTables = listTablesFileName(listInputTables())
	outputTables = listTablesFileName(listOutputTables())
	o = []
	for a, b in [(preferredInputTables, inputTables), (preferredOutputTables, outputTables)]:
		o_ = []
		for e in a:
			if e in b:
				o_.append(b.index(e))
		o.append(o_)
	return o


def getCustomBrailleTables():
	return [config.conf["brailleExtender"]["brailleTables"][k].split('|', 3) for k in config.conf["brailleExtender"]["brailleTables"]]


def isContractedTable(fileName):
	return fileName in listTablesFileName(listContractedTables())


def getTable(fileName, tables=None):
	if not tables:
		tables = listTables()
	for table in tables:
		if table.fileName == fileName:
			return table
	return None


def getTablesFilenameByID(l: List[int], tables=None) -> List[int]:
	tablesFileName = [table.fileName for table in (tables or listTables())]
	o = []
	size = len(tablesFileName)
	for i in l:
		if i < size:
			o.append(tablesFileName[i])
	return o


def translateUsableIn(s):
	labels = USABLE_LIST_LABELS
	return labels[s] if s in labels.keys() else _("None")


def setDict(newGroups):
	global _groups
	_groups = newGroups


def getPathGroups():
	return f"{configDir}/table-groups.json"


def initializeGroups():
	global _groups
	_groups = []
	fp = getPathGroups()
	if not os.path.exists(fp):
		return
	json_ = json.load(codecs.open(fp, "r", "UTF-8"))
	for entry in json_:
		_groups.append(
			GroupTables(
				entry["name"], entry["members"], entry["usableIn"]
			)
		)


def saveGroups(entries=None):
	if not entries:
		entries = getGroups()
	entries = [
		{
			"name": entry.name,
			"members": entry.members,
			"usableIn": entry.usableIn,
		}
		for entry in entries
	]
	with codecs.open(getPathGroups(), "w", "UTF-8") as outfile:
		json.dump(entries, outfile, ensure_ascii=False, indent=2)


def getGroups(plain=True):
	if plain:
		return _groups if _groups else []
	groups = getGroups()
	i = [group for group in groups if group.usableIn in ['i', 'io']]
	o = [group for group in groups if group.usableIn in ['o', 'io']]
	return i, o


def getAllGroups(usableIn):
	usableInIndex = USABLE_LIST.index(usableIn)
	return [None] + tablesToGroups(getPreferredTables()[usableInIndex], usableIn=usableIn) + getGroups(0)[usableInIndex]


def getGroup(
	usableIn,
	position=POSITION_CURRENT,
	choices=None
):
	global _currentGroup
	if position not in POSITIONS or usableIn not in USABLE_LIST:
		return None
	usableInIndex = USABLE_LIST.index(usableIn)
	currentGroup = _currentGroup[usableInIndex]
	if not choices:
		choices = getAllGroups(usableIn)
	if currentGroup not in choices:
		currentGroup = choices[0]
	curPos = choices.index(currentGroup)
	newPos = curPos
	if position == POSITION_PREVIOUS:
		newPos = curPos - 1
	elif position == POSITION_NEXT:
		newPos = curPos + 1
	return choices[newPos % len(choices)]


def setTableOrGroup(usableIn, e, choices=None):
	global _currentGroup
	if not usableIn in USABLE_LIST:
		return False
	usableInIndex = USABLE_LIST.index(usableIn)
	choices = getAllGroups(usableIn)
	if not e in choices:
		return False
	_currentGroup[usableInIndex] = e
	return True


def tablesToGroups(tables, usableIn):
	groups = []
	for table in tables:
		groups.append(GroupTables(
			", ".join(fileName2displayName([table])),
			[table],
			usableIn
		))
	return groups


def groupEnabled():
	return bool(_groups)


_groups = None
_currentGroup = [None, None]


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Braille tables")

	def makeSettings(self, settingsSizer):
		listPreferredTablesIndexes = getPreferredTablesIndexes()
		currentTableLabel = _("Use the current input table")
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		tables = [
			f"{table.displayName}, {table.fileName}" for table in listTables() if table.input]
		label = _("Preferred &input tables")
		self.inputTables = sHelper.addLabeledControl(
			label, gui.nvdaControls.CustomCheckListBox, choices=tables)
		self.inputTables.CheckedItems = listPreferredTablesIndexes[0]
		self.inputTables.Select(0)

		tables = [
			f"{table.displayName}, {table.fileName}" for table in listTables() if table.output]
		label = _("Preferred &output tables")
		self.outputTables = sHelper.addLabeledControl(
			label, gui.nvdaControls.CustomCheckListBox, choices=tables)
		self.outputTables.CheckedItems = listPreferredTablesIndexes[1]
		self.outputTables.Select(0)

		label = _("Input braille table to use for keyboard shortcuts")
		try:
			selectedItem = 0 if conf["shortcuts"] == '?' else listTablesFileName(
				listUncontractedInputTables
			).index(conf["shortcuts"]) + 1
		except ValueError:
			selectedItem = 0
		self.inputTableShortcuts = sHelper.addLabeledControl(label, wx.Choice, choices=[
			currentTableLabel] + listTablesDisplayName(listUncontractedInputTables))
		self.inputTableShortcuts.SetSelection(selectedItem)

		self.tablesGroupBtn = bHelper1.addButton(
			self, wx.NewId(), "%s..." % _("Table &groups"), wx.DefaultPosition)
		self.tablesGroupBtn.Bind(wx.EVT_BUTTON, self.onTableGroupsBtn)

		self.customBrailleTablesBtn = bHelper1.addButton(self, wx.NewId(), "%s..." % _(
			"Alternative and &custom braille tables"), wx.DefaultPosition)
		self.customBrailleTablesBtn.Bind(
			wx.EVT_BUTTON, self.onCustomBrailleTablesBtn)

		# Translators: label of a dialog.
		self.tabSpace = sHelper.addItem(wx.CheckBox(
			self, label=_("Display &tab signs as spaces")))
		self.tabSpace.SetValue(config.conf["brailleExtender"]["tabSpace"])
		self.tabSpace.Bind(wx.EVT_CHECKBOX, self.onTabSpace)

		# Translators: label of a dialog.
		self.tabSize = sHelper.addLabeledControl(_("Number of &space for a tab sign")+" "+_("for the currrent braille display"),
												 gui.nvdaControls.SelectOnFocusSpinCtrl, min=1, max=42, initial=int(config.conf["brailleExtender"]["tabSize_%s" % configBE.curBD]))
		sHelper.addItem(bHelper1)
		self.onTabSpace()

	def onTabSpace(self, evt=None):
		if self.tabSpace.IsChecked():
			self.tabSize.Enable()
		else:
			self.tabSize.Disable()

	def onTableGroupsBtn(self, evt):
		tableGroupsDlg = TableGroupsDlg(self, multiInstanceAllowed=True)
		tableGroupsDlg.ShowModal()

	def onCustomBrailleTablesBtn(self, evt):
		customBrailleTablesDlg = CustomBrailleTablesDlg(
			self, multiInstanceAllowed=True)
		customBrailleTablesDlg.ShowModal()

	def postInit(self): self.tables.SetFocus()

	def isValid(self):
		if self.tabSize.Value > 42:
			gui.messageBox(
				_("Tab size is invalid"),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				self
			)
			self.tabSize.SetFocus()
			return False
		return super().isValid()

	def onSave(self):
		inputTables = '|'.join(getTablesFilenameByID(
			self.inputTables.CheckedItems,
			listInputTables()
		))
		outputTables = '|'.join(
			getTablesFilenameByID(
				self.outputTables.CheckedItems,
				listOutputTables()
			)
		)
		tablesShortcuts = getTablesFilenameByID(
			[self.inputTableShortcuts.GetSelection()-1],
			listUncontractedInputTables
		)[0] if self.inputTableShortcuts.GetSelection() > 0 else '?'
		conf["preferredInput"] = inputTables
		conf["preferredOutput"] = outputTables
		conf["shortcuts"] = tablesShortcuts
		config.conf["brailleExtender"]["tabSpace"] = self.tabSpace.IsChecked()
		config.conf["brailleExtender"][f"tabSize_{configBE.curBD}"] = self.tabSize.Value

	def postSave(self):
		pass #initializePreferredTables()


class TableGroupsDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = f"{addonName} - %s" % _("table groups")

	def makeSettings(self, settingsSizer):
		self.tmpGroups = getGroups()
		self.tmpGroups.sort(key=lambda e: e.name)
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		groupsLabelText = _("List of table groups")
		self.groupsList = sHelper.addLabeledControl(
			groupsLabelText, wx.ListCtrl, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=(550, 350))
		self.groupsList.InsertColumn(0, _("Name"), width=150)
		self.groupsList.InsertColumn(1, _("Members"), width=150)
		self.groupsList.InsertColumn(2, _("Usable in"), width=150)
		self.onSetEntries()

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table groups dialog to add new entries.
			label=_("&Add")
		).Bind(wx.EVT_BUTTON, self.onAddClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table groups dialog to edit existing entries.
			label=_("&Edit")
		).Bind(wx.EVT_BUTTON, self.onEditClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table groups dialog to remove existing entries.
			label=_("Re&move")
		).Bind(wx.EVT_BUTTON, self.onRemoveClick)

		sHelper.addItem(bHelper)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table groups dialog to open table groups file in an editor.
			label=_("&Open the table groups file in an editor")
		).Bind(wx.EVT_BUTTON, self.onOpenFileClick)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in table groups dialog to reload table groups.
			label=_("&Reload table groups")
		).Bind(wx.EVT_BUTTON, self.onReloadClick)
		sHelper.addItem(bHelper)

	def postInit(self):
		self.groupsList.SetFocus()

	def onSetEntries(self, evt=None):
		self.groupsList.DeleteAllItems()
		for group in self.tmpGroups:
			self.groupsList.Append((
				group.name,
				", ".join(fileName2displayName(group.members)),
				translateUsableIn(group.usableIn)
			))

	def onAddClick(self, event):
		entryDialog = GroupEntryDlg(self, title=_("Add group entry"))
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.groupEntry
			self.tmpGroups.append(entry)
			self.groupsList.Append(
				(entry.name, ", ".join(fileName2displayName(entry.members)),
				 translateUsableIn(entry.usableIn))
			)
			index = self.groupsList.GetFirstSelected()
			while index >= 0:
				self.groupsList.Select(index, on=0)
				index = self.groupsList.GetNextSelected(index)
			addedIndex = self.groupsList.GetItemCount() - 1
			self.groupsList.Select(addedIndex)
			self.groupsList.Focus(addedIndex)
			self.groupsList.SetFocus()
		entryDialog.Destroy()

	def onEditClick(self, event):
		if self.groupsList.GetSelectedItemCount() != 1:
			return
		editIndex = self.groupsList.GetFirstSelected()
		entryDialog = GroupEntryDlg(self)
		entryDialog.name.SetValue(self.tmpGroups[editIndex].name)
		entryDialog.members.CheckedItems = listTablesIndexes(
			self.tmpGroups[editIndex].members, listUncontractedInputTables)
		entryDialog.refreshOrders()
		selectedItem = 0
		try:
			selectedItem = list(entryDialog.orderPermutations.keys()).index(tuple(
				listTablesIndexes(self.tmpGroups[editIndex].members, listUncontractedTables())))
			entryDialog.order.SetSelection(selectedItem)
		except ValueError:
			pass
		entryDialog.usableIn.CheckedItems = translateUsableInIndexes(
			self.tmpGroups[editIndex].usableIn)
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.groupEntry
			self.tmpGroups[editIndex] = entry
			self.groupsList.SetItem(editIndex, 0, entry.name)
			self.groupsList.SetItem(editIndex, 1, ", ".join(
				fileName2displayName(entry.members)))
			self.groupsList.SetItem(
				editIndex, 2, translateUsableIn(entry.usableIn))
			self.groupsList.SetFocus()
			entryDialog.Destroy()

	def onRemoveClick(self, event):
		index = self.groupsList.GetFirstSelected()
		while index >= 0:
			self.groupsList.DeleteItem(index)
			del self.tmpGroups[index]
			index = self.groupsList.GetNextSelected(index)
		self.onSetEntries()
		self.groupsList.SetFocus()

	def onOpenFileClick(self, evt):
		path = getPathGroups()
		if not os.path.exists(path):
			return
		try:
			os.startfile(path)
		except OSError:
			os.popen(f"notepad \"{path}\"")

	def onReloadClick(self, evt):
		self.tmpGroups = getGroups()
		self.onSetEntries()

	def onOk(self, evt):
		saveGroups(self.tmpGroups)
		setDict(self.tmpGroups)
		super().onOk(evt)


class GroupEntryDlg(wx.Dialog):

	orderPermutations = {}

	def __init__(self, parent=None, title=_("Edit Dictionary Entry")):
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		self.name = sHelper.addLabeledControl(_("Group &name"), wx.TextCtrl)
		label = _("Group &members")
		self.members = sHelper.addLabeledControl(
			label, gui.nvdaControls.CustomCheckListBox, choices=listTablesDisplayName(listUncontractedTables()))
		self.members.SetSelection(0)
		self.members.Bind(wx.EVT_CHECKLISTBOX, lambda s: self.refreshOrders())
		label = _("Table &order")
		self.order = sHelper.addLabeledControl(
			label, wx.Choice, choices=[])
		self.refreshOrders()
		label = _("&Usable in")
		choices = list(USABLE_LIST_LABELS.values())
		self.usableIn = sHelper.addItem(wx.RadioBox(self,
			label=label, choices=choices))
		self.usableIn.SetSelection(1)
		sHelper.addDialogDismissButtons(
			self.CreateButtonSizer(wx.OK | wx.CANCEL))
		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)
		self.name.SetFocus()

	def refreshOrders(self, evt=None):
		tables = listUncontractedTables()
		self.orderPermutations = {e: fileName2displayName(getTablesFilenameByID(
			e, tables)) for e in permutations(self.members.CheckedItems) if e}
		self.order.SetItems([", ".join(e)
							 for e in self.orderPermutations.values()])
		self.order.SetSelection(0)

	def onOk(self, evt):
		name = self.name.Value
		if not self.orderPermutations:
			return
		members = getTablesFilenameByID(list(self.orderPermutations.keys())[
			self.order.GetSelection()], listUncontractedTables())
		matches = ['i', 'o']
		usableIn = ''.join([matches[e] for e in self.usableIn.CheckedItems])
		if not name:
			gui.messageBox(
				_("Please specify a group name"),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				self
			)
			return self.name.SetFocus()
		if len(members) < 2:
			gui.messageBox(
				_("Please select at least 2 tables"),
				_("Error"),
				wx.OK | wx.ICON_ERROR,
				self
			)
			return self.members.SetFocus()
		self.groupEntry = GroupTables(name, members, usableIn)
		evt.Skip()


class CustomBrailleTablesDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = f"{addonName} - %s" % _("Custom braille tables")
	providedTablesPath = "%s/res/json" % baseDir
	userTablesPath = "%s/json" % configDir

	def makeSettings(self, settingsSizer):
		self.providedTables = self.getBrailleTablesFromJSON(
			self.providedTablesPath)
		self.userTables = self.getBrailleTablesFromJSON(self.userTablesPath)
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.inTable = sHelper.addItem(wx.CheckBox(
			self, label=_("Use a custom table as input table")))
		self.outTable = sHelper.addItem(wx.CheckBox(
			self, label=_("Use a custom table as output table")))
		self.addBrailleTablesBtn = bHelper1.addButton(
			self, wx.NewId(), "%s..." % _("&Add a braille table"), wx.DefaultPosition)
		self.addBrailleTablesBtn.Bind(
			wx.EVT_BUTTON, self.onAddBrailleTablesBtn)
		sHelper.addItem(bHelper1)

	@staticmethod
	def getBrailleTablesFromJSON(path):
		if not os.path.exists(path):
			path = "%s/%s" % (baseDir, path)
			if not os.path.exists(path):
				return {}
		f = open(path)
		return json.load(f)

	def onAddBrailleTablesBtn(self, evt):
		addBrailleTablesDlg = AddBrailleTablesDlg(
			self, multiInstanceAllowed=True)
		addBrailleTablesDlg.ShowModal()

	def postInit(self): self.inTable.SetFocus()

	def onOk(self, event):
		super().onOk(evt)


class AddBrailleTablesDlg(gui.settingsDialogs.SettingsDialog):
	# Translators: title of a dialog.
	title = "Braille Extender - %s" % _("Add a braille table")
	tbl = []

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		bHelper1 = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.name = sHelper.addLabeledControl(_("Display name"), wx.TextCtrl)
		self.description = sHelper.addLabeledControl(
			_("Description"), wx.TextCtrl, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER, size=(360, 90), pos=(-1, -1))
		self.path = sHelper.addLabeledControl(_("Path"), wx.TextCtrl)
		self.browseBtn = bHelper1.addButton(
			self, wx.NewId(), "%s..." % _("&Browse"), wx.DefaultPosition)
		self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowseBtn)
		sHelper.addItem(bHelper1)
		self.isContracted = sHelper.addItem(wx.CheckBox(
			self, label=_("Contracted (grade 2) braille table")))
		# Translators: label of a dialog.
		self.inputOrOutput = sHelper.addLabeledControl(_("Available for"), wx.Choice, choices=[
			_("Input and output"), _("Input only"), _("Output only")])
		self.inputOrOutput.SetSelection(0)

	def postInit(self): self.name.SetFocus()

	def onBrowseBtn(self, event):
		dlg = wx.FileDialog(None, _("Choose a table file"), "%PROGRAMFILES%", "", "%s (*.ctb, *.cti, *.utb, *.uti)|*.ctb;*.cti;*.utb;*.uti" %
							_("Liblouis table files"), style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return self.path.SetFocus()
		self.path.SetValue(dlg.GetDirectory() + '\\' + dlg.GetFilename())
		dlg.Destroy()
		self.path.SetFocus()

	def onOk(self, event):
		path = self.path.GetValue().strip().encode("UTF-8")
		displayName = self.name.GetValue().strip()
		if not displayName:
			gui.messageBox(_("Please specify a display name."), _(
				"Invalid display name"), wx.OK | wx.ICON_ERROR)
			self.name.SetFocus()
			return
		if not os.path.exists(path.decode("UTF-8").encode("mbcs")):
			gui.messageBox(_("The specified path is not valid (%s).") % path.decode(
				"UTF-8"), _("Invalid path"), wx.OK | wx.ICON_ERROR)
			self.path.SetFocus()
			return
		switch_possibleValues = ["both", "input", "output"]
		v = "%s|%s|%s|%s" % (
			switch_possibleValues[self.inputOrOutput.GetSelection()],
			self.isContracted.IsChecked(), path.decode("UTF-8"), displayName
		)
		k = hashlib.md5(path).hexdigest()[:15]
		config.conf["brailleExtender"]["brailleTables"][k] = v
		super().onOk(evt)

	@staticmethod
	def getAvailableBrailleTables():
		out = []
		brailleTablesDir = configBE.TABLES_DIR
		ls = glob.glob(brailleTablesDir+'\\*.ctb')+glob.glob(brailleTablesDir +
															 '\\*.cti')+glob.glob(brailleTablesDir+'\\*.utb')
		for i, e in enumerate(ls):
			e = str(e.split('\\')[-1])
			if e in configBE.tablesFN or e.lower() in configBE.tablesFN:
				del ls[i]
			else:
				out.append(e.lower())
		out = sorted(out)
		return out
