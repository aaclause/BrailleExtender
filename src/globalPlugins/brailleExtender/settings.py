# coding: utf-8
import re 
import wx
import gui

import addonHandler
import braille
import brailleInput
import brailleTables
import inputCore
import ui
addonHandler.initTranslation()
from logHandler import log

import configBE

class Settings(wx.Dialog):
    def __init__(self, *args):
        global curBD, reviewModeApps, noUnicodeTable, noKC, gesturesFileExists, iniProfile, quickLaunch, quickLaunchS, keyboardLayouts, instanceGP, backupDisplaySize, iTables
        (curBD, reviewModeApps, noUnicodeTable, noKC, gesturesFileExists, iniProfile, quickLaunch, quickLaunchS, instanceGP, keyboardLayouts, backupDisplaySize, iTables) = args
        if instanceGP.instanceST != None:
            return
        instanceGP.instanceST = self
        if not type(iTables) == list:
            iTables = iTables.replace(', ',',').split(',')
        wx.Dialog.__init__(self, None, title=_('BrailleExtender settings'))
        self.p = wx.Panel(self)
        self.nb = wx.Notebook(self.p)
        self.general = General(self.nb)
        self.reading = Reading(self.nb)
        self.keyboard = Keyboard(self.nb)
        self.quickLaunch = QuickLaunch(self.nb)
        self.nb.AddPage(self.general, _("General"))
        self.nb.AddPage(self.reading, _("Reading"))
        self.nb.AddPage(self.keyboard, _("Braille keyboard"))
        self.nb.AddPage(self.quickLaunch, _("Quick launches"))
        self.sizer = wx.BoxSizer()
        self.btnS = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.nb, 1, wx.EXPAND)
        self.p.SetSizer(self.sizer)
        self.buttonS = wx.Button(self, label=_('&Save'))
        self.btnS.Add(self.buttonS)
        self.buttonC = wx.Button(self, label=_('&Close'), id=wx.ID_CLOSE)
        self.btnS.Add(self.buttonC)
        self.buttonS.Bind(wx.EVT_BUTTON, self.onSave)
        self.buttonC.Bind(wx.EVT_BUTTON, self.onClose)
        self.sizer.Add(self.btnS)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.EscapeId = wx.ID_CLOSE
        self.Show()
        return

    def onSave(self, evt):
        i = 0
        configBE.conf['general']['showConstructST'] = self.general.assistS.GetValue()
        configBE.conf['general']['reportvolumeb'] = self.general.reportvolumeb.GetValue()
        configBE.conf['general']['reportvolumes'] = self.general.reportvolumes.GetValue()
        configBE.conf['general']['hourDynamic'] = self.general.hourDynamic.GetValue()
        configBE.conf['general']['delayScroll_' + curBD] = self.reading.delayScroll.GetValue()
        try:
            if int(
                    self.general.limitCells.GetValue()) > backupDisplaySize or int(
                    self.general.limitCells.GetValue()) < 0:
                configBE.conf['general']['limitCells_' + curBD] = 0
            else:
                if configBE.conf['general']['limitCells_' +
                                   curBD] != 0 and int(self.general.limitCells.GetValue()) == 0:
                    braille.handler.displaySize = backupDisplaySize
                configBE.conf['general']['limitCells_' +
                                curBD] = int(self.general.limitCells.GetValue())
        except BaseException:
            configBE.conf['general']['limitCells_' + curBD] = 0
        configBE.conf['general']['smartDelayScroll'] = self.reading.smartDelayScroll.GetValue()
        configBE.conf['general']['reviewModeApps'] = self.general.reviewModeApps.GetValue()
        if not noUnicodeTable:
            configBE.conf['general']['iTableSht'] = self.keyboard.iTableSht.GetSelection() - 1
        if not self.reading.smartDelayScroll.GetValue():
            configBE.conf['general']['ignoreBlankLineScroll'] = self.reading.ignoreBlankLineScroll.GetValue()
        if gesturesFileExists:
            configBE.conf['general']['keyboardLayout_' +curBD] = iniProfile['keyboardLayouts'].keys()[self.keyboard.KBMode.GetSelection()]
            tApps = []
            for app in quickLaunchS:
                tApps.append(app.strip())
            configBE.conf['general']['quickLaunch_'+curBD] = '; '.join(tApps)
            configBE.conf['general']['iTables'] = ','.join(iTables)
        
        configBE.conf['general']['favbd1'] = self.general.favbd1.GetSelection()
        configBE.conf['general']['favbd2'] = self.general.favbd2.GetSelection()
        self.buttonC.SetFocus()
        configBE.saveSettings()
        return instanceGP.onReload(None,True)


    def onClose(self, evt):
        instanceGP.instanceST = None
        return self.Destroy()

