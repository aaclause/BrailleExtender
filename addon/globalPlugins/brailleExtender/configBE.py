# coding: utf-8
from os import path as osp
import ui
import re
from cStringIO import StringIO
from configobj import ConfigObj
from validate import Validator

from colors import RGB

import addonHandler
addonHandler.initTranslation()
import braille
import config
import inputCore
import languageHandler
from logHandler import log

curBD = braille.handler.display.name
cfgFile = config.getUserDefaultConfigPath() + '\\BrailleExtender.conf'
cfgFileAttribra = config.getUserDefaultConfigPath() + '\\attribra-BE.ini'
reviewModeApps = []
quickLaunch = []
quickLaunchS = []
backupDisplaySize = braille.handler.displaySize
conf = {}
iniGestures = {}
iniProfile = {}
confAttribra = {}
profileFileExists = gesturesFileExists = False
lang = languageHandler.getLanguage().split('_')[-1].lower()
noMessageTimeout = True if 'noMessageTimeout' in config.conf["braille"] else False
sep = u' ' if 'fr' in lang else ''
oTables = iTables = None
_addonDir = osp.join(osp.dirname(__file__), "..", "..").decode("mbcs")
_addonName = addonHandler.Addon(_addonDir).manifest['name']
_addonVersion = addonHandler.Addon(_addonDir).manifest['version']
_addonURL = addonHandler.Addon(_addonDir).manifest['url']
_addonAuthor = addonHandler.Addon(_addonDir).manifest['author']
_addonDesc = addonHandler.Addon(_addonDir).manifest['description']
profilesDir = osp.join(osp.dirname(__file__), "", "") + \
    ('Profiles/').decode('utf-8').encode('mbcs')
log.error('Profiles\' path not found') if not osp.exists(profilesDir) else log.debug('Profiles\' path (%s) found' % profilesDir)
begFileAttribra = """# Attribra for BrailleExtender
# Thanks to Alberto Zanella
# -> https://github.com/albzan/attribra/
"""
try:
    import brailleTables
    tablesFN = [t[0] for t in brailleTables.listTables()]
    tablesTR = [t[1] for t in brailleTables.listTables()]
    noUnicodeTable = False
except BaseException:
    noUnicodeTable = True

def loadConf():
    global conf, reviewModeApps, quickLaunch, quickLaunchS, gesturesFileExists, iTables, oTables
    kld = iniProfile['keyboardLayouts'].keys()[0] if gesturesFileExists else None
    confspec = ConfigObj(StringIO("""
    [general]
        autoCheckUpdate = boolean(default=True)
        lastCheckUpdate = float(min=0, default=0)
        keyboardLayout_{CUR_BD} = string(default={KEYBOARDLAYOUT})
        showConstructST = boolean(default=True)
        brailleDisplay1 = string(default="noBraille")
        brailleDisplay2 = string(default="noBraille")
        reportVolumeBraille = boolean(default=True)
        reportVolumeSpeech = boolean(default=False)
        reviewModeApps = string(default="cmd, putty, bash, powershell")
        hourDynamic = boolean(default=True)
        limitCells_{CUR_BD} = integer(min=0, default=0, max={MAX_CELLS})
        delayScroll_{CUR_BD} = float(min=0, default=3, max={MAX_DELAYSCROLL})
        smartDelayScroll = boolean(default=False)
        reverseScroll = boolean(default=False)
        ignoreBlankLineScroll = boolean(default=True)
        iTableSht = integer(min=-1, default=-1, max={MAX_TABLES})
        iTables = string(default="{ITABLE}")
        oTables = string(default="{OTABLE}")
        quickLaunch_{CUR_BD} = string(default="notepad; wordpad; calc; cmd")
        attribra = boolean(default=True)
    """.format(
            CUR_BD=curBD,
            MAX_BD=42,
            ITABLE=config.conf["braille"]["inputTable"]+', unicode-braille.utb',
            OTABLE=config.conf["braille"]["translationTable"],
            MAX_CELLS=420,
            MAX_DELAYSCROLL=999,
            MAX_TABLES=420,
            KEYBOARDLAYOUT=kld
        )), encoding="UTF-8", list_values=False)
    confspec.initial_comment = ['%s (%s)' % (_addonName, _addonVersion), _addonURL]
    confspec.final_comment = ['End Of File']
    confspec.newlines = "\n"
    conf = ConfigObj(cfgFile, configspec=confspec,
                     indent_type="\t", encoding="UTF-8")
    result = conf.validate(Validator())
    if result is not True:
        log.error('Malformed configuration file')
        return False
    else:
        if conf['general']['limitCells_' +
                           curBD] <= backupDisplaySize and conf['general']['limitCells_' +
                                                                           curBD] > 0:
            braille.handler.displaySize = conf['general']['limitCells_' + curBD]
        reviewModeApps = re.sub(',{2,}', ',', conf['general']['reviewModeApps'].strip())
        reviewModeApps = re.sub(
            '(, +| +,)([^ ,])',
            r',\2',
            reviewModeApps).split(',')
    quickLaunchS = ''.join(conf['general']['quickLaunch_'+curBD].strip().lower().split(';')) if type(conf['general']['quickLaunch_'+curBD]) == list else conf['general']['quickLaunch_'+curBD].strip().lower().split(';')
    quickLaunchS = [k.strip() for k in quickLaunchS]
    if not noUnicodeTable:
        lITables = [table[0] for table in brailleTables.listTables() if table.input]
        lOTables = [table[0] for table in brailleTables.listTables() if table.output]
        iTables = conf['general']['iTables']
        oTables = conf['general']['oTables']
        if not type(iTables) == list:
            iTables = iTables.replace(', ',',').split(',')
        if not type(oTables) == list:
            oTables = oTables.replace(', ',',').split(',')
        iTables = [t for t in iTables if t in lITables]
        oTables = [t for t in oTables if t in lOTables]
    return True


