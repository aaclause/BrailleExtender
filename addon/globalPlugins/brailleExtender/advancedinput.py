# advancedinput.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2021 André-Abush CLAUSE, released under GPL.
import codecs
import json
import os
from copy import deepcopy
from logHandler import log

import addonHandler
import brailleInput
import brailleTables
import config
import gui
import ui
import wx

from .common import configDir
from .utils import getTextInBraille

addonHandler.initTranslation()

PATH_DICT = os.path.join(configDir, "advancedInputMode.json")


class AdvancedInputDictEntry:

	def __init__(self, abreviation: str, replacement: str, table: str):
		self.abreviation = abreviation
		self.replacement = replacement
		self.table = table

	@property
	def abreviation(self):
		return self._abreviation

	@abreviation.setter
	def abreviation(self, abreviation):
		self._abreviation = abreviation

	@property
	def replacement(self):
		return self._replacement

	@replacement.setter
	def replacement(self, replacement):
		self._replacement = replacement

	@property
	def table(self):
		return self._table

	@table.setter
	def table(self, table):
		self._table = table

	def __repr__(self):
		return '(abreviation="{abreviation}", replacement="{replacement}", table="{table}")'.format(
			abreviation=self.abreviation, replacement=self.replacement, table=self.table)


class AdvancedInputDict:

	def __init__(self, entries=None):
		self.entries = []
		if entries:
			self.update(entries)

	def update(self, entries):
		for entry in entries:
			self._addEntry(entry)

	def _addEntry(self, entry):
		if isinstance(entry, dict):
			entryDict = AdvancedInputDictEntry(
				entry["abreviation"], entry["replaceBy"], entry["table"]
			)
		elif isinstance(entry, AdvancedInputDictEntry):
			entryDict = entry
		else:
			log.error("wrong type")
		self.addEntry(entryDict)

	def addEntry(self, newEntry):
		if not isinstance(newEntry, AdvancedInputDictEntry):
			raise TypeError("newEntry: wrong type")
		for i, entry in enumerate(self.entries):
			if newEntry.abreviation == entry.abreviation and newEntry.table == entry.table:
				entry.abreviation = newEntry.abreviation
				entry.replacement = newEntry.replacement
				entry.table = newEntry.table
				return i
		self.entries.append(newEntry)
		self.sort()
		return self.entries.index(newEntry)

	def editEntry(self, editIndex, entry):
		self.entries[editIndex] = entry

	def removeEntry(self, entry):
		del self.entries[entry]

	def sort(self):
		self.entries = sorted(self.entries, key=lambda e: e.replacement)

	def getEntries(self):
		return self.entries

	def terminate(self):
		del self.entries
		del self


advancedInputDictHandler = None


def initialize():
	global advancedInputDictHandler
	advancedInputDictHandler = AdvancedInputDict()
	if not os.path.exists(PATH_DICT):
		return
	json_ = json.load(codecs.open(PATH_DICT, "r", "UTF-8"))
	advancedInputDictHandler.update(json_)


def terminate(save=False):
	global advancedInputDictHandler
	if save:
		saveDict(advancedInputDictHandler)
	advancedInputDictHandler.terminate()
	advancedInputDictHandler = None


def saveDict(dictToSave, fp=None):
	entries = [
		{
			"abreviation": entry.abreviation,
			"replacement": entry.replacement,
			"table": entry.table,
		}
		for entry in dictToSave.getEntries()
	]
	if not fp:
		fp = PATH_DICT
	with codecs.open(fp, "w", "UTF-8") as outfile:
		json.dump(entries, outfile, ensure_ascii=False, indent=2)


def getReplacements(abreviations, strict=False):
	if isinstance(abreviations, str):
		abreviations = [abreviations]
	currentInputTable = brailleInput.handler.table.fileName
	out = []
	for abreviation in abreviations:
		if abreviation.endswith("⠀"):
			strict = True
			abreviation = abreviation[:-1]
		if not strict:
			out += [
				entry
				for entry in advancedInputDictHandler.getEntries()
				if entry.abreviation.startswith(abreviation)
				and entry.table in [currentInputTable, "*"]
			]
		else:
			out += [
				entry
				for entry in advancedInputDictHandler.getEntries()
				if entry.abreviation == abreviation
				and entry.table in [currentInputTable, "*"]
			]
	return out


def translateTable(tableFilename):
	if tableFilename == "*":
		return _("all tables")
	for table in brailleTables.listTables():
		if table.fileName == tableFilename:
			return table.displayName
	return tableFilename


class AdvancedInputModeDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = _("Advanced input mode dictionary")

	def makeSettings(self, settingsSizer):
		self.backupDict = deepcopy(advancedInputDictHandler)
		self.curDict = advancedInputDictHandler
		self.curDict.sort()
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: The label for the combo box of dictionary entries in
		# advanced input mode dictionary dialog.
		entriesLabelText = _("Dictionary &entries")
		self.dictList = sHelper.addLabeledControl(
			entriesLabelText,
			wx.ListCtrl,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
			size=(550, 350),
		)
		# Translators: The label for a column in dictionary entries list used
		# to identify comments for the entry.
		self.dictList.InsertColumn(0, _("Replacement"), width=150)
		self.dictList.InsertColumn(1, _("Input"), width=150)
		self.dictList.InsertColumn(2, _("Input table"), width=150)
		self.onSetEntries()
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to add new entries.
			label=_("&Add"),
		).Bind(wx.EVT_BUTTON, self.onAddClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to edit existing entries.
			label=_("&Edit"),
		).Bind(wx.EVT_BUTTON, self.onEditClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to remove existing entries.
			label=_("Re&move"),
		).Bind(wx.EVT_BUTTON, self.onRemoveClick)

		sHelper.addItem(bHelper)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to save entries.
			label=_("&Save"),
		).Bind(wx.EVT_BUTTON, self.onSaveClick)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to open dictionary file in an editor.
			label=_("&Open the dictionary file in an editor"),
		).Bind(wx.EVT_BUTTON, self.onOpenFileClick)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode
			# dictionariy dialog to reload dictionary.
			label=_("&Reload the dictionary"),
		).Bind(wx.EVT_BUTTON, self.onReloadDictClick)
		sHelper.addItem(bHelper)

	def onSetEntries(self):
		self.dictList.DeleteAllItems()
		for entry in self.curDict.getEntries():
			self.dictList.Append(
				(entry.replacement,
				 entry.abreviation,
				 translateTable(
					 entry.table)))
		self.dictList.SetFocus()

	def onAddClick(self, event):
		entryDialog = DictionaryEntryDlg(self, title=_("Add Dictionary Entry"))
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			addIndex = self.curDict.addEntry(entry)
			self.onSetEntries()
			self.dictList.Focus(addIndex)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def onEditClick(self, event):
		if self.dictList.GetSelectedItemCount() != 1:
			return
		editIndex = self.dictList.GetFirstSelected()
		entry = self.curDict.getEntries()[editIndex]
		entryDialog = DictionaryEntryDlg(self)
		entryDialog.abreviationTextCtrl.SetValue(entry.abreviation)
		entryDialog.replacementTextCtrl.SetValue(entry.replacement)
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			self.curDict.editEntry(editIndex, entry)
			self.onSetEntries()
			self.dictList.Focus(editIndex)
			entryDialog.Destroy()

	def onRemoveClick(self, event):
		deleteIndex = self.dictList.GetFirstSelected()
		while deleteIndex >= 0:
			self.dictList.DeleteItem(deleteIndex)
			self.curDict.removeEntry(deleteIndex)
			deleteIndex = self.dictList.GetNextSelected(deleteIndex)
		self.dictList.SetFocus()

	def onSaveClick(self, evt):
		saveDict(self.curDict)
		self.dictList.SetFocus()

	def onOpenFileClick(self, event):
		if not os.path.exists(PATH_DICT):
			return ui.message(_("File doesn't exist yet"))
		try:
			os.startfile(PATH_DICT)
		except OSError:
			os.popen('notepad "%s"' % dictPath)

	def onReloadDictClick(self, event):
		self.curDict.terminate()
		initialize()
		self.curDict = advancedInputDictHandler
		self.onSetEntries()

	def postInit(self):
		self.dictList.SetFocus()

	def onOk(self, evt):
		saveDict(self.curDict)
		super().onOk(evt)

	def onCancel(self, evt):
		global advancedInputDictHandler
		advancedInputDictHandler = self.backupDict
		super().onCancel(evt)


class DictionaryEntryDlg(wx.Dialog):

	# Translators: This is the label for the edit dictionary entry dialog.
	def __init__(self, parent=None, title=_("Edit Dictionary Entry")):
		super().__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		# Translators: This is a label for an edit field in add dictionary
		# entry dialog.
		abreviationLabelText = _("&Abreviation")
		self.abreviationTextCtrl = sHelper.addLabeledControl(
			abreviationLabelText, wx.TextCtrl
		)
		# Translators: This is a label for an edit field in add dictionary
		# entry dialog.
		replacementLabelText = _("&Replace by")
		self.replacementTextCtrl = sHelper.addLabeledControl(
			replacementLabelText, wx.TextCtrl
		)

		sHelper.addDialogDismissButtons(
			self.CreateButtonSizer(wx.OK | wx.CANCEL))

		mainSizer.Add(sHelper.sizer, border=20, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)
		self.abreviationTextCtrl.SetFocus()
		self.Bind(wx.EVT_BUTTON, self.onOk, id=wx.ID_OK)

	def onOk(self, evt):
		abreviation = getTextInBraille(self.abreviationTextCtrl.GetValue())
		replacement = self.replacementTextCtrl.GetValue()
		newEntry = AdvancedInputDictEntry(abreviation, replacement, "*")
		self.dictEntry = newEntry
		evt.Skip()


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Advanced input mode")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: label of a dialog.
		self.stopAdvancedInputModeAfterOneChar = sHelper.addItem(wx.CheckBox(
			self, label=_("E&xit the advanced input mode after typing one pattern")))
		self.stopAdvancedInputModeAfterOneChar.SetValue(
			config.conf["brailleExtender"]["advancedInputMode"]["stopAfterOneChar"])
		self.escapeSignUnicodeValue = sHelper.addLabeledControl(
			_("&Escape character for Unicode values input"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["advancedInputMode"]
			["escapeSignUnicodeValue"],)

	def onSave(self):
		config.conf["brailleExtender"]["advancedInputMode"]["stopAfterOneChar"] = self.stopAdvancedInputModeAfterOneChar.IsChecked()
		s = self.escapeSignUnicodeValue.Value
		if s:
			config.conf["brailleExtender"]["advancedInputMode"][
				"escapeSignUnicodeValue"] = getTextInBraille(s[0])
