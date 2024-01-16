#!/usr/bin/env python3

# jianpu2ly: Jianpu to LilyPond Converter with Jianpu and/or Staff Notation Output
# v0.1 (c) 2023 Xiangmin Jiao <xmjiao@gmail.com>

# Summary:
# This script converts musical scores written in Jianpu (numbered musical notation)
# into the LilyPond format. LilyPond is a music engraving system that can create
# sheet music from text inputs. The script supports converting to traditional Western
# staff notation as well as including lyrics, time signatures, key signatures, and other
# musical symbols. It also provides features for rendering the output as a LilyPond file (.ly),
# HTML document, or Markdown file. Additionally, it can handle input from Google Drive when
# given a file ID.

# Forked and expanded from 'Jianpu (numbered musical notation) for Lilypond'
# originally created by Silas S. Brown, v1.731 (c) 2012-2023 Silas S. Brown.

# jianpu2ly extends the original work by enabling the generation of both Jianpu and
# standard Western staff notations, with more standard handling of ties and
# slurs in Jianpu. The core functionality has been refactored to enhance
# readability and expand capabilities.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Homepage for jianpu2ly: https://github.com/xmjiao/jianpu2ly
# Git repository for jianpu2ly: https://github.com/xmjiao/jianpu2ly

# For detailed usage and documentation, refer to the provided instructions below.

# (The following doc string's format is fixed, see --html)
r"""Run jianpu2ly text-file
Text files are whitespace-separated and can contain:
Scale going up: 1 2 3 4 5 6 7 1'
Accidentals: 1 #1 2 b2 1
Octaves: 1,, 1, 1 1' 1''
Shortcuts for 1' and 2': 8 9
Change base octave: < >
Semiquaver, quaver, crotchet (16/8/4th notes): s1 q1 1
Dotted versions of the above (50% longer): s1. q1. 1.
Demisemiquaver, hemidemisemiquaver (32/64th notes): d1 h1
Minims (half notes) use dashes: 1 -
Dotted minim: 1 - -
Semibreve (whole note): 1 - - -
Time signature: 4/4
Time signature with quaver anacrusis (8th-note pickup): 4/4,8
Key signature (major): 1=Bb
Key signature (minor): 6=F#
Tempo: 4=85
Lyrics: L: here are the syl- la- bles (all on one line)
Lyrics (verse 1): L: 1. Here is verse one
Lyrics (verse 2): L: 2. Here is verse two
Hanzi lyrics (auto space): H: hanzi (with or without spaces)
Lilypond headers: title=the title (on a line of its own)
Multiple parts: NextPart
Instrument of current part: instrument=Flute (on a line of its own)
Multiple movements: NextScore
Prohibit page breaks until end of this movement: OnePage
Suppress bar numbers: NoBarNums
Old-style time signature: SeparateTimesig 1=C 4/4
Indonesian 'not angka' style: angka
Add a Western staff doubling the tune: WithStaff
Tuplets: 3[ q1 q1 q1 ]
Grace notes before: g[#45] 1
Grace notes after: 1 ['1]g
Simple chords: 135 1 13 1
Da capo: 1 1 Fine 1 1 1 1 1 1 DC
Repeat (with alternate endings): R{ 1 1 1 } A{ 2 | 3 }
Repeat twice (with alternate endings) twice: R3{ 1 1 1 } A{ 2 | 3 | 4 }
Short repeats (percent): R4{ 1 2 }
Ties (like Lilypond's, if you don't want dashes): 1 ~ 1
Slurs (like Lilypond's): 1 ( 2 )
Erhu fingering (applies to previous note): Fr=0 Fr=4
Erhu symbol (applies to previous note): souyin harmonic up down bend tilde
Tremolo: 1/// - 1///5 -
Rehearsal letters: letterA letterB
Multibar rest: R*8 0*32
Dynamics (applies to previous note): \p \mp \f
Other 1-word Lilypond \ commands: \fermata \> \! \( \) etc
Text: ^"above note" _"below note"
Other Lilypond code: LP: (block of code) :LP (each delimeter at start of its line)
Unicode approximation instead of Lilypond: Unicode
Ignored: % a comment
"""

import sys
import os
import re
import shutil
import tempfile
import argparse
import requests
import subprocess
import six

from fractions import Fraction as F
from string import ascii_letters as letters
from subprocess import getoutput

# Control options
bar_number_every = 0
midiInstrument = "choir aahs"  # see  https://lilypond.org/doc/v2.24/Documentation/notation/midi-instruments
padding = 3


def as_unicode(input_string):
    """
    Converts the input to Unicode if it is not already in Unicode format.

    Args:
        input_str: The input to be converted to Unicode.

    Returns:
        The input in Unicode format.
    """
    if isinstance(input_string, six.text_type):
        return input_string
    elif isinstance(input_string, six.binary_type):
        return input_string.decode("utf-8")
    else:
        raise TypeError(f"Expected unicode or bytes, got {input_string}")


def lilypond_minor_version():
    """
    Returns the minor version number of LilyPond installed on the system.
    If LilyPond is not installed, returns 20 (corresponding to version 2.20).
    :return: int
    """
    global _lilypond_minor_version
    try:
        return _lilypond_minor_version
    except NameError:
        pass
    cmd = lilypond_command()
    if cmd:
        m = re.match(r".*ond-2\.([1-9][0-9])\.", cmd)
        if m:
            _lilypond_minor_version = int(m.group(1))
        else:
            _lilypond_minor_version = int(
                getoutput(cmd + " --version").split()[2].split(".")[1]
            )
    else:
        _lilypond_minor_version = 20  # 2.20
    return _lilypond_minor_version


def lilypond_command():
    """
    Returns the path to the LilyPond executable if it is installed on the system.
    If LilyPond is not found, returns None.
    """
    w = shutil.which("lilypond")
    if w:
        return "lilypond"
    elif not sys.platform.startswith("win"):
        # e.g. from Mac OS 10.4-10.14 Intel build https://web.archive.org/web/20221121202056/https://lilypond.org/download/binaries/darwin-x86/lilypond-2.22.2-1.darwin-x86.tar.bz2 (unpacked and moved to /Applications), or similarly 2.20 for macOS 10.15+ from https://gitlab.com/marnen/lilypond-mac-builder/-/package_files/9872804/download
        placesToTry = ["/Applications/LilyPond.app/Contents/Resources/bin/lilypond"]
        # if renamed from the above (try specific versions 1st, in case default is older)
        placesToTry = [
            "/Applications/LilyPond-2.22.2.app/Contents/Resources/bin/lilypond",
            "/Applications/LilyPond-2.20.0.app/Contents/Resources/bin/lilypond",
        ] + placesToTry
        # if unpacked 2.24 (which drops the .app; in macOS 13, might need first to manually open at least lilypond and gs binaries for Gatekeeper approval if installing it this way)
        placesToTry += [
            "lilypond-2.24.0/bin/lilypond",
            "/opt/lilypond-2.24.0/bin/lilypond",
        ]
        for t in placesToTry:
            if os.path.exists(t):
                return t
    return None


def all_scores_start(poet1st, hasarranger):
    """
    Returns a string containing the Lilypond code for setting up the score.
    The code includes settings for staff size, paper size, margins, fonts, and spacing.
    :param poet1st: bool, if True, 'header:poet' appears before 'header:composer', otherwise the order is reversed.
    :return: str
    """
    staff_size = float(os.environ.get("j2ly_staff_size", 20))
    # Normal: j2ly_staff_size=20
    # Large: j2ly_staff_size=25.2
    # Small: j2ly_staff_size=17.82
    # Tiny: j2ly_staff_size=15.87
    r = (
        fr"""\version "2.18.0"
#(set-global-staff-size {staff_size})"""
    )

    # Modify the headers section based on poet1st argument
    headers_poet_composer = (
        (
            r"\right-align \fromproperty #'header:poet"
            "\n"
            r"\right-align \fromproperty #'header:composer"
            "\n"
        )
        if poet1st
        else (
            r"\right-align \fromproperty #'header:composer"
            "\n"
            r"\right-align \fromproperty #'header:poet"
            "\n"
        )
    )

    nullrow = "\n" if hasarranger else "\n"
    r += (
        r"""

% comment out the next line to have Lilypond tagline:
\header { tagline="" }

\pointAndClickOff

\paper {
  print-all-headers = ##t %% allow per-score headers

  #(set-default-paper-size "letter" )
  #(set-paper-size "letter")

  scoreTitleMarkup = \markup {
    \fill-line {
      \dir-column {
        \null
        \left-align \fontsize #2 \bold \fromproperty #'header:keytimesignature
        \left-align \fromproperty #'header:meter
        \null
        \left-align \fromproperty #'header:emotion
      }
      \dir-column {
          \center-align \fontsize #6 \bold \fromproperty #'header:title
          \null
          \center-align \fontsize #1 \fromproperty #'header:subtitle
          \center-align \fromproperty #'header:piece
      }
      \dir-column {
          """
        + nullrow
        + headers_poet_composer
        + r"""
          \right-align \fromproperty #'header:arranger
      }
    }
  }
  % un-comment the next line for no page numbers:
  % print-page-number = ##f

  top-margin = 20\mm
  bottom-margin = 25\mm
  left-margin = 25\mm
  right-margin = 25\mm
"""
    )
    # Note: For consistency across platforms,
    # Make sure to install Noto Serif CJK SC (regular and bold)
    # and Noto Sans CJK SC (regular and bold) from https://fonts.google.com/
    # On Ubuntu, the fonts can be installed by running `apt install fonts-noto-cjk`
    if lilypond_minor_version() >= 20:
        r += r"""
  #(define fonts
    (set-global-fonts
     #:roman "Noto Serif CJK SC,Times New Roman"
     #:sans "Noto Sans CJK SC,Arial Unicode MS"
     #:factor (/ staff-height pt 20)
    ))
"""

    if has_lyrics:
        global padding
        r += rf"""
  % Might need to enforce a minimum spacing between systems, especially if lyrics are
  % below the last staff in a system and numbers are on the top of the next
  system-system-spacing = #'((basic-distance . 7) (padding . {padding}) (stretchability . 1e7))
  score-markup-spacing = #'((basic-distance . 9) (padding . {padding}) (stretchability . 1e7))
  score-system-spacing = #'((basic-distance . 9) (padding . {padding}) (stretchability . 1e7))
  markup-system-spacing = #'((basic-distance . 2) (padding . 2) (stretchability . 0))
"""
    r += "}\n"  # end of \paper block
    return r


def score_start():
    """
    Returns the starting string for a LilyPond score.

    If `midi` is True, the score will be unfolded. If `notehead_markup.noBarNums`
    and `midi` are both False, the score will include bar numbers.

    Returns:
        str: The starting string for a LilyPond score.
    """
    ret = "\\score {\n"
    if midi:
        ret += "\\unfoldRepeats\n"
    ret += r"<< "
    if bar_number_every and not notehead_markup.noBarNums and not midi:
        ret += (
            f"\\override Score.BarNumber #'break-visibility = #end-of-line-invisible\n\\set Score.barNumberVisibility = #(every-nth-bar-number-visible {bar_number_every})"
        )
    return ret


def score_end(**headers):
    """
    Returns a string representing the end of a music score, including any headers and MIDI information.

    Args:
        headers: A dictionary of header key-value pairs to include in the score.

    Returns:
        A string representing the end of a music score.
    """
    ret = ">>\n"
    if headers:
        # since about Lilypond 2.7, music must come
        # before the header block if it's per-score
        ret += r"\header{" + "\n"
        for k, v in headers.items():
            if '"' not in v and r"\markup" not in v:
                v = '"' + v + '"'
            ret += k + "=" + v + "\n"
        # Placeholder for key and time signatures
        ret += r'keytimesignature=""' + "\n"
        ret += "}\n"

    if midi:
        # will be overridden by any \tempo command used later
        ret += (
            r'\midi { \context { \Score midiInstrument = "'
            + midiInstrument
            + r'" tempoWholesPerMinute = #(ly:make-moment 84 4)}}'
        )
        # ret += r'\midi { \context { \Score tempoWholesPerMinute = #(ly:make-moment 84 4)}}'
    elif notehead_markup.noBarNums:
        ret += r'\layout { indent = 0.0 \context { \Score \remove "Bar_number_engraver" } }'
    else:
        # ret += r"\layout{}"
        ret += r"\layout { indent = 0.0 \context { \Score \override TimeSignature.break-visibility = #'#(#f #t #t) } }"
    return ret + " }"


def unique_name():
    """
    Returns a unique name by incrementing the global variable uniqCount and
    translating it using the letters variable.
    """
    global uniqCount
    r = str(uniqCount)
    uniqCount += 1
    return r.translate((letters * 5)[:256])


def jianpu_voice_start(isTemp=0):
    """
    Create a new voice for Jianpu notation in LilyPond. Configures various
    overrides and settings for Jianpu, replacing standard noteheads with numbers.

    Args:
        isTemp (int, optional): Indicates if the voice is temporary (1) or not (0).
                                Temporary voices may have different settings,
                                particularly for stem length. Default is 0.

    Returns:
        tuple: A tuple containing:
               - A string with LilyPond code for initializing a new voice.
               - The name of the created voice.

    This function sets several overrides for the voice:
        - Beam visibility, thickness, and transparency are configured.
        - Stem direction and length are set based on the voice type and beam count.
        - Tie positions and tuplet directions are adjusted for Jianpu style.
        - Rest style is set to 'neomensural' for better alignment.
        - Accidental style is set to 'neo-modern', allowing repeating accidentals
          within a measure.
        - The 'chordChanges' property is set to True, enabling the substitution of
          Jianpu numbers for noteheads when 'chordChanges' is True.
    """

    stemLenFrac = "0.5" if not isTemp and maxBeams >= 2 else "0"
    voiceName = unique_name()
    r = f"""\\new Voice="{voiceName}" {{\n"""
    r += r"""
    #(set-accidental-style 'neo-modern) % Allow repeating accidentals within a measure
    \override Beam #'transparent = ##f
    """

    if not_angka:
        r += r"""
        \override Stem #'direction = #UP
        \override Tie #'staff-position = #-2.5
        \tupletDown
        """
        stemLenFrac = str(0.4 + 0.2 * max(0, maxBeams - 1))
    else:
        r += r"""
        \override Stem #'direction = #DOWN
        \override Tie #'staff-position = #2.5
        \override Beam.positions = #'(-1 . -1)
        \tupletUp
        """

    r += rf"""
    \override Stem #'length-fraction = #{stemLenFrac}
    \override Beam #'beam-thickness = #0.1
    \override Beam #'length-fraction = #-0.5
    \override Voice.Rest #'style = #'neomensural
    \override Accidental #'font-size = #-4
    \override TupletBracket #'bracket-visibility = ##t
    \set Voice.chordChanges = ##t %% 2.19 bug workaround
    \override BreathingSign.text = \markup {{ \fontsize #-4 \musicglyph #"scripts.upbow" }}
    """

    return r + "\n", voiceName