class General(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        settings = wx.BoxSizer(wx.VERTICAL)
        loadBDs = wx.BoxSizer(wx.VERTICAL)
        i = 0
        self.assistS = wx.CheckBox(self, label=_('Detail the progress of a keyboard shortcut when it is typed'))
        if configBE.conf['general']['showConstructST']:
            self.assistS.SetValue(True)
        settings.Add(self.assistS)
        self.reportvolumeb = wx.CheckBox(self, label=_('Report of the new volume in braille'))
        if configBE.conf['general']['reportvolumeb']:
            self.reportvolumeb.SetValue(True)
        settings.Add(self.reportvolumeb)
        self.reportvolumes = wx.CheckBox(self, label=_('Report of the new volume in speech'))
        if configBE.conf['general']['reportvolumes']:
            self.reportvolumes.SetValue(True)
        settings.Add(self.reportvolumes)
        self.hourDynamic = wx.CheckBox(self, label=_(u'Display time and date infinitely'))
        if configBE.conf['general']['hourDynamic']:
            self.hourDynamic.SetValue(True)
        settings.Add(self.hourDynamic)
        settings.Add(wx.StaticText(self, -1, label=_('Re&view mode in')))
        self.reviewModeApps = wx.TextCtrl(self, -1, value=str(', '.join(reviewModeApps)))
        settings.Add(self.reviewModeApps)
        self.reviewModeApps.Bind(wx.EVT_CHAR, self.onReviewModeApps)
        settings.Add(wx.StaticText(self, -1, label='(' +_('experimental, works poorly with Baum devices') +') ' +_('&Limit number of cells to (0 for no limit)')))
        self.limitCells = wx.TextCtrl(self, -1, value=str(configBE.conf['general']['limitCells_' + curBD]))
        settings.Add(self.limitCells)
        self.limitCells.Bind(wx.EVT_CHAR, self.onLimitCells)
        lb = braille.getDisplayList()
        lbl = []
        for l in lb:
            if l[0] == 'noBraille':
                lbl.append(_('Last known'))
            else:
                lbl.append(l[1])
        loadBDs.Add(
            wx.StaticText(
                self, -1, label=_('Braille display to load on NVDA+&k')))
        self.favbd1 = wx.Choice(self, pos=(-1, -1),
                                choices=lbl)
        if configBE.conf['general']['favbd1'] == -1:
            self.favbd1.SetSelection(len(lbl) - 1)
        else:
            self.favbd1.SetSelection(configBE.conf['general']['favbd1'])
        loadBDs.Add(
            wx.StaticText(
                self, -1, label=_('Braille display to load on NVDA+Shift+k')))
        self.favbd2 = wx.Choice(self, pos=(-1, -1),
                                choices=lbl)
        if configBE.conf['general']['favbd2'] == -1:
            self.favbd2.SetSelection(len(lbl) - 1)
        else:
            self.favbd2.SetSelection(configBE.conf['general']['favbd2'])
        loadBDs.Add(self.favbd1)
        loadBDs.Add(self.favbd2)
        settings.Add(loadBDs)
        return

    def onReviewModeApps(self, event):
        keycode = event.GetKeyCode()
        if keycode > 255 or keycode < 32 or re.match('[a-zA-Z_\-0-9 .,]', chr(keycode)):
            return event.Skip()

    def onLimitCells(self, event):
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_UP, wx.WXK_DOWN]:
            v = self.limitCells.GetValue()
            try:
                v = int(v)
            except BaseException:
                v = 0
            if v < 0 or v > backupDisplaySize:
                v = 0
            if v >= 0 and v <= backupDisplaySize:
                if keycode == wx.WXK_DOWN:
                    nv = v - 1 if v - 1 >= 0 else 0
                    self.limitCells.SetValue(str(nv))
                else:
                    v = backupDisplaySize if v == backupDisplaySize else v+1
                    self.limitCells.SetValue(str(v))
            return
        if keycode in [wx.WXK_CONTROL_V]:
            return
        if keycode > 255 or keycode < 32 or re.match('[0-9]', chr(keycode)):
            event.Skip()
        return

