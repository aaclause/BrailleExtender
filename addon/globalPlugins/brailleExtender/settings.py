# coding: utf-8
# settings.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
import re
import wx
import gui

import addonHandler
import braille
import brailleTables
import controlTypes
import core
import inputCore
import scriptHandler
import ui
addonHandler.initTranslation()
from logHandler import log
import configBE
import queueHandler
lastCaptured = None
tables = brailleTables.listTables()
restartNVDA_ = False

instanceGP = None

class Settings(wx.Dialog):
	def __init__(self):
		if instanceGP.instanceST is not None or instanceGP is None:
			return
		instanceGP.instanceST = self
		wx.Dialog.__init__(self, None, title=_('BrailleExtender settings'))
		configBE.loadConfAttribra()
		self.p = wx.Panel(self)
		self.nb = wx.Notebook(self.p)
		self.general = General(self.nb)
		self.reading = Reading(self.nb)
		self.keyboard = Keyboard(self.nb)
		self.attribra = Attribra(self.nb)
		if configBE.curBD != 'noBraille':
			self.quickLaunch = QuickLaunch(self.nb)
		self.nb.AddPage(self.general, _("General"))
		self.nb.AddPage(self.reading, _("Reading and display"))
		self.nb.AddPage(self.attribra, _("Attribra"))
		self.nb.AddPage(self.keyboard, _("Braille keyboard"))
		if configBE.curBD != 'noBraille':
			self.nb.AddPage(self.quickLaunch, _("Quick launches"))
		self.sizer = wx.BoxSizer()
		self.sizer.Add(self.nb, 1, wx.EXPAND)
		self.p.SetSizer(self.sizer)
		self.buttonOK = wx.Button(self, label=_('OK'))
		self.buttonS = wx.Button(self, label=_('Appl&y'))
		self.buttonC = wx.Button(self, label=_('Close'), id=wx.ID_CLOSE)
		self.buttonOK.Bind(wx.EVT_BUTTON, self.onOK)
		self.buttonS.Bind(wx.EVT_BUTTON, self.onSave)
		self.buttonC.Bind(wx.EVT_BUTTON, self.onClose)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.EscapeId = wx.ID_CLOSE
		self.Show()
		return

	def onOK(self, evt):
		self.onSave(None)
		self.onClose(None)

	def onSave(self, evt):
		postTableID = self.reading.postTable.GetSelection()
		postTable = "None" if postTableID == 0 else configBE.tablesFN[postTableID]
		restartNVDA = False if not restartNVDA_ else True
		if ((self.reading.tabSpace.GetValue() or postTable != "None")
				and not configBE.conf["patch"]["updateBraille"]):
			log.info("Enabling patch for update braille function")
			configBE.conf["patch"]["updateBraille"] = True
			restartNVDA = True
		if (self.reading.speakScroll.GetValue() and not configBE.conf["patch"]["scrollBraille"]):
			log.info("Enabling patch for scroll braille functions")
			configBE.conf["patch"]["scrollBraille"] = True
			restartNVDA = True
		if (not restartNVDA and (configBE.conf['general']['tabSize'] != int(self.reading.tabSize.GetValue()) or
								 configBE.conf['general']['tabSpace'] != self.reading.tabSpace.GetValue() or
								 configBE.conf['general']['postTable'] != postTable or
								 (configBE.gesturesFileExists and configBE.conf['general']['keyboardLayout_%s' % configBE.curBD] != configBE.iniProfile['keyboardLayouts'].keys()[self.keyboard.KBMode.GetSelection()]))):
			restartNVDA = True
		configBE.conf['general']['postTable'] = postTable
		configBE.conf['general']['autoCheckUpdate'] = self.general.autoCheckUpdate.GetValue()
		configBE.conf['general']['showConstructST'] = self.general.assistS.GetValue()
		configBE.conf['general']['reportVolumeBraille'] = self.general.reportVolumeBraille.GetValue()
		configBE.conf['general']['reportVolumeSpeech'] = self.general.reportVolumeSpeech.GetValue()
		configBE.conf['general']['hourDynamic'] = self.general.hourDynamic.GetValue()
		if configBE.conf['general']['reverseScroll'] != self.reading.reverseScroll.GetValue(
		):
			if self.reading.reverseScroll.GetValue():
				instanceGP.reverseScrollBtns()
			else:
				instanceGP.reverseScrollBtns(None, True)
			configBE.conf['general']['reverseScroll'] = self.reading.reverseScroll.GetValue()
		configBE.conf['general']['delayScroll_' + configBE.curBD] = self.reading.delayScroll.GetValue()
		try:
			if int(self.general.limitCells.GetValue()) > configBE.backupDisplaySize or int(self.general.limitCells.GetValue()) < 0:
				configBE.conf['general']['limitCells_' + configBE.curBD] = 0
			else:
				if configBE.conf['general']['limitCells_' + configBE.curBD] != 0 and int(self.general.limitCells.GetValue()) == 0: braille.handler.displaySize = configBE.backupDisplaySize
				configBE.conf['general']['limitCells_' + configBE.curBD] = int(self.general.limitCells.GetValue())
		except BaseException:
			configBE.conf['general']['limitCells_' + configBE.curBD] = 0
		configBE.conf['general']['smartDelayScroll'] = self.reading.smartDelayScroll.GetValue()
		configBE.conf['general']['speakScroll'] = self.reading.speakScroll.GetValue()
		configBE.conf['general']['speakRoutingTo'] = self.reading.speakRoutingTo.GetValue()
		configBE.conf['general']['tabSpace'] = self.reading.tabSpace.GetValue()
		configBE.conf['general']['tabSize'] = self.reading.tabSize.GetValue()
		configBE.conf['general']['attribra'] = self.attribra.attribraEnabled.GetValue()
		configBE.conf['general']['reviewModeApps'] = self.general.reviewModeApps.GetValue()
		if not configBE.noUnicodeTable:
			configBE.conf['general']['iTableSht'] = self.keyboard.iTableSht.GetSelection(
			) - 1
		if not self.reading.smartDelayScroll.GetValue():
			configBE.conf['general']['ignoreBlankLineScroll'] = self.reading.ignoreBlankLineScroll.GetValue()
		if configBE.gesturesFileExists:
			configBE.conf['general']['keyboardLayout_%s' % configBE.curBD] = configBE.iniProfile['keyboardLayouts'].keys()[self.keyboard.KBMode.GetSelection()]
		if configBE.curBD != 'noBraille':
			configBE.conf['general']['quickLaunchGestures_%s' % configBE.curBD] = ', '.join(self.quickLaunch.quickLaunchGestures)
			configBE.conf['general']['quickLaunchLocations_%s' % configBE.curBD] = '; '.join(self.quickLaunch.quickLaunchLocations)
		configBE.conf['general']['iTables'] = ','.join(self.keyboard.iTables)
		configBE.conf['general']['oTables'] = ','.join(self.reading.oTables)
		configBE.conf['general']['brailleDisplay1'] = braille.getDisplayList()[self.general.brailleDisplay1.GetSelection()][0]
		configBE.conf['general']['brailleDisplay2'] = braille.getDisplayList()[self.general.brailleDisplay2.GetSelection()][0]
		self.buttonC.SetFocus()
		configBE.saveSettingsAttribra()
		configBE.saveSettings()
		if restartNVDA:
			gui.messageBox(_(u"You have made a change that requires you restart NVDA"), '%s – %s' % (configBE._addonName, _(u"Restart required")),
				wx.OK | wx.ICON_INFORMATION)
			self.onClose(None)
			core.restart()
		return instanceGP.onReload(None, True)

	def onClose(self, evt):
		instanceGP.instanceST = None
		return self.Destroy()


