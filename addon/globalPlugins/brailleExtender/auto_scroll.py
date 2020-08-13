# auto_scroll.py
# Part of BrailleExtender addon for NVDA
# Copyright 2016-2020 André-Abush CLAUSE, released under GPL.

import braille
import config
import speech
import wx
from logHandler import log
from .utils import isLastLine

DEFAULT_AUTO_SCROLL_DELAY = 3000

conf = config.conf["brailleExtender"]


def get_auto_scroll_delay():
	key = f"delay_{braille.handler.display.name}"
	if key in conf["autoScroll"]:
		return conf["autoScroll"][key]
	return DEFAULT_AUTO_SCROLL_DELAY


def set_auto_scroll_delay(delay):
	key = f"delay_{braille.handler.display.name}"
	conf["autoScroll"][key] = delay


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