def loadGestures():
    if gesturesFileExists:
        if osp.exists(profilesDir +('_BrowseMode/' + '/' + config.conf["braille"]["inputTable"] + '.ini').decode('utf-8').encode('mbcs')):
            GLng = config.conf["braille"]["inputTable"]
        else:
            GLng = 'en-us-comp8.ctb'
        gesturesBMPath = profilesDir + ('_BrowseMode/common.ini').decode('utf-8').encode('mbcs')
        gesturesLangBMPath = profilesDir + ('_BrowseMode/'+GLng+'.ini').decode('utf-8').encode('mbcs')
        inputCore.manager.localeGestureMap.clear()
        inputCore.manager.localeGestureMap.load(gesturesBDPath())
        for fn in [gesturesBMPath, gesturesLangBMPath]:
            f = open(fn)
            tmp = [line.strip().replace(' ','').replace('$',iniProfile['general']['nameBK']).replace('=', '=br(%s):'% curBD) for line in f if line.strip() and not line.strip().startswith('#') and line.count('=') == 1]
            tmp = {k.split('=')[0]: k.split('=')[1] for k in tmp}
            inputCore.manager.localeGestureMap.update({'browseMode.BrowseModeTreeInterceptor': tmp})
    return


def saveSettings():
    global conf
    """
    Save the current configuration.
    """
    try:
        conf.validate(Validator(), copy=True)
        conf.write()
        log.debug('%s add-on configuration saved' % _addonName)
    except BaseException:
        log.exception('Cannot save Configuration')
    return

def translateRule(E):
        r = []
        for e in E:
            if type(e) == RGB:
                r.append('"RGB(%s, %s, %s)"' % (e.red, e.green, e.blue))
            else:
                r.append('"%s"'% e)
        return ', '.join(r)

def saveSettingsAttribra():
    global confAttribra
    try:
        f = open(config.getUserDefaultConfigPath() + '\\attribra-BE.ini', "w")
        c = begFileAttribra+'\n'
        for k in sorted(confAttribra.keys()):
            c += '[%s]\n' % k
            for kk, v in confAttribra[k].items():
                if kk not in ['bold','italic','underline','invalid-spelling']:
                    vv = translateRule(v)
                else:
                    vv = v[0]
                c += '%s = %s\n' % (kk, vv)
            c += '\n'
        f.write(c)
        f.close()
    except BaseException, e:
        ui.message('Error: '+str(e))
    return

