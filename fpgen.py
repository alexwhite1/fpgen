#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
from subprocess import call
import re, sys, string, os, shutil
import textwrap
import codecs
import platform
import unittest
from unittest.mock import MagicMock, Mock, call

import config

# 20140214 bugfix: handle mixed quotes in toc entry
#          added level='3' to headings for subsections
# 20140216 lg.center to allow mt/b decimal value
# 20140217 windows path bugfix; rend=block propogate error
# 20140220 switch mobi generator from ebook-convert to kindlegen
# 20140221 changes to OPT_PDF_ARGS
# 20140226 allows specifying .8em in addition to 0.8em margins
# 20140228 --disable-remove-fake-margins added to PDF and mobi
# 20140304 TESTING. wide spaces as nbsp. mobi from epub.
# 20140307 TESTING for Ross. XP compatibile build test.
# 20140316 added lg rend='right'
# 4.04     bugfix. illustration links. kindle added to !t.
#          --level1-toc "//h:h1" --level2-toc "//h:h2" added for epub
#          <br> in heading handled in text
# 4.05/6   epub margin user option. Alex's "nobreak" option
# 4.07     fractional thought breaks
# 4.08     overline <ol>line over text</ol>
# 4.09     tags in <lit> blocks
# 4.10     alternate comment form "//"
# 4.11     <br><br> converts to "—" in tablet versions
# 4.12     meta line restrictions imposed for PGC
# 4.13     <hang> tag (alex)
# 4.14     allow <pn=''> anywhere on line
# 4.15     used &ensp; instead of &nbsp; as leader for indented poetry lines
# 4.16     drop cap property to use an image
# 4.17     pagenum->pageno, so not part of copy/paste
# 4.17A    <l rend='right'> now works like <l rend='mr:0'>
# 4.17B    level 4 headers
# 4.17C    Error msg for word >75 chars; error msg for text output table w/o width
# 4.18     Use nbsp instead of ensp for ellipsis
# 4.19     Uppercase <sc> output for text; add sc=titlecase option
# 4.19a    Various text output table width bug fixes
# 4.20     Add <table> line drawing in text and html both
# 4.20a    Add <table> double-lines & column <span>ing
# 4.20b    text table bug fix
# 4.20c    empty line produce bars in text; spanned cols in html end in correct border
# 4.20d    table rule lines throw off count; add cell alignment
# 4.20e    Minor bug fix with trailing spaces in text output
# 4.21     Leading \<sp> not in <lg> is nbsp; also unicode nbsp(0xA0)
# 4.21a    Bug with level 4 headers
# 4.22     Text footnote output change to [#] same line
# 4.23     <drama> tag
# 4.23a    Fix bug from 4.22: <lg> starting a footnote (text output)
# 4.23b    Fix bug with gesperrt inside <sc>
# 4.23c    Fix pn_cover usage broken in 4.23
# 4.23d    Fix .verse-align-noindent with hang