class Reading(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.delayScrollT = wx.StaticText(self, -1, label=_('&Delay for scroll'))
        self.delayScroll = wx.TextCtrl(self, -1, value=str(configBE.conf['general']['delayScroll_' + curBD]))
        self.delayScroll.Bind(wx.EVT_CHAR, self.onDelayScroll)
        self.ignoreBlankLineScroll = wx.CheckBox(self, label=_(u'Hide empty views during autoscroll'))
        if configBE.conf['general']['ignoreBlankLineScroll']:
            self.ignoreBlankLineScroll.SetValue(True)
        self.ignoreBlankLineScroll.Disable()
        self.smartDelayScroll = wx.CheckBox(
            self, label=_('Adjust the delay autoscroll to the content'))
        if configBE.conf['general']['smartDelayScroll']:
            self.smartDelayScroll.SetValue(True)
        self.smartDelayScroll.Bind(wx.wx.EVT_CHECKBOX, self.onSmartDelay)
        self.smartDelayScroll.Disable()

    def onDelayScroll(self, event):
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_UP, wx.WXK_DOWN]:
            v = self.delayScroll.GetValue()
            v = v.replace(',', '.')
            try:
                v = float(v)
            except BaseException:
                v = configBE.conf['general']['delayScroll_' + curBD]
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
                    (re.match('[0-9]', chr(keycode)))
                    or
                    (re.match('[0-9.,]', chr(keycode))
                     and
                     (
                        self.delayScroll.GetValue().count(',') == 0
                        and self.delayScroll.GetValue().count('.') == 0)
                        and re.match('[0-9][0-9.,]{0,}', self.delayScroll.GetValue())
                     )
                )
            )
        ):
            event.Skip()
        return

    def onSmartDelay(self, e):
        cb = e.GetEventObject()
        if cb.GetValue():
            self.ignoreBlankLineScroll.Disable()
        else:
            self.ignoreBlankLineScroll.Enable()
        return