def jianpu_staff_start(inst=None, withStaff=False):
    """
    Initialize the start of a Jianpu or Not Angka staff in LilyPond notation.

    This function prepares the LilyPond string for starting a new RhythmicStaff,
    configured for either Jianpu or Not Angka notation. It includes several
    overrides to adjust the appearance of the staff and bar lines, and optionally
    includes settings for an associated Western staff.

    Args:
        inst (str, optional): The name of the instrument, if applicable. Default is None.
        withStaff (bool, optional): Flag to indicate whether to include settings for an
                                    associated Western staff. Default is False.

    Returns:
        tuple: A tuple containing:
               - A string with LilyPond code for initializing the staff.
               - The name of the created voice from jianpu_voice_start function.

    The function adds comments to mark the beginning of the staff section.
    If 'withStaff' is True, it adjusts the spacing between the Jianpu and the
    Western staff. It also sets various overrides to remove the staff lines
    (making it a RhythmicStaff) but retain the bar lines.
    """

    # Adding comments for ease of copy/pasting into other files
    r = (
        "\n%% === BEGIN NOT ANGKA STAFF ===\n"
        if not_angka
        else "\n%% === BEGIN JIANPU STAFF ===\n"
    )
    r += r"\new RhythmicStaff \with {"
    r += '\n    \\consists "Accidental_engraver"' if not not_angka else ""

    # Adding instrument name if provided
    if inst:
        r += '\n    instrumentName = "' + inst + '"'
        r += '\n    shortInstrumentName = "' + inst + '"'

    # Adjusting spacing for an associated Western staff
    if withStaff:
        r += r"""
    %% Limit space between Jianpu and corresponding-Western staff
    \override VerticalAxisGroup.staff-staff-spacing = #'((minimum-distance . 7) (basic-distance . 7) (stretchability . 0))
    """

    # Overrides for the appearance of the staff and bar lines
    r += r"""
    %% Get rid of the stave but not the barlines:
    \override StaffSymbol #'line-count = #0
    \override BarLine #'bar-extent = #'(-2 . 2)
    }
    { """

    # Initialize Jianpu voice settings
    j, voiceName = jianpu_voice_start()
    r += j
    r += r"""
    \override Staff.TimeSignature #'style = #'numbered
    \once \omit Staff.TimeSignature
    \override Staff.Stem #'transparent = ##t
    """

    return r, voiceName


def jianpu_staff_end():
    """
    Conclude the Jianpu or Not Angka staff section in LilyPond notation.

    This function generates the closing braces for a staff section initiated by
    jianpu_staff_start. It also adds a comment indicating the end of the staff section.

    Returns:
        str: A string containing the LilyPond code to end the staff section.

    The function determines whether to label the end of the section as "JIANPU" or
    "NOT ANGKA" based on the global flag 'not_angka'. The returned string is used
    to properly close the staff block in the LilyPond file.
    """

    # Close the staff section with appropriate comments
    if not_angka:
        return "} }\n% === END NOT ANGKA STAFF ===\n"
    else:
        return "} }\n% === END JIANPU STAFF ===\n"


def midi_staff_start():
    """
    Begin a new MIDI staff section in LilyPond notation.

    Returns:
        str: A string containing the LilyPond code to start a new MIDI staff.

    This function generates the LilyPond code to start a new MIDI staff with a unique voice name.
    It includes a comment indicating the beginning of the MIDI staff section.
    """
    return (
        r"""
%% === BEGIN MIDI STAFF ===
    \new Staff { \new Voice="%s" {"""
        % unique_name()
    )


def midi_staff_end():
    """
    Conclude the MIDI staff section in LilyPond notation.

    Returns:
        str: A string containing the LilyPond code to end the MIDI staff section.

    This function generates the closing braces for the MIDI staff section along with a comment.
    """
    return "} }\n% === END MIDI STAFF ===\n"


def western_staff_start(inst=None):
    """
    Begin a new Western (5-line) staff section in LilyPond notation.

    Args:
        inst (str, optional): The name of the instrument, if applicable. Default is None.

    Returns:
        tuple: A tuple containing:
               - A string with LilyPond code to start a new Western staff.
               - The name of the created voice.

    This function prepares the LilyPond string for starting a new Staff,
    configured for Western notation. It includes various overrides for appearance
    and an optional instrument name.
    """
    r = r"""
%% === BEGIN 5-LINE STAFF ===
    \new Staff """
    if inst:
        r += r'\with { instrumentName = "' + inst + '" } '
    voiceName = unique_name()
    return (
        r
        + r"""{
    \override Score.SystemStartBar.collapse-height = #11 %% (needed on 2.22)
    \new Voice="%s" {
    #(set-accidental-style 'modern-cautionary)
    \override Staff.TimeSignature #'style = #'numbered
    \set Voice.chordChanges = ##f %% for 2.19.82 bug workaround
"""
        % voiceName,
        voiceName,
    )


def western_staff_end():
    """
    Conclude the Western (5-line) staff section in LilyPond notation.

    Returns:
        str: A string containing the LilyPond code to end the Western staff section.

    This function generates the closing braces for the Western staff section along with a comment.
    """
    return "} }\n% === END 5-LINE STAFF ===\n"


def lyrics_start(voiceName):
    """
    Begin a new Lyrics section associated with a specific voice in LilyPond notation.

    Args:
        voiceName (str): The name of the voice to which the lyrics are associated.

    Returns:
        str: A string containing the LilyPond code to start a new Lyrics section.

    This function sets up a new Lyrics context that is linked to a specified voice,
    allowing for lyrics to be aligned with the notes of that voice.
    """
    uniqueName = unique_name()
    return rf'\new Lyrics = "I{uniqueName}" {{ \lyricsto "{voiceName}" {{ '


def lyrics_end():
    """
    Conclude the Lyrics section in LilyPond notation.

    Returns:
        str: A string containing the LilyPond code to end the Lyrics section.

    This function generates the closing braces for the Lyrics section,
    properly closing the Lyrics context in the LilyPond file.
    """
    return "} }"


# Implement dash (-) continuations as invisible ties rather than rests; sometimes works better in awkward beaming situations
dashes_as_ties = True
# Implement short rests as notes (and if there are lyrics, creates temporary voices so the lyrics miss them); sometimes works better for beaming (at least in 2.15, 2.16 and 2.18)
use_rest_hack = True
if __name__ == "__main__" and "--noRestHack" in sys.argv:  # TODO: document
    use_rest_hack = False
    sys.argv.remove("--noRestHack")
assert not (
    use_rest_hack and not dashes_as_ties
), "This combination has not been tested"


def errExit(msg):
    """
    Prints an error message and exits the program if called from the main module.
    Otherwise, raises an Exception with the error message.

    Args:
        msg (str): The error message to print/raise.

    Returns:
        None
    """
    if __name__ == "__main__":
        sys.stderr.write("Error: " + msg + "\n")
        sys.exit(1)
    else:
        raise Exception(msg)


def scoreError(msg, word, line):
    """
    Generates an error message for a score, highlighting the problematic word.

    Args:
        msg (str): The base error message.
        word (str): The word causing the error.
        line (str): The line in which the error occurred.

    Raises:
        Exception: Raises an exception with the formatted error message.
    """
    MAX_WORD_LENGTH = 60
    MAX_LINE_LENGTH = 600
    TRUNCATED_WORD_LENGTH = 50
    TRUNCATED_LINE_LENGTH = 500

    # Truncate 'word' and 'line' if they exceed maximum lengths
    word = (
        word if len(word) <= MAX_WORD_LENGTH else word[:TRUNCATED_WORD_LENGTH] + "..."
    )
    line = (
        line if len(line) <= MAX_LINE_LENGTH else line[:TRUNCATED_LINE_LENGTH] + "..."
    )

    # Check if the word is actually in the line
    if word in line:
        highlighted_line = highlight_word_in_line(word, line)
        msg = f"{msg} {word} in score {scoreNo}\n{highlighted_line}"
    else:
        msg = f"{msg} {word} in score {scoreNo}\nin this line: {line}"

    errExit(msg)


def highlight_word_in_line(word, line):
    """
    Highlights the given word in a line for terminal output.

    Args:
        word (str): The word to highlight.
        line (str): The line in which the word appears.

    Returns:
        str: The line with the word highlighted.
    """
    if "xterm" in os.environ.get("TERM", ""):
        # Use xterm underline escapes
        return re.sub(
            r"(\s|^)" + re.escape(word) + r"(?=\s|$)",
            lambda m: m.group(1) + "\x1b[4m" + word + "\x1b[m",
            line,
        )
    elif re.match("[ -~]*$", line):
        # All ASCII: underline the word with '^'
        underline = re.sub(
            "[^^]",
            " ",
            re.sub(
                r"(\s|^)" + re.escape(word) + r"(?=\s|$)",
                lambda m: m.group(1) + "^" * len(word),
                line,
            ),
        )
        return line + "\n" + underline
    else:
        # Default: no special handling for non-ASCII or unsupported terminals
        return line


placeholders = {
    # for accidentals and word-fitting to work
    # (we make them relative to the actual key later
    # so that MIDI pitches are correct)
    "0": "r",
    "1": "c",
    "2": "d",
    "3": "e",
    "4": "f",
    "5": "g",
    "6": "a",
    "7": "b",
    "-": "r",
}


def addOctaves(octave1, octave2):
    """
    Given two octave strings, returns the resulting octave string after adding them together.

    Args:
        octave1 (str): The first octave string.
        octave2 (str): The second octave string.

    Returns:
        str: The resulting octave string after adding octave1 and octave2 together.
    """
    # so it can be used with a base-octave change
    octave2 = octave2.replace(">", "'").replace("<", ",")
    while octave1:
        if octave1[0] in "'>":  # go up
            if "," in octave2:
                octave2 = octave2[:-1]
            else:
                octave2 += "'"
        else:  # , or < : go down
            if "'" in octave2:
                octave2 = octave2[:-1]
            else:
                octave2 += ","
        octave1 = octave1[1:]
    return octave2


