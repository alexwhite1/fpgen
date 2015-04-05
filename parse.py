#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import re
import sys
import collections
from msgs import fatal

# Extract the text on a line which looks like <tag>XXXX</tag>
def parseLineEntry(tag, line):
  pattern = "^<" + tag + "\s*(.*?)>(.*)</" + tag + ">$"
  m = re.match(pattern, line)
  if not m:
    fatal("Incorrect line: " + line)
  return m.group(1), m.group(2)

# Look for <tag> ... </tag> where the tags are on standalone lines.
# As we find each such block, invoke the function against it
def parseStandaloneTagBlock(lines, tag, function):
  i = 0
  startTag = "<" + tag
  endTag = "</" + tag + ">"
  regex = re.compile(startTag + "(.*?)>")
  while i < len(lines):
    m = regex.match(lines[i])
    if not m:
      i += 1
      continue

    openLine = lines[i]
    openArgs = m.group(1)
    block = []

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
  def setUp(self):
    from fpgen import Book
    self.book = Book(None, None, None, None)

  def verify(self, lines, expectedResult, expectedBlocks, replacementBlocks, open=""):
    self.callbackN = -1
    def f(l0, block):
      self.callbackN += 1
      self.assertEquals(l0, open)
      self.assertSequenceEqual(block, expectedBlocks[self.callbackN])
      return replacementBlocks[self.callbackN] if replacementBlocks != None else []

    parseStandaloneTagBlock(lines, "tag", f)
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
