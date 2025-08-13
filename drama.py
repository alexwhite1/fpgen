#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re, sys, string, os, shutil
import platform
import unittest
from unittest.mock import MagicMock, Mock, call

import config
from fpgen import parseStandaloneTagBlock, wrap2
from parse import parseTagAttributes, parseOption1
from config import FORMATTED_PREFIX
from msgs import fatal, uprint, cprint, dprint

class Style:
  indent = 1
  hang = 2
  block = 3
  off = 4
  centre = 5
  inline = 6
  left = 7

  words = {
      indent:'indent', hang:'hang', block:'block', off:'off',
      centre:'center', inline:'inline', left:'left',
  }

  def parseOption(tag, valid, default):
    tagValue = config.uopt.getopt(tag)
    if tagValue == '':
      return default
    for value in valid:
      if tagValue == Style.words[value]:
        return value
    fatal("Option " + tag + ": Illegal value: " + tagValue)

class Drama:

  def __init__(self, wb):
    self.wb = wb
    self.speechIndent = Style.parseOption('drama-speech-style',
      [Style.indent, Style.hang, Style.block],
      Style.hang)
    self.speechContinue = Style.parseOption('drama-speech-cont',
      [Style.indent, Style.block],
      Style.block)
    self.stageIndent = Style.parseOption('drama-stage-style',
      [Style.indent, Style.hang, Style.block, Style.off],
      Style.indent)
    self.speakerStyle = Style.parseOption('drama-speaker-style',
      [Style.hang, Style.centre, Style.inline, Style.left],
      Style.inline)
    self.verseAlignLast = False

  # Allow for anything needed at the start of drama
  def startSection(self):
    return []

  def doDrama(self):
    parseStandaloneTagBlock(self.wb, "drama", self.oneDramaBlock)

  # A <drama>...</drama> block has been found.
  # All the lines between are in the drama arg, a sequence of lines
  def oneDramaBlock(self, openTag, drama):
    args = parseTagAttributes("drama", openTag, [ 'type', 'rend' ])

    if 'type' in args:
      blockType = args['type']
      if blockType == 'verse':
        verse = True
      elif blockType == 'prose':
        verse = False
      else:
        fatal("Drama tag: Illegal type value: " + blockType)
    else:
      verse = False

    if 'rend' in args:
      rendArgs = parseOption1(args['rend'])
      if 'align-last' in rendArgs:
        align = rendArgs['align-last']
        if align == 'true':
          self.verseAlignLast = True
        elif align == 'false':
          self.verseAlignLast = False
        else:
          fatal("align-last rend argument must be true or false: " + openTag)

    # Local variables
    inStageDirection = False
    speaker = None
    line = ''
    block = []
    alignRight = False
    regexSpeaker = re.compile("<sp>(.*)</sp>")

    self.emitCss();
    result = self.startSection()

    drama.append('')    # Make sure we always end in blank line to flush
    for lineNo, line in enumerate(drama):

      if line == '<verse>':
        verse = True
        continue
      elif line == '<prose>':
        verse = False
        continue

      # Note an empty last line has a formatted prefix
      thisEmpty = line == ''

      if thisEmpty:
        if len(block) != 0:
          if inStageDirection:
            block = self.stageDirection(block, alignRight)
          else:
            if speaker == None:
              # No explicit speaker defined.  See if we can make implicit
              # speaker recognition.
              block[0], speaker = self.extractSpeaker(block[0])
              if speaker != None:
                # Generate left/center speakers, if we did an implicit
                # speaker recognition
                result.extend(self.speakerStandalone(speaker))
            isContinue = speaker == None
            block = self.speech(block, verse, speaker, isContinue)
            # Note speaker may have a blank line after it
            speaker = None
        result.extend(block)

        # Reset for next block
        block = []
        alignRight = False
        inStageDirection = False
        continue

      if line.startswith("<right>"):
        line = line[7:]
        alignRight = True

      # See if there is an explicitly tagged speaker
      m = regexSpeaker.search(line)
      if m:
        speaker = m.group(1)
        line = regexSpeaker.sub("", line)

        # Generate speaker for left and center.
        # Note that hang and lineline are generated in speech,
        # since they are part of the generated speech
        result.extend(self.speakerStandalone(speaker))

        # <sp>speak</sp> line
        # exactly one space is normal and removed; more than one space is
        # preserved and used for alignment.
        if len(line) > 1 and line[0] == ' ' and line[1] != ' ':
          line = line[1:]
#        if line != '':
#          fatal("<sp>...</sp> must be alone on the line: " + self.wb[lineNo-1])

      # Is this line a stage direction?
      # Either explicit with tag; or implicity with common convention of [
      if self.stageIndent != Style.off and \
        len(block) == 0 and \
        (line.startswith("<stage>") or \
          (re.match(r" *\[", line) and not re.search("\] *[^ ]", line))):
        if inStageDirection:
          fatal("Already in stage direction at " + line)
        inStageDirection = True
        if line.startswith("<stage>"):
          line = line[7:]
        else:
          line = re.sub("^  *", "", line)

      if line != '':
        block.append(line)

    return result

  # Even in verse, stage directions are stage directions, and
  # can't have per-line paragraphs, since there are cross-line
  # font changes
  # Returns a sequence, where each entry is either a line of verse,
  # or a sequence of one or more lines of stage direction
  def decomposeVerse(self, block):
    result = []
    inStage = False
    for i,line in enumerate(block):

      # Line starts stage direction
      if not inStage and line.startswith("["):
        # If line ends the stage direction, only treat it as a stage
        # direction if there is nothing after it
        if line.find('] ') < 0:
          inStage = True
          stage = []

      # Put the line in whichever batch
      if inStage:
        stage.append(line)
      else:
        result.append(line)

      # Closing of the stage direction
      if inStage and line.find(']') >= 0:
        inStage = False
        result.append(stage)

    if inStage:
      fatal("No end to stage direction embedded in verse: " + stage[0])
    return result

  """
  def decorateInlineSpeaker(self, sp):
    if not re.search(": *", sp):
      return sp + ": "
    else:
      return sp
  """

