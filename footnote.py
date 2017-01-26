import config
import unittest

import re
from parse import parseStandaloneTagBlock, parseTagAttributes
from fpgen import userOptions
from msgs import fatal, cprint, dprint

# If more than 6 in a chapter, it will start using numbers
# This list comes from "Note (typography)" on wikipedia.
footnoteMarkers = [
  "*", "†", "‡", "§", "‖", "¶",
]

footnoteMarkersText = [
  "star", "dagger", "doubledagger", "section", "parallelto", "pilcrow",
]

# This method both relocates the <footnote> tags, and also normalizes
# both <fn> and <footnote> to have both id= and target= attributes;
# handing autoincrement (id='#').  Autoincrement needs to be handled here,
# since when we reset we need to create special unique id tags(target),
# since the display value (id) is no longer unique.
#
# Note this method is device-independent.
# The tags are parsed again below in footnotesToHtml (both fn and footnote),
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
  mode = config.uopt.getOptEnum("footnote-location", options, none)

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
    target = None
    if id == '#':
      nonlocal footnotec
      id = str(footnotec)
      if mode == asterisk and footnotec <= len(footnoteMarkers):
        displayid = footnoteMarkers[footnotec-1]
      else:
        displayid = "[" + id + "]"
      footnotec += 1
    else:
      if id in footnoteMarkers:
        i = footnoteMarkers.index(id)
        displayid = id  # Don't add the square brackets
        target = footnoteMarkersText[i]
        if not reset:
          fatal("Use of explicit footnote symbols requires footnote-location to be set to either asterisk or heading-reset: " + str(opts))
      else:
        displayid = "[" + id + "]"
    if target == None:
      target = id
    if reset:
      target += "_" + str(footnoteChapter)
    opts = "id='" + displayid + "' target='" + target + "'"

    # Handle fn tags inside footnotes!
    relocateFootnotes(block)

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
      target = None
      if id == '#':
        id = str(fnc)
        if mode == asterisk and fnc <= len(footnoteMarkers):
          displayid = footnoteMarkers[fnc-1]
        else:
          displayid = "[" + id + "]"
        fnc += 1
      else:
        if id in footnoteMarkers:
          i = footnoteMarkers.index(id)
          displayid = id  # Don't add the square brackets
          target = footnoteMarkersText[i]
        else:
          displayid = "[" + id + "]"
      if target == None:
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

