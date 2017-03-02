#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import re
import sys
import collections
from msgs import fatal, cprint

# parseEmbeddedTagWithoutContent: (e.g. <fn>, <target>)
#   text<tag arg>text
#
# parseEmbeddedSingleLineTagWithContent: (e.g. <link>)
#   text<tag arg>content</tag>text
#
# parseStandaloneSingleLineTagWithContent: (e.g. <heading>)
#   <tag arg>content</tag>
#
# parseEmbeddedTagBlock:
#   text<tag>...\n...</tag>text
#
# parseStandaloneTagBlock: (e.g. <if>, <illustration>)
#   <tag>...\n...</tag>
#
# parseLineEntry:
#   <tag>content</tag>

def parseEmbeddedTagWithoutContent(block, tag, function):
  for i,line in enumerate(block):
    block[i] = _parseEmbeddedTagWithoutContent(line, tag, function)

def _parseEmbeddedTagWithoutContent(line, tag, function):
  origLine = line
  startTag = "<" + tag
  startLen = len(startTag)
  off = 0
  while True:
    startTagOff = line.find(startTag, off)
    if startTagOff == -1:
      return line
    s = list(line)
    s.append('\0')
    startArg = startTagOff + startLen
    c = s[startArg]
    i = startArg
    if c != '>' and c != ' ' and c != '/':
      # Nope, not really this tag
      off = i
      continue
    # Look for end of arg
    while s[i] != '>' and s[i] != '\0':
      i += 1
    if s[i] == '\0':
      # Again, not really this tag?  <tag xxx without closing greater...
      off = i
      continue
    startTagEnd = i+1
    endArgOff = i-1 if s[i-1] == '/' else i

    arg = line[startArg:endArgOff].strip()
    repl = function(arg, origLine)
    leftPart = line[0:startTagOff]
    rightPart = line[startTagEnd:]
    line = leftPart + repl + rightPart
    off = len(leftPart) + len(repl)

def parseStandaloneSingleLineTagWithContent(block, tag, function):
  return parseEmbeddedSingleLineTagWithContent(block, tag, function, wholeLine = True)

def parseEmbeddedSingleLineTagWithContent(block, tag, function, wholeLine = False):
  for i,line in enumerate(block):
    block[i] = _parseEmbeddedSingleLineTagWithContent(line, tag, function, wholeLine)
  
def _parseEmbeddedSingleLineTagWithContent(line, tag, function, wholeLine = False):
  origLine = line
  startTag = "<" + tag
  startLen = len(startTag)
  endTag = "</" + tag + ">"
  endLen = len(endTag)
  off = 0
  while True:
    startTagOff = line.find(startTag, off)
    if startTagOff == -1:
      if endTag in line:
        fatal("Found closing tag " + endTag + " without open tag: " + line)
      return line
    s = list(line)
    s.append('\0')
    startArg = startTagOff + startLen
    c = s[startArg]
    i = startArg
    if c != '>' and c != ' ':
      # Nope, not really this tag
      off = i
      continue
    # Look for end of arg
    while s[i] != '>' and s[i] != '\0':
      i += 1
    if s[i] == '\0':
      # Again, not really this tag?  <tag xxx without closing greater...
      off = i
      continue
    if s[i-1] == '/':
      fatal("Open tag " + tag + " is marked for close; this tag requires an open and close tag, with text between: " + line)
    arg = line[startArg:i].strip()
    startContent = i+1
    endTagOff = line.find(endTag, startContent)
    if endTagOff == -1:
      fatal("Open tag " + tag + " found, no closing tag: " + line)
    content = line[startContent:endTagOff]

    repl = function(arg, content, origLine)

    leftPart = line[0:startTagOff]
    rightPart = line[endTagOff+endLen:]
    line = leftPart + repl + rightPart
    off = len(leftPart) + len(repl)
    if wholeLine:
      if leftPart != "" or rightPart != "":
        fatal("Tag " + startTag +
          ">: This tag must be alone on the line. Line: " + origLine +
          " >>>" + leftPart + "<<<>>>" + rightPart + "<<<")

# Extract the text on a line which looks like <tag>XXXX</tag>
def parseLineEntry(tag, line):
  pattern = "^<" + tag + "\s*(.*?)>(.*)</" + tag + ">$"
  m = re.match(pattern, line)
  if not m:
    fatal("Incorrect line: " + line)
  return m.group(1), m.group(2)

