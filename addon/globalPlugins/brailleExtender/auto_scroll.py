# auto_scroll.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import braille
import config
import configobj
import gui
import speech
import ui
import wx
from logHandler import log
from .utils import isLastLine

DEFAULT_AUTO_SCROLL_DELAY = 3000

conf = config.conf["brailleExtender"]["autoScroll"]


def get_auto_scroll_delay():
	key = f"delay_{braille.handler.display.name}"
	if key in conf:
		return conf[key]
	return DEFAULT_AUTO_SCROLL_DELAY


def set_auto_scroll_delay(delay):
	key = f"delay_{braille.handler.display.name}"
	try:
		conf[key] = delay
		return True
	except configobj.validate.VdtValueTooSmallError:
		return False


def increase_auto_scroll_delay(self):
	cur_delay = get_auto_scroll_delay()
	if cur_delay:
		new_delay = cur_delay + conf["stepDelayChange"]
	set_auto_scroll_delay(new_delay)


def decrease_auto_scroll_delay(self):
	cur_delay = get_auto_scroll_delay()
	if cur_delay:
		new_delay = cur_delay - conf["stepDelayChange"]
	set_auto_scroll_delay(new_delay)


def report_auto_scroll_delay(self):
	cur_delay = get_auto_scroll_delay()
	ui.message(_("{delay} ms").format(delay=cur_delay))


def toggle_auto_scroll(self, sil=False):
	if self._enable_auto_scroll:
		if self._auto_scroll_timer:
			self._auto_scroll_timer.Stop()
			self._auto_scroll_timer = None
		if not sil:
			speech.speakMessage(_("Autoscroll stopped"))
	else:
		self._auto_scroll_timer = wx.PyTimer(self._auto_scroll)
		try:
			self._auto_scroll_timer.Start(get_auto_scroll_delay())
		except BaseException as e:
			log.error("%s | %s" % (get_auto_scroll_delay(), e))
			ui.message(_("Unable to start autoscroll. More info in NVDA log"))
			return
	self._enable_auto_scroll = not self._enable_auto_scroll


def _auto_scroll(self):
	self.scrollForward()
	if isLastLine():
		self.toggle_auto_scroll()


def _displayWithCursor(self):
	if not self._cells:
		return
	cells = list(self._cells)
	if self._cursorPos is not None and self._cursorBlinkUp and not self._enable_auto_scroll:
		if self.getTether() == self.TETHER_FOCUS:
			cells[self._cursorPos] |= config.conf["braille"]["cursorShapeFocus"]
		else:
			cells[self._cursorPos] |= config.conf["braille"]["cursorShapeReview"]
	self._writeCells(cells)


class SettingsDlg(gui.settingsDialogs.SettingsPanel):

	# Translators: title of a dialog.
	title = _("Auto scroll")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: label of a dialog.
		label = _("Autoscroll &delay for the active braille display (ms):")
		self.autoScrollDelay = sHelper.addLabeledControl(
			label,
			gui.nvdaControls.SelectOnFocusSpinCtrl,
			min=125,
			max=42000,
			initial=get_auto_scroll_delay()
		)
		# Translators: label of a dialog.
		label = _("&Step for delay change (ms):")
		self.stepDelayChange = sHelper.addLabeledControl(
			label,
			gui.nvdaControls.SelectOnFocusSpinCtrl,
			min=25,
			max=42000,
			initial=conf["stepDelayChange"]
		)
		# Translators: label of a dialog.
		label = _("&Adjust the delay to content")
		self.adjustToContent = sHelper.addItem(wx.CheckBox(self, label=label))
		self.adjustToContent.SetValue(conf["adjustToContent"])
		# Translators: label of a dialog.
		label = _("Ignore &blank line")
		self.ignoreBlankLine = sHelper.addItem(wx.CheckBox(self, label=label))
		self.ignoreBlankLine.SetValue(conf["ignoreBlankLine"])

	def onSave(self):
		set_auto_scroll_delay(self.autoScrollDelay.Value)
		conf["stepDelayChange"] = self.stepDelayChange.Value
		conf["adjustToContent"] = self.adjustToContent.IsChecked()
		conf["ignoreBlankLine"] = self.ignoreBlankLine.IsChecked()