class NoteheadMarkup:
    """
    A class that defines a notehead graphical object for the figures.
    """

    def __init__(self, withStaff=True):
        """
        Initializes the NoteheadMarkup object.

        Args:
        - withStaff (bool): whether to include staff in the object or not.
        """
        self.defines_done = {}
        self.withStaff = withStaff
        self.initOneScore()

    def initOneScore(self):
        """
        Initializes the score.
        """
        self.barLength = 64
        self.beatLength = 16  # in 64th notes
        self.barPos = self.startBarPos = F(0)
        self.inBeamGroup = (
            self.lastNBeams
        ) = self.onePage = self.noBarNums = self.separateTimesig = 0
        self.keepLength = 0
        self.last_octaves = self.last_accidentals = []
        self.base_octave = ""
        self.current_accidentals = {}
        self.barNo = 1
        self.tuplet = (1, 1)
        self.last_figures = None
        self.last_was_rest = False
        self.notesHad = []
        self.unicode_approx = []

    def endScore(self):
        """
        Ends the score.
        """
        if self.barPos == self.startBarPos:
            pass
        elif os.environ.get("j2ly_sloppy_bars", ""):
            sys.stderr.write(
                f"Wrong bar length at end of score {scoreNo} ignored (j2ly_sloppy_bars set)\n"
            )
        elif self.startBarPos and not self.barPos:
            # this is on the music theory syllabi at about Grade 3, but you can get up to Grade 5 practical without actually covering it, so we'd better not expect all users to understand "final bar does not make up for anacrusis bar"
            errExit(
                f"Score {scoreNo} should end with a {self.startBarPos / self.beatLength}-beat bar to make up for the {(self.barLength - self.startBarPos) / self.beatLength}-beat anacrusis bar.  Set j2ly_sloppy_bars environment variable if you really want to break this rule."
            )
        else:
            errExit(
                f"Incomplete bar at end of score {scoreNo} ({self.barPos/self.beatLength} beats)"
            )

    def setTime(self, num, denom):
        """
        Sets the time signature.

        Args:
        - num (int): the numerator of the time signature.
        - denom (int): the denominator of the time signature.
        """
        self.barLength = int(64 * num / denom)
        if denom > 4 and num % 3 == 0:
            self.beatLength = 24  # compound time
        else:
            self.beatLength = 16

    def setAnac(self, denom, dotted):
        """
        Sets the anacrusis.

        Args:
        - denom (int): the denominator of the anacrusis.
        - dotted (bool): whether the anacrusis is dotted or not.
        """
        self.barPos = F(self.barLength) - F(64) / denom
        if dotted:
            self.barPos -= F(64) / denom / 2
        if self.barPos < 0:
            # but anacrusis being exactly equal to bar is OK: we'll just interpret that as no anacrusis
            errExit(f"Anacrusis is longer than bar in score {scoreNo}")
        self.startBarPos = self.barPos

    def wholeBarRestLen(self):
        """
        Returns the length of a whole bar rest.
        """
        return {96: "1.", 48: "2.", 32: "2", 24: "4.", 16: "4", 12: "8.", 8: "8"}.get(
            self.barLength, "1"
        )  # TODO: what if irregular?

    def baseOctaveChange(self, change):
        """
        Changes the base octave.

        Args:
        - change (int): the amount of change in the octave.
        """
        self.base_octave = addOctaves(change, self.base_octave)

    def _validate_figures(self, figures, accidentals, word, line):
        """
        Validates the figures based on specific rules and formats.

        Args:
        - figures (list of str): List of figures to be validated.
        - accidentals (list of str): List of accidentals to be validated.
        - word (str): The word for context, used in error reporting.
        - line (int): The line number for context, used in error reporting.

        Raises:
        - Exception: If validation fails.
        """

        # Check if figures contain more than one character
        if len(figures) > 1:
            if "0" in figures:
                scoreError("Can't have rest in chord:", word, line)
            if "-" in figures:
                scoreError("Dash not allowed in multi-figure chords:", word, line)

        for acc in accidentals:
            if acc not in ["", "#", "b"]:
                scoreError("Can't handle accidental " + acc + " in", word, line)

    def _process_figures(self, figures, accidentals, octaves, word, line):
        """
        Processes the figures to extract note names and placeholder chords.

        Args:
        - figures (str): a chord string of '1'-'7', or '0' or '-'.
        - accidentals (list of str): list of '', '#', 'b' corresponding to each figure.
        - octaves (list of str): list of '', "'", "''", "," or ",," corresponding to each figure.
        - word (str): for error handling.
        - line (int): for error handling.

        Returns:
        - names (list of str): List of concatenated names of the notes.
        - placeholder_chord (str): Placeholder chord string.
        - updated_figures (list of str): Modified figures.
        - updated_accidentals (list of str): Modified accidentals.
        - updated_octaves (list of str): Modified octaves.
        - invisTieLast (bool): Flag indicating if an invisible tie is present.
        """

        names = {
            "0": "nought",
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
            "6": "six",
            "7": "seven",
            "-": "dash",
        }

        def get_placeholder_chord(figures):
            if len(figures) == 1:
                return placeholders[figures[0]]
            elif not midi and not western:
                return "c"  # Override appearance
            else:
                return "< " + " ".join(placeholders[f] for f in figures) + " >"

        invisTieLast = (
            dashes_as_ties
            and self.last_figures
            and figures[0] == "-"
            and not self.last_was_rest
        )

        if invisTieLast:
            assert len(figures) == 1

            figures = [
                "-" + f for f in self.last_figures
            ]  # Prepend '-' to each last figure
            octaves = self.last_octaves  # for MIDI or 5-line
            accidentals = self.last_accidentals
            combined_name = "-" + "".join(names[f] for f in self.last_figures)
            placeholder_chord = get_placeholder_chord(self.last_figures)
        else:
            combined_name = ""
            for fig, acc in zip(figures, accidentals):
                name = names[fig]
                if not_angka:
                    fig += acc
                    name += {"#": "-sharp", "b": "-flat", "": ""}[fig]
                combined_name += name

            placeholder_chord = get_placeholder_chord(figures)
            octaves = [addOctaves(octv, self.base_octave) for octv in octaves]
            for octave in octaves:
                if octave not in [",,", ",", "", "'", "''"]:
                    scoreError("Can't handle octave " + octave + " in", word, line)

            self.last_figures = figures
            self.last_octaves = octaves
            self.last_accidentals = accidentals

        assert self.last_figures[0] != "-"

        # Combine placeholder chords for chords
        self.last_was_rest = figures == ["0"] or (
            figures == ["-"] and self.last_was_rest
        )

        return (
            combined_name,
            placeholder_chord,
            figures,
            accidentals,
            octaves,
            invisTieLast,
        )

    def toMarkup(
        self, figures, nBeams, dots, octaves, accidentals, tremolo, word, line
    ):
        """
        Calls the NoteheadMarkup object.

        Args:
        - figures (list): list of chord string(s) of '1'-'7', or '0' or '-'.
        - nBeams (int): number of beams for this note.
        - dots (str): extra length.
        - octave (list): list of '', "'", "''", "," or ",,", matching figures.
        - accidental (list): list of '', '#', 'b', matching figures.
        - tremolo (str): '' or ':32'.
        - word (str): for error handling.
        - line (int): for error handling.
        """

        # Validate figures
        self._validate_figures(figures, accidentals, word, line)

        # Keep track of notes processed
        self.notesHad.append("".join(figures))

        # Process figures
        (
            name,
            placeholder_chord,
            figures,
            accidentals,
            octaves,
            invisTieLast,
        ) = self._process_figures(figures, accidentals, octaves, word, line)

        if figures[0][0] == "-":
            figures = "-" + "".join([f[1:] for f in figures])
        else:
            figures = "".join(figures)
        octave = "".join(octaves)
        accidental = "".join(accidentals)

        if figures not in self.defines_done and not midi and not western:
            # Define a notehead graphical object for the figures
            self.defines_done[figures] = "note-" + name
            if figures.startswith("-"):
                if not_angka:
                    figuresNew = "."
                else:
                    figuresNew = "\u2013"
            else:
                figuresNew = figures
            ret = (
                """#(define (%s grob grob-origin context)
  (if (and (eq? (ly:context-property context 'chordChanges) #t)
      (or (grob::has-interface grob 'note-head-interface)
        (grob::has-interface grob 'rest-interface)))
    (begin
      (ly:grob-set-property! grob 'stencil
        (grob-interpret-markup grob
          """
                % self.defines_done[figures]
            )
            k = len(self.last_figures)
            if figures.startswith("-") and k > 1:
                # Repeat the en-dash k times vertically
                ret += '''(markup (#:lower 0.5
                    (#:override (cons (quote direction) 1)
                    (#:override (cons (quote baseline-skip) 1.8)
                    (#:dir-column (
                    {})))))))))))'''.format("#:line (#:bold \"–\")\n" * k)
            elif len(figuresNew) == 1 or figures.startswith("-"):
                ret += f'(make-lower-markup 0.5 (make-bold-markup "{figuresNew}")))))))\n'
            elif not_angka and accidental:  # not chord
                # TODO: the \ looks better than the / in default font
                accidental_markup = {"#": "\u0338", "b": "\u20e5"}[accidental]
                ret += f'(make-lower-markup 0.5 (make-bold-markup "{figures[:1]}{accidental_markup}")))))))\n'
            else:
                ret += (
                    """(markup (#:lower 0.5
          (#:override (cons (quote direction) 1)
          (#:override (cons (quote baseline-skip) 1.8)
          (#:dir-column (\n"""
                    + "".join('    #:line (#:bold "' + f + '")\n' for f in figuresNew)
                    + """)))))))))))
"""
                )  # TODO: can do accidentals e.g. #:halign 1 #:line ((#:fontsize -5 (#:raise 0.7 (#:flat))) (#:bold "3")) but might cause the beam not to extend its full length if this chord occurs at the end of a beamed group, + accidentals won't be tracked by Lilypond and would have be taken care of by jianpu-ly (which might mean if any chord has an accidental on one of its notes we'd have to do all notes in that bar like this, whether they are chords or not)
        else:
            ret = ""
        if self.barPos == 0 and self.barNo > 1:
            ret += "| "  # barline in Lilypond file: not strictly necessary but may help readability
            if self.onePage and not midi:
                ret += r"\noPageBreak "
            ret += "%{ bar " + str(self.barNo) + ": %} "
        if octave not in self.current_accidentals:
            self.current_accidentals[octave] = [""] * 7
        if nBeams == None:  # unspecified
            if self.keepLength:
                nBeams = self.lastNBeams
            else:
                nBeams = 0
        if (
            figures == "-"
            or all(
                "1" <= figure <= "7"
                and not accidental == self.current_accidentals[octave][int(figure) - 1]
                for figure in list(figures)
            )
            and nBeams > self.lastNBeams
        ):
            leftBeams = nBeams  # beam needs to fit under the new accidental (or the dash which might be slightly to the left of where digits are), but if it's no more than last note's beams then we'll hang it only if in same beat.  (TODO: the current_accidentals logic may need revising if other accidental styles are used, e.g. modern-cautionary, although then would need to check anyway if our \consists "Accidental_engraver" is sufficient)
        # TODO: if figures=="0" then that might be typeset a bit to the left as well (because it's also a rest), however extending the line TOO far left in this case could be counterproductive
        elif self.inBeamGroup:
            if nBeams < self.lastNBeams:
                leftBeams = nBeams
            else:
                leftBeams = self.lastNBeams
        else:
            leftBeams = 0
        if leftBeams:
            assert (
                nBeams
            ), "following logic assumes if (leftBeams or nBeams) == if nBeams"
        aftrlast0 = ""
        if not nBeams and self.inBeamGroup:
            if not self.inBeamGroup == "restHack":
                aftrlast0 = "] "
            self.inBeamGroup = 0
        length = 4
        b = 0
        toAdd = F(16)  # crotchet
        while b < nBeams:
            b, length, toAdd = b + 1, length * 2, toAdd / 2
        toAdd0 = toAdd
        for _ in dots:
            toAdd0 /= 2
            toAdd += toAdd0
        toAdd_preTuplet = toAdd
        if not self.tuplet[0] == self.tuplet[1]:
            toAdd = toAdd * self.tuplet[0] / self.tuplet[1]
        # must set these unconditionally regardless of what we think their current values are (Lilypond's own beamer can change them from note to note)
        if nBeams and not midi and not western:
            if not_angka:
                leftBeams = nBeams
                if (self.barPos + toAdd) % self.beatLength == 0:
                    nBeams = 0
            ret += (r"\set stemLeftBeamCount = #%d" + "\n") % leftBeams
            ret += (r"\set stemRightBeamCount = #%d" + "\n") % nBeams
            if not_angka:
                nBeams = leftBeams
        need_space_for_accidental = False
        for figure in list(figures):
            if "1" <= figure <= "7":
                if not accidental == self.current_accidentals[octave][int(figure) - 1]:
                    need_space_for_accidental = True
                # TODO: not sensible (assumes accidental applies to EVERY note in the chord, see above)
                self.current_accidentals[octave][int(figure) - 1] = accidental
        inRestHack = 0
        if not midi and not western:
            if ret:
                ret = ret.rstrip() + "\n"  # try to keep the .ly code vaguely readable
            if octave == "''" and not invisTieLast:
                # inside bar numbers etc
                ret += r"  \once \override Score.TextScript.outside-staff-priority = 45"
            ret += r"  \applyOutput #'Voice #" + self.defines_done[figures] + " "
            if placeholder_chord == "r" and use_rest_hack and nBeams:
                placeholder_chord = "c"
                # C to work around diagonal-tail problem with
                # some isolated quaver rests in some Lilypond
                # versions (usually at end of bar); new voice
                # so lyrics miss it as if it were a rest:
                # (OK if self.withStaff: lyrics will be attached to that instead)
                if has_lyrics and not self.withStaff:
                    ret = jianpu_voice_start(1)[0] + ret
                    inRestHack = 1
                    if self.inBeamGroup and not self.inBeamGroup == "restHack":
                        aftrlast0 = "] "
        if placeholder_chord.startswith("<"):
            # Octave with chords: apply to last note if up, 1st note if down
            notes = placeholder_chord.split()[1:-1]
            assert len(notes) >= 2
            notes[0] += {",": "", ",,": ","}.get(octave, "'")
            for n in range(1, len(notes) - 1):
                notes[n] += "'"
            notes[-1] += {"'": "''", "''": "'''"}.get(octave, "'")
            ret += "< " + " ".join(notes) + " >"
        else:  # single note or rest
            ret += placeholder_chord + {"": "", "#": "is", "b": "es"}[accidental]
            if not placeholder_chord == "r":
                ret += {"": "'", "'": "''", "''": "'''", ",": "", ",,": ","}[
                    octave
                ]  # for MIDI + Western, put it so no-mark starts near middle C
        ret += f"{length}{dots}"

        if tremolo:
            self._apply_tremolo_to_note(
                ret, placeholder_chord, tremolo, midi or western,
                toAdd_preTuplet, dots
            )

        if (
            nBeams
            and (not self.inBeamGroup or self.inBeamGroup == "restHack" or inRestHack)
            and not midi
            and not western
        ):
            # We need the above stemLeftBeamCount, stemRightBeamCount override logic to work even if we're an isolated quaver, so do this:
            ret += "["
            self.inBeamGroup = 1
        self.barPos += toAdd
        # sys.stderr.write(accidental+figure+octave+dots+"/"+str(nBeams)+"->"+str(self.barPos)+" ") # if need to see where we are
        if self.barPos > self.barLength:
            errExit(
                f'(notesHad={" ".join(self.notesHad)}) barcheck fail: note crosses barline at "{figures}" with {nBeams} beams ({toAdd} skipped from {self.barPos - toAdd} to {self.barPos}, bypassing {self.barLength}), scoreNo={scoreNo} barNo={self.barNo} (but the error could be earlier)'
            )
        # (self.inBeamGroup is set only if not midi/western)
        if self.barPos % self.beatLength == 0 and self.inBeamGroup:
            # jianpu printouts tend to restart beams every beat
            # (but if there are no beams running anyway, it occasionally helps typesetting to keep the logical group running, e.g. to work around bugs involving beaming a dash-and-rest beat in 6/8) (TODO: what if there's a dash-and-rest BAR?  [..]-notated beams don't usually work across barlines
            ret += "]"
            # DON'T reset lastNBeams here (needed for start-of-group accidental logic)
            self.inBeamGroup = 0
        elif inRestHack and self.inBeamGroup:
            ret += "]"
            self.inBeamGroup = "restHack"
        self.lastNBeams = nBeams
        beamC = "\u0333" if nBeams >= 2 else "\u0332" if nBeams == 1 else ""
        self.unicode_approx.append(
            ""
            + ("-" if invisTieLast else figures[-1:])
            + (
                ""
                if invisTieLast
                else ("\u0323" if "," in octave else "\u0307" if "'" in octave else "")
            )
            + beamC
            + "".join(c + beamC for c in dots)
            + ("" if self.inBeamGroup else " ")
        )  # (NB inBeamGroup is correct only if not midi and not western)
        if self.barPos == self.barLength:
            self.unicode_approx[-1] = self.unicode_approx[-1].rstrip() + "\u2502"
            self.barPos = 0
            self.barNo += 1
            self.current_accidentals = {}
        # Octave dots:
        if not midi and not western and not invisTieLast:
            # Tweak the Y-offset, as Lilypond occasionally puts it too far down:
            if not nBeams:
                oDict = {
                    "": "",
                    "'": "^.",
                    "''": r"-\tweak #'X-offset #0.3 ^\markup{\bold :}",
                    ",": r"-\tweak #'X-offset #0.45 _\markup{\bold .}",
                    ",,": r"-\tweak #'X-offset #0.45 _\markup{\bold :}",
                }
            else:
                oDict = {
                    "": "",
                    "'": "^.",
                    "''": r"-\tweak #'X-offset #0.3 ^\markup{\bold :}",
                    ",": r"-\tweak #'X-offset #0.3 _\markup{\bold .}",
                    ",,": r"-\tweak #'X-offset #0.3 _\markup{\bold :}",
                }
            if not_angka:
                oDict.update(
                    {
                        "'": r"-\tweak #'extra-offset #'(0.4 . 2.7) -\markup{\bold \fontsize #2 ·}",
                        "''": r"-\tweak #'extra-offset #'(0.4 . 3.5) -\markup{\bold :}",
                    }
                )
            ret += oDict[octave]
        if invisTieLast:
            if midi or western:
                b4last, aftrlast = "", " ~"
            else:
                b4last, aftrlast = (
                    r"\once \override Tie #'transparent = ##t \once \override Tie #'staff-position = #0 ",
                    " ~",
                )
        else:
            b4last, aftrlast = "", ""
        if inRestHack:
            ret += " } "
        return (
            b4last,
            aftrlast0 + aftrlast,
            ret,
            need_space_for_accidental,
            nBeams,
            octave,
        )

    def _apply_tremolo_to_note(
        self, ret, placeholder_chord, tremolo, is_midi_or_western, toAdd_preTuplet, dots
    ):
        """
        Applies tremolo notation to the note markup

        Args:
        - ret (str): The current markup string.
        - placeholder_chord (str): The basic representation of the note or chord.
        - tremolo (str): Tremolo notation to be applied, either '' or ':32'.
        - toAdd_preTuplet (Fraction): Duration of the note before tuplet adjustment.
        - dots (str): Dots representing the note's duration extension.

        Returns:
        - str: The updated markup string with tremolo.
        """
        if is_midi_or_western:
            if (
                placeholder_chord.startswith("<")
                and len(placeholder_chord.split()) == 4
            ):
                # Handling tremolo for chords in MIDI/Western notation
                previous, n1, n2, gtLenDot = ret.rsplit(None, 3)
                previous = previous[:-1]  # drop <
                tremolo_count = int(toAdd_preTuplet / 4)
                return f"{previous}\repeat tremolo {tremolo_count} {{ {n1}32 {n2}32 }}"
            else:
                return ret + tremolo
        else:
            # Handling tremolo in Lilypond 2.22+ or 2.20
            tremolo_markup = self._get_tremolo_symbol(tremolo, dots)
            return ret + tremolo_markup

    def _get_tremolo_symbol(self, tremolo, dots):
        """
        Generates the tremolo markup for Lilypond.

        Args:
        - tremolo (str): The tremolo notation.
        - dots (str): Dots representing the note's duration extension.

        Returns:
        - str: The tremolo markup.
        """
        if tremolo != ":32":
            return ""

        if lilypond_minor_version() >= 22:
            if dots:
                return (
                    r"""_\tweak outside-staff-priority ##f """
                    r"""^\tweak avoid-slur #'inside """
                    r"""_\markup {\with-dimensions #'(0 . 0) #'(2.8 . 2.1) """
                    r"""\postscript "1.6 -0.2 moveto 2.6 0.8 lineto 1.8 -0.4 moveto """
                    r"""2.8 0.6 lineto 2.0 -0.6 moveto 3.0 0.4 lineto stroke" } """
                    r"""%{ requires Lilypond 2.22+ %} """
                )
            else:
                return (
                    r"""_\tweak outside-staff-priority ##f """
                    r"""^\tweak avoid-slur #'inside """
                    r"""_\markup {\with-dimensions #'(0 . 0) #'(2.5 . 2.1) """
                    r"""\postscript "1.1 0.4 moveto 2.1 1.4 lineto 1.3 0.2 moveto """
                    r"""2.3 1.2 lineto 1.5 0.0 moveto 2.5 1.0 lineto stroke" } """
                    r"""%{ requires Lilypond 2.22+ %} """
                )
        elif lilypond_minor_version() < 20:
            errExit(
                "tremolo requires Lilypond 2.20+, we found 2."
                + str(lilypond_minor_version())
            )
        elif dots:
            return (
                r"""_\tweak outside-staff-priority ##f """
                r"""^\tweak avoid-slur #'inside """
                r"""_\markup {\with-dimensions #'(0 . 0) #'(2.8 . 2.6) """
                r"""\postscript "1.4 1.6 moveto 2.4 2.6 lineto 1.6 1.4 moveto """
                r"""2.6 2.4 lineto 1.8 1.2 moveto 2.8 2.2 lineto stroke" } """
                r"""%{ requires Lilypond 2.20 %} """
            )
        else:
            return (
                r"""_\tweak outside-staff-priority ##f """
                r"""^\tweak avoid-slur #'inside """
                r"""_\markup {\with-dimensions #'(0 . 0) #'(2.5 . 2.6) """
                r"""\postscript "1.1 1.6 moveto 2.1 2.6 lineto 1.3 1.4 moveto """
                r"""2.3 2.4 lineto 1.5 1.2 moveto 2.5 2.2 lineto stroke" } """
                r"""%{ requires Lilypond 2.20 %} """
            )