# Look for <tag> ... </tag> where the tags can be embedded,
# i.e.   text<tag>...\n...</tag>text
# If there is no text following <tag>, no line is added
# and if there is no text following </tag>, no line is added
# Unlike parseStandaloneTagBlock, which almost always gets the
# whole file as the lines arg; this would probably get the set
# of lines from parseStandaloneTagBlock.
def parseEmbeddedTagBlock(lines, tag, function):
  i = 0
  startTag = "<" + tag
  endTag = "</" + tag + ">"
  regex = re.compile(startTag + "(.*?)>")
  regexEnd = re.compile(endTag)
  while i < len(lines):
    m = regex.search(lines[i])
    if not m:
      i += 1
      continue

    openLine = lines[i]
    openArgs = m.group(1)
    block = []
    startLineStart = openLine[:m.start(0)]
    startLineTrailer = openLine[m.end(0):]
    line = startLineTrailer
    startLineNumber = i

    j = i
    while True:
      m = regexEnd.search(line)
      if m:
        endLineStart = line[:m.start(0)]
        endLineTrailer = line[m.end(0):]
        if endLineStart != "":
          block.append(endLineStart)
        endLineNumber = j
        if len(block) == 0 and startLineNumber != endLineNumber:
          block.append("")
        break
      if j == startLineNumber:
        if startLineTrailer != "":
          block.append(startLineTrailer)
      else:
        block.append(line)
      j += 1
      if j == len(lines):
        fatal("No closing tag found for " + tag + "; open line: " + openLine)
      line = lines[j]

    replacement = function(openArgs, block)

    # put startLine at the beginning of the first line,
    # put endLineTrailer at the end of the last line.
    n = len(replacement)
    if n == 0:
      if startLineNumber == endLineNumber:
        # <tag>xxx</tag> => ""
        # b4<tag>xxx</tag> => b4
        # b4<tag>xxx</tag>after => b4after
        # <tag>xxx</tag>after => after
        replacement.append(startLineStart + endLineTrailer)
      else:
        # <tag>x\nx</tag> => "", ""
        # b4<tag>x\nx</tag> => b4, ""
        # b4<tag>x\nx</tag>after => b4, after
        # <tag>x\nx</tag>after => "", after
        replacement.append(startLineStart)
        replacement.append(endLineTrailer)
    else:
      # <tag></tag>; repl=R => block=[], R
      # <tag></tag>after; repl=R => block=[], Rafter
      # b4<tag></tag>; repl=R => block=[], b4R
      # b4<tag></tag>after; repl=R => block=[], b4Rafter
      # <tag>\n</tag>; repl=R => block=[""], R
      # <tag>\n</tag>after; repl=R => block=[""], R\nafter
      # b4<tag>\n</tag>; repl=R => block=[""], b4\nR
      # b4<tag>\n</tag>after; repl=R => block=[""], b4\nR\nafter
      # b4<tag>x\n</tag>after; repl=R => block=["x"], b4\nR\nafter
      # b4<tag>x\ny</tag>after; repl=R => block=["x","y"], b4\nR\nafter
      if startLineNumber == endLineNumber:
        # On the same line, prefix & suffix on same line
        replacement[0] = startLineStart + replacement[0]
        replacement[-1] = replacement[-1] + endLineTrailer
      else:
        # On different lines, prefix & suffix on different lines
        if startLineStart != "":
          replacement.insert(0, startLineStart)
        if endLineTrailer != "":
          replacement.append(endLineTrailer)

    lines[i:j+1] = replacement

    # Keep going, in case there are more tags on the same line.
    # Danger! One consequence is recursion, we will expand an
    # expanded tag.  Would be nice to keep going, but only on the
    # end of the current line...
    #i += len(replacement)

  return lines

