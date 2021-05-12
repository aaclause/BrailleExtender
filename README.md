# Braille Extender

- Authors: André-Abush Clause and contributors
- License: GNU General Public License, version 2
- Download [stable version](https://andreabc.net/projects/NVDA_addons/BrailleExtender/latest)
- Download [development version](https://andreabc.net/projects/NVDA_addons/BrailleExtender/latest?channel=dev)

BrailleExtender is an [NVDA](http://nvda-project.org/) add-on that provides various features at braille level. Currently, the following features are implemented:

- reload two favorite braille display with shortcuts.
- automatic review cursor tethering in terminal role like in PuTTY, Powershell, bash, cmd.
- auto scroll.
- switch between several input/output braille tables.
- mark the text with special attributes through dot 7, dot 8 or both.
- use two output braille tables simultaneously.
- display tab signs as spaces.
- reverse forward scroll and back scroll buttons.
- say the current line during text scrolling either in review mode, or in focus mode or both.
- translate text easily in Unicode braille and vice versa. E.g.: z <--> ⠵.
- convert cell description to Unicode braille and vice versa. E.g.: 123 <--> ⠇.
- lock braille keyboard.
- launch an application/URL with gesture.
- braille dictionaries.
- type with one-hand from braille keyboard.
- display undefined characters from braille tables (including emojis) using altenative representations.
- enter any character from braille keyboard (including emojis).
- skip blank lines during text scrolling.
- and much more!

For some braille displays, it extends the braille display commands to provide: 

- offer complete gesture maps including function keys, multimedia keys, quick navigation, etc.;
- emulate modifier keys, and thus any keyboard shortcut;
- offer several keyboard configurations concerning the possibility to input dots 7 and 8, enter and backspace;
- add actions and quick navigation through a rotor.

Once the add-on is installed, read the documentation and go through the settings using the BrailleExtender submenu (located in the NVDA menu).

## Let's explore some common features

### Representation of undefined characters
The extension allows you to customize how an undefined character should be represented within a braille table. To do so, go to the — Representation of undefined characters — settings. You can choose between the following representations:

- Use braille table behavior (no description possible)
- Dots 1-8 (⣿)
- Dots 1-6 (⠿)
- Empty cell (⠀)
- Other dot pattern (e.g.: 6-123456)
- Question mark (depending on output table)
- Other sign/pattern (e.g.: ??)
- Hexadecimal
- Hexadecimal, HUC8
- Hexadecimal, HUC6
- Decimal
- Octal
- Binary

You can also combine this option with the “describe the character if possible” setting.

Notes:

- To distinguish the undefined set of characters while maximizing space, the best combination is the usage of the HUC8 representation without checking the “Show punctuation/symbol name for undefined characters if available” option.
- To learn more about the HUC representation, see <https://danielmayr.at/huc/>
- Keep in mind that definitions in tables and those in your table dictionaries take precedence over character descriptions, which also take precedence over the chosen representation for undefined characters.

### Getting Current Character Info
This feature allows you to obtain various information regarding the character under the cursor using the current input braille table, such as:
the HUC8 and HUC6 representations; the hexadecimal, decimal, octal or binary values; A description of the character if possible; the Unicode braille representation and the braille pattern dots.

Pressing the defined gesture associated to this function once shows you the information in a flash message and a double-press displays the same information in a virtual NVDA buffer.

On supported displays the defined gesture is ⡉+space. No system gestures are defined by default.

For example, for the '&' character, we will get the following information:

> &: 0x26, 38, 0o46, 0b100110  
> and (AMPERSAND [Po])  
> ⢿ (1234568)  
> ⣥⣺⡧, ⠿⠺⠏⠏

### Advanced braille input
This feature allows you to enter any character from its HUC8 representation or its hexadecimal/decimal/octal/binary value. Moreover, it allows you to develop abbreviations. To use this function, enter the advanced input mode and then enter the desired pattern. Default gestures: NVDA+Windows+i or ⡊+space (on supported displays). Press the same gesture to exit this mode. Alternatively, an option allows you to automatically exit this mode after entering a single pattern. 
If you want to enter a character from its HUC8 representation, simply enter the HUC8 pattern. Since a HUC8 sequence must fit on 3 or 4 cells, the interpretation will be performed each time 3 or 4 dot combinations are entered. If you wish to enter a character from its hexadecimal, decimal, octal or binary value, do the following:

1. Enter ⠼
2. Specify the basis as follows:
	- ⠭ or ⠓: for a hexadecimal value
	- ⠙: for a decimal value
	- ⠕: for an octal value
	- ⠃: for a binary value
3. Enter the value of the character according to the previously selected basis.
4. Press Space to validate.

For abbreviations, you must first add them in the dialog box — Advanced input mode dictionary —. Then, you just have to enter your abbreviation and press space to expand it. For example, you can define the following abbreviations: "⠎⠺" with "sandwich", "⠋⠛⠋⠗" to "🇫🇷".


Here are some examples of sequences to be entered for given characters:

| Character         | HUC8 | Hexadecimal      | Decimal | Octal   | Binary             |
| ----------------- | ---- | ---------------- | ------- | ------- | ------------------ |
| 👍 (thumbs up)     | ⣭⢤⡙  | ⠭1f44d or ⠓1f44d | ⠙128077 | ⠕372115 | ⠃11111010001001101 |
| 😀 (grinning face) | ⣭⡤⣺  | ⠭1f600 or ⠓1f600 | ⠙128512 | ⠕373000 | ⠃11111011000000000 |
| 🍑 (peach)         | ⣭⠤⠕  | ⠭1f351 or ⠓1f351 | ⠙127825 | ⠕371521 | ⠃11111001101010001 |
| 🌊 (water wave)    | ⣭⠤⠺  | ⠭1f30a or ⠓1f30a | ⠙127754 | ⠕371412 | ⠃11111001100001010 |

Note: the HUC6 input is currently not supported.

### One-hand mode

This feature allows you to compose a cell in several steps. This can be activated in the general settings of the extension's preferences or on the fly using NVDA+Windows+h gesture by default (⡂+space on supported displays). Three input methods are available.

#### Method #1: fill a cell in 2 stages on both sides
With this method, type the left side dots, then the right side dots. If one side is empty, type the dots correspondig to the opposite side twice, or type the dots corresponding to the non-empty side in 2 steps.

For example:

- For ⠛: press dots 1-2 then dots 4-5.
- For ⠃: press dots 1-2 then dots 1-2, or dot 1 then dot 2.
- For ⠘: press 4-5 then 4-5, or dot 4 then dot 5.

#### Method #2: fill a cell in two stages on one side (Space = empty side)
Using this method, you can compose a cell with one hand, regardless of which side of the Braille keyboard you choose. The first step allows you to enter dots 1-2-3-7 and the second one 4-5-6-8. If one side is empty, press space. An empty cell will be obtained by pressing the space key twice.

For example:

- For ⠛: press dots 1-2 then dots 1-2, or dots 4-5 then dots 4-5.
- For ⠃: press dots 1-2 then space, or 4-5 then space.
- For ⠘: press space then 1-2, or space then dots 4-5.

#### Method #3: fill a cell dots by dots (each dot is a toggle, press Space to validate the character)

In this mode, each dot is a toggle. You must press the space key as soon as the cell you have entered is the desired one to input the character. Thus, the more dots are contained in the cell, the more ways you have to enter the character.

For example, for ⠛, you can compose the cell in the following ways:

- Dots 1-2, then dots 4-5, then space.
- Dots 1-2-3, then dot 3 (to correct), then dots 4-5, then space.
- Dot 1, then dots 2-4-5, then space.
- Dots 1-2-4, then dot 5, then space.
- Dot 2, then dot 1, then dot 5, then dot 4, and then space.
- Etc.