class General(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		settings = wx.BoxSizer(wx.VERTICAL)
		loadBDs = wx.BoxSizer(wx.VERTICAL)
		self.autoCheckUpdate = wx.CheckBox(self, label=_('Check for updates automatically'))
		if configBE.conf['general']['autoCheckUpdate']: self.autoCheckUpdate.SetValue(True)
		self.assistS = wx.CheckBox(self, label=_('Detail the progress of a keyboard shortcut when it is typed'))
		if configBE.conf['general']['showConstructST']: self.assistS.SetValue(True)
		settings.Add(self.assistS)
		self.reportVolumeBraille = wx.CheckBox(self, label=_('Report of the new volume in braille'))
		if configBE.conf['general']['reportVolumeBraille']: self.reportVolumeBraille.SetValue(True)
		settings.Add(self.reportVolumeBraille)
		self.reportVolumeSpeech = wx.CheckBox(self, label=_('Report of the new volume in speech'))
		if configBE.conf['general']['reportVolumeSpeech']: self.reportVolumeSpeech.SetValue(True)
		settings.Add(self.reportVolumeSpeech)
		self.hourDynamic = wx.CheckBox(self, label=_('Display time and date infinitely'))
		if configBE.conf['general']['hourDynamic']: self.hourDynamic.SetValue(True)
		settings.Add(self.hourDynamic)
		settings.Add(wx.StaticText(self, -1, label=_('Re&view mode in')))
		self.reviewModeApps = wx.TextCtrl(self, -1, value=str(', '.join(configBE.reviewModeApps)))
		settings.Add(self.reviewModeApps)
		self.reviewModeApps.Bind(wx.EVT_CHAR, self.onReviewModeApps)
		settings.Add(wx.StaticText(self, -1, label=_('&Limit number of cells to (0 for no limit)')))
		self.limitCells = wx.TextCtrl(self, -1, value=str(configBE.conf['general']['limitCells_' + configBE.curBD]))
		settings.Add(self.limitCells)
		self.limitCells.Bind(wx.EVT_CHAR, self.onLimitCells)
		lb = braille.getDisplayList()
		lbl = []
		for l in lb:
			if l[0] == 'noBraille': lbl.append(_('Last known'))
			else: lbl.append(l[1])
		loadBDs.Add(wx.StaticText(self, -1, label=_('Braille display to load on NVDA+&k')))
		self.brailleDisplay1 = wx.Choice(self, pos=(-1, -1),choices=lbl)
		if configBE.conf['general']['brailleDisplay1'] == -1: self.brailleDisplay1.SetSelection(len(lbl) - 1)
		else: self.brailleDisplay1.SetSelection(self.getIdBD(configBE.conf['general']['brailleDisplay1']))
		loadBDs.Add(wx.StaticText(self, -1, label=_('Braille display to load on NVDA+Shift+k')))
		self.brailleDisplay2 = wx.Choice(self, pos=(-1, -1), choices=lbl)
		if configBE.conf['general']['brailleDisplay2'] == -1: self.brailleDisplay2.SetSelection(len(lbl) - 1)
		else: self.brailleDisplay2.SetSelection(self.getIdBD(configBE.conf['general']['brailleDisplay2']))
		loadBDs.Add(self.brailleDisplay1)
		loadBDs.Add(self.brailleDisplay2)
		settings.Add(loadBDs)

	@staticmethod
	def onReviewModeApps(event):
		keycode = event.GetKeyCode()
		if keycode > 255 or keycode < 32 or re.match('[a-zA-Z_\-0-9 .,]', chr(keycode)): return event.Skip()

	def onLimitCells(self, event):
		keycode = event.GetKeyCode()
		if keycode in [wx.WXK_UP, wx.WXK_DOWN]:
			v = self.limitCells.GetValue()
			try: v = int(v)
			except BaseException: v = 0
			if v < 0 or v > configBE.backupDisplaySize: v = 0
			if v >= 0 and v <= configBE.backupDisplaySize:
				if keycode == wx.WXK_DOWN:
					nv = v - 1 if v - 1 >= 0 else 0
					self.limitCells.SetValue(str(nv))
				else:
					v = configBE.backupDisplaySize if v == configBE.backupDisplaySize else v + 1
					self.limitCells.SetValue(str(v))
			return
		if keycode in [wx.WXK_CONTROL_V]: return
		if keycode > 255 or keycode < 32 or re.match('[0-9]', chr(keycode)): event.Skip()

	@staticmethod
	def getIdBD(name): return [k[0] for k in braille.getDisplayList()].index(name) if name in [k[0] for k in braille.getDisplayList()] else len(braille.getDisplayList()) - 1


class Reading(wx.Panel):
	oTables = []
	def __init__(self, parent):
		self.oTables = configBE.oTables
		lt = [_('None')]
		for table in tables:
			if table.output: lt.append(table[1])
		wx.Panel.__init__(self, parent)
		wx.StaticText(
			self, -1, label=_('Output braille tables present in the switch'))
		self.oTablesPresent = wx.Choice(
			self, pos=(-1, -1), choices=self.outputTablesInSwitch())
		self.oTablesPresent.SetSelection(0)
		self.deleteOutputTableInSwitch = wx.Button(self, label=_('&Remove'))
		self.deleteOutputTableInSwitch.Bind(
			wx.EVT_BUTTON, self.onDeleteOutputTableInSwitch)
		wx.StaticText(
			self, -1, label=_('Output tables not present in the switch'))
		self.oTablesNotPresent = wx.Choice(
			self, pos=(-1, -1), choices=self.outputTablesNotInSwitch())
		self.oTablesNotPresent.SetSelection(0)
		self.addOutputTableInSwitch = wx.Button(self, label=_('&Add'))
		self.addOutputTableInSwitch.Bind(
			wx.EVT_BUTTON, self.onAddOutputTableInSwitch)
		wx.StaticText(self, -1, label=_('Secondary output table to use') + (' (%s) ' %
																			 _('function disabled automatically due to a crash') if not configBE.conf["patch"]["updateBraille"] else ''))
		self.postTable = wx.Choice(self, pos=(-1, -1), choices=lt)
		self.postTable.SetSelection(configBE.tablesFN.index(
			configBE.conf['general']['postTable']) if configBE.conf['general']['postTable'] in configBE.tablesFN else 0)
		self.tabSpace = wx.CheckBox(self, label=_('Display tab signs as spaces') + (' (%s) ' % _(
			'function disabled automatically due to a crash') if not configBE.conf["patch"]["updateBraille"] else ''))
		if configBE.conf['general']['tabSpace']:
			self.tabSpace.SetValue(True)
		self.tabSize = wx.StaticText(
			self, -1, label=_('Number of space for a tab sign'))
		self.tabSize = wx.TextCtrl(
			self, -1, value=str(configBE.conf['general']['tabSize']))
		self.tabSize.Bind(wx.EVT_CHAR, self.onTabSize)
		self.speakRoutingTo = wx.CheckBox(self, label=_('Announce the character when moving with routing buttons'))
		if configBE.conf['general']['speakRoutingTo']:
			self.speakRoutingTo.SetValue(True)
		self.speakScroll = wx.CheckBox(self, label=_('In review mode, say the current line during text scrolling') + (
				' (%s) ' %
				_('function disabled automatically due to a crash') if not configBE.conf["patch"]["scrollBraille"] else ''))
		if configBE.conf['general']['speakScroll']:
			self.speakScroll.SetValue(True)
		self.delayScrollT = wx.StaticText(
			self, -1, label=_('&Delay for scroll'))
		self.delayScroll = wx.TextCtrl(
			self, -1, value=str(configBE.conf['general']['delayScroll_' + configBE.curBD]))
		self.delayScroll.Bind(wx.EVT_CHAR, self.onDelayScroll)
		self.ignoreBlankLineScroll = wx.CheckBox(
			self, label=_('Hide empty views during autoscroll'))
		if configBE.conf['general']['ignoreBlankLineScroll']:
			self.ignoreBlankLineScroll.SetValue(True)
		self.ignoreBlankLineScroll.Disable()
		self.smartDelayScroll = wx.CheckBox(
			self, label=_('Adjust the delay autoscroll to the content'))
		if configBE.conf['general']['smartDelayScroll']:
			self.smartDelayScroll.SetValue(True)
		self.smartDelayScroll.Bind(wx.wx.EVT_CHECKBOX, self.onSmartDelay)
		self.smartDelayScroll.Disable()
		self.reverseScroll = wx.CheckBox(
			self, label=_('Reverse forward scroll and back scroll buttons'))
		if configBE.conf['general']['reverseScroll']:
			self.reverseScroll.SetValue(True)
		self.labelsGroup = wx.StaticText(self, -1, label=_('Customize role labels'))
		self.roleLabelCategory = wx.StaticText(self, -1, label=_('Category'))
		self.roleLabelCategories = wx.Choice(
			self, pos=(-1, -1), choices=[_('General'), _('Landmark'), _('Positive state'), _('Negative state')])
		self.roleLabelCategories.Bind(wx.EVT_CHOICE, self.onRoleLabelCategories)
		self.roleLabelCategories.SetSelection(0)
		self.labels = wx.Choice(
			self, pos=(-1, -1), choices=[controlTypes.roleLabels[k] for k in braille.roleLabels.keys()])
		self.labels.Bind(wx.EVT_CHOICE, self.onRoleLabels)
		self.layoutLabel = wx.TextCtrl(self, -1, value=braille.roleLabels.values()[controlTypes.roleLabels.keys()[0]])
		self.labels.SetSelection(0)

	def onRoleLabelCategories(self, event):
		idCategory = self.roleLabelCategories.GetSelection()
		if idCategory == 0:
			self.labels.SetItems([controlTypes.roleLabels[k] for k in braille.roleLabels.keys()])
		elif idCategory == 1:
			self.labels.SetItems(braille.landmarkLabels.keys())
		elif idCategory == 2:
			self.labels.SetItems([controlTypes.stateLabels[k] for k in braille.positiveStateLabels.keys()])
		elif idCategory == 3:
			self.labels.SetItems([controlTypes.stateLabels[k] for k in braille.negativeStateLabels.keys()])
		else:
			self.labels.SetItems([])
		if idCategory > -1 and idCategory < 4:
			self.labels.SetSelection(0)
		self.onRoleLabels(None)
		return

	def onRoleLabels(self, event):
		idCategory = self.roleLabelCategories.GetSelection()
		if idCategory == 0:
			self.layoutLabel.SetValue(braille.roleLabels[braille.roleLabels.keys()[self.labels.GetSelection()]])
		elif idCategory == 1:
			self.layoutLabel.SetValue(braille.landmarkLabels.values()[self.labels.GetSelection()])
		elif idCategory == 2:
			self.layoutLabel.SetValue(braille.positiveStateLabels[braille.positiveStateLabels.keys()[self.labels.GetSelection()]])
		elif idCategory == 3:
			self.layoutLabel.SetValue(braille.negativeStateLabels[braille.negativeStateLabels.keys()[self.labels.GetSelection()]])
		return

	def onDeleteOutputTableInSwitch(self, event):
		if self.oTablesPresent.GetStringSelection() != '':
			self.oTables.remove(configBE.tablesFN[configBE.tablesTR.index(
				self.oTablesPresent.GetStringSelection())])
			self.oTablesNotPresent.SetItems(self.outputTablesNotInSwitch())
			self.oTablesNotPresent.SetSelection(0)
			self.oTablesPresent.SetItems(self.outputTablesInSwitch())
			self.oTablesPresent.SetSelection(0)
			self.oTablesPresent.SetFocus()
		else:
			ui.message(_(u"You have no output tables present in the switch"))
		return

	def onAddOutputTableInSwitch(self, event):
		if self.oTablesNotPresent.GetStringSelection() != '':
			self.oTables.append(configBE.tablesFN[configBE.tablesTR.index(
				self.oTablesNotPresent.GetStringSelection())])
			self.oTablesNotPresent.SetItems(self.outputTablesNotInSwitch())
			self.oTablesNotPresent.SetSelection(0)
			self.oTablesPresent.SetItems(self.outputTablesInSwitch())
			self.oTablesPresent.SetSelection(0)
			self.oTablesPresent.SetFocus()

	@staticmethod
	def onTabSize(evt):
		key = evt.GetKeyCode()
		okChars = "0123456789"
		if key < 32 or key > 255 or chr(key) in okChars:
			evt.Skip()
			return
		else: return False

	def onDelayScroll(self, event):
		keycode = event.GetKeyCode()
		if keycode in [wx.WXK_UP, wx.WXK_DOWN]:
			v = self.delayScroll.GetValue().replace(',', '.')
			try:
				v = float(v)
			except BaseException:
				v = configBE.conf['general']['delayScroll_' + configBE.curBD]
			if v >= 0 and v < 1000:
				if keycode == wx.WXK_DOWN:
					nv = v - 0.25 if v - 0.25 >= 0.25 else 0.25
					self.delayScroll.SetValue(str(nv))
				else:
					self.delayScroll.SetValue(str(v + 0.25))
			return

		if keycode in [wx.WXK_CONTROL_V]:
			return
		if (
				(keycode < 32 or keycode > 255)
				or
				(
					(
						(re.match('[0-9]', chr(keycode))) or (re.match('[0-9.,]', chr(keycode))
						and (self.delayScroll.GetValue().count(',') == 0 and self.delayScroll.GetValue().count('.') == 0)
						and re.match('[0-9][0-9.,]{0,}', self.delayScroll.GetValue())
					)
				)
			)
		): event.Skip()
		return

	def onSmartDelay(self, e):
		cb = e.GetEventObject()
		if cb.GetValue():
			self.ignoreBlankLineScroll.Disable()
		else:
			self.ignoreBlankLineScroll.Enable()
		return

	outputTablesNotInSwitch = lambda s: [table[1] for table in tables if table.output and table[0] not in configBE.oTables] if configBE.oTables != None else []
	outputTablesInSwitch = lambda s: [configBE.tablesTR[configBE.tablesFN.index(table)] for table in configBE.oTables if table != ''] if configBE.oTables != None else []

class Attribra(wx.Panel):
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.attribraEnabled = wx.CheckBox(self, label=_('Enable Attribra'))
		if configBE.conf['general']['attribra']:
			self.attribraEnabled.SetValue(True)
		self.profilesLabel = wx.StaticText(self, -1, label=_('Profile'))
		self.profiles = wx.Choice(
			self, pos=(-1, -1), choices=self.getListProfiles())
		self.profiles.SetSelection(0)
		self.profiles.Bind(wx.EVT_CHOICE, self.onProfiles)
		self.bold = wx.CheckBox(self, label=_('Bold'))
		self.italic = wx.CheckBox(self, label=_('Italic'))
		self.underline = wx.CheckBox(self, label=_('Underline'))
		self.spellingErrors = wx.CheckBox(self, label=_('Spelling errors'))
		self.spellingErrors.Bind(wx.EVT_CHECKBOX, self.onSpellingErrors)
		self.bold.Bind(wx.EVT_CHECKBOX, self.onBold)
		self.italic.Bind(wx.EVT_CHECKBOX, self.onItalic)
		self.underline.Bind(wx.EVT_CHECKBOX, self.onUnderline)
		self.onProfiles()

	def onBold(self, event):
		if self.bold.GetValue():
			if 'bold' not in configBE.confAttribra[self.getCurrentProfile()]:
				configBE.confAttribra[self.getCurrentProfile()]['bold'] = [1]
			configBE.confAttribra[self.getCurrentProfile()]['bold'][0] = 1
		else:
			if 'bold' in configBE.confAttribra[self.getCurrentProfile()]:
				del configBE.confAttribra[self.getCurrentProfile()]['bold']
		return

	def onItalic(self, event):
		if self.italic.GetValue():
			if 'italic' not in configBE.confAttribra[self.getCurrentProfile()]:
				configBE.confAttribra[self.getCurrentProfile()]['italic'] = [1]
			configBE.confAttribra[self.getCurrentProfile()]['italic'][0] = 1
		else:
			if 'italic' in configBE.confAttribra[self.getCurrentProfile()]:
				del configBE.confAttribra[self.getCurrentProfile()]['italic']
		return

	def onUnderline(self, event):
		if self.underline.GetValue():
			if 'underline' not in configBE.confAttribra[self.getCurrentProfile()]:
				configBE.confAttribra[self.getCurrentProfile()]['underline'] = [1]
			configBE.confAttribra[self.getCurrentProfile()]['underline'][0] = 1
		else:
			if 'underline' in configBE.confAttribra[self.getCurrentProfile()]:
				del configBE.confAttribra[self.getCurrentProfile()]['underline']
		return

	def onSpellingErrors(self, event):
		if self.spellingErrors.GetValue():
			if 'invalid-spelling' not in configBE.confAttribra[self.getCurrentProfile()]:
				configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling'] = [1]
			configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling'][0] = 1
		else:
			if 'invalid-spelling' in configBE.confAttribra[self.getCurrentProfile()]:
				del configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling']
		return

	def getCurrentProfile(self): return 'global' if self.profiles.GetSelection(
	) == 0 else self.getListProfiles(False)[self.profiles.GetSelection()]

	getListProfiles = lambda self, t = True: ['Default'] + [self.translateApp(k) if t else k for k in configBE.confAttribra.keys() if k != 'global']

	def onProfiles(self, event=None):
		profileId = self.profiles.GetSelection()
		app = 'global' if profileId == 0 else self.getListProfiles(False)[
			profileId]
		if 'bold' in configBE.confAttribra[app].keys(
		) and self.bold.GetValue() != configBE.confAttribra[app]['bold']:
			self.bold.SetValue(not self.bold.GetValue())
		if 'bold' not in configBE.confAttribra[app].keys():
			self.bold.SetValue(False)
		if 'italic' in configBE.confAttribra[app].keys(
		) and self.italic.GetValue() != configBE.confAttribra[app]['italic']:
			self.italic.SetValue(not self.italic.GetValue())
		if 'italic' not in configBE.confAttribra[app].keys():
			self.italic.SetValue(False)
		if 'underline' in configBE.confAttribra[app].keys(
		) and self.underline.GetValue() != configBE.confAttribra[app]['underline']:
			self.underline.SetValue(not self.underline.GetValue())
		if 'underline' not in configBE.confAttribra[app].keys():
			self.underline.SetValue(False)
		if 'invalid-spelling' in configBE.confAttribra[app].keys(
		) and self.spellingErrors.GetValue() != configBE.confAttribra[app]['invalid-spelling']:
			self.spellingErrors.SetValue(not self.spellingErrors.GetValue())
		if 'invalid-spelling' not in configBE.confAttribra[app].keys():
			self.spellingErrors.SetValue(False)

	@staticmethod
	def translateApp(app):
		tApps = {
			'winword': 'Microsoft Word',
		}
		return tApps[app] + ' (%s)' % app if app in tApps else app.capitalize()


class Keyboard(wx.Panel):
	iTables = []
	def __init__(self, parent):
		wx.Panel.__init__(self, parent)
		self.iTables = configBE.iTables
		if not configBE.noUnicodeTable:
			lt = [_('Use the current input table')]
			for table in tables:
				if table.input: lt.append(table[1])
			wx.StaticText(self, -1, label=_('Input braille table for keyboard shortcut keys'))
			self.iTableSht = wx.Choice(self, pos=(-1, -1), choices=lt)
			self.iTableSht.SetSelection(configBE.conf['general']['iTableSht'] + 1)
			wx.StaticText(self, -1, label=_('Input braille tables present in the switch'))
			self.iTablesPresent = wx.Choice(self, pos=(-1, -1), choices=self.inputTablesInSwitch())
			self.iTablesPresent.SetSelection(0)
			self.deleteInputTableInSwitch = wx.Button(self, label=_('&Remove'))
			self.deleteInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteInputTableInSwitch)
			wx.StaticText(self, -1, label=_('Input tables not present in the switch'))
			self.iTablesNotPresent = wx.Choice(self, pos=(-1, -1), choices=self.inputTablesNotInSwitch())
			self.iTablesNotPresent.SetSelection(0)
			self.addInputTableInSwitch = wx.Button(self, label=_('&Add'))
			self.addInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddInputTableInSwitch)
		if configBE.gesturesFileExists and not instanceGP.noKeyboarLayout():
			lb = [k for k in instanceGP.getKeyboardLayouts()]
			wx.StaticText(self, -1, label=_('Braille keyboard configuration'))
			self.KBMode = wx.Choice(self, pos=(-1, -1), choices=lb)
			self.KBMode.SetSelection(self.getKeyboardLayout())

	def getKeyboardLayout(self):
		if (configBE.conf['general']['keyboardLayout_' + configBE.curBD] is not None
		 and configBE.conf['general']['keyboardLayout_' + configBE.curBD] in configBE.iniProfile['keyboardLayouts'].keys()):
			return configBE.iniProfile['keyboardLayouts'].keys().index(configBE.conf['general']['keyboardLayout_' + configBE.curBD])
		else: return 0

	def onDeleteInputTableInSwitch(self, event):
		if self.iTablesPresent.GetStringSelection() != '':
			self.iTables.remove(configBE.tablesFN[configBE.tablesTR.index(self.iTablesPresent.GetStringSelection())])
			self.iTablesNotPresent.SetItems(self.inputTablesNotInSwitch())
			self.iTablesNotPresent.SetSelection(0)
			self.iTablesPresent.SetItems(self.inputTablesInSwitch())
			self.iTablesPresent.SetSelection(0)
			self.iTablesPresent.SetFocus()
		else:
			ui.message(_(u"You have no input tables present in the switch"))
		return

	def onAddInputTableInSwitch(self, event):
		if self.iTablesNotPresent.GetStringSelection() != '':
			self.iTables.append(configBE.tablesFN[configBE.tablesTR.index(
				self.iTablesNotPresent.GetStringSelection())])
			self.iTablesNotPresent.SetItems(self.inputTablesNotInSwitch())
			self.iTablesNotPresent.SetSelection(0)
			self.iTablesPresent.SetItems(self.inputTablesInSwitch())
			self.iTablesPresent.SetSelection(0)
			self.iTablesPresent.SetFocus()

	inputTablesNotInSwitch = lambda s: [table[1] for table in tables if table.input and table[0] not in configBE.iTables] if configBE.iTables != None else []
	inputTablesInSwitch = lambda s: [configBE.tablesTR[configBE.tablesFN.index(table)] for table in configBE.iTables if table.strip() != ''] if configBE.iTables != None else []