def parseNote(word, origWord, line):
    """
    Parses a note in Jianpu notation and returns its components.

    This function interprets the Jianpu note notation, extracting the pitch,
    rhythm, and other musical characteristics.

    Args:
        word (str): The Jianpu notation for the note.
        origWord (str): The original word before any modifications.
        line (int): The line number where the note appears.

    Returns:
        tuple: A tuple containing the following components of the note:
            - figures (str): The figures representing the note's pitch (e.g., '1', '2', ... '7').
            - nBeams (int or None): The number of beams representing the note's rhythm (None if unspecified).
            - dots (str): Dots representing the note's duration extension.
            - octave (str): The octave indicator ('', ''', ''', ',', ',,').
            - accidental (str): The accidental ('#' for sharp, 'b' for flat, or '' if none).
            - tremolo (str): The tremolo notation (e.g., ':32') or an empty string if none.

    Raises:
        ValueError: If an unrecognized command is found in the word.
    """

    if word == ".":
        # (for not angka, TODO: document that this is now acceptable as an input word?)
        word = "-"
    word = word.replace("8", "1'").replace("9", "2'")
    word = word.replace("\u2019", "'")
    if "///" in word:
        tremolo, word = ":32", word.replace("///", "", 1)
    else:
        tremolo = ""
    # unrecognised stuff in it: flag as error, rather than ignoring and possibly getting a puzzling barsync fail
    if not re.match(r"[0-7.,'cqsdh\\#b-]+$", word):
        scoreError("Unrecognised command", origWord, line)

    # Identify figures with accidentals and octave indicators
    notes_with_accidental_octave = re.findall(r"[#b]*[-0-7][',]*", word)
    figures = [re.sub(r"[#b',]+", "", note) for note in notes_with_accidental_octave]
    accidentals = [
        re.sub(r"[0-7',-]", "", note) for note in notes_with_accidental_octave
    ]
    octaves = [re.sub(r"[#b0-7]", "", note) for note in notes_with_accidental_octave]

    dots = "".join(c for c in word if c == ".")
    nBeams = "".join(re.findall(r"[cqsdh\\]", word))
    if re.match(r"[\\]+$", nBeams):
        nBeams = len(
            nBeams
        )  # requested by a user who found British note-length names hard to remember; won't work if the \ is placed at the start, as that'll be a Lilypond command, so to save confusion we won't put this in the docstring
    elif nBeams:
        try:
            nBeams = list("cqsdh").index(nBeams)
        except ValueError:
            scoreError(
                "Can't calculate number of beams from " + nBeams + " in", origWord, line
            )
    else:
        nBeams = None  # unspecified

    return figures, nBeams, dots, octaves, accidentals, tremolo


def write_docs():
    """
    Write an HTML or Markdown version of the doc string.

    This function takes no arguments and returns nothing. It reads the docstring
    of the current module and converts it into an HTML or Markdown table,
    depending on the command line arguments passed to the script. The table
    contains information about the function arguments and their types.

    If the "--html" argument is passed, the table is formatted as an HTML table.
    If the "--markdown" argument is passed, the table is formatted as a Markdown table.
    If neither argument is passed, the table is formatted as plain text.

    The function prints the resulting table to standard output.
    """

    def htmlify(l):
        if "--html" in sys.argv:
            return l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        else:
            return l

    inTable = 0
    justStarted = 1
    for line in __doc__.split("\n"):
        if not line.strip():
            continue
        if ":" in line and line.split(":", 1)[1].strip():
            toGet, shouldType = line.split(":", 1)
            if not inTable:
                if "--html" in sys.argv:
                    # "<tr><th>To get:</th><th>Type:</th></tr>"
                    print("<table border>")
                else:
                    print("")
                inTable = 1
            if re.match(r".*[A-Za-z]\)$", shouldType):
                shouldType, note = shouldType.rsplit("(", 1)
                note = " (" + note
            else:
                note = ""
            if "--html" in sys.argv:
                print(
                    "<tr><td>"
                    + htmlify(toGet.strip())
                    + "</td><td><kbd>"
                    + htmlify(shouldType.strip())
                    + "</kbd>"
                    + htmlify(note)
                    + "</td>"
                )
            else:
                print(toGet.strip() + ": `" + shouldType.strip() + "`" + note + "\n")
        else:
            if "--markdown" in sys.argv:
                print("")
            elif inTable:
                print("</table>")
            elif not justStarted:
                print("<br>")
            inTable = justStarted = 0
            print(htmlify(line))
    if inTable and "--html" in sys.argv:
        print("</table>")


def merge_lyrics(content):
    """
    Merge lines starting with "H:(\s*\d+\.)" within each part of content,
    separated by "NextPart" or "NextScore". Each group of "H:(\s*\d+\.)"
    lines is replaced with a single merged line, removing the verse number.
    Replaces 'w*n' patterns with 'n' occurrences of 'w' and spaces '_'.

    Args:
        content (str): Content with parts separated by "NextPart" or "NextScore".

    Returns:
        str: Content with merged "H: \d+:" lines, preserving separators.
    """

    def process_part(part):
        def process_line(line):
            # Replace 'w*n' pattern with n copies of w and space '_'
            line = re.sub(
                r"(.)\*(\d+)", lambda m: "".join([m.group(1)] * int(m.group(2))), line
            )
            line = re.sub(r"(?<!\s)_", " _", line)
            line = re.sub(r"_(?!\s)", "_ ", line)
            return line

        # Standardize "H:" lines to "H:1."
        part = re.sub(r"^\s*H:(?!\s*\d+\.)", "H:1.", part, flags=re.MULTILINE)

        # Extract unique H: \d+ prefixes in order
        prefixes = re.findall(r"^\s*H:\s*(\d+\.)?", part, flags=re.MULTILINE)
        prefixes = list(dict.fromkeys(prefixes))  # Remove duplicates
        prefixes.sort(key=lambda prefix: -1 if prefix == "" else int(prefix[:-1]))

        for prefix in prefixes:
            # Merge lines with the same prefix
            label = rf"H:\s*{re.escape(prefix)}"
            h_lines = re.findall(rf"^\s*{label}(.*)$", part, re.MULTILINE)
            h_lines = [line.strip() for line in h_lines]
            merged_line = "H:" + process_line(" ".join(h_lines))

            def replace_first_H(match):
                replace_first_H.first_encountered = True
                return merged_line + "\n"

            replace_first_H.first_encountered = False
            part = re.sub(
                r"^\s*" + label + ".*(\n|$)",
                lambda m: replace_first_H(m)
                if not replace_first_H.first_encountered
                else "",
                part,
                flags=re.MULTILINE,
            )

        # Replace '0*n' with separated 0s within the part
        part = re.sub(
            r"(\s+)0\*(\d+)(\s+)",
            lambda m: m.group(1) + ("".join(["0 "] * int(m.group(2)))) + m.group(3),
            part,
        )
        return part

    parts = re.split(r"(NextPart|NextScore)", content)
    processed_parts = []

    for i in range(0, len(parts), 2):
        processed_part = process_part(parts[i])
        separator = parts[i + 1] + "\n" if i + 1 < len(parts) else ""
        processed_parts.append(processed_part + separator)

    return "".join(processed_parts).strip()


def getInput0(f, is_google_drive=False):
    """
    This function reads input data from a file or from standard input. If the
    input file is not found, it raises an IOError.
    :param f: The input file path.
    :param is_google_drive: A boolean flag indicating whether the input file
              is on Google Drive.
    :return: A list containing the input data.
    """
    inDat = []

    # Check if we are reading from Google Drive or a local file
    if is_google_drive:
        inDat.append(merge_lyrics(f))
    else:
        try:
            inDat.append(merge_lyrics(open(f, encoding="utf-8").read()))
        except IOError:
            errExit("Unable to read file " + f)

    if inDat:
        return inDat
    if not sys.stdin.isatty():
        return [fix_utf8(sys.stdin, "r").read()]
    # They didn't give us any input.  Try to use a
    # file chooser.  If that fails, just print the
    # help text.
    if os.path.exists("/usr/bin/osascript"):
        f = (
            os.popen(
                "osascript -e $'tell application \"System Events\"\nactivate\nset f to choose file\nend tell\nPOSIX path of f'"
            )
            .read()
            .rstrip()
        )
        if f:
            try:
                return [open(f, encoding="utf-8").read()]
            except:
                return [open(f).read()]
    sys.stderr.write(__doc__)
    raise SystemExit


def get_input(infile, is_google_drive=False):
    """
    Reads input from a file and returns it as a string.

    Args:
        infile (str): The path to the input file.
        is_google_drive (bool, optional): Whether the input file is stored in Google Drive. Defaults to False.

    Returns:
        str: The input data as a string.
    """
    inDat = getInput0(infile, is_google_drive)

    for i in range(len(inDat)):
        if inDat[i].startswith("\xef\xbb\xbf"):
            inDat[i] = inDat[i][3:]
        if inDat[i].startswith(r"\version"):
            errExit(
                "jianpu-ly does not READ Lilypond code.\nPlease see the instructions."
            )

    return " NextScore ".join(inDat)


def fix_utf8(stream, mode):
    """
    Fixes the encoding of the given stream to UTF-8, regardless of the system locale.

    Args:
        stream: The stream to fix the encoding for.
        mode: The mode in which the stream is opened ("r" for reading, "w" for writing, etc.).

    Returns:
        The stream with the fixed encoding.
    """
    # Python 3: please use UTF-8 for Lilypond, even if the system locale says something else
    import codecs
    if mode == "r":
        return codecs.getreader("utf-8")(stream.buffer)
    else:
        return codecs.getwriter("utf-8")(stream.buffer)


def fix_fullwidth(t):
    """
    Replaces fullwidth characters in a string with their ASCII equivalents.

    Args:
    t (str): The string to be processed.

    Returns:
    str: The processed string with fullwidth characters replaced by their ASCII equivalents.
    """
    utext = t
    r = []
    for c in utext:
        if 0xFF01 <= ord(c) <= 0xFF5E:
            r.append(chr(ord(c) - 0xFEE0))
        elif c == "\u201a":
            r.append(",")  # sometimes used as comma (incorrectly)
        elif c == "\uff61":
            r.append(".")
        else:
            r.append(c)
    utext = "".join(r)
    return utext


