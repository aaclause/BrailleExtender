# coding: utf-8
# advancedInputMode.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.
import codecs
import json
from collections import namedtuple

import wx

import addonHandler
import brailleInput
import brailleTables
import config
import gui

from .common import *
from .utils import getTextInBraille

addonHandler.initTranslation()

AdvancedInputModeDictEntry = namedtuple(
	"AdvancedInputModeDictEntry", ("abreviation", "replaceBy", "table")
)

entries = None


def getPathDict():
	return f"{configDir}/brailleDicts/advancedInputMode.json"


def getDictionary():
	return entries if entries else []


def initialize():
	global entries
	entries = []
	fp = getPathDict()
	if not os.path.exists(fp):
		return
	json_ = json.load(codecs.open(fp, "r", "UTF-8"))
	for entry in json_:
		entries.append(
			AdvancedInputModeDictEntry(
				entry["abreviation"], entry["replaceBy"], entry["table"]
			)
		)


def terminate(save=False):
	global entries
	if save:
		saveDict()
	entries = None


def setDict(newDict):
	global entries
	entries = newDict


def saveDict(entries=None):
	if not entries:
		entries = getDictionary()
	entries = [
		{
			"abreviation": entry.abreviation,
			"replaceBy": entry.replaceBy,
			"table": entry.table,
		}
		for entry in entries
	]
	with codecs.open(getPathDict(), "w", "UTF-8") as outfile:
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
				for entry in getDictionary()
				if entry.abreviation.startswith(abreviation)
				and entry.table in [currentInputTable, "*"]
			]
		else:
			out += [
				entry
				for entry in getDictionary()
				if entry.abreviation == abreviation
				and entry.table in [currentInputTable, "*"]
			]
	return out


def translateTable(tableFilename):
	if tableFilename == "*":
		return _("all tables")
	else:
		for table in brailleTables.listTables():
			if table.fileName == tableFilename:
				return table.displayName
	return tableFilename


class AdvancedInputModeDlg(gui.settingsDialogs.SettingsDialog):

	# Translators: title of a dialog.
	title = _("Advanced input mode dictionary")

	def makeSettings(self, settingsSizer):
		self.tmpDict = getDictionary()
		self.tmpDict.sort(key=lambda e: e.replaceBy)
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		# Translators: The label for the combo box of dictionary entries in advanced input mode dictionary dialog.
		entriesLabelText = _("Dictionary &entries")
		self.dictList = sHelper.addLabeledControl(
			entriesLabelText,
			wx.ListCtrl,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
			size=(550, 350),
		)
		# Translators: The label for a column in dictionary entries list used to identify comments for the entry.
		self.dictList.InsertColumn(0, _("Abbreviation"), width=150)
		self.dictList.InsertColumn(1, _("Replace by"), width=150)
		self.dictList.InsertColumn(2, _("Input table"), width=150)
		self.onSetEntries()
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode dictionariy dialog to add new entries.
			label=_("&Add"),
		).Bind(wx.EVT_BUTTON, self.onAddClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode dictionariy dialog to edit existing entries.
			label=_("&Edit"),
		).Bind(wx.EVT_BUTTON, self.onEditClick)

		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode dictionariy dialog to remove existing entries.
			label=_("Re&move"),
		).Bind(wx.EVT_BUTTON, self.onRemoveClick)

		sHelper.addItem(bHelper)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode dictionariy dialog to open dictionary file in an editor.
			label=_("&Open the dictionary file in an editor"),
		).Bind(wx.EVT_BUTTON, self.onOpenFileClick)
		bHelper.addButton(
			parent=self,
			# Translators: The label for a button in advanced input mode dictionariy dialog to reload dictionary.
			label=_("&Reload the dictionary"),
		).Bind(wx.EVT_BUTTON, self.onReloadDictClick)
		sHelper.addItem(bHelper)

	def onSetEntries(self):
		self.dictList.DeleteAllItems()
		for entry in self.tmpDict:
			self.dictList.Append(
				(entry.abreviation, entry.replaceBy, translateTable(entry.table))
			)
		self.dictList.SetFocus()

	def onAddClick(self, event):
		entryDialog = DictionaryEntryDlg(self, title=_("Add Dictionary Entry"))
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			self.tmpDict.append(entry)
			self.dictList.Append(
				(entry.abreviation, entry.replaceBy, translateTable(entry.table))
			)
			index = self.dictList.GetFirstSelected()
			while index >= 0:
				self.dictList.Select(index, on=0)
				index = self.dictList.GetNextSelected(index)
			addedIndex = self.dictList.GetItemCount() - 1
			self.dictList.Select(addedIndex)
			self.dictList.Focus(addedIndex)
			self.dictList.SetFocus()
		entryDialog.Destroy()

	def onEditClick(self, event):
		if self.dictList.GetSelectedItemCount() != 1:
			return
		editIndex = self.dictList.GetFirstSelected()
		entryDialog = DictionaryEntryDlg(self)
		entryDialog.abreviationTextCtrl.SetValue(
			self.tmpDict[editIndex].abreviation)
		entryDialog.replaceByTextCtrl.SetValue(
			self.tmpDict[editIndex].replaceBy)
		if entryDialog.ShowModal() == wx.ID_OK:
			entry = entryDialog.dictEntry
			self.tmpDict[editIndex] = entry
			self.dictList.SetItem(editIndex, 0, entry.abreviation)
			self.dictList.SetItem(editIndex, 1, entry.replaceBy)
			self.dictList.SetItem(editIndex, 2, translateTable(entry.table))
			self.dictList.SetFocus()
			entryDialog.Destroy()

	def onRemoveClick(self, event):
		index = self.dictList.GetFirstSelected()
		while index >= 0:
			self.dictList.DeleteItem(index)
			del self.tmpDict[index]
			index = self.dictList.GetNextSelected(index)
		self.dictList.SetFocus()

	def onOpenFileClick(self, event):
		dictPath = getPathDict()
		if not os.path.exists(dictPath):
			return ui.message(_("File doesn't exist yet"))
		try:
			os.startfile(dictPath)
		except OSError:
			os.popen('notepad "%s"' % dictPath)

	def onReloadDictClick(self, event):
		self.tmpDict = getDictionary()
		self.onSetEntries()

	def postInit(self):
		self.dictList.SetFocus()

	def onOk(self, evt):
		saveDict(self.tmpDict)
		setDict(self.tmpDict)
		super(AdvancedInputModeDlg, self).onOk(evt)