"""

  fpgen.py

  Copyright 2014, Asylum Computer Services LLC
  Licensed under the MIT license:
  http://www.opensource.org/licenses/mit-license.php

  Roger Frank (rfrank@rfrank.net)

  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:

  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

# class to save user options
class userOptions(object):
  def __init__(self):
    self.opt = {}

  def addopt(self,k,v):
    # print("adding {}:{}".format(k, v))
    self.opt[k] = v

  def getopt(self,k):
    if k in self.opt:
      return self.opt[k]
    else:
      return ""

empty = re.compile("^$")

def dprint(level, msg):
  if int(config.debug) >= level:
    cprint("{}".format(msg))

# safe print of possible UTF-8 character strings on ISO-8859 terminal
def cprint(s):
  s = re.sub("◻"," ", s)
  t = "".join([x if ord(x) < 128 else '?' for x in s])
  print(t)

# Emit the UTF-8 chars as \uXXXX hex strings
def uprint(s):
  s = re.sub("◻"," ", s)
  t = "".join([x if ord(x) < 128 else ("\\u"+hex(ord(x))) for x in s])
  print(t)

def fatal(message):
  sys.stderr.write("fatal: " + message + "\n")
  exit(1)

# wrap string s, returns wrapped list
# parameters
#   lm left margin default=0
#   rm right margin default=0
#   li all lines but line 0 indent default = 0
#   l0 line 0 indent default=0
# notes
#   base line length is 72 - lm - rm - li
#   first line indent is lm + ti
#   subsequent lines indent is lm + li
#   gesperrt comes in with ◮ in for spaces.

def wrap2h(s, lm, rm, li, l0):  # 22-Feb-2014
  lines = []
  wrapper = textwrap.TextWrapper()
  wrapper.width = config.LINE_WIDTH - lm - rm
  wrapper.break_long_words = False
  wrapper.break_on_hyphens = False
  wrapper.initial_indent = l0 * ' '
  wrapper.subsequent_indent = li * ' '
  s = re.sub("—", "◠◠", s) # compensate long dash
  lines = wrapper.wrap(s)
  for i, line in enumerate(lines):
      lines[i] = re.sub("◠◠", "—", lines[i]) # restore dash
      lines[i] = re.sub("◮", " ", lines[i]) # restore spaces from gesperrt or ti
      lines[i] = " " * lm + lines[i]
  return lines

def wrap2(s, lm=0, rm=0, li=0, ti=0):  # 22-Feb-2014
  lines = []
  while re.search("<br\/>", s):
    m = re.search("(.*?)<br\/>(.*)", s)
    if m:
      lines += wrap2h(m.group(1).strip(), lm, rm, li, ti)
      s = m.group(2)
  lines += wrap2h(s.strip(), lm, rm, li, ti) # last or only piece to wrap
  return lines

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

class Book(object):
  wb = []
  supphd =[] # user's supplemental header lines

  def __init__(self, ifile, ofile, d, fmt):
    config.debug = d # numeric, 0=no debug, 1=function level, 2=line level
    self.debug = d # numeric, 0=no debug, 1=function level, 2=line level
    self.srcfile = ifile
    self.dstfile = ofile
    self.gentype = fmt
    self.back2 = -1 # loop detector
    self.back1 = -1
    self.poetryindent = 'left'
    self.italicdef = 'emphasis'

  # display (fatal) error and exit
  def fatal(self, message):
    sys.stderr.write("fatal: " + message + "\n")
    exit(1)

  # level is set by calling program and is compared to self.debug.
  # >= means print msg
  def dprint(self, level, msg):
    if int(self.debug) >= level:
      cprint("{}: {}".format(self.__class__.__name__, msg))

  numeral_map = tuple(zip(
      (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
      ('m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i')
  ))

  def int_to_roman(self,i):
      result = []
      for integer, numeral in self.numeral_map:
          count = i // integer
          result.append(numeral * count)
          i -= integer * count
      return ''.join(result)

  def roman_to_int(self,n):
      i = result = 0
      for integer, numeral in self.numeral_map:
          while n[i:i + len(numeral)] == numeral:
              result += integer
              i += len(numeral)
      return result

  # validate file as UTF-8
  def checkFile(self, fn):
    fileOk = True
    file = open(fn, 'rb')
    for i,line in enumerate(file):
      try:
        converted = line.decode('utf-8')
      except:
        if fileOk:
            cprint("fatal: file is not UTF-8")
            cprint("lines:")
        fileOk = False
        s = str(line)
        s = re.sub("^b'","",s)
        s = re.sub("'$","",s)
        s = re.sub(r"\\r","",s)
        s = re.sub(r"\\n","",s)
        cprint("  {}: ".format(i) + s)
    file.close()
    if not fileOk:
        exit(1)

  # load file from specified source file
  def loadFile(self, fn):
    self.dprint(1, "loadFile")
    self.checkFile(fn)
    try:
      wbuf = open(fn, "r", encoding='UTF-8').read()
      self.wb = wbuf.split("\n")
      t = ":".join("{0:x}".format(ord(c)) for c in self.wb[0])
      if t[0:4] == 'feff':
        self.wb[0] = self.wb[0][1:]
    except UnicodeDecodeError:
      self.fatal("loadFile: source file {} not UTF-8".format(fn))
    except:
      self.fatal("loadFile: cannot open source file {}".format(fn))
    self.wb.insert(0,"")
    self.wb = [s.rstrip() for s in self.wb]

    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("//"): # line starts with "//"
        del self.wb[i]
        continue
      if self.wb[i].startswith("<!--") and self.wb[i].find("-->") > 0:
        del self.wb[i]
        continue
      # multi-line
      if self.wb[i].startswith("<!--"):
        while not re.search("-->", self.wb[i]):
          del self.wb[i]
          continue
        del self.wb[i]
      # ANSI standard
      if self.wb[i].startswith("/*") and self.wb[i].endswith("*/"):
        # entire line is comment
        del self.wb[i]
        continue
      if re.search(r"\/\*.*?\*\/", self.wb[i]): # comment as part of line
        self.wb[i] = re.sub(r"\/\*.*?\*\/", "", self.wb[i])
        self.wb[i] = self.wb[i].rstrip()
        continue
      # multi-line (must be last)
      if self.wb[i].startswith("/*"):
        while not re.search("\*\/", self.wb[i]):
          del self.wb[i]
          continue
        del self.wb[i] # closing comment line
      i += 1

    # page number tags
    # force page numbers to separate line and to single-quote version
    i = 0
    regex = re.compile(r"<pn=[\"'](.+?)[\"']>")
    regex1 = re.compile("^(.*?)(\s?<pn='.*?'>\s?)(.*)$")
    while i < len(self.wb):
      self.wb[i] = regex.sub(r"<pn='\1'>", self.wb[i])
      m = regex1.search(self.wb[i])
      if m:
        if m.group(1) != "" and m.group(3) != "":
          t = [m.group(1), m.group(2).strip(), m.group(3)]
          self.wb[i:i+1] = t
          i += 2
        if m.group(1) != "" and m.group(3) == "":
          t = [m.group(1), m.group(2).strip()]
          self.wb[i:i+1] = t
          i += 1
        if m.group(1) == "" and m.group(3) != "":
          t = [m.group(2).strip(), m.group(3)]
          self.wb[i:i+1] = t
          i += 1
      i += 1
      
    # process optional formatting (DEPRECATED)
    # <I>..</I> will be italics only in media that can render it natively.
    # <B>..</B> will be bold only in media that can render it natively.
    # both are ignored in Text
    #
    i = 0
    while i < len(self.wb):
      if self.gentype == 't':
        self.wb[i] = re.sub("<\/?I>", "", self.wb[i])
        self.wb[i] = re.sub("<\/?B>", "", self.wb[i])
      else:
        self.wb[i] = re.sub("<I>", "<i>", self.wb[i])
        self.wb[i] = re.sub("<B>", "<b>", self.wb[i])
        self.wb[i] = re.sub("<\/I>", "</i>", self.wb[i])
        self.wb[i] = re.sub("<\/B>", "</b>", self.wb[i])
      i += 1

    # process conditional source directives
    self.dprint(1,"conditionals")
    def oneIfBlock(openTag, block):
      m = re.match(" *type=['\"](.*?)['\"]", openTag)
      if not m:
        fatal("Badly formatted <if> conditional")

      conditional_type = m.group(1)
      if conditional_type == "!t": # 08-Sep-2013
        conditional_type = 'hepk' # 26-Mar-2014
      if self.gentype in conditional_type:
        return block
      else:
        return []

    parseStandaloneTagBlock(self.wb, "if", oneIfBlock)

    # 19-Nov-2013
    i = 0
    self.supphd = []
    regex = re.compile("<lit section=['\"]head['\"]>")
    while i < len(self.wb):
      if regex.match(self.wb[i]):
        del(self.wb[i])
        while not re.match(r"<\/lit>", self.wb[i]):
          self.supphd.append(self.wb[i])
          del(self.wb[i])
        del(self.wb[i])
        i -= 1
      i += 1

    # 29-Oct-2013 literals after conditionals
    i = 0
    inliteral = False
    while i < len(self.wb):
      if self.wb[i].startswith("<lit"):
        inliteral = True
        i += 1
        continue
      if self.wb[i].startswith("</lit>"):
        inliteral = False
        i += 1
        continue
      if inliteral:
        self.wb[i] = re.sub(r"<",'≼', self.wb[i]) # literal open tag marks
        self.wb[i] = re.sub(r">",'≽', self.wb[i]) # literal close tag marks
      i += 1

    # combine multi-line <caption>...</caption> lines into one.
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("<caption>") and not re.search("<\/caption>", self.wb[i]):
        while not re.search("<\/caption>", self.wb[i]):
          self.wb[i] = self.wb[i] + " " + self.wb[i+1]
          del self.wb[i+1]
      i += 1

    # add id to unadorned heading lines
    self.dprint(1,"headings+id")
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("<heading"):
        if not re.search("id=", self.wb[i]):
          genid = "t{}".format(i)
          self.wb[i] = re.sub("<heading", "<heading id='{}'".format(genid), self.wb[i])
      i += 1

    # ensure heading has a blank line before
    self.dprint(1,"headings+spacing")
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("<heading"):
        if not empty.match(self.wb[i-1]):
          t = self.wb[i]
          self.wb[i:i+1] = ["", t]
          i += 1
      i += 1

    # ensure line group has a blank line before
    self.dprint(1,"line group+spacing")
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("<lg"):
        if not empty.match(self.wb[i-1]):
          t = self.wb[i]
          self.wb[i:i+1] = ["", t]
          i += 1
      i += 1

    # ensure line group has a blank line after
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("</lg"):
        if not empty.match(self.wb[i+1]):
          t = self.wb[i]
          self.wb[i:i+1] = [t,""]
          i += 1
      i += 1

    # ensure standalone illustration line has blank lines before, after
    i = 0
    regex = re.compile("<illustration.*?\/>")
    while i < len(self.wb):
      if regex.match(self.wb[i]):
        t = self.wb[i]
        u = []
        if not empty.match(self.wb[i-1]):
          u.append("")
        u.append(t)
        if not empty.match(self.wb[i+1]):
          u.append("")
        self.wb[i:i+1] = u
        i += len(u)
      i += 1

    # ensure illustration line has blank lines before
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("<illustration"):
        t = self.wb[i]
        u = []
        if not empty.match(self.wb[i-1]):
          u.append("")
        u.append(t)
        self.wb[i:i+1] = u
        i += len(u)
      i += 1

    # illustration close
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("</illustration>"):
        t = self.wb[i]
        u = []
        u.append(t)
        if not empty.match(self.wb[i+1]):
          u.append("")
        self.wb[i:i+1] = u
        i += len(u)
      i += 1

    # map drop caps requests
    for i, line in enumerate(self.wb):
      self.wb[i] = re.sub("<drop>", "☊", self.wb[i])
      self.wb[i] = re.sub("<\/drop>", "☋", self.wb[i])

    # courtesy remaps mr:0 to mr:0em, etc. for all formats
    for i,line in enumerate(self.wb):
      self.wb[i] = re.sub("mr:0", "mr:0em", self.wb[i])
      self.wb[i] = re.sub("ml:0", "ml:0em", self.wb[i])
      self.wb[i] = re.sub("mt:0", "mt:0em", self.wb[i])
      self.wb[i] = re.sub("mb:0", "mb:0em", self.wb[i])
      self.wb[i] = re.sub("<br>", "<br/>", self.wb[i])

    # normalize rend format to have trailing semicolons
    # honor <lit>...</lit> blocks
    in_pre = False
    for i,line in enumerate(self.wb):
      if "<lit" in line:
        in_pre = True
      if "</lit" in line:
        in_pre = False
      m = re.search('rend="(.*?)"', line)
      if m:
        self.wb[i] = re.sub('rend=".*?"', "rend='{}'".format(m.group(1)), self.wb[i])
      m = re.search("rend='(.*?)'", self.wb[i])
      if not in_pre and m:
        therend = m.group(1)
        therend = re.sub(" ",";", therend)
        therend += ";"
        therend = re.sub(";;", ";", therend)
        self.wb[i] = re.sub("rend='.*?'", "rend='{}'".format(therend), self.wb[i])

    # isolate <pn to separate lines
    i = 0
    regex1 = re.compile("^<pn=[\"'].*?[\"']>$")
    regex2 = re.compile("^(.*?)(<pn=[\"'].*?[\"']>)(.*?)$")
    while i < len(self.wb):
      # standalone pn
      if regex1.match(self.wb[i]):
        i += 1
        continue
      m = regex1.match(self.wb[i])
      if m:
        t = []
        if not empty.match(m.group(1)):
          t.append(m.group(1))
        t.append(m.group(2))
        if not empty.match(m.group(3)):
          t.append(m.group(3))
        self.wb[i:i+1] = t
        i += 2
      i += 1

    # process macros
    self.dprint(1,"macros")
    macro = {}

    # define macros and save
    i = 0
    regex = re.compile("<macro (.*?)=\"(.*?)\"\/?>")
    while i < len(self.wb):
      m = regex.match(self.wb[i])
      if m:
        macroName = m.group(1)
        macroDef = m.group(2)
        macro[macroName] = macroDef
        del self.wb[i] # macro has been stored
        i -= 1
      i += 1

    # apply macros to text
    i = 0
    regex = re.compile("%([^;].*?)%")
    while i < len(self.wb):
      m = regex.search(self.wb[i])
      while m: # found a macro
        if m.group(1) in macro: # is this in our list of macros already defined?
          self.wb[i] = re.sub("%{}%".format(m.group(1)), macro[m.group(1)], self.wb[i], 1)
          m = re.search("%(.*?)%", self.wb[i])
        else:
          self.fatal("macro %{}% undefined in line\n{}".format(m.group(1), self.wb[i]))
      i += 1

    # ensure spacing around standalone <l> or <l/> elements that are not in a line group
    i = 0
    inLineGroup = False
    while i < len(self.wb):
      if self.wb[i].startswith("<lg"):
          inLineGroup = True
      if self.wb[i].startswith("</lg"):
          inLineGroup = False
      if inLineGroup:
          i += 1
          continue
      m = re.search("<l[^i]", self.wb[i])
      if m:
        # if the line before this isn't blank or another <l element, add a blank line before
        if not empty.match(self.wb[i-1]) and not re.match("^<l", self.wb[i-1]):
          self.wb[i:i+1] = ["", self.wb[i]]
          i += 1
        # if the line after this isn't blank or another <l element, add a blank line after
        if not empty.match(self.wb[i+1]) and not re.match("^<l", self.wb[i+1]):
          self.wb[i:i+1] = [self.wb[i],""]
          i += 1
      i += 1

    # display user-supplied warnings (<warn>...</warn>)
    i = 0
    regex = re.compile("<warning>(.*?)<\/warning>")
    while i < len(self.wb):
      m = regex.match(self.wb[i])
      if m:
        cprint("warning: {}".format(m.group(1)))
        del self.wb[i]
      i += 1

    # format footnotes to standard form 08-Sep-2013
    i = 0
    fnc = 1 # footnote counter to autonumber if user has used '#'
    reOneLine = re.compile("(<footnote id=[\"'].*?[\"']>)(.+?)(<\/footnote>)")
    reStart = re.compile("(<footnote id=[\"'].*?[\"']>)(.+?)$")
    reStartWOText = re.compile("<footnote id=[\"'].*?[\"']>$")
    reEnd = re.compile("^(.+?)(<\/footnote>)")
    while i < len(self.wb):

      # all on one line
      m = reOneLine.match(self.wb[i])
      if m:
        mg1 = m.group(1).strip()
        mg2 = m.group(2).strip()
        mg3 = m.group(3).strip()
        m = re.search("id=[\"']#[\"']", mg1)
        if m:
          mg1 = "<footnote id='{}'>".format(fnc)
          fnc += 1
        self.wb[i:i+1] = [mg1, mg2, mg3]
        i += 2

      # starts but doesn't end on this line
      m = reStart.match(self.wb[i])
      if m:
        mg1 = m.group(1).strip()
        mg2 = m.group(2).strip()
        m = re.search("id=[\"']#[\"']", mg1)
        if m:
          mg1 = "<footnote id='{}'>".format(fnc)
          fnc += 1
        self.wb[i:i+1] = [mg1, mg2]
        i += 1

      # starts without text on this line
      m = reStartWOText.match(self.wb[i])
      if m:
        m = re.search("id=[\"']#[\"']", self.wb[i])
        if m:
          self.wb[i] = "<footnote id='{}'>".format(fnc)
          fnc += 1
        i += 1

      # ends but didn't start on this line
      m = reEnd.match(self.wb[i])
      if m:
        self.wb[i:i+1] = [m.group(1).strip(),m.group(2).strip()]
        i += 1

      i += 1


  # save file to specified dstfile
  def saveFile(self, fn):
    self.dprint(1,"saveFile")
    if os.linesep == "\r\n":
      self.dprint(1, "running on Win machine")
      lineEnd = "\n"
    else:
      self.dprint(1, "running on Mac/Linux machine")
      lineEnd = "\r\n"
    f1 = open(fn, "w", encoding='utf-8')
    for index,t in enumerate(self.wb):
        f1.write( "{:s}{}".format(t,lineEnd) )
    f1.close()

  # snapshot to named file and continue
  def snap(self, fn):
    f1 = open(fn, "w", encoding='utf-8')
    if os.linesep == "\r\n":
      for index,t in enumerate(self.wb):
        f1.write( "{:s}\n".format(t) )
    else:
      for index,t in enumerate(self.wb):
        f1.write( "{:s}\r\n".format(t) )
    f1.close()

  # bailout after saving working buffer
  def bailout(self):
    self.dprint(1,"bailout")
    f1 = open("bailout.txt", "w", encoding='utf-8')
    for index,t in enumerate(self.wb):
      f1.write( "{:s}\n".format(t) )
    f1.close()
    exit(1)

  # loop detector
  def checkLoop(self, i, c):
    if i == self.back1 and i == self.back2:
      self.fatal("loop detected at line {}: {} (referrer: {})".format(i, self.wb[i], c))
    self.back2 = self.back1
    self.back1 = i

  def __str__(self):
    return "fpgen"

# end of class Book

def parseTablePattern(line):
  # pull the pattern
  m = re.search("pattern=[\"'](.*?)[\"']", line)
  if not m:
    fatal("No pattern= option to table: " + line)
  tpat = m.group(1)

  cols = []

  list = tpat.split()

  for oneCol in list:
    col = Col()
    cols.append(col)
    off = 0
    n = len(oneCol)

    # Each column is |*[lrc]#*|*

    # Parse leading |
    c = oneCol[off]
    if c == '#' or c == '|':
      col.lineBeforeStyle = c
      while oneCol[off] == c:
        col.lineBefore += 1
        off += 1
        if off == n:
          fatal("Incorrect table specification " + oneCol + " inside " + line)
      # Double line needs to be wider or you can't see it!
      if col.lineBeforeStyle == '#':
        col.lineBefore *= 4

    # Parse column position
    if oneCol[off] == 'c':
      col.align = "center"
    elif oneCol[off] == 'l':
      col.align = "left"
    elif oneCol[off] == 'r':
      col.align = "right"
    off += 1

    # Does the column have a user-specified width?
    col.userWidth = False
    col.width = 0
    if off < n:
      # Yes, parse the user-specified width
      digOff = off
      while oneCol[off].isdigit():
        off += 1
        if off == n:
          break
      if digOff != off:
        col.userWidth = True
        col.width = int(oneCol[digOff:off])

      if off < n:
        # Parse trailing |
        c = oneCol[off]
        if c == '#' or c == '|':
          col.lineAfterStyle = c
          while oneCol[off] == c:
            col.lineAfter += 1
            off += 1
            if off == n:
              break
          # Double line needs to be wider or you can't see it!
          if col.lineAfterStyle == '#':
            col.lineAfter *= 4

        if off != n:
          fatal("Incorrect table specification " + oneCol + " inside " + line)

    #self.dprint(1, "col: " + str(col))

  if len(cols) == 0:
    fatal("No table columns found in pattern " + line)

  cols[len(cols)-1].isLast = True
  for n, col in enumerate(cols):
    if col.isLast:
      col.lineBetween = col.lineAfter
    else:
      col.lineBetween = col.lineAfter + cols[n+1].lineBefore

  return cols

class Col:
  def __init__(self):
    self.userWidth = 0
    self.width = 0
    self.align = ""
    self.lineBefore = 0
    self.lineAfter = 0
    self.lineBetween = 0
    self.lineBeforeStyle = '|'
    self.lineAfterStyle = '|'
    self.isLast = False

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  def __str__(self):
    return str(self.__dict__)
#    return str(self.userWidth) + ":" + \
#      str(self.width) + ":" + \
#      self.align + ":" + \
#      str(self.lineBefore) + ":" + \
#      str(self.lineAfter)

class TestParseTableColumn(unittest.TestCase):
  expect = Col()
  expect.align = 'right';
  expect.isLast = True;

  def test_empty(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("pattern=''")
    self.assertEqual(cm.exception.code, 1)

  def test_nopattern(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("atern='r c l'")
    self.assertEqual(cm.exception.code, 1)

  def test_simple(self):
    assert parseTablePattern("pattern='r'") == [ TestParseTableColumn.expect ]

  def test_simple1(self):
    assert parseTablePattern("pattern='   r   '") == [ TestParseTableColumn.expect ]

  def test_simple2(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("pattern='   rr   '")
    self.assertEqual(cm.exception.code, 1)

  def test_simple3(self):
    result = parseTablePattern("pattern='   r   l33 c5 '")
    assert len(result) == 3
    assert result[0].align == "right"
    assert result[1].align == "left"
    assert result[2].align == "center"
    assert result[0].width == 0
    assert result[1].width == 33
    assert result[2].width == 5
    assert result[0].userWidth == False
    assert result[1].userWidth == True
    assert result[2].userWidth == True
    assert result[0].isLast == False
    assert result[1].isLast == False
    assert result[2].isLast == True

  def test_bar1(self):
    with self.assertRaises(SystemExit) as cm:
      result = parseTablePattern("pattern='|'")
    self.assertEqual(cm.exception.code, 1)

  def test_bar2(self):
    result = parseTablePattern("pattern='|r| c55||| |||l ||r99||'")
    assert len(result) == 4
    assert result[0].lineBefore == 1
    assert result[0].lineAfter == 1
    assert result[0].lineBeforeStyle == '|'
    assert result[0].lineAfterStyle == '|'
    assert result[1].lineBefore == 0
    assert result[1].lineAfter == 3
    assert result[1].lineBeforeStyle == '|'
    assert result[1].lineAfterStyle == '|'
    assert result[2].lineBefore == 3
    assert result[2].lineAfter == 0
    assert result[2].lineBeforeStyle == '|'
    assert result[2].lineAfterStyle == '|'
    assert result[3].lineBefore == 2
    assert result[3].lineAfter == 2
    assert result[3].lineBeforeStyle == '|'
    assert result[3].lineAfterStyle == '|'

  def test_bar3(self):
    with self.assertRaises(SystemExit) as cm:
      result = parseTablePattern("pattern='|r|c'")
    self.assertEqual(cm.exception.code, 1)

  def test_hash(self):
    result = parseTablePattern("pattern='r# #l'")
    assert len(result) == 2
    assert result[0].lineAfter == 4
    assert result[0].lineAfterStyle == '#'
    assert result[1].lineBefore == 4
    assert result[1].lineBeforeStyle == '#'

# ===== class Lint ============================================================

class Lint(Book):

  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)

  def process(self):
    inLineGroup = False
    reports = []
    for i,line in enumerate(self.wb):

      if re.match("<tb\/?>", line) and (not empty.match(self.wb[i+1]) or not empty.match(self.wb[i-1])):
        reports.append("non-isolated <tb> tag:\nline number: {}".format(i))

      if re.match("<pb\/?>", line) and (not empty.match(self.wb[i+1]) or not empty.match(self.wb[i-1])):
        reports.append("non-isolated <pb> tag:\nline number: {}".format(i))

      # all lines stand alone
      if re.match("<l[> ]", line) and not re.search("<\/l>$", line):
        reports.append("line missing closing </l>:\nline number: {}\n{}".format(i,line))
      if not re.match("<l[> ]", line) and re.search("<\/l>$", line):
        reports.append("line missing opening <l>:\nline number: {}\n{}".format(i,line))

      # no nested line groups
      if re.match("<lg", line):
        if inLineGroup:
          reports.append("line group error: unexpected <lg tag\nline number: {}\nunclosed lg started at line: {}".format(i,lineGroupStartLine))
        inLineGroup = True
        lineGroupStartLine = i
      if re.match("<\/lg", line):
        if not inLineGroup:
          reports.append("line group error: closing a </lg that is not open:\nline number: {}".format(i))
        inLineGroup = False

      # while in a line group all inline tags must be paired
      if inLineGroup:
        oLine = line

        m = re.search("<sc>", line)
        while m:
          line = re.sub("<sc>", "", line, 1)
          if not re.search("<\/sc>", line):
            reports.append("error:unclosed <sc> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<\/sc>", "", line, 1)
          m = re.search("<sc>", line)
        line = oLine
        m = re.search("<\/sc>", line)
        while m:
          line = re.sub("<\/sc>", "", line, 1)
          if not re.search("<sc>", line):
            reports.append("error:unopened </sc> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<sc>", "", line, 1)
          m = re.search("<\/sc>", line)

        line = oLine
        m = re.search("<i>", line)
        while m:
          line = re.sub("<i>", "", line, 1)
          if not re.search("<\/i>", line):
            reports.append("error:unclosed <i> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<\/i>", "", line, 1)
          m = re.search("<i>", line)
        line = oLine
        m = re.search("<\/i>", line)
        while m:
          line = re.sub("<\/i>", "", line, 1)
          if not re.search("<i>", line):
            reports.append("error:unopened </i> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<i>", "", line, 1)
          m = re.search("<\/i>", line)

        line = oLine
        m = re.search("<b>", line)
        while m:
          line = re.sub("<b>", "", line, 1)
          if not re.search("<\/b>", line):
            reports.append("error:unclosed <b> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<\/b>", "", line, 1)
          m = re.search("<b>", line)
        line = oLine
        m = re.search("<\/b>", line)
        while m:
          line = re.sub("<\/b>", "", line, 1)
          if not re.search("<b>", line):
            reports.append("error:unopened </b> tag in line group starting at line {}:\nline number: {}\n{}".format(lineGroupStartLine, i, oLine))
          line = re.sub("<b>", "", line, 1)
          m = re.search("<\/b>", line)

    # check for obsolete rend markup
    for i,line in enumerate(self.wb):
      if re.search("fs\d", line) or re.search("m[ltrb]\d", line):
        reports.append("error:obsolete markup:\nline number: {}\n{}".format(i, line))

    logfile = "errorlog.txt"
    if len(reports) > 0:
      cprint("\nThis file cannot be processed due to errors.")
      cprint("report is in file: {}\n".format(logfile))
      f1 = open(logfile, "w", encoding='utf-8')
      for line in reports:
        f1.write( "{:s}\n".format(line) )
      f1.close()
      exit(1)
    else:
      # remove error log file if present
      if os.path.exists(logfile):
        os.remove(logfile)

  def run(self):
    self.loadFile(self.srcfile)
    self.process()

  def __str__(self):
    return "fpgen lint"

# ===== class HTML ============================================================

class HTML(Book):

  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)
    self.css = self.CSS()
    self.uprop = self.userProperties()
    self.umeta = self.userMeta()
    self.srcfile = ifile
    self.dstfile = ofile
    self.cpn = 0
    self.showPageNumbers = False

  # internal class to manage CSS as it is added at runtime
  class CSS(object):
    def __init__(self):
      self.cssline = {}

    def addcss(self, s):
      if s in self.cssline:
        self.cssline[s] += 1
      else:
        self.cssline[s] = 1

    def show(self):
      t = []
      keys = list(self.cssline.keys())
      keys.sort()
      for s in keys:
        t.append("      " + s[6:])
      return t

  # internal class to save user properties
  class userProperties(object):
    def __init__(self):
      self.prop = {}

    def addprop(self,k,v):
      self.prop[k] = v

    def show(self):
      cprint(self.prop)

  # internal class to save user meta information
  class userMeta(object):
    def __init__(self):
      self.meta = []

    def addmeta(self,s):
      self.meta.append(s)

    def show(self):
      t = []
      for s in self.meta:
        t.append("    " + s)
      return t

  def shortHeading(self):
    # allow shortcut heading
    #
    # .title (default "Unknown")
    # .author (default "Unknown")
    # .language (default "en")
    # .created (no default) alternate: "date"
    # .cover (default "images/cover.jpg")
    # .display title (default "{.title}, by {.author}")
    #
    h = []
    dc_title = "Unknown"
    dc_author = "Unknown"
    dc_language = "en"
    dc_created = ""
    config.pn_cover = "images/cover.jpg"
    pn_displaytitle = ""
    m_generator = "fpgen {}".format(config.VERSION)
    i = 0
    where = 0
    shortused = False
    while i < len(self.wb):

      m = re.match(r"\.title (.*)", self.wb[i])
      if m:
        dc_title = m.group(1)
        where = i
        del(self.wb[i])
        shortused = True

      m = re.match(r"\.author (.*)", self.wb[i])
      if m:
        dc_author = m.group(1)
        where = i
        del(self.wb[i])
        shortused = True

      m = re.match(r"\.language (.*)", self.wb[i])
      if m:
        dc_language = m.group(1)
        where = i
        del(self.wb[i])
        shortused = True

      m = re.match(r"\.created (.*)", self.wb[i])
      if m:
        dc_created = m.group(1)
        where = i
        del(self.wb[i])
        shortused = True

      m = re.match(r"\.date (.*)", self.wb[i])
      if m:
        dc_created = m.group(1)
        where = i
        del(self.wb[i])
        shortused = True

      m = re.match(r".cover (.*)", self.wb[i])
      if m:
        config.pn_cover = m.group(1)
        where = i
        del(self.wb[i])

      m = re.match(r".displaytitle (.*)", self.wb[i])
      if m:
        pn_displaytitle = m.group(1)
        where = i
        del(self.wb[i])

      i += 1

    # if user hasn't specified display title, build it from title+author
    if pn_displaytitle == "":
      pn_displaytitle = "{}, by {}".format(dc_title, dc_author)

    if shortused:
      self.umeta.addmeta("<meta name='DC.Title' content='{}'/>".format(dc_title))
      self.umeta.addmeta("<meta name='DC.Creator' content='{}'/>".format(dc_author))
      self.umeta.addmeta("<meta name='DC.Language' content='{}'/>".format(dc_language))
      if dc_created != "":
        self.umeta.addmeta("<meta name='DC.Created' content='{}'/>".format(dc_created))

    self.uprop.addprop("cover image", "{}".format(config.pn_cover))
    self.uprop.addprop("display title", "{}".format(pn_displaytitle))

  # translate marked-up line to HTML
  # input:
  #   s:   line in <l>...</l> markup
  #   pf:  true if line being used in poetry
  #   lgr: encompassing markup (i.e. from a lg rend attribute)

  def m2h(self, s, pf='False', lgr=''):
    incoming = s
    m = re.match("<l(.*?)>(.*?)<\/l>",s)
    if not m:
      self.fatal("malformed line: {}".format(s))
    # combine rend specified on line with rend specified for line group
    t1 = m.group(1).strip() + " " + lgr
    t2 = m.group(2)

    setid = ""
    m = re.search("id=[\"'](.*?)[\"']", t1) # an id (target)
    if m:
      setid = m.group(1)
      t1 = re.sub("id=[\"'](.*?)[\"']", "", t1)

    therend = t1

    if re.match("(◻+)", t2) and re.search("center", therend):
      self.fatal("indent requested on centered line. exiting")
    if re.match("(◻+)", t2) and re.search("right", therend):
      self.fatal("indent requested on right-aligned line. exiting")

    # with poetry, leave indents as hard spaces; otherwise, convert to ml
    m = re.match("(\s+)", t2) # leading spaces on line
    if m:
      if not pf: # not poetry
        therend += "ml:{}em".format(len(m.group(1)))
        t2 = re.sub("^\s+","",t2)
      else:
        t2 = "&#160;"*len(m.group(1)) + re.sub("^\s+","",t2)

    thetext = t2
    therend = therend.strip()
    thestyle = "" # reset the style

    # ----- alignment -----------
    if re.search("center", therend):
      thestyle += "text-align:center;"
      therend = re.sub("center", "", therend)

    if re.search("right", therend):
      thestyle += "text-align:right;"
      therend = re.sub("right", "", therend)

    if re.search("left", therend):
      thestyle += "text-align:left;"
      therend = re.sub("left", "", therend)

    # ----- margins -------------

    # three forms: mt:2em or mt:2.5em or mt:.8em

    m = re.search("m[tblr]:\.\d+em", therend)
    if m:
      therend = re.sub(":\.",":0.", therend)

    m = re.search("mt:(\d+)em", therend)
    if m:
      thestyle += "margin-top:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)
    m = re.search("mt:(\d+\.\d+)em", therend)
    if m:
      thestyle += "margin-top:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)

    m = re.search("mr:(\d+)em", therend)
    if m:
      thestyle += "text-align:right;margin-right:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)
    m = re.search("mr:(\d+\.\d+)em", therend)
    if m:
      thestyle += "text-align:right;margin-right:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)

    m = re.search("mb:(\d+)em", therend)
    if m:
      thestyle += "margin-bottom:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)
    m = re.search("mb:(\d+\.\d+)em", therend)
    if m:
      thestyle += "margin-bottom:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)

    m = re.search("ml:(\d+)em", therend)
    if m:
      thestyle += "text-align:left;margin-left:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)
    m = re.search("ml:(\d+\.\d+)em", therend)
    if m:
      thestyle += "text-align:left;margin-left:{}em;".format(m.group(1))
      therend = re.sub(m.group(0), "", therend)

    # check that all mt, mr, mb and ml have been handled
    if re.search(r"mt|mr|mb|ml", therend):
      print("unhandled margin: {}".format(incoming))

    # ----- font size -----------
    if re.search("xlg", therend):
      thestyle += "font-size:x-large;"
      therend = re.sub("xlg", "", therend)
    if re.search("lg", therend):
      thestyle += "font-size:large;"
      therend = re.sub("lg", "", therend)

    if re.search("xsm", therend):
      thestyle += "font-size:x-small;"
      therend = re.sub("xsm", "", therend)
    if re.search("sm", therend):
      thestyle += "font-size:small;"
      therend = re.sub("sm", "", therend)

    m = re.search("fs:([\d\.]+)em", therend)
    if m:
      thestyle += "font-size:{}em;".format(m.group(1))
      therend = re.sub("fs([\d\.]+)em", "", therend)

    # ----- font presentation ---
    if re.search("under", therend):
      thestyle += "text-decoration:underline;"
      therend = re.sub("under", "", therend)
    if re.search("bold", therend):
      thestyle += "font-weight:bold;"
      therend = re.sub("bold", "", therend)
    if re.search("sc", therend):
      thestyle += "font-variant:small-caps;"
      therend = re.sub("sc", "", therend)
    if re.search("i", therend):
      thestyle += "font-style:italic;"
      therend = re.sub("i", "", therend)

    thestyle = thestyle.strip()
    hstyle = ""
    if not empty.match(thestyle):
      hstyle = "style='{}'".format(thestyle)
    hid = ""
    if not empty.match(setid):
      hid = "id='{}'".format(setid)

    if pf: # poetry
      self.css.addcss("[511] div.lgp p.line0 { text-indent:-3em; margin:0 auto 0 3em; }")
      s =  "<p class='line0' {} {}>".format(hstyle,hid) + thetext + "</p>"
    else:
      self.css.addcss("[510] p.line { text-indent:0; margin-top:0; margin-bottom:0; }")
      s =  "<p class='line' {} {}>".format(hstyle,hid) + thetext + "</p>"
    s = re.sub(" +>", ">", s) # trailing internal spaces in tags

    # ensure content in blank lines
    if re.search("<p class='line[^>]*?><\/p>", s):
      s = re.sub("<p class='line[^>]*?><\/p>", "<p class='line'>&#160;</p>", s)
    return s

  # preprocess text
  def preprocess(self):
    self.dprint(1,"preprocess")

    i = 0
    while i < len(self.wb):

      if not self.wb[i].startswith("▹"):
        # protect special characters
        self.wb[i] = re.sub(r"\\ ", '⋀', self.wb[i]) # escaped (hard) spaces
        self.wb[i] = re.sub(r" ",   '⋀', self.wb[i]) # unicode 0xA0, non-breaking space
        self.wb[i] = re.sub(r"\\%", '⊐', self.wb[i]) # escaped percent signs (macros)
        self.wb[i] = re.sub(r"\\#", '⊏', self.wb[i]) # escaped octothorpes (page links)
        self.wb[i] = re.sub(r"\\<", '≼', self.wb[i]) # escaped open tag marks
        self.wb[i] = re.sub(r"\\>", '≽', self.wb[i]) # escaped close tag marks

        # Line ending in period must join with subsequent line starting with periods
        # We do not have agreement on this yet!
#        if self.wb[i].endswith('.') and  i + 1 < len(self.wb) :
#          m = re.match("^\. [\. ]+\W*", self.wb[i+1])
#          if m:
#            leading = m.group(0)
#            if leading != "":
#              self.wb[i] = self.wb[i] + ' ' + leading.rstrip();
#              self.wb[i+1] = self.wb[i+1][len(leading):]

        while re.search(r"\. \.", self.wb[i]):
          self.wb[i] = re.sub(r"\. \.",'.⋀.', self.wb[i]) # spaces in spaced-out ellipsis
        self.wb[i] = re.sub(r"\\'",'⧗', self.wb[i]) # escaped single quote
        self.wb[i] = re.sub(r'\\"','⧢', self.wb[i]) # escaped double quote
        self.wb[i] = re.sub(r"&",'⧲', self.wb[i]) # ampersand
        self.wb[i] = re.sub("<l\/>","<l></l>", self.wb[i]) # allow user shortcut <l/> -> </l></l>
      i += 1

    i = 0
    while i < len(self.wb):
      # unadorned lines in line groups get marked here
      m = re.match("<lg(.*?)>",self.wb[i])
      if m:
        lgopts = m.group(1) # what kind of line group
        i += 1
        if re.search("rend='center'",lgopts): # it's a centered line group
          while not re.match("<\/lg>",self.wb[i]): # go over each line until </lg>
            # already marked? <l or <ill..
            if not re.match("^\s*<",self.wb[i]) or re.match("<link",self.wb[i]):
              self.wb[i] = "<l>" + self.wb[i] + "</l>" # no, mark it now.
            i += 1
        else: # not a centered line group so honor leading spaces
          while not re.search("<\/lg>",self.wb[i]): # go over each line until </lg>
            if not re.match("^\s*<l",self.wb[i]) or re.match("<link",self.wb[i]): # already marked?
              self.wb[i] = "<l>" + self.wb[i].rstrip() + "</l>"
              m = re.match(r"(<l.*?>)(\s+)(.*?)<\/l>", self.wb[i])
              if m:
                self.wb[i] = m.group(1) + "◻"*len(m.group(2)) + m.group(3) + "</l>"
            i += 1
      i += 1

    i = 1
    while i < len(self.wb)-1:
      if re.match("<quote", self.wb[i]) and not empty.match(self.wb[i+1]):
        t = [self.wb[i], ""]
        # inject blank line
        self.wb[i:i+1] = t
        i += 1
      if re.match("</quote>", self.wb[i]) and not empty.match(self.wb[i-1]):
        t = ["", "</quote>"]
        # inject blank line
        self.wb[i:i+1] = t
        i += 1
      i += 1

    # single-line or split-line format footnotes to multi
    i = 0
    while i < len(self.wb):
      m = re.match("(<footnote id=[\"'].*?[\"']>)(.*?)(<\/footnote>)", self.wb[i])
      if m:
        self.wb[i:i+1] = [m.group(1),m.group(2).strip(),m.group(3)]
        i += 2
        continue
      m = re.match("(<footnote id=[\"'].*?[\"']>)(.*?)$", self.wb[i]) # closing tag on separate line
      if m:
        self.wb[i:i+1] = [m.group(1),m.group(2).strip()]
        i += 1
        continue
      i += 1

    # whitespace around <footnote and </footnote
    i = 0
    while i < len(self.wb):
      if re.match("<\/?footnote", self.wb[i]):
        self.wb[i:i+1] = ["", self.wb[i], ""]
        i += 2
      i += 1

  #
  def processLiterals(self):
    self.dprint(1,"processLiterals")
    i = 0
    while i < len(self.wb):
      if re.match("<lit>", self.wb[i]):
        del self.wb[i] # <lit
        while not re.match("<\/lit>", self.wb[i]):
          self.wb[i] = re.sub('≼', "⨭", self.wb[i]) # literal open tag marks
          self.wb[i] = re.sub('≽', '⨮', self.wb[i]) # literal close tag marks
          self.wb[i] = "▹"+self.wb[i]
          i += 1
        del self.wb[i] # </lit
      i += 1

  def userHeader(self):
    self.dprint(1,"userHeader")
    i = 0
    while i < len(self.wb):
      m = re.match("<property name=[\"'](.*?)[\"'] content=[\"'](.*?)[\"']\s*\/?>", self.wb[i])
      if m:
        self.uprop.addprop(m.group(1), m.group(2))
        # 22-Feb-2014 if it's a specified cover, need to put it in global variable
        # so epub &c. can use it after instance is complete
        if m.group(1) == "cover image":
          config.pn_cover = m.group(2)
          # print("cover image: {}".format(config.pn_cover))
        del self.wb[i]
        continue

      m = re.match("<meta", self.wb[i])
      if m:
        if not re.search("\/>$", self.wb[i]):
          self.wb[i] =re.sub(">$", "/>", self.wb[i])
        self.umeta.addmeta(self.wb[i])
        del self.wb[i]
        continue

      m = re.match("<option name=[\"'](.*?)[\"'] content=[\"'](.*?)[\"']\s*\/?>", self.wb[i])
      if m:
        config.uopt.addopt(m.group(1), m.group(2))
        del self.wb[i]
        continue
      i += 1

  # page numbers honored in HTML, if present
  # convert all page numbers to absolute
  def processPageNum(self):
    self.dprint(1,"processPageNum")

    cpn = ""
    for i, line in enumerate(self.wb):
      if line.startswith("▹"): # no page numbers in preformatted text
        continue
      m = re.search(r"pn=['\"](\+?)(.+?)['\"]", self.wb[i])
      if m:
        self.showPageNumbers = True
        if not m.group(1):
          cpn = m.group(2) # page number specified literally
        else:
          if cpn != "":
            # increment page number by specified amount
            if cpn.isdigit():
              cpn = str(int(cpn) + int(m.group(2)))
            else:
              increment = int(m.group(2))
              cpn = self.int_to_roman(self.roman_to_int(cpn) + increment)
          else:
            self.fatal("no starting page number" + self.wb[i])
        self.wb[i] = re.sub(r"pn=['\"](\+?)(.+?)['\"]", "⪦{}⪧".format(cpn), self.wb[i], 1)
        if "heading" not in self.wb[i]:
          self.wb[i] = re.sub("<⪦","⪦", self.wb[i])
          self.wb[i] = re.sub("⪧>","⪧", self.wb[i])

  def userToc(self):
    self.dprint(1,"userToc")

    needToc = False
    for i,line in enumerate(self.wb):
      if re.match("<tocloc", line):
        needToc = True
        break

    if needToc:
      m = re.match("<tocloc(.*?)>", line)
      if m:
          attrib = m.group(1)
      m = re.search("heading=[\"'](.*?)[\"']", attrib)
      usehead = "Table of Contents"
      if m:
          usehead = m.group(1)
      t = [] # build replacement stanza
      t.append("<div class='literal-container'>")
      t.append("<p class='toch'>{}</p>".format(usehead))
      self.css.addcss("[972] p.toch { text-align:center; text-indent: 0; font-size:1.2em; margin:1em auto; }")
      t.append("<div class='literal'>")
      self.css.addcss("[970] .literal-container { text-align:center; margin:1em auto; }")
      self.css.addcss("[971] .literal { display:inline-block; text-align:left; }")
      # now scan the book for headings with toc='' entries
      for i,line in enumerate(self.wb):
        m1 = re.match(r"<heading",line)
        m2 = re.search(r"level=[\"'](\d)[\"']",line)
        if re.search(r"toc='", line): # single quote delimiter
          m3 = re.search(r"toc='(.*?)'",line)
        else:
          m3 = re.search(r'toc="(.*?)"',line)
        m4 = re.search(r"id=[\"'](.*?)[\"']",line)
        if m1 and m2: # we have a line for the TOC
          htoc = ""
          if m3:
            htoc = m3.group(1) # optional toc contents
          hid = ""
          if m4:
            hid = m4.group(1) # optional id for toc link
          indent = 2*(int(m2.group(1))-1) # indent based on heading level
          if indent > 0:
            t.append("<p class='toc' style='margin-left: {0}em'><a href='#{1}'>{2}</a></p>".format(indent,hid,htoc))
          else:
            t.append("<p class='toc'><a href='#{0}'>{1}</a></p>".format(hid,htoc))
          self.css.addcss("[972] p.toc { text-align:left; text-indent:0; margin-top:0; margin-bottom:0; }")
      t.append("</div>")
      t.append("</div>")
      # insert TOC into document
      for i,line in enumerate(self.wb):
        if re.search("<tocloc", line):
          self.wb[i:i+1] = t

  def processLinks(self):
    self.dprint(1,"processLinks")
    for i,line in enumerate(self.wb):
      m = re.search("<link target=[\"'](.*?)[\"']>.*?<\/link>", self.wb[i])
      if m:
        self.wb[i] = re.sub("<link target=[\"'].*?[\"']>","⩤a href='#{}'⩥".format(m.group(1)), self.wb[i])
        self.wb[i] = re.sub("<\/link>","⩤/a⩥",self.wb[i])

  def processTargets(self):
    self.dprint(1,"processTargets")
    for i,line in enumerate(self.wb):
      m = re.search("<target id=[\"'](.*?)[\"']\/?>", self.wb[i])
      if m:
        self.wb[i] = re.sub("<target id=[\"'].*?[\"']\/?>","⩤a id='{}'⩥⩤/a⩥".format(m.group(1)), self.wb[i])

  def protectMarkup(self):
    fnc = 1 # available to autonumber footnotes
    self.dprint(1,"protectMarkup")
    for i,line in enumerate(self.wb):
      self.wb[i] = re.sub("<em>",'⩤em⩥', self.wb[i])
      self.wb[i] = re.sub("<\/em>",'⩤/em⩥', self.wb[i])
      self.wb[i] = re.sub("<i>",'⩤i⩥', self.wb[i])
      self.wb[i] = re.sub("<\/i>",'⩤/i⩥', self.wb[i])
      self.wb[i] = re.sub("<sc>",'⩤sc⩥', self.wb[i])
      self.wb[i] = re.sub("<\/sc>",'⩤/sc⩥', self.wb[i])
      self.wb[i] = re.sub("<b>",'⩤b⩥', self.wb[i])
      self.wb[i] = re.sub("<\/b>",'⩤/b⩥', self.wb[i])
      self.wb[i] = re.sub("<u>",'⩤u⩥', self.wb[i])
      self.wb[i] = re.sub("<\/u>",'⩤/u⩥', self.wb[i])
      self.wb[i] = re.sub("<g>",'⩤g⩥', self.wb[i])
      self.wb[i] = re.sub("<\/g>",'⩤/g⩥', self.wb[i])
      self.wb[i] = re.sub("<r>",'⩤r⩥', self.wb[i])
      self.wb[i] = re.sub("<\/r>",'⩤/r⩥', self.wb[i])
      while re.search("fn id=['\"]#['\"]", self.wb[i]):
        self.wb[i] = re.sub("fn id=['\"]#['\"]", "fn id='{}'".format(fnc), self.wb[i], 1)
        fnc += 1
      self.wb[i] = re.sub(r"<(fn id=['\"].*?['\"]/?)>",r'⩤\1⩥', self.wb[i])

      # new inline tags 2014.01.27
      self.wb[i] = re.sub("<(\/fs)>", r'⩤\1⩥', self.wb[i])
      self.wb[i] = re.sub("<(fs:.+?)>", r'⩤\1⩥', self.wb[i])

      # overline 13-Apr-2014
      if re.search("<ol>", self.wb[i]):
        self.css.addcss("[116] .ol { text-decoration:overline; }")
      self.wb[i] = re.sub("<ol>", '⎧', self.wb[i]) # overline
      self.wb[i] = re.sub("<\/ol>", '⎫', self.wb[i]) # overline

  def markPara(self):
    self.dprint(1,"markPara")

    if config.uopt.getopt("pstyle") == "indent": # new 27-Mar-2014
      self.css.addcss("[811] .pindent { margin-top:0; margin-bottom:0; text-indent:1.5em; }")
      self.css.addcss("[812] .noindent { margin-top:0; margin-bottom:0; text-indent:0; }")
      indent = True
      defaultPara = "<p class='pindent'>"
      noIndentPara = "<p class='noindent'>"
    else:
      defaultPara = "<p>"
      indent = False
    hangPara = "<p class='hang'>"
    self.css.addcss("[813] .hang { padding-left:1.5em; text-indent:-1.5em; }");
    paragraphTag = defaultPara

    i = 1
    while i < len(self.wb)-1:

      if re.match("▹", self.wb[i]): # preformatted
        i += 1
        continue

      if re.match("<lg",self.wb[i]): # no paragraphs in line groups
        while not re.match("<\/lg",self.wb[i]):
          i += 1
        i += 1
        continue

      if re.match("<table",self.wb[i]): # no paragraphs in tables
        while not re.match("<\/table",self.wb[i]):
          i += 1
        i += 1
        continue

      if re.match("<nobreak>", self.wb[i]): # new 27-Mar-2014
        if not indent:
          self.fatal("<nobreak> only legal with option pstyle set to indent")
        paragraphTag = noIndentPara
        self.wb[i] = re.sub("<nobreak>", "", self.wb[i])

      # If the line has a drop cap, don't indent
      if re.search("☊", self.wb[i]) and indent:
        paragraphTag = noIndentPara

      if re.match("<hang>", self.wb[i]):
        paragraphTag = hangPara
        self.wb[i] = re.sub("<hang>", "", self.wb[i])

      # outside of tables and line groups, no double blank lines
      if empty.match(self.wb[i-1]) and empty.match(self.wb[i]):
        del (self.wb[i])
        i -= 1
        continue

      # a single, unmarked line # 07-Mar-2014 edit
      if (empty.match(self.wb[i-1]) and empty.match(self.wb[i+1])
        and not re.match("^<", self.wb[i]) and not re.match(">$", self.wb[i])
        and not empty.match(self.wb[i])):
          self.wb[i] = paragraphTag + self.wb[i] + "</p>" #27-Mar-2014
          paragraphTag = defaultPara
          i +=  1
          continue

      # start of paragraph # 07-Mar-2014 edit
      if (empty.match(self.wb[i-1]) and not empty.match(self.wb[i])
        and not re.match("<", self.wb[i])):
          self.wb[i] = paragraphTag + self.wb[i] # 27-Mar-2014
          paragraphTag = defaultPara
          i +=  1
          continue

      # end of paragraph
      if (empty.match(self.wb[i+1]) and not empty.match(self.wb[i])
         and not re.search(">$", self.wb[i])):
        self.wb[i] = self.wb[i] + "</p>"
        i +=  1
        continue

      i += 1

  def restoreMarkup(self):
    self.dprint(1,"restoreMarkup")
    for i,line in enumerate(self.wb):
      self.wb[i] = re.sub("⩤",'<', self.wb[i])
      self.wb[i] = re.sub("⩥",'>', self.wb[i])

      if re.search("<i>", self.wb[i]):
        self.css.addcss("[110] .it { font-style:italic; }")
      self.wb[i] = re.sub("<i>","①", self.wb[i])
      self.wb[i] = re.sub("</i>",'②', self.wb[i])

      if re.search("<b>", self.wb[i]):
        self.css.addcss("[111] .bold { font-weight:bold; }")
      self.wb[i] = re.sub("<b>","③", self.wb[i])
      self.wb[i] = re.sub("</b>",'②', self.wb[i])

      if re.search("<sc>", self.wb[i]):
        self.css.addcss("[112] .sc { font-variant:small-caps; }")
      self.wb[i] = re.sub("<sc>","④", self.wb[i])
      self.wb[i] = re.sub("</sc>",'②', self.wb[i])

      if re.search("<u>", self.wb[i]):
        self.css.addcss("[113] .ul { text-decoration:underline; }")
      self.wb[i] = re.sub("<u>","⑤", self.wb[i])
      self.wb[i] = re.sub("</u>",'②', self.wb[i])

      if re.search("<g>", self.wb[i]):
        self.css.addcss("[114] .gesp { letter-spacing:0.2em; }")
      self.wb[i] = re.sub("<g>","⑥", self.wb[i])
      self.wb[i] = re.sub("</g>",'②', self.wb[i])

      if re.search("<r>", self.wb[i]):
        self.css.addcss("[115] .red { color: red; }")
      self.wb[i] = re.sub("<r>","⑦", self.wb[i])
      self.wb[i] = re.sub("</r>",'②', self.wb[i])

      self.wb[i] = re.sub(r"⩤(fn id=['\"].*?['\"]/?)⩥",r'<\1>', self.wb[i])

      # new inline tags 2014.01.27
      self.wb[i] = re.sub(r"<fs:l>",'⓯', self.wb[i])
      self.wb[i] = re.sub(r"<fs:xl>",'⓰', self.wb[i])
      self.wb[i] = re.sub(r"<fs:s>",'⓱', self.wb[i])
      self.wb[i] = re.sub(r"<fs:xs>",'⓲', self.wb[i])
      self.wb[i] = re.sub(r"<\/fs>",'⓳', self.wb[i])

  def startHTML(self):
    self.dprint(1,"startHTML")

    body_defined = False
    if 'e' in self.gentype:
      self.css.addcss("[100] body { margin-left:0;margin-right:0; }")
      body_defined = True
    if 'k' in self.gentype:
      self.css.addcss("[100] body { margin-left:0;margin-right:0; }")
      body_defined = True
    if 'p' in self.gentype:
      self.css.addcss("[100] body { margin-left:0;margin-right:0; }")
      body_defined = True
    if not body_defined:
      self.css.addcss("[100] body { margin-left:8%;margin-right:10%; }")

    if self.showPageNumbers: # only possible in HTML
      if 'h' == self.gentype:
        self.css.addcss("[105] .pageno  { right: 1%; font-size: x-small; background-color: inherit; color: silver;")
        self.css.addcss("[106]          text-indent: 0em; text-align: right; position: absolute;")
        self.css.addcss("[107]          border:1px solid silver; padding:1px 3px; font-style:normal;")
        self.css.addcss("[108]          font-variant: normal; font-weight: normal; text-decoration:none; }")
        self.css.addcss("[109] .pageno:after { color: gray; content: attr(title); }") # new 4.17
      else:
        self.css.addcss("[105] .pageno { display:none; }") # no visible page numbers in non-browser HTML

    self.css.addcss("[170] p { text-indent:0; margin-top:0.5em; margin-bottom:0.5em;") # para style
    if config.uopt.getopt("quote-para-style") == 'block':
      self.css.addcss("[170] div.blockquote p.pindent { text-indent:0; }") # para style in quote
    align_defined = False
    if 'e' in self.gentype:
      self.css.addcss("[171]     text-align: left; }") # epub ragged right
      align_defined = True
    if 'k' in self.gentype:
      self.css.addcss("[171]     text-align: left; }") # mobi ragged right
      align_defined = True
    if not align_defined:
      self.css.addcss("[171]     text-align: justify; }") # browser HTML justified

    t =[]
    t.append("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"")
    t.append("    \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">")
    t.append("<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\">")
    t.append("  <head>")
    t.append("    <meta http-equiv=\"Content-Type\" content=\"text/html;charset=utf-8\" />")

    if "display title" in self.uprop.prop:
      t.append("    <title>{}</title>".format(self.uprop.prop["display title"]))
    else:
      # use default title
      t.append("    <title>{}</title>".format(re.sub("-src.txt", "", self.srcfile)))

    if "cover image" in self.uprop.prop:
      t.append("    <link rel=\"coverpage\" href=\"{}\"/>".format(self.uprop.prop["cover image"]))
      t.append("    <meta name=\"cover\" content=\"{}\" />".format(self.uprop.prop["cover image"]))
    else:
      # self.cprint("warning: no cover image specified")
      t.append("    <link rel=\"coverpage\" href=\"{}\"/>".format("images/cover.jpg"))
      t.append("    <meta name=\"cover\" content=\"images/cover.jpg\" />")

    t.append("      META PLACEHOLDER")
    t.append("    <style type=\"text/css\">")
    t.append("      CSS PLACEHOLDER")
    t.append("    </style>")

    if len(self.supphd) > 0:
      t += self.supphd

    t.append("  </head>")
    t.append("  <body>   ")

    self.wb = t + self.wb # prepend header

  def cleanup(self):
    self.dprint(1,"cleanup")
    for i in range(len(self.wb)):
      self.wb[i] = re.sub('⧗', "'", self.wb[i]) # escaped single quote
      self.wb[i] = re.sub('⧢', '"', self.wb[i]) # double quote
      self.wb[i] = re.sub('⧲', '&amp;', self.wb[i]) # ampersand

      self.wb[i] = re.sub('◻', '&ensp;', self.wb[i]) # wide space
      self.wb[i] = re.sub('⋀', '&nbsp;', self.wb[i]) # non-breaking space

      self.wb[i] = re.sub('▹', '', self.wb[i]) # unprotect literal lines
      self.wb[i] = re.sub('⧀', '<', self.wb[i]) # protected tag braces
      self.wb[i] = re.sub('⧁', '>', self.wb[i])
      self.wb[i] = re.sub('⊐', '%', self.wb[i]) # escaped percent signs (macros)
      self.wb[i] = re.sub('⊏', '#', self.wb[i]) # escaped octothorpes (page links)
      self.wb[i] = re.sub('≼', '&lt;', self.wb[i]) # escaped <
      self.wb[i] = re.sub('≽', '&gt;', self.wb[i]) # escaped >

      self.wb[i] = re.sub('⨭', '<', self.wb[i]) # protected <
      self.wb[i] = re.sub('⨮', '>', self.wb[i]) # protected >

      # Handle drop-caps, which have images.
      # Each image must be mapped in a property to its image file;
      # e.g. <property name='drop-T' content='images/T.jpg'>
      m = re.search('☊(.*)☋', self.wb[i])
      if m:
        letter = m.group(1)
        # Check for an open double-quote before the letter
        hasquote = re.match('“.*', letter)
        if hasquote:
          letter = letter[1:]
        # See if the property is there, if it isn't the old code which just
        # makes a large letter will be used
        if "drop-"+letter in self.uprop.prop:
          # Yes, property is there.  Image will be used.
          # If leading quote, generate special code to put it in the margin
          if hasquote:
            self.wb[i] = \
              '<div style="position:absolute;margin-left:-.5em; font-size:150%;">“</div>' + \
              self.wb[i]
          imgFile = self.uprop.prop["drop-" + letter]
          self.wb[i] = re.sub("☊.*☋", \
          "<img src='" + imgFile + "' style='float:left;' alt='" + letter + "'/>", \
          self.wb[i])

      # Drop-cap code for no image
      self.wb[i] = re.sub("☊", "<span style='float:left; clear: left; margin:0 0.1em 0 0; padding:0; line-height: 1.0em; font-size: 200%;'>", self.wb[i])
      self.wb[i] = re.sub("☋", "</span>", self.wb[i])

      self.wb[i] = re.sub("①","<span class='it'>", self.wb[i])
      self.wb[i] = re.sub("②","</span>", self.wb[i])
      self.wb[i] = re.sub("③","<span class='bold'>", self.wb[i])
      self.wb[i] = re.sub("④","<span class='sc'>", self.wb[i])
      self.wb[i] = re.sub("⑤","<span class='ul'>", self.wb[i])
      self.wb[i] = re.sub("⑥","<span class='gesp'>", self.wb[i])
      self.wb[i] = re.sub("⑦","<span class='red'>", self.wb[i])

      self.wb[i] = re.sub("⎧","<span class='ol'>", self.wb[i])
      self.wb[i] = re.sub("⎫","</span>", self.wb[i])

    # superscripts, subscripts
    for i in range(len(self.wb)):
      # special cases first: ^{} and _{}
      self.wb[i] = re.sub('\^\{\}', r'<sup>&#8203;</sup>', self.wb[i])
      self.wb[i] = re.sub('_\{\}', r'<sub>&#8203;</sub>', self.wb[i])
      self.wb[i] = re.sub('\^\{(.*?)\}', r'<sup>\1</sup>', self.wb[i]) # superscript format 1: Rob^{t}
      self.wb[i] = re.sub('\^(.)', r'<sup>\1</sup>', self.wb[i]) # superscript format 2: Rob^t
      self.wb[i] = re.sub('_\{(.*?)\}', r'<sub>\1</sub>', self.wb[i]) # subscript: H_{2}O

    # 2014.01.27 new font size inline
    for i in range(len(self.wb)):
      self.wb[i] = re.sub('⓯', "<span style='font-size:larger'>", self.wb[i])
      self.wb[i] = re.sub('⓰', "<span style='font-size:x-large'>", self.wb[i])
      self.wb[i] = re.sub('⓱', "<span style='font-size:smaller'>", self.wb[i])
      self.wb[i] = re.sub('⓲', "<span style='font-size:x-small'>", self.wb[i])
      self.wb[i] = re.sub('⓳', "</span>", self.wb[i])

  # page links
  # 2014.01.14 new in 3.02c
  def plinks(self):
    self.dprint(1,"plinks")

    # of the form #124:ch03#
    # displays 124, links to ch03
    for i in range(len(self.wb)): # new 2014.01.13
      m = re.search(r"#\d+:.*?#", self.wb[i])
      while m:
        self.wb[i] = re.sub(r"#(\d+):(.*?)#", r"<a href='#\2'>\1</a>", self.wb[i],1)
        m = re.search(r"#\d+\:.*?#", self.wb[i])

    # of the form #274#
    # displays 274, links to Page_274
    for i in range(len(self.wb)):
      m = re.search(r"#\d+#", self.wb[i])
      while m:
        self.wb[i] = re.sub(r"#(\d+)#", r"<a href='#Page_\1'>\1</a>", self.wb[i],1)
        m = re.search(r"#\d+#", self.wb[i])

  def placeCSS(self):
    self.dprint(1,"placeCSS")
    i = 0
    notplaced = True
    while i < len(self.wb) and notplaced:
      if re.search("CSS PLACEHOLDER", self.wb[i]):
        self.wb[i:i+1] = self.css.show()
        notplaced = False
      i += 1

  def placeMeta(self):
    self.dprint(1,"placeMeta")
    i = 0
    while i < len(self.wb):
      if re.search("META PLACEHOLDER", self.wb[i]):
        t = self.umeta.show()
        u = []
        for mline in t:
          if "Gutenberg Canada" in mline:
            print("discarding: {}".format(mline))
          else:
            u.append(mline)
        self.wb[i:i+1] = u
        return
      i += 1

  def endHTML(self):
    self.dprint(1,"endHTML")
    self.wb.append("  </body>")
    self.wb.append("  <!-- created with fpgen.py {} on {} -->".format(config.VERSION, config.NOW))
    self.wb.append("</html>")

  def doHeadings(self):
    self.dprint(1,"doHeadings")
    regex = re.compile("<heading(.*?)>(.*?)<\/heading>")
    for i,line in enumerate(self.wb):
      m = regex.match(line)
      if m:
        harg = m.group(1)
        htitle = m.group(2)
        htarget = ""
        hlevel = 0
        showpage = False

        m = re.search("id=[\"'](.*?)[\"']", harg)
        if m:
          htarget = m.group(1)

        m = re.search("level=[\"'](.*?)[\"']", harg)
        if m:
          hlevel = int(m.group(1))

        m = re.search("⪦([^-]+)⪧", harg)
        if m:
          self.cpn = m.group(1)
          showpage = True

        style = ""
        m = re.search("hidden", harg)
        if m:
          style = " style='visibility:hidden; margin:0; font-size:0;' "

        useclass = ""
        if re.search("nobreak", harg):
          useclass = " class='nobreak'"
          self.css.addcss("[427] h1.nobreak { page-break-before: avoid; }")

        if not showpage: # no visible page numbers

          if hlevel == 1:
            if not empty.match(htarget):
              self.wb[i] = "<h1{}{} id='{}'>{}</h1>".format(style, useclass, htarget, htitle)
            else:
              self.wb[i] = "<h1{}{}>{}</h1>".format(style, useclass, htitle)
            self.css.addcss("[250] h1 { text-align:center; font-weight:normal;")
            if self.gentype != 'h':
              self.css.addcss("[251]  page-break-before:always; ")
            self.css.addcss("[252]      font-size:1.2em; margin:2em auto 1em auto}")

          if hlevel == 2:
            if not empty.match(htarget):
              self.wb[i] = "<h2{}{} id='{}'>{}</h2>".format(style, useclass, htarget, htitle)
            else:
              self.wb[i] = "<h2{}{}>{}</h2>".format(style, useclass, htitle)
            self.css.addcss("[254] h2 { text-align:center; font-weight:normal;")
            self.css.addcss("[255]      font-size:1.1em; margin:1em auto 0.5em auto}")

          if hlevel == 3:
            if not empty.match(htarget):
              self.wb[i] = "<h3{}{} id='{}'>{}</h3>".format(style, useclass, htarget, htitle)
            else:
              self.wb[i] = "<h3{}{}>{}</h3>".format(style, useclass, htitle)
            self.css.addcss("[258] h3 { text-align:center; font-weight:normal;")
            self.css.addcss("[259]      font-size:1.0em; margin:1em auto 0.5em auto}")

          if hlevel == 4:
            if not empty.match(htarget):
              self.wb[i] = "<h4{}{} id='{}'>{}</h4>".format(style, useclass, htarget, htitle)
            else:
              self.wb[i] = "<h4{}{}>{}</h4>".format(style, useclass, htitle)
            self.css.addcss("[260] h4 { text-align:center; font-weight:normal;")
            self.css.addcss("[261]      font-size:1.0em; margin:1em auto 0.5em auto}")

        if showpage:

          if self.gentype != 'h': # other than browser HTML, just the link
            span = "<a name='Page_{0}' id='Page_{0}'></a>".format(self.cpn)
          else:
            span = "<span class='pageno' title='{0}' id='Page_{0}'></span>".format(self.cpn)

          if hlevel == 1:
            if not empty.match(htarget):
             self.wb[i] = "<div>{}<h1{}{} id='{}'>{}</h1></div>".format(span, style, useclass, htarget, htitle)
            else:
             self.wb[i] = "<div>{}<h1{}{}>{}</h1></div>".format(span, style, useclass, htitle)
            self.css.addcss("[250] h1 { text-align:center; font-weight:normal;")
            if self.gentype != 'h':
              self.css.addcss("[251]  page-break-before:always; ")
            self.css.addcss("[252]      font-size:1.2em; margin:2em auto 1em auto}")

          if hlevel == 2:
            if not empty.match(htarget):
             self.wb[i] = "<h2{}{} id='{}'>{}{}</h2>".format(style, useclass, htarget, span, htitle)
            else:
             self.wb[i] = "<h2{}{}>{}{}</h2>".format(style, useclass, span, htitle)
            self.css.addcss("[254] h2 { text-align:center; font-weight:normal;")
            self.css.addcss("[255]      font-size:1.1em; margin:1em auto 0.5em auto}")

          if hlevel == 3:
            if not empty.match(htarget):
             self.wb[i] = "<h3{}{} id='{}'>{}{}</h3>".format(style, useclass, htarget, span, htitle)
            else:
             self.wb[i] = "<h3{}{}>{}{}</h3>".format(style, useclass, span, htitle)
            self.css.addcss("[258] h3 { text-align:center; font-weight:normal;")
            self.css.addcss("[259]      font-size:1.0em; margin:1em auto 0.5em auto}")

          if hlevel == 4:
            if not empty.match(htarget):
              self.wb[i] = "<h4{}{} id='{}'>{}{}</h4>".format(style, useclass, htarget, span, htitle)
            else:
              self.wb[i] = "<h4{}{}>{}{}</h4>".format(style, useclass, span, htitle)
            self.css.addcss("[260] h4 { text-align:center; font-weight:normal;")
            self.css.addcss("[261]      font-size:1.0em; margin:1em auto 0.5em auto}")

  def doBlockq(self):
    self.dprint(1,"doBlockq")
    regex = re.compile("<quote(.*?)>")
    for i,line in enumerate(self.wb):
      owned = False
      m = regex.match(line)
      if m:
        rendatt = m.group(1)

        # is a width specified? must be in em
        m = re.search("w:(\d+)em", rendatt)
        if m:
          rendw = m.group(1)
          self.wb[i] = "<div class='blockquote"+rendw+"'>"
          self.css.addcss("[391] div.blockquote"+rendw+" { margin:1em auto; width:"+rendw+"em; }")
          self.css.addcss("[392] div.blockquote"+rendw+" p { text-align:left; }")
          owned = True

        # is a font size specified? must be in em
        m = re.search("fs:([\d\.]+)em", rendatt)
        if m:
          if owned:
            self.fatal("doBlockq rend overload")
          rendfs = m.group(1)
          # user-specified font size.
          drendfs = re.sub("\.","r", rendfs)
          self.wb[i] = "<div class='blockquote"+drendfs+"'>"
          stmp = "[391] div.blockquote" + drendfs+ " { margin:1em 2em; }"
          self.css.addcss(stmp)
          stmp = "[392] div.blockquote" + drendfs + " p { font-size: " + rendfs + "em }"
          self.css.addcss(stmp)
          owned = True

        # nothing special specified
        if not owned:
          self.wb[i] = "<div class='blockquote'>"
          self.css.addcss("[390] div.blockquote { margin:1em 2em; text-align:justify; }")
      if re.match("<\/quote>",line):
        self.wb[i] = "</div>"

  def doBreaks(self): # 02-Apr-2014 rewrite
    self.dprint(1,"doBreaks")
    cssc = 100

    regex = re.compile("<tb(.*?)\/?>")
    for i,line in enumerate(self.wb):

      m = regex.search(line)
      if m:
        # set defaults
        tb_thick = "1px"
        tb_linestyle = "solid"
        tb_color = "black"
        tb_width = "30"
        tb_mt = "0.5em"
        tb_mb = "0.5em"
        tb_align = "text-align:center"

        m = re.search(r"rend='(.*?)'", self.wb[i])
        if m:
          style = ""
          border = ""
          tbrend = m.group(1)

          m = re.search("mt:(\-?\d+\.?\d*)+(px|%|em)", tbrend)
          if m:
            tb_mt = "{}{}".format(m.group(1),m.group(2))

          m = re.search("mb:(\-?\d+\.?\d*)+(px|em)", tbrend)
          if m:
            tb_mb = "{}{}".format(m.group(1),m.group(2))

          # line style:
          m = re.search("ls:(\w+?);", tbrend)
          if m:
            tb_linestyle = m.group(1)

          # line color
          m = re.search("lc:(\w+?)[;']", tbrend)
          if m:
            tb_color = m.group(1)

          m = re.search("thickness:(\w+?)[;']", tbrend)
          if m:
            tb_thick = m.group(1)

          m = re.search("w:(\d+)%", tbrend)
          if m:
            tb_width = "{}".format(m.group(1))

          tb_marginl = str((100 - int(tb_width))//2) + "%" # default if centered
          tb_marginr = tb_marginl

          m = re.search("right", tbrend)
          if m:
            tb_align = "text-align:right"
            tb_marginl = "auto"
            tb_marginr = "0"

          m = re.search("left", tbrend)
          if m:
            tb_align = "text-align:left"
            tb_marginl = "0"
            tb_marginr = "auto"

          # m = re.search("s:([\d\.]+?)em", tbrend) # special form: invisible, for spacing
          # if m:
          # ...

          # build the css class
          bcss = "border:none; border-bottom:{} {} {}; width:{}%; margin-top:{}; margin-bottom:{}; {}; margin-left:{}; margin-right:{}".format(tb_thick, tb_linestyle, tb_color, tb_width, tb_mt, tb_mb, tb_align, tb_marginl, tb_marginr)
          self.css.addcss("[370] hr.tbk{}".format(cssc) + "{ " + bcss + " }")
          self.wb[i]= "<hr class='tbk{}'/>".format(cssc)
          cssc += 1
        else:
          self.css.addcss("[370] hr.tbk { border:none; border-bottom:1px solid black; width:30%; margin-left:35%; margin-right:35%; }")
          self.wb[i]= "<hr class='tbk'/>"

      if re.match("<pb\/?>",line):
        if self.gentype == 'h':
          self.wb[i]= "<hr class='pbk'/>"
          self.css.addcss("[372] hr.pbk { border:none; border-bottom:1px solid silver; width:100%; margin-top:2em; margin-bottom:2em }")
        else:
          self.wb[i]= "<div class='pbba'></div>"
          self.css.addcss("[372] div.pbba { page-break-before:always; }")

      m = re.match("<hr rend='(.*?)'\/?>",line)
      if m:
        if re.search("footnotemark", m.group(1)):
          self.wb[i]= "<hr class='footnotemark'/>"
          self.css.addcss("[378] hr.footnotemark { border:none; border-bottom:1px solid silver; width:10%; margin:1em auto 1em 0; }")
        else:
          self.fatal("unknown hr rend: /{}/".format(m.group(1)))


  def doTables(self):
    self.dprint(1,"doTables")
    tableCount = 0
    i = 0
    regex = re.compile("<table(.*?)>")
    while i < len(self.wb):
      m = regex.match(self.wb[i])
      if m:

        tableCount += 1
        tableID = "tab" + str(tableCount)
        vpad = "2" # defaults
        hpad = "5"

        # can include rend and pattern
        tattr = m.group(1)
        self.css.addcss("[560] table.center { margin:0.5em auto; border-collapse: collapse; padding:3px; }")
        self.css.addcss("[560] table.left { margin:0.5em 1.2em; border-collapse: collapse; padding:3px; }")

        # pull the pattern
        columns = parseTablePattern(tattr)

        # Were there any user-specified widths?
        userWidth = False
        for col in columns:
          if col.userWidth:
            userWidth = True
            break

        # pull the rend attributes
        trend = ""
        useborder = False
        left = False
        m = re.search("rend='(.*?)'", tattr)
        if m:
          trend = m.group(1)
          m = re.search("vp:(\d+)", trend) # vertical cell padding
          if m:
            vpad = int(m.group(1))
          m = re.search("hp:(\d+)", trend) # horizontal cell padding
          if m:
            hpad = int(m.group(1))
          useborder = re.search("border", trend) # table uses borders
          left = re.search("left", trend)  # Left, not centre

        # Generate nth-of-type css for columns that need lines between them
        colIndex = 1
        for col in columns:
          colID = "c" + str(colIndex)
          if col.lineBefore != 0:
            property = "border-left"
            linetype = "solid" if col.lineBeforeStyle == '|' else "double"
            value = str(col.lineBefore) + "px"
            self.css.addcss("[562] ." + tableID + colID +
              " { " + property + ": " + value + " " + linetype + " black; }");
          if col.lineAfter != 0:
            property = "border-right"
            linetype = "solid" if col.lineBeforeStyle == '|' else "double"
            value = str(col.lineAfter) + "px"
            self.css.addcss("[563] ." + tableID + colID + 
              " { " + property + ": " + value + " " + linetype + " black; }");
          colIndex += 1

        # build the table header
        t = []
        j = i + 1

        s = "<table id='" + tableID +"' summary='' class='"
        if left:
          s += 'left'
        else:
          s += 'center'

        if useborder:
          s += " border"
          self.css.addcss("[561] table.border td { border: 1px solid black; }")
        s += "'>"
        t.append(s)
        if userWidth:
          t.append("<colgroup>")
          for col in columns:
            t.append("<col span='1' style='width: {}em;'/>".format(col.width//2))
          t.append("</colgroup>")

        # emit each row of table
        rowNum = 1
        ncols = len(columns)
        while not re.match("<\/table>", self.wb[j]):

          row = TableRow(self.wb[j])

          if row.isSingle() or row.isDouble():
            # Process horizontal line
            # The first row is on the top; the n-th row is on the bottom of the
            # previous row
            location = "bottom"
            nTH = rowNum-1
            if rowNum == 1:
              location = "top"
              nTH = 1
            if row.isSingle():
              width = "1px"
              style = "solid"
            else:
              width = "4px"
              style = "double"
            self.css.addcss("[564] #" + tableID + " tr:nth-of-type(" + str(nTH) +
              ") td { border-" + location + ": " + width + " " + style + " black; }")
            j += 1
            # Do not increment rowNum
            continue

          # Process real data line
          # Need to generate all the columns, even if no column data in this row,
          # in case there are any verticals
          cells = row.getCells()
          nColData = len(cells)
          line = "<tr>"
          for n,col in enumerate(columns):
            if n >= nColData:
              cell = TableCell("&nbsp;")
            else:
              cell = cells[n]
            data = cell.getData().strip()

            # If this cell was spanned by the previous, ignore it.
            if cell.isSpanned():
              continue;

            # Look ahead into the following cells, to see if this is supposed to span
            nspan = cell.getSpan()
            if nspan > 1:
              colspan = " colspan='" + str(nspan) + "'"
            else:
              colspan = ""

            colID = "c" + str(n+1)
            class1 = tableID + colID
            class2 = ""

            if nspan > 1:
              endID = "-col" + str(n+nspan)
              class2 = tableID + colID + endID
              endCol = columns[n+nspan-1]

              property = "border-right"
              linetype = "solid" if endCol.lineAfterStyle == '|' else "double"
              value = str(endCol.lineAfter) + "px"
              self.css.addcss("[563] ." + class2 +
                " { " + property + ": " + value + " " + linetype + " black; }");

            if cell.isDefaultAlignment():
              align = col.align
            else:
              align = cell.getAlignment()

            userClass = cell.getUserClass()
            if userClass != None:
              class2 = class2 + ' ' + userClass

            line += "<td class='" + class1 + " " + class2 + "' " +\
              "style='padding: " + \
              str(vpad) + "px " + str(hpad) + "px; " + \
              "text-align:" + align + "; vertical-align:top'" + \
              colspan + ">" + data + "</td>"

          line += "</tr>"
          self.wb[j] = line
          t.append(self.wb[j])
          j += 1
          rowNum += 1
        self.wb[i:j] = t
        i = i+len(t)
      i += 1

  def doIllustrations(self):
    self.dprint(1,"doIllustrations")
    idcnt = 0 # auto id counter
    i_w = 0 # image width
    i_h = 0 # image height
    i_caption = "" # image caption or "" if no caption
    i_posn = "" # placement, left, center, right
    i_filename ="" # filename
    i_rend = "" # rend string
    i_clear = 0 # how many lines of source to replace
    i_link = "" # name of file to be linked-to or "" if no link

    i = 0
    while i < len(self.wb):
      m = re.search("<illustration(.*?)", self.wb[i])
      if m:

        # --------------------------------------------------------------------
        # set i_filename ("content" or "src")
        m = re.search("(content|src)=[\"'](.*?)[\"']", self.wb[i])
        if m:
          i_filename = m.group(2)
        if i_filename == "":
          self.fatal("no image filename specified in {}".format(self.wb[i]))

        # --------------------------------------------------------------------
        # pull rend string, if any
        m = re.search("rend=[\"'](.*?)[\"']", self.wb[i])
        if m:
          i_rend = m.group(1)

        # --------------------------------------------------------------------
        # set i_id
        m = re.search("id=[\"'](.*?)[\"']", self.wb[i])
        if m:
          i_id = m.group(1)
        else:
          i_id = "iid-{:04}".format(idcnt)
          idcnt += 1

        # --------------------------------------------------------------------
        # set i_posn placement
        i_posn = "center" # default
        if re.search("left", i_rend):
          i_posn = "left"
        if re.search("right", i_rend):
          i_posn = "right"

        if i_posn == "right":
          self.css.addcss("[380] .figright { float:right; clear:right; margin-left:1em;")
          self.css.addcss("[381]             margin-bottom:1em; margin-top:1em; margin-right:0;")
          self.css.addcss("[382]             padding:0; text-align:center; }")
        if i_posn == "left":
          self.css.addcss("[383] .figleft  { float:left; clear:left; margin-right:1em;")
          self.css.addcss("[384]             margin-bottom:1em; margin-top:1em; margin-left:0;")
          self.css.addcss("[385]             padding:0; text-align:center; }")
        if i_posn == "center":
          self.css.addcss("[386] .figcenter { text-align:center; margin:1em auto;}")

        # --------------------------------------------------------------------
        # set i_w, i_h width and height
        i_w = "none"
        m = re.search(r"w:(\d+)(px)?[;'\"]", i_rend)
        if m:
          i_w = m.group(1) + "px"
        m = re.search(r"w:(\d+)%[;'\"]", i_rend)
        if m:
          i_w = m.group(1) + "%"
        i_h = "auto"
        m = re.search(r"h:(\d+)(px)?[;'\"]", i_rend)
        if m:
          i_h = m.group(1)+"px"
        if i_w == "none":
          self.fatal("must specify image width\n{}".format(self.wb[i]))

        # --------------------------------------------------------------------
        # determine if link to larger image is requested.
        # if so, link is to filename+f in images folder.
        i_link = "" # assume no link
        m = re.search(r"link", i_rend)
        if m:
          i_link = re.sub(r"\.", "f.", i_filename)

        # --------------------------------------------------------------------
        # illustration may be on one line (/>) or three (>)
        if re.search("\/>", self.wb[i]): # one line, no caption
          i_caption = ""
          i_clear = 1
        else:
          i_caption = self.wb[i+1]
          i_caption = re.sub(r"<\/?caption>", "", i_caption)
          i_caption = re.sub("<br>","<br/>", i_caption) # honor hard breaks in captions
          i_clear = 3

        # --------------------------------------------------------------------
        #
        t = []
        style="width:{};height:{};".format(i_w,i_h)
        t.append("<div class='fig{}'>".format(i_posn, i_w))

        # handle link to larger images in HTML only
        s0 = ""
        s1 = ""
        if 'h' == self.gentype and i_link != "":
          s0 = "<a href='{}'>".format(i_link)
          s1 = "</a>"
        t.append("{}<img src='{}' alt='' id='{}' style='{}'/>{}".format(s0, i_filename, i_id, style, s1))
        if i_caption != "":
          self.css.addcss("[392] p.caption { text-align:center; margin:0 auto; width:100%; }")
          t.append("<p class='caption'>{}</p>".format(i_caption))
        t.append("</div>")
        self.wb[i:i+i_clear] = t

      i += 1

  def doLinks(self):
    self.dprint(1,"doLinks")
    for i,line in enumerate(self.wb):
      m = re.search("<link target=[\"'](.*?)[\"']>.*?<\/link>", self.wb[i])
      if m:
        tgt = m.group(1)
        self.wb[i] = re.sub("<link target=[\"'].*?[\"']>","<a href='#{}'>".format(tgt),self.wb[i])
        self.wb[i] = re.sub("<\/link>","</a>",self.wb[i])

  def doFootnotes(self):
    self.dprint(1,"doFootnotes")

    # footnote marks in text
    i = 0
    while i < len(self.wb):
      m = re.search("<fn id=[\"'](.*?)[\"']\/?>", self.wb[i])
      while m: # two footnotes on same line
        fmid = m.group(1)
        self.wb[i] = re.sub("<fn id=[\"'](.*?)[\"']\/?>",
          "<a id='r{0}'/><a href='#f{0}' style='text-decoration:none'><sup><span style='font-size:0.9em'>[{0}]</span></sup></a>".format(fmid),
          self.wb[i],1)
        m = re.search("<fn id=[\"'](.*?)[\"']\/?>", self.wb[i])
      i += 1

    # footnote targets and text
    i = 0
    while i < len(self.wb):
      m = re.match("<footnote id=[\"'](.*?)[\"']>", self.wb[i])
      if m:
        fnid = m.group(1)
        self.wb[i] = "<div id='f{0}'><a href='#r{0}'>[{0}]</a></div>".format(fnid)
        while not re.match("<\/footnote>", self.wb[i]):
          i += 1
        self.wb[i] = "</div> <!-- footnote end -->"
      i += 1

  # setup the framework around the lines
  # if a rend option of mt or mb appears, it applies to the entire block
  # other rend options apply to the contents of the block
  def doLineGroups(self):
    self.dprint(1,"doLineGroups")
    regex = re.compile("<lg(.*?)>")
    for i,line in enumerate(self.wb):
      m = regex.match(line)
      if m:
        lgopts = m.group(1).strip()

        # if a rend option of mt or mb is included, pull it out.
        # 16-Feb-2014 may be decimal
        blockmargin = "style='"
        m = re.search("mt:([\d]+)(em|px)", lgopts)
        if m:
          blockmargin += " margin-top: {}{}; ".format(m.group(1),m.group(2))
          lgopts = re.sub("mt:([\d]+)(em|px)\;?","", lgopts)
        m = re.search("mt:([\d]+\.[\d]+)(em|px)", lgopts)
        if m:
          blockmargin += " margin-top: {}{}; ".format(m.group(1),m.group(2))
          lgopts = re.sub("mt:([\d]+\.[\d]+)(em|px)\;?","", lgopts)
        m = re.search("mb:([\d]+)(em|px)", lgopts)
        if m:
          blockmargin += " margin-bottom: {}{}; ".format(m.group(1),m.group(2))
          lgopts = re.sub("mb:([\d]+)(em|px)\;?","", lgopts)
        m = re.search("mb:([\d]+\.[\d]+)(em|px)", lgopts)
        if m:
          blockmargin += " margin-bottom: {}{}; ".format(m.group(1),m.group(2))
          lgopts = re.sub("mb:([\d]+\.[\d]+)(em|px)\;?","", lgopts)
        blockmargin += "'"

        # default is left
        if empty.match(lgopts) or re.search("left", lgopts):
          lgopts = re.sub("left", "", lgopts) # 17-Feb-2014
          self.wb[i] = "<div class='lgl' {}> <!-- {} -->".format(blockmargin,lgopts)
          self.css.addcss("[220] div.lgl { }")
          self.css.addcss("[221] div.lgl p { text-indent: -17px; margin-left:17px; margin-top:0; margin-bottom:0; }")
          while not re.match("<\/lg>", self.wb[i]):
            i += 1
          self.wb[i] = "</div> <!-- end rend -->" # closing </lg>
          continue

        if re.search("center", lgopts):
          lgopts = re.sub("center", "", lgopts) # 17-Feb-2014
          self.wb[i] = "<div class='lgc' {}> <!-- {} -->".format(blockmargin,lgopts)
          self.css.addcss("[220] div.lgc { }")
          self.css.addcss("[221] div.lgc p { text-align:center; text-indent:0; margin-top:0; margin-bottom:0; }")
          while not re.match("<\/lg>", self.wb[i]):
            i += 1
          self.wb[i] = "</div> <!-- end rend -->" # closing </lg>
          continue

        if re.search("right", lgopts):
          lgopts = re.sub("right", "", lgopts) # 16-Mar-2014
          self.wb[i] = "<div class='lgr' {}> <!-- {} -->".format(blockmargin,lgopts)
          self.css.addcss("[220] div.lgr { }")
          self.css.addcss("[221] div.lgr p { text-align:right; text-indent:0; margin-top:0; margin-bottom:0; }")
          while not re.match("<\/lg>", self.wb[i]):
            i += 1
          self.wb[i] = "</div> <!-- end rend -->" # closing </lg>
          continue

        if re.search("block", lgopts):
          lgopts = re.sub("block", "", lgopts) # 17-Feb-2014
          self.wb[i] = "<div class='literal-container' {}><div class='literal'> <!-- {} -->".format(blockmargin,lgopts)
          self.css.addcss("[970] .literal-container { text-align:center; margin:0 0; }")
          self.css.addcss("[971] .literal { display:inline-block; text-align:left; }")
          while not re.match("<\/lg", self.wb[i]):
            i += 1
          self.wb[i] = "</div></div> <!-- end rend -->" # closing </lg>
          continue

        if re.search("poetry", lgopts):
          lgopts = re.sub("poetry", "", lgopts) # 17-Feb-2014
          if self.poetryindent == 'left':
              self.wb[i] = "<div class='poetry-container' {}><div class='lgp'> <!-- {} -->".format(blockmargin,lgopts)
              self.css.addcss("[230] div.lgp { }")
              self.css.addcss("[231] div.lgp p { text-align:left; text-indent:0; margin-top:0; margin-bottom:0; }")
              self.css.addcss("[233] .poetry-container { display:inline-block; text-align:left; margin-left:2em; }")
              while not re.match("<\/lg", self.wb[i]):
                i += 1
              # breaks: self.wb[i] = "</div></div> <div style='clear:both'/> <!-- end poetry block -->" # closing </lg>
              self.wb[i] = "</div></div> <!-- end poetry block --><!-- end rend -->" # closing </lg>
              continue
          else: # centered
              self.css.addcss("[233] .poetry-container { text-align:center; }")
              self.css.addcss("[230] div.lgp { display: inline-block; text-align: left; }")
              self.wb[i] = "<div class='poetry-container' {}><div class='lgp'> <!-- {} -->".format(blockmargin,lgopts)
              self.css.addcss("[231] div.lgp p { text-align:left; margin-top:0; margin-bottom:0; }")
              while not re.match("<\/lg", self.wb[i]):
                i += 1
              # breaks: self.wb[i] = "</div></div> <div style='clear:both'/> <!-- end poetry block -->" # closing </lg>
              self.wb[i] = "</div></div> <!-- end poetry block --><!-- end rend -->" # closing </lg>
              continue

  # process lines, in or outside a line group
  def doLines(self):
    self.dprint(1,"doLines")
    i = 0
    rendopts = ""
    inPoetry = False
    while i < len(self.wb):
      if re.search("<l[ig]", self.wb[i]): # skip links or linegroups
        i += 1
        continue

      m = re.search("<!-- rend='(.*?)' -->", self.wb[i])
      if m:
        rendopts = m.group(1)
      m = re.search("<!-- end rend -->", self.wb[i])
      if m:
        rendopts = ""

      if re.search("poetry-container", self.wb[i]):
        inPoetry = True # poetry lines are different
      if re.search("<!-- end poetry block -->", self.wb[i]):
        inPoetry = False

      m = re.search("<l(.*?)>", self.wb[i]) and not re.search("<li", self.wb[i])
      if m: # we have a line to rend
        self.wb[i] = self.m2h(self.wb[i], inPoetry, rendopts)
      i += 1

  # anything particular for derived-class media (epub, mobi, PDF)
  # can use this as an overridden method
  def mediaTweak(self):
    # for HTML, gather footnotes into a table structure
    i = 0
    while i < len(self.wb):
      m = re.match("<div id='f(.+?)'><a href='#r.+?'>\[.*?\]<\/a>", self.wb[i])
      if m:
        t = []
        t.append("<table style='margin:0 4em 0 0;' summary='footnote_{}'>".format(m.group(1)))

        t.append("<colgroup>")
        t.append("<col span='1' style='width: 3em;'/>")
        t.append("<col span='1'/>")
        t.append("</colgroup>")

        t.append("<tr><td style='vertical-align:top;'>")
        t.append(self.wb[i])
        del(self.wb[i])
        t.append("</td><td>")
        while not re.search("<!-- footnote end -->",self.wb[i]):
          t.append(self.wb[i])
          del(self.wb[i])
        del(self.wb[i]) # closing div
        t.append("</td></tr>")
        t.append("</table>")
        t.append("")
        self.wb[i:i+1] = t
        i += len(t)-1
      i += 1

  def processPageNumDisp(self):
    inBlockElement = False
    for i,line in enumerate(self.wb):
      if re.search("<p", line):
        inBlockElement = True
      m = re.search("⪦([^-]+)⪧", self.wb[i])
      if m:
        cpn = m.group(1)
        if 'h' in self.gentype:
          if inBlockElement:
            self.wb[i]=re.sub("⪦.+?⪧","<span class='pageno' title='{0}' id='Page_{0}'></span>".format(cpn), self.wb[i])
          else:
            self.wb[i]=re.sub("⪦.+?⪧","<div class='pageno' title='{0}' id='Page_{0}'></div>".format(cpn), self.wb[i])
        else:
          self.wb[i]=re.sub("⪦.+?⪧","<a name='Page_{0}' id='Page_{0}'></a>".format(cpn), self.wb[i])
      if re.search("<\/p", line):
        inBlockElement = False

  def processMarkup(self):
    self.doHeadings()
    # self.doDrama()
    self.doBlockq()
    self.doBreaks()
    self.doTables()
    self.doIllustrations()
    self.doLinks()
    self.doFootnotes()
    self.doLineGroups()
    self.doLines()

  def process(self):
    self.shortHeading()
    self.processLiterals()
    self.processPageNum()
    self.protectMarkup()
    self.preprocess()
    self.userHeader()
    self.userToc()
    self.processLinks()
    self.processTargets()
    from drama import DramaHTML
    DramaHTML(self.wb, self.css).doDrama();
    self.markPara()
    self.restoreMarkup()
    self.startHTML()
    self.processMarkup()
    self.processPageNumDisp()
    self.placeCSS()
    self.placeMeta()
    self.cleanup()
    self.plinks()
    self.endHTML()
    self.mediaTweak()

  def run(self):
    self.loadFile(self.srcfile)
    self.process()
    self.saveFile(self.dstfile)
# END OF CLASS HTML

# ===== class Text ============================================================

class Text(Book):
  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)
    self.srcfile = ifile
    self.dstfile = ofile

    self.qstack = [] # quote level stack

  def userHeader(self):
    self.dprint(1,"userHeader")
    i = 0
    while i < len(self.wb):
      m = re.match("<option name=[\"'](.*?)[\"'] content=[\"'](.*?)[\"']\s*\/?>", self.wb[i])
      if m:
        config.uopt.addopt(m.group(1), m.group(2))
        del self.wb[i]
        continue
      i += 1

  # save file to specified dstfile
  # overload to do special wrapping for text output only
  def saveFile(self, fn):
    while empty.match(self.wb[-1]): # no trailing blank lines
      self.wb.pop()
    nwrapped = 0
    self.dprint(1,"text:saveFile")
    if os.linesep == "\r\n":
      self.dprint(1, "running on Win machine")
      lineEnd = "\n"
    else:
      self.dprint(1, "running on Mac/Linux machine")
      lineEnd = "\r\n"
    lineWidth = 75
    f1 = open(fn, "w", encoding='utf-8')
    for index,t in enumerate(self.wb):
      if len(t) < lineWidth:
        f1.write( "{:s}{}".format(t,lineEnd) ) # no wrapping required
      else:
        sliceat = 0
        try:
          sliceat = t.rindex(" ", 0, lineWidth) # should be 74?
        except:
          cprint("Cannot wrap text: Line longer than " + str(lineWidth) + \
              " characters without a space.\n" + \
              t + "\nLine will be emitted without wrapping.")
          f1.write(t+"\n")
          continue
        m = re.match("( +)", t)
        if m:
          userindent = len(m.group(1))
        else:
          userindent = 0
        firstline = " " * userindent + t[0:sliceat].strip()
        f1.write( "{:s}{}".format(firstline,lineEnd) )
        cprint("Wrapping: " + t)
        t = t[sliceat:].strip()
        nwrapped += 1
        while len(t) > 0:
          if len(t) < lineWidth-3:
            f1.write( " " * userindent + "  {:s}{}".format(t,lineEnd) )
            t = ""
          else:
            try:
              sliceat = t.rindex(" ", 0, lineWidth)
            except:
              cprint("Line->" + t + "<");
              self.fatal("text: cannot wrap in saveFile")
            nextline = t[0:sliceat].strip()
            f1.write( " " * userindent + "  {:s}{}".format(nextline,lineEnd) )
            t = t[sliceat:].strip()
            nwrapped += 1
    f1.close()
    if nwrapped > 0:
      cprint ("info: {} lines rewrapped in text file.".format(nwrapped))

  # 19-Sep-2013 this should be superfluous.
  # removes tags or converts to text representation
  # one line as string
  def detag(self, s):
    s = re.sub("\[\[\/?i\]\]", "_", s) # italics
    s = re.sub("\[\[\/?b\]\]", "=", s) # bold
    s = re.sub("\[\[\/?u\]\]", "=", s) # underline

    m = re.search("\[\[sc\]\](.*?)\[\[\/sc\]\]", s) # small-caps
    while m:
      replace = m.group(1).upper()
      s = re.sub("\[\[sc\]\].*?\[\[\/sc\]\]", replace, s, 1)
      m = re.search("\[\[sc\]\](.*?)\[\[\/sc\]\]", s)

    m = re.search("\[\[g\]\](.*?)\[\[/g\]\]", s) # gesperrt
    while m:
      replace = ""
      x = m.group(1)
      for i in range(len(x)-1):
        replace += x[i] + " "
      replace += x[-1]
      s = re.sub("\[\[g\]\].*?\[\[/g\]\]", replace, s, 1)
      m = re.search("\[\[g\]\](.*?)\[\[/g\]\]", s)
    return s

  # Uppercase between the <sc> tags
  # NOTE: Do not uppercase any tags! e.g. <sc><g>xx</g></sc> do not
  # uppercase the <g> tags or they stop working!
  # self.wb[i] = re.sub("<sc>(.*?)<\/sc>", lambda pat: pat.group(1).upper(), line)
  def smallCaps(self, line):
    scTitle = (config.uopt.getopt("sc") == "titlecase")

    # return re.sub("<\/?sc>", "=", line) # small-caps

    if (scTitle):
      # Title-case: Just delete the tags
      return re.sub("<\/?sc>", "", line)

    while True:
      m = re.search("<sc>(.*?)<\/sc>", line)
      if not m:
        break
      sub = line[m.start(1):m.end(1)]
      n = len(sub)
      replace = ""
      off = 0
      while off < n:
        c = sub[off]
        if c == '<':
          # Ignore tags
          while True:
            c = sub[off]
            replace += c
            if c == '>':
              break
            off += 1
            if off >= n:
              break
        else:
          replace += c.upper()
        off += 1

      line = line[:m.start()] + replace + line[m.end():]

    return line

  # convert all inline markup to text equivalent at start of run
  def processInline(self):
    if self.italicdef == "decorative":
        replacewith = "" # decorative. ignore
    else:
        replacewith = "_" # emphasis. treat as <em>

    regexOL = re.compile("<\/?ol>")
    regexI = re.compile("<\/?i>")
    regexEM = re.compile("<\/?em>")
    regexB = re.compile("<\/?b>")
    regexU = re.compile("<\/?u>")
    regexDOT = re.compile(r"\. \.")
    regexFS = re.compile("<\/?fs>")
    regexFS1 = re.compile("<fs:.+?>")
    regexG = re.compile(r"<g>(.*?)<\/g>")

    i = 0
    while i < len(self.wb):

        self.wb[i] = regexOL.sub("‾", self.wb[i]) # overline 10-Apr-2014

        self.wb[i] = regexI.sub(replacewith, self.wb[i]) # italic
        self.wb[i] = regexEM.sub("_", self.wb[i]) # italic
        self.wb[i] = regexB.sub("=", self.wb[i]) # bold
        self.wb[i] = self.smallCaps(self.wb[i]) # smallcaps
        self.wb[i] = regexU.sub("=", self.wb[i]) # underline
        while regexDOT.search(self.wb[i]):
            self.wb[i] = regexDOT.sub(".□.", self.wb[i], 1) # spaces in ellipsis
        self.wb[i] = re.sub(r"…", "...", self.wb[i]) # unwrap ellipsis UTF-8 character for text
        self.wb[i] = re.sub(r"\\%",'⊐', self.wb[i]) # escaped percent signs (macros)
        self.wb[i] = re.sub(r"\\#",'⊏', self.wb[i]) # escaped octothorpes (page links)
        self.wb[i] = re.sub(r"\\<",'≼', self.wb[i]) # escaped open tag marks
        self.wb[i] = re.sub(r"\\>",'≽', self.wb[i]) # escaped close tag marks

        m = regexG.search(self.wb[i]) # gesperrt
        while m:
          replace = ""
          x = m.group(1)
          for j in range(len(x)-1):
            replace += x[j] + "□" # space after all but last character
          replace += x[-1] # last character
          self.wb[i] = regexG.sub(replace, self.wb[i], 1)
          m = regexG.search(self.wb[i])

        # new inline tags 2014.01.27
        # inline font size changes ignored in text
        # <fs:l> ... </fs>
        # <fs:xl> ... </fs>
        # <fs:s> ... </fs>
        # <fs:xs> ... </fs>
        self.wb[i] = regexFS.sub("", self.wb[i])
        self.wb[i] = regexFS1.sub("", self.wb[i])

        # remove table super/subscript balance tokens
        self.wb[i] = re.sub('\^\{\}', '', self.wb[i])
        self.wb[i] = re.sub('_\{\}', '', self.wb[i])

        i += 1

  # literals are marked as preformatted
  # tag delimeters are protected
  def processLiterals(self):
    self.dprint(1,"processLiterals")
    i = 0
    while i < len(self.wb):
      if re.match("<lit>", self.wb[i]):
        del self.wb[i] # <lit
        while not re.match("<\/lit>", self.wb[i]):
          self.wb[i] = re.sub(r"<",'⨭', self.wb[i])
          self.wb[i] = re.sub(r">",'⨮', self.wb[i])
          self.wb[i] = "▹"+self.wb[i]
          i += 1
        del self.wb[i] # </lit
      i += 1

  #
  def genToc(self):
    self.dprint(1,"genToc")
    tocrequest = False
    for index, line in enumerate(self.wb):
      self.checkLoop(index,32)
      if re.match("<tocloc", line):
        tocrequest = True
        m = re.match("<tocloc(.*?)>", line)
        if m:
            attrib = m.group(1)
        tocwhere = index
        self.wb[index] = "TOCPLACE"
        break
    if tocrequest:
      m = re.search("heading=[\"'](.*?)[\"']", attrib)
      usehead = "Table of Contents"
      if m:
          usehead = m.group(1)
      t = ["<l rend='center'>{}</l>".format(usehead)]
      t.append("<lg rend='block'>")
      for line in self.wb:
        if re.match(r"<heading", line):
          if re.search('toc="', line): # TOC content in double quotes
            # may have embedded single quotes
            # double quotes must be escaped
            line = re.sub(r'\\"', '\u25D0', line)
            # single quotes may be escaped
            line = re.sub(r"\\'", '\u25D1', line)
            m1 = re.match(r"<heading",line)
            m2 = re.search(r"level=[\"'](\d)[\"']",line)
            m3 = re.search(r"toc=\"(.*?)\"",line) # double quotes
            if m1 and m2 and m3:
              entry = " " * (2 * (int(m2.group(1)) -1)) + m3.group(1)
              entry = re.sub('\u25D0', '"', entry)
              entry = re.sub('\u25D1', "'", entry)
              entry = self.detag(entry)
              t.append("<l>{}</l>".format(entry))
          if re.search("toc='", line): # TOC content in single quotes
            # may have embedded double quotes
            # single quotes must be escaped
            line = re.sub(r"\\'", '\u25D1', line)
            # double quotes may be escaped
            line = re.sub(r'\\"', '\u25D0', line)
            m1 = re.match(r"<heading",line)
            m2 = re.search(r"level=[\"'](\d)[\"']",line)
            m3 = re.search(r"toc='(.*?)'",line) # single quotes
            if m1 and m2 and m3:
              entry = " " * (2 * (int(m2.group(1)) -1)) + m3.group(1)
              entry = re.sub('\u25D0', '"', entry)
              entry = re.sub('\u25D1', "'", entry)
              entry = self.detag(entry)
              t.append("<l>{}</l>".format(entry))
      t.append("</lg>")
      self.wb[tocwhere:tocwhere+1] = t

  def processPageNum(self):
    self.dprint(1,"processPageNum")
    i = 0
    while i < len(self.wb):
      if re.match("<pn", self.wb[i]):
        del self.wb[i]
        continue
      i += 1

  #
  def stripHeader(self):
    self.dprint(1,"stripHeader")
    i = 0
    while i < len(self.wb):
      if (self.wb[i].startswith("<option")
          or self.wb[i].startswith("<property")
          or self.wb[i].startswith("<meta")
          or re.match("\.[a-z]", self.wb[i])):
        del self.wb[i]
        continue
      i += 1

  # strip links and targets
  def stripLinks(self):
    self.dprint(1,"stripLinks")
    i = 0
    while i < len(self.wb):
      self.wb[i] = re.sub("<\/?link.*?>", "", self.wb[i])
      self.wb[i] = re.sub("<target.*?>", "", self.wb[i])
      i += 1

  # simplify footnotes, move <l> to left, unadorn page links
  # preformat hr+footnotemark
  def preProcess(self):
    fnc = 1
    self.dprint(1,"preProcess")
    for i in range(len(self.wb)):

      self.wb[i] = re.sub("<nobreak>", "", self.wb[i])  # 28-Mar-2014
      self.wb[i] = re.sub("<hang>", "", self.wb[i])  # 05-Jun-2014

      self.wb[i] = re.sub("#(\d+)#", r'\1', self.wb[i]) # page number links
      self.wb[i] = re.sub("#(\d+):.*?#", r'\1', self.wb[i]) # page number links type 2 2014.01.14

      while re.search("fn id=['\"]#['\"]", self.wb[i]):
        self.wb[i] = re.sub("fn id=['\"]#['\"]", "fn id='{}'".format(fnc), self.wb[i], 1)
        fnc += 1

      m = re.search(r"<fn id=['\"](.*?)['\"]\/?>", self.wb[i])
      if m:
        while m:
          self.wb[i] = re.sub(r"<fn id=['\"](.*?)['\"]\/?>", r'[\1]', self.wb[i], 1)
          m = re.search(r"<fn id=['\"](.*?)['\"]\/?>", self.wb[i])

      m = re.match("\s+(<l.*)$", self.wb[i])
      if m:
        self.wb[i] = m.group(1)

      # allow user shortcut <l/> -> </l></l>
      self.wb[i] = re.sub("<l\/>","<l></l>", self.wb[i])

      if self.wb[i].startswith("<hr rend='footnotemark'>"):
        s = re.sub("<hr rend='footnotemark'>", "▹-----", self.wb[i])
        self.wb[i:i+1] = [".rs 1", s, ".rs 1"]

      # remove any target tags
      if re.search("<target.*?\/>", self.wb[i]):
        self.wb[i] = re.sub("<target.*?\/>", "", self.wb[i])

    # leading spaces inside pre-marked standalong line
    # example:       <l>  This was indented.</l>
    # converts to:   <l>\ \ This was indented.</l>
    regex = re.compile(r"<l>(\s+)(.*?)<\/l>")
    i = 0
    while i < len(self.wb):
      m = regex.match(self.wb[i])
      if m:
        self.wb[i] = "<l>" + "\\ "*len(m.group(1)) + m.group(2) + "</l>"
      i += 1

  # after 19-Sep-2013 should be superfluous
  # protect inline markup
  def protectInline(self):
    self.dprint(1,"protectInline")
    i = 0
    while i < len(self.wb):
      s = self.wb[i]
      s = re.sub("<(\/?i)>", r"[[\1]]", s) # italics
      s = re.sub("<(\/?b)>", r"[[\1]]", s) # bold
      s = re.sub("<(\/?sc)>", r"[[\1]]", s) # small caps
      s = re.sub("<(\/?g)>", r"[[\1]]", s) # gesperrt
      s = re.sub("<(\/?u)>", r"[[\1]]", s) # underline
      s = re.sub(r"\\ ", "□", s) # hard spaces
      s = re.sub(r" ",'□', s) # unicode 0xA0, non-breaking space
      while re.search(r"\. \.", s):
        s = re.sub(r"\. \.", ".□.", s) # spaces in ellipsis
      s = re.sub(r"…", "...", s) # unwrap ellipsis UTF-8 character for text
      s = re.sub("<\/?r>", "", s) # red markup
      s = re.sub(r"\\%",'⊐', s) # escaped percent signs (macros)
      s = re.sub(r"\\#",'⊏', s) # escaped octothorpes (page links)
      s = re.sub(r"\\<",'≼', s) # escaped open tag marks
      s = re.sub(r"\\>",'≽', s) # escaped close tag marks

      self.wb[i] = s
      i += 1

  # mark lines
  # process any line in a line group that doesn't have <l> markup
  # include left-indent for poetry
  def markLines(self):
    self.dprint(1,"markLines")
    i = 0
    while i < len(self.wb):
      if re.match("<lg", self.wb[i]):
        i += 1
        while not re.match("</lg>", self.wb[i]):
          if not (re.match("<l", self.wb[i]) or re.match("<tb", self.wb[i])):
            self.wb[i] = re.sub(" ", "□", self.wb[i])
            self.wb[i] = "<l>{0}</l>".format(self.wb[i])
          i += 1
      i += 1

  # illustrations
  def illustrations(self):
    self.dprint(1,"illustrations")
    i = 0
    while i < len(self.wb):
      m = re.search("<illustration", self.wb[i])
      if m:
        # process with and without caption
        m = re.search("<illustration.*?\/>", self.wb[i])
        if m:
          self.wb[i] = "<l>[Illustration]</l>" # 19-Oct-2013
          i += 1
          continue
        m = re.search("<illustration.*?>", self.wb[i])
        if m:
          m = re.match("<caption>(.*?)</caption>", self.wb[i+1])
          if m:
            caption = m.group(1)
            # if there is a <br> in the caption, then user wants
            # control of line breaks. otherwise, wrap
            m = re.search("<br\/?>", caption)
            if m: # user control
              s = "[Illustration: " + caption + "]"
              s = re.sub("<br\/?>", "\n", s)
              t = []
              t.append("▹.rs 1")
              u = s.split('\n')
              for x in u:
                t.append("▹"+x) # may be multiple lines
              t.append("▹.rs 1")
              self.wb[i:i+3] = t
              i += len(t)
              continue
            else: # fpgen wraps illustration line
              s = "[Illustration: " + caption + "]"
              t = []
              t.append("▹.rs 1")
              u = wrap2(s)
              for x in u:
                t.append("▹"+x) # may be multiple lines
              t.append("▹.rs 1")
              self.wb[i:i+3] = t
              i += len(t)
              continue
      i += 1

  # rewrap
  # doesn't touch lines that are already formatted
  # honors <quote> level
  def rewrap(self):
    self.dprint(1,"rewrap")
    self.qstack = [""] # no initial indent
    i = 0
    regexTable = re.compile(r"<table(.*?)>")
    regexLg = re.compile("<lg(.*?)>")
    regexL = re.compile("<l(.*?)>(.*?)<\/l>")
    regexFootnote = re.compile(r"<footnote id=['\"](.*?)['\"]>")
    regexHeading = re.compile("<heading(.*?)>(.*?)</heading>")
    while i < len(self.wb):
      self.dprint(2,"[rewrap] {}: {}".format(i,self.wb[i]))
      if self.wb[i].startswith("<quote"):
        # is there a prescribed width?
        m = re.match("<quote rend='w:(.*?)em'>", self.wb[i])
        if m:
          rendw = int(m.group(1))
          # user-specified width (in characters). calculate indent
          indent = " " * ((config.LINE_WIDTH - rendw) // 2)
          self.qstack.append(indent)
          del(self.wb[i])
          continue
        newlevel = self.qstack[-1] + "    "
        self.qstack.append(newlevel)
        del(self.wb[i])
        continue

      if re.match("<\/quote>", self.wb[i]):
        self.qstack.pop()
        del(self.wb[i])
        continue

      if re.match("▹", self.wb[i]): # already formatted
        i += 1
        continue

      if empty.match(self.wb[i]): # toss blank lines
        del(self.wb[i])
        continue

      # ----- footnotes -------------------------------------------------------

      m = regexFootnote.match(self.wb[i])
      if m:
        # strip blank lines leading the footnote
        j = i+1;
        while j < len(self.wb):
          if self.wb[j] != '':
            break
          del self.wb[j]
        # Put the first line on the same line as the footnote number [#]
        # unless it is formatting itself, e.g. <lg>...</lg>
        fn = "[{}] ".format(m.group(1));
        if self.wb[j][0] != '<':
          self.wb[i] = fn + self.wb[j];
          del self.wb[i+1:j+1]
        else:
          self.wb[i] = fn
          del self.wb[i+1:j]
        # continue & wrap

      if self.wb[i].startswith("</footnote"):
        del self.wb[i]
        continue

      # ----- headings --------------------------------------------------------
      m = regexHeading.match(self.wb[i])
      if m:
        m1 = re.search("rend='(.*?)'", self.wb[i])
        if m1:
          rendatt = m1.group(1)
          if re.search("hidden", rendatt):
            del self.wb[i]
            i -= 1
            continue
        level = 1 # default
        att = m.group(1)
        head = m.group(2)
        m = re.search("level=[\"'](.*?)[\"']", att)
        if m:
          level = int(m.group(1))
        if level == 1:
          t = ["▹.rs 4"] # chapters
        if level == 2:
          t = ["▹.rs 2"] # sections
        if level == 3:
          t = ["▹.rs 1"] # sub-sections
        if level == 4:
          t = [] # sub-sub-sections
        # this may be an empty header element
        if empty.match(head):
          self.wb[i:i+1] = t
        else:
          s = self.detag(head)
          if "<br" in s: # split into separate lines
            s1 = re.sub(r"<br(\/)?>", "|", s)
            t1 = s1.split("|")
            for s2 in t1:
              if s2 == "":
                t.append('▹.rs 1')
              else:
                t.append('▹{:^72}'.format(s2))
          else:
            t.append('▹{:^72}'.format(s)) # all on one line
          if level == 1:
            t.append("▹.rs 2")
          else:
            t.append("▹.rs 1")
          self.wb[i:i+1] = t
          i += 1
        i += 1
        continue

      # ----- thought breaks and hr/footnotemark ------------------------------

      # any thought break in text is just centered asterisks
      if self.wb[i].startswith("<tb"):
        t = ["▹.rs 1"]
        t.append("▹                 *        *        *        *        *")
        t.append("▹.rs 1")
        self.wb[i:i+1] = t
        i += 1
        continue

      # ----- testing ---------------------------------------------------------

      # 19-Sep-2013
      if self.wb[i].startswith("<x"):
        t = ["If you had stood there in the edge of the bleak",
        "spruce forest, with the wind moaning dismally",
        "through the twisting trees—midnight of deep",
        "December—the Transcontinental would have looked",
        "like a thing of fire; dull fire, glowing with a",
        "smouldering warmth, but of strange ghostliness and",
        "out of place. It was a weird shadow, helpless and",
        "without motion, and black as the half-Arctic night",
        "save for the band of illumination that cut it in",
        "twain from the first coach to the last, with a",
        "space like an inky hyphen where the baggage car",
        "lay. Out of the North came armies of snow-laden",
        "clouds that scudded just above the earth, and with",
        "these clouds came now and then a shrieking mockery",
        "of wind to taunt this stricken creation of man and",
        "the creatures it sheltered—men and women who had",
        "begun to shiver, and whose tense white faces",
        "stared with increasing anxiety into the mysterious",
        "darkness of the night that hung like a sable",
        "curtain ten feet from the car windows."]
        s = " ".join(t)
        if re.match("<x1", self.wb[i]):
            t = wrap2(s)
        if re.match("<x2", self.wb[i]):
            t = wrap2(s, 2, 2, 2, -2)
        if re.match("<x3", self.wb[i]):
            t = wrap2(s, 2, 2, 2, 2)
        self.wb[i:i+1] = ["▹.rs 1"] + t + ["▹.rs 1"]
        i += len(t) + 2
        continue

      if self.wb[i].startswith("<hr"):
        m = re.search("rend='(.*?)'\/?>",self.wb[i])
        t = ["▹.rs 1"]
        if re.search("footnotemark", m.group(1)):
          t.append("▹-----")
        else: # all other hr's default to tb styling
          t.append("▹                   *     *     *     *     *")
        t.append("▹.rs 1")
        self.wb[i:i+1] = t
        i += 1
        continue


      # ----- page breaks --------------------------------------------------
      if self.wb[i].startswith("<pb"):
        self.wb[i] = "▹.rs 4"
        i += 1
        continue

      # ----- process standalone line -----------------------------------------
      m = regexL.match(self.wb[i])
      if m:
        handled = False

        if not empty.match(m.group(2)):
          thetext = (self.detag(m.group(2)))
          therend = m.group(1)

          m = re.search("sb:(\d+)", therend) # text spaces before
          if m:
            howmuch = m.group(1)
            self.wb.insert(i, ".rs {}".format(howmuch))
            i += 1

          m = re.search("sa:(\d+)", therend) # text spaces after
          if m:
            howmuch = m.group(1)
            self.wb.insert(i+1, ".rs {}".format(howmuch))

          m = re.search("ml:([\d\.]+)em", therend)
          if m:
            # indent left
            howmuch = int(m.group(1))
            self.wb[i] = self.qstack[-1] + " " * howmuch + thetext.strip()
            handled = True

          m = re.search("right", therend)
          if m:
            howmuch = 0
          else:
            m = re.search("mr:([\d\.]+)em", therend)
            if m:
              # indent right
              howmuch = int(m.group(1))

          if m:
            # rend="right" or rend="mr:0"
            rmar = config.LINE_WIDTH - len(self.qstack[-1]) - howmuch
            fstr = "{:>" + str(rmar) + "}"
            self.wb[i] = fstr.format(thetext.strip())
            handled = True

          m = re.search("center", therend)
          if m:
            # center
            self.wb[i] = "▹" + '{:^{width}}'.format(thetext.strip(), width=config.LINE_WIDTH)
            handled = True

          if not handled:
            self.wb[i] = self.qstack[-1] + thetext.strip()

        else:
          self.wb[i] = "▹"

        i += 1
        continue

      # ----- tables ----------------------------------------------------------

      m = regexTable.match(self.wb[i])
      if m:
        startloc = i
        j = i
        while not re.match("<\/table>", self.wb[j]):
          j += 1
        endloc = j
        self.wb[startloc:endloc+1] = self.makeTable(self.wb[startloc:endloc+1])

      # ----- process line group ----------------------------------------------
      m = regexLg.match(self.wb[i])
      if m:
        self.wb[i] = ".rs 1" # the <lg...
        i += 1 # first line of line group
        attrib = m.group(1)

        m = re.search("center", attrib)
        if m:
          while not re.match("<\/lg>",self.wb[i]):
            # bandaid alert: tb in center
            m = re.search(r"<tb", self.wb[i])
            if m:
              self.wb[i] = "▹                 *        *        *        *        *"
              i += 1
              continue
            m = re.match(r"<l.*?>(.*?)</l>", self.wb[i])
            if m:
              if not empty.match(m.group(1)):
                theline = self.detag(m.group(1))
                if len(theline) > 75:
                  s = re.sub("□", " ", theline)
                  cprint("warning (long line):\n{}".format(s))
                self.wb[i] = "▹" + '{:^{width}}'.format(theline, width=config.LINE_WIDTH)
              else:
                self.wb[i] = "▹"
            i += 1
          self.wb[i] = ".rs 1" # overwrites the </lg>
          continue

        m = re.search("right", attrib)
        if m:
          while not re.match("<\/lg>",self.wb[i]):
            m = re.match(r"<l.*?>(.*?)</l>", self.wb[i])
            if m:
              if not empty.match(m.group(1)):
                theline = self.detag(m.group(1))
                if len(theline) > 75:
                  s = re.sub("□", " ", theline)
                  cprint("warning (long line):\n{}".format(s))
                self.wb[i] = "▹" + '{:>72}'.format(theline)
              else:
                self.wb[i] = "▹"
            i += 1
          self.wb[i] = ".rs 1" # overwrites the </lg>
          continue

        # ----- begin poetry code ---------------------------------------------
        # poetry allows rends: ml:Nem, center, mr:0em
        m = re.search("poetry", attrib)
        if m:
          # first determine maximum width in poetry block
          j = i
          maxwidth = 0
          maxline = ""
          while not re.match("<\/lg>",self.wb[j]):
            self.wb[j] = self.detag(self.wb[j])
            theline = re.sub(r"<.+?>", "", self.wb[j]) # centering tags, etc.
            if len(theline) > maxwidth:
              maxwidth = len(self.wb[j])
              maxline = self.wb[j]
            j += 1
          maxwidth -= 3
          if maxwidth > 70:
            cprint("warning (long poetry line {} chars)".format(maxwidth))
            self.dprint(1,"  " + maxline) # shown in debug in internal form
          while not re.match("<\/lg>",self.wb[i]):
            m = re.match("<l(.*?)>(.*?)</l>", self.wb[i])
            if m:
              irend = m.group(1)
              itext = m.group(2)

              # center and right override ml
              if re.search("center", irend):
                tstr = "▹{0:^" + "{}".format(maxwidth) + "}"
                self.wb[i] = tstr.format(itext)
                i += 1
                continue
              if re.search("mr:0em", irend):
                tstr = "▹{0:>" + "{}".format(maxwidth) + "}"
                self.wb[i] = tstr.format(itext)
                i += 1
                continue

              m = re.search("ml:(\d+)em", irend)
              if m:
                isml = True
                itext = "□" * int(m.group(1)) + itext
              if not empty.match(itext):
                theline = self.detag(itext)
                if len(theline) > 75:
                  s = re.sub("□", " ", theline)
                  self.dprint(1,"warning: long poetry line:\n{}".format(s))
                if self.poetryindent == 'center':
                    leader = " " * ((config.LINE_WIDTH - maxwidth) // 2)
                else:
                    leader = " " * 4
                self.wb[i] = "▹" + self.qstack[-1] + leader + "{:<}".format(theline)

              else:
                self.wb[i] = "▹"

            i += 1
          self.wb[i] = ".rs 1"  # overwrites the </lg>
          continue
        # ----- end of poetry code --------------------------------------------

        # block allows rends: ml, mr
        m = re.search("block", attrib)
        if m:
          # find width of block
          j = i
          maxw = 0
          longline = ""
          while not re.match("<\/lg>",self.wb[j]):
            m = re.match("<l(.*?)>(.*?)</l>", self.wb[j])
            if m:
              therend = m.group(1)
              thetext = m.group(2)
              rendlen = 0
              textlen = 0
              m = re.search("m[lr]:([\d\.]+)em", therend)
              if m: # length may be affected
                rendlen = int(m.group(1))
              if not empty.match(thetext): # if not empty
                thetext = self.detag(thetext) # handle markup
              textlen = len(thetext) # calculate length
              totlen = rendlen + textlen
            else:
              self.fatal(self.wb[j])
            if totlen > maxw:
              maxw = totlen
              longline = thetext
            j += 1
          # have maxw calculated
          if maxw > config.LINE_WIDTH:
            self.dprint(1,"warning: long line: ({})\n{}".format(len(longline),longline))
            leader = ""
          else:
            leader = "□" * ((config.LINE_WIDTH - maxw) // 2) # fixed left indent for block

          while not re.match("<\/lg>",self.wb[i]):
            m = re.match("<l(.*?)>(.*?)</l>", self.wb[i]) # parse each line
            if m:
              s = m.group(2) # text part
              if not empty.match(s):
                thetext = self.detag(s) # expand markup
              else:
                thetext = ""
              irend = m.group(1)

              m = re.search("ml:([\d\.]+)em", irend) # padding on left?
              if m:
                thetext = "□" * int(m.group(1)) + thetext

              m = re.search("mr:([\d\.]+)", irend) # right aligned
              if m:
                inright = int(m.group(1))
                fstr = "{:>"+str(maxw-inright)+"}"
                thetext = fstr.format(thetext)
                thetext = re.sub(" ", "□", thetext)

              m = re.search("center", irend) # centered in block
              if m:
                thetext = " " * ((maxw - len(thetext))//2) + thetext
                thetext = re.sub(" ", "□", thetext)

              # if not specified,
              self.wb[i] = "▹" + leader + thetext
            else:
              self.wb[i] = "▹"
            i += 1
          self.wb[i] = ".rs 1"
          continue

        # if not handled, line group is left-align
        while not re.match("<\/lg>",self.wb[i]):
          m = re.match("<l.*?>(.*?)</l>", self.wb[i])
          if m:
            if empty.match(m.group(1)):
              self.wb[i] = "▹"
            else:
              theline = self.detag(m.group(1))
              if len(theline) > 75:
                s = re.sub("□", " ", theline)
                self.dprint(1,"warning: long line:\n{}".format(s))
              self.wb[i] = "▹" + '{:<72}'.format(theline)
          i += 1
        self.wb[i] = ".rs 1"

      # ----- wrap ------------------------------------------------------------

      # if it's not been handled, it's wrappable.
      # if it's still a tag, then it's unhandled. fatal.
      if re.match("<", self.wb[i]):
        self.fatal("unhandled tag@{}: {}".format(i, self.wb[i]))
      t = []
      mark1 = i
      while (i < len(self.wb)
          and not empty.match(self.wb[i])
          and not re.match("[<▹]",self.wb[i])):
        t.append(self.wb[i])
        i += 1
      mark2 = i
      # here at end of para or eof
      llen = config.LINE_WIDTH - (2 * len(self.qstack[-1]))
      leader = self.qstack[-1]
      s = " ".join(t)

      # u = self.wrap(s, llen, leader) # before 19-Sep-2013

      # leader is a string of spaces. # 19-Sep-2013
      lm = len(leader)
      rm = len(leader)
      li = 0
      ti = 0
      u = wrap2(s, lm, rm, li, ti)

      u.insert(0, ".rs 1")
      u.append(".rs 1")
      self.wb[mark1:mark2] = u
      i = mark1 + len(u)

  # make printable table from source code block
  def makeTable(self, t):

    for k, line in enumerate(t): # 11-Sep-2013
      t[k] = self.detag(line)
    tableLine = t[0]

    del t[0] # <table line
    del t[-1] # </table line

    tf = TableFormatter(tableLine, t)
    return tf.format()

  # merge all contiguous requested spaces
  def finalSpacing(self):
    self.dprint(1,"finalSpacing")

    # merge user-forced lines
    i = 0
    while i < len(self.wb):
      if "▹" == self.wb[i]:
        startloc = i
        spacecount = 1
        i += 1
        while i < len(self.wb) and "▹" == self.wb[i]:
          spacecount += 1
          i += 1
        self.wb[startloc:i] = [".rs {}".format(spacecount)]
        i -= 1
      i += 1

    for i in range(len(self.wb)):
      self.wb[i] = re.sub("\s+\.rs",".rs", self.wb[i])

    i = 0
    while re.match("▹?\.rs", self.wb[i]): # no initial vertical space
      del self.wb[0]
    while i < len(self.wb)-1:
      m1 = re.match("▹?\.rs (\d+)", self.wb[i])
      m2 = re.match("▹?\.rs (\d+)", self.wb[i+1])
      if m1 and m2:
        self.wb[i] = ".rs {}".format(max(int(m1.group(1)),int(m2.group(1))))
        del(self.wb[i+1])
      else:
        i += 1

  # convert space requests to real (vertical) spaces
  # convert space markers to real spaces
  # trim trailing spaces
  def finalRend(self):
    self.dprint(1,"finalRend")

    regexI = re.compile("\[\[\/?i\]\]")
    regexB = re.compile("\[\[\/?b\]\]")
    regexU = re.compile("\[\[\/?u\]\]")
    regexSC = re.compile("\[\[\/?sc\]\]")
    regexRS = re.compile(".rs (\d+)")

    i = 0
    while i < len(self.wb):
      l = self.wb[i]

      l = regexI.sub("_", l) # italics
      l = regexB.sub("=", l) # bold
      l = regexU.sub("=", l) # underline mark as bold
      l = regexSC.sub("=", l) # small caps marked as bold

      if False:
        line = []
        for c in l:
          if c == "▹" or c == "☊" or c == "☋": # ?? or start or end dropcap
            continue
          elif c == "□":
            c = " "
          elif c == "⊐": # escaped percent signs (macros)
            c = "%"
          elif c == "⊏": # escaped octothorpes (page links)
            c = "#"
          elif c == "≼": # <
            c = "<"
          elif c == "≼": # >
            c = ">"
          elif c == "⨭": # literal <
            c = "<"
          elif c == "⨮": # literal >
            c = ">"
          line.append(c)

        l = ''.join(line)

      else:
        l = re.sub("▹", "", l)
        l = re.sub("□", " ", l)
        l = re.sub('⊐', '%', l) # escaped percent signs (macros)
        l = re.sub('⊏', '#', l) # escaped octothorpes (page links)
        l = re.sub("≼", "<", l) # <
        l = re.sub("≽", ">", l) # >

        l = re.sub("⨭", "<", l) # literal <
        l = re.sub("⨮", ">", l) # literal >

        l = re.sub("☊", "", l) # start dropcap
        l = re.sub("☋", "", l) # end dropcap

      l = l.rstrip()
      m = regexRS.match(l)
      if m:
        nlines = int(m.group(1))
        t = []
        while nlines > 0:
          t.append("")
          nlines -= 1
        self.wb[i:i+1] = t
      else:
        self.wb[i] = l
      i += 1

  def process(self):
    self.userHeader()
    self.processInline()
    self.processLiterals()
    self.processPageNum()
    self.stripHeader()
    self.stripLinks()
    self.preProcess()
    self.protectInline() # should be superfluous as of 19-Sep-13
    self.illustrations()
    self.genToc()
    from drama import DramaText
    DramaText(self.wb).doDrama()
    self.markLines()
    self.rewrap()
    self.finalSpacing()
    self.finalRend()

  def run(self):
    self.loadFile(self.srcfile)
    self.process()
    self.saveFile(self.dstfile)
# END OF CLASS Text

class TableFormatter:

  FIRST_LINECHARS = "─┬┰━┯┳"
  MIDDLE_LINECHARS = "─┼╂━┿╋"
  LAST_LINECHARS = "─┴┸━┷┻"
  ISOLATED_LINECHARS = "───━━━"

  def __init__(self, tableLine, lines):
    self.tableLine = tableLine
    self.lines = lines
    self.nlines = len(lines)
    self.parseFormat()
    self.computeWidths()
    self.u = []

  #
  # Parse the <table> tag to pull off the rend= and pattern= attributes
  #
  def parseFormat(self):
    # the only rend text cares about is "pad"
    self.vpad = False
    m = re.search(r"rend='(.*?)'", self.tableLine)
    if m:
      rend = m.group(1)
      if re.search("pad", rend):
        self.vpad = True

    # pattern must be specified
    self.columns = parseTablePattern(self.tableLine)
    self.ncols = len(self.columns)

  #
  # Figure out how wide each column is going to be.
  #
  def computeWidths(self):
    totalwidth = tableWidth(self.columns)

    # any cells missing a width we need to calculate
    for col in self.columns:
      if col.width == 0:
        # need to calculate max width on each column
        for line in self.lines:
          u = line.split("|")
          for x, item in enumerate(u):
            item = item.strip()
            if len(item) > self.columns[x].width:
              self.columns[x].width = len(item)
        # and compute totalwidth against those maxes
        totalwidth = tableWidth(self.columns)
        dprint(1, "Computed table widths: " +
          toWidthString(self.columns) +
          ", total: " + str(totalwidth))
        break

    maxTableWidth = 75  # this is the size that saveFile decides to wrap at

    # for text, may have to force narrower to keep totalwidth < maxTableWidth
    while totalwidth > maxTableWidth:
      widest = 0
      for x, item in enumerate(self.columns):
        if item.width > widest:
          widest = item.width
          widex = x

      # Shrink widest column by one
      self.columns[widex].width -= 1

      # Recompute total width
      totalwidth = tableWidth(self.columns)
      cprint("warning: Table too wide: column " + str(widex) +
        "[" + str(widest) + "->" + str(self.columns[widex].width) +
        "], total width now " + str(totalwidth));

    # calculate tindent from max table width
    self.tindent = (maxTableWidth - totalwidth) // 2
    dprint(1, "Table totalwidth: " + str(totalwidth) +
      ", indenting: " + str(self.tindent) + "; final widths: " +
      toWidthString(self.columns))

  #
  # Create a single horizontal line.
  #
  def drawLine(self, isSingle, lineno, lines):
    line = "▹" + " " * self.tindent
    for colno, col in enumerate(self.columns):

      # Did the last line do a span over the next column?
      lastSpan = False
      if lineno > 0:
        lastLine = lines[lineno-1]
        if colno+1 < len(lastLine.getCells()):
          lastSpan = (lastLine.getCells()[colno+1].isSpanned())

      # Will the next line span over the next column?
      nextSpan = False
      if lineno+1 < self.nlines:
        nextLine = lines[lineno+1]
        if colno+1 < len(nextLine.getCells()):
          nextSpan = (nextLine.getCells()[colno+1].isSpanned())

      if lineno == 0 and nextSpan:
        chars = self.ISOLATED_LINECHARS
      elif lineno == 0:    # First line
        chars = self.FIRST_LINECHARS
      elif lineno+1 == self.nlines and not lastSpan:      # Last Line
        chars = self.LAST_LINECHARS
      elif lineno+1 == self.nlines and lastSpan:
        chars = self.ISOLATED_LINECHARS
      elif lastSpan and nextSpan:
        chars = self.ISOLATED_LINECHARS
      elif lastSpan:
        chars = self.FIRST_LINECHARS
      elif nextSpan:
        chars = self.LAST_LINECHARS
      else:
        chars = self.MIDDLE_LINECHARS

      off = 0 if isSingle else 3
      line += col.width * chars[off + 0]

      if not col.isLast:
        if col.lineBetween == 0:
          line += chars[off + 0]
        elif col.lineBetween == 1:
          line += chars[off + 1]
        else:
          line += chars[off + 2]
    return line

  #
  # Add a line to this table's output
  #
  def output(self, l):
    self.u.append(l.rstrip())

  def format(self):

    self.output(".rs 1")

    self.splitLines = splitTableLines(self.lines)

    # Format each row
    for lineno, tablerow in enumerate(self.splitLines):
      self.formatOneRow(lineno, tablerow, self.splitLines)

    self.output(".rs 1")

    return self.u

  #
  # Format up one source row of input.  Could result in multiple lines of output
  # tablerow is an array of TableRow objects
  #
  def formatOneRow(self, lineno, tablerow, splitLines):

      rowtext = tablerow.getCells()

      # Draw box characters with appropriate connectors for a line
      if tablerow.isSingle() or tablerow.isDouble():
        line = self.drawLine(tablerow.isSingle(), lineno, splitLines)
        # Add the box line to the output & finished with this row
        self.output(line)
        return

      if len(rowtext) == 0:
        # A completely blank line has no data, so hasAnyData will be false
        # But we need column delimiters on empty lines
        rowtext = [ TableCell(" ") ]

      # Cells may be wrapped onto multiple lines.
      # As we emit each cell, we reduce its content by the line just emitted
      # When all cells have become empty, we're done
      # Always go through once, so blank lines are processed
      hasData = True
      while hasData:
        self.formatOneOutputLine(rowtext)
        hasData = tablerow.hasAnyData()

      if self.vpad:
        self.output("▹" + ".rs 1")

  #
  # Output one real line of output.  The cells in rowtext are adjusted
  # for whatever was emitted
  # rowtext is an array of TableCell objects
  #
  def formatOneOutputLine(self, rowtext):
    line = ""
    nColData = len(rowtext)
    for n, column in enumerate(self.columns):
      if n < nColData:
        cell = rowtext[n]
      else:
        cell = TableCell("")

      # If this cell was spanned by the previous, ignore it.
      if cell.isSpanned():
        continue;

      # Look ahead into the following cells, to see if this is supposed to span
      nspan = cell.getSpan()
      lastSpanningColumn = self.columns[n+nspan-1]

      # Compute total column width, over all spanned columns
      w = column.width
      while nspan > 1:
        w += 1      # for the delimiter
        w += self.columns[n+nspan-1].width
        nspan -= 1
      if w <= 0 and len(cell.getData()) > 0:
        fatal("Unable to compute text table widths for " + tableLine + \
          ".  Specify them manually.")

      # Figure out what will fit in the current width and remove from the cell
      s2 = cell.getData().strip()
      try:
        if len(s2) <= w:
          # It all fits, done
          fits = s2.strip()
          remainder = ""
        else:
          # Doesn't fit; find the last space in the
          # allocated width, and break into this line, and
          # subsequent lines
          chopat = s2.rindex(" ", 0, w)
          fits = s2[0:chopat+1].strip()
          remainder = s2[chopat+1:].strip()
      except:
        fits = s2.strip()
        remainder = ""

      if n < nColData:
        # Replace cell with whatever is left, if we wrapped the cell
        cell.setData(remainder) # empty or something for another line

      # And format the part we decided to use onto the end of the current line
      if not cell.isDefaultAlignment():
        align = cell.getAlignment()
      else:
        align = column.align
      if align == 'left':
        fstr = '{:<'+str(w)+'}'
      elif align == 'center':
        fstr = '{:^'+str(w)+'}'
      elif align == 'right':
        fstr = '{:>'+str(w)+'}'
      line += fstr.format(fits)

      # Compute delimiter: sum of this column's after and next column's before
      delimiter = " "
      n = lastSpanningColumn.lineBetween
      if n > 0:
        if n > 1:
          delimiter = "┃"
        else:
          delimiter = "│"

      if not lastSpanningColumn.isLast:
        line += delimiter    # delimiter between cols; none on last or we'll wrap

    # Finally! Emit the line, indented appropriately
    self.output("▹" + " " * self.tindent + line)


def toWidthString(columns):
  s = "["
  for col in columns:
    if s != "[": s += ", "
    s += str(col.width)
  s += "]"
  return s

def tableWidth(columns):
  tw = 0
  for col in columns:
    if col.width != 0:
      tw += col.width + 1
  # TODO: subtract one for last column not having a delimiter?
  return tw

#
# Create an array, where each entry is a TableRow object.
# Within each TableRow object, is an array of TableCell objects
#
def splitTableLines(lines):
  # Split all the lines into cells
  splitLines = []
  for line in lines:
    splitLines.append(TableRow(line))
  return splitLines

class TableRow:
  SINGLE = 0
  DOUBLE = 1
  TEXT = 2

  # type: SINGLE, DOUBLE, or TEXT
  # columns: array of TableCell

  def __init__(self, line):
    if line == '_':
      self.type = self.SINGLE
    elif line == '=':
      self.type = self.DOUBLE
    else:
      self.type = self.TEXT
    rowtext = line.split("|")

    # Blank lines must still be processed.
    if len(rowtext) == 1 and rowtext[0] == '':
      rowtext = [ " " ]

    self.columns = []
    for col in rowtext:
      self.columns.append(TableCell(col))

    # For each column, look at following columns and figure out
    # how many columns wide it is
    nColData = len(self.columns)
    for n, col in enumerate(self.columns):
      nspan = 1
      for m in range(n+1, nColData):
        if self.columns[m].isSpanned():
          nspan += 1
        else:
          break
      col.spanning = nspan

  def getCells(self):
    return self.columns

  def isText(self):
    return self.type == self.TEXT

  def isSingle(self):
    return self.type == self.SINGLE

  def isDouble(self):
    return self.type == self.DOUBLE

  def hasAnyData(self):
    for col in self.columns:
      if col.getData() != "":
        return True
    return False

class TableCell:
  SPAN = 0
  TEXT = 1

  # type: SPAN or TEXT
  # data: the text, or ""
  # spanning: number of cells across
  # align: 0, 'l', 'r', 'c', for default, left, right or centre
  def __init__(self, data):
    if data == "<span>":
      self.type = self.SPAN
      self.data = ""
    else:
      self.type = self.TEXT
      self.data = data
    self.spanning = 1
    if data.startswith("<align=c>"):
      self.align = 'center'
    elif data.startswith("<align=r>"):
      self.align = 'right'
    elif data.startswith("<align=l>"):
      self.align = 'left'
    else:
      self.align = '0'
    if not self.isDefaultAlignment():
      self.data = self.data[9:]

    m = re.match("<class=(.*?)>", data)
    if m:
      self.userClass = m.group(1)
      self.data = self.data[m.end():]
    else:
      self.userClass = None

  def getUserClass(self):
    return self.userClass

  def getAlignment(self):
    return self.align

  def isDefaultAlignment(self):
    return self.align == '0'

  def getData(self):
    return self.data

  def setData(self, data):
    self.data = data

  def isSpanned(self):
    return self.type == self.SPAN

  # Number of columns wide
  def getSpan(self):
    return self.spanning

class TestMakeTable(unittest.TestCase):
  t = Text('ifile', 'ofile', 0, 'fmt')

  def test_simple(self):
    with self.assertRaises(SystemExit) as cm:
      u = self.t.makeTable([ "<table>", "</table>" ])
    self.assertEqual(cm.exception.code, 1)

  def common_assertions(self, u, n, textN):
    assert len(u) == n
    assert u[0] == '.rs 1' and u[n-1] == '.rs 1'
    #for l in u:
    #  t.uprint("Line: " + l)
    # 11 + 11 = 22, 75-22=53//2 = 26.
    # Should be 26 + 1 + 10 + 1 + 10 
    assert len(u[textN]) == 48 and u[textN][0] == '▹'

  def test_t1(self):
    u = self.t.makeTable([ "<table pattern='r10 r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1          2")

  def test_t2(self):
    u = self.t.makeTable([ "<table pattern='l10 r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1                   2")

  def test_t3(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         │         2")

  def test_t3hash(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         ┃         2")

  def test_t4(self):
    u = self.t.makeTable([ "<table pattern='l10|| r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         ┃         2")

  def test_t5(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "_", "1|2", "_", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("──────────┬──────────")
    assert u[2].endswith("1         │         2")
    assert u[3].endswith("──────────┴──────────")

  def test_t6(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "=", "1|2", "=", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("━━━━━━━━━━┯━━━━━━━━━━")
    assert u[2].endswith("1         │         2")
    assert u[3].endswith("━━━━━━━━━━┷━━━━━━━━━━")

  def test_t7(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "=", "1|2", "=", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("━━━━━━━━━━┳━━━━━━━━━━")
    assert u[2].endswith("1         ┃         2")
    assert u[3].endswith("━━━━━━━━━━┻━━━━━━━━━━")

  def test_span1(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "=", "1|<span>", "=", "</table>" ])
    assert u[1].endswith("━━━━━━━━━━━━━━━━━━━━━")
    assert u[2].endswith("1")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━")

  def test_span2(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "_", "1|<span>", "=", "</table>" ])
    assert u[1].endswith("─────────────────────")
    assert u[2].endswith("1")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━")

  def test_span3(self):
    u = self.t.makeTable([ "<table pattern='l10# r10 |l1'>", "=", "1|<span>|A", "=", "2|<span>|B", "=", "</table>" ])
    assert len(u) == 7
    assert u[1].endswith("━━━━━━━━━━━━━━━━━━━━━┯━")
    assert u[2].endswith("1                    │A")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━┿━")
    assert u[4].endswith("2                    │B")
    assert u[5].endswith("━━━━━━━━━━━━━━━━━━━━━┷━")

  def test_indent_of_horiz_line(self):
    u = self.t.makeTable([ "<table pattern='l1 r1'>", '_', 'A|B', '_', "</table>" ])
    # 75-3=72//2 = 36.
    # Should be 36 + 3
    assert len(u) == 5
    assert len(u[1]) == 39
    assert u[1].endswith("                                   ───")
    assert u[2].endswith("                                   A B")
    assert u[3].endswith("                                   ───")

  def test_blank_line(self):
    u = self.t.makeTable([ "<table pattern='l1 |r1'>", '_', '', '_', "</table>" ])
    # 75-3=72//2 = 36.
    # Should be 36 + 3
    assert len(u) == 5
    assert len(u[1]) == 39
    assert u[1].endswith("                                   ─┬─")
    assert u[2].endswith("                                    │")
    assert u[3].endswith("                                   ─┴─")

  def test_span4(self):
    u = self.t.makeTable([
      "<table pattern='l10# r10 ||l1'>",
        "_",
        "1|<span>|A",
        "_",
        "2|<span>|B",
        "_",
      "</table>"
    ])
    assert len(u) == 7
    assert u[1].endswith("─────────────────────┰─")
    assert u[2].endswith("1                    ┃A")
    assert u[3].endswith("─────────────────────╂─")
    assert u[4].endswith("2                    ┃B")
    assert u[5].endswith("─────────────────────┸─")

  def test_span5(self):
    u = self.t.makeTable([
      "<table pattern='l10# r10 ||l1'>",
        "_",
        "1|<span>|A",
        "_",
        "2|3|B",
        "_",
      "</table>"
    ])
    assert len(u) == 7
    assert u[1].endswith("─────────────────────┰─")
    assert u[2].endswith("1                    ┃A")
    assert u[3].endswith("──────────┰──────────╂─")
    assert u[4].endswith("2         ┃         3┃B")
    assert u[5].endswith("──────────┸──────────┸─")

  def test_2span1(self):
    u = self.t.makeTable([
      "<table pattern='r5# r5| r5| |l1'>",
        "_",
        "1|<span>|<span>|A",
        "_",
      "</table>" ])
    assert len(u) == 5
    self.assertRegexpMatches(u[1], "────────────────┰─$")
    assert u[2].endswith("               1┃A")
    assert u[3].endswith("────────────────┸─")

  def test_2span5(self):
    u = self.t.makeTable([
      "<table pattern='l5# r5| r5| l1'>",
        "_",
        "1|<span>|<span>|A",
        "_",
        "2|<span>|3|B",
        "_",
      "</table>"
    ])
    #for l in u:
    #  self.t.uprint("Line: " + l)
    assert len(u) == 7
    assert u[1].endswith("─────────────────┬─")
    assert u[2].endswith("1                │A")
    assert u[3].endswith("───────────┬─────┼─")
    assert u[4].endswith("2          │    3│B")
    assert u[5].endswith("───────────┴─────┴─")

  def test_wrap1(self):
    u = self.t.makeTable([
      "<table pattern='r8 r1'>",
        "word longer test w1|B",
      "</table>"
    ])
    assert len(u) == 5
    assert u[1].endswith("    word B")
    assert u[2].endswith("  longer")
    assert u[3].endswith(" test w1")

  def test_wrap_align(self):
    u = self.t.makeTable([
      "<table pattern='r8 r1'>",
        "<align=l>word longer test w1|B",
      "</table>"
    ])
    assert len(u) == 5
    assert u[1].endswith("word     B")
    assert u[2].endswith("longer")
    assert u[3].endswith("test w1")

  def test_wrap_align2(self):
    u = self.t.makeTable([
      "<table pattern='r8 r2'>",
        "<align=l>word longer test w1|<align=l>B",
        "word longer test w2|C",
      "</table>"
    ])
#    for l in u:
#      uprint("Line: " + l)
    assert len(u) == 8
    assert u[1].endswith("word     B")
    assert u[2].endswith("longer")
    assert u[3].endswith("test w1")
    assert u[4].endswith("    word  C")
    assert u[5].endswith("  longer")
    assert u[6].endswith(" test w2")

  # TODO: Tests for computing widths
  # TODO: Tests for computing some widths

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
  attributes = {}
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

# Parse a single attribute list
# e.g. rend='mr:5em mb:1em italic'
# would parse into
#  { 'mr' : '5em', 'mb' : '1em', 'italic' : '' }
def parseOption(arg):
  options = {}
  arg = arg.strip()
  while True:
    m = re.match("^([^ :]*)([ :])(.*)$", arg)
    if not m:
      # Rest of string is keyword
      if arg != "":
        options[arg] = ""
      break

    keyword = m.group(1)
    sep = m.group(2)
    rest = m.group(3)

    # Remove trailing semi-colon
    if rest[-1] == ';':
      rest = rest[0:-1]

    if sep == ' ':
      # Simple keyword, no value
      options[keyword] = ""
      arg = rest
    else:
      off = rest.find(' ')
      if off == -1:
        off = len(rest)
      value = rest[0:off]
      options[keyword] = value
      arg = rest[off:].lstrip()
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
    assert parseOption('mr:5em   mb:1em italic') ==  { 'mr' : '5em', 'mb' : '1em', 'italic' : '' }
  def test_OptionEmpty(self):
    assert parseOption('') == { }
  def test_OptionSpacesOnly(self):
    assert parseOption('') == { }
  def test_OptionSingleNoEq(self):
    assert parseOption('italic') == { 'italic' : '' }
  def test_OptionNoEqLeading(self):
    assert parseOption('poetry mt:5em') == { 'poetry' : '', 'mt' : '5em' }
  def test_OptionSingleNoEqTrailingSp(self):
    assert parseOption('italic  ') == { 'italic' : '' }
  def test_OptionNoEqSp(self):
    assert parseOption('   mt:33    italic  ') == { 'mt' : '33', 'italic' : '' }
  def test_OptionSingleNoEqLeadingSp(self):
    assert parseOption('  italic') == { 'italic' : '' }
  def test_OptionSingleEq(self):
    assert parseOption('mr:4em') == { 'mr' : '4em' }
  def test_OptionSingleEqTrailingSp(self):
    assert parseOption('mr:4em   ') == { 'mr' : '4em' }
  def test_OptionSingleEqLeadingSp(self):
    assert parseOption('  mr:4em') == { 'mr' : '4em' }
  def test_OptionSingleEqTrailingSp(self):
    assert parseOption('mr:4em   ') == { 'mr' : '4em' }

if __name__ == '__main__':
  from main import main
  main()