class QuickLaunch(wx.Panel):

	quickLaunchGestures = []
	quickLaunchLocations = []

	def __init__(self, parent):
		self.quickLaunchGestures = configBE.quickLaunchs.keys()
		self.quickLaunchLocations = configBE.quickLaunchs.values()
		wx.Panel.__init__(self, parent)
		if configBE.curBD != 'noBraille':
			self.quickKeysT = wx.StaticText(self, -1, label=_('Gestures for the quick launches')+' ('+_('display: %s' % configBE.curBD)+')' if configBE.curBD != 'noBraille' else '')
			self.quickKeys = wx.Choice(self, pos=(-1, -1), choices=self.getQuickLaunchList())
			self.quickKeys.SetSelection(0)
			self.quickKeys.Bind(wx.EVT_CHOICE, self.onQuickKeys)
			self.target = wx.TextCtrl(self, -1, value=self.quickLaunchLocations[0] if self.quickLaunchLocations != [] else '')
			self.target.Bind(wx.wx.EVT_TEXT, self.onTarget)
			self.browseBtn = wx.Button(self, -1, label=_('&Browse...'))
			self.removeGestureBtn = wx.Button(self, -1, label=_('&Remove this gesture'))
			self.addGestureBtn = wx.Button(self, -1, label=_('&Add a quick launch'))
			self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowseBtn)
			self.removeGestureBtn.Bind(wx.EVT_BUTTON, self.onRemoveGestureBtn)
			self.addGestureBtn.Bind(wx.EVT_BUTTON, self.onAddGestureBtn)

	def getQuickLaunchList(s): return [
'%s%s: %s' % (s.quickLaunchGestures[i], configBE.sep, s.quickLaunchLocations[i]) for i, v in enumerate(s.quickLaunchLocations)]

	def onRemoveGestureBtn(self, event):
		global restartNVDA_
		id = self.quickKeys.GetSelection()
		g=self.quickLaunchGestures.pop(id)
		self.quickLaunchLocations.pop(id)
		self.quickKeys.SetItems(self.getQuickLaunchList())
		self.quickKeys.SetSelection(id-1 if id > 0 else 0)
		self.onQuickKeys(None)
		self.quickKeys.SetFocus()
		queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('%s removed.' % g))
		
		return
	def captureNow(self):
		def getCaptured(gesture):
			if gesture.isModifier:
				return False
			if scriptHandler.findScript(gesture) is not None:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('Unable to associate this gesture. Please enter another, now'))
				return False
			if gesture.normalizedIdentifiers[0].startswith('kb') and ':escape' not in gesture.normalizedIdentifiers[0]:
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('Please enter a gesture from your %s braille display. Press Escape to cancel.' % configBE.curBD))
				return False
			if ':escape' not in gesture.normalizedIdentifiers[0]:
				self.quickLaunchGestures.append(gesture.normalizedIdentifiers[0].split(':')[1])
				self.quickLaunchLocations.append('')
				self.quickKeys.SetItems(self.getQuickLaunchList())
				self.quickKeys.SetSelection(len(self.quickLaunchGestures)-1)
				self.onQuickKeys(None)
				self.quickKeys.SetFocus()
				queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('OK. The gesture captured is %s') % gesture.normalizedIdentifiers[0].split(':')[1])
			inputCore.manager._captureFunc = None
		inputCore.manager._captureFunc = getCaptured


	def onAddGestureBtn(self, event):
		self.captureNow()
		queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _('Please enter the desired gesture for this command, now'))
		return

	def onTarget(self, event):
		oldS = self.quickKeys.GetSelection()
		self.quickLaunchLocations[self.quickKeys.GetSelection()] = self.target.GetValue()
		self.quickKeys.SetItems(self.getQuickLaunchList())
		self.quickKeys.SetSelection(oldS)
		return

	def onQuickKeys(self, event):
		if not self.quickKeys.GetStringSelection().strip().startswith(':'):
			self.target.SetValue(self.quickKeys.GetStringSelection().split(': ')[1])
		else:
			self.target.SetValue('')
		return

	def onBrowseBtn(self, event):
		oldS = self.quickKeys.GetSelection()
		dlg = wx.FileDialog(None, _("Choose a file for {0}".format(self.quickLaunchGestures[self.quickKeys.GetSelection()])), "%PROGRAMFILES%", "", "*", wx.OPEN)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return self.quickKeys.SetFocus()
		self.target.SetValue(dlg.GetDirectory() + '\\' + dlg.GetFilename())
		self.quickLaunchLocations[self.quickKeys.GetSelection()] = dlg.GetDirectory() + '\\' + dlg.GetFilename()
		self.quickKeys.SetItems(self.getQuickLaunchList())
		self.quickKeys.SetSelection(oldS)
		dlg.Destroy()
		return self.quickKeys.SetFocus()