class DictionaryEntryDlg(wx.Dialog):
	# Translators: This is the label for the edit dictionary entry dialog.
	def __init__(self, parent=None, title=_("Edit Dictionary Entry")):
		super(DictionaryEntryDlg, self).__init__(parent, title=title)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
		# Translators: This is a label for an edit field in add dictionary entry dialog.
		abreviationLabelText = _("&Abreviation")
		self.abreviationTextCtrl = sHelper.addLabeledControl(
			abreviationLabelText, wx.TextCtrl
		)
		# Translators: This is a label for an edit field in add dictionary entry dialog.
		replaceByLabelText = _("&Replace by")
		self.replaceByTextCtrl = sHelper.addLabeledControl(
			replaceByLabelText, wx.TextCtrl
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
		replaceBy = self.replaceByTextCtrl.GetValue()
		newEntry = AdvancedInputModeDictEntry(abreviation, replaceBy, "*")
		self.dictEntry = newEntry
		evt.Skip()


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Advanced input mode")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: label of a dialog.
		self.stopAdvancedInputModeAfterOneChar = sHelper.addItem(
			wx.CheckBox(
				self, label=_(
					"E&xit the advanced input mode after typing one pattern")
			)
		)
		self.stopAdvancedInputModeAfterOneChar.SetValue(
			config.conf["brailleExtender"]["advancedInputMode"]["stopAfterOneChar"]
		)
		self.escapeSignUnicodeValue = sHelper.addLabeledControl(
			_("Escape sign for Unicode values"),
			wx.TextCtrl,
			value=config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"],
		)

	def onSave(self):
		config.conf["brailleExtender"]["advancedInputMode"]["stopAfterOneChar"] = self.stopAdvancedInputModeAfterOneChar.IsChecked()
		s = self.escapeSignUnicodeValue.Value
		if s:
			config.conf["brailleExtender"]["advancedInputMode"]["escapeSignUnicodeValue"] = getTextInBraille(
				s[0])
