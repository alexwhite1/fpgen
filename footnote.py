import config
import unittest

import re
from parse import parseStandaloneTagBlock, parseTagAttributes
from fpgen import userOptions

# If more than 6 in a chapter, it will start using numbers
# This list comes from "Note (typography)" on wikipedia.
footnoteMarkers = [
  "*", "†", "‡", "§", "‖", "¶",
]

# This method both relocates the <footnote> tags, and also normalizes
# both <fn> and <footnote> to have both id= and target= attributes;
# handing autoincrement (id='#').  Autoincrement needs to be handled here,
# since when we reset we need to create special unique id tags(target),
# since the display value (id) is no longer unique.
#
# Note this method is device-independent.
# The tags are parsed again in HTML.doFootnotes (both fn and footnote),
# (and once again in mediaTweak, or at least the generated html is!)
# and Text.preProcess(fn), and Text.rewrap(footnote)
#
# Note that the footnotes have already been normalized to the format
#    <footnote>\ntext\n</footnote>
# in loadFile
#
# This method is unittested in testfootnote.py
def relocateFootnotes(block):
  #self.dprint(1, "relocate footnotes")

  none = 1
  heading = 2
  headingReset = 3
  marker = 4
  asterisk = 5
  options = {
      'none':none,
      'heading':heading, 'heading-reset':headingReset,
      'marker':marker,
      'asterisk':asterisk,
  }
  tagValue = config.uopt.getopt("footnote-location")
  if tagValue == '':
    mode = none
  elif tagValue in options:
    mode = options[tagValue]
  else:
    fatal("footnote-location option " + tagValue + " is not legal.  Valid values are: none, heading, heading-reset, marker.")

  notes = []
  fnc = 1
  footnotec = 1
  footnoteChapter = 1
  reset = (mode == headingReset or mode == asterisk)
  emitAtHeading = (mode == heading or reset)
  matchFN = re.compile("<fn\s+(.*?)/?>")

  # When we hit a footnote block, accumulate it, and clear it from
  # the current text.
  # Handle auto-incrementing footnote ids
  def footnoteRelocate(opts, block):

    opts = opts.strip()
    # Parse and recreate the footnote tag, to handle autonumbering footnotes
    args = parseTagAttributes("footnote", opts, [ "id" ])
    if not "id" in args:
      fatal("<footnote> does not have id attribute: " + opts)
    id = args["id"]
    if id == '#':
      nonlocal footnotec
      id = str(footnotec)
      if mode == asterisk and footnotec <= len(footnoteMarkers):
        displayid = footnoteMarkers[footnotec-1]
      else:
        displayid = "[" + id + "]"
      footnotec += 1
    else:
      displayid = "[" + id + "]"
    target = id
    if reset:
      target += "_" + str(footnoteChapter)
    opts = "id='" + displayid + "' target='" + target + "'"

    # Recreate the block
    block.insert(0, "<footnote " + opts + ">")
    block.append("</footnote>")

    # If we aren't supposed to move footnotes, do nothing
    if mode == none:
      return block

    # Otherwise accumulate them for emitting elsewhere
    nonlocal notes
    notes.append(block)

    # Clear the current location of the footnote
    return []

  # Method called on every line.
  def processLine(i, line):
    nonlocal fnc, footnotec

    # Process <fn> tags, fixing id='#' with an appropriate number
    # Loop, can be multiple on a line.
    off = 0
    while True:
      m = matchFN.search(line, off)
      if not m:
        break
      opts = m.group(1)
      args = parseTagAttributes("fn", opts, [ "id" ])
      if not "id" in args:
        fatal("<fn> does not have id attribute: " + line)
      id = args["id"]
      if id == '#':
        id = str(fnc)
        if mode == asterisk and fnc <= len(footnoteMarkers):
          displayid = footnoteMarkers[fnc-1]
        else:
          displayid = "[" + id + "]"
        fnc += 1
      else:
        displayid = "[" + id + "]"
      target = id
      if reset:
        nonlocal footnoteChapter
        target += "_" + str(footnoteChapter)
      opts = "id='" + displayid + "' target='" + target + "'"
      l = line[:m.start(0)] + "<fn " + opts + ">"
      off = len(l)    # Start next loop after end of this
      line = l + line[m.end(0):]

    # Are we going to emit it here?
    # Always emit if we hit a genfootnotes,
    # emit when we hit a heading, but only in heading mode.
    emit = False
    if line.startswith("<genfootnotes>"):
      emit = True
      line = None       # Remove the line, we don't want it!
    elif emitAtHeading:
      if line.startswith("<heading"):
        emit = True

    # If there weren't any, forget it, nothing to do
    if len(notes) == 0:
      emit = False

    if not emit:
      if line == None:
        return []
      else:
        return [ line ]

    all = formatNotes(line)

    # If our mode is reset, then whenever we emit, we reset our counters
    if reset:
      fnc = 1
      footnotec = 1
      footnoteChapter += 1

    return all

  def formatNotes(line):
    nonlocal notes

    # Emit a footnote mark, then all the footnotes, then a blank line,
    # then this current line which triggered us
    all = [ "<hr rend='footnotemark'>" ]
    for block in notes:
      all.extend(block)
      all.append("") # Blank line between footnotes and after
    if line != None:
      all.append(line)

    # We emitted, so clear the current footnotes
    notes = []

    return all

  parseStandaloneTagBlock(block, "footnote", footnoteRelocate,
      lineFunction = processLine)

  # Anything left when we get to the end of the file? i.e. last chapter?
  if len(notes) != 0:
    block += formatNotes(None)