def graceNotes_markup(notes, isAfter):
    """
    Returns a LilyPond markup string for a sequence of grace notes.

    Args:
        notes (str): A string representing the sequence of grace notes.
        isAfter (bool): A boolean indicating whether the grace notes come after the main note.

    Returns:
        str: A LilyPond markup string for the grace notes.
    """
    if isAfter:
        cmd = "jianpu-grace-after"
    else:
        cmd = "jianpu-grace"
    r = []
    afternext = None
    thinspace = "\u2009"
    notes = grace_octave_fix(notes)
    for i in range(len(notes)):
        n = notes[i]
        if n == "#":
            r.append(r"\fontsize #-4 { \raise #0.6 { \sharp } }")
        elif n == "b":
            r.append(r"\fontsize #-4 { \raise #0.4 { \flat } }")
        elif n == "'":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == "''":
                above = ":"
            else:
                above = "."
            r.append(
                r"\override #'(direction . 1) \override #'(baseline-skip . 1.2) \dir-column { \line {"
            )
            afternext = r"} \line { " + '"' + thinspace + above + '" } }'
        elif n == ",":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == ",,":
                below = ":"
            else:
                below = "."
            r.append(r"\override #'(baseline-skip . 1.0) \center-column { \line { ")
            afternext = (
                r"} \line { \pad-to-box #'(0 . 0) #'(-0.2 . 0) " + '"' + below + '" } }'
            )
        else:
            if r and r[-1].endswith('"'):
                r[-1] = r[-1][:-1] + n + '"'
            else:
                r.append(f'"{n}"')
            if afternext:
                r.append(afternext)
                afternext = None
    return (
        r"^\tweak outside-staff-priority ##f ^\tweak avoid-slur #'inside ^\markup \%s { \line { %s } }"
        % (cmd, " ".join(r))
    )


def grace_octave_fix(notes):
    """
    This function takes a string of notes in jianpu notation and applies the following fixes:
    1. Moves '+ and ,+ to before the preceding number
    2. Replaces 8 and 9 with the respective higher octave notes

    Args:
    notes (str): A string of notes in jianpu notation

    Returns:
    str: A string of notes with the above fixes applied
    """

    # Move '+ and ,+ to before the preceding number
    notes = re.sub(r"([1-9])(')+", r"\2\1", notes)
    notes = re.sub(r"([1-9])(,)+", r"\2\1", notes)

    # Replacing 8 and 9 with the respective higher octave notes
    notes = notes.replace("8", "'1").replace("9", "'2")

    return notes


def gracenotes_western(notes):
    """
    Converts a list of Jiapu-style grace notes to LilyPond notation.

    Args:
    notes (list): A list of grace notes in Jianpu notation.

    Returns:
    str: A string of LilyPond notation representing the grace notes.
    """

    # for western and MIDI staffs
    notes = grace_octave_fix(notes)

    nextAcc = ""
    next8ve = "'"
    r = []
    for i in range(len(notes)):
        n = notes[i]
        if n == "#":
            nextAcc = "is"
        elif n == "b":
            nextAcc = "es"
        elif n == "'":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == "''":
                next8ve = "'''"
            else:
                next8ve = "''"
        elif n == ",":
            if i and notes[i - 1] == notes[i]:
                continue
            if notes[i : i + 2] == ",,":
                next8ve = ","
            else:
                next8ve = ""
        else:
            if n not in placeholders:
                continue  # TODO: errExit ?
            r.append(placeholders[n] + nextAcc + next8ve + "16")
            nextAcc = ""
            next8ve = "'"

    return " ".join(r)


def convert_ties_to_slurs(jianpu):
    """
    Convert tied notes in Jianpu notation to slurs.

    Args:
        jianpu (str): A string containing Jianpu notation with ties.

    Returns:
        str: The Jianpu notation with ties converted to slurs. Time signatures
             following ties are handled properly, preserving their placement.
    """
    # Remove comments from the input
    jianpu = re.sub(r"%.*$", "", jianpu, flags=re.MULTILINE)

    # Define the pattern to match the entire tied note sequence
    tied_note_sequence_pattern = r"(?<!\\)\([^()]*~[^()]*\)(?<!\\)"

    # protect ties within slurs
    def protect_ties_in_slurs(match):
        return match.group(0).replace("~", "__TIE__")

    jianpu = re.sub(tied_note_sequence_pattern, protect_ties_in_slurs, jianpu)

    # Pattern parts:
    note_pattern = r"([qshb]?(?:[1-7][',]*)+\.?)"  # Matches a note with optional modifier [qshb], digit 1-7, optional ' or ,, and optional dot.
    annotation_pattern = (
        r'(\s*[\^_]"[^"]*")*'  # Matches optional annotations with leading spaces.
    )
    dash_pattern = r"(\s+-)"  # Matches a space followed by a dash.
    tie_pattern = r"(\s+~\s+)"  # Matches a tie symbol with spaces before and after.
    dash_and_annotation_pattern = (
        r"(" + dash_pattern + annotation_pattern + ")*"
    )  # Combines dashes and annotations.
    time_signature_pattern = r"(\s*\d+/\d+\s*)?"

    # Full combined pattern for sequences of tied notes
    combined_tie_pattern = (
        note_pattern
        + annotation_pattern
        + dash_and_annotation_pattern
        + "(?:"  # Use the combined dash and annotation pattern here
        + tie_pattern
        + time_signature_pattern
        + note_pattern  # Include the time signature pattern here, optionally preceded by a newline
        + annotation_pattern
        + dash_and_annotation_pattern
        + ")+"  # And also here
    )

    # This function will be used as the replacement function in the sub call
    def slur_replacement(match):
        # Get the full matched string, preserving newlines
        matched_string = match.group(0)

        # Replace newlines followed by a time signature to a special token to avoid splitting
        matched_string = re.sub(r"(\n\s*\d+/\d+\s*)", r"__TIMESIG__\1", matched_string)

        # Split the string into its parts using the tie symbol as the delimiter
        parts = re.split(r"~\s*", matched_string)

        # Replace the special token back to the original time signature
        parts = [re.sub(r"__TIMESIG__", "", part) for part in parts]

        # Remove trailing whitespace from each part, except for newlines
        parts = [part.rstrip() for part in parts]

        # Construct the slur by wrapping all but the first part in parentheses
        slur_content = parts[0] + " ( " + " ".join(parts[1:]) + " )"

        # Ensure we don't have multiple spaces in a row, but preserve newlines
        slur_content = re.sub(r"[ \t\f\v]{2,}", " ", slur_content)

        # Move parenthesis before dashes
        slur_content = re.sub(
            r'((?:(?:\s+-)(?:\s+[\^_]"[^"]*")*' + r")+)(\s+[\(\)])",
            r"\2\1",
            slur_content,
        )

        return slur_content

    # Replace all instances of ties with slurs using the replacement function
    converted_jianpu = re.sub(combined_tie_pattern, slur_replacement, jianpu)

    return converted_jianpu.strip().replace("__TIE__", "~")


def reformat_slurs(jianpu):
    """
    Reformat slurs in Jianpu notation by moving opening and closing parentheses
    to after any dashes.

    In Jianpu notation, slurs are typically represented by parentheses. This function
    adjusts the positioning of these parentheses so that they follow any dashes ("-"),
    which represent extended note durations or connections between notes.

    Args:
        jianpu (str): A string containing Jianpu notation, which may include slurs.

    Returns:
        str: The Jianpu notation string with slurs reformatted.

    The function first removes any comments from the Jianpu string. Then, it searches for
    patterns where a slur parenthesis precedes a dash and rearranges them so that the
    parenthesis follows the dash. This reformatting aids in the visual clarity and
    correctness of the notation.
    """
    # Remove comments from the input
    jianpu = re.sub(r"%.*$", "", jianpu, flags=re.MULTILINE)

    # Move opening and closing parenthesis after dashes
    return re.sub(
        r'(\s+[\(\)])((?:(?:\s+-)(?:\s+[\^_]"[^"]*")*' + r")+)",
        r"\2\1",
        jianpu,
    )


def process_lyrics_line(line, do_hanzi_spacing):
    """
    Process a line of lyrics, including handling verse numbers and Chinese character spacing.

    Args:
    line (str): The line of lyrics to be processed.
    do_hanzi_spacing (bool): Whether to handle Chinese character spacing.

    Returns:
    str: The processed lyrics line.
    """
    toAdd = ""
    if (
        line
        and "1" <= line[0] <= "9"
        and (line[1] == "." or as_unicode(line)[1] == "\uff0e")
    ):
        # a verse number
        toAdd = fr'\set stanza = #"{line[:1]}." '
        line = line[2:].strip()

    if do_hanzi_spacing:
        # Handle Chinese characters (hanzi) and related spacing:
        # for overhanging commas etc to work
        l2 = [r"\override LyricText #'self-alignment-X = #LEFT "]
        if toAdd:
            l2.append(toAdd)
            toAdd = ""
        needSpace = 0
        for c in list(as_unicode(line)):
            # TODO: also cover those outside the BMP?  but beware narrow Python builds
            is_hanzi = 0x3400 <= ord(c) < 0xA700
            is_openquote = c in "\u2018\u201c\u300A"
            if needSpace and (is_hanzi or is_openquote):
                l2.append(" ")
                needSpace = 0
                if is_openquote:  # hang left
                    # or RIGHT if there's no punctuation after
                    l2.append(
                        r"\once \override LyricText #'self-alignment-X = #CENTER "
                    )
            if is_hanzi:
                needSpace = 1
            if c == "-":
                needSpace = 0  # TODO: document this: separate hanzi with - to put more than one on same note
            else:
                l2.append(c)
        line = "".join(l2)

    # Replace certain characters and encode as needed, and
    # prepare the lyrics line with or without verse numbers.
    processed_lyrics = toAdd + re.sub("(?<=[^- ])- ", " -- ", line).replace(
        " -- ", " --\n"
    )
    return processed_lyrics


def process_headers_line(line, headers):
    """
    Process a single line of headers in a Jianpu file.

    Args:
        line (str): A single line of headers in the format "header_name=header_value".
        headers (dict): A dictionary containing the current headers in the Jianpu file.

    Raises:
        ValueError: If the header value does not match the expected value.

    Returns:
        None
    """
    hName, hValue = line.split("=", 1)
    hName, hValue = hName.strip().lower(), hValue.strip()
    if not headers.get(hName, hValue) == hValue:
        if hName == "instrument":
            missing = "NextPart or NextScore"
        else:
            missing = "NextScore"
        errExit(
            f"Changing header '{hName}' from '{headers[hName]}' to '{hValue}' (is there a missing {missing}?)"
        )
    headers[hName] = hValue


def process_key_signature(word, out, midi, western, inTranspose, notehead_markup):
    """
    Process a key signature in LilyPond syntax and add it to the output.

    Args:
        word (str): The key signature in LilyPond syntax.
        out (list): The list to which LilyPond code should be appended.
        midi (bool): Whether the output is for MIDI.
        western (bool): Whether the output is for Western notation.
        inTranspose (int): The current transpose state.
        notehead_markup (NoteheadMarkup): The notehead markup object.

    Returns:
        int: The updated transpose state.
    """

    # Convert '#' and 'b' to Unicode for approximation display
    unicode_repr = (
        re.sub("(?<!=)b$", "\u266d", word.replace("#", "\u266f")).upper() + " "
    )
    notehead_markup.unicode_approx.append(unicode_repr)

    if midi or western:
        # Close any open transposition block
        if inTranspose:
            out.append("}")

        transposeTo = word.split("=")[1].replace("#", "is").replace("b", "es").lower()

        # Ensure correct octave for MIDI pitch
        if midi and transposeTo[0] in "gab":
            transposeTo += ","

        # Transpose command for key
        out.append(r"\transpose c " + transposeTo + r" { \key c \major ")

        inTranspose = 1
    else:
        # Non-transposing key change marker for display
        out.append(
            r"\mark \markup{%s}" % word.replace("b", r"\flat").replace("#", r"\sharp")
        )

    # Return the updated transpose state
    return inTranspose


def process_fingering(word, out):
    """
    Extracts the fingering from the word and maps it to a Unicode character.
    The Unicode character is then appended to the LilyPond finger notation command.

    Args:
    word (str): A string containing the fingering to be extracted.
    out (list): A list to which the LilyPond finger notation command is appended.

    Returns:
    None
    """
    # Extract the fingering from the word
    finger = word.split("=")[1]
    # Mapping from textual representation to Unicode character
    finger_to_unicode = {
        "1": "\u4e00",  # Chinese numeral 1
        "2": "\u4c8c",  # Chinese numeral 2
        "3": "\u4e09",  # Chinese numeral 3
        "4": "\u56db",  # Chinese numeral 4
        "souyin": "\u4e45",  # Symbol for Souyin
        "harmonic": "\u25cb",  # White circle symbol for harmonic
        "up": "\u2197",  # NE arrow
        "down": "\u2198",  # SE arrow
        "bend": "\u293b",  # Bottom arc anticlockwise arrow
        "tilde": "\u223c",  # Full-width tilde
    }
    # Get the Unicode character for the fingering, defaulting to the original string
    finger_unicode = finger_to_unicode.get(finger, finger)

    # Append the LilyPond finger notation command
    out.append(fr'\finger "{finger_unicode}"')


def process_time_signature(word, out, notehead_markup, midi):
    """
    Process a time signature and add it to the output.

    Args:
    - word (str): The time signature in the form of "num/denom".
    - out (list): The list to which the output should be appended.
    - notehead_markup (NoteheadMarkup): The NoteheadMarkup object to be updated.
    - midi (bool): Whether or not MIDI output is being generated.

    Returns:
    - None
    """

    # Check if there is an anacrusis (pickup measure) indicated by a comma
    if "," in word:  # anacrusis
        word, anac = word.split(",", 1)
    else:
        anac = ""

    # Add a markup for the time signature if it should be separate and if we're not generating MIDI
    if notehead_markup.separateTimesig and not midi:
        out.append(r"\mark \markup{" + word + "}")

    # Add the time signature to the output
    out.append(r"\time " + word)

    # Set the time signature in the notehead_markup for later reference
    num, denom = word.split("/")
    notehead_markup.setTime(int(num), int(denom))

    # If there is an anacrusis, handle it accordingly
    if anac:
        # Check for dotted anacrusis (e.g., "2.")
        if anac.endswith("."):
            a2 = anac[:-1]
            anacDotted = 1
        else:
            a2, anacDotted = anac, 0

        # Set the anacrusis in the notehead_markup
        notehead_markup.setAnac(int(a2), anacDotted)

        # Add the partial (anacrusis) to the output
        out.append(r"\partial " + anac)


