#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import string, re
import unittest
from unittest.mock import MagicMock, Mock, call

import config
from config import FORMATTED_PREFIX
from msgs import fatal, uprint, cprint, dprint
import footnote
import fpgen

from parse import parseTagAttributes

leadInCSS = """[3335]
  .lead-in {
    font-variant: small-caps;
  }
"""

paragraphListCSS = """[815]
    .listTag {
        padding-right:.5em;
        text-align:right;
        display:table-cell;
    }
    .listPara {
      display:table-cell;
    }
    .listEntry {
      display:table-row;
    }
"""

paraStyles = [
  "hang",
  "indent",
  "nobreak",
  "list",
  "default"
]

paraTags = [ "<" + style + ">" for style in paraStyles ]
pstyleTags = [ "<pstyle=" + style + ">" for style in paraStyles ]

# At this point, all tags which are purely inside text have been converted
# into internal codes. (i.e. font styles and sizes)
# So we don't have to worry about them causing artificial paragraph
# boundaries. At this point, we can simply split off paragraphs by stopping
# at blank lines, or lines which start with tags.
# Well, always an exception: we special case <br/> and don't start a para
# for that one case.
#
# We need to ignore (except as delimiters) anything within blocks which
# are formatted differently: <lg>, <table>, <sidenote>.
# <caption> inside <illustration> is treated a little special, in that
# we find paragraphs inside the caption, but tag them with the caption class.
#
# Most of the code this is involved in handling the paragraph-specific 
# instructions: <hang>, <nobreak> and <pstyle>
class ParaIterator: #{

  def __init__(self, wb, style):
    self.wb = wb
    self.defaultStyle = style
    self.globalStyle = style
    self.sidenoteBreak = (config.uopt.getopt('sidenote-breaks-paragraphs', True) == True)

    # No formatting inside footnotes if they are sidenotes
    self.noFormattingTags = [ "lg", "table", "illustration" ]
    if footnote.getFootnoteStyle() == footnote.sidenote:
      self.noFormattingTags.append("footnote")

  def __iter__(self):
    self.i = 0
    return self

  def __next__(self):
    i = self.i
    paragraphStyle = self.defaultStyle
    lastTagLine = None
    while i < len(self.wb):
      line = self.wb[i]

      # A whole bunch of ways that a line or group of lines isn't formatted
      if line.startswith(config.FORMATTED_PREFIX): # preformatted
        i += 1
        continue

      # No formatting inside these tags
      for tag in self.noFormattingTags:
        j = self.skip(tag, self.wb, i)
        if i != j:
          break
      if i != j:
        i = j
        continue

      # No formatting inside these, but slightly different parsing
      for tag in [ "sidenote" ]:
        j = self.skipSameline(tag, self.wb, i)
        if i != j:
          break
      if i != j:
        i = j
        continue

      # <pstyle=XXX> alone on a line
      # Sets defaultStyle either as specified, or to global default
      if line.startswith("<pstyle="):
        self.defaultStyle = None
        line = line.strip()
        for j,style in enumerate(pstyleTags):
          if line == style:
            self.defaultStyle = paraStyles[j]
            break
        if self.defaultStyle == None:
          fatal("Bad pstyle: " + self.wb[i])
        if self.defaultStyle == "default":
          self.defaultStyle = self.globalStyle

        # Next paragraph will be this style
        paragraphStyle = self.defaultStyle

        # Remove <pstyle> line completely
        del(self.wb[i])
        if i > 0:
          i -= 1
        continue

      # See if there is a single-paragraph style
      if line.startswith("<"):
        line = line.strip()
        for j,tag in enumerate(paraTags):
          if line.startswith(tag):
            line = line[len(tag):]
            self.wb[i] = line
            # Override for next paragraph
            paragraphStyle = paraStyles[j]
            break

      # outside of tables and line groups, no double blank lines
      if self.wb[i-1] == "" and line == "":
        del (self.wb[i])
        if i > 0:
          i -= 1
        continue

      # Ignore a blank line
      if line == "":
        i += 1
        continue

      # Ignore lines with tags; note that textual tags like <i> have been
      # converted into special characters, not <
      if line[0] == '<' and line != "<br/>":
        lastTagLine = line
        i += 1
        continue

      # A paragraph starts on a non-blank line,
      # and ends at:
      # - A blank line
      # - a standalone line: preformatted, <table>, <lg>, <sidenote>
      # - end of file
      # - a paragraph tag: <nobreak>, <hang>, <pstyle>, drop-cap
      # - any other tag!
      block = [ ]
      n = len(self.wb)
      self.start = i
      while i < n:
        if self.isParaBreak(self.wb[i]):
          break
        block.append(self.wb[i])
        i += 1

      # Paragraph now accumulated into block[]
      self.i = i
      return paragraphStyle, block, lastTagLine

    # Ran out of lines, no more paragraphs
    raise StopIteration

  def replace(self, block):
    self.wb[self.start:self.i] = block
    self.i = self.start + len(block)
  
  # No paragraphs in this particular tag; for a tag which must start a line
  @staticmethod
  def skip(tag, wb, start):
    n = start
    if wb[n].startswith("<" + tag):
      if wb[n].endswith("/>"):
        return n+1
      endTag = "</" + tag
      m = len(wb)
      while not wb[n].startswith(endTag):
        n += 1
        if n >= m:
          fatal("Missing end tag: " + endTag + " starting near " + str(start))
    return n

  # No paragraphs in this tag; for a tag which can end inside a line.
  @staticmethod
  def skipSameline(tag, wb, start):
    n = start
    if wb[n].startswith("<" + tag):
      endTag = "</" + tag
      m = len(wb)
      while not endTag in wb[n]:
        n += 1
        if n >= m:
          fatal("Missing end tag: " + endTag + " starting near " + str(start))
      n += 1
    return n

  def isParaBreak(self, line):
    if line == "":
      return True
    if line[0] == config.FORMATTED_PREFIX: # preformatted
      return True
    if line[0] == '<' and line != "<br/>":
      if line[0:10] == "<sidenote>":
        # sidenote causes a para break depending on option
        return self.sidenoteBreak
      return True
    return False
