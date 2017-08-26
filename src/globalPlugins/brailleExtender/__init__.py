# coding: utf-8
import os
import re
import time
import urllib
from collections import OrderedDict

import gui
import wx

import addonHandler
addonHandler.initTranslation()
import braille
import brailleInput
import brailleTables
import config
import cursorManager
import globalPluginHandler
import globalCommands
import inputCore
import languageHandler
import speech
import ui
import versionInfo
from keyboardHandler import KeyboardInputGesture
from logHandler import log

import configBE
import settings
import utils

instanceGP = None
instanceUP = None
noKC = None
lang = configBE.lang

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = configBE._addonName
    hourDatePlayed = False
    autoScrollRunning = False
    modifiers = {
        'control': False,
        'alt': False,
        'windows': False,
        'shift': False,
        'nvda': False,
    }
    _tGestures = OrderedDict()
    _pGestures = OrderedDict()
    if not configBE.noUnicodeTable:
        backupInputTable = brailleInput.handler.table
    backupMessageTimeout = None
    backupShowCursor = False
    backupTether = braille.handler.tether
    switchedMode = False
    instanceST = None
    def __init__(self):
        super(globalPluginHandler.GlobalPlugin, self).__init__()
        global instanceGP
        instanceGP = self
        log.debug('! New instance of GlobalPlugin: {0}'.format(id(instanceGP)))
        configBE.initGestures()
        configBE.loadGestures()
        self.gesturesInit()
        if not self.createMenu():
            log.error(u'Impossible to create menu')
        if time.time()-configBE.conf['general']['lastCheckUpdate'] > 172800:
            CheckUpdates(True)
            configBE.conf['general']['lastCheckUpdate'] = time.time()
        return

    def event_gainFocus(self, obj, nextHandler):
        if self.hourDatePlayed:
            self.script_hourDate(None)
        if self.autoScrollRunning:
            self.script_autoScroll(None)
        if obj.appModule.appName in configBE.reviewModeApps and not self.switchedMode:
            self.backupTether = braille.handler.tether
            self.switchedMode = True
            braille.handler.tether = braille.handler.TETHER_REVIEW
        elif self.switchedMode and obj.appModule.appName not in configBE.reviewModeApps:
            braille.handler.tether = self.backupTether
            self.switchedMode = False
        nextHandler()

    def createMenu(self):
        try:
            self.menu = wx.Menu()
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("Documentation"),
                _("Opens the addon's documentation.")
            )
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.onDoc, self.item)
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("Changelog"),
                _("Opens the addon's changelog.")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU, self.onChangelog, self.item)
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("Settings..."),
                _("Opens the addon's settings.")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU, self.onSettings, self.item)
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("Reload add-on"),
                _("Reload this add-on.")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU, self.onReload, self.item)
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("&Check for update..."),
                _("Checks if update is available")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU,
                self.onUpdate,
                self.item
            )
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("&About..."),
                _("About this addon")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU,
                self.onAbout, self.item
            )
            self.item = self.menu.Append(
                wx.ID_ANY,
                _("&Website"),
                _("Open addon's website.")
            )
            gui.mainFrame.sysTrayIcon.Bind(
                wx.EVT_MENU, self.onWebsite, self.item)
            self.menu = gui.mainFrame.sysTrayIcon.menu.InsertMenu(
                2,
                wx.ID_ANY,
                configBE._addonName,
                self.menu
            )
            return True
        except BaseException:
            return False

    def terminate(self):
        inputCore.manager.localeGestureMap.clear()
        self.removeMenu()
        if configBE.noUnicodeTable:
            brailleInput.handler.table = self.backupInputTable
        if self.hourDatePlayed:
            self.hourDateTimer.Stop()
            if configBE.noMessageTimeout:
                config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
        if self.autoScrollRunning:
            self.autoScrollTimer.Stop()
            config.conf["braille"]["showCursor"] = self.backupShowCursor
        return configBE.saveSettings()

    def removeMenu(self):
        try:
            if self.menu is not None:
                gui.mainFrame.sysTrayIcon.menu.RemoveItem(self.menu)
            return True
        except wx.PyDeadObjectError:
            return False

    def gesturesInit(self):
        global noKC
        gK = OrderedDict()
        try:
            cK = configBE.iniProfile['keyboardLayouts'][configBE.conf['general']['keyboardLayout_' + configBE.curBD]] if configBE.conf['general']['keyboardLayout_' + configBE.curBD] and configBE.conf['general']['keyboardLayout_' + configBE.curBD] in configBE.iniProfile['keyboardLayouts'] != None else configBE.iniProfile['keyboardLayouts'].keys()[0]
            for k in cK:
                if k in ['enter', 'backspace']:
                    if isinstance(cK[k], list):
                        for l in cK[k]:
                            gK[inputCore.normalizeGestureIdentifier(
                                'br(' + configBE.curBD + '):' + l)] = 'kb:' + k
                    else:
                        gK['kb:' + k] = inputCore.normalizeGestureIdentifier(
                            'br(' + configBE.curBD + '):' + cK[k])
                elif k == 'braille_dots':
                    if isinstance(cK[k], list):
                        for i in range(len(cK[k])):
                            if ':' not in cK[k][i]:
                                cK[k][i] = inputCore.normalizeGestureIdentifier(
                                    str('br(' + configBE.curBD + '):') + str(cK[k][i]))
                    else:
                        if ':' not in cK[k]:
                            cK[k] = str('br(' + configBE.curBD + '):') + str(cK[k])
                    gK[k] = cK[k]
            inputCore.manager.localeGestureMap.update({'globalCommands.GlobalCommands': gK})
            noKC = False
            log.debug('Keyboard conf found, loading layout `%s`' %configBE.conf['general']['keyboardLayout_' + configBE.curBD])
        except BaseException:
            log.debug('No keyboard conf found')
            noKC = True

        self._tGestures = {
            "bk:dots": "end_combKeysChar",
            "br(" + configBE.curBD + "):routing": "cancelShortcut",
            #: arrow keys
            "br(" + configBE.curBD + "):up": "end_combKeys",
            "br(" + configBE.curBD + "):down": "end_combKeys",
            "br(" + configBE.curBD + "):left": "end_combKeys",
            "br(" + configBE.curBD + "):right": "end_combKeys",
        }
        if configBE.gesturesFileExists:
            for g in configBE.iniGestures['globalCommands.GlobalCommands']:
                if isinstance(
                        configBE.iniGestures['globalCommands.GlobalCommands'][g],
                        list):
                    for h in range(
                            len(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
                        self._tGestures[inputCore.normalizeGestureIdentifier(
                            str(configBE.iniGestures['globalCommands.GlobalCommands'][g][h]))] = "end_combKeys"
                elif ('kb:' in g and g not in ['kb:alt', 'kb:ctrl', 'kb:windows', 'kb:control', 'kb:applications']):
                    self._tGestures[inputCore.normalizeGestureIdentifier(
                        str(configBE.iniGestures['globalCommands.GlobalCommands'][g]))] = "end_combKeys"
        
            self._pGestures = {}
            for k, v in configBE.iniProfile["modifierKeys"].items()+configBE.iniProfile["miscs"].items():
                if isinstance(v, list):
                    for i in range(len(v)):
                        if k == 'shortcutsOn':
                            pass
                        else:
                            self._pGestures[inputCore.normalizeGestureIdentifier(
                                'br(' + configBE.curBD + '):' + v[i])] = k
                else:
                    self._pGestures[inputCore.normalizeGestureIdentifier(
                        'br(' + configBE.curBD + '):' + v)] = k
            self.bindGestures(self._pGestures)
        return

    def script_position(self, gesture=None):
        return ui.message('{0}% ({1}/{2})'.format(round(utils.getPositionPercentage(),2), utils.getPosition()[0], utils.getPosition()[1]))
    script_position.__doc__=_('Get the cursor position of text')

    def script_hourDate(self, gesture = None):
        if self.autoScrollRunning:
            return
        if self.hourDatePlayed:
            self.hourDateTimer.Stop()
            self.clearMessageFlash()
            if configBE.noMessageTimeout:
                config.conf["braille"]["noMessageTimeout"] = self.backupMessageTimeout
        else:
            if configBE.conf['general']['hourDynamic']:
                if configBE.noMessageTimeout:
                    self.backupMessageTimeout = config.conf["braille"]["noMessageTimeout"]
                    config.conf["braille"]["noMessageTimeout"] = True
            self.showHourDate()
            if configBE.conf['general']['hourDynamic']:
                self.hourDateTimer = wx.PyTimer(self.showHourDate)
                time.sleep(1.02 - round(time.time() - int(time.time()), 3))
                self.showHourDate()
                self.hourDateTimer.Start(1000)
            else:
                return
        self.hourDatePlayed = not self.hourDatePlayed
        return

    script_hourDate.__doc__ = _('Hour and date with autorefresh')

    def showHourDate(self):
        currentHourDate = time.strftime(
            u'%X %x (%a, %W/53, %b)', time.localtime())
        return braille.handler.message(currentHourDate.decode('mbcs'))

    def script_autoScroll(self, gesture):
        if self.hourDatePlayed:
            return
        if self.autoScrollRunning:
            self.autoScrollTimer.Stop()
            ui.message(_(u'Autoscroll stopped'))
            config.conf["braille"]["showCursor"] = self.backupShowCursor
        else:
            self.backupShowCursor = config.conf["braille"]["showCursor"]
            config.conf["braille"]["showCursor"] = False
            self.autoScrollTimer = wx.PyTimer(self.autoScroll)
            self.autoScrollTimer.Start(
                configBE.conf['general']['delayScroll_' + configBE.curBD] * 1000)
        self.autoScrollRunning = not self.autoScrollRunning
        return

    script_autoScroll.__doc__ = _('Enable/disable autoscroll')

    def autoScroll(self):
        return braille.handler.scrollForward()

    def script_volumePlus(s, g):
        KeyboardInputGesture.fromName('volumeup').send()
        s = str(utils.getVolume()) + _('% (master volume)')
        braille.handler.message(s) if configBE.conf['general']['reportvolumeb'] else None
        speech.speakMessage(s) if configBE.conf['general']['reportvolumes'] else None
        return
    script_volumePlus.__doc__ = _('Increase the master volume')

    def clearMessageFlash(self):
        if config.conf["braille"]["messageTimeout"] != 0:
            braille.handler.message("?")
            braille.handler.routeTo(1)

    def script_volumeMinus(s, g):
        KeyboardInputGesture.fromName('volumedown').send()
        s = str(utils.getVolume()) + _('% (master volume)')
        braille.handler.message(s) if configBE.conf['general']['reportvolumeb'] else None
        speech.speakMessage(s) if configBE.conf['general']['reportvolumes'] else None
        return

    script_volumeMinus.__doc__ = _('Decrease the master volume')

    def script_toggleVolume(s, g):
        KeyboardInputGesture.fromName('volumemute').send()
        if utils.getMute() and configBE.conf['general']['reportvolumeb']:
            return braille.handler.message(_('Muted sound'))
        s = _('Unmuted sound') + ' (' + str(utils.getVolume()) + _('%)')
        if configBE.conf['general']['reportvolumes']:
            speech.speakMessage(s)
        if configBE.conf['general']['reportvolumeb']:
            braille.handler.message(s)
        return

    script_toggleVolume.__doc__ = _('Mute or unmute sound')

    def script_getHelp(s, g):
        return s.getDoc()
    script_getHelp.__doc__ = _('Show the %s documentation') % configBE._addonName

    def getKeyboardLayouts(self):
        i = 0
        lb = []
        if not noKC and 'keyboardLayouts' in configBE.iniProfile:
            for layout in configBE.iniProfile['keyboardLayouts']:
                t = []
                for lk in configBE.iniProfile['keyboardLayouts'][layout]:
                    if lk == 'braille_dots':
                        if isinstance(configBE.iniProfile['keyboardLayouts'][layout][lk], list):
                            t.append(utils.beautifulSht(
                                ' / '.join(configBE.iniProfile['keyboardLayouts'][layout][lk]), 1) + configBE.sep + ': ' + _(u'input braille dot'))
                        else:
                            t.append(utils.beautifulSht(
                                str(configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + _(u'input braille dot'))
                    else:
                        if isinstance(configBE.iniProfile['keyboardLayouts'][layout][lk], list):
                            t.append(utils.beautifulSht(
                                ' / '.join(configBE.iniProfile['keyboardLayouts'][layout][lk]), 1) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
                        else:
                            t.append(utils.beautifulSht(
                                str(configBE.iniProfile['keyboardLayouts'][layout][lk])) + configBE.sep + ': ' + utils.getKeysTranslation(lk))
                lb.append((configBE.sep + '; ').join(t))
        return lb

    def getDocScript(s, n):
        doc = None
        if type(n) == list:
            n = str(n[-1][-1])
        if n.startswith('kb:'):
            return _('Emulates pressing %s on the system keyboard') % utils.getKeysTranslation(n)
        places = ['s.script_','globalCommands.commands.script_','cursorManager.CursorManager.script_']
        for place in places:
            try:
                doc = re.sub(r'\.$', '', eval(''.join([place, n, '.__doc__'])))
                break
            except BaseException:
                pass
        return doc if doc != None else '`%s`' % n

    def translateLst(s, lst):
        doc = u'<ul>'
        for g in lst:
            if 'kb:' in g and 'capsLock' not in g and 'insert' not in g:
                if isinstance(lst[g], list):
                    doc += u'<li>{0} ≡ {1}{2};</li>'.format(utils.beautifulSht(' / '.join(lst[g]).replace('br(' + configBE.curBD + '):', ''), 1), utils.getKeysTranslation(g), configBE.sep)
                else:
                    doc += u'<li>{0} ≡ {1}{2};</li>'.format(utils.beautifulSht(str(lst[g])), utils.getKeysTranslation(g), configBE.sep)
            elif 'kb:' in g:
                gt = _('caps lock') if 'capsLock' in g else g
                doc += u'<li>{0} ≡ {1}{2};</li>'.format(
                    utils.beautifulSht(
                        lst[g]).replace(
                        'br(' + configBE.curBD + '):',
                        ''),
                    gt.replace(
                        'kb:',
                        ''),
                    configBE.sep)
            else:
                if isinstance(lst[g], list):
                    doc += u'<li>{0}{1}: {2}{3};</li>'.format(
                        utils.beautifulSht(
                            ' / '.join(
                                lst[g]).replace(
                                'br(' + configBE.curBD + '):',
                                ''),
                            1),
                        configBE.sep,
                        re.sub(
                            '^([A-Z])',
                            lambda m: m.group(1).lower(),
                            utils.uncapitalize(s.getDocScript(g))),
                        configBE.sep)
                else:
                    doc += u'<li>{0}{1}: {2}{3};</li>'.format(
                        utils.beautifulSht(
                            lst[g]).replace(
                            'br(' + configBE.curBD + '):',
                            ''),
                        configBE.sep,
                        re.sub(
                            '^([A-Z])',
                            lambda m: m.group(1).lower(),
                            utils.uncapitalize(s.getDocScript(g))),
                        configBE.sep)
        doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
        doc += u'</ul>'
        return doc

    def getDoc(s):
        if not configBE.gesturesFileExists:
            return ui.message(_("No braille display supported found."))
        doc = u''
        doc += u'<h1>' + _('{0}\'s documentation{1}: {2} braille display').format(
            configBE._addonName, configBE.sep, configBE.curBD.capitalize()) + '</h1>'
        doc += u'<p>Version {0}<br />{1}<br />{2}</p>'.format(
            configBE._addonVersion,
            configBE._addonAuthor.replace(
                '<',
                '&lt;').replace(
                '>',
                '&gt;'),
            '<a href="' +
            configBE._addonURL +
            '">' +
            configBE._addonURL +
            '</a>')
        doc += '<pre>' + configBE._addonDesc + '</pre>'
        mKB = OrderedDict()
        mNV = OrderedDict()
        mW = OrderedDict()
        for g in configBE.iniGestures['globalCommands.GlobalCommands'].keys():
            if 'kb:' in g:
                if '+' in g:
                    mW[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
                else:
                    mKB[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
            else:
                mNV[g] = configBE.iniGestures['globalCommands.GlobalCommands'][g]
        doc += ('<h2>' + _('Simple keys') +
                ' (%s)</h2>') % str(len(mKB))
        doc += s.translateLst(mKB)
        doc += ('<h2>' + _('Usual shortcuts') +
                ' (%s)</h2>') % str(len(mW))
        doc += s.translateLst(mW)

        doc += ('<h2>' + _('Standard NVDA commands') +
                ' (%s)</h2>') % str(len(mNV))
        doc += s.translateLst(mNV)
        doc += '<h2>{0} ({1})</h2>'.format(_('Modifier keys'), len(configBE.iniProfile["modifierKeys"]))
        doc += s.translateLst(configBE.iniProfile["modifierKeys"])
        doc += '<h2>' + _('Quick navigation keys') + '</h2>'
        doc += _(u'<p>In virtual documents (HTML/PDF/…) you can navigate element type by element type using keyboard. These navigation keys should work with your braille terminal equally.</p><p>In addition to these, there are some specific shortcuts:</p>')
        doc += s.translateLst(configBE.iniGestures['cursorManager.CursorManager'])
        doc += ('<h2>' + _('Gadget commands') +
                ' (%s)</h2>') % str(len(configBE.iniProfile["miscs"]))
        doc += s.translateLst(configBE.iniProfile["miscs"])
        doc += ('<h2>' + _('Shortcuts on system keyboard specific to the add-on') +
                ' (%s)</h2>') % str(len(s.__gestures))
        doc += '<ul>'
        for g in s.__gestures:
            doc += (u'<li>{0}{1}: {2}{3};</li>').format(utils.getKeysTranslation(g), configBE.sep, re.sub(
                '^([A-Z])', lambda m: m.group(1).lower(), s.getDocScript(s.__gestures[g])), configBE.sep)
        doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
        doc += '</ul>'
        doc += u'<h2>{0} ({1})</h2>'.format(_('Shortcuts defined outside add-on'), len(braille.handler.display.gestureMap._map))
        doc += '<ul>'
        for g in braille.handler.display.gestureMap._map:
            doc += (u'<li>{0}{1}: {2}{3};</li>').format(
            utils.beautifulSht(g).capitalize(),
            configBE.sep,
            utils.uncapitalize(re.sub('^([A-Z])', lambda m: m.group(1).lower(), s.getDocScript(braille.handler.display.gestureMap._map[g]))),
            configBE.sep)
        doc = re.sub(r'[  ]?;(</li>)$', r'.\1', doc)
        doc += '</ul>'

        # list keyboard layouts
        if not noKC and 'keyboardLayouts' in configBE.iniProfile:
            lb = s.getKeyboardLayouts()
            doc += '<h2>{}</h2>'.format(_('Keyboard configurations provided'))
            doc += u'<p>{}{}:</p><ol>'.format(
                _('Keyboard configurations are'), configBE.sep)
            for l in lb:
                doc += u'<li>{}.</li>'.format(l)
            doc += '</ol>'
        return ui.browseableMessage(
            doc, _(u'%s\'s documentation') %
            configBE._addonName, True)

    def script_quickLaunch(self, gesture):
        try:
            return os.startfile(configBE.quickLaunchS[configBE.quickLaunch.index('+'.join(sorted((gesture.id).lower().split('+'))))].strip())
        except BaseException:
            return ui.message(_("No such file or directory"))
    script_quickLaunch.__doc__=_('Opens a custom program/file. Go to settings to define them')

    def script_checkUpdate(self, gesture):
        CheckUpdates()
        return

    script_checkUpdate.__doc__ = _(
        'Check for %s updates, and starts the download if there is one') % configBE._addonName
    def increaseDelayAutoScroll():
        return

    def decreaseDelayAutoScroll():
    
        returnn
    
    def script_switchKeyboardLayout(self, gesture):
        self.clearGestureBindings()
        ls = configBE.iniProfile['keyboardLayouts'].keys()
        if (configBE.conf['general']['keyboardLayout_' + configBE.curBD] in ls
            and ls.index(configBE.conf['general']['keyboardLayout_'+configBE.curBD]) < len(ls)):
            id = ls.index(configBE.conf['general']['keyboardLayout_' + configBE.curBD])
            (nId,id) = (ls[id+1], id+1) if id+1 < len(ls) else (ls[0],0)
        else:
            (nId, id) = (ls[0],0)
        configBE.conf['general']['keyboardLayout_' + configBE.curBD] = nId
        ui.message(_("Configuration {0} ({1})").format(str(ls.index(nId)+1), self.getKeyboardLayouts()[id]))
        configBE.saveSettings()
        return self.onReload(None, True)

    script_switchKeyboardLayout.__doc__ = _(
        "Switch between different braille keyboard configurations.")

    def script_switchBrailleTable(self, gesture):
        if configBE.noUnicodeTable:
            return ui.message(_("Please use NVDA 2017.3 minimum for this feature"))
        iTables = configBE.conf['general']['iTables']
        lTables = [t[0] for t in brailleTables.listTables()]
        if not type(iTables) == list:
            iTables = iTables.replace(', ',',').split(',')
        iTables = [t for t in iTables if t in lTables]
        if len(iTables) < 2:
            return ui.message(_('You must choose at least two tables for this feature. Please fill in the settings'))
        if not config.conf["braille"]["inputTable"] in iTables:
            iTables.append(config.conf["braille"]["inputTable"])
        id = iTables.index(config.conf["braille"]["inputTable"])
        nID = id+1 if id+1<len(iTables) else 0
        brailleInput.handler.table = brailleTables.listTables()[lTables.index(iTables[nID])]
        return ui.message(brailleInput.handler.table.displayName)

    script_switchBrailleTable.__doc__ = _("Switch between his favorite input braille tables")

    def script_brlDescChar(self, gesture):
        utils.currentCharDesc()
    script_brlDescChar.__doc__ = _(
        "Gives the Unicode value of the "
        "character where the cursor is located "
        "and the decimal, binary and octal equivalent.")

    def script_showConstructST(self, gesture):
        configBE.conf['general']['showConstructST'] = not configBE.conf['general']['showConstructST']
        if configBE.conf['general']['showConstructST']:
            return ui.message(_("Disabled (assist shortcuts)."))
        else:
            return ui.message(_("Enabled (assist shortcuts)."))

    script_showConstructST.__doc__ = _('Turn on/off the assistance shortcuts.')

    def onDoc(self, evt):
        return self.getDoc()

    def onChangelog(self, evt):
        loc = '\\'.join(os.path.abspath(__file__).split('\\')[:-3]) + "\\doc\\" + lang.lower() + '\\changelog.html'
        ok = os.path.exists(loc)
        if not ok and gui.messageBox(_('Currently, the Changelog is not available in your language: Do you want open the French version?'),_('%s Changelog') %configBE._addonName, wx.YES_NO | wx.ICON_WARNING) != wx.YES: return
        return os.startfile(loc if ok else '\\'.join(os.path.abspath(__file__).split('\\')[:-3]) + "\\doc\\fr\\changelog.html")

    def onReload(self, evt=None, sil=False, sv=False):
        if sv:
            configBE.saveSettings()
        configBE.checkConfigPath()
        configBE.initGestures()
        configBE.loadConf()
        configBE.loadGestures()
        self.gesturesInit()
        if not sil:
            ui.message(_('%s reloaded') % configBE._addonName)
        return

    def onUpdate(self, evt):
        return CheckUpdates()
        
    def onAbout(self, evt):
        msg = (
            _(u"Copyright (C) 2017 André-Abush Clause, and other contributors:") +
            "\r\n" +
            _(u"* All testers."))
        msg += "\nURL: " + configBE._addonURL + "\n"
        dlg = wx.MessageDialog(
            None, msg, _(
                "About %s" %
                (configBE._addonName) + " " + configBE._addonVersion), wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
        return

    def onWebsite(self, evt):
        return os.startfile(configBE._addonURL)

    def script_reloadAddon(self, gesture):
        return self.onReload()
    script_reloadAddon.__doc__ = _('Reload %s') % configBE._addonName

    def script_reload_brailledisplay(self, gesture):
        i = 2 if 'shift' in gesture.normalizedIdentifiers[0] else 1
        if configBE.conf['general']['favbd'+str(i)] == -1 or braille.getDisplayList()[configBE.conf['general']['favbd'+str(i)]][0] == 'noBraille':
            if config.conf["braille"]["display"] == 'noBraille':
                return ui.message(_('No braille display specified. No reload to do')) 
            else:
                utils.reload_brailledisplay(config.conf["braille"]["display"])
                configBE.curBD = config.conf["braille"]["display"]
        else:
            utils.reload_brailledisplay(braille.getDisplayList()[configBE.conf['general']['favbd'+str(i)]][0])
            configBE.curBD = braille.getDisplayList()[configBE.conf['general']['favbd'+str(i)]][0]
        return self.onReload(None, True)

    script_reload_brailledisplay.__doc__ = _('Reload the driver of an favorite or last braille display. Practical if the braille display is not plugged immediately or that the latter is disconnected and then reconnected')

    def shortcutInProgress(self):
        for k in self.modifiers:
            if self.modifiers[k]:
                return True
        return False

    def lenModifiers(self):
        return len([k for k in self.modifiers if self.modifiers[k]])

    def clearModifiers(self):
        self.modifiers = {k: False for k in self.modifiers}
        self.clearGestureBindings()
        self.bindGestures(self.__gestures)
        return self.bindGestures(self._pGestures)

    def sendCombKeys(self, sendKS, send=True):
        self.clearModifiers()
        if send:
            log.debug("Sending " + sendKS)
            KeyboardInputGesture.fromName(sendKS).send() if not sendKS == "" else None
        return

    def script_end_combKeys(self, gesture):
        _tmpGesture = {
            'up': 'uparrow',
            'down': 'downarrow',
            'left': 'leftarrow',
            'right': 'rightarrow',
        }
        for g in configBE.iniGestures['globalCommands.GlobalCommands']:
            if isinstance(configBE.iniGestures['globalCommands.GlobalCommands'][g], list):
                for h in range(
                        len(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
                    _tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g][h])).replace(
                        'br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
            elif ('kb:' in g and g not in ['kb:alt', 'kb:ctrl', 'kb:windows', 'kb:control', 'kb:applications'] and 'br(' + configBE.curBD + '):' in str(configBE.iniGestures['globalCommands.GlobalCommands'][g])):
                _tmpGesture[inputCore.normalizeGestureIdentifier(str(configBE.iniGestures['globalCommands.GlobalCommands'][g])).replace('br(' + configBE.curBD + '):', '')] = g.replace('kb:', '')
            gId = inputCore.normalizeGestureIdentifier('br(' + configBE.curBD + '):' + str(gesture.id)).replace('br(' + configBE.curBD + '):', '')
        sht = self.getActualModifiers(False) +_tmpGesture[gId]
        if not gId in _tmpGesture:
            return ui.message("Unknown " + gId)
        return self.sendComb(sht)

    def script_end_combKeysChar(self, gesture):
        self.sendComb(self.getActualModifiers(False) + utils.bkToChar(gesture.dots, brailleTables.listTables()[configBE.conf['general']['iTableSht']][0]) if not configBE.noUnicodeTable and configBE.conf['general']['iTableSht'] > - 1 and configBE.conf['general']['iTableSht'] < nbTables else self.getActualModifiers(False) + utils.bkToChar(gesture.dots))

    def sendComb(self, sht):
        self.clearMessageFlash()
        self.clearModifiers()
        NVDASht = utils.sendCombKeysNVDA(sht)
        if not NVDASht and not 'nvda' in sht.lower():
            try:
                return self.sendCombKeys(sht)
            except BaseException:
                return ui.message('Unable to send %s' % sht)
        elif not NVDASht: # and 'nvda' in sht.lower()
            return ui.message(_(u'%s is not part of a basic NVDA commands') % sht)

    def initCombKeys(self):
        self.bindGestures(self._tGestures) if self.lenModifiers() == 1 else None

    def getActualModifiers(self, short=True):
        s = ""
        t = {'windows': _('WIN'),'control': _('CTRL'),'shift': _('SHIFT'),'alt': _('ALT'),'nvda': 'NVDA'}
        if configBE.conf['general']['showConstructST']:
            for k in [k for k in self.modifiers if self.modifiers[k]]:
                s += t[k] + '+' if short else k + '+'
        return ui.message(s + '...') if short and self.lenModifiers() != 0 else s if not short else self.script_cancelShortcut(None)

    def script_ctrl(self, gesture = None, sil=True):
        self.modifiers["control"] = not self.modifiers["control"]
        self.getActualModifiers() if sil else None
        return self.initCombKeys()

    def script_nvda(self, gesture = None):
        self.modifiers["nvda"] = not self.modifiers["nvda"]
        self.getActualModifiers()
        return self.initCombKeys()

    def script_alt(self, gesture = None, sil=True):
        self.modifiers["alt"] = not self.modifiers["alt"]
        self.getActualModifiers() if sil else None
        return self.initCombKeys()

    def script_win(self, gesture = None, sil=True):
        self.modifiers["windows"] = not self.modifiers["windows"]
        self.getActualModifiers() if sil else None
        return self.initCombKeys()

    def script_shift(self, gesture = None, sil=True):
        self.modifiers["shift"] = not self.modifiers["shift"]
        self.getActualModifiers() if sil else None
        return self.initCombKeys()

    def script_ctrlWin(self, gesture):
        self.script_ctrl(None, False)
        return self.script_win(None)

    def script_altWin(self, gesture):
        self.script_alt(None, False)
        return self.script_win(None)

    def script_winShift(self, gesture):
        self.script_shift(None, False)
        return self.script_win(None)

    def script_ctrlShift(self, gesture):
        self.script_ctrl(None, False)
        return self.script_shift(None)

    def script_ctrlWinShift(self, gesture):
        self.script_ctrl(None, False)
        self.script_shift(None, False)
        return self.script_win(None)

    def script_altShift(self, gesture):
        self.script_alt(None, False)
        return self.script_shift()

    def script_altWinShift(self, gesture):
        self.script_alt(None, False)
        self.script_shift(None, False)
        return self.script_win()

    def script_ctrlAlt(self, gesture):
        self.script_ctrl(None, False)
        return self.script_alt()

    def script_ctrlAltWin(self, gesture):
        self.script_ctrl(None, False)
        self.script_alt(None, False)
        return self.script_win()

    def script_ctrlAltShift(self, gesture):
        self.script_ctrl(None, False)
        self.script_alt(None, False)
        return self.script_shift()

    def script_ctrlAltWinShift(self, gesture):
        self.script_ctrl(None, False)
        self.script_alt(None, False)
        self.script_shift(None, False)
        return self.script_win()

    def script_cancelShortcut(self, g):
        ui.message(_("Cancelling shortcut."))
        return self.sendCombKeys("", False)

    # /* docstrings for modifier keys */
    docS = [_('Emulate pressing down '), _(' on the system keyboard')]
    script_ctrl.__doc__ = docS[0] + "CTRL" + docS[1]
    script_alt.__doc__ = docS[0] + "ALT" + docS[1]
    script_win.__doc__ = docS[0] + "Windows" + docS[1]
    script_shift.__doc__ = docS[0] + "SHIFT" + docS[1]
    script_nvda.__doc__ = docS[0] + "NVDA" + docS[1]
    script_altShift.__doc__ = docS[0] + "ALT+SHIFT" + docS[1]
    script_ctrlShift.__doc__ = docS[0] + "CTRL+SHIFT" + docS[1]
    script_ctrlAlt.__doc__ = docS[0] + "CTRL+Alt" + docS[1]
    script_ctrlAltShift.__doc__ = docS[0] + \
        "CTRL+Alt+SHIFT" + docS[1]
    script_ctrlWin.__doc__ = docS[0] + "CTRL+Windows" + docS[1]
    script_altWin.__doc__ = docS[0] + "ALT+Windows" + docS[1]
    script_winShift.__doc__ = docS[0] + "Windows+SHIFT" + docS[1]
    script_altWinShift.__doc__ = docS[0] + \
        "ALT+Windows+SHIFT" + docS[1]
    script_ctrlWinShift.__doc__ = (docS[0] +
                                             "CTRL+SHIFT+Windows" +
                                             docS[1])
    script_ctrlAltWin.__doc__ = docS[0] + \
        "CTRL+Alt+Windows" + docS[1]
    script_ctrlAltWinShift.__doc__ = (docS[0] +
                                                "CTRL+Alt+SHIFT+Windows" +
                                                docS[1])

    def onSettings(self, event):
        settings.Settings(configBE.curBD, configBE.reviewModeApps, configBE.noUnicodeTable, noKC, configBE.gesturesFileExists, configBE.iniProfile, configBE.quickLaunch, configBE.quickLaunchS, instanceGP, self.getKeyboardLayouts(), configBE.backupDisplaySize, configBE.conf['general']['iTables'])

    __gestures = {
        "kb:nvda+k": "reload_brailledisplay",
        "kb:nvda+shift+k": "reload_brailledisplay",
        "kb:windows+nvda+k": "reloadAddon"}

class CheckUpdates(wx.Dialog):
    def __init__(self, sil = False):
        global instanceUP
        if instanceUP != None:
            return
        instanceUP = self
        title = _('{0} update').format(configBE._addonName)
        newUpdate = False
        params={
                "v": "1.1",
                "version": configBE._addonVersion,
                "versionNVDA": versionInfo.version,
                "language": languageHandler.getLanguage(),
                "installed": config.isInstalledCopy(),
               }
        url = '{0}BrailleExtender.latest?{1}'.format(configBE._addonURL, urllib.urlencode(params))
        log.info(url)
        try:
            page = urllib.urlopen(url)
            pageContent = page.read()
            pageContent = re.sub('\s+$', '', pageContent)
            if (page.code == 200 and pageContent.replace('_', '-') != configBE._addonVersion and len(pageContent) < 20):
                newUpdate = True
                msg = _("New version available, version %s. Do you want download it now?") % pageContent.strip()
            else:
                msg = _("You are up-to-date. %s is the latest version.") % configBE._addonVersion
        except BaseException:
            msg = _("Unable to Check for Update.")
        if not newUpdate and sil:
            return
        wx.Dialog.__init__(self, None, title=_("BrailleExtender's Update"))
        self.msg = wx.StaticText(self, -1, label=msg)
        if newUpdate:
            self.yesBTN = wx.Button(self, wx.ID_YES, label=_("Yes"))
            self.noBTN = wx.Button(self, label=_("No"), id=wx.ID_CLOSE)
            self.yesBTN.Bind(wx.EVT_BUTTON, self.onYes)
            self.noBTN.Bind(wx.EVT_BUTTON, self.onClose)
        else:
            self.okBTN = wx.Button(self, label=_("OK"), id=wx.ID_CLOSE)
            self.okBTN.Bind(wx.EVT_BUTTON, self.onClose)
        self.EscapeId = wx.ID_CLOSE
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Show(True)
        return

    def onYes(self, event):
        global instanceUP
        self.Destroy()
        os.startfile(str((configBE._addonURL + "latest")))
        instanceUP = None
        return

    def onClose(self, event):
        global instanceUP
        self.Destroy()
        instanceUP = None
        return