# Look for <tag> ... </tag> where the tags are on standalone lines.
# As we find each such block, invoke the function against it
#
# If the optional allowClose is set to true, then the opening tag
# may end in />, to close at the same time, for a zero-length block.
#
# If the optional lineFunction is given, then each line is passed
# to that function, and the function may return a list of lines which
# are replace that line.  Only the last line of that block is processed
def parseStandaloneTagBlock(lines, tag, function, allowClose = False, lineFunction = None):
  i = 0
  startTag = "<" + tag
  endTag = "</" + tag + ">"
  regex = re.compile(startTag + "(.*?)(/)?>")
  while i < len(lines):

    if lineFunction != None:
      insertion = lineFunction(i, lines[i])
      lines[i:i+1] = insertion
      i += len(insertion)-1

    m = regex.match(lines[i])
    if not m:
      i += 1
      continue

    openLine = lines[i]
    openArgs = m.group(1)

    block = []
    close = m.group(2)
    if close != None:
      if not allowClose:
        fatal("Open tag " + tag + " marked for close. " + openLine)
      j = i
    else:
      j = i+1
      while j < len(lines):
        line = lines[j]
        if line.startswith(endTag):
          break
        if line.startswith(startTag):
          fatal("No closing tag found for " + tag + "; open line: " + openLine +
            "; found another open tag: " + line)
        block.append(line)
        j += 1

      if j == len(lines):
        fatal("No closing tag found for " + tag + "; open line: " + openLine)
    
    replacement = function(openArgs, block)

    lines[i:j+1] = replacement
    i += len(replacement)

  return lines