def process_note(
    word,
    out,
    notehead_markup,
    lastPtr,
    afternext,
    not_angka,
    need_final_barline,
    maxBeams,
    line,
):
    """
    Process a note and return the updated values of lastPtr, afternext, need_final_barline, and maxBeams.

    This function takes a note (word) and various parameters regarding the notation and modifies the output list accordingly.
    It processes the note by applying octave changes, parsing the note, and applying any necessary markups. It also updates
    the pointer to the last note, the markup for the next note, and the maximum number of beams needed for the music piece.

    Args:
    - word (str): the note to be processed
    - out (list): the list of notes (output of processed notes)
    - notehead_markup (function): a function that returns the notehead markup
    - lastPtr (int): the index of the last note in the list
    - afternext (str): the markup for the next note
    - not_angka (bool): whether the note is a number or not (pertains to a specific notation system)
    - need_final_barline (bool): whether a final barline is needed at the end of the music piece
    - maxBeams (int): the maximum number of beams encountered so far in the piece
    - line (int): the line number in the source LilyPond data

    Returns:
    - lastPtr (int): the updated index of the last note in the list
    - afternext (str): the updated markup for the next note
    - need_final_barline (bool): the updated value indicating if a final barline is needed
    - maxBeams (int): the updated maximum number of beams
    """

    word0 = word  # Keep a copy of the original word for later use

    # Extract octave changes from the note, if present (indicated by "<" or ">")
    baseOctaveChange = "".join(c for c in word if c in "<>")
    if baseOctaveChange:
        notehead_markup.baseOctaveChange(baseOctaveChange)
        word = "".join(
            c for c in word if not c in "<>"
        )  # Remove octave changes from the note
        if not word:
            # If the word was only octave changes, no further processing is needed
            return lastPtr, afternext, need_final_barline, maxBeams

    # Parse the note to separate its components (figures, beams, etc.)
    figures, nBeams, dots, octaves, accidentals, tremolo = parseNote(word, word0, line)
    need_final_barline = (
        True  # After processing a note, a final barline is assumed to be needed
    )

    # Call the notehead markup function to get necessary markups before and after the note
    (
        b4last,
        aftrlast,
        this,
        need_space_for_accidental,
        nBeams,
        octave,
    ) = notehead_markup.toMarkup(
        figures, nBeams, dots, octaves, accidentals, tremolo, word0, line
    )

    # If there's any markup before the last note, prepend it to the last note in the output
    if b4last:
        out[lastPtr] = b4last + out[lastPtr]

    # If there's any markup after the last note, insert it after the last note in the output
    if aftrlast:
        out.insert(lastPtr + 1, aftrlast)

    # Update the pointer to the last note
    lastPtr = len(out)
    out.append(this)  # Add the current note to the output

    # If there's any markup for the next note, handle accidental spacing and append it
    if afternext:
        if need_space_for_accidental:
            afternext = afternext.replace(r"\markup", r"\markup \halign #2 ", 1)
        out.append(afternext)
        afternext = None  # Reset the markup for the next note

    # Update the maximum number of beams, accounting for octave if the notation is numerical
    if not_angka and "'" in octave:
        maxBeams = max(maxBeams, len(octave) * 0.8 + nBeams)
    else:
        maxBeams = max(maxBeams, nBeams)

    # Return the updated values
    return lastPtr, afternext, need_final_barline, maxBeams


def process_grace_notes(
    word, out, notehead_markup, midi, western, afternext, defined_jianpuGrace
):
    """
    Process grace notes in the given word and append the corresponding notation to `out`.

    Args:
        word (str): The word containing the grace note to be processed.
        out (list): The list to which the processed notation will be appended.
        notehead_markup: The notehead markup object.
        midi (bool): Whether to use MIDI notation.
        western (bool): Whether to use Western notation.
        afternext: The afternext object.
        defined_jianpuGrace (bool): Whether the jianpu-grace markup definition has already been appended to `out`.

    Returns:
        Tuple[bool, Any]: A tuple containing the updated value of `defined_jianpuGrace` and `afternext`.
    """
    gracenote_content = word[2:-1]  # Extract the content between 'g[' and ']'

    if midi or western:
        # Append Western notation grace note
        out.append(r"\acciaccatura { " + gracenotes_western(gracenote_content) + " }")
    else:
        if notehead_markup.tuplet != (1, 1):
            for i in range(1, 4):
                if r"\times" in out[-i]:
                    out[-i] = (
                        "\\once \\override TupletBracket.padding = #2.5 " + out[-i]
                    )
                    break
        # Handle the jianpu notation for grace note
        afternext = graceNotes_markup(gracenote_content, 0)
        if not notehead_markup.withStaff:
            out.append(r"\once \textLengthOn ")
        if not defined_jianpuGrace:
            defined_jianpuGrace = True
            # Append the necessary jianpu-grace markup definition to `out`
            out.append(
                r"""#(define-markup-command (jianpu-grace layout props text)
(markup?) "Draw right-pointing jianpu grace under text."
(let ((textWidth (cdr (ly:stencil-extent (interpret-markup layout props (markup (#:fontsize -4 text))) 0))))
(interpret-markup layout props
(markup
  #:line
  (#:right-align
   (#:override
    (cons (quote baseline-skip) 0.2)
    (#:column
     (#:line
      (#:fontsize -4 text)
      #:line
      (#:pad-to-box
       (cons -0.1 0)  ; X padding before grace
       (cons -1.6 0)  ; affects height of grace
       (#:path
        0.1
        (list (list (quote moveto) 0 0)
              (list (quote lineto) textWidth 0)
              (list (quote moveto) 0 -0.3)
              (list (quote lineto) textWidth -0.3)
              (list (quote moveto) (* textWidth 0.5) -0.3)
              (list (quote curveto) (* textWidth 0.5) -1 (* textWidth 0.5) -1 textWidth -1)))))))))))) """
            )
    return defined_jianpuGrace, afternext


def process_grace_notes_after(
    word, out, lastPtr, notehead_markup, midi, western, defined_JGR
):
    """
    Process the grace notes after the last note.

    Args:
    - word: str, the grace note content.
    - out: list, the list of output strings.
    - lastPtr: int, the index of the last note.
    - notehead_markup: object, the notehead markup object.
    - midi: bool, whether to use MIDI notation.
    - western: bool, whether to use Western notation.
    - defined_JGR: bool, whether the jianpu-grace-after markup command is defined.

    Returns:
    - defined_JGR: bool, whether the jianpu-grace-after markup command is defined.
    """
    gracenote_content = word[
        1:-2
    ]  # Remove the "[" and "]g" to isolate the grace note content
    if midi or western:
        # Handle grace notes for MIDI or Western notation:
        out[lastPtr] = (
            r" \afterGrace { "
            + out[lastPtr]
            + " } { "
            + gracenotes_western(gracenote_content)
            + " }"
        )
    else:
        if notehead_markup.tuplet != (1, 1):
            for i in range(1, 4):
                if r"\times" in out[-i]:
                    out[-i] = (
                        "\\once \\override TupletBracket.padding = #2.5 " + out[-i]
                    )
                    break

        # Handle grace notes for Jianpu notation:
        if not notehead_markup.withStaff:
            out[lastPtr] = r"\once \textLengthOn " + out[lastPtr]
        out.insert(lastPtr + 1, graceNotes_markup(gracenote_content, 1))
        if not defined_JGR:
            defined_JGR = True
            out[lastPtr] = (
                r"""#(define-markup-command (jianpu-grace-after layout props text)
(markup?) "Draw left-pointing jianpu grace under text."
(let ((textWidth (cdr (ly:stencil-extent (interpret-markup layout props (markup (#:fontsize -4 text))) 0))))
(interpret-markup layout props
(markup
  #:line
  (#:halign -4
   (#:override
    (cons (quote baseline-skip) 0.2)
    (#:column
     (#:line
      (#:fontsize -4 text)
      #:line
      (#:pad-to-box (cons 0 0)
       (cons -1.6 0)  ; affects height of grace
      (#:path
       0.1
       (list (list (quote moveto) 0 0)
             (list (quote lineto) textWidth 0)
             (list (quote moveto) 0 -0.3)
             (list (quote lineto) textWidth -0.3)
             (list (quote moveto) (* textWidth 0.5) -0.3)
             (list (quote curveto) (* textWidth 0.5) -1 (* textWidth 0.5) -1 0 -1)))))))))))) """
                + out[lastPtr]
            )
    return defined_JGR


def collapse_tied_notes(out):
    """
    Collapse sequences of tied notes into longer ones in the given LilyPond code.

    Args:
        out: str
            A string containing LilyPond musical notation code.

    Returns:
        str: The inputted LilyPond code with sequences of tied notes collapsed
        into longer notes, staff spacing corrected and bar checks adjusted.

    This function transforms sequences of tied notes into their equivalent
    longer note representations. It also corrects the staff spacing to maintain
    a consistent look throughout the score and adjusts bar checks for accurate
    measure counting.
    """
    # Patterns for converting sequences of tied notes into longer notes
    note_patterns = [
        (4, r"\.", "1."),  # in 12/8, 4 dotted crotchets = dotted semibreve
        (4, "", "1"),  # 4 crotchets = semibreve
        (3, "", "2."),  # 3 crotchets = dotted minim
        (2, r"\.", "2."),  # in 6/8, 2 dotted crotchets = dotted minim
        (2, "", "2"),  # 2 crotchets = minim
    ]

    # Use regular expressions to match tied note patterns and
    # replace them with the corresponding long note.
    for numNotes, dot, result in note_patterns:
        # Define regex pattern for tied notes.
        tied_note_pattern = (
            r"(?P<note>[^<][^ ]*|<[^>]*>)4"
            + dot
            + r"((?::32)?) +~(( \\[^ ]+)*) "
            + " +~ ".join([r"(?P=note)4" + dot] * (numNotes - 1))
        )
        out = re.sub(tied_note_pattern, r"\g<note>" + result + r"\g<2>\g<3>", out)

        tremolo_pattern = (
            r"\\repeat tremolo "
            + str(4 if not dot else 6)
            + r" { (?P<note1>[^ ]+)32 (?P<note2>[^ ]+)32 } +~(( \\[^ ]+)*) "
            + " +~ ".join([r"< (?P=note1) (?P=note2) >4" + dot] * (numNotes - 1))
        )
        out = re.sub(
            tremolo_pattern,
            r"\\repeat tremolo "
            + str(4 * numNotes if not dot else 6 * numNotes)
            + r" { \g<note1>32 \g<note2>32 }\g<3>",
            out,
        )

        out = out.replace(" ".join([r"r4" + dot] * numNotes), "r" + result)

    # Dynamics should be attached inside the tremolo, except for '\bar'.
    out = re.sub(
        r"(\\repeat tremolo [^{]+{ [^ ]+)( [^}]+ })(( +\\[^b][^ ]*)+)",
        r"\g<1>\g<3>\g<2>",
        out,
    )

    # Replace placeholders with actual bar numbers.
    out = re.sub(r"(%\{ bar [0-9]*: %\} )r([^ ]* \\bar)", r"\g<1>R\g<2>", out)

    # Adjust staff spacing for consistent look across the entire score.
    out = out.replace(
        r"\new RhythmicStaff \with {",
        r"\new RhythmicStaff \with {"
        + r"\override VerticalAxisGroup.default-staff-staff-spacing = "
        + r"#'((basic-distance . 6) (minimum-distance . 6) (stretchability . 0)) ",
    )

    return out


def finalize_output(out_list, need_final_barline, midi, western, not_angka):
    """
    Refines the music notation output by making several adjustments.

    Args:
        out_list (list): A list of strings representing the music score.
        need_final_barline (bool): Indicates whether a final barline is needed.
        midi (bool): Flag for whether the output format is MIDI.
        western (bool): Flag for whether the output format is Western notation.
        not_angka (bool): Flag for whether the output format is numeric notation.

    Returns:
        str: The refined musical score as a string.

    This function fine-tunes the musical notation output by carrying out various tasks like adding
    a final barline if needed, consolidating consecutive \mark \markup{} commands, ensuring each line
    is suitably terminated and does not exceed 60 characters in length, combining tied notes into
    their corresponding single notes, replacing bold markup commands with simple ones, and correcting
    the improper partitioning of long note sequences.
    """

    # Add a final barline if it's needed and we're not creating a MIDI file.
    if need_final_barline and not midi:
        out_list.append(r'\bar "|."')

    # Combine consecutive \mark \markup{} commands into a single command.
    i = 0
    while i < len(out_list) - 1:
        while (
            i < len(out_list) - 1
            and out_list[i].startswith(r"\mark \markup{")
            and out_list[i].endswith("}")
            and out_list[i + 1].startswith(r"\mark \markup{")
            and out_list[i + 1].endswith("}")
        ):
            nbsp = " "  # No need for the encoded non-breaking space, Python 3 defaults to unicode
            out_list[i] = (
                out_list[i][:-1]
                + nbsp
                + " "
                + out_list[i + 1][len(r"\mark \markup{") :]
            )
            del out_list[i + 1]
        i += 1

    # Ensure that each line ends properly and does not surpass 60 characters.
    for i in range(len(out_list) - 1):
        if not out_list[i].endswith("\n"):
            if "\n" in out_list[i] or len(out_list[i]) > 60:
                out_list[i] += "\n"
            else:
                out_list[i] += " "

    # Join all sequences and strings in the output list into a single string.
    out_str = "".join(out_list)

    # If we're outputting to MIDI or using Western notation, collapse tied notes.
    if midi or western:
        out_str = collapse_tied_notes(out_str)

    # If we're using numeric notation, change all bold markup commands to simple markup.
    if not_angka:
        out_str = out_str.replace("make-bold-markup", "make-simple-markup")

    # Adjust the breaking up of long notes in the musical score.
    pattern = r"([a-g]+[',]*)4\s*~\s*\(\s*([a-g]+[',]*)2\."
    out_str = re.sub(
        pattern,
        lambda m: m.group(1) + "1 (" if m.group(1) == m.group(2) else m.group(0),
        out_str,
    )

    # Replace \breathe with \tweak Y-offset #1 \breathe
    out_str = out_str.replace(r"\breathe", r"\tweak Y-offset #1 \breathe")

    return out_str


