# coding: utf-8
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2019 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import gui
import wx
from logHandler import log
import brailleTables
import config

class Converter(gui.settingsDialogs.SettingsDialog):

	title = "Braille converter"
	tables = brailleTables.listTables()
	tablesFN = [table.fileName for table in tables if table.output]

	def makeSettings(self, sizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=sizer)
		label = _("&Source type")
		choices = [
			"BRF",
			"Braille Unicode",
			"Dot patterns",
			"Normal text"
		]
		self.sourceType = sHelper.addItem(wx.RadioBox(self, label=label, choices=choices))
		label = _("&Target type")
		self.targetType = sHelper.addItem(wx.RadioBox(self, label=label, choices=choices))
		self.sourceType.Bind(wx.EVT_RADIOBOX , self.onTypes)
		self.targetType.Bind(wx.EVT_RADIOBOX , self.onTypes)
		label = _("Braille table")
		choices = [table.displayName for table in self.tables if table.output]
		self.brailleTable = sHelper.addLabeledControl(label, wx.Choice, choices=choices)
		self.onTypes()

	def onTypes(self, evt=None):
		if self.sourceType.GetSelection() == 3 or self.targetType.GetSelection() == 3:
			self.brailleTable.Enable()
			toSelect = self.tablesFN.index(config.conf["braille"]["translationTable"])
			self.brailleTable.SetSelection(toSelect)
		else:
			self.brailleTable.Disable()