def footnotesToHtml(wb):

  matchFN = re.compile("<fn\s+(.*?)/?>")
  footnotes = {}

  # footnote marks in text
  i = 0
  while i < len(wb):
    off = 0
    line = wb[i]
    while True:
      m = matchFN.search(line, off)
      if not m:
        break
      opts = m.group(1)
      args = parseTagAttributes("fn", opts, [ "id", "target" ])
      fmid = args["id"]
      if not "target" in args:
        fatal("Missing internal target in fn: " + line)
      target = args["target"]
      dprint(1, "id: " + fmid + ", target: " + target)
      if fmid in footnotes and footnotes[fmid] == target:
        cprint("warning: footnote id <fn id='" + fmid + "'> occurs multiple times.  <footnote> link will be to the first.")
        repl = "<a href='#f{0}' style='text-decoration:none'><sup><span style='font-size:0.9em'>{1}</span></sup></a>".format(target, fmid)
      else:
        footnotes[fmid] = target
        repl = "<a id='r{0}'/><a href='#f{0}' style='text-decoration:none'><sup><span style='font-size:0.9em'>{1}</span></sup></a>".format(target, fmid)
      l = line[0:m.start(0)] + repl
      off = len(l)    # Next loop
      line = l + line[m.end(0):]
    wb[i] = line
    i += 1

  # footnote targets and text
  i = 0
  while i < len(wb):
    m = re.match("<footnote\s+(.*?)>", wb[i])
    if m:
      opts = m.group(1)
      args = parseTagAttributes("footnote", opts, [ "id", "target" ])
      fnid = args["id"]
      target = args["target"]
      wb[i] = "<div class='footnote-id' id='f{0}'><a href='#r{0}'>{1}</a></div>".format(target, fnid)
      while not re.match("<\/footnote>", wb[i]):
        i += 1
      wb[i] = "</div> <!-- footnote end -->"
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

  def test_footnote_none_fn_inside_footnote(self):

    input = [
      "l1",
      "w1<fn id='1'> w2",
      "w3",
      "<footnote id='1'>",
      "foot<fn id='1-1'> inside foot",
      "</footnote>",
      "<footnote id='1-1'>",
      "interior footnote",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot<fn id='[1-1]' target='1-1'> inside foot",
      "</footnote>",
      "<footnote id='[1-1]' target='1-1'>",
      "interior footnote",
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

  def test_footnote_asterisk_cross_gen(self):
    config.uopt.addopt("footnote-location", "asterisk")
    # Broke in 4.42d, fixed again in 4.43a
    # Does not really test correctly, it is footnoteToHtml that
    # we want to test.  See next test case
    input = [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
      "<genfootnotes>", # force new chapter
      "second blah<fn id='#'>",
      "<footnote id='#'>",
      "second fn",
      "</footnote>",
    ]
    # Note targets are id, underscore, chapter
    result = [
      "blah<fn id='*' target='1_1'>",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_1'>",
      "fn",
      "</footnote>",
      "",
      "second blah<fn id='*' target='1_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_2'>",
      "second fn",
      "</footnote>",
      "",
    ]
    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnoteToHtml_asterisk_cross_gen(self):
    config.uopt.addopt("footnote-location", "asterisk")
    # Broke in 4.42d, fixed again in 4.43a
    # Note targets are id, underscore, chapter
    input = [
      "blah<fn id='*' target='1_1'>",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_1'>",
      "fn",
      "</footnote>",
      "",
      "second blah<fn id='*' target='1_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='1_2'>",
      "second fn",
      "</footnote>",
      "",
    ]
    result = [
      "blah<a id='r1_1'/><a href='#f1_1' style='text-decoration:none'><sup><span style='font-size:0.9em'>*</span></sup></a>",
      "<hr rend='footnotemark'>",
      "<div id='f1_1'><a href='#r1_1'>*</a></div>",
      'fn',
      '</div> <!-- footnote end -->',
      '',
      "second blah<a id='r1_2'/><a href='#f1_2' style='text-decoration:none'><sup><span style='font-size:0.9em'>*</span></sup></a>",
      "<hr rend='footnotemark'>",
      "<div id='f1_2'><a href='#r1_2'>*</a></div>",
      'second fn',
      '</div> <!-- footnote end -->',
      '',
    ]
    footnotesToHtml(input)
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

  def test_footnote_asterisk(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
        "l1",
        "w1<fn id='*'> w2",
        "l3",
        "<footnote id='*'>",
        "footnote",
        "</footnote>"
    ]
    result = [
      'l1',
      "w1<fn id='*' target='star_1'> w2",
      'l3',
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='star_1'>",
      'footnote',
      '</footnote>',
      "",
    ]

    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  # two starred footnotes separated by footnote dump
  # should point at their two separate footnotes
  def test_footnote_asterisk_two_different(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
        "l1",
        "w1<fn id='*'> w2",
        "l3",
        "<footnote id='*'>",
        "footnote",
        "</footnote>",
        "<genfootnotes>",
        "l1a",
        "w1a<fn id='*'> w2a",
        "l3a",
        "<footnote id='*'>",
        "footnotea",
        "</footnote>",
    ]
    result = [
      'l1',
      "w1<fn id='*' target='star_1'> w2",
      'l3',
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='star_1'>",
      'footnote',
      '</footnote>',
      '',
      'l1a',
      "w1a<fn id='*' target='star_2'> w2a",
      'l3a',
      "<hr rend='footnotemark'>",
      "<footnote id='*' target='star_2'>",
      'footnotea',
      '</footnote>',
      '',
    ]

    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_section(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
        "l1",
        "w1<fn id='§'> w2",
        "l3",
        "<footnote id='§'>",
        "footnote",
        "</footnote>"
    ]
    result = [
      'l1',
      "w1<fn id='§' target='section_1'> w2",
      'l3',
      "<hr rend='footnotemark'>",
      "<footnote id='§' target='section_1'>",
      'footnote',
      '</footnote>',
      '',
    ]

    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_section_two_forward(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
        "l1",
        "w1<fn id='§'> w2",
        "l3",
        "w3<fn id='§'> w4",
        "l5",
        "<footnote id='§'>",
        "footnote",
        "</footnote>"
    ]
    result = [
      'l1',
      "w1<fn id='§' target='section_1'> w2",
      'l3',
      "w3<fn id='§' target='section_1'> w4",
      'l5',
      "<hr rend='footnotemark'>",
      "<footnote id='§' target='section_1'>",
      'footnote',
      '</footnote>',
      "",
    ]

    relocateFootnotes(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_section_two_forward_Html(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    input = [
      'l1',
      "w1<fn id='§' target='section_1'> w2",
      'l3',
      "w3<fn id='§' target='section_1'> w4",
      'l5',
      "<hr rend='footnotemark'>",
      "<footnote id='§' target='section_1'>",
      'footnote',
      '</footnote>',
      "",
    ]
    result = [
      'l1',
      "w1<a id='rsection_1'/><a href='#fsection_1' style='text-decoration:none'><sup><span style='font-size:0.9em'>\xa7</span></sup></a> w2",
      'l3',
      "w3<a href='#fsection_1' style='text-decoration:none'><sup><span style='font-size:0.9em'>\xa7</span></sup></a> w4",
      'l5',
      "<hr rend='footnotemark'>",
      "<div id='fsection_1'><a href='#rsection_1'>\xa7</a></div>",
      'footnote',
      '</div> <!-- footnote end -->',
      '',
    ]

    # TODO: Warning that id is twice, <footnote> link to the first
    footnotesToHtml(input)
    self.assertSequenceEqual(input, result)

  def test_footnote_no_id(self):
    input = [ "<footnote xid='x'>", "</footnote>" ]
    with self.assertRaises(SystemExit) as cm:
      relocateFootnotes(input)
    self.assertEqual(cm.exception.code, 1)

  def test_footnote_no_id_fn(self):
    input = [ "text<fn iid='1'>" ]
    with self.assertRaises(SystemExit) as cm:
      relocateFootnotes(input)
    self.assertEqual(cm.exception.code, 1)

  def test_footnote_bad_option(self):
    input = [ "text<fn id='1'>" ]
    config.uopt.addopt("footnote-location", "headings")
    with self.assertRaises(SystemExit) as cm:
      relocateFootnotes(input)
    self.assertEqual(cm.exception.code, 1)