#### End of class Drama

class DramaHTML(Drama):

  def __init__(self, wb, css):
    Drama.__init__(self, wb)
    self.css = css
    self.space = '◻' # ensp; or ⋀ for nbsp?
    self.lastLine = None
    self.lastLineHadIndent = False

  def extractSpeaker(self, line):
    m = re.match("⩤sc⩥(.*)⩤/sc⩥", line)
    if m:
      speaker = m.group(1)
      return line[m.end():], speaker
    return line, None

  def startSection(self):
    #
    # This div is needed to stop the margin collapse between any quote
    # before the start of the drama; and leading spaces above our first
    # paragraph.  Not that we really care about the collapse, but if we
    # are using hanging speakers, then that div does not collapse, but
    # ends up at a different level than the speech.
    #
    # Note the html comment stops HTML Tidy from warning about empty div
    return [ FORMATTED_PREFIX + "<div class='dramastart'><!----></div>", '' ]

  # Handle speaker when it is part of a diversion: all but inline
  def speakerStandalone(self, speaker):
    result = []
    if speaker != None and self.speakerStyle != Style.inline:
      result.append("<div class='speaker'>" + speaker + "</div>")
    return result

  def speech(self, block, verse, speaker, isContinue):
    result = []

    for i,line in enumerate(block):
      # Leading spaces; or spaces after the speaker's name colon
      # are preserved -- turn them into magic unicode character
      # which will later become &ensp;
      m = re.match(":?(  *)", line)
      if m:
        n = len(m.group(1))
        spaces = self.space * len(m.group(1)) 
        block[i] = line[0:m.start(1)] + spaces + line[m.end(1):]

    if verse:
      block = self.verseSpeech(block, isContinue, speaker)
    else:
      block = self.filledSpeech(block, isContinue, speaker)
    result.extend(block)

    # Whitespace to make it look pretty
    result.append('')

    return result

  def verseSpeech(self, block, isContinue, speaker):
    result = []
    block = self.decomposeVerse(block)
    for i,line in enumerate(block):

      # A sequence of lines which is an embedded stage direction
      if not isinstance(line, str):
          stage = line
          stage[0] = "<p class='stage-embed'>" + stage[0]
          stage[-1] = stage[-1] + "</p>"
          for j,line in enumerate(stage):
              result.append(FORMATTED_PREFIX + line)
          continue

      if i == 0:
        if isContinue:
          # first line of a speech which doesn't look like a speech, is
          # probably a speech interrupted by a direction
          cl = 'dramaline-cont'
        else:
          cl = 'speech'
      else:
        cl = 'dramaline'

      para = "<p class='{}'>".format(cl)

      # Inline speaker gets added to the start of the line now, we want it as part of
      # the line for alignment purposes
      if speaker != None and self.speakerStyle == Style.inline:
        speak = "<span class='speaker-inline'>{}</span>".format(speaker)
        line = speak + line

      # Alignment of a verse line with the end of the last emitted line
      if self.verseAlignLast and \
        self.lastLine != None and \
        re.search(self.space + self.space, line):
        if self.lastLineHadIndent:
          invis = "\n<span class='verse-align'>" + self.lastLine + "</span>"
        else:
          # Last line wasn't indented; since this is the first line of a paragraph,
          # need to reverse the indent of the current line, if there was one.
          invis = "\n<span class='verse-align-noindent'>" + self.lastLine + "</span>"

        # See if we have two non-breaking spaces.  The left of them needs to be
        # positioned absolutely, since it isn't relevant to the positioning of
        # the the line which we want aligned.
        # The right is the positioned after emitting the last line as invisible.
        m = re.search(self.space + self.space + "*", line)
        if m:
          p1 = line[:m.start()]
          p2 = line[m.end():]
          if p1 != '':
            # Absolute position the left (i.e. speaker, colon)
            p1 = "<span class='verse-align-inline'>" + p1 + "</span>"
          line = p1 + invis + p2

      # Save the last line of the block, for the first line of the next
      self.lastLine = line
      self.lastLineHadIndent = i==0 and not isContinue

      # Put the paragraph markers in, and we have our final line
      result.append(FORMATTED_PREFIX + para + line + "</p>")

      speaker = None

    return result

  def filledSpeech(self, block, isContinue, speaker):
    result = []
    for i,line in enumerate(block):
      if i == 0:
        if isContinue: # first line of a speech which doesn't look like a speech, is
          # probably a speech interrupted by a direction
          cl = 'speech-cont'
        else:
          cl = 'speech'
      else:
        cl = ''

      if cl != '':
        l = "<p class='" + cl + "'>"
        if speaker != None and self.speakerStyle == Style.inline and not isContinue:
          l += "<span class='speaker-inline'>" + speaker + "</span>"
        line = l + line
      result.append(FORMATTED_PREFIX + line)

    # terminate the paragraph
    n = len(result)
    result[n-1] = result[n-1] + "</p>"

    return result

  def stageDirection(self, block, alignRight):
    if alignRight:
      for i,l in enumerate(block):
        if i == 0:
          block[i] = FORMATTED_PREFIX + "<p class='stageright'>" + l
        else:
          block[i] = FORMATTED_PREFIX + l
    else:
      for i,l in enumerate(block):
        if i == 0:
          block[i] = FORMATTED_PREFIX + "<p class='stage'>" + l
        else:
          block[i] = FORMATTED_PREFIX + l

    # Terminate the paragraph
    n = len(block)
    block[n-1] = block[n-1] + "</p>"

    # Whitespace to make it look pretty
    block.append('')

    return block

  speechCSS = "[899] .{0} {{ margin-top: .2em; margin-bottom: 0; text-indent: {1}; padding-left: {2}; text-align: left; }}"
  stageCSS = "[899] .stage {{ margin-top: 0; margin-bottom: 0; text-indent: {0}; padding-left: {1}; margin-left: {2}; }}"
  stageStageCSS = "[899] .stage + .stage {{ margin-top: {} }}"
  stageembedCSS = "[899] .stage-embed {{ margin-top: 0; margin-bottom: 0; text-indent: 0; padding-left: {}; }}"
  dramalineCSS = "[899] .{} {{ margin-top: {}; margin-bottom: 0; text-indent: 0em; padding-left: {} }}"
  stagerightCSS = "[899] .stageright { margin-top: 0; margin-bottom: 0; text-align:right; }"
  speakerCSS = "[899] .speaker {{ margin-left: 0; margin-top: {}; font-variant: small-caps; {} {} }}"
  speakerInlineCSS = "[899] .speaker-inline { font-variant: small-caps; }"
  alignmentCSS = "[899] .verse-align { visibility:hidden; }"
  alignmentNoIndentCSS = "[899] .verse-align-noindent {{ visibility:hidden; margin-left:{}; }}"
  alignmentInlineCSS = "[899] .verse-align-inline { position:absolute; text-indent:0; }"

  # This avoids a problem with margin-collapse when in speaker hang mode
  startCSS = "[899] .dramastart { min-height: 1px; }"

  speakerWidth = "5em"

  def emitCss(self):
    if self.speechIndent == Style.indent:
      indent = "1.2em"
      padding = "0em"
    elif self.speechIndent == Style.hang:
      indent = "-1.2em"
      padding = "2.4em"
    elif self.speechIndent == Style.block:
      indent = "0em"
      padding = "1.2em"

    if self.speakerStyle == Style.hang:
      hangLeft = "float:left; clear:both;"
      padding = self.speakerWidth
      top = ".2em"
      stageMarginLeft = "0em"
    else:
      hangLeft = ''
      top = ".8em"
      stageMarginLeft = "3em"

    self.css.addcss(self.speechCSS.format("speech", indent, padding))
    self.css.addcss(self.speechCSS.format("speech-cont", "0em" if self.speechContinue == Style.block else indent, padding))
    self.css.addcss(self.dramalineCSS.format("dramaline", "0em", padding))
    self.css.addcss(self.dramalineCSS.format("dramaline-cont", ".8em", padding))
    self.css.addcss(self.stageembedCSS.format(padding))

    self.css.addcss(self.alignmentCSS)
    self.css.addcss(self.alignmentNoIndentCSS.format(indent[1:] if indent[0]=='-' else '-' + indent))
    self.css.addcss(self.alignmentInlineCSS)

    if self.stageIndent == Style.indent:
      indent = "1em"
      padding = "0em"
    elif self.stageIndent == Style.hang:
      indent = "-1em"
      padding = "2em"
    elif self.stageIndent == Style.block:
      indent = "0em"
      padding = "2em"
      if self.speakerStyle == Style.hang:
        padding = self.speakerWidth
    self.css.addcss(self.stageCSS.format(indent, padding, stageMarginLeft))
    self.css.addcss(self.stageStageCSS.format(".8em"))
    self.css.addcss(self.stagerightCSS)
    self.css.addcss(self.startCSS)

    if self.speakerStyle == Style.centre:
      speakerStyle = "text-align: center;"
    else:
      speakerStyle = ''
    self.css.addcss(self.speakerCSS.format(top, hangLeft, speakerStyle))
    self.css.addcss(self.speakerInlineCSS)