def getLY(score, headers=None, midi=True):
    """
    Transforms a given score into LilyPond format.

    Args:
        score (str): The raw input string containing musical notation.
        headers (dict): A dictionary with LilyPond header information, defaults to None.
        midi (bool): A Boolean flag indicating whether MIDI output is desired, defaults to True.

    Returns:
        tuple: A 4-tuple containing the generated output in LilyPond format,
               the maximum number of beams found, a list of processed lyrics,
               and the dictionary of headers.
    """

    # Check if MIDI output is not being generated
    if not midi:
        # In Jianpu, ties need to be converted into slurs.
        score = convert_ties_to_slurs(score)
    else:
        # In Staff, slurs should not break dashes.
        score = reformat_slurs(score)

    # Use an empty dictionary for headers if not provided to avoid mutable default argument
    if not headers:
        headers = {}

    lyrics = []  # Initialize list to store processed lyrics
    notehead_markup.initOneScore()  # Initialize notation specifics for one score
    out = []  # Output list to accumulate LilyPond code
    maxBeams = 0  # Variable to track the maximum number of beams
    need_final_barline = False  # Flag to determine if a final barline is needed
    repeatStack = []  # Stack to handle repeat barlines
    lastPtr = 0  # Position tracker for handling elements added to `out`
    escaping = inTranspose = 0  # Flags for escaping LilyPond blocks and transposing
    afternext = defined_jianpuGrace = defined_JGR = None  # Initialize state flags

    for line in score.split("\n"):
        line = fix_fullwidth(line).strip()
        # Upgrade path compatibility for tempo
        line = re.sub(r"^%%\s*tempo:\s*(\S+)\s*$", r"\1", line)
        if line.startswith("LP:"):
            # Escaped LilyPond block.
            escaping = 1
            if len(line) > 3:
                out.append(line[3:] + "\n")  # remainder of current line
        elif line.startswith(":LP"):
            # TODO: and process the rest of the line?  (assume on line of own for now)
            escaping = 0
        elif escaping:
            out.append(line + "\n")
        elif not line:
            pass
        elif line.startswith("L:") or line.startswith("H:"):
            # lyrics
            do_hanzi_spacing = line.startswith("H:")
            line = line[2:].strip()
            processed_lyrics = process_lyrics_line(line, do_hanzi_spacing)
            lyrics.append(processed_lyrics)
        elif re.match(r"\s*[A-Za-z]+\s*=", line):
            # Lilypond header
            process_headers_line(line, headers)
        else:
            line = re.sub(
                '(?<= )[_^]"[^" ]* [^"]*"(?= |$)',
                lambda m: m.group().replace(" ", chr(0)),
                " " + line,
            )[
                1:
            ]  # multi-word text above/below stave
            for word in line.split():
                word = word.replace(chr(0), " ")
                if word in ["souyin", "harmonic", "up", "down", "bend", "tilde"]:
                    word = "Fr=" + word  # (Fr= before these is optional)
                if word.startswith("%"):
                    break  # a comment
                elif re.match("[1-468]+[.]*=[1-9][0-9]*$", word):
                    out.append(r"\tempo " + word)  # TODO: reduce size a little?
                elif re.match("[16]=[A-Ga-g][#b]?$", word):  # key
                    inTranspose = process_key_signature(
                        word, out, midi, western, inTranspose, notehead_markup
                    )
                elif word.startswith("Fr="):
                    process_fingering(word, out)
                elif re.match("letter[A-Z]$", word):
                    # TODO: not compatible with key change at same point, at least not in lilypond 2.20 (2nd mark mentioned will be dropped)
                    out.append(r'\mark \markup { \box { "%s" } }' % word[-1])
                elif re.match(r"R\*[1-9][0-9\/]*$", word):
                    if not western:
                        # \compressFullBarRests on Lilypond 2.20, \compressEmptyMeasures on 2.22, both map to \set Score.skipBars
                        out.append(
                            r"\set Score.skipBars = ##t \override MultiMeasureRest #'expand-limit = #1 "
                        )
                    out.append(r"R" + notehead_markup.wholeBarRestLen() + word[1:])
                elif re.match(
                    "[1-9][0-9]*/[1-468]+(,[1-9][0-9]*[.]?)?$", word
                ):  # time signature
                    process_time_signature(word, out, notehead_markup, midi)
                elif word == "OnePage":
                    if notehead_markup.onePage:
                        sys.stderr.write(
                            "WARNING: Duplicate OnePage, did you miss out a NextScore?\n"
                        )
                    notehead_markup.onePage = 1
                elif word == "KeepOctave":
                    pass  # undocumented option removed in 1.7, no effect
                # TODO: document this.  If this is on, you have to use c in a note to go back to crotchets.
                elif word == "KeepLength":
                    notehead_markup.keepLength = 1
                elif word == "NoBarNums":
                    if notehead_markup.noBarNums:
                        sys.stderr.write(
                            "WARNING: Duplicate NoBarNums, did you miss out a NextScore?\n"
                        )
                    notehead_markup.noBarNums = 1
                elif word == "SeparateTimesig":
                    if notehead_markup.separateTimesig:
                        sys.stderr.write(
                            "WARNING: Duplicate SeparateTimesig, did you miss out a NextScore?\n"
                        )
                    notehead_markup.separateTimesig = 1
                    out.append(r"\override Staff.TimeSignature #'stencil = ##f")
                elif word in ["angka", "Indonesian"]:
                    global not_angka
                    if not_angka:
                        sys.stderr.write(
                            "WARNING: Duplicate angka, did you miss out a NextScore?\n"
                        )
                    not_angka = True
                elif word == "WithStaff":
                    pass
                elif word == "PartMidi":
                    pass  # handled in process_input
                elif word[0] == "R" and word[-1] == "{":  # word == "R{" or "R2{"
                    n = int(word[1:-1]) if len(word) > 2 else 2
                    repeatStack.append((1, 0, 0))
                    out.append(rf"\repeat volta {n} {{")
                elif re.match("R[1-9][0-9]*{$", word):
                    times = int(word[1:-1])
                    repeatStack.append((1, notehead_markup.barPos, times - 1))
                    out.append(r"\repeat percent %d {" % times)
                elif word == "}":
                    numBraces, oldBarPos, extraRepeats = repeatStack.pop()
                    out.append("}" * numBraces)
                    # Re-synchronise so bar check still works if percent is less than a bar:
                    newBarPos = notehead_markup.barPos
                    while newBarPos < oldBarPos:
                        newBarPos += notehead_markup.barLength
                    # newBarPos-oldBarPos now gives the remainder (mod barLength) of the percent section's length
                    notehead_markup.barPos = (
                        notehead_markup.barPos + (newBarPos - oldBarPos) * extraRepeats
                    ) % notehead_markup.barLength
                    # TODO: update barNo also (but it's used only for error reports)
                elif word == "A{":
                    repeatStack.append((2, notehead_markup.barPos, 0))
                    out.append(r"\alternative { {")
                elif word == "|" and repeatStack and repeatStack[-1][0] == 2:
                    # separate repeat alternates (if the repeatStack conditions are not met i.e. we're not in an A block, then we fall through to the undocumented use of | as barline check below)
                    out.append("} {")
                    notehead_markup.barPos = repeatStack[-1][1]
                elif (
                    word.startswith("\\")
                    or word in ["(", ")", "~", "->", "|"]
                    or word.startswith('^"')
                    or word.startswith('_"')
                ):
                    # Lilypond command, \p, ^"text", barline check (undocumented, see above), etc
                    if out and "afterGrace" in out[lastPtr]:
                        # apply to inside afterGrace in midi/western
                        out[lastPtr] = out[lastPtr][:-1] + word + " }"
                    else:
                        out.append(word)
                elif re.match(r"[1-9][0-9]*\[$", word):
                    # tuplet start, e.g. 3[
                    fitIn = int(word[:-1])
                    i = 2
                    while i < fitIn:
                        i *= 2
                    if i == fitIn:
                        num = int(fitIn * 3 / 2)
                    else:
                        num = int(i / 2)
                    out.append("\\times %d/%d {" % (num, fitIn))
                    notehead_markup.tuplet = (num, fitIn)
                elif word == "]":  # tuplet end
                    out.append("}")
                    notehead_markup.tuplet = (1, 1)
                elif re.match(r"g\[[#b',1-9\s]+\]$", word):
                    defined_jianpuGrace, afternext = process_grace_notes(
                        word,
                        out,
                        notehead_markup,
                        midi,
                        western,
                        afternext,
                        defined_jianpuGrace,
                    )
                elif re.match(r"\[[#b',1-9]+\]g$", word):
                    defined_JGR = process_grace_notes_after(
                        word, out, lastPtr, notehead_markup, midi, western, defined_JGR
                    )
                elif word == "Fine":
                    need_final_barline = False
                    out.append(
                        r'''\once \override Score.RehearsalMark #'break-visibility = #begin-of-line-invisible \once \override Score.RehearsalMark #'self-alignment-X = #RIGHT \mark "Fine" \bar "|."'''
                    )
                elif word == "DC":
                    need_final_barline = False
                    out.append(
                        r'''\once \override Score.RehearsalMark #'break-visibility = #begin-of-line-invisible \once \override Score.RehearsalMark #'self-alignment-X = #RIGHT \mark "D.C. al Fine" \bar "||"'''
                    )
                else:  # note (or unrecognised)
                    lastPtr, afternext, need_final_barline, maxBeams = process_note(
                        word,
                        out,
                        notehead_markup,
                        lastPtr,
                        afternext,
                        not_angka,
                        need_final_barline,
                        maxBeams,
                        line,
                    )

    # Final checks and finalizations
    if notehead_markup.barPos == 0 and notehead_markup.barNo == 1:
        errExit(f"No jianpu in score {scoreNo}")
    if (
        notehead_markup.inBeamGroup
        and not midi
        and not western
        and not notehead_markup.inBeamGroup == "restHack"
    ):
        out[lastPtr] += "]"  # needed if ending on an incomplete beat
    if inTranspose:
        out.append("}")
    if repeatStack:
        errExit(f"Unterminated repeat in score {scoreNo}")
    if escaping:
        errExit(f"Unterminated LP: in score {scoreNo}")
    notehead_markup.endScore()  # perform checks

    # Finalize the output by performing additional cleanup
    out = finalize_output(out, need_final_barline, midi, western, not_angka)

    return out, maxBeams, lyrics, headers


def process_input(inDat, withStaff=False):
    """
    Process the input data and return the corresponding LilyPond code.

    Args:
    - inDat: str - The input data to be processed.
    - withStaff: bool - Whether to include staff notation in the output.

    Returns:
    - str - The LilyPond code corresponding to the input data.
    """
    global unicode_mode
    unicode_mode = not not re.search(r"\sUnicode\s", " " + inDat + " ")
    if unicode_mode:
        return get_unicode_approx(
            re.sub(r"\sUnicode\s", " ", " " + inDat + " ").strip()
        )
    ret = []
    global scoreNo, western, has_lyrics, midi, not_angka, maxBeams, uniqCount, notehead_markup
    uniqCount = 0
    notehead_markup = NoteheadMarkup(withStaff)
    scoreNo = 0  # incr'd to 1 below
    western = False
    poet1st = not re.search(r"^\s*poet=[^\n]+填词", inDat, re.M)
    hasarranger = re.search(r"^\s*arranger=", inDat, re.M)

    for score in re.split(r"\sNextScore\s", " " + inDat + " "):
        if not score.strip():
            continue
        scoreNo += 1
        # The occasional false positive doesn't matter: has_lyrics==False is only an optimisation so we don't have to create use_rest_hack voices.  It is however important to always detect lyrics if they are present.
        has_lyrics = not not re.search("(^|\n)[LH]:", score)
        parts = [p for p in re.split(r"\sNextPart\s", " " + score + " ") if p.strip()]
        for midi in [False, True]:
            not_angka = False  # may be set by getLY
            if scoreNo == 1 and not midi:
                # now we've established non-empty
                ret.append(all_scores_start(poet1st, hasarranger))
            # TODO: document this (results in 1st MIDI file containing all parts, then each MIDI file containing one part, if there's more than 1 part)
            separate_score_per_part = (
                midi
                and re.search(r"\sPartMidi\s", " " + score + " ")
                and len(parts) > 1
            )
            for separate_scores in (
                [False, True] if separate_score_per_part else [False]
            ):
                headers = {}  # will accumulate below
                for partNo, part in enumerate(parts):
                    if partNo == 0 or separate_scores:
                        ret.append(score_start())
                    out, maxBeams, lyrics, headers = getLY(part, headers, midi)

                    if notehead_markup.withStaff and notehead_markup.separateTimesig:
                        errExit(
                            "Use of both WithStaff and SeparateTimesig in the same piece is not yet implemented"
                        )
                    if len(parts) > 1 and "instrument" in headers:
                        inst = headers["instrument"]
                        del headers["instrument"]
                    else:
                        inst = None
                    if midi:
                        ret.append(
                            midi_staff_start() + " " + out + " " + midi_staff_end()
                        )
                    else:
                        staffStart, voiceName = jianpu_staff_start(
                            inst, notehead_markup.withStaff
                        )
                        ret.append(staffStart + " " + out + " " + jianpu_staff_end())
                        if notehead_markup.withStaff:
                            western = True
                            staffStart, voiceName = western_staff_start(inst)
                            ret.append(
                                staffStart
                                + " "
                                + getLY(part)[0]
                                + " "
                                + western_staff_end()
                            )
                            western = False
                        if lyrics:
                            ret.append(
                                "".join(
                                    lyrics_start(voiceName)
                                    + l
                                    + " "
                                    + lyrics_end()
                                    + " "
                                    for l in lyrics
                                )
                            )
                    if partNo == len(parts) - 1 or separate_scores:
                        ret.append(score_end(**headers))
    ret = "".join(r + "\n" for r in ret)
    ret = re.sub(r'([\^_])"(\\[^"]+)"', r"\1\2", ret)

    # Add staff group if there are multiple sections starting with "BEGIN JIANPU STAFF".
    # If so, add "\new StaffGroup <<" after first occurance of "%% === BEGIN JIANPU STAFF ===".
    # and add ">>" after the last occurance of "% === END JIANPU STAFF ==="
    if ret.count("=== BEGIN JIANPU STAFF ===") > 1:
        ret = ret.replace(
            "=== BEGIN JIANPU STAFF ===",
            "=== BEGIN JIANPU STAFF ===\n\\new StaffGroup <<",
            1,
        )
        ret = "=== END JIANPU STAFF ===\n>>".join(ret.rsplit("=== END JIANPU STAFF ===", 1))

    if lilypond_minor_version() >= 24:
        # needed to avoid deprecation warnings on Lilypond 2.24
        ret = re.sub(r"(\\override [A-Z][^ ]*) #'", r"\1.", ret)
    return ret


def get_unicode_approx(inDat):
    """
    Returns the Unicode approximation of the given input data.

    Args:
        inDat (str): The input data to be converted to Unicode.

    Returns:
        str: The Unicode approximation of the input data.
    """
    if re.search(r"\sNextPart\s", " " + inDat + " "):
        errExit("multiple parts in Unicode mode not yet supported")
    if re.search(r"\sNextScore\s", " " + inDat + " "):
        errExit("multiple scores in Unicode mode not yet supported")
    # TODO: also pick up on other not-supported stuff e.g. grace notes (or check for unicode_mode when these are encountered)
    global notehead_markup, western, midi, uniqCount, scoreNo, has_lyrics, not_angka, maxBeams
    notehead_markup = NoteheadMarkup()
    western = midi = not_angka = False
    # doesn't matter for our purposes (see 'false positive' comment above)
    has_lyrics = True
    uniqCount = 0
    scoreNo = 1
    getLY(inDat, {})
    u = "".join(notehead_markup.unicode_approx)
    if u.endswith("\u2502"):
        u = u[:-1] + "\u2551"
    return u


try:
    from shlex import quote