def checkConfigPath():
    global profileFileExists, iniProfile, quickLaunch
    configPath = profilesDir + \
        (curBD + '/profile.ini').decode('utf-8').encode('mbcs')
    if osp.exists(configPath):
        log.debug('Config\'s path for `%s` found' % curBD)
        profileFileExists = True
        confGen = osp.join(osp.join(osp.dirname(__file__),
                                    "..",
                                    "").decode("mbcs"), configPath)
        confspec = ConfigObj(StringIO("""
        """), encoding="UTF-8", list_values=False)
        iniProfile = ConfigObj(confGen, configspec=confspec,
                            indent_type="\t", encoding="UTF-8")
        result = iniProfile.validate(Validator())
        if result is not True:
            log.exception('Malformed configuration file')
            return False
        else:
            if type(iniProfile['miscs']['quickLaunch']) ==list:
                tmp = ', '.join(iniProfile['miscs']['quickLaunch']).strip().lower().split(',')
            else:
                tmp = iniProfile['miscs']['quickLaunch'].strip().lower().split(',')
            quickLaunch = ['+'.join(sorted(k.strip().split('+'))) for k in tmp]
            return True
    else:
        log.warn('`%s` not found or is inaccessible' % configPath)
        return False

gesturesBDPath = lambda: profilesDir + (curBD + "/gestures.ini").decode('utf-8').encode('mbcs')
def initGestures():
    global gesturesFileExists, iniGestures
    if profileFileExists and osp.exists(gesturesBDPath()):
        log.debug('Main gestures map found')
        confGen = osp.join(osp.join(osp.dirname(__file__),
                                    "",
                                    "").decode("mbcs"), gesturesBDPath())
        confspec = ConfigObj(StringIO("""
        """), encoding="UTF-8", list_values=False)
        iniGestures = ConfigObj(confGen, configspec=confspec,
                            indent_type="\t", encoding="UTF-8")
        result = iniGestures.validate(Validator())
        if result is not True:
            log.exception('Malformed configuration file')
            gesturesFileExists = False
        else:
            gesturesFileExists = True
    else:
        log.warn('No main gestures map (%s) found' % gesturesBDPath())
        gesturesFileExists = False

    if gesturesFileExists:
        for g in iniGestures['globalCommands.GlobalCommands']:
            if isinstance(iniGestures['globalCommands.GlobalCommands'][g], list):
                for h in range(
                        len(iniGestures['globalCommands.GlobalCommands'][g])):
                    iniGestures[inputCore.normalizeGestureIdentifier(
                        str(iniGestures['globalCommands.GlobalCommands'][g][h]))] = g
            elif ('kb:' in g and g not in ['kb:alt', 'kb:control', 'kb:windows', 'kb:control', 'kb:applications'] and 'br(' + curBD + '):' in str(iniGestures['globalCommands.GlobalCommands'][g])):
                iniGestures[inputCore.normalizeGestureIdentifier(str(
                    iniGestures['globalCommands.GlobalCommands'][g])).replace('br(' + curBD + '):', '')] = g
    return gesturesFileExists, iniGestures

def loadConfAttribra():
    global confAttribra
    try:
        cfg = ConfigObj(cfgFileAttribra, encoding="UTF-8")
        for app, map in cfg.iteritems():
            mappings = {}
            for name, value in map.iteritems():
                if isinstance(value, basestring):
                    if value.startswith("RGB("): #it's an RGB Object
                        rgbval = value.split("RGB(")[1]
                        rgbval = rgbval.split(")")[0]
                        rgbval = rgbval.split(",")
                        mappings[name] = [RGB(int(rgbval[0]),int(rgbval[1]),int(rgbval[2]))]
                    else:
                        try:
                            #if possible adds the value and its int
                            mappings[name] = [value, int(value)]
                        except ValueError:
                            mappings[name] = [value]
                else: mappings[name] = value
            confAttribra[app] = mappings
    except IOError:
        log.debugWarning("No Attribra config file found")
    
checkConfigPath()
loadConf()

if not osp.exists(cfgFileAttribra):
    f = open(config.getUserDefaultConfigPath() + '\\attribra-BE.ini', "w")
    f.write(begFileAttribra+"""

[global]
    bold = 1

[winword]
    invalid-spelling = 1

[eclipse]
    background-color = "rgb(24420045)", "rgb(2550128)"

[firefox]
    color = "RGB(255,0,0)"

[thunderbird]
    invalid-spelling = 1
    """)    
    f.close()
