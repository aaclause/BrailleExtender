# rolelabels.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2021 André-Abush CLAUSE, released under GPL.

import gui
import wx

import addonHandler
import braille
import config
import controlTypes

addonHandler.initTranslation()

class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Role labels")

	roleLabels = {}

	def makeSettings(self, settingsSizer):
		self.roleLabels = config.conf["brailleExtender"]["roleLabels"].copy()
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		self.toggleRoleLabels = sHelper.addItem(wx.CheckBox(self, label=_("Use custom braille &role labels")))
		self.toggleRoleLabels.SetValue(config.conf["brailleExtender"]["features"]["roleLabels"])
		self.categories = sHelper.addLabeledControl(_("Role &category:"), wx.Choice, choices=[_("General"), _("Landmarks"), _("Positive states"), _("Negative states")])
		self.categories.Bind(wx.EVT_CHOICE, self.onCategories)
		self.categories.SetSelection(0)
		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		choices = []
		if hasattr(controlTypes, "roleLabels"):
			choices = [controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()]

		self.labels = sHelper2.addLabeledControl(_("&Role:"), wx.Choice, choices=choices)
		self.labels.Bind(wx.EVT_CHOICE, self.onLabels)
		self.label = sHelper2.addLabeledControl(_("Braille &label"), wx.TextCtrl)
		self.label.Bind(wx.EVT_TEXT, self.onLabel)
		sHelper.addItem(sHelper2)
		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		self.resetLabelBtn = bHelper.addButton(self, wx.NewId(), _("&Reset this role label"), wx.DefaultPosition)
		self.resetLabelBtn.Bind(wx.EVT_BUTTON, self.onResetLabelBtn)
		self.resetAllLabelsBtn = bHelper.addButton(self, wx.NewId(), _("Reset all role labels"), wx.DefaultPosition)
		self.resetAllLabelsBtn.Bind(wx.EVT_BUTTON, self.onResetAllLabelsBtn)
		sHelper.addItem(bHelper)
		self.onCategories(None)

	def onCategories(self, event):
		labels = []
		idCategory = self.categories.GetSelection()
		oldRoleLabels = hasattr(controlTypes, "roleLabels")
		if idCategory == 0:
			if oldRoleLabels:
				labels = [controlTypes.roleLabels[int(k)] for k in braille.roleLabels.keys()]
			else:
				labels = [role.displayString for role in braille.roleLabels.keys()]
		elif idCategory == 1:
			labels = list(braille.landmarkLabels.keys())
		elif idCategory == 2:
			if oldRoleLabels:
				labels = [controlTypes.stateLabels[k] for k in braille.positiveStateLabels.keys()]
			else:
				labels = [role.displayString for role in braille.positiveStateLabels.keys()]
		elif idCategory == 3:
			if oldRoleLabels:
				labels = [controlTypes.stateLabels[k] for k in braille.negativeStateLabels.keys()]
			else:
				labels = [role.displayString for role in braille.negativeStateLabels.keys()]
		for iLabel, label in enumerate(labels):
			idLabel = getIDFromIndexes(idCategory, iLabel)
			actualLabel = getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			labels[iLabel] += _(f": %s") % actualLabel
			if actualLabel != originalLabel: labels[iLabel] += " (%s)" % originalLabel
		self.labels.SetItems(labels)
		if idCategory > -1 and idCategory < 4: self.labels.SetSelection(0)
		self.onLabels(None)

	def onLabels(self, event):
		idCategory = self.categories.GetSelection()
		idLabel = getIDFromIndexes(idCategory, self.labels.GetSelection())
		key = f"{idCategory}:{idLabel}"
		if key in self.roleLabels.keys(): self.label.SetValue(self.roleLabels[key])
		else: self.label.SetValue(self.getOriginalLabel(idCategory, idLabel))

	def onLabel(self, evt):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		label = self.label.GetValue()
		if idCategory >= 0 and iLabel >= 0:
			if self.getOriginalLabel(idCategory, idLabel, chr(4)) == label:
				if key in self.roleLabels.keys():
					self.roleLabels.pop(key)
			else: self.roleLabels[key] = label
			actualLabel = getLabelFromID(idCategory, idLabel)
			originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
			if label != originalLabel: self.resetLabelBtn.Enable()
			else: self.resetLabelBtn.Disable()

	def onResetLabelBtn(self, event):
		idCategory = self.categories.GetSelection()
		iLabel = self.labels.GetSelection()
		idLabel = getIDFromIndexes(idCategory, iLabel)
		key = "%d:%s" % (idCategory, idLabel)
		actualLabel = getLabelFromID(idCategory, idLabel)
		originalLabel = self.getOriginalLabel(idCategory, idLabel, actualLabel)
		self.label.SetValue(originalLabel)
		self.onLabel(None)
		self.label.SetFocus()

	def onResetAllLabelsBtn(self, event):
		nbCustomizedLabels = len(self.roleLabels)
		if not nbCustomizedLabels:
			queueHandler.queueFunction(queueHandler.eventQueue, ui.message, _("You have no customized role labels."))
			return
		res = gui.messageBox(
			_("You have %d customized role labels defined. Do you want to reset all labels?") % nbCustomizedLabels,
			_("Reset role labels"),
			wx.YES|wx.NO|wx.ICON_INFORMATION)
		if res == wx.YES:
			self.roleLabels = {}
			config.conf["brailleExtender"]["roleLabels"] = {}
			self.onCategories(None)

	def getOriginalLabel(self, idCategory, idLabel, defaultValue = ''):
		key = f"{idCategory}:{idLabel}"
		if key in backupRoleLabels.keys():
			return backupRoleLabels[key][1]
		return getLabelFromID(idCategory, idLabel)

	def postInit(self): self.toggleRoleLabels.SetFocus()

	def onSave(self):
		config.conf["brailleExtender"]["features"]["roleLabels"] = self.toggleRoleLabels.IsChecked()
		config.conf["brailleExtender"]["roleLabels"] = self.roleLabels
		discardRoleLabels()
		if config.conf["brailleExtender"]["features"]["roleLabels"]:
			loadRoleLabels(config.conf["brailleExtender"]["roleLabels"].copy())