class Keyboard(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        kbCfg = wx.BoxSizer(wx.VERTICAL)
        if not noUnicodeTable:
            lt = [_('Use the current input table')]
            [lt.append(tables[i][1]) for i in range(len(tables))]
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input braille table for keyboard shortcut keys')))
            self.iTableSht = wx.Choice(self, pos=(-1, -1), choices=lt)
            self.iTableSht.SetSelection(configBE.conf['general']['iTableSht'] + 1)
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input braille table present in the switch')))
            self.iTablesPresent = wx.Choice(self, pos=(-1, -1), choices=self.tablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.deleteTableInSwitch = wx.Button(self, label=_('&Remove'))
            self.deleteTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteTableInSwitch)
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input braille table for switch to add')))
            self.iTables = wx.Choice(self, pos=(-1, -1), choices=self.tablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.addTableInSwitch = wx.Button(self, label=_('&Add'))
            self.addTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddTableInSwitch)
        if gesturesFileExists and not noKC:
            lb = keyboardLayouts
            kbCfg.Add(wx.StaticText(self, -1, label=_('Braille keyboard configuration')))
            self.KBMode = wx.Choice(self, pos=(-1, -1), choices=lb)
            self.KBMode.SetSelection(iniProfile['keyboardLayouts'].keys().index(configBE.conf['general']['keyboardLayout_' + curBD]) if configBE.conf['general']['keyboardLayout_' +configBE.curBD] != None and configBE.conf['general']['keyboardLayout_'+curBD] in iniProfile['keyboardLayouts'].keys() else 0)
            kbCfg.Add(self.KBMode)

    def onDeleteTableInSwitch(self, event):
        if self.iTablesPresent.GetStringSelection() != '':
            iTables.remove(tablesFN[tablesTR.index(self.iTablesPresent.GetStringSelection())])
            self.iTables.SetItems(self.tablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.iTablesPresent.SetItems(self.tablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.iTablesPresent.SetFocus()
        else:
            ui.message(_(u"You have no input tables present in the switch"))
        return

    def onAddTableInSwitch(self, event):
        if self.iTables.GetStringSelection() != '':
            iTables.append(tablesFN[tablesTR.index(self.iTables.GetStringSelection())])
            self.iTables.SetItems(self.tablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.iTablesPresent.SetItems(self.tablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.iTablesPresent.SetFocus()

    global tables, tablesFN, tablesTR
    tables = brailleTables.listTables()
    tablesFN = [t[0] for t in tables]
    tablesTR = [t[1] for t in tables]
    tablesNotInSwitch = lambda s: [tables[i][1] for i in range(len(tables)) if tables[i][0] not in iTables]
    tablesInSwitch = lambda s: [tablesTR[tablesFN.index(table)] for table in iTables if table != ''] if (len(iTables)>0 and iTables[0] != '') or len(tables) > 2 else []

class QuickLaunch(wx.Panel):
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        shts = wx.BoxSizer(wx.VERTICAL)
        t = wx.StaticText(self, -1, "This is a PageTwo object", (40,40))
        if gesturesFileExists:
            self.quickKeysT = wx.StaticText(self, -1, label=_('Combination keys for the quick launches'))
            self.quickKeys = wx.Choice(self, pos=(-1, -1), choices=self.getQuickLaunchList())
            self.quickKeys.SetSelection(0)
            self.quickKeys.Bind(wx.EVT_CHOICE, self.onQuickKeys)
            self.target = wx.TextCtrl(self, -1, value=quickLaunchS[0])
            self.target.Bind(wx.wx.EVT_TEXT, self.onTarget)
            self.browse = wx.Button(self, -1, label=_(u'&Browse...'))
            self.Bind(wx.EVT_BUTTON, self.onBrowse, self.browse)

    getQuickLaunchList = lambda s: [quickLaunch[k]+configBE.sep+': '+quickLaunchS[k] for k in range(len(quickLaunch))]
    
    def onTarget(self, event):
        oldS = self.quickKeys.GetSelection()
        quickLaunchS[self.quickKeys.GetSelection()] = self.target.GetValue()
        self.quickKeys.SetItems(self.getQuickLaunchList())
        return self.quickKeys.SetSelection(oldS)

    def onQuickKeys(self, event):
        return self.target.SetValue(self.quickKeys.GetStringSelection().split(': ')[1])

    def onBrowse(self, event):
        oldS = self.quickKeys.GetSelection()
        dlg = wx.FileDialog(None,
                            _("Choose a file for {0}".format(quickLaunch[self.quickKeys.GetSelection()])),
                            "%PROGRAMFILES%",
                            "",
                            "*",
                            wx.OPEN)
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return self.quickKeys.SetFocus()
        self.target.SetValue(dlg.GetDirectory() + '\\' + dlg.GetFilename())
        quickLaunchS[self.quickKeys.GetSelection()] = dlg.GetDirectory() + '\\' + dlg.GetFilename()
        self.quickKeys.SetItems(self.getQuickLaunchList())
        self.quickKeys.SetSelection(oldS)
        dlg.Destroy()
        return self.quickKeys.SetFocus()