#
# Reformat footnotes to standard form, i.e.
# <footnote>\ntext\n</footnote>
#
def reformat(block):
  reOneLine = re.compile("(<footnote\s+id=[\"'].*?[\"']>)(.+?)(<\/footnote>)")
  reStart = re.compile("(<footnote\s+id=[\"'].*?[\"']>)(.+?)$")
  reStartWOText = re.compile("<footnote\s+id=[\"'].*?[\"']>$")
  reEnd = re.compile("^(.+?)(<\/footnote>)")

  i = 0
  while i < len(block):

    # all on one line
    m = reOneLine.match(block[i])
    if m:
      mg1 = m.group(1).strip()
      mg2 = m.group(2).strip()
      mg3 = m.group(3).strip()
      block[i:i+1] = [mg1, mg2, mg3]
      i += 2

    # starts but doesn't end on this line
    m = reStart.match(block[i])
    if m:
      mg1 = m.group(1).strip()
      mg2 = m.group(2).strip()
      block[i:i+1] = [mg1, mg2]
      i += 1

    # starts without text on this line
    m = reStartWOText.match(block[i])
    if m:
      i += 1

    # ends but didn't start on this line
    m = reEnd.match(block[i])
    if m:
      block[i:i+1] = [m.group(1).strip(), m.group(2).strip()]
      i += 1

    i += 1

class TestFootnote(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    config.uopt = userOptions()

  input1 = [
    "l1",
    "w1<fn id='1'> w2",
    "w3",
    "<footnote id='1'>",
    "foot",
    "</footnote>",
    "",
    "More text",
    "",
    "<heading level='1'>h1</heading>",
    "text",
  ]

  input2 = [
    "l1",
    "w1<fn id='#'> w2",
    "w3",
    "<footnote id='#'>",
    "foot",
    "</footnote>",
    "",
    "More text",
    "",
    "<heading level='1'>h1</heading>",
    "text",
  ]

  def test_footnote_none_auto(self):
    input = self.input1.copy()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_none_auto2(self):
    input = self.input2.copy()
    input += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[2]' target='2'>",
      "<footnote id='[2]' target='2'>",
      "fn",
      "</footnote>",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_none_auto_same_line(self):
    input = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1'>, more words, <fn id='[2]' target='2'>, another <fn id='[3]' target='3'>",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_reset_auto_same_line(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1_1'>, more words, <fn id='[2]' target='2_1'>, another <fn id='[3]' target='3_1'>",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_reset_auto_same_line_and_reset(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
      "<footnote id='1'>",
      "fn",
      "</footnote>",
      "<genfootnotes>",
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1_1'>, more words, <fn id='[2]' target='2_1'>, another <fn id='[3]' target='3_1'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_1'>",
      "fn",
      "</footnote>",
      "",
      "blah<fn id='[1]' target='1_2'>, more words, <fn id='[2]' target='2_2'>, another <fn id='[3]' target='3_2'>",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_none_unchanged(self):
    input = self.input1.copy()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_heading(self):
    input = self.input1.copy()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    config.uopt.addopt("footnote-location", "heading")
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  # Emit early if marker hit
  def test_footnote_heading_marker(self):
    input = self.input1.copy()
    input[-2] = "<genfootnotes>"
    input += [ "l2", "<heading level='1'>h1</heading>", "more text" ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "text",
      "l2",
      "<heading level='1'>h1</heading>",
      "more text",
    ]
    config.uopt.addopt("footnote-location", "heading")
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_heading_auto2(self):
    config.uopt.addopt("footnote-location", "heading")
    input = self.input2.copy()
    input += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[2]' target='2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[2]' target='2'>",
      "fn",
      "</footnote>",
      "",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_heading_reset_auto2(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = self.input2.copy()
    input += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1_1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[1]' target='1_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_2'>",
      "fn",
      "</footnote>",
      "",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_heading_reset_asterisk2(self):
    config.uopt.addopt("footnote-location", "asterisk")
    input = self.input2.copy()
    input += [
      "blah<fn id='#'> bar<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
      "<footnote id='#'>",
      "fn2",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='*' target='1_1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='*' target='1_2'> bar<fn id='†' target='2_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_2'>",
      "fn",
      "</footnote>",
      "",
      "<footnote id='†' target='2_2'>",
      "fn2",
      "</footnote>",
      "",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)


  def test_footnote_heading_reset_manual2(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
      "l1",
      "w1<fn id='1'> w2",
      "w3",
      "<footnote id='1'>",
      "foot",
      "</footnote>",
      "<footnote id='2'>",
      "foot2",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='1'>",
      "<footnote id='1'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1_1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_1'>",
      "foot",
      "</footnote>",
      "",
      "<footnote id='[2]' target='2_1'>",
      "foot2",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[1]' target='1_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_2'>",
      "fn",
      "</footnote>",
      "",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)


  # No <heading> tag? Emit at end of file
  def test_footnote_heading_end(self):
    input = self.input1.copy()
    del input[-2]     # remove heading
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "text",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
    ]
    config.uopt.addopt("footnote-location", "heading")
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  # Emit at marker, not heading
  def test_footnote_marker(self):
    input = self.input1.copy()
    input += [
      "<genfootnotes>",
      "more text",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",       # blank line after footnotes
      "more text",
    ]
    config.uopt.addopt("footnote-location", "marker")
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)
