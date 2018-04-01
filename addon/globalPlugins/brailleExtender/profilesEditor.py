# coding: utf-8
# profilesEditor.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2018 André-Abush CLAUSE, released under GPL.

from __future__ import unicode_literals
from configobj import ConfigObj
import glob
import os
import gui
from gui.settingsDialogs import SettingsDialog
import wx
import keyLabels
from logHandler import log
import ui
import configBE
import utils

keyLabelsList = sorted([(t[1], t[0]) for t in keyLabels.localizedKeyLabels.items()])+[('f%d' %i, 'f%d' %i) for i in range(1, 13)]

class ProfilesEditor(SettingsDialog):
	title = _("Profiles editor") + " (%s)" % configBE.curBD
	profilesList = []
	addonGesturesPrfofile = None
	generalGesturesProfile = None

	def makeSettings(self, settingsSizer):
		if configBE.curBD == 'noBraille':
			self.Destroy()
			wx.CallAfter(gui.messageBox, _("You must have a braille display to editing a profile"), self.title, wx.OK|wx.ICON_ERROR)

		if not os.path.exists(configBE.profilesDir):
			self.Destroy()
			wx.CallAfter(gui.messageBox, _("Profiles directory is not present or accessible. Unable to edit profiles"), self.title, wx.OK|wx.ICON_ERROR)

		self.profilesList = self.getListProfiles()

		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		labelText = _("Profile to edit")
		self.profiles = sHelper.addLabeledControl(labelText, wx.Choice, choices=self.profilesList)
		self.profiles.SetSelection(0)
		self.profiles.Bind(wx.EVT_CHOICE, self.onProfiles)

		sHelper2 = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		labelText = _('Gestures category')
		categoriesList = [_("Single keys"), _("Modifier keys"), _("Practical shortcuts"), _("NVDA commands"), _("Addon features")]
		self.categories = sHelper2.addLabeledControl(labelText, wx.Choice, choices=categoriesList)
		self.categories.SetSelection(0)
		self.categories.Bind(wx.EVT_CHOICE, self.refreshGestures)
		labelText = _('Gestures list')
		self.gestures = sHelper2.addLabeledControl(labelText, wx.Choice, choices=[])
		self.gestures.Bind(wx.EVT_CHOICE, self.onGesture)

		sHelper.addItem(sHelper2)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		addGestureButtonID = wx.NewId()
		self.addGestureButton = bHelper.addButton(self, addGestureButtonID, _("Add gesture"), wx.DefaultPosition)

		removeGestureButtonID = wx.NewId()
		self.removeGestureButton = bHelper.addButton(self, addGestureButtonID, _("Remove this gesture"), wx.DefaultPosition)

		assignGestureButtonID = wx.NewId()
		self.assignGestureButton = bHelper.addButton(self, assignGestureButtonID, _("Assign a braille gesture"), wx.DefaultPosition)

		sHelper.addItem(bHelper)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)

		removeProfileButtonID = wx.NewId()
		self.removeProfileButton = bHelper.addButton(self, removeProfileButtonID, _("Remove this profile"), wx.DefaultPosition)

		addProfileButtonID = wx.NewId()
		self.addProfileButton = bHelper.addButton(self, addProfileButtonID, _("Add a profile"), wx.DefaultPosition)
		self.addProfileButton.Bind(wx.EVT_BUTTON, self.onAddProfileButton)

		sHelper.addItem(bHelper)

		edHelper = gui.guiHelper.BoxSizerHelper(self, orientation=wx.HORIZONTAL)
		labelText = _('Name for the new profile')
		self.newProfileName = edHelper.addLabeledControl(labelText, wx.TextCtrl)
		sHelper.addItem(edHelper)

		bHelper = gui.guiHelper.ButtonHelper(orientation=wx.HORIZONTAL)
		validNewProfileNameButtonID = wx.NewId()
		self.validNewProfileNameButton = bHelper.addButton(self, validNewProfileNameButtonID, _('Create'))

		sHelper.addItem(bHelper)

	def postInit(self):
		self.hideNewProfileSection()
		self.refreshGestures()
		if len(self.profilesList)>0:
			self.profiles.SetSelection(self.profilesList.index(configBE.conf["general"]["profile_%s" % configBE.curBD]))
		self.onProfiles()
		self.profiles.SetFocus()

	def refreshGestures(self, evt = None):
		category = self.categories.GetSelection()
		items = []
		ALT = keyLabels.localizedKeyLabels['alt'].capitalize()
		CTRL = keyLabels.localizedKeyLabels['control'].capitalize()
		SHIFT = keyLabels.localizedKeyLabels['shift'].capitalize()
		WIN = keyLabels.localizedKeyLabels['windows'].capitalize()
		if category == 0: items = [k[0].capitalize() for k in keyLabelsList]
		elif category == 1:
			items = [ALT, CTRL, SHIFT, WIN, "NVDA",
			'%s+%s' % (ALT, CTRL),
			'%s+%s' % (ALT, SHIFT),
			'%s+%s' % (ALT, WIN),
			'%s+%s+%s' % (ALT, CTRL, SHIFT), 
			'%s+%s+%s+%s' % (ALT, CTRL, SHIFT, WIN),
			'%s+%s+%s' % (ALT, CTRL, WIN),
			'%s+%s' % (CTRL, SHIFT),
			'%s+%s' % (CTRL, WIN),
				'%s+%s+%s' % (CTRL, SHIFT, WIN),
			'%s+%s' % (SHIFT, WIN)
			]
		elif category == 2:
			items = sorted([
				'%s+F4' % ALT,
				'%s+Tab' % ALT,
				'%s+Tab' % SHIFT,
			])
		self.gestures.SetItems(items)
		self.gestures.SetSelection(0)
		self.gestures.SetSelection(0)
		if category<2:
			self.addGestureButton.Disable()
			self.removeGestureButton.Disable()
		else:
			self.addGestureButton.Enable()
			self.removeGestureButton.Enable()

	def onProfiles(self, evt = None):
		if len(self.profilesList) == 0: return
		curProfile = self.profilesList[self.profiles.GetSelection()]
		self.addonGesturesPrfofile = ConfigObj('%s/baum/%s/profile.ini' % (configBE.profilesDir, curProfile), encoding="UTF-8")
		self.generalGesturesProfile = ConfigObj('%s/baum/%s/gestures.ini' % (configBE.profilesDir, curProfile), encoding="UTF-8")
		if self.addonGesturesPrfofile == {}:
			wx.CallAfter(gui.messageBox, _("Unable to load this profile. Malformed or inaccessible file"), self.title, wx.OK|wx.ICON_ERROR)

	def getListProfiles(self):
		profilesDir = '%s\%s' %(configBE.profilesDir, configBE.curBD)
		res = []
		ls = glob.glob(profilesDir+'\\*')  
		for e in ls:
			if os.path.isdir(e) and os.path.exists('%s\%s' %(e, 'profile.ini')): res.append(e.split('\\')[-1])
		return res

	def switchProfile(self, evt = None):
		self.refreshGestures()

	def onGesture(self, evt = None):
		category = self.categories.GetSelection()
		gesture = self.gestures.GetSelection()
		gestureName = keyLabelsList[gesture][1]

	def onAddProfileButton(self, evt = None):
		if not self.addProfileButton.IsEnabled():
			self.hideNewProfileSection()
			self.addProfileButton.Enable()
		else:
			self.newProfileName.Enable()
			self.validNewProfileNameButton.Enable()
			self.addProfileButton.Disable()

	def hideNewProfileSection(self, evt = None):
		self.validNewProfileNameButton.Disable()
		self.newProfileName.Disable()