backupRoleLabels = {}

def getIDFromIndexes(idCategory, idLabel):
	if not isinstance(idCategory, int):
		raise TypeError(f"Wrong type for idCategory ({idCategory})")
	if not isinstance(idLabel, int):
		raise TypeError(f"Wrong type for idLabel ({idLabel})")
	idRole = -1
	if idCategory == 0: idRole = list(braille.roleLabels.keys())[idLabel]
	elif idCategory == 1: idRole = list(braille.landmarkLabels.keys())[idLabel]
	elif idCategory == 2: idRole = list(braille.positiveStateLabels.keys())[idLabel]
	elif idCategory == 3: idRole = list(braille.negativeStateLabels.keys())[idLabel]
	else: raise ValueError(f"Wrong value for category ({idCategory})")
	if isinstance(idRole, (controlTypes.Role, controlTypes.State)):
		idRole = idRole.value
	return idRole

def getLabelFromID(idCategory, idLabel):
	if idCategory == 0: return braille.roleLabels[int(idLabel)]
	if idCategory == 1: return braille.landmarkLabels[idLabel]
	if idCategory == 2: return braille.positiveStateLabels[int(idLabel)]
	if idCategory == 3: return braille.negativeStateLabels[int(idLabel)]
	raise ValueError("Invalid value: %d" % idCategory)

def setLabelFromID(idCategory, idLabel, newLabel):
	if idCategory == 0: braille.roleLabels[int(idLabel)] = newLabel
	elif idCategory == 1: braille.landmarkLabels[idLabel] = newLabel
	elif idCategory == 2: braille.positiveStateLabels[int(idLabel)] = newLabel
	elif idCategory == 3: braille.negativeStateLabels[int(idLabel)] = newLabel

def loadRoleLabels(roleLabels):
	global backupRoleLabels
	for k, v in roleLabels.items():
		idCategory, idRole = k.split(':')
		idCategory = int(idCategory)
		backupRoleLabels[k] = (v, getLabelFromID(idCategory, idRole))
		setLabelFromID(idCategory, idRole, v)

def discardRoleLabels():
	global backupRoleLabels
	for k, v in backupRoleLabels.items():
		arg1 = int(k.split(':')[0])
		arg2 = k.split(':')[1]
		setLabelFromID(arg1, arg2, v[1])
	backupRoleLabels = {}