#### End of class DramaHTML

class DramaText(Drama):

  SPEAKER_HANG_WIDTH = 10

  def __init__(self, wb):
    Drama.__init__(self, wb)
    w = config.uopt.getopt("drama-speaker-hang-text-width")
    if w != '':
      try:
        self.SPEAKER_HANG_WIDTH = int(w)
      except ValueError:
        fatal("Invalid option for drama-speaker-hang-text-width: " + w)

  # Complications:
  # stage directions after the speaker before the colon
  #   TIPTREE (looking out):
  # speaker ends with a period (mixes up with MR. FOO:)
  #   ELMA.
  # Returns rest-of-line, speaker
  def extractSpeaker(self, line):
    nCap = 0
    off = 0
    for i in range(len(line)):
      c = line[i]
      if c == ' ':
        continue
      elif c == '(':      # start of inline stage direction
        off = i
        break
      elif c == ':':      # end of character name
        off = i
        break
      elif c == '.' or c == '-' or c == "'" or c == "’":      # Mr., Mrs.
        continue
      elif c.isupper():
        nCap += 1
      else:
        if nCap > 1:      # More than one leading cap
          # Back off to the last space
          while i > 0:
            if line[i] == ' ':
              off = i
              break
            i -= 1
          if i > 0:
            break
        return line, None
    if off > 0:
      return line[off:], line[:off]
    if nCap > 0:
      # All upper-case?
      return '', line
    else:
      return line, None

  def fill(self, block, indent, line0indent, leftmargin):
    # Fill the block in specified width
    # note: wrap2 uses line0indent on the first line,
    # and indent on all subsequent lines
    result = wrap2(" ".join(block), leftmargin, 0, indent, line0indent)
    for i,l in enumerate(result):
      dprint(2, ">" + l + "<")
    return result

  # Handle speaker when it is on its own line: either left or center
  def speakerStandalone(self, speaker):
    result = []
    if speaker != None and self.speakerStyle != Style.inline and self.speakerStyle != Style.hang:
      sp = speaker.upper()
      if self.speakerStyle == Style.centre:
        result.append(FORMATTED_PREFIX + (((config.LINE_WIDTH-len(sp))//2) * ' ') + sp)
      else: # self.speakerStyle == Style.left
        result.append(FORMATTED_PREFIX + sp)
    return result

  def speech(self, block, verse, speaker, isContinue):
    #cprint("Speech: " + block[0] + ", " + str(verse) + ", " + str(speaker) + ", " + str(isContinue));
    result = []

    if self.speechIndent == Style.indent:
      speech0Prefix = "  "
      speechPrefix = ""
      indent = 0
      line0indent = 2
    elif self.speechIndent == Style.hang:
      speech0Prefix = ""
      speechPrefix = "  "
      indent = 2
      line0indent = 0
    elif self.speechIndent == Style.block:
      speech0Prefix = "  "
      speechPrefix = "  "
      indent = 2
      line0indent = 2

    # Continuation block (i.e. no speaker);
    # Can be either block or indent; if block, simply make it the
    # same as the other lines
    if isContinue and self.speechContinue == Style.block:
      speech0Prefix = speechPrefix
      line0indent = indent

    if self.speakerStyle == Style.hang:
      leftmargin = self.SPEAKER_HANG_WIDTH

      # Hanging speakers with block don't need extra indents!
      if self.speechIndent == Style.block:
        speech0Prefix = ''
        speechPrefix = ''
        indent = 0
        line0indent = 0

    else:
      leftmargin = 0

    if speaker != None and self.speakerStyle == Style.inline:
      if len(speaker) > 0 and speaker[-1] != ' ' and len(block[0]) > 0 and block[0][0].isalpha():
        speaker += ' '
      block[0] = speaker + block[0]
    if not verse:
      block = self.fill(block, indent, line0indent, leftmargin)
    else:
      # Verse we have to do manually
      # Fill the internal stage directions!
      block = self.decomposeVerse(block)
      lm = ' ' * leftmargin
      temp = []
      for i,l in enumerate(block):
        if isinstance(l, str):
          if i == 0:
            temp.append(lm + speech0Prefix + block[i])
          else:
            temp.append(lm + speechPrefix + block[i])
        else:
          # An embedded stage direction to fill
          stage = self.fill(l, indent, indent, leftmargin)
          for j, l1 in enumerate(stage):
            temp.append(l1)
      block = temp

    # Hang style speaker: replace leading spaces on first line with speaker
    if self.speakerStyle == Style.hang and speaker != None:
      block[0] = speaker.upper() + block[0][len(speaker):]

    for i,l in enumerate(block):
      result.append(FORMATTED_PREFIX + l)
    result.append(FORMATTED_PREFIX)
    return result

  def stageDirection(self, block, alignRight):
    if alignRight:
      for i,l in enumerate(block):
        block[i] = FORMATTED_PREFIX + ' ' * (config.LINE_WIDTH - len(l)) + l
    else:
      if self.speakerStyle == Style.hang:
        offset = self.SPEAKER_HANG_WIDTH
      else:
        offset = 3
      indent = offset + 3
      if self.stageIndent == Style.indent:
        line0indent = indent
        lineNindent = offset
      elif self.stageIndent == Style.hang:
        stage0Prefix = ' ' * offset
        stagePrefix = ' ' * indent
        line0indent = offset
        lineNindent = indent
      elif self.stageIndent == Style.block:
        line0indent = offset
        lineNindent = offset
      block = self.fill(block, lineNindent, line0indent, 0)

      for i,l in enumerate(block):
        block[i] = FORMATTED_PREFIX + l
    block.append(FORMATTED_PREFIX)
    return block

  def emitCss(self):
    pass

#### End of class DramaText

class TestOneDramaBlockMethod(unittest.TestCase):
  def setUp(self):
    self.d = DramaHTML([], None)
    self.d.speech = MagicMock()
    self.d.stageDirection = MagicMock()
    self.d.extractSpeaker = Mock()
    self.d.extractSpeaker.side_effect = lambda line: (line, None)
    self.d.emitCss = MagicMock(name='emitCss')

  def test_drama_parse_1(self):
    self.d.oneDramaBlock("", [ "A simple speech" ])
    self.d.speech.assert_called_once_with(["A simple speech"], False, None, True)

  def test_drama_parse_1a(self):
    self.d.oneDramaBlock("", [ "l1", "l2" ])
    self.d.speech.assert_called_once_with(["l1", "l2"], False, None, True)

  def test_drama_parse_verse(self):
    self.d.oneDramaBlock("type='verse'", [ "l1", "l2" ])
    self.d.speech.assert_called_once_with(["l1", "l2"], True, None, True)

  def test_drama_parse_prose(self):
    self.d.oneDramaBlock("type='prose'", [ "l1", "l2" ])
    self.d.speech.assert_called_once_with(["l1", "l2"], False, None, True)

  def test_drama_parse_prose_verse(self):
    self.d.oneDramaBlock("type='prose'", [ "<verse>", "l1", "l2" ])
    self.d.speech.assert_called_once_with(["l1", "l2"], True, None, True)

  def test_drama_parse_verse_prose(self):
    self.d.oneDramaBlock("type='verse'", [ "<prose>", "l1", "l2" ])
    self.d.speech.assert_called_once_with(["l1", "l2"], False, None, True)

  def test_drama_parse_type_bad(self):
    with self.assertRaises(SystemExit) as cm:
      self.d.oneDramaBlock("type='xverse'", [ "<prose>", "l1", "l2" ])
    self.assertEqual(cm.exception.code, 1)

  def test_drama_parse_rend_bad(self):
    with self.assertRaises(SystemExit) as cm:
      self.d.oneDramaBlock("rend='align-last:maybe'", [ "<prose>", "l1", "l2" ])
    self.assertEqual(cm.exception.code, 1)

  def test_drama_parse_2(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )

  def test_drama_parse_2_verse(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "<verse>", "", "v1", "v2" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["v1", "v2"], True, None, True)
      ]
    )

  def test_drama_parse_stage(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "[stage1", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["[stage1"], False)

  def test_drama_parse_stage_inline(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "[stage1] text", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["[stage1] text"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )

  @unittest.expectedFailure
  def test_drama_parse_stage_in_stage(self):
    self.d.stageIndent = Style.left
    with self.assertRaises(SystemExit) as cm:
      self.d.oneDramaBlock("", [ "[stage1", "<stage>[stage2", "", "l3" ])
    self.assertEqual(cm.exception.code, 1)

  def test_drama_parse_stage_leading_spaces(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "    [stage1", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["[stage1"], False)

  def test_drama_parse_stage_right(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "<right>[stage1", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["[stage1"], True)

  def test_drama_parse_stage_right_2line(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "<right>", "[stage1", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["[stage1"], True)

  def test_drama_parse_explicit_stage(self):
    self.d.oneDramaBlock("", [ "l1", "l2", "", "<stage>stage1", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["stage1"], False)

  def test_drama_parse_explicit_stage_2line(self):
    self.d.oneDramaBlock("", [
      "l1", "l2", "", "<stage>", "stage1", "stage2", "", "l3"
    ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )
    self.d.stageDirection.assert_called_once_with(["stage1", "stage2"], False)

  def test_drama_parse_explicit_sp(self):
    self.d.oneDramaBlock("", [ "<sp>speaker</sp>l1", "l2", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, "speaker", False),
        call(["l3"], False, None, True)
      ]
    )

  def test_drama_parse_explicit_sp_own_line(self):
    self.d.oneDramaBlock("", [ "<sp>speaker</sp>", "l1", "l2", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, "speaker", False),
        call(["l3"], False, None, True)
      ]
    )

  def test_drama_parse_explicit_sp_blank_line(self):
    self.d.oneDramaBlock("", [ "<sp>speaker</sp>", "", "l1", "l2", "", "l3" ])
    self.assertEqual(
      self.d.speech.call_args_list,
      [
        call(["l1", "l2"], False, "speaker", False),
        call(["l3"], False, None, True)
      ]
    )

  def test_drama_parse_implicit_sp(self):
    # Don't want extractSpeaker mocked. Is there an easier way?
    d = DramaHTML([], None)
    d.speech = MagicMock()
    d.stageDirection = MagicMock()
    d.emitCss = MagicMock(name='emitCss')
    d.oneDramaBlock("", [ "⩤sc⩥speaker⩤/sc⩥: l1", "l2", "", "l3" ])
    self.assertEqual(
      d.speech.call_args_list,
      [
        call([": l1", "l2"], False, "speaker", False),
        call(["l3"], False, None, True)
      ]
    )

  def test_drama_parse_implicit_sp_calls_standalone(self):
    # Don't want extractSpeaker mocked. Is there an easier way?
    d = DramaHTML([], None)
    d.speech = MagicMock()
    d.stageDirection = MagicMock()
    d.emitCss = MagicMock(name='emitCss')
    d.speakerStandalone = MagicMock()
    d.oneDramaBlock("", [ "⩤sc⩥speaker⩤/sc⩥", "", "l1", "l2", "", "l3" ])
    self.assertEqual(
      d.speakerStandalone.call_args_list,
      [
        call("speaker"),
      ]
    );
    self.assertEqual(
      d.speech.call_args_list,
      [
        call([""], False, "speaker", False),
        call(["l1", "l2"], False, None, True),
        call(["l3"], False, None, True)
      ]
    )

#### End of class TestOneDramaBlockMethod

class TestDrama(unittest.TestCase):
  def setUp(self):
    self.d = DramaText([])
    self.html = DramaHTML([], None)
    config.LINE_WIDTH = 25
    self.block = [
      "This is the first line which is long",
      "Short second line",
      "This is the third line",
    ]

  def test_verse_speech_align_no_leading_spaces(self):
    block = [ "This is a simple line" ]
    expectedResult = [
      FORMATTED_PREFIX + "<p class='speech'>This is a simple line</p>",
      ""
    ]
    self.align(block, expectedResult, True)

  def test_verse_speech_align_leading_spaces(self):
    block = [ "  This is a simple line" ]
    expectedResult = [
      FORMATTED_PREFIX +
        "<p class='speech'>" +
        "\n<span class='verse-align'>Indented line</span>" +
        "This is a simple line</p>",
      ""
    ]
    self.align(block, expectedResult, True)

  def test_verse_speech_align_leading_spaces_noindent(self):
    block = [ "  This is a simple line" ]
    expectedResult = [
      FORMATTED_PREFIX +
        "<p class='speech'>" +
        "\n<span class='verse-align-noindent'>Indented line</span>" +
        "This is a simple line</p>",
      ""
    ]
    self.align(block, expectedResult, False)

  def align(self, block, expectedResult, hadIndent):
    self.html.lastLine = "Indented line"
    self.html.lastLineHadIndent = hadIndent
    self.html.verseAlignLast = True
    result = self.html.speech(block, verse=True, speaker=None, isContinue=False)
    self.assertSequenceEqual(result, expectedResult)

  def test_option_drama_speaker_hang_text_width(self):
    self.assertEqual(self.d.SPEAKER_HANG_WIDTH, 10)
    config.uopt.addopt("drama-speaker-hang-text-width", "15")
    t = DramaText([])
    config.uopt.addopt("drama-speaker-hang-text-width", "10")
    self.assertEqual(t.SPEAKER_HANG_WIDTH, 15)

  def test_extract_speaker_html(self):
    line, speaker = self.html.extractSpeaker("⩤sc⩥speaker⩤/sc⩥: This is a line")
    self.assertEqual(line, ": This is a line")
    self.assertEqual(speaker, "speaker")

  def test_extract_speaker_html_none(self):
    line, speaker = self.html.extractSpeaker("This is a continued line")
    self.assertEqual(line, "This is a continued line")
    self.assertEqual(speaker, None)

  def test_extract_speaker_text(self):
    line, speaker = self.d.extractSpeaker("SPEAKER: This is a line")
    self.assertEqual(line, ": This is a line")
    self.assertEqual(speaker, "SPEAKER")

  def test_extract_speaker_text_standalone(self):
    line, speaker = self.d.extractSpeaker("SPEAKER.")
    self.assertEqual(line, "")
    self.assertEqual(speaker, "SPEAKER.")

  def test_extract_speaker_text_with_stage(self):
    line, speaker = self.d.extractSpeaker("SPEAKER (stage): This is a line")
    self.assertEqual(line, "(stage): This is a line")
    self.assertEqual(speaker, "SPEAKER ")

  def test_extract_speaker_text_dot(self):
    line, speaker = self.d.extractSpeaker("MR. FOO-BAR'S SPEECH: This is a line")
    self.assertEqual(line, ": This is a line")
    self.assertEqual(speaker, "MR. FOO-BAR'S SPEECH")

  def test_extract_speaker_text_cap_then_normal(self):
    line, speaker = self.d.extractSpeaker("O'Brien is not caps")
    self.assertEqual(line, "O'Brien is not caps")
    self.assertEqual(speaker, None)

  def test_extract_speaker_text_dot2(self):
    line, speaker = self.d.extractSpeaker("ANNA. This is a line")
    self.assertEqual(line, " This is a line")
    self.assertEqual(speaker, "ANNA.")

  def test_extract_speaker_text_none(self):
    line, speaker = self.d.extractSpeaker("This is a continued line")
    self.assertEqual(line, "This is a continued line")
    self.assertEqual(speaker, None)

  def test_stage_block(self):
    expectedResult = [
      FORMATTED_PREFIX + "   This is the first line",
      FORMATTED_PREFIX + "   which is long Short",
      FORMATTED_PREFIX + "   second line This is",
      FORMATTED_PREFIX + "   the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.stageIndent = Style.block
    result = self.d.stageDirection(self.block, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_stage_indent(self):
    expectedResult = [
      FORMATTED_PREFIX + "      This is the first",
      FORMATTED_PREFIX + "   line which is long",
      FORMATTED_PREFIX + "   Short second line This",
      FORMATTED_PREFIX + "   is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.stageIndent = Style.indent
    result = self.d.stageDirection(self.block, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_stage_hang(self):
    expectedResult = [
      FORMATTED_PREFIX + "   This is the first line",
      FORMATTED_PREFIX + "      which is long Short",
      FORMATTED_PREFIX + "      second line This is",
      FORMATTED_PREFIX + "      the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.stageIndent = Style.hang
    result = self.d.stageDirection(self.block, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_stage_right_true(self):
    expectedResult = [
      FORMATTED_PREFIX + "              [Exit right",
      FORMATTED_PREFIX + ""
    ]
    self.d.stageIndent = Style.hang     # ignored
    result = self.d.stageDirection([ "[Exit right" ], True)
    self.assertSequenceEqual(result, expectedResult)

  def test_stage_right_false(self):
    expectedResult = [
      FORMATTED_PREFIX + "   [Exit right",
      FORMATTED_PREFIX + ""
    ]
    self.d.stageIndent = Style.hang     # ignored
    result = self.d.stageDirection([ "[Exit right" ], False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "  which is long Short",
      FORMATTED_PREFIX + "  second line This is the",
      FORMATTED_PREFIX + "  third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(self.block, False, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_speaker_inline(self):
    expectedResult = [
      FORMATTED_PREFIX + "  Speaker: This is the",
      FORMATTED_PREFIX + "  first line which is",
      FORMATTED_PREFIX + "  long Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    self.d.speakerStyle = Style.inline
    result = self.d.speech(self.block, False, "Speaker: ", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_speaker_hang(self):
    expectedResult = [
      FORMATTED_PREFIX + "SPEAKER   This is the",
      FORMATTED_PREFIX + "          first line",
      FORMATTED_PREFIX + "          which is long",
      FORMATTED_PREFIX + "          Short second",
      FORMATTED_PREFIX + "          line This is",
      FORMATTED_PREFIX + "          the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    self.d.speakerStyle = Style.hang
    result = self.d.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_speaker_hang_width(self):
    expectedResult = [
      FORMATTED_PREFIX + "SPEAKER        This is",
      FORMATTED_PREFIX + "               the first",
      FORMATTED_PREFIX + "               line which",
      FORMATTED_PREFIX + "               is long",
      FORMATTED_PREFIX + "               Short",
      FORMATTED_PREFIX + "               second",
      FORMATTED_PREFIX + "               line This",
      FORMATTED_PREFIX + "               is the",
      FORMATTED_PREFIX + "               third line",
      FORMATTED_PREFIX + ""
    ]
    config.uopt.addopt("drama-speaker-hang-text-width", "15")
    t = DramaText([])
    config.uopt.addopt("drama-speaker-hang-text-width", "10")
    t.speechIndent = Style.block
    t.speakerStyle = Style.hang
    result = t.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speaker_center(self):
    expectedResult = [
      FORMATTED_PREFIX + "         SPEAKER",
    ]
    self.d.speakerStyle = Style.centre
    result = self.d.speakerStandalone("speaker")
    self.assertSequenceEqual(result, expectedResult)

  def test_speaker_inline(self):
    self.d.speakerStyle = Style.inline
    result = self.d.speakerStandalone("speaker")
    self.assertSequenceEqual(result, [])

  def test_speaker_left(self):
    expectedResult = [
      FORMATTED_PREFIX + "SPEAKER",
    ]
    self.d.speakerStyle = Style.left
    result = self.d.speakerStandalone("speaker")
    self.assertSequenceEqual(result, expectedResult)

  def test_speaker_hang(self):
    expectedResult = [ ]
    self.d.speakerStyle = Style.hang
    result = self.d.speakerStandalone("speaker")
    self.assertSequenceEqual(result, expectedResult)

  def test_speaker_center(self):
    expectedResult = [
      FORMATTED_PREFIX + "         SPEAKER",
    ]
    self.d.speakerStyle = Style.centre
    result = self.d.speakerStandalone("speaker")
    self.assertSequenceEqual(result, expectedResult)

  """ TODO: non-hang speaker code moved out of speech
  def test_speech_block_speaker_centre(self):
    expectedResult = [
      FORMATTED_PREFIX + "         SPEAKER",
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "  which is long Short",
      FORMATTED_PREFIX + "  second line This is the",
      FORMATTED_PREFIX + "  third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    self.d.speakerStyle = Style.centre
    result = self.d.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)
  """

  def test_speech_block_verse(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(self.block, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_speaker_inline(self):
    expectedResult = [
      FORMATTED_PREFIX + "  Speaker: This is the first line which is long",
      FORMATTED_PREFIX + "  Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    self.d.speakerStyle = Style.inline
    result = self.d.speech(self.block, True, "Speaker: ", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_leading_spaces_preserved(self):
    b = [
      "    This is the first line which is indented",
      "This is the second line",
    ]
    expectedResult = [
      FORMATTED_PREFIX + "      This is the first line which is indented",
      FORMATTED_PREFIX + "  This is the second line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(b, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_embed_stage(self):
    b = [
      "This is the first line which is long",
      "[Embed Stage Direction in verse]",
      "This is the third line",
    ]
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  [Embed Stage Direction",
      FORMATTED_PREFIX + "  in verse]",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(b, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_embed_stage_multi(self):
    b = [
      "This is the first line which is long",
      "[Embed Stage Direction in verse",
      "which continues onward]",
      "This is the third line",
    ]
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  [Embed Stage Direction",
      FORMATTED_PREFIX + "  in verse which",
      FORMATTED_PREFIX + "  continues onward]",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(b, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_embed_stage_not_mixed(self):
    b = [
      "This is the first line which is long",
      "[Embed Stage Direction] with more verse",
      "This is the third line",
    ]
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  [Embed Stage Direction] with more verse",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(b, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_verse_embed_stage_not_closed(self):
    b = [
      "This is the first line which is long",
      "[Embed Stage Direction not closed",
      "This is the third line",
    ]
    self.d.speechIndent = Style.block
    with self.assertRaises(SystemExit) as cm:
      result = self.d.speech(b, True, None, False)
    self.assertEqual(cm.exception.code, 1)

  def test_speech_block_verse_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(self.block, True, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "which is long Short",
      FORMATTED_PREFIX + "second line This is the",
      FORMATTED_PREFIX + "third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    result = self.d.speech(self.block, False, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_speaker_inline(self):
    expectedResult = [
      FORMATTED_PREFIX + "  Speaker: This is the",
      FORMATTED_PREFIX + "first line which is long",
      FORMATTED_PREFIX + "Short second line This is",
      FORMATTED_PREFIX + "the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    self.d.speakerStyle = Style.inline
    result = self.d.speech(self.block, False, "Speaker: ", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_speaker_hang(self):
    expectedResult = [
      FORMATTED_PREFIX + "SPEAKER     This is the",
      FORMATTED_PREFIX + "          first line",
      FORMATTED_PREFIX + "          which is long",
      FORMATTED_PREFIX + "          Short second",
      FORMATTED_PREFIX + "          line This is",
      FORMATTED_PREFIX + "          the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    self.d.speakerStyle = Style.hang
    result = self.d.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)

  """
  def test_speech_indent_speaker_centre(self):
    expectedResult = [
      FORMATTED_PREFIX + "         SPEAKER",
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "which is long Short",
      FORMATTED_PREFIX + "second line This is the",
      FORMATTED_PREFIX + "third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    self.d.speakerStyle = Style.centre
    result = self.d.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)
  """

  def test_speech_indent_verse(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "Short second line",
      FORMATTED_PREFIX + "This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    result = self.d.speech(self.block, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_verse_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "This is the first line which is long",
      FORMATTED_PREFIX + "Short second line",
      FORMATTED_PREFIX + "This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    result = self.d.speech(self.block, True, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_verse_embed_stage(self):
    b = [
      "This is the first line which is long",
      "[Embed Stage Direction in verse]",
      "This is the third line",
    ]
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "[Embed Stage Direction in",
      FORMATTED_PREFIX + "verse]",
      FORMATTED_PREFIX + "This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    result = self.d.speech(b, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_hang(self):
    expectedResult = [
      FORMATTED_PREFIX + "This is the first line",
      FORMATTED_PREFIX + "  which is long Short",
      FORMATTED_PREFIX + "  second line This is the",
      FORMATTED_PREFIX + "  third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    result = self.d.speech(self.block, False, None, False)
    self.assertSequenceEqual(expectedResult, result)

  def test_speech_hang_speaker_inline(self):
    expectedResult = [
      FORMATTED_PREFIX + "Speaker: This is the",
      FORMATTED_PREFIX + "  first line which is",
      FORMATTED_PREFIX + "  long Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    self.d.speakerStyle = Style.inline
    result = self.d.speech(self.block, False, "Speaker: ", False)
    self.assertSequenceEqual(expectedResult, result)

  def test_speech_hang_speaker_hang(self):
    expectedResult = [
      FORMATTED_PREFIX + "SPEAKER   This is the",
      FORMATTED_PREFIX + "            first line",
      FORMATTED_PREFIX + "            which is long",
      FORMATTED_PREFIX + "            Short second",
      FORMATTED_PREFIX + "            line This is",
      FORMATTED_PREFIX + "            the third",
      FORMATTED_PREFIX + "            line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    self.d.speakerStyle = Style.hang
    result = self.d.speech(self.block, False, "speaker", False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_hang_verse(self):
    expectedResult = [
      FORMATTED_PREFIX + "This is the first line which is long",
      FORMATTED_PREFIX + "  Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    result = self.d.speech(self.block, True, None, False)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_hang_verse_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line which is long",
      FORMATTED_PREFIX + "  Short second line",
      FORMATTED_PREFIX + "  This is the third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    result = self.d.speech(self.block, True, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_block_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "  which is long Short",
      FORMATTED_PREFIX + "  second line This is the",
      FORMATTED_PREFIX + "  third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.block
    result = self.d.speech(self.block, False, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "This is the first line",
      FORMATTED_PREFIX + "which is long Short",
      FORMATTED_PREFIX + "second line This is the",
      FORMATTED_PREFIX + "third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    result = self.d.speech(self.block, False, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_indent_cont_continue_indent(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "which is long Short",
      FORMATTED_PREFIX + "second line This is the",
      FORMATTED_PREFIX + "third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.indent
    self.d.speechContinue = Style.indent
    result = self.d.speech(self.block, False, None, True)
    self.assertSequenceEqual(result, expectedResult)

  def test_speech_hang_cont(self):
    expectedResult = [
      FORMATTED_PREFIX + "  This is the first line",
      FORMATTED_PREFIX + "  which is long Short",
      FORMATTED_PREFIX + "  second line This is the",
      FORMATTED_PREFIX + "  third line",
      FORMATTED_PREFIX + ""
    ]
    self.d.speechIndent = Style.hang
    result = self.d.speech(self.block, False, None, True)
    self.assertSequenceEqual(expectedResult, result)

#### End of class TestDrama
