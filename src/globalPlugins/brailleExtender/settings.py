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
from colors import RGB
import configBE
inProcessMsg = _('Feature Not Implemented Yet')
CaptureMsg = _('Please enter the desired gesture for this command, now')
endCaptureMsg = _('OK. The gesture captured is %s')
failCaptureMsg = _('Unable to associate this gesture. Please enter another, now')
class Settings(wx.Dialog):
    def __init__(self, *args):
        global curBD, reviewModeApps, noUnicodeTable, noKC, gesturesFileExists, iniProfile, quickLaunch, quickLaunchS, keyboardLayouts, instanceGP, backupDisplaySize, iTables, oTables
        (curBD, reviewModeApps, noUnicodeTable, noKC, gesturesFileExists, iniProfile, quickLaunch, quickLaunchS, instanceGP, keyboardLayouts, backupDisplaySize, iTables, oTables) = args
        if instanceGP.instanceST != None:
            return
        instanceGP.instanceST = self
        wx.Dialog.__init__(self, None, title=_('BrailleExtender settings'))
        configBE.loadConfAttribra()
        self.p = wx.Panel(self)
        self.nb = wx.Notebook(self.p)
        self.general = General(self.nb)
        self.reading = Reading(self.nb)
        self.attribra = Attribra(self.nb)
        self.keyboard = Keyboard(self.nb)
        self.quickLaunch = QuickLaunch(self.nb)
        self.nb.AddPage(self.general, _("General"))
        self.nb.AddPage(self.reading, _("Reading"))
        self.nb.AddPage(self.attribra, _("Attribra"))
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
        configBE.conf['general']['autoCheckUpdate'] = self.general.autoCheckUpdate.GetValue()
        configBE.conf['general']['showConstructST'] = self.general.assistS.GetValue()
        configBE.conf['general']['reportVolumeBraille'] = self.general.reportVolumeBraille.GetValue()
        configBE.conf['general']['reportVolumeSpeech'] = self.general.reportVolumeSpeech.GetValue()
        configBE.conf['general']['hourDynamic'] = self.general.hourDynamic.GetValue()
        if configBE.conf['general']['reverseScroll'] != self.reading.reverseScroll.GetValue():
            if self.reading.reverseScroll.GetValue():
                instanceGP.reverseScrollBtns()
            else:
                instanceGP.reverseScrollBtns(None, True)
            configBE.conf['general']['reverseScroll'] = self.reading.reverseScroll.GetValue()
        configBE.conf['general']['delayScroll_' + curBD] = self.reading.delayScroll.GetValue()
        try:
            if int(self.general.limitCells.GetValue()) > backupDisplaySize or int(self.general.limitCells.GetValue()) < 0:
                configBE.conf['general']['limitCells_' + curBD] = 0
            else:
                if configBE.conf['general']['limitCells_' +curBD] != 0 and int(self.general.limitCells.GetValue()) == 0:
                    braille.handler.displaySize = backupDisplaySize
                configBE.conf['general']['limitCells_' +curBD] = int(self.general.limitCells.GetValue())
        except BaseException:
            configBE.conf['general']['limitCells_' + curBD] = 0
        configBE.conf['general']['smartDelayScroll'] = self.reading.smartDelayScroll.GetValue()
        configBE.conf['general']['attribra'] = self.attribra.attribraEnabled.GetValue()
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
        configBE.conf['general']['oTables'] = ','.join(oTables)
        configBE.conf['general']['brailleDisplay1'] = braille.getDisplayList()[self.general.brailleDisplay1.GetSelection()][0]
        configBE.conf['general']['brailleDisplay2'] = braille.getDisplayList()[self.general.brailleDisplay2.GetSelection()][0]
        self.buttonC.SetFocus()
        configBE.saveSettingsAttribra()
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
        self.autoCheckUpdate = wx.CheckBox(self, label=_('Check for updates automatically'))
        if configBE.conf['general']['autoCheckUpdate']:
            self.autoCheckUpdate.SetValue(True)
        self.assistS = wx.CheckBox(self, label=_('Detail the progress of a keyboard shortcut when it is typed'))
        if configBE.conf['general']['showConstructST']:
            self.assistS.SetValue(True)
        settings.Add(self.assistS)
        self.reportVolumeBraille = wx.CheckBox(self, label=_('Report of the new volume in braille'))
        if configBE.conf['general']['reportVolumeBraille']:
            self.reportVolumeBraille.SetValue(True)
        settings.Add(self.reportVolumeBraille)
        self.reportVolumeSpeech = wx.CheckBox(self, label=_('Report of the new volume in speech'))
        if configBE.conf['general']['reportVolumeSpeech']:
            self.reportVolumeSpeech.SetValue(True)
        settings.Add(self.reportVolumeSpeech)
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
        self.brailleDisplay1 = wx.Choice(self, pos=(-1, -1),
                                choices=lbl)
        if configBE.conf['general']['brailleDisplay1'] == -1:
            self.brailleDisplay1.SetSelection(len(lbl) - 1)
        else:
            self.brailleDisplay1.SetSelection(self.getIdBD(configBE.conf['general']['brailleDisplay1']))
        loadBDs.Add(
            wx.StaticText(
                self, -1, label=_('Braille display to load on NVDA+Shift+k')))
        self.brailleDisplay2 = wx.Choice(self, pos=(-1, -1),
                                choices=lbl)
        if configBE.conf['general']['brailleDisplay2'] == -1:
            self.brailleDisplay2.SetSelection(len(lbl) - 1)
        else:
            self.brailleDisplay2.SetSelection(self.getIdBD(configBE.conf['general']['brailleDisplay2']))
        loadBDs.Add(self.brailleDisplay1)
        loadBDs.Add(self.brailleDisplay2)
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
    getIdBD = lambda self, name: [k[0] for k in braille.getDisplayList()].index(name) if name in [k[0] for k in braille.getDisplayList()] else len(braille.getDisplayList())-1

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
        self.reverseScroll = wx.CheckBox(self, label=_('Reverse forward scroll and back scroll buttons'))
        if configBE.conf['general']['reverseScroll']:
            self.reverseScroll.SetValue(True)

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