#}

# The different tags we use for paragraphs
hangPara = "<p class='hang'>"
linePara = "<p>"
blockPara = "<p class='noindent'>"
indentPara = "<p class='pindent'>"
captionPara = "<p class='caption'>"
creditPara = "<p class='credit'>"

styleToHtml = {
  "hang" : hangPara,
  "indent" : indentPara,
  "nobreak" : blockPara,
  "list" : "XXX",
  "line" : "<p>",
  "caption" : captionPara,
  "credit" : creditPara,
}

def after(parent, tag, css):
  result = False
  if tag in parent.uprop.prop:
    result = parent.uprop.prop[tag].split(',')
    if css != None:
      parent.addcss(css)
  return result

# All the hard parts of this are isolating the paragraphs, this has
# been moved into the ParaIterator, which is responsible for finding
# and returning us blocks of paragraphs.
def markParaArray(parent, wb, globalStyle):
  autoDropCap = after(parent, "drop-after", fpgen.dropCapCSS)
  tagLeadIn = after(parent, "lead-in-after", leadInCSS)
  noindentAfter = after(parent, "pstyle-noindent-after", None)

  p = ParaIterator(wb, globalStyle)

  for style, para, lastTagLine in iter(p):
    #cprint(style + ": " + str(para) + ", last: " + str(lastTagLine))

    dropCap = False
    leadIn = False
    if autoDropCap:
      dropCap = isFollowing(autoDropCap, lastTagLine)
    if tagLeadIn:
      leadIn = isFollowing(tagLeadIn, lastTagLine)
    if noindentAfter:
      if isFollowing(noindentAfter, lastTagLine):
        style = "nobreak"

    para = decoration(para, dropCap, leadIn)

    if style == "list":
      parent.css.addcss(paragraphListCSS)
      w = para[0].split(" ")
      if w[0] == "":
        l = ''
      else:
        l = "<span class='listTag'>" + w[0] + "</span>"
      l += "<p class='listPara'>" + " ".join(w[1:])
      para[0] = l
      para[-1] += "</p>"
      para.insert(0, "<div class='listEntry'>")
      para.append("</div>")
    else:
      # If the line has a drop cap, don't indent
      if parent.dropCapMarker in para[0] and style == "indent":
        style = "nobreak"
      para[0] = para[0].replace(parent.dropCapMarker, "")
      tag = styleToHtml[style]
      if parent.dropCapParaMarker in para[0]:
        para[0] = para[0].replace(parent.dropCapParaMarker, tag)
      else:
        para[0] = tag + para[0]
      para[-1] += "</p>"

    p.replace(para)
  return wb