class TestParsing(unittest.TestCase):

  #
  # Tests of parseEmbeddedTagWithoutContent
  #
  def verifyEmbeddedTagWOC(self, line, expectedArg, expectedResult, replacement):
    self.callbackN = 0
    def f(arg, orig):
      index = self.callbackN
      self.callbackN += 1
      self.assertEquals(line, orig)
      self.assertEquals(arg, expectedArg[index])
      return replacement[index] if replacement != None else ""
    result = _parseEmbeddedTagWithoutContent(line, "tag", f)
    self.assertEquals(self.callbackN, 1 if replacement == None else len(replacement))
    self.assertEquals(result, expectedResult)

  def test_embed_without_empty(self):
    line = ""
    self.verifyEmbeddedTagWOC(line, [""], "", [])

  def test_embed_without_empty1(self):
    line = "xx"
    self.verifyEmbeddedTagWOC(line, [""], "xx", [])

  def test_embed_without_empty1(self):
    line = "xx<tagger>"
    self.verifyEmbeddedTagWOC(line, [""], "xx<tagger>", [])

  def test_embed_without(self):
    line = "abc<tag>def"
    self.verifyEmbeddedTagWOC(line, [""], "abcdef", None)

  def test_embed_without_arg(self):
    line = "abc<tag arg arg>def"
    self.verifyEmbeddedTagWOC(line, ["arg arg"], "abcdef", None)

  def test_embed_without_arg_close(self):
    line = "abc<tag arg arg/>def"
    self.verifyEmbeddedTagWOC(line, ["arg arg"], "abcdef", None)

  def test_embed_without_repl(self):
    line = "abc<tag>def"
    self.verifyEmbeddedTagWOC(line, [""], "abcrepldef", [ "repl" ])

  def test_embed_without_repl_close(self):
    line = "abc<tag/>def"
    self.verifyEmbeddedTagWOC(line, [""], "abcrepldef", [ "repl" ])

  def test_embed_without_repl_close_space(self):
    line = "abc<tag   />def"
    self.verifyEmbeddedTagWOC(line, [""], "abcrepldef", [ "repl" ])

  def test_embed_without_twice(self):
    line = "abc<tag>def<tag>xxx"
    self.verifyEmbeddedTagWOC(line, ["", ""], "abcdefxxx", [ "", "" ])

  def test_embed_without_twice_arg(self):
    line = "abc<tag a1>def<tag a2>xxx"
    self.verifyEmbeddedTagWOC(line, ["a1", "a2"], "abcdefxxx", [ "", "" ])

  def test_embed_without_twice_arg_repl(self):
    line = "abc<tag a1>def<tag a2>xxx"
    self.verifyEmbeddedTagWOC(line, ["a1", "a2"], "abcr1defr2xxx", [ "r1", "r2" ])

  #
  # Tests of parseEmbeddedSingleLineTagWithContent
  #
  def verifyEmbeddedContent(self, line, expectedArg, expectedContent, \
    expectedResult, replacement):
    self.callbackN = 0
    def f(arg, content, orig):
      index = self.callbackN
      self.callbackN += 1
      self.assertEquals(line, orig)
      self.assertEquals(arg, expectedArg[index])
      self.assertEquals(content, expectedContent[index])
      return replacement[index] if replacement != None else ""

    result = _parseEmbeddedSingleLineTagWithContent(line, "tag", f)
    self.assertEquals(self.callbackN, 1 if replacement == None else len(replacement))
    self.assertEquals(result, expectedResult)

  def test_embed_content_empty(self):
    line = ""
    self.verifyEmbeddedContent(line, [""], ["yyy"], "", [])

  def test_embed_content_empty1(self):
    line = "yyy"
    self.verifyEmbeddedContent(line, [], [], "yyy", [])

  def test_embed_content_empty2(self):
    line = "yyy<tagger>foo</tagger>"
    self.verifyEmbeddedContent(line, [], [], "yyy<tagger>foo</tagger>", [])

  def test_embed_content_empty3(self):
    line = "yyy<tag"
    self.verifyEmbeddedContent(line, [], [], "yyy<tag", [])

  def test_embed_content_empty4(self):
    line = "yyy<tag more"
    self.verifyEmbeddedContent(line, [], [], "yyy<tag more", [])

  def test_embed_content(self):
    line = "xxx<tag>yyy</tag>"
    self.verifyEmbeddedContent(line, [""], ["yyy"], "xxx", None)

  def test_embed_content_alone(self):
    line = "<tag>yyy</tag>"
    self.verifyEmbeddedContent(line, [""], ["yyy"], "", None)

  def test_embed_content_arg(self):
    line = "xxx<tag arg arg arg>yyy</tag>zzz"
    self.verifyEmbeddedContent(line, ["arg arg arg"], ["yyy"], "xxxzzz", None)

  def test_embed_content_arg_spaces(self):
    # preserve spaces in content, but not arg
    line = "xxx<tag     arg >  yyy  </tag>zzz"
    self.verifyEmbeddedContent(line, ["arg"], ["  yyy  "], "xxxzzz", None)

  def test_embed_content_repl(self):
    line = "xxx<tag>yyy</tag>zzz"
    self.verifyEmbeddedContent(line, [""], ["yyy"], "xxxreplzzz", [ "repl" ])

  def test_embed_content_twice(self):
    line = "xxx<tag arg>yyy</tag>zzz<tag arg2>aaaa</tag>bbbb"
    self.verifyEmbeddedContent(line, ["arg", "arg2"], ["yyy", "aaaa"],
        "xxxzzzbbbb", [ "", "" ])

  def test_embed_content_twice_repl(self):
    line = "xxx<tag arg>yyy</tag>zzz<tag arg2>aaaa</tag>bbbb"
    self.verifyEmbeddedContent(line, ["arg", "arg2"], ["yyy", "aaaa"],
        "xxxr1zzzr2bbbb", [ "r1", "r2" ])

  def test_embed_content_no_close(self):
    line = "xxx<tag arg arg arg>yyy< /tag>"
    with self.assertRaises(SystemExit) as cm:
      self.verifyEmbeddedContent(line, None, None, None, None)
    self.assertEqual(cm.exception.code, 1)

  def test_embed_content_no_openclose(self):
    line = "xxx<tag arg arg arg/>yyy</tag>"
    with self.assertRaises(SystemExit) as cm:
      self.verifyEmbeddedContent(line, None, None, None, None)
    self.assertEqual(cm.exception.code, 1)

  def test_embed_content_no_open(self):
    line = "xxx< tag arg arg arg/>yyy</tag>"
    with self.assertRaises(SystemExit) as cm:
      self.verifyEmbeddedContent(line, None, None, None, None)
    self.assertEqual(cm.exception.code, 1)

  #
  # Tests of parseStandaloneTagBlock
  #
  def verify(self, lines, expectedResult, expectedBlocks, replacementBlocks, open="", allowClose = False):
    self.callbackN = -1
    def f(l0, block):
      self.callbackN += 1
      self.assertEquals(l0, open)
      self.assertSequenceEqual(block, expectedBlocks[self.callbackN])
      return replacementBlocks[self.callbackN] if replacementBlocks != None else []

    parseStandaloneTagBlock(lines, "tag", f, allowClose = allowClose)
    self.assertSequenceEqual(lines, expectedResult)

  def test_parse0(self):
    lines = [ "<tag>", "</tag>", ]
    expectedResult = [ ]
    expectedBlock = [ [ ] ]
    self.verify(lines, expectedResult, expectedBlock, None)

  def test_parse_no_close(self):
    lines = [ "<tag>", "l1", ]
    with self.assertRaises(SystemExit) as cm:
      parseStandaloneTagBlock(lines, "tag", None)
    self.assertEqual(cm.exception.code, 1)

  def test_parse_bad_close(self):
    lines = [ "<tag/>", "l1", ]
    with self.assertRaises(SystemExit) as cm:
      parseStandaloneTagBlock(lines, "tag", None)
    self.assertEqual(cm.exception.code, 1)

  def test_parse_close(self):
    lines = [ "<tag/>", "l1", ]
    expectedResult = [ "l1" ]
    expectedBlock = [ [ ] ]
    self.verify(lines, expectedResult, expectedBlock, None, allowClose = True)

  def test_parse_close_repl(self):
    lines = [ "<tag/>", ]
    expectedResult = [ "r1" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "r1" ] ]
    self.verify(lines, expectedResult, expectedBlock, replacementBlocks, allowClose = True)

  def test_parse_mixed(self):
    lines = [ "<tag/>", "<tag>", "l1", "l2", "</tag>", "l3" ]
    expectedResult = [ "r1", "r2", "r3", "l3" ]
    expectedBlock = [ [ ], [ "l1", "l2" ] ]
    replacementBlocks = [ [ "r1" ], [ "r2", "r3" ] ]
    self.verify(lines, expectedResult, expectedBlock, replacementBlocks, allowClose = True)

  def test_parse_no_close2(self):
    lines = [ "<tag>", "l1", "<tag>", "l3", "</tag>" ]
    with self.assertRaises(SystemExit) as cm:
      parseStandaloneTagBlock(lines, "tag", None)
    self.assertEqual(cm.exception.code, 1)

  def test_parse1(self):
    lines = [ "l0", "<tag>", "l2", "l3", "</tag>", "l4", ]
    expectedResult = [ "l0", "l4" ]
    expectedBlock = [ [ "l2", "l3" ] ]
    self.verify(lines, expectedResult, expectedBlock, None)

  def test_parse1_with_args(self):
    lines = [ "l0", "<tag rend='xxx'>", "l2", "l3", "</tag>", "l4", ]
    expectedResult = [ "l0", "l4" ]
    expectedBlock = [ [ "l2", "l3" ] ]
    self.verify(lines, expectedResult, expectedBlock, None, open=" rend='xxx'")

  def test_parse_close_with_args(self):
    lines = [ "l0", "<tag rend='xxx'/>", "l1", ]
    expectedResult = [ "l0", "l1" ]
    expectedBlock = [ [ ] ]
    self.verify(lines, expectedResult, expectedBlock, None, open=" rend='xxx'", allowClose = True)

  def test_parse_close_with_args_repl(self):
    lines = [ "l0", "<tag rend='xxx'/>", "l1", ]
    expectedResult = [ "l0", "r1", "r2", "l1" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "r1", "r2" ] ]
    self.verify(lines, expectedResult, expectedBlock, replacementBlocks,
        open=" rend='xxx'", allowClose = True)

  def test_parse2(self):
    lines = [
      "l0", "<tag>", "l2", "l3", "</tag>", "l4", "<tag>", "l6", "</tag>", "l7"
    ]
    expectedResult = [ "l0", "l4", "l7" ]
    expectedBlocks = [ [ "l2", "l3" ], [ "l6" ] ]
    self.verify(lines, expectedResult, expectedBlocks, None)

  def test_parse2_replace(self):
    lines = [
      "l0", "<tag>", "l2", "l3", "</tag>", "l4", "<tag>", "l6", "</tag>", "l7"
    ]
    expectedResult = [ "l0", "R1", "R2", "R3", "l4", "R4", "l7" ]
    expectedBlocks = [ [ "l2", "l3" ], [ "l6" ] ]
    replacementBlocks = [ [ "R1", "R2", "R3" ], [ "R4" ] ]
    self.verify(lines, expectedResult, expectedBlocks, replacementBlocks)

  def verifyEmbedded(self, lines, expectedResult, expectedBlocks, replacementBlocks, open=""):
    self.callbackN = -1
    def f(l0, block):
      self.callbackN += 1
      self.assertEquals(l0, open)
      self.assertSequenceEqual(block, expectedBlocks[self.callbackN])
      return replacementBlocks[self.callbackN] if replacementBlocks != None else []

    parseEmbeddedTagBlock(lines, "tag", f)
    self.assertSequenceEqual(lines, expectedResult)

  def test_embedded_sameline(self):
    lines = [ "<tag></tag>", ]
    expectedResult = [ "" ]
    expectedBlock = [ [ ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_leading(self):
    lines = [ "b4<tag></tag>", ]
    expectedResult = [ "b4" ]
    expectedBlock = [ [ ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_trailing(self):
    lines = [ "<tag></tag>after", ]
    expectedResult = [ "after" ]
    expectedBlock = [ [ ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_both(self):
    lines = [ "b4<tag></tag>after", ]
    expectedResult = [ "b4after" ]
    expectedBlock = [ [ ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_both_content(self):
    lines = [ "b4<tag>blah</tag>after", ]
    expectedResult = [ "b4after" ]
    expectedBlock = [ [ "blah" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_twice(self):
    lines = [ "b4<tag>tc1</tag>after<tag>tc2</tag>", ]
    expectedResult = [ "b4after" ]
    expectedBlock = [ [ "tc1" ], [ "tc2" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_twice_trail(self):
    lines = [ "b4<tag>tc1</tag>after<tag>tc2</tag>aftermath", ]
    expectedResult = [ "b4afteraftermath" ]
    expectedBlock = [ [ "tc1" ], [ "tc2" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_sameline_twice_repl(self):
    lines = [ "b4<tag>tc1</tag>after<tag>tc2</tag>aftermath", ]
    expectedResult = [ "b4R1afterR2aftermath" ]
    expectedBlock = [ [ "tc1" ], [ "tc2" ] ]
    replacementBlocks = [ [ "R1" ], [ "R2" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_empty(self):
    lines = [ "<tag>", "</tag>", ]
    expectedResult = [ "", "" ]
    expectedBlock = [ [ "" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_twoline_empty_leading(self):
    lines = [ "b4<tag>", "</tag>", ]
    expectedResult = [ "b4", "" ]
    expectedBlock = [ [ "" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_twoline_empty_trailing(self):
    lines = [ "l0", "b4<tag>", "</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "after", "l4" ]
    expectedBlock = [ [ "" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_twoline_l1trail_trailing(self):
    lines = [ "l0", "b4<tag>xx", "</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "after", "l4" ]
    expectedBlock = [ [ "xx" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_twoline_l2trail_trailing(self):
    lines = [ "l0", "b4<tag>", "yy</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "after", "l4" ]
    expectedBlock = [ [ "yy" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_twoline_l1_l2trail_trailing(self):
    lines = [ "l0", "b4<tag>xx", "yy</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "after", "l4" ]
    expectedBlock = [ [ "xx", "yy" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  def test_embedded_multiline_trailing(self):
    lines = [ "l0", "b4<tag>", "l2", "</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "after", "l4" ]
    expectedBlock = [ [ "l2" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, None)

  # <tag></tag>; repl=R => block=[], R
  # <tag></tag>after; repl=R => block=[], Rafter
  # b4<tag></tag>; repl=R => block=[], b4R
  # b4<tag></tag>after; repl=R => block=[], b4Rafter

  def test_embedded_empty_empty_repl(self):
    lines = [ "l0", "<tag></tag>", "l4" ]
    expectedResult = [ "l0", "R1", "l4" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_empty_after_repl(self):
    lines = [ "l0", "<tag></tag>after", "l4" ]
    expectedResult = [ "l0", "R1after", "l4" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_empty_b4_repl(self):
    lines = [ "l0", "b4<tag></tag>", "l4" ]
    expectedResult = [ "l0", "b4R1", "l4" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_empty_b4_after_repl(self):
    lines = [ "l0", "b4<tag></tag>after", "l4" ]
    expectedResult = [ "l0", "b4R1after", "l4" ]
    expectedBlock = [ [ ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  # <tag>\n</tag>; repl=R => block=[""], R
  # <tag>\n</tag>after; repl=R => block=[""], R\nafter
  # b4<tag>\n</tag>; repl=R => block=[""], b4\nR
  # b4<tag>\n</tag>after; repl=R => block=[""], b4\nR\nafter
  # b4<tag>x\n</tag>after; repl=R => block=["x"], b4\nR\nafter
  # b4<tag>x\ny</tag>after; repl=R => block=["x","y"], b4\nR\nafter

  def test_embedded_twoline_empty_empty_repl(self):
    lines = [ "l0", "<tag>", "l2", "</tag>", "l4" ]
    expectedResult = [ "l0", "R1", "l4" ]
    expectedBlock = [ [ "l2" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_b4_empty_repl(self):
    lines = [ "l0", "b4<tag>", "l2", "</tag>", "l4" ]
    expectedResult = [ "l0", "b4", "R1", "l4" ]
    expectedBlock = [ [ "l2" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_empty_after_repl(self):
    lines = [ "l0", "<tag>", "l2", "</tag>after", "l4" ]
    expectedResult = [ "l0", "R1", "after", "l4" ]
    expectedBlock = [ [ "l2" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_b4_after_repl(self):
    lines = [ "l0", "b4<tag>", "l2", "</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "R1", "after", "l4" ]
    expectedBlock = [ [ "l2" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_b4_after_repl_x(self):
    lines = [ "l0", "b4<tag>x", "l2", "</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "R1", "after", "l4" ]
    expectedBlock = [ [ "x", "l2" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_b4_after_repl_y(self):
    lines = [ "l0", "b4<tag>", "l2", "y</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "R1", "after", "l4" ]
    expectedBlock = [ [ "l2", "y" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

  def test_embedded_twoline_b4_after_repl_xy(self):
    lines = [ "l0", "b4<tag>x", "l2", "y</tag>after", "l4" ]
    expectedResult = [ "l0", "b4", "R1", "after", "l4" ]
    expectedBlock = [ [ "x", "l2", "y" ] ]
    replacementBlocks = [ [ "R1" ] ]
    self.verifyEmbedded(lines, expectedResult, expectedBlock, replacementBlocks)

def parseTagAttributes(tag, arg, legalAttributes = None):
  try:  # TODO: Move this up
    attributes = parseTagAttributes1(arg)

    if legalAttributes != None:
      for attribute in attributes.keys():
        if not attribute in legalAttributes:
          raise Exception("Keyword " + attribute + ": Unknown keyword in " + arg)

  except Exception as e:
    fatal(tag + ": " + str(e))
  return attributes

# A tag looks like:
#   <tag key1='value1' key2="value2" ...>
# where whatever quote starts a value, must end a value
# Returns { 'key1' : 'value1', 'key2' : 'value2' ... }
def parseTagAttributes1(arg):
  attributes = collections.OrderedDict()
  while True:
    keyword, sep, rest = arg.partition('=')
    # Done?
    if not sep:
      break
    keyword = keyword.lstrip()
    quote = rest[0]
    if quote not in [ "'", '"' ]:
      raise Exception("Keyword {}: value is not quoted in {}".format(keyword, arg))
    off = rest.find(quote, 1)
    if off == -1:
      raise Exception("keyword {}: value has no terminating quote in {}".format(keyword, arg))
    value = rest[1:off]
    attributes[keyword] = value
    if off+1 == len(rest):
      break
    arg = rest[off+1:].lstrip()
  #sys.stdout.write("result={}".format(attributes))
  return attributes

def parseOption(tag, arg, legalOptions = None):
  try:
    options = parseOption1(arg)

    if legalOptions != None:
      for option in options.keys():
        if not option in legalOptions:
          raise Exception("Option " + option + ": Unknown option in " + arg)
  except Exception as e:
    fatal(tag + ": " + str(e))
  return options


# Parse a single attribute list
# e.g. rend='mr:5em mb:1em italic'
# would parse into
#  { 'mr' : '5em', 'mb' : '1em', 'italic' : '' }
def parseOption1(arg):
  options = collections.OrderedDict()
  arg = arg.strip()
  while True:
    while len(arg) > 0 and (arg[0] == ';' or arg[0] == ' '):
      arg = arg[1:]
    m = re.match("^([^ :;]*)([ :;])(.*)$", arg)
    if not m:
      # Rest of string is keyword
      if arg != "":
        options[arg] = ""
      break

    keyword = m.group(1)
    sep = m.group(2)
    rest = m.group(3)

    if sep == ':':
      # Can terminate the option with space, semi, or end-of string
      off1= rest.find(' ')
      off2 = rest.find(';')
      if off1 == -1:
        off = off2
      elif off2 == -1:
        off = off1
      elif off1 < off2:
        off = off1
      else:
        off = off2
      if off == -1:
        off = len(rest)
      value = rest[0:off]
      options[keyword] = value
      arg = rest[off:]
    else:
      options[keyword] = ''
      arg = rest

  #sys.stdout.write("result={}\n".format(options))
  return options

class TestParseTagAttributes(unittest.TestCase):
  def test_1(self):
    assert parseTagAttributes1("k1='a' k2='b'") == { 'k1':'a', 'k2':'b' }
  def test_EmbeddedOtherQuote(self):
    assert parseTagAttributes1("k1='aa\"bc'") == { 'k1':'aa"bc' }
  def test_Empty(self):
    assert parseTagAttributes1("") == { }
  def test_SpacesOnly(self):
    assert parseTagAttributes1("   ") == { }
  def test_SpaceInKey(self):
    assert parseTagAttributes1("   kxx ky='a' ") == { "kxx ky" : 'a' }
  def test_NoCloseQuote1(self):
    self.assertRaises(Exception, parseTagAttributes1, "   k1='a ")
  def test_NoCloseQuote(self):
    assert parseTagAttributes1("   k1='a k2='b' ") == { "k1" : "a k2=" }
  def test_NoQuote(self):
    self.assertRaises(Exception, parseTagAttributes1, "k1=a k2='b'")

  def test_WithAtt(self):
    assert parseTagAttributes("x", "k1='a' k2='b'", [ 'k1', 'k2' ]) == { 'k1':'a', 'k2':'b' }
  def test_WithAttBad(self):
    with self.assertRaises(SystemExit) as cm:
      parseTagAttributes("x", "k1='a' kx='b'", [ 'k1', 'k2' ]) == { 'k1':'a', 'k2':'b' }
    self.assertEqual(cm.exception.code, 1)

  def test_Option(self):
    assert parseOption1('mr:5em   mb:1em italic') ==  { 'mr' : '5em', 'mb' : '1em', 'italic' : '' }
  def test_OptionSemi(self):
    self.assertEqual(parseOption1('mr:5em;  mb:1em;italic'), { 'mr' : '5em', 'italic' : '', 'mb' : '1em' })
  def test_OptionEmpty(self):
    assert parseOption1('') == { }
  def test_OptionSpacesOnly(self):
    assert parseOption1('') == { }
  def test_OptionSingleNoEq(self):
    assert parseOption1('italic') == { 'italic' : '' }
  def test_OptionNoEqLeading(self):
    assert parseOption1('poetry mt:5em') == { 'poetry' : '', 'mt' : '5em' }
  def test_OptionSingleNoEqTrailingSp(self):
    assert parseOption1('italic  ') == { 'italic' : '' }
  def test_OptionNoEqSp(self):
    assert parseOption1('   mt:33    italic  ') == { 'mt' : '33', 'italic' : '' }
  def test_OptionSingleNoEqLeadingSp(self):
    assert parseOption1('  italic') == { 'italic' : '' }
  def test_OptionSingleEq(self):
    assert parseOption1('mr:4em') == { 'mr' : '4em' }
  def test_OptionSingleEqTrailingSp(self):
    assert parseOption1('mr:4em   ') == { 'mr' : '4em' }
  def test_OptionSingleEqLeadingSp(self):
    assert parseOption1('  mr:4em') == { 'mr' : '4em' }
  def test_OptionSingleEqTrailingSp(self):
    assert parseOption1('mr:4em   ') == { 'mr' : '4em' }
  def test_OptionMultipleSpInMiddle(self):
    assert parseOption1('mr:4em   ml:88em') == { 'mr' : '4em', 'ml' : '88em' }
  def test_OptionMultipleInMiddle(self):
    assert parseOption1('mr:4em ;;  ml:88em') == { 'mr' : '4em', 'ml' : '88em' }