class Attribra(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.attribraEnabled = wx.CheckBox(self, label=_('Enable Attribra'))
        if configBE.conf['general']['attribra']:
            self.attribraEnabled.SetValue(True)
        self.profilesLabel = wx.StaticText(self, -1, label=_(u'Profile'))
        self.profiles = wx.Choice(self, pos=(-1, -1), choices=self.getListProfiles())
        self.profiles.SetSelection(0)
        self.profiles.Bind(wx.EVT_CHOICE, self.onProfiles)
        self.bold = wx.CheckBox(self, label=_('Bold'))
        self.italic = wx.CheckBox(self, label=_('Italic'))
        self.underline = wx.CheckBox(self, label=_('Underline'))
        self.spellingErrors = wx.CheckBox(self, label=_('Spelling errors'))
        self.advancedRulesLabel = wx.StaticText(self, -1, label=_(u'Advanced rules'))
        self.advancedRules = wx.Choice(self, pos=(-1, -1), choices=[])
        self.editRuleBtn = wx.Button(self, label=_('&Edit this rule'))
        self.removeRuleBtn = wx.Button(self, label=_('&Remove this rule'))
        self.addRuleBtn = wx.Button(self, label=_('&Add a rule'))

        self.addProfileBtn = wx.Button(self, label=_('Add a profile'))
        self.editProfileBtn = wx.Button(self, label=_('Edit this profile'))
        self.removeProfileBtn = wx.Button(self, label=_('Remove this profile'))
        
        self.addRuleBtn.Bind(wx.EVT_BUTTON, self.onAddRuleBtn)
        self.editRuleBtn.Bind(wx.EVT_BUTTON, self.onEditRuleBtn)
        self.removeRuleBtn.Bind(wx.EVT_BUTTON, self.onRemoveRuleBtn)
        self.addProfileBtn.Bind(wx.EVT_BUTTON, self.onAddProfileBtn)
        self.editProfileBtn.Bind(wx.EVT_BUTTON, self.onEditProfileBtn)
        self.removeProfileBtn.Bind(wx.EVT_BUTTON, self.onRemoveProfileBtn)

        self.spellingErrors.Bind(wx.EVT_CHECKBOX, self.onSpellingErrors)
        self.bold.Bind(wx.EVT_CHECKBOX, self.onBold)
        self.italic.Bind(wx.EVT_CHECKBOX, self.onItalic)
        self.underline.Bind(wx.EVT_CHECKBOX, self.onUnderline)
        return self.onProfiles()

    def onBold(self, event):
        if self.bold.GetValue():
            if not 'bold' in configBE.confAttribra[self.getCurrentProfile()]:
                configBE.confAttribra[self.getCurrentProfile()]['bold'] = [1]
            configBE.confAttribra[self.getCurrentProfile()]['bold'][0] = 1
        else:
            if 'bold' in configBE.confAttribra[self.getCurrentProfile()]:
                del configBE.confAttribra[self.getCurrentProfile()]['bold']
        return

    def onItalic(self, event):
        if self.italic.GetValue():
            if not 'italic' in configBE.confAttribra[self.getCurrentProfile()]:
                configBE.confAttribra[self.getCurrentProfile()]['italic'] = [1]
            configBE.confAttribra[self.getCurrentProfile()]['italic'][0] = 1
        else:
            if 'italic' in configBE.confAttribra[self.getCurrentProfile()]:
                del configBE.confAttribra[self.getCurrentProfile()]['italic']
        return

    def onUnderline(self, event):
        if self.underline.GetValue():
            if not 'underline' in configBE.confAttribra[self.getCurrentProfile()]:
                configBE.confAttribra[self.getCurrentProfile()]['underline'] = [1]
            configBE.confAttribra[self.getCurrentProfile()]['underline'][0] = 1
        else:
            if 'underline' in configBE.confAttribra[self.getCurrentProfile()]:
                del configBE.confAttribra[self.getCurrentProfile()]['underline']
        return

    def onSpellingErrors(self, event):
        if self.spellingErrors.GetValue():
            if not 'invalid-spelling' in configBE.confAttribra[self.getCurrentProfile()]:
                configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling'] = [1]
            configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling'][0] = 1
        else:
            if 'invalid-spelling' in configBE.confAttribra[self.getCurrentProfile()]:
                del configBE.confAttribra[self.getCurrentProfile()]['invalid-spelling']
        return


    def onAddRuleBtn(self, event):
        ui.message(inProcessMsg)
        return
    def onEditRuleBtn(self, event):
        ui.message(inProcessMsg)
        return

    def onRemoveRuleBtn(self, event):
        ui.message(inProcessMsg)
        return

    def onAddProfileBtn(self, event):
        ui.message(inProcessMsg)
        return

    def onEditProfileBtn(self, event):
        ui.message(inProcessMsg)
        return

    def onRemoveProfileBtn(self, event):
        ui.message(inProcessMsg)
        return

    getCurrentProfile = lambda self: 'global' if self.profiles.GetSelection() == 0 else self.getListProfiles(False)[self.profiles.GetSelection()]

    def getAdvancedRules(self):
        profileId = 'global' if self.profiles.GetSelection() == 0 else self.getListProfiles(False)[self.profiles.GetSelection()]
        return [k+': '+configBE.translateRule(configBE.confAttribra[profileId][k]) for k in configBE.confAttribra[profileId].keys() if k not in ['bold','italic','underline','invalid-spelling']]

    getListProfiles = lambda self, t = True: ['Default']+[self.translateApp(k) if t else k for k in configBE.confAttribra.keys() if k != 'global']

    def onProfiles(self, event = None):
        profileId = self.profiles.GetSelection()
        app = 'global' if profileId == 0 else self.getListProfiles(False)[profileId]
        if 'bold' in configBE.confAttribra[app].keys() and self.bold.GetValue() != configBE.confAttribra[app]['bold']:
            self.bold.SetValue(not self.bold.GetValue())
        if not 'bold' in configBE.confAttribra[app].keys():
            self.bold.SetValue(False)
        if 'italic' in configBE.confAttribra[app].keys() and self.italic.GetValue() != configBE.confAttribra[app]['italic']:
            self.italic.SetValue(not self.italic.GetValue())
        if not 'italic' in configBE.confAttribra[app].keys():
            self.italic.SetValue(False)
        if 'underline' in configBE.confAttribra[app].keys() and self.underline.GetValue() != configBE.confAttribra[app]['underline']:
            self.underline.SetValue(not self.underline.GetValue())
        if not 'underline' in configBE.confAttribra[app].keys():
            self.underline.SetValue(False)
        if 'invalid-spelling' in configBE.confAttribra[app].keys() and self.spellingErrors.GetValue() != configBE.confAttribra[app]['invalid-spelling']:
            self.spellingErrors.SetValue(not self.spellingErrors.GetValue())
        if not 'invalid-spelling' in configBE.confAttribra[app].keys():
            self.spellingErrors.SetValue(False)
        self.advancedRules.SetItems(self.getAdvancedRules())
        if len(self.getAdvancedRules()) > 0:
            self.advancedRules.SetSelection(0)
            self.advancedRules.Enable()
            self.editRuleBtn.Enable()
            self.removeRuleBtn.Enable()
        else:
            self.advancedRules.Disable()
            self.editRuleBtn.Disable()
            self.removeRuleBtn.Disable()
        return

    def translateApp(self, app):
        tApps = {
            'winword': 'Microsoft Word',
        }
        return tApps[app]+' (%s)' % app if app in tApps else app.capitalize()

class Keyboard(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        kbCfg = wx.BoxSizer(wx.VERTICAL)
        if not noUnicodeTable:
            lt = [_('Use the current input table')]
            [lt.append(table[1]) for table in tables if table.input]
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input braille table for keyboard shortcut keys')))
            self.iTableSht = wx.Choice(self, pos=(-1, -1), choices=lt)
            self.iTableSht.SetSelection(configBE.conf['general']['iTableSht'] + 1)
            
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input braille tables present in the switch')))
            self.iTablesPresent = wx.Choice(self, pos=(-1, -1), choices=self.inputTablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.deleteInputTableInSwitch = wx.Button(self, label=_('&Remove'))
            self.deleteInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteInputTableInSwitch)
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Input tables not present in the switch')))
            self.iTables = wx.Choice(self, pos=(-1, -1), choices=self.inputTablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.addInputTableInSwitch = wx.Button(self, label=_('&Add'))
            self.addInputTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddInputTableInSwitch)
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Output braille tables present in the switch')))
            self.oTablesPresent = wx.Choice(self, pos=(-1, -1), choices=self.outputTablesInSwitch())
            self.oTablesPresent.SetSelection(0)
            self.deleteOutputTableInSwitch = wx.Button(self, label=_('&Remove'))
            self.deleteOutputTableInSwitch.Bind(wx.EVT_BUTTON, self.onDeleteOutputTableInSwitch)
            kbCfg.Add(wx.StaticText(self, -1, label=_(u'Output tables not present in the switch')))
            self.oTables = wx.Choice(self, pos=(-1, -1), choices=self.outputTablesNotInSwitch())
            self.oTables.SetSelection(0)
            self.addOutputTableInSwitch = wx.Button(self, label=_('&Add'))
            self.addOutputTableInSwitch.Bind(wx.EVT_BUTTON, self.onAddOutputTableInSwitch)
        if gesturesFileExists and not noKC:
            lb = keyboardLayouts
            kbCfg.Add(wx.StaticText(self, -1, label=_('Braille keyboard configuration')))
            self.KBMode = wx.Choice(self, pos=(-1, -1), choices=lb)
            self.KBMode.SetSelection(iniProfile['keyboardLayouts'].keys().index(configBE.conf['general']['keyboardLayout_' + curBD]) if configBE.conf['general']['keyboardLayout_' +configBE.curBD] != None and configBE.conf['general']['keyboardLayout_'+curBD] in iniProfile['keyboardLayouts'].keys() else 0)
            kbCfg.Add(self.KBMode)

    def onDeleteInputTableInSwitch(self, event):
        if self.iTablesPresent.GetStringSelection() != '':
            iTables.remove(configBE.tablesFN[configBE.tablesTR.index(self.iTablesPresent.GetStringSelection())])
            self.iTables.SetItems(self.inputTablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.iTablesPresent.SetItems(self.inputTablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.iTablesPresent.SetFocus()
        else:
            ui.message(_(u"You have no input tables present in the switch"))
        return

    def onAddInputTableInSwitch(self, event):
        if self.iTables.GetStringSelection() != '':
            iTables.append(configBE.tablesFN[configBE.tablesTR.index(self.iTables.GetStringSelection())])
            self.iTables.SetItems(self.inputTablesNotInSwitch())
            self.iTables.SetSelection(0)
            self.iTablesPresent.SetItems(self.inputTablesInSwitch())
            self.iTablesPresent.SetSelection(0)
            self.iTablesPresent.SetFocus()
    
    def onDeleteOutputTableInSwitch(self, event):
        if self.oTablesPresent.GetStringSelection() != '':
            oTables.remove(configBE.tablesFN[configBE.tablesTR.index(self.oTablesPresent.GetStringSelection())])
            self.oTables.SetItems(self.outputTablesNotInSwitch())
            self.oTables.SetSelection(0)
            self.oTablesPresent.SetItems(self.outputTablesInSwitch())
            self.oTablesPresent.SetSelection(0)
            self.oTablesPresent.SetFocus()
        else:
            ui.message(_(u"You have no output tables present in the switch"))
        return

    def onAddOutputTableInSwitch(self, event):
        if self.oTables.GetStringSelection() != '':
            oTables.append(configBE.tablesFN[configBE.tablesTR.index(self.oTables.GetStringSelection())])
            self.oTables.SetItems(self.outputTablesNotInSwitch())
            self.oTables.SetSelection(0)
            self.oTablesPresent.SetItems(self.outputTablesInSwitch())
            self.oTablesPresent.SetSelection(0)
            self.oTablesPresent.SetFocus()

    global tables
    tables = brailleTables.listTables()
    inputTablesNotInSwitch = lambda s: [table[1] for table in tables if table.input and table[0] not in iTables]
    inputTablesInSwitch = lambda s: [configBE.tablesTR[configBE.tablesFN.index(table)] for table in iTables if table != ''] if (len(iTables)>0 and iTables[0] != '') or len(tables) > 2 else []
    outputTablesNotInSwitch = lambda s: [table[1] for table in tables if table.output and table[0] not in oTables]
    outputTablesInSwitch = lambda s: [configBE.tablesTR[configBE.tablesFN.index(table)] for table in oTables if table != ''] if (len(oTables)>0 and oTables[0] != '') or len(tables) > 2 else []

class QuickLaunch(wx.Panel):
    
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        shts = wx.BoxSizer(wx.VERTICAL)
        if gesturesFileExists:
            self.quickKeysT = wx.StaticText(self, -1, label=_('Gestures for the quick launches'))
            self.quickKeys = wx.Choice(self, pos=(-1, -1), choices=self.getQuickLaunchList())
            self.quickKeys.SetSelection(0)
            self.quickKeys.Bind(wx.EVT_CHOICE, self.onQuickKeys)
            self.target = wx.TextCtrl(self, -1, value=quickLaunchS[0])
            self.target.Bind(wx.wx.EVT_TEXT, self.onTarget)
            self.browseBtn = wx.Button(self, -1, label=_(u'&Browse...'))
            self.removeGestureBtn = wx.Button(self, -1, label=_(u'&Remove this gesture'))
            self.addGestureBtn = wx.Button(self, -1, label=_(u'&Add a quick launch'))
            self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowseBtn)
            self.removeGestureBtn.Bind(wx.EVT_BUTTON, self.onRemoveGestureBtn)
            self.addGestureBtn.Bind(wx.EVT_BUTTON, self.onAddGestureBtn)

    getQuickLaunchList = lambda s: [quickLaunch[k]+configBE.sep+': '+quickLaunchS[k] for k in range(len(quickLaunch))]

    def onRemoveGestureBtn(self, event):
        ui.message(inProcessMsg)
        return

    def onAddGestureBtn(self, event):
        ui.message(inProcessMsg)
        return
    
    def onTarget(self, event):
        oldS = self.quickKeys.GetSelection()
        quickLaunchS[self.quickKeys.GetSelection()] = self.target.GetValue()
        self.quickKeys.SetItems(self.getQuickLaunchList())
        return self.quickKeys.SetSelection(oldS)

    def onQuickKeys(self, event):
        self.target.SetValue(self.quickKeys.GetStringSelection().split(': ')[1]) if not self.quickKeys.GetStringSelection().strip().startswith(':') else self.target.SetValue('')
        return

    def onBrowseBtn(self, event):
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