def testAutoFor(prop, value):
  try:
    prop.index(value)
    return True
  except ValueError:
    pass

# Does this line trigger the next paragraph?
def isFollowing(prop, line):
  if line == None:
    return False

  if line.startswith("<tb>"):
    return testAutoFor(prop, "tb")

  if line.startswith("<heading"):
    m = re.match("^<heading\s*(.*?)>", line)
    if m:
      harg = m.group(1)
      if "nobreak" in harg:
        harg = harg.replace("nobreak", "")
      attributes = parseTagAttributes("heading", harg, fpgen.headerAttributes)

      level = 1
      if "level" in attributes:
        hlevel = int(attributes["level"])
      return testAutoFor(prop, "h" + str(hlevel))

  return False

# Extract the lead in from a line.
#
# Might include <drop src="..."> so basically looking for space
# but not inside <>
#
# If we see a <sc> tag, assume they are doing everything manually, and
# return without a word.
#
# Use multiple words in the case of an honorific: e.g. Sir Freako Barto
# by taking all words which start with an uppercase letter.
# Handle also one and two letter words, i.e. A, and It.
def getLeadIn(line):
  word, line = getLeadingWord(line)
  includeNext = (wordlen(word) < 2)
  while True:
    nextWord, rest = getLeadingWord(line)
    if nextWord == "":
      break
    if not includeNext and not nextWord[0].isupper():
      break
    word = word + " " + nextWord
    line = rest
    includeNext = False

  dprint(2, "lead in phrase: [" + word + "], rest: [" + line + "]")
  return word, line

def wordlen(w):
  i = 0
  n = len(w)
  while i < n:
    c = w[i]
    if c.isalnum():
      break
    i += 1
  j = i
  while i < n:
    c = w[i]
    if not c.isalnum():
      break
    i += 1
  return i - j

def getLeadingWord(line):
  line = line.strip()
  word = ""
  tag = ""
  inTag = False
  for c in line:
    if inTag:
      if c == '⩥':
        inTag = False
        if tag == 'sc':
          return "", line
    if c == '⩤':
      inTag = True
      tag = ""
    else:
      tag += c
    if not inTag:
      if c == ' ':
        break
    word += c
  line = line[len(word):]
  dprint(3, "lead in word: [" + word + "], rest: [" + line + "]")
  return word, line

def decorateLeadIn(word):
  return "⩤span class='lead-in'⩥" + word + "⩤/span⩥"

def decoration(block, dropCap, leadIn):
  if not dropCap and not leadIn:
    return block

  line = block[0]
  word, line = getLeadIn(line)
  if dropCap:
    word = autoDropCap(word)
  if leadIn and word:
    word = decorateLeadIn(word)
  block[0] = word + line
  return block

# Add a drop cap to this paragraph
def autoDropCap(word):
  dprint(2, "Add drop cap before: " + word)
  letter = word[0]
  if letter == '<' or letter == "⩤":
    # If it is in italics or something, just do nothing
    return word
  if letter == "“" or letter == "‘":
    letter += word[1]
    word = word[1:]
  word = fpgen.HTML.dropCapMarker + "⩤span class='dropcap'⩥" + letter + "⩤/span⩥" + word[1:]
  return word

