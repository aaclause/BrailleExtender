# coding: utf-8
from collections import namedtuple

BrailleDictEntry = namedtuple("BrailleDictEntry", ["opcode", "textPattern", "braillePattern", "direction", "comment"], rename=False)
OPCODE_SIGN = "sign"
OPCODE_MATH = "math"
OPCODE_REPLACE = "replace"
OPCODE_LABELS = {
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_SIGN: _("Sign"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_MATH: _("Math"),
	# Translators: This is a label for an Entry Type radio button in add dictionary entry dialog.
	OPCODE_REPLACE: _("Replace"),
}
OPCODE_LABELS_ORDERING = (OPCODE_SIGN, OPCODE_MATH, OPCODE_REPLACE)

DIRECTION_BOTH = "both"
DIRECTION_BACKWARD = "noforward"
DIRECTION_FORWARD = "noback"
DIRECTION_LABELS = {
	DIRECTION_BOTH: _("Both (input and output)"),
	DIRECTION_BACKWARD: _("Backward (input only)"),
	DIRECTION_FORWARD: _("Forward (output only)")
}
DIRECTION_LABELS_ORDERING = (DIRECTION_BOTH, DIRECTION_FORWARD, DIRECTION_BACKWARD)

testBrailleDictionary = [
	BrailleDictEntry("sign", "a", "1", "both", "Temporary test #1"),
	BrailleDictEntry("sign", "b", "12", "both", "Temporary test #2"),
	BrailleDictEntry("sign", "c", "14", "noback", "Temporary test #3"),
	BrailleDictEntry("sign", "d", "145", "nofor", "Temporary test #4"),
	BrailleDictEntry("math", "α", "45-1", "both", ""),
]