except ImportError:

    def quote(f):
        return "'" + f.replace("'", "'\"'\"'") + "'"


def write_output(outDat, fn, infile):
    """
    Write the output data to a file or to the console.

    Args:
    - outDat: the output data to be written
    - fn: the file name to write to, or None to write to the console
    - infile: the input file name

    Returns: None
    """
    if sys.stdout.isatty():
        if unicode_mode:
            if sys.platform == "win32" and sys.version_info() < (3, 6):
                # Unicode on this console could be a problem
                print(
                    """
For Unicode approximation on this system, please do one of these things:
(1) redirect output to a file,
(2) upgrade to Python 3.6 or above, or
(3) switch from Microsoft Windows to GNU/Linux"""
                )
                return
        else:  # normal Lilypond
            if not fn:
                # They didn't redirect our output.
                # Try to be a little more 'user friendly'
                # and see if we can put it in a temporary
                # Lilypond file and run Lilypond for them.
                # New in jianpu-ly v1.61.
                if len(sys.argv) > 1:
                    fn = os.path.split(infile)[1]
                else:
                    fn = "jianpu"
                if os.extsep in fn:
                    fn = fn[: -fn.rindex(os.extsep)]
                fn += ".ly"

                cwd = os.getcwd()
                os.chdir(tempfile.gettempdir())
                print("Outputting to " + os.getcwd() + "/" + fn)
            else:
                cwd = None

            o = open(fn, "w")
            fix_utf8(o, "w").write(outDat)
            o.close()
            pdf = fn[:-3] + ".pdf"

            try:
                os.remove(pdf)  # so won't show old one if lilypond fails
            except:
                pass
            cmd = lilypond_command()
            if cmd:
                if lilypond_minor_version() >= 20:
                    # if will be viewed on-screen rather than printed, and it's not a Retina display
                    cmd += " -dstrokeadjust"
                os.system(cmd + " " + quote(fn))
                if sys.platform == "darwin":
                    os.system("open " + quote(pdf.replace("..pdf", ".pdf")))
                elif sys.platform.startswith("win"):
                    import subprocess

                    subprocess.Popen([quote(pdf)], shell=True)
                elif hasattr(shutil, "which") and shutil.which("evince"):
                    os.system("evince " + quote(pdf))
            if cwd:
                os.chdir(cwd)
            return
    fix_utf8(sys.stdout, "w").write(outDat)


def reformat_key_time_signatures(s, with_staff):
    """
    Reformat key and time signatures in a string representing musical notation. The function
    reformats key signatures, extracts Jianpu staff notation, sorts unique time signatures,
    and updates the key signature line to include sorted time signatures. If there's only
    one time signature, it includes a command to omit it from the staff.

    Args:
    - s (str): String containing musical notation to be reformatted.
    - with_staff (bool): Unused parameter, kept for backward compatibility.

    Returns:
    - str: Reformatted string with updated key and time signatures.
    """

    # Pattern to capture key signature with optional flat or sharp
    key_signature_pattern = re.compile(r"\\markup\{\s*1=([A-G])(\\flat|\\sharp)?\}")

    # Function to replace key signature matches with correct formatting
    def replace_key_signature(match):
        note, alteration = match.group(1), match.group(2)
        alteration_symbol = (
            "♭" if alteration == "\\flat" else "♯" if alteration == "\\sharp" else ""
        )
        return f"\\markup{{1={alteration_symbol}{note}}}"

    # Apply replacement to key signatures
    s = key_signature_pattern.sub(replace_key_signature, s)

    # Extract Jianpu staff notation section
    jianpu_staff_section_match = re.search(
        r"%% === BEGIN JIANPU STAFF ===(.*?)% === END JIANPU STAFF ===", s, re.DOTALL
    )

    if jianpu_staff_section_match:
        jianpu_staff_section = jianpu_staff_section_match.group(1)

        # Find unique time signatures and maintain their order of occurrences
        time_signatures = re.findall(r"\\time\s+(\d+)/(\d+)", jianpu_staff_section)

        # Remove duplicates while preserving order using dict.fromkeys()
        time_signatures_ordered = list(dict.fromkeys(time_signatures))

        # Convert ordered time signatures back to strings in the preferred format
        time_signatures_str = " ".join(
            [
                f"\\hspace #1 \\fraction {num} {denom}"
                for num, denom in time_signatures_ordered
            ]
        )

        # Update original string with sorted time signatures
        keysig = re.search(r"\\mark \\markup\{\s*([16]=[♭♯]?[A-G])\}", s).group(1)
        s = re.sub(r"(\\override Staff\.Stem\.transparent = ##t\s+)\\mark \\markup\{[16]=[♭♯]?[A-G]\}", r"\1", s)
        s = s.replace(
            'keytimesignature=""',
            r"keytimesignature=\markup{ \concat { "
            + keysig
            + " "
            + time_signatures_str
            + " } }",
        )

        # Replace remaining time signatures using fractions
        s = re.sub(
            r"\\time\s+(\d+)/(\d+)",
            r"\\override Staff.TimeSignature.stencil = #ly:text-interface::print \\override Staff.TimeSignature.text = \\markup { \\translate #'(0 . -0.5) \\bold \\fontsize #2 \\fraction \1 \2} \\time \1/\2",
            s,
        )

    return s


def filter_out_jianpu(lilypond_text):
    """
    This function accepts a LilyPond formatted text string as input and removes
    any section between the lines that start with "%% === BEGIN JIANPU STAFF ==="
    and "% === END JIANPU STAFF ===" (both lines inclusive).

    Parameters:
    lilypond_text (str): String containing LilyPond notation

    Returns:
    str: The modified LilyPond text with all JIANPU sections removed
    """

    begin_jianpu = "\n%% === BEGIN JIANPU STAFF ===\n"
    end_jianpu = "\n% === END JIANPU STAFF ===\n"

    while True:
        start_index = lilypond_text.find(begin_jianpu)
        end_index = lilypond_text.find(end_jianpu) + len(end_jianpu)

        if start_index != -1 and end_index != -1:
            # Remove the JIANPU section
            lilypond_text = lilypond_text[:start_index] + lilypond_text[end_index:]
        else:
            # No more JIANPU sections exist, so break from the loop
            break

    return lilypond_text


# Function to download plain text file from Google Drive
def download_file_from_google_drive(id):
    """
    This function downloads a Google Docs document as plain text using its file ID.

    :param id: The ID of the file to download from Google Drive
    :returns: The text content of the downloaded file
    """

    # Construct the URL for downloading the document as plain text
    url = f"https://docs.google.com/document/export?format=txt&id={id}"

    # Send a GET request to the constructed URL
    response = requests.get(url)
    response.raise_for_status()

    # Decode the response content with UTF-8
    text = response.content.decode("utf-8")

    # Remove BOM if present
    if text.startswith("\ufeff"):
        text = text[len("\ufeff") :]

    # Replace CRLF with LF
    text = text.replace("\r\n", "\n")

    # Return the processed text
    return text


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        args (argparse.Namespace): An object containing parsed arguments.
    """
    # Create ArgumentParser object
    parser = argparse.ArgumentParser()

    # Define command-line options
    parser.add_argument(
        "--html", action="store_true", default=False, help="output in HTML format"
    )
    parser.add_argument(
        "-m",
        "--markdown",
        action="store_true",
        default=False,
        help="output in Markdown format",
    )
    parser.add_argument(
        "-s",
        "--staff-only",
        action="store_true",
        default=False,
        help="only output Staff sections",
    )
    parser.add_argument(
        "-B",
        "--with-staff",
        action="store_true",
        default=False,
        help="output both Jianpu and Staff sections",
    )
    parser.add_argument(
        "-b",
        "--bar-number-every",
        type=int,
        default=0,
        help="option to set bar number, default is 0 for beginning of each line",
    )
    parser.add_argument(
        "-i",
        "--instrument",
        action="store",
        default="",
        help="instrument to be used with MIDI",
    )

    parser.add_argument(
        "-p",
        "--padding",
        type=int,
        default=0,
        help="specify the spacing or padding between lines, defaults to 3",
    )

    parser.add_argument(
        "-M",
        "--metronome",
        action="store_true",
        default=False,
        help="Whether to enable metronome in the mp3 file",
    )

    parser.add_argument(
        "-g",
        "--google-drive",
        action="store_true",
        default=False,
        help="Use if the input_file is a Google Drive ID",
    )

    # Add positional arguments
    parser.add_argument(
        "input_file", help="input file name or Google Drive file ID (if -g is enabled)"
    )
    parser.add_argument(
        "output_file", nargs="?", default="", help="output file name (optional)"
    )

    args = parser.parse_args()

    global bar_number_every, midiInstrument, padding

    bar_number_every = args.bar_number_every

    if args.padding:
        padding = args.padding

    if args.instrument:
        midiInstrument = args.instrument
    elif args.metronome:
        midiInstrument = "choir aahs"
    else:
        midiInstrument = "flute"

    # Parse options from command line
    return args


def get_title_from_text(input_text):
    """
    Extracts the title from a string of text that contains a line with 'title='.

    Args:
        input_text (str): The input text to search for the title.

    Returns:
        str or None: The extracted title as a string, or None if no title is found.
    """
    # Find the line containing 'title=' and extract <title>
    title_line = next(
        (line for line in input_text.split("\n") if "title=" in line), None
    )
    if title_line:
        title = title_line.split("=")[1].strip()  # Remove leading/trailing whitespaces
        title = title.replace(" ", "_")  # Replace spaces with underscores
        return title
    return None  # Return None if no title is found


def set_output_file(args, input_text):
    """
    Sets the output file name based on the input arguments and text.

    If the output file name is not specified in the input arguments, the function
    attempts to extract the title from the input text and use it as the output file
    name. If a title cannot be extracted, the default output file name 'song.ly' is
    used.

    Args:
        args: The input arguments.
        input_text: The input text.

    Returns:
        The updated input arguments with the output file name set.
    """
    if not args.output_file:
        title = get_title_from_text(input_text)
        if title:
            args.title = title
            args.output_file = f"{title}.ly"  # Set output file name
        else:
            args.title = "song"
            args.output_file = "song.ly"  # Default output file name
    return args


def convert_midi_to_mp3(base_name, with_metronome, normalize=True):
    """
    Converts a MIDI file to an MP3 file using either 'mscore', 'musescore', or 'timidity' with 'lame'.
    If 'with_metronome' is True, uses either 'mscore' or 'musescore' to include a metronome in the output.
    Otherwise, uses 'timidity' with 'lame' to convert the MIDI file to MP3.
    Optionally normalizes the volume of the output file.

    Args:
        base_name (str): The base name of the MIDI file (without the '.midi' extension).
        with_metronome (bool): Whether to include a metronome in the output.
        normalize (bool): Whether to normalize the volume of the output MP3.

    Returns:
        None
    """

    command = None

    if with_metronome and shutil.which("mscore"):
        command = f"mscore -o {base_name}.mp3 {base_name}.midi"
    elif with_metronome and shutil.which("musescore"):
        command = f"musescore -o {base_name}.mp3 {base_name}.midi"
    else:
        command = f"timidity {base_name}.midi -Ow -o - | lame - -b 192 {base_name}.mp3"

    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()

    if error:
        print(f"Error: {error}")
    else:
        print(f"Output: {output}")

    if normalize:
        normalize_volume(f"{base_name}.mp3")


def normalize_volume(filename, inplace=True):
    """
    Normalizes the volume of an MP3 file.

    This function first tries to use the pydub library for normalization.
    If pydub is not available, it falls back to using ffmpeg. It calculates
    the change in dBFS needed to normalize the volume and applies this gain
    to the audio.

    Args:
        filename (str): The path to the MP3 file to be normalized.
        inplace (bool): If True, the original file is overwritten.
                        Otherwise, a new file is created.

    Returns:
        None: The function modifies the file directly and does not return anything.
    """
    try:
        # Try to import pydub and use it for normalization
        from pydub import AudioSegment

        audio = AudioSegment.from_file(filename, format="mp3")
        change_in_dBFS = -audio.max_dBFS
        normalized_audio = audio.apply_gain(change_in_dBFS)

        if not inplace:
            filename = "normalized_" + filename
        normalized_audio.export(filename, format="mp3")

    except ImportError:
        # pydub is not available, use ffmpeg instead
        cmd_detect_volume = f"ffmpeg -i {filename} -af volumedetect -f null /dev/null"
        result = subprocess.run(
            cmd_detect_volume, capture_output=True, text=True, shell=True
        )
        max_volume_line = [
            line for line in result.stderr.split("\n") if "max_volume" in line
        ]
        if max_volume_line:
            max_volume = max_volume_line[0].split(":")[1].strip().replace(" dB", "")
            volume_adjustment = str(-float(max_volume))

            # Create a unique temporary file
            with tempfile.NamedTemporaryFile(delete=True, suffix=".mp3") as temp_file:
                temp_filename = temp_file.name

            cmd_normalize_volume = (
                f"ffmpeg -i {filename} -af volume={volume_adjustment}dB {temp_filename}"
            )
            subprocess.run(cmd_normalize_volume, shell=True)

            # Move the temp file to overwrite the original file if inplace is True
            if inplace:
                shutil.move(temp_filename, filename)


def main():
    """
    Main function that processes input data and writes output to a file.
    """
    args = parse_arguments()

    if args.html or args.markdown:
        return write_docs()

    # Check whether to read file from google drive or local directory
    if args.google_drive:
        input_text = download_file_from_google_drive(args.input_file)
        inDat = get_input(input_text, True)
        args = set_output_file(args, input_text)
    else:
        inDat = get_input(args.input_file)

    out = process_input(inDat, args.staff_only or args.with_staff)
    if not args.staff_only:
        out = reformat_key_time_signatures(out, args.with_staff)

    if args.staff_only:
        out = filter_out_jianpu(out)

    if re.search(r"春\s*节\s*序\s*曲", out):
        print('WARNING: Fixing "春节序曲".')
        out = workaround_text(out)

    write_output(out, args.output_file, args.input_file)
    if args.google_drive:
        convert_midi_to_mp3(args.title, args.metronome)


def workaround_text(original_text):
    # Text to be replaced
    old_text = """
    #:line (#:bold "1")
    #:line (#:bold "3")
"""

    # New text to be inserted
    new_text = """
    #:line (
      #:combine
        (#:bold "1")
        (#:translate (cons 0.25 1.8) #:bold ".")
    )
    #:vspace 0.2
    #:line (#:bold "3")
"""

    # Replace the old text with the new text
    modified_text = original_text.replace(old_text, new_text)

    modified_text = modified_text.replace("< c' e'' >", "< c'' e'' >")
    return modified_text


if __name__ == "__main__":
    main()
