#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
from subprocess import call
import re, sys, string, os, shutil
import textwrap
import codecs
import platform
import collections
from userOptions import userOptions
import config
import footnote
import font

from parse import parseTagAttributes, parseOption, parseLineEntry, \
  parseStandaloneTagBlock, \
  parseEmbeddedSingleLineTagWithContent, \
  parseEmbeddedTagWithoutContent, \
  parseStandaloneSingleLineTagWithContent
from msgs import cprint, uprint, dprint, fatal
import config
import template

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

summaryHang = 1
summaryBlock = 2
summaryIndent = 3
summaryCenter = 4

empty = re.compile("^$")

class TextWrapperDash(textwrap.TextWrapper):
  dashre = re.compile(r'(\s+|◠◠|—)')
  def _split(self, text):
    chunks = self.dashre.split(text)
    chunks = [c for c in chunks if c]
    return chunks

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

def wrap2h(s, lm, rm, li, l0, breakOnEmDash):  # 22-Feb-2014
  lines = []
  wrapper = TextWrapperDash() if breakOnEmDash else textwrap.TextWrapper()
  wrapper.width = config.LINE_WIDTH - lm - rm
  wrapper.break_long_words = False
  wrapper.break_on_hyphens = False
  wrapper.initial_indent = l0 * ' '
  wrapper.subsequent_indent = li * ' '
  s = re.sub("—", "◠◠", s) # compensate long dash
  lines = wrapper.wrap(s)
  for i, line in enumerate(lines):
      lines[i] = lines[i].replace("◠◠", "—") # restore dash
      lines[i] = lines[i].replace("◮", " ") # restore spaces from gesperrt or ti
      lines[i] = " " * lm + lines[i]
  return lines

def wrap2(s, lm=0, rm=0, li=0, ti=0, breakOnEmDash=False):  # 22-Feb-2014
  lines = []
  while "<br/>" in s:
    m = re.search("(.*?)<br\/>(.*)", s)
    if m:
      lines += wrap2h(m.group(1).strip(), lm, rm, li, ti, breakOnEmDash)
      s = m.group(2)
  lines += wrap2h(s.strip(), lm, rm, li, ti, breakOnEmDash) # last or only piece to wrap
  return lines

def alignLine(line, align, w, padChar=' '):
  # Figure out what will fit in the current width and remove from the cell
  remainder = line
  lines = []

  # Empty: always one line, never any padding
  if remainder == "":
    remainder = " "
    padChar = ' '

  indent = 0
  first = True

  while remainder != "":
    try:
      if len(remainder) <= w:
        # It all fits, done
        fits = remainder
        remainder = ""
      else:
        # Doesn't fit; find the last space in the
        # allocated width, and break into this line, and
        # subsequent lines
        if remainder[w] == ' ':
          # Exact fit?
          fits = remainder[0:w].rstrip()
          remainder = remainder[w:].strip()
        else:
          chopat = remainder.rindex(" ", 0, w)
          fits = remainder[0:chopat+1].rstrip()
          remainder = remainder[chopat+1:].strip()
    except:
      fits = remainder[0:w]
      remainder = remainder[w:]

    # Make sure we use the printable width
    pad = w - textCellWidth(fits)
    if align == 'left' or align == 'hang':
      pc = padChar

      # For lines using hang, don't pad with anything except space
      # if there are more lines to be done.
      if align == 'hang':
        if remainder != "":
          pc = ' '

      content = fits + (pc * pad)[0:pad]
    elif align == 'center':
      half = pad // 2
      content = (half * padChar)[0:pad] + fits + ((pad-half) * padChar)[0:pad]
    elif align == 'right':
      content = (pad * padChar)[0:pad] + fits

    lines.append(' ' * indent + content)

    # For hang, change indent after first line
    if first and align == 'hang':
      indent = 2
      w -= 2
      first = False

  return lines

class Book(object): #{
  wb = []

  def __init__(self, ifile, ofile, d, fmt):
    config.debug = d # numeric, 0=no debug, 1=function level, 2=line level
    self.debug = d # numeric, 0=no debug, 1=function level, 2=line level
    self.srcfile = ifile
    self.dstfile = ofile
    self.gentype = fmt
    self.back2 = -1 # loop detector
    self.back1 = -1
    self.italicdef = 'emphasis'
    self.uprop = self.userProperties()
    self.umeta = self.userMeta()
    self.templates = template.createTemplates(fmt)
    self.supphd = [] # user's supplemental header lines
    config.uopt.setGenType(fmt)

  def poetryIndent(self):
    return config.uopt.getOptEnum("poetry-style", {
        "left":"left",
        "center":"center"
      }, "left");

  def getFonts(self):
    fonts = {}
    for key,value in self.uprop.prop.items():
      if key.startswith("font-"):
        fonts[key[5:]] = value
    return fonts

  def getFontIndex(self, name):
    keyname = "font-" + name
    index = 0
    for key in self.uprop.prop.keys():
      if key.startswith(keyname):
        return index
      if key.startswith("font-"):
        index += 1
    fatal("<font:> tag has an unknown font: " + name + ". Font must have a property named " + keyname + ".")

  # display (fatal) error and exit
  def fatal(self, message):
    sys.stderr.write("fatal: " + message + "\n")
    exit(1)

  # level is set by calling program and is compared to self.debug.
  # >= means print msg
  def dprint(self, level, msg):
    if int(self.debug) >= level:
      cprint("{}: {}".format(self.__class__.__name__, msg))

  # internal class to save user properties
  class userProperties(object):
    def __init__(self):
      self.prop = {}
      self.addprop("leader-dots", ".")

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

    def add(self, key, value):
      self.addmeta("<meta name='" + key + "' content='" + value + "'/>")

    def show(self):
      t = []
      for s in self.meta:
        # Hack to convert &, because we now steal the meta before
        # we run the html preprocess code
        t.append("    " + s.replace("&", "&amp;"))
      return t

    def get(self, tag):
      for l in self.meta:
        m = re.match("<meta (.*?)/?>", l)
        if not m:
          continue
        args = m.group(1)
        attributes = parseTagAttributes("meta", args, [ "name", "content" ])
        if not "name" in attributes:
          fatal("Missing 'name' in meta tag: " + l)
        if not "content" in attributes:
          fatal("Missing 'content' in meta tag: " + l)
        name = attributes["name"]
        if name == tag and "content" in attributes:
          return attributes["content"]
      return None

    def getAsDict(self):
      d = {}
      for l in self.meta:
        m = re.match("<meta (.*?)/?>", l)
        if not m:
          continue
        args = m.group(1)
        attributes = parseTagAttributes("meta", args, [ "name", "content" ])
        if "name" in attributes:
          name = attributes["name"]
        if "content" in attributes:
          value = attributes["content"]
        d[name] = value
      return d

  def addcss(self, css):
    pass

  def shortHeading(self):
    self.dprint(1, "shortHeadings")
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
    dc_subject = None
    config.pn_cover = "images/cover.jpg"
    pn_displaytitle = ""
    m_generator = None
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

      m = re.match(r".generator (.*)", self.wb[i])
      if m:
        m_generator = m.group(1)
        where = i
        del(self.wb[i])

      m = re.match(r".tags (.*)", self.wb[i])
      if m:
        dc_subject = m.group(1)
        where = i
        del(self.wb[i])

      i += 1

    if shortused:
      self.umeta.add("DC.Title", dc_title)
      self.umeta.add("DC.Creator", dc_author)
      self.umeta.add("DC.Language", dc_language)
      if dc_created != "":
        self.umeta.add("DC.Created", dc_created)
        self.umeta.add("DC.date.issued", dc_created)

    if dc_subject != None:
      self.umeta.add("DC.Subject", dc_subject)
      self.umeta.add("Tags", dc_subject)

    if m_generator != None:
      self.umeta.addmeta("generator", m_generator)

    self.uprop.addprop("cover image", "{}".format(config.pn_cover))
    self.uprop.addprop("display title", "{}".format(pn_displaytitle))

  def addMeta(self):
    self.dprint(1,"userHeader")
    i = 0
    while i < len(self.wb):
      m = re.match("<meta", self.wb[i])
      if m:
        if not re.search("\/>$", self.wb[i]):
          self.wb[i] = re.sub(">$", "/>", self.wb[i])
        self.umeta.addmeta(self.wb[i])
        del self.wb[i]
        continue

      i += 1

  def addOptionsAndProperties(self):
    self.dprint(1,"addOptionsAndProperties")
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

      m = re.match("<option name=[\"'](.*?)[\"'] content=[\"'](.*?)[\"']\s*\/?>", self.wb[i])
      if m:
        config.uopt.addopt(m.group(1), m.group(2))
        del self.wb[i]
        continue
      i += 1

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

  summaryStyle = summaryHang

  def doSummary(self):
    self.dprint(1,"doSummary")
    options = {
      'hang':summaryHang,
      'block':summaryBlock,
      'indent':summaryIndent,
      'center':summaryCenter,
    }
    self.summaryStyle = config.uopt.getOptEnum("summary-style", options, summaryHang);

    parseStandaloneTagBlock(self.wb, "summary", self.oneSummary)

  def doIndex(self):
    self.dprint(1,"doIndex")
    parseStandaloneTagBlock(self.wb, "index", self.oneIndex)

  def doMulticol(self):
    self.dprint(1,"doMulticol")
    parseStandaloneTagBlock(self.wb, "multicol", self.oneMulticol)

  #
  # Retrieve the caption out of the <illustration>...</illustration> block
  #
  def trimCaptionTags(self, block):
    if len(block) == 0:
      return
    if not block[0].startswith("<caption>"):
      fatal("Illustration block does not start with <caption>: " + str(block))
    n = len(block)-1
    if not block[n].endswith("</caption>"):
      fatal("Illustration block does not end with </caption>: " + str(block))

    block[0] = block[0][9:]
    block[n] = block[n][0:-10]
    if block[n].strip() == '':
      del(block[n])
    if len(block) > 0:
      if block[0].strip() == '':
        del(block[0])

  #
  # Captions are traditionally joined, delimited by spaces. This conflicts
  # with markPara which paragraphs them. Someday we need to resolve this,
  # it causes a real mess in markPara
  #
  def getCaption(self, block):
    self.trimCaptionTags(block)
    return " ".join(block).strip()

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

  def blankLines(self, tag, before, after):
    self.dprint(1, tag + "+spacing")
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith(tag):
        if before:
          if i == 0 or not empty.match(self.wb[i-1]):
            t = self.wb[i]
            self.wb[i:i+1] = ["", t]
            i += 1
        if after:
          if i+1 == len(self.wb) or not empty.match(self.wb[i+1]):
            t = self.wb[i]
            self.wb[i:i+1] = [t, ""]
            i += 1
      i += 1

  def stripComments(self):
    i = 0
    while i < len(self.wb):
      if self.wb[i].startswith("//"): # line starts with "//"
        del self.wb[i]
        continue
      if self.wb[i].startswith("<!--") and "-->" in self.wb[i]:
        del self.wb[i]
        continue
      # multi-line
      if self.wb[i].startswith("<!--"):
        while not "-->" in self.wb[i]:
          del self.wb[i]
          if i == len(self.wb):
            fatal("Open comment marker <!-- found at line " + str(i) + \
                " with no closing marker. Check for a typo in closing -->");
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
        while not "*/" in self.wb[i]:
          del self.wb[i]
          if i == len(self.wb):
            fatal("Open comment marker /* found at line " + str(i) + \
                " with no closing marker. Check for a typo in closing */");
          continue
        del self.wb[i] # closing comment line
        continue
      i += 1

  def applyMacros(self):
    # process macros
    self.dprint(1, "define macros")
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
    self.dprint(1, "apply macros")
    i = 0
    regex = re.compile("%([^; ].*?)%")
    for i, line in enumerate(self.wb):
      while True:
        m = regex.search(line)
        if not m:
          break
        macroName = m.group(1)
        if not macroName in macro: # is this in our list of macros already defined?
          self.fatal("macro %{}% undefined in line\n{}".format(macroName, self.wb[i]))
        line = line[0:m.start(0)] + macro[macroName] + line[m.end(0):]
        self.wb[i] = line
      i += 1

  def applyConditionals(self):
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

  def fixPageNumberTags(self):
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

  def literals(self):
    self.dprint(1, "protecting literals")

    def oneLitBlock(openTag, block):
      attributes = parseTagAttributes("lit", openTag, [ "section" ])
      if "section" in attributes:
        value = attributes["section"]
        opts = parseOption("lit/section", value, [ "head" ])
        if "head" in opts:
          # Entire block is simply appended to supphd, which will be emitted
          # with the rest of the css later
          self.supphd += block
          return []

      # No section='head'; so just protect the block.
      for i, line in enumerate(block):
        line = line.replace("<", '⨭') # literal open tag marks
        line = line.replace(">", '⨮') # literal close tag marks
        block[i] = config.FORMATTED_PREFIX + line
      return block

    parseStandaloneTagBlock(self.wb, "lit", oneLitBlock)

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

    self.stripComments()

    # Before or after conditions & macros?
    self.fixPageNumberTags()

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
        self.wb[i] = self.wb[i].replace("<I>", "<i>")
        self.wb[i] = self.wb[i].replace("<B>", "<b>")
        self.wb[i] = self.wb[i].replace("</I>", "</i>")
        self.wb[i] = self.wb[i].replace("</B>", "</b>")
      i += 1

    self.applyConditionals()

    self.applyMacros()

    self.createUserDefinedTemplates()

    self.literals()

    # ensure heading has a blank line before
    self.blankLines("<heading", True, False)

    # ensure line group has a blank line before
    self.blankLines("<lg", True, False)
    self.blankLines("</lg", False, True)

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
    self.blankLines("<illustration", True, False)
    self.blankLines("</illustration", False, True)

    for i, line in enumerate(self.wb):
      # map <br> to be legal
      line = line.replace("<br>", "<br/>")
      self.wb[i] = line

    # normalize rend format to have trailing semicolons
    # honour <lit>...</lit> blocks
    # FIX ME! This changes rend='...' when it is not inside <...>
    # TODO: Make all users of rend= use parseOption, and then remove this!
    in_pre = False
    regexDouble = re.compile('rend="(.*?)"')
    regexSingle = re.compile("rend='(.*?)'")
    for i,line in enumerate(self.wb):
      if "<lit" in line:
        in_pre = True
      if "</lit" in line:
        in_pre = False
      m = regexDouble.search(line)
      if m:
        self.wb[i] = re.sub('rend=".*?"', "rend='{}'".format(m.group(1)), self.wb[i])
      m = regexSingle.search(self.wb[i])
      if not in_pre and m:
        therend = m.group(1)
        therend = re.sub(" ",";", therend)
        therend += ";"
        therend = re.sub(";;", ";", therend)
        self.wb[i] = re.sub("rend='.*?'", "rend='{}'".format(therend), self.wb[i])

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
    footnote.reformat(self.wb)
  ## End of loadFile method

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

  # loop detector
  def checkLoop(self, i, c):
    if i == self.back1 and i == self.back2:
      self.fatal("loop detected at line {}: {} (referrer: {})".format(i, self.wb[i], c))
    self.back2 = self.back1
    self.back1 = i

  def createUserDefinedTemplates(self):
    self.dprint(1, "user-defined templates")

    parseStandaloneTagBlock(self.wb, "template", self.templates.defineTemplate)

  def macroTemplates(self):
    self.dprint(1, "applying macro templates")

    # Now we can set the globals, since we have now extracted all the metadata
    self.templates.setGlobals(self.umeta.getAsDict())

    regexMacro = re.compile("<expand-macro\s+(.*?)/?>")
    i = 0
    while i < len(self.wb):
      line = self.wb[i]

      # What about multiple macro expansions on a line?  Or recursion?
      # Make it simpler for now by just punting: if you expand, then we move on
      # to the next line.
      m = regexMacro.search(line)
      if m:
        opts = m.group(1)
        replacement = self.templates.expandMacro(opts)
        prefix = line[:m.start(0)]
        suffix = line[m.end(0):]

        if len(replacement) == 0:
          # If the template returns nothing, then you end up with a single line of
          # the prefix and suffix around the <expand-macro>
          replacement = [ prefix + suffix ]
        else:
          # Otherwise the prefix goes on the first line; and the suffix at the end of
          # the last; which might be the same single line.
          replacement[0] = prefix + replacement[0]
          replacement[-1] = replacement[-1] + suffix
        self.wb[i:i+1] = replacement
        i += len(replacement)
        continue

      i += 1

  def run(self):
    self.loadFile(self.srcfile)
    self.process()
    self.saveFile(self.dstfile)

  # Common processing output independent code.
  # Invoked as super() followed by output dependent code in the subclasses
  def process(self):
    self.shortHeading()
    self.addOptionsAndProperties()
    self.addMeta()
    self.macroTemplates()
    self.chapterHeaders()
    footnote.relocateFootnotes(self.wb)

  def __str__(self):
    return "fpgen"

  # Process <chap-head> and <sub-head> tags.
  # Calls into output-specific method `headers'.
  def chapterHeaders(self):
    self.dprint(1, "chapter headers")
    i = 0
    emittitle = True
    usingBook = False
    while i < len(self.wb):
      line = self.wb[i]
      if line.startswith("<chap-head"):
        keys = {}
        opts, chapHead = parseLineEntry("chap-head", line)
        j = i+1
        while j < len(self.wb) and re.match("^\s*$", self.wb[j]):
          j += 1
        if j == len(self.wb):
          fatal("End of file after <chap-head>")
        attributes = parseTagAttributes("chap-head", opts, [ "pn", "id", "emittitle", "break", "type" ])
        pn = attributes["pn"] if "pn" in attributes else None
        id = attributes["id"] if "id" in attributes else None
        nobreak = True if "break" in attributes and attributes["break"] == "no" else False

        # Override first, with emittitle tag
        if "emittitle" in attributes:
          v = attributes["emittitle"] 
          if v == "yes":
            emittitle = True
          elif v == "no":
            emittitle = False
          else:
            fatal("<chap-head> emittitle must be yes or no, not " + v)

        book = False
        if "type" in attributes:
          type = attributes["type"]
          if type == "chap":
            book = False
          elif type == "book":
            book = True
            usingBook = True
          else:
            fatal("<chap-head> type must be chap or book, not " + type)

        line = self.wb[j]
        if line.startswith("<sub-head"):
          opts, subHead = parseLineEntry("sub-head", line)
          # No opts for now
        else:
          # Do not eat this line!
          subHead = None
          j -= 1

        replacement = self.headers(chapHead, subHead, pn, id, emittitle, nobreak, book, usingBook)
        self.wb[i:j+1] = replacement
        i += len(replacement)
        emittitle = False
        continue

      if line.startswith("<sub-head>"):
        fatal("Found <sub-head> not after a <chap-head>: " + line)

      i += 1
#}
# end of class Book

# Parse the font size on <lg> and <table>
def parseFontSize(options1, options2, options3, textOpt):
  style = ''
  found = False
  for key in fontSizeMap:
    if key in options1:
      style = "font-size:" + fontSizeMap[key] + ";"
      found = True
  if not found:
    for key in fontSizeMap:
      if key in options2:
        style = "font-size:" + fontSizeMap[key] + ";"

  if "fs" in options3:
    value = options3['fs']
    if not re.match("[\d\.]+em$", value):
      fatal("Font size option fs:" + value + ", must be specified in ems." +
        " Found in options: " + textOpt)
    style = "font-size:{};".format(options3['fs'])

  return style

# Common parsing for the lg tag, to pull out and parse the rend attribute,
# and figure out the alignment.
# Returns (opts, align), where opts is the parsed rend attribute array,
# and align is one of the six alignment options.
def parseLgOptions(args):
  lgopts = args
  attributes = parseTagAttributes("l", lgopts, [ 'rend', 'id' ])
  rend = attributes['rend'] if 'rend' in attributes else ""
  opts = parseOption("<lg>/rend=", rend, lgRendOptions)

  center = "center" in opts
  left = "left" in opts
  right = "right" in opts
  block = "block" in opts
  poetry = "poetry" in opts
  blockRight = "block-right" in opts

  modeCount = \
      (1 if center else 0) + \
      (1 if left else 0) + \
      (1 if right else 0) + \
      (1 if block else 0) + \
      (1 if blockRight else 0) + \
      (1 if poetry else 0)
  if modeCount > 1:
    fatal("Multiple lg mode options given in " + rend)
  if modeCount == 0:
    left = True

  if left:
    align = "left"
  elif right:
    align = "right"
  elif center:
    align = "center"
  elif block:
    align = "block"
  elif poetry:
    align = "poetry"
  elif blockRight:
    align = "block-right"
  else:
    fatal("Cannot happen: " + args)

  return (opts, align)

def parseTablePattern(line, isHTML, uprop = None):
  # pull the pattern
  if isHTML:
    m = re.search("patternhtml=[\"'](.*?)[\"']", line)
  else:
    m = re.search("patterntext=[\"'](.*?)[\"']", line)
  if not m:
    m = re.search("pattern=[\"'](.*?)[\"']", line)
    if not m:
      fatal("No pattern= option to table: " + line)
  tpat = m.group(1)

  cols = []

  list = tpat.split()

  for oneCol in list:
    col = ColDescr(oneCol, line, uprop)
    cols.append(col)

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

# Column Descriptor. A Parsed version of the user defined pattern
class ColDescr: #{
  def __init__(self, description, tableLine = "?", uprop = None):
    self.userWidth = 0
    self.width = 0
    self.align = ""
    self.valign = "top"
    self.lineBefore = 0
    self.lineAfter = 0
    self.lineBetween = 0
    self.lineBeforeStyle = '|'
    self.lineAfterStyle = '|'
    self.isLast = False
    self.hang = False
    self.preserveSpaces = False
    self.leaderName = None
    self.leaderChars = None
    self.uprop = uprop

    self.parse(description, tableLine)

  def parse(self, oneCol, tableLine):
    off = 0
    n = len(oneCol)

    # Each column is |*[lrch][TBC][S]#*|*

    # Parse leading |
    c = oneCol[off]
    if c == '#' or c == '|':
      self.lineBeforeStyle = c
      while oneCol[off] == c:
        self.lineBefore += 1
        off += 1
        if off == n:
          fatal("Incorrect table specification " + oneCol + " inside " + tableLine)
      # Double line needs to be wider or you can't see it!
      if self.lineBeforeStyle == '#':
        self.lineBefore *= 4

    # Parse column horizontal and vertical alignment
    while True:
      c = oneCol[off]
      if c == 'c':
        self.align = "center"
      elif c == 'l':
        self.align = "left"
      elif c == 'h':
        self.align = "left"
        self.hang = True
      elif c == 'r':
        self.align = "right"
      elif c == 'T':
        self.valign = "top"
      elif c == 'B':
        self.valign = "bottom"
      elif c == 'C':
        self.valign = "middle"
      elif c == 'S':
        self.preserveSpaces = True
      elif c == 'L':
        # Parse leader in format either L, or L(X) where X is a string
        name = "dots"
        if off+1 < n:
          c = oneCol[off+1]
          if c == '(':
            off += 1
            try:
              end = oneCol.index(')', off)
            except ValueError:
              fatal("Incorrect table column specification " + oneCol +
                  " inside " + tableLine + ": L(name) not correctly specified")
            name = oneCol[off+1:end]
            off = end

        # Note leader-dots is always there
        self.leaderName = "leader-" + name
        if not self.leaderName in self.uprop.prop:
          fatal("Incorrect table specification " + oneCol + " inside " +
            tableLine + ": L(" + name + "): requires a property named " +
            self.leaderName)
        self.leaderChars = self.uprop.prop[self.leaderName]
      else:
        break
      off += 1
      if off == n:
        break

    # Does the column have a user-specified width?
    self.userWidth = False
    self.width = 0
    if off < n:
      # Yes, parse the user-specified width
      digOff = off
      while oneCol[off].isdigit():
        off += 1
        if off == n:
          break
      if digOff != off:
        self.userWidth = True
        self.width = int(oneCol[digOff:off])

      if off < n:
        # Parse trailing |
        c = oneCol[off]
        if c == '#' or c == '|':
          self.lineAfterStyle = c
          while oneCol[off] == c:
            self.lineAfter += 1
            off += 1
            if off == n:
              break
          # Double line needs to be wider or you can't see it!
          if self.lineAfterStyle == '#':
            self.lineAfter *= 4

        if off != n:
          fatal("Incorrect table specification " + oneCol + " inside " + tableLine + ": >>>" + c + "<<<")

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  def __str__(self):
    return str(self.__dict__)
#    return str(self.userWidth) + ":" + \
#      str(self.width) + ":" + \
#      self.align + ":" + \
#      str(self.lineBefore) + ":" + \
#      str(self.lineAfter)

# } End of class ColDescr


# ===== class Lint ============================================================

class Lint(Book): #{

  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)

  def balanced(self, reports, line, lineno, lineGroupStartLine):
    for tag in [ "sc", "i", "b", "u", "g" ]:
      self.verifyMatching(reports, tag, line, lineno, lineGroupStartLine)

  def verifyMatching(self, reports, tag, line, lineno, lineGroupStartLine):
    open = "<" + tag + ">"
    close = "</" + tag + ">"

    # Match all opens to a close
    oLine = line
    while True:
      m = re.search(open, line)
      if not m:
        break
      line = re.sub(open, "", line, 1)
      if not re.search(close, line):
        if lineGroupStartLine == None:
          reports.append("error:unclosed " + open +
            " tag at line number: {}\n{}".format(lineno, oLine))
        else:
          reports.append("error:unclosed " + open +
              " tag on line " + str(lineno) +
              ", in line group starting at line " + str(lineGroupStartLine) +
              ".\n" +
              "Font changes must be balanced on each line, within a line group.\n" +
              "Check for a missing end line group tag (</lg>).\n" +
              "Line: " + oLine)
      line = re.sub(close, "", line, 1)

    # Match all closes to an open
    line = oLine
    while True:
      m = re.search(close, line)
      if not m:
        break
      line = re.sub(close, "", line, 1)
      if not re.search(open, line):
        if lineGroupStartLine == None:
          reports.append("error:unopened " + close +
            " tag at line number: {}\n{}".format(lineno, oLine))
        else:
          reports.append("error:unopened " + close +
              " tag on line " + str(lineno) +
              ", in line group starting at line " + str(lineGroupStartLine) +
              ".\n" +
              "Font changes must be balanced on each line, within a line group.\n" +
              "Check for a missing end line group tag (</lg>).\n" +
              "Line: " + oLine)
      line = re.sub(open, "", line, 1)

  # Lint: Main logic: Override Book.processCommon
  def process(self):
    #### Do NOT call super()
    inLineGroup = False
    reports = []
    for i,line in enumerate(self.wb):

      if re.match("<tb\/?>", line) and (not empty.match(self.wb[i+1]) or not empty.match(self.wb[i-1])):
        reports.append("non-isolated <tb> tag:\nline number: {}".format(i))

      if re.match("<pb\/?>", line) and (not empty.match(self.wb[i+1]) or not empty.match(self.wb[i-1])):
        reports.append("non-isolated <pb> tag:\nline number: {}".format(i))

      # all lines stand alone
      standaloneL = line.startswith("<l ") or line.startswith("<l>")
      if standaloneL:
        if not re.search("<\/l>$", line):
          reports.append("line missing closing </l>:\nline number: {}\n{}".format(i,line))
      else:
        if re.search("<\/l>$", line):
          reports.append("line missing opening <l>:\nline number: {}\n{}".format(i,line))

      # no nested line groups
      if line.startswith("<lg"):
        if inLineGroup:
          reports.append("line group error: unexpected <lg tag\nline number: {}\nunclosed lg started at line: {}".format(i,lineGroupStartLine))
        inLineGroup = True
        lineGroupStartLine = i
      if line.startswith("</lg"):
        if not inLineGroup:
          reports.append("line group error: closing a </lg that is not open:\nline number: {}".format(i))
        inLineGroup = False

      # while in a line group all inline tags must be paired
      # Also in a <l>...</l>, and <heading>...</heading>
      if inLineGroup:
        self.balanced(reports, line, i, lineGroupStartLine)

      if standaloneL or re.match("<heading[> ]", line):
        self.balanced(reports, line, i, None)

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

  # Lint does not save the file
  def saveFile(self, fn):
    pass

  def __str__(self):
    return "fpgen lint"
#}
# END OF CLASS Lint

# ===== class HTML ============================================================

class HTML(Book): #{

  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)
    self.css = self.CSS()
    self.srcfile = ifile
    self.dstfile = ofile
    self.cpn = 0
    self.showPageNumbers = False
    self.tableCount = 0
    self.styleClasses = {}


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
        lines = s[6:].split("\n")
        for l in lines:
          t.append("      " + l)
      return t

  def addcss(self, css):
    self.css.addcss(css)

  # translate marked-up line to HTML
  # input:
  #   s:   line in <l>...</l> markup
  #   pf:  true if line being used in poetry
  #   lgr: encompassing markup (i.e. from a lg rend attribute)

  # This is only an ordered dictionary so that the values come out in
  # the same order as they used to, which is only required for tests,
  # to not show changes.
  marginMap = collections.OrderedDict(
    [
      ("ml", 'margin-left'),
      ("mr", 'margin-right'),
      ("mt", 'margin-top'),
      ("mb", 'margin-bottom'),
    ]
  )

  lgMarginMap = collections.OrderedDict(
    [
      ("mt", 'margin-top'),
      ("mb", 'margin-bottom'),
    ]
  )

  def parseMargins(self, options, string, mm = marginMap):
    thestyle = ""
    for key in mm:
      if key in options:
        value = options[key]
        if value != '0' and not value.endswith('em') and not value.endswith('px'):
          fatal("Margin option " + key + " value " + value +
            " must either be 0 or end with em.  Found in options: " +
            string)
        if value == '0':
          value = '0em'
        thestyle += self.marginMap[key] + ":" + value + ";"
    return thestyle

  def m2h(self, s, pf=False, lgr=''):
    incoming = s
    m = re.match("<l(.*?)>(.*?)<\/l>",s)
    if not m:
      self.fatal("malformed line: {}".format(s))
    # combine rend specified on line with rend specified for line group
    attributes = parseTagAttributes("l", m.group(1), [ 'rend', 'id' ])
    rend = attributes['rend'] if 'rend' in attributes else ""
    optionsLG = parseOption("<lg>/rend=", lgr, lRendOptions) if lgr != '' else {}
    optionsL = parseOption("<l>/rend=", rend, lRendOptions)
    options = optionsLG.copy()
    options.update(optionsL)
    if len(options) > 0:
      dprint(1, "Options: " + str(options))
    #t1 = m.group(1).strip() + " " + lgr
    t2 = m.group(2)

    thisLineRaw = t2

    setid = attributes['id'] if 'id' in attributes else ''

    if re.match("(◻+)", t2) and 'center' in options:
      self.fatal("indent requested on centered line. exiting")
    if re.match("(◻+)", t2) and 'right' in options:
      self.fatal("indent requested on right-aligned line. exiting")

    # with poetry, leave indents as hard spaces; otherwise, convert to ml
    m = re.match("(\s+)", t2) # leading spaces on line
    if m:
      if not pf: # not poetry
        options['ml'] = '{}em'.format(len(m.group(1)))
        t2 = re.sub("^\s+","",t2)
      else:
        t2 = "&#160;"*len(m.group(1)) + re.sub("^\s+","",t2)

    thetext = t2
    thestyle = "" # reset the style

    # ----- alignment -----------
    if 'center' in options:
      thestyle += "text-align:center;"

    if 'right' in options:
      thestyle += "text-align:right;"

    if 'left' in options:
      thestyle += "text-align:left;"

    if 'align-last' in options:
      if not pf:
        fatal("align-last only legal inside poetry")
      if self.lastLineRaw == None:
        fatal("Use of rend='align-last' without a last line: " + thetext)
      alignLast = True
      self.css.addcss("[234] .poetry-align-last { visibility:hidden; }")
    else:
      alignLast = False

    alignTriple = 'triple' in options

    alignCount = \
      (1 if alignTriple else 0) + \
      (1 if alignLast else 0) + \
      (1 if 'center' in options else 0) + \
      (1 if 'right' in options else 0) + \
      (1 if 'left' in options else 0)

    if alignCount > 1:
      fatal("Multiple alignment options given in: " + rend + "; " + thetext)

    # ----- margins -------------
    if 'mr' in options:
      thestyle += 'text-align:right;'
    elif 'ml' in options:
      thestyle += 'text-align:left;'

    thestyle += self.parseMargins(options, rend + " " + lgr)

    # ----- font size -----------
    # This is based on keys, not values; so the <l> options don't overwrite the
    # <lg> options, i.e. <lg rend='lg'>...<l rend='xlg'>...</l>...</lg>
    # would end up with both lg and xlg as keys.  So check the <l> options first,
    # and only look at the <lg> options if there were no size options there
    thestyle += parseFontSize(optionsL, optionsLG, options, rend + " " + lgr)

    # ----- font presentation ---
    if "under" in options:
      thestyle += "text-decoration:underline;"
    if "bold" in options:
      thestyle += "font-weight:bold;"
    if "sc" in options or "smallcaps" in options:
      thestyle += "font-variant:small-caps;"
    if "i" in options or "italic" in options:
      thestyle += "font-style:italic;"

    thestyle = thestyle.strip()
    hstyle = ""
    if not empty.match(thestyle):
      hstyle = "style='{}'".format(thestyle)
    hid = ""
    if not empty.match(setid):
      hid = "id='{}'".format(setid)

    if alignTriple:
      pieces = thetext.split('|')
      if len(pieces) != 3:
        fatal("<l> triple alignment does not have three pieces: " + thetext)
      s = """
        <div class='center' {} {}>
          <table border="0" cellpadding="4" cellspacing="0" summary="triple" width="100%">
          <tr>
            <td align='left'>{}</td>
            <td align='center'>{}</td>
            <td align='right'>{}</td>
          </tr>
          </table>
        </div>
      """.format(hstyle, hid, pieces[0], pieces[1], pieces[2])
    elif pf: # poetry
      self.css.addcss("[511] div.lgp p.line0 { text-indent:-3em; margin:0 auto 0 3em; }")
      if alignLast:
        thetext = "<span class='poetry-align-last'>" + self.lastLineRaw + "</span>" + thetext
      paraStart = "<p class='line0' {} {}>".format(hstyle,hid)
      if self.dropCapQuoteMarker in thetext:
        s = thetext.replace(self.dropCapQuoteMarker, paraStart)
      else:
        s = paraStart + thetext
      if self.dropCapMarkerA in s:
        s = s.replace(self.dropCapMarkerA, "")
      s += "</p>"
    else:
      self.css.addcss("[510] p.line { text-indent:0; margin-top:0; margin-bottom:0; }")
      s =  "<p class='line' {} {}>".format(hstyle,hid) + thetext + "</p>"
    s = re.sub(" +>", ">", s) # trailing internal spaces in tags

    # ensure content in blank lines
    if re.search("<p class='line[^>]*?><\/p>", s):
      s = re.sub("<p class='line[^>]*?><\/p>", "<p class='line'>&#160;</p>", s)

    if thisLineRaw != "":
      self.lastLineRaw = thisLineRaw
    return s

  def preprocessOneBlock(self, block):
    i = 0
    while i < len(block):
      l = block[i]

      if not l.startswith(config.FORMATTED_PREFIX):
        # protect special characters
        l = l.replace("\\ ", '⋀') # escaped (hard) spaces
        l = l.replace(" ",   '⋀') # unicode 0xA0, non-breaking space
        l = l.replace("\\%", '⊐') # escaped percent signs (macros)
        l = l.replace("\\#", '⊏') # escaped octothorpes (page links)
        l = l.replace("\\<", '≼') # escaped open tag marks
        l = l.replace("\\>", '≽') # escaped close tag marks

        l = l.replace("<thinsp>", "\u2009")
        l = l.replace("<nnbsp>", "\u202f")
        l = l.replace("<wjoiner>", "\u2060")

        while ". ." in l:
          l = l.replace(". .", '.⋀.') # spaces in spaced-out ellipsis
        l = l.replace("\\'",'⧗') # escaped single quote
        l = l.replace('\\"','⧢') # escaped double quote
        l = l.replace(r"&",'⧲') # ampersand
        l = l.replace("<l/>","<l></l>") # allow user shortcut <l/> -> </l></l>
        block[i] = l
      i += 1

  # HTML: preprocess text
  def preprocess(self):
    self.dprint(1,"preprocess")

    self.preprocessOneBlock(self.wb)

    # TODO: Get rid of this silly method
    def lgBlock(lgopts, block):
      ##### THIS DOES NOT WORK! has been changed to rend='center;' so never matches!
      if re.search("rend='center'",lgopts): # it's a centered line group
        for i, line in enumerate(block):
          # already marked? <l or <ill..
          if not re.match("^\s*<", line) or re.match("<link", line):
            block[i] = "<l>" + line + "</l>" # no, mark it now.
      else: # not a centered line group so honor leading spaces
        illustration = False
        for i, line in enumerate(block):
          # Ignore illustration within the <lg>
          if line.startswith("</illustration"):
            illustration = False
            continue
          if illustration:
            continue
          if line.startswith("<illustration"):
            if not re.search("/>", line):
              illustration = True
            # Illustrations are aligned based on their own rend, not
            # an enclosing <lg>, so don't tag with <l>...</l>
            continue
          if not re.match("^\s*<l", line) or re.match("<link", line): # already marked?
            line = "<l>" + line.rstrip() + "</l>"
            m = re.match(r"(<l[^>]*>)(\s+)(.*?)<\/l>", line)
            if m:
              line = m.group(1) + "◻"*len(m.group(2)) + m.group(3) + "</l>"
            block[i] = line
      return [ "<lg " + lgopts + ">" ] + block + [ "</lg>" ]

    parseStandaloneTagBlock(self.wb, "lg", lgBlock)

    i = 1
    while i < len(self.wb)-1:
      if self.wb[i].startswith("<quote") and not empty.match(self.wb[i+1]):
        t = [self.wb[i], ""]
        # inject blank line
        self.wb[i:i+1] = t
        i += 1
      if self.wb[i].startswith("</quote>") and not empty.match(self.wb[i-1]):
        t = ["", "</quote>"]
        # inject blank line
        self.wb[i:i+1] = t
        i += 1
      i += 1

    # whitespace around <footnote and </footnote
    i = 0
    while i < len(self.wb):
      if re.match("<\/?footnote", self.wb[i]):
        self.wb[i:i+1] = ["", self.wb[i], ""]
        i += 2
      i += 1

  # page numbers honored in HTML, if present
  # convert all page numbers to absolute
  def processPageNum(self):
    self.dprint(1,"processPageNum")

    cpn = ""
    for i, line in enumerate(self.wb):
      if line.startswith(config.FORMATTED_PREFIX): # no page numbers in preformatted text
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
      headingNumber = 1
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

          # id for the link from the TOC
          if m4:
            hid = m4.group(1)
          else:
            # id is not optional.  Generate one, and add it into the <heading>
            hid = 'h_' + str(headingNumber)
            headingNumber += 1
            self.wb[i] = re.sub("<heading", "<heading id='" + hid + "'", line)

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

    def oneLink(arg, content, orig):
      attributes = parseTagAttributes("link", arg, [ "target" ])
      if "target" not in attributes:
        fatal("<link> must always have a target attribute: " + orig)
      target = attributes["target"]
      return "⩤a href='#" + target + "'⩥" + content + "⩤/a⩥"

    parseEmbeddedSingleLineTagWithContent(self.wb, "link", oneLink)

  #
  # These tags are real hacks--used for two things
  # a) To put the paragraph marker in the correct place when we have a leading
  # quote; since we want the quote as a <div> in the margin; not part of the
  # paragraph.  Perhaps we could instead insert a new line prior to the
  # paragraph with a FORMATTED_PREFIX?
  #
  # b) When a paragraph begins with a drop cap, then we don't want to
  # indent the paragraph. i.e. put in <nobreak> before the paragraph.
  # Could we do that somehow by putting <nobreak> before the line? But we
  # don't have the line here...
  #
  dropCapQuoteMarker = '<!--quote-->'
  dropCapMarker = '⩤!--dropcap--⩥'
  dropCapMarkerA = '<!--dropcap-->'
  def processDropCaps(self):
    self.dprint(1,"DropCaps")

    def oneDrop(arg, letter, orig):
      attributes = parseTagAttributes("drop", arg, [ "src", "rend" ])

      hasquote = letter.startswith("“")
      if hasquote:
        letter = letter[1:]

      imgFile = None
      if "drop-"+letter in self.uprop.prop:
        imgFile = self.uprop.prop["drop-" + letter]
      else:
        if "src" in attributes:
          imgFile = attributes["src"]

      # No image file? Generate simply a large letter
      if imgFile == None:
        self.addcss(dropCapCSS)

        # If starts with a double-quote, this will remove it completely,
        # or it will be very large and look funny.
        # This is what most printed texts do.
        return self.dropCapMarker + "⩤span class='dropcap'⩥" + letter + "⩤/span⩥"

      # Width is, in priority
      # a) rend='w:XX%'
      # b) property drop-width-Letter
      # c) property drop-width
      # d) unspecified, i.e. pixel width of image
      width = None
      if "rend" in attributes:
        # Only a width
        rendAtt = parseOption("drop", attributes["rend"], [ "w" ])
        if "w" in rendAtt:
          width = "width:" + rendAtt["w"] + ";"
      if width == None:
        if "drop-width-"+letter in self.uprop.prop:
          width = "width:" + self.uprop.prop["drop-width-" + letter]
        elif "drop-width" in self.uprop.prop:
          width = "width:" + self.uprop.prop["drop-width"]
        else:
          width = ""

      # For image-based, we add an open quote in the left margin
      quote = '⩤div style="position:absolute;margin-left:-.5em; font-size:150%;"⩥“⩤/div⩥' + self.dropCapQuoteMarker if hasquote else ""

      return self.dropCapMarker + quote + "⩤img src='" + imgFile + "' style='float:left;" + \
        width + "' alt='" + letter + "'/⩥"

    parseEmbeddedSingleLineTagWithContent(self.wb, "drop", oneDrop)

  def processTargets(self):
    self.dprint(1,"processTargets")

    def oneTarget(arg, orig):
      attributes = parseTagAttributes("target", arg, [ "id" ])
      if "id" not in attributes:
        fatal("<target> must always have an id attribute: " + orig)
      id = attributes["id"]
      return "⩤a id='" + id + "'⩥⩤/a⩥"

    parseEmbeddedTagWithoutContent(self.wb, "target", oneTarget)

  def protectMarkup(self, block):
    self.dprint(1,"protectMarkup")
    for i,line in enumerate(block):
      block[i] = block[i].replace("<em>",'⩤em⩥')
      block[i] = block[i].replace("</em>",'⩤/em⩥')
      block[i] = block[i].replace("<i>",'⩤i⩥')
      block[i] = block[i].replace("</i>",'⩤/i⩥')
      block[i] = block[i].replace("<sc>",'⩤sc⩥')
      block[i] = block[i].replace("</sc>",'⩤/sc⩥')
      block[i] = block[i].replace("<b>",'⩤b⩥')
      block[i] = block[i].replace("</b>",'⩤/b⩥')
      block[i] = block[i].replace("<u>",'⩤u⩥')
      block[i] = block[i].replace("</u>",'⩤/u⩥')
      block[i] = block[i].replace("<g>",'⩤g⩥')
      block[i] = block[i].replace("</g>",'⩤/g⩥')
      block[i] = block[i].replace("<r>",'⩤r⩥')
      block[i] = block[i].replace("</r>",'⩤/r⩥')
      block[i] = re.sub(r"<(fn id=['\"].*?['\"]/?)>",r'⩤\1⩥', block[i])

      # new inline tags 2014.01.27
      block[i] = block[i].replace("</fs>", r'⩤/fs⩥')
      block[i] = re.sub("<(fs:.+?)>", r'⩤\1⩥', block[i])

      block[i] = block[i].replace("</font>", r'⩤/font⩥')
      block[i] = re.sub("<(font:.+?)>", r'⩤\1⩥', block[i])

      # overline 13-Apr-2014
      if "<ol>" in block[i]:
        self.css.addcss("[116] .ol { text-decoration:overline; }")
      block[i] = block[i].replace("<ol>", '⎧') # overline
      block[i] = block[i].replace("</ol>", '⎫') # overline

  # No paragraphs in this particular tag; for a tag which must start a line
  def skip(self, tag, wb, start):
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
  def skipSameline(self, tag, wb, start):
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

  # <caption>...</caption> tags are considered paragraphs themselves.
  # Extract them, and format them up separately.
  def markIllustrationPara(self):
    def oneIllustration(args, block):
      self.trimCaptionTags(block)
      if len(block) == 0:
        # No caption, return unchanged
        return [ "<illustration" + args + "/>" ]

      # Have just the caption. Mark it up as text paragraphs.
      self.markParaArray(block, "caption")

      # Turn the caption back into an illustration, for future reparsing in
      # the normal flow in doIllustrations(). Why can't we mark the paragraphs
      # at that point? Because ordering is all-important in this mess...
      block.insert(0, "<caption>")
      block.insert(0, "<illustration" + args + ">")
      block.append("</caption>")
      block.append("</illustration>")
      return block
    parseStandaloneTagBlock(self.wb, "illustration", oneIllustration, allowClose = True)

  def markPara(self):
    defaultStyle = "indent" if config.uopt.getopt("pstyle") == "indent" else "line"
    self.css.addcss(paragraphCSS)

    self.markParaArray(self.wb, defaultStyle)
    self.markIllustrationPara()

  # The different tags we use for paragraphs
  hangPara = "<p class='hang'>"
  linePara = "<p>"
  blockPara = "<p class='noindent'>"
  indentPara = "<p class='pindent'>"
  captionPara = "<p class='caption'>"

  styleToHtml = {
    "hang" : hangPara,
    "indent" : indentPara,
    "nobreak" : blockPara,
    "list" : "XXX",
    "line" : "<p>",
    "caption" : captionPara,
  }

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
  def markParaArray(self, wb, globalStyle):
    self.dprint(1,"markPara")

    paragraphStyle = globalStyle
    defaultStyle = globalStyle

    noFormattingTags = [ "lg", "table", "illustration" ]

    # No formatting inside footnotes if they are sidenotes
    if footnote.getFootnoteStyle() == footnote.sidenote:
      noFormattingTags.append("footnote")

    i = 0
    while i < len(wb):

      line = wb[i]

      # A whole bunch of ways that a line or group of lines isn't formatted
      if line.startswith(config.FORMATTED_PREFIX): # preformatted
        i += 1
        continue

      # No formatting inside these tags
      for tag in noFormattingTags:
        j = self.skip(tag, wb, i)
        if i != j:
          i = j
          continue

      # No formatting inside these, but slightly different parsing
      for tag in [ "sidenote" ]:
        j = self.skipSameline(tag, wb, i)
        if i != j:
          break
      if i != j:
        i = j
        continue

      # <pstyle=XXX> alone on a line
      # Sets defaultStyle either as specified, or to global default
      if line.startswith("<pstyle="):
        defaultStyle = None
        line = line.strip()
        for j,style in enumerate(pstyleTags):
          if line == style:
            defaultStyle = paraStyles[j]
            break
        if defaultStyle == None:
          fatal("Bad pstyle: " + wb[i])
        if defaultStyle == "default":
          defaultStyle = globalStyle

        # Next paragraph will be this style
        paragraphStyle = defaultStyle

        # Remove <pstyle> line completely
        del(wb[i])
        if i > 0:
          i -= 1
        continue

      # See if there is a single-paragraph style
      if line.startswith("<"):
        line = line.strip()
        for j,tag in enumerate(paraTags):
          if line.startswith(tag):
            line = line[len(tag):]
            wb[i] = line
            # Override for next paragraph
            paragraphStyle = paraStyles[j]
            break

      # outside of tables and line groups, no double blank lines
      if wb[i-1] == "" and line == "":
        del (wb[i])
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
      n = len(wb)
      start = i
      while i < n:
        if self.isParaBreak(wb[i]):
          break
        block.append(wb[i])
        i += 1

      # Paragraph now accumulated into block[]
      if paragraphStyle == "list":
        self.css.addcss(paragraphListCSS)
        w = block[0].split(" ")
        l = "<span class='listTag'>" + w[0] + "</span>" + \
          "<p class='listPara'>" + " ".join(w[1:])
        block[0] = l
        block[-1] += "</p>"
        block.insert(0, "<div class='listEntry'>")
        block.append("</div>")
      else:
        # If the line has a drop cap, don't indent
        if self.dropCapMarker in block[0] and paragraphStyle == "indent":
          paragraphStyle = "nobreak"
        block[0] = block[0].replace(self.dropCapMarker, "")
        tag = self.styleToHtml[paragraphStyle]
        if self.dropCapQuoteMarker in block[0]:
          block[0] = block[0].replace(self.dropCapQuoteMarker, tag)
        else:
          block[0] = tag + block[0]
        block[-1] += "</p>"

      wb[start:i] = block
      i = start + len(block)

      # After emitting paragraph, revert to default paragraph style
      paragraphStyle = defaultStyle

    return wb

  def isParaBreak(self, line):
    if line == "":
      return True
    if line[0] == config.FORMATTED_PREFIX: # preformatted
      return True
    if line[0] == '<' and line != "<br/>":
      return True
    return False

  fontmap = {
    'l' : '⓯',
    'xl' : '⓰',
    's' : '⓱',
    'xs' : '⓲'
  }

  # protectMarkup was used to hide just our known, inline font-related tags
  # by converting <> into ⩤⩥.
  #
  # restoreMarkup converts the tags back to <>, and then converts the
  # full tag into single character internal values.
  #
  # cleanup will then convert those single character internal values into 
  # actual html strings.
  def restoreMarkup(self, block):
    self.dprint(1,"restoreMarkup")
    reFS = re.compile(r"<fs:(.*?)>")
    reFont = re.compile(r"<font:(.*?)>")
    allFonts = None
    for i,line in enumerate(block):
      block[i] = block[i].replace("⩤",'<')
      block[i] = block[i].replace("⩥",'>')

      if "<i>" in block[i]:
        self.css.addcss("[110] .it { font-style:italic; }")
      block[i] = block[i].replace("<i>","①")
      block[i] = block[i].replace("</i>",'②')

      if "<b>" in block[i]:
        self.css.addcss("[111] .bold { font-weight:bold; }")
      block[i] = block[i].replace("<b>","③")
      block[i] = block[i].replace("</b>",'②')

      if "<sc>" in block[i]:
        self.css.addcss("[112] .sc { font-variant:small-caps; }")
      block[i] = block[i].replace("<sc>","④")
      block[i] = block[i].replace("</sc>",'②')

      if "<u>" in block[i]:
        self.css.addcss("[113] .ul { text-decoration:underline; }")
      block[i] = block[i].replace("<u>","⑤")
      block[i] = block[i].replace("</u>",'②')

      if "<g>" in block[i]:
        self.css.addcss("[114] .gesp { letter-spacing:0.2em; }")
      block[i] = block[i].replace("<g>","⑥")
      block[i] = block[i].replace("</g>",'②')

      if "<r>" in block[i]:
        self.css.addcss("[115] .red { color: red; }")
      block[i] = block[i].replace("<r>","⑦")
      block[i] = block[i].replace("</r>",'②')

      # new inline tags 2014.01.27
      while True:
        m = reFS.search(block[i])
        if not m:
          break
        size = m.group(1)
        if not size in self.fontmap:
          fatal("<fs> tag has an unknown or unsupported size " + size +
              " in line " + block[i])
        block[i] = block[i][:m.start()] + self.fontmap[size] + block[i][m.end():]

      while True:
        m = reFont.search(block[i])
        if not m:
          break
        font = m.group(1)
        fontChar = config.FONT_BASE + self.getFontIndex(font)
        dprint(1, "Using font " + str(fontChar) + " to " + font)
        block[i] = block[i][:m.start()] + str(chr(fontChar)) + block[i][m.end():]

      block[i] = block[i].replace("</fs>",'⓳')
      block[i] = block[i].replace("</font>", config.FONT_END)

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

    # Figure out the display title.
    # Either specified by <property name='display title'>
    # or generate a default via .title; or via <meta name="DC.Title">
    # If they didn't use .title, <meta>, or <property>, use the source
    # filename
    displayTitle = ""
    if "display title" in self.uprop.prop:
      displayTitle = self.uprop.prop["display title"]
    if displayTitle == "":
      dc_title = self.umeta.get("DC.Title")
      if dc_title == None:
        cprint("warning: no display title or title given")
        dc_title = re.sub("-src.txt", "", self.srcfile)
      displayTitle = "The Distributed Proofreaders Canada eBook of {}".format(dc_title)
    t.append("    <title>{}</title>".format(displayTitle))

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

  cleanTrans = {
    '⧗': "'",    # escaped single quote
    '⧢': '"',    # double quote
    '⧲': '&amp;',# ampersand

    '◻': '&ensp;',# wide space
    '⋀': '&nbsp;',# non-breaking space

    '▹': None,   # unprotect literal lines
    '⧀': '<',    # protected tag braces
    '⧁': '>',
    '⊐': '%',    # escaped percent signs (macros)
    '⊏': '#',    # escaped octothorpes (page links)
    '≼': '&lt;', # escaped <
    '≽': '&gt;', # escaped >

    '⨭': '<',    # protected <
    '⨮': '>',    # protected >
    "①": "<span class='it'>",
    "②": "</span>",
    "③": "<span class='bold'>",
    "④": "<span class='sc'>",
    "⑤": "<span class='ul'>",
    "⑥": "<span class='gesp'>",
    "⑦": "<span class='red'>",

    "⎧": "<span class='ol'>",
    "⎫": "</span>",

    # Inline font size changes
    '⓯': "<span style='font-size:larger'>",
    '⓰': "<span style='font-size:x-large'>",
    '⓱': "<span style='font-size:smaller'>",
    '⓲': "<span style='font-size:x-small'>",
    '⓳': "</span>",     # </fs>

    config.FONT_END: "</span>",
  }

  def cleanup(self):
    self.dprint(1,"cleanup")

    # Add the mapping for any font properties
    fonts = self.getFonts().keys()
    index = config.FONT_BASE
    for font in fonts:
      dprint(1, "Adding entry for " + str(index) + ": " + font)
      self.cleanTrans[str(chr(index))] = """<span style="font-family:'{}';">""".format(font)
      index += 1

    trans = "".maketrans(self.cleanTrans)
    for i in range(len(self.wb)):

      self.wb[i] = self.wb[i].translate(trans)

      # superscripts, subscripts
      # special cases first: ^{} and _{}
      # 8203 is ZERO WIDTH SPACE U+200B
      self.wb[i] = self.wb[i].replace('^{}', r'<sup>&#8203;</sup>')
      self.wb[i] = self.wb[i].replace('_{}', r'<sub>&#8203;</sub>')
      self.wb[i] = re.sub('\^\{(.*?)\}', r'<sup>\1</sup>', self.wb[i]) # superscript format 1: Rob^{t}
      self.wb[i] = re.sub('\^(.)', r'<sup>\1</sup>', self.wb[i]) # superscript format 2: Rob^t
      self.wb[i] = re.sub('_\{(.*?)\}', r'<sub>\1</sub>', self.wb[i]) # subscript: H_{2}O

  # page links
  # 2014.01.14 new in 3.02c
  def plinks(self):
    self.dprint(1,"plinks")

    # of the form #124:ch03#
    # displays 124, links to ch03
    regex = re.compile(r"#\d+:.*?#")
    for i in range(len(self.wb)): # new 2014.01.13
      while True:
        m = regex.search(self.wb[i])
        if not m:
          break
        self.wb[i] = re.sub(r"#(\d+):(.*?)#", r"<a href='#\2'>\1</a>", self.wb[i],1)

    # of the form #274#
    # displays 274, links to Page_274
    regex = re.compile(r"#\d+#")
    for i in range(len(self.wb)):
      while True:
        m = regex.search(self.wb[i])
        if not m:
          break
        self.wb[i] = re.sub(r"#(\d+)#", r"<a href='#Page_\1'>\1</a>", self.wb[i],1)

  def placeCSS(self):
    self.dprint(1,"placeCSS")
    i = 0
    while i < len(self.wb):
      if re.search("CSS PLACEHOLDER", self.wb[i]):
        self.wb[i:i+1] = self.css.show() + font.formatFonts(self.getFonts())
        break
      i += 1

  def placeMeta(self):
    self.dprint(1,"placeMeta")

    # Generate default meta values: Always want a generator, and DC.Publisher
    if self.umeta.get("generator") == None:
      self.umeta.add("generator", "fpgen {}".format(config.VERSION))
    if self.umeta.get("DC.Publisher") == None:
      self.umeta.add("DC.Publisher", "Distributed Proofreaders Canada")

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

  NARROW_NO_BREAK_SPACE = "\u202f"
  RIGHT_DOUBLE_ANGLE_QUOTATION_MARK = "\u00bb"

  # Add non-breaking thin space before !, ? and ;
  # per french typographic rules.
  # Only done with an option
  def tweakSpacing(self):
    self.dprint(1, "tweakSpacing")

    # Default is false, this code is not run
    if not config.uopt.isOpt("french-with-typographic-spaces", False):
      return

    repl = r"\1" + self.NARROW_NO_BREAK_SPACE + r"\2"
    sub = r"([\w⩥" + self.RIGHT_DOUBLE_ANGLE_QUOTATION_MARK + "])([!?;])"
    for i,line in enumerate(self.wb):
      if line.startswith(config.FORMATTED_PREFIX):
        continue
      if not line.startswith("<"):
        # Note that all <font> changes are protected by changing to ⩥
        self.wb[i] = re.sub(sub, repl, line)
      # TODO
      # matching <l rend='center; mt:3em'>text!</l>
      # don't sub before the semi, but do the exclamation!
      # Ditto any arbitrary leading tag that is allowed to be followed by
      # text...  Note that font changes do work, because they have been
      # protected already.  But <target>, <l>, ...

  def endHTML(self):
    self.dprint(1,"endHTML")
    self.wb.append("  </body>")
    self.wb.append("  <!-- created with fpgen.py {} on {} -->".format(config.VERSION, config.NOW))
    self.wb.append("</html>")

  def doHeadings(self):
    self.dprint(1,"doHeadings")

    def oneHeading(harg, htitle, orig):

      # Defaults
      htarget = ""
      hlevel = 0
      showpage = False
      style = ""
      useclass = ""
      span = ""
      options = {}

      # pn's have been converted
      m = re.search("⪦([^-]+)⪧", harg)
      if m:
        self.cpn = m.group(1)
        showpage = True
        # Remove it
        harg = harg[0:m.start(0)] + harg[m.end(0):]

      # For historic reasons, nobreak can occur standalone, or as a rend option
      if "nobreak" in harg:
        options["nobreak"] = ""
        harg = harg.replace("nobreak", "")

      attributes = parseTagAttributes("heading", harg, [
        "nobreak", "hidden", "level", "id", "pn", "toc", "rend"
      ])

      if "rend" in attributes:
        rend = attributes["rend"]
        options.update(parseOption("heading", rend, [ "hidden", "nobreak" ]))

      # Note: Earlier, we have ensured that all headers have ids, just
      # in case <tocloc> is in use.
      if "id" in attributes:
        htarget = " id='" + attributes["id"] + "'"

      if "level" in attributes:
        hlevel = int(attributes["level"])
        if hlevel < 1 or hlevel > 4:
          fatal("<heading>: level must be a number between 1 and 4 in line: " +
              line)

      if "hidden" in options:
        style = " style='visibility:hidden; margin:0; font-size:0;' "

      if "nobreak" in options:
        useclass = " class='nobreak'"
        self.css.addcss("[427] .nobreak { page-break-before: avoid; }")

      if showpage: # visible page numbers
        if self.gentype != 'h': # other than browser HTML, just the link
          span = "<a name='Page_{0}' id='Page_{0}'></a>".format(self.cpn)
        else:
          span = "<span class='pageno' title='{0}' id='Page_{0}'></span>".format(self.cpn)

      self.css.addcss(headingCSS[hlevel])
      if hlevel == 1:
        if self.gentype != 'h':
          # There will be a page break before the header; if we emit the pn anchor
          # before the <h1>, the TOC will link to the prior page
          l = "<div><h1{}{}{}>{}{}</h1></div>".format(style, useclass, htarget, span, htitle)
        else:
          # I don't know why the div for only the <h1>!
          l = "<div>{}<h1{}{}{}>{}</h1></div>".format(span, style, useclass, htarget, htitle)

      if hlevel == 2:
        l = "<h2{}{}{}>{}{}</h2>".format(style, useclass, htarget, span, htitle)

      if hlevel == 3:
        l = "<h3{}{}{}>{}{}</h3>".format(style, useclass, htarget, span, htitle)

      if hlevel == 4:
        l = "<h4{}{}{}>{}{}</h4>".format(style, useclass, htarget, span, htitle)

      return l

    parseStandaloneSingleLineTagWithContent(self.wb, "heading", oneHeading)

  def oneSummary(self, openTag, block):
    if openTag != "":
      fatal("Badly formatted <summary>: <summary " + openTag + ">")
    self.css.addcss(summaryCSS[self.summaryStyle])
    return [ "<div class='summary'>" ] + block + [ "</div>" ]

  indexN = 0
  def oneIndex(self, openTag, block):
    self.indexN += 1
    nCol = 2

    attributes = parseTagAttributes("index", openTag, [ "rend" ])
    if "rend" in attributes:
      rend = attributes["rend"]
      options = parseOption("index", rend, [ "ncol" ])
      if "ncol" in options:
        try:
          nCol = int(options["ncol"])
        except:
          fatal("<index>: rend option ncol requires a number: " + options["ncol"])

    # Note indexes look yuky justified, so text-align: left
    self.css.addcss("""[1235] .index{N} {{
      -moz-column-count: {nCol};
      -moz-column-gap: 20px;
      -webkit-column-count: {nCol};
      -webkit-column-gap: 20px;
      column-count: {nCol};
      column-gap: 20px;
    }}
    .index{N} .line {{
      text-align: left;
      text-indent:-2em;
      margin:0 auto 0 2em;
    }}""".format(N=self.indexN, nCol=nCol))
    b = [ \
      '', \
      '<div class="index{}">'.format(self.indexN), \
      '<lg rend="left">' \
    ]
    for i, l in enumerate(block):
      l = "<l>" + l.rstrip() + "</l>"
      m = re.match(r"(<l.*?>)(\s+)(.*?)<\/l>", l)
      if m:
        l = m.group(1) + "◻"*len(m.group(2)) + m.group(3) + "</l>"
      b.append(l)
    b.append('</lg>')
    b.append('')
    b.append('</div>')
    return b

  def oneMulticol(self, openTag, block):
    self.indexN += 1
    nCol = 2

    attributes = parseTagAttributes("multicol", openTag, [ "rend" ])
    if "rend" in attributes:
      rend = attributes["rend"]
      options = parseOption("multicol", rend, [ "ncol" ])
      if "ncol" in options:
        try:
          nCol = int(options["ncol"])
        except:
          fatal("<multicol>: rend option ncol requires a number: " + options["ncol"])

    self.css.addcss("""[1236] .multicol{nCol} {{
      -moz-column-count: {nCol};
      -moz-column-gap: 20px;
      -webkit-column-count: {nCol};
      -webkit-column-gap: 20px;
      column-count: {nCol};
      column-gap: 20px;
    }}""".format(nCol=nCol))
    b = [ \
      '', \
      '<div class="multicol{}">'.format(nCol), \
    ]
    b += block
    b.append('</div>')
    return b

  def doBlockq(self):
    self.dprint(1,"doBlockq")
    regex = re.compile("<quote(.*?)>")
    for i,line in enumerate(self.wb):
      owned = False
      m = regex.match(line)
      if m:
        rendatt = m.group(1)
        opts = m.group(1).strip()
        attributes = parseTagAttributes("quote", opts, [ 'rend' ])
        rend = attributes['rend'] if 'rend' in attributes else ""
        opts = parseOption("<quote>/rend=", rend, quoteRendOptions)

        if "w" in opts and "fs" in opts:
          self.fatal("Cannot specify both width and fontsize in <quote>")

        # is a width specified? must be in em
        if "w" in opts:
          m = re.search("(\d+)em", opts["w"])
          rendw = self.marginSize("quote", opts, "w", "")
          drendw = re.sub("%", "percent", rendw)

          if "right" in opts:
            self.wb[i] = "<div class='blockquote-right" + drendw + "'>"
            self.css.addcss("[391] div.blockquote-right"+ drendw + " { margin:1em 0em 1em auto; text-align:right; width:"+rendw+"; }")
            self.css.addcss("[392] div.blockquote-right"+ drendw + " p { text-align:left; }")
          else:
            self.wb[i] = "<div class='blockquote"+drendw+"'>"
            self.css.addcss("[391] div.blockquote"+drendw+" { margin:1em auto; width:"+rendw+"; }")
            self.css.addcss("[392] div.blockquote"+drendw+" p { text-align:left; }")
          owned = True
        else:
          if "right" in opts:
            self.fatal("<quote>: Must specify w option if using right")

        # is a font size specified? must be in em
        if "fs" in opts:
          m = re.search("([\d\.]+)em", opts["fs"])
          if m:
            rendfs = "{}".format(m.group(1))
          else:
            fatal("<quote>: malformed fs option in rend tag: " + opts["fs"])

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

  def marginSize(self, tag, opts, name, default):
    if not name in opts:
      return default

    opt = opts[name]
    m = re.match("^(.*)(px|%|em)$", opt)
    if m:
      number = m.group(1)
      try:
        v = float(number)
        return opt
      except:
        pass

    # Standalone number?  If so, its in ems
    try:
      v = float(opt)
      return opt + "em"
    except:
      pass

    fatal("<" + tag + ">: malformed " + name + " option in rend tag: " + opt)

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

        attr = parseTagAttributes("tb", m.group(1), tbAttributes)
        if "rend" in attr:
          rend = attr["rend"]
          opts = parseOption("rend", rend, tbRendOptions)

          tb_mt = self.marginSize("tb", opts, "mt", tb_mt)
          tb_mb = self.marginSize("tb", opts, "mb", tb_mb)

          # line style:
          if "ls" in opts:
            tb_linestyle = opts["ls"]

          # line color
          if "lc" in opts:
            tb_color = opts["lc"]

          if "thickness" in opts:
            tb_thick = opts["thickness"]

          # Only in %, so we can calculate margin-left and margin-right!
          if "w" in opts:
            m = re.search("(\d+)%", opts["w"])
            if m:
              tb_width = "{}".format(m.group(1))
            else:
              fatal("<tb>: malformed w option in rend tag: " + opts["w"])

          tb_marginl = str((100 - int(tb_width))//2) + "%" # default if centered
          tb_marginr = tb_marginl

          # Accept either align:left, or just left
          align = "center"
          if "align" in opts:
            align = opts["align"]
          elif "right" in opts:
            align = "right"
          elif "left" in opts:
            align = "left"

          if align == "right":
            tb_align = "text-align:right"
            tb_marginl = "auto"
            tb_marginr = "0"
          elif align == "left":
            tb_align = "text-align:left"
            tb_marginl = "0"
            tb_marginr = "auto"
          # else center

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
          self.css.addcss("""[378] hr.footnotemark {
            border:none;
            border-bottom:1px solid silver;
            width:10%;
            margin:1em auto 1em 0;
            page-break-after: avoid;
          }""");
        else:
          self.fatal("unknown hr rend: /{}/".format(m.group(1)))

  def parsePx(self, opts, key, defval):
    value = defval
    if key in opts:
      s = opts[key]
      # Can either have nothing, or px; but treated the same as px
      if s.endswith("px"):
        s = s[0:-2]
      try:
        value = int(s)
      except:
        fatal("rend option " + key + " requires a number, not: " + opts[key])
    return value

  def oneTableBlock(self, openTag, block):
    self.tableCount += 1
    tableID = "tab" + str(self.tableCount)
    vpad = 2 # defaults
    hpad = 5
    hangIndent = 24

    # can include rend and pattern
    self.css.addcss("[560] table.center { margin:0.5em auto; border-collapse: collapse; padding:3px; }")
    self.css.addcss("[560] table.left { margin:0.5em 1.2em; border-collapse: collapse; padding:3px; }")
    self.css.addcss("[560] table.flushleft { margin:0.5em 0em; border-collapse: collapse; padding:3px; }")

    # pull the pattern
    columns = parseTablePattern(openTag, True, self.uprop)

    # Were there any user-specified widths?
    userWidth = False
    for col in columns:
      if col.userWidth:
        userWidth = True
        break

    # pull the rend attributes
    useborder = False
    left = False
    flushleft = False
    fontsize = None
    m = re.search("rend='(.*?)'", openTag)
    if m:
      trend = m.group(1)
      opts = parseOption("rend", trend, tableRendOptions)
      vpad = self.parsePx(opts, 'vp', vpad)
      hpad = self.parsePx(opts, 'hp', hpad)
      hangIndent = self.parsePx(opts, 'hang', hangIndent)
      fontsize = parseFontSize(opts, opts, opts, trend)

      useborder = 'border' in opts # table uses borders
      left = 'left' in opts  # Left, not centre
      flushleft = 'flushleft' in opts  # Left, without indent

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
        self.css.addcss("[562] ." + tableID + colID + 
          " { " + property + ": " + value + " " + linetype + " black; }");
      # Generate empty CSS if no border, since we generate the class below.
      # Calibre doesn't convert non-existing classes correctly
      if col.lineAfter == 0 and col.lineBefore == 0:
        self.css.addcss("[562] ." + tableID + colID + " { }");
      colIndex += 1

    # build the table header
    t = []

    s = "<table id='" + tableID +"' summary='' class='"
    if flushleft:
      s += 'flushleft'
    elif left:
      s += 'left'
    else:
      s += 'center'

    if useborder:
      s += " border"
      self.css.addcss("[561] table.border td { border: 1px solid black; }")

    # end of class arg
    s += "'"

    if fontsize != None and fontsize != '':
      s += " style='" + fontsize + "'"

    s += ">"
    t.append(s)
    if userWidth:
      t.append("<colgroup>")
      for col in columns:
        t.append("<col span='1' style='width: {}em;'/>".format(col.width//2))
      t.append("</colgroup>")

    # Parse the table
    ncols = len(columns)
    splitLines = parseTableRows(block, columns)

    # emit each row of table
    rowNum = 1
    for lineno, row in enumerate(splitLines):

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
          cell = TableCell("&nbsp;", col)
        else:
          cell = cells[n]
        data = cell.getData()

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
          if n+nspan-1 >= len(columns):
            fatal("More spans than table columns")
          endCol = columns[n+nspan-1]

          property = "border-right"
          linetype = "solid" if endCol.lineAfterStyle == '|' else "double"
          value = str(endCol.lineAfter) + "px"
          self.css.addcss("[563] ." + class2 +
            " { " + property + ": " + value + " " + linetype + " black; }")

        align = cell.getAlignment()
        valign = cell.getVAlignment()

        userClass = cell.getUserClass()
        if userClass != None:
          if class2 != "":
            class2 = class2 + ' ' + userClass
          else:
            class2 = userClass

        # Check both hang and align: hang can be set, but <align=c> override
        if (col.hang and align == 'left') or align == 'hang':
          # We still want our horizontal padding, i.e. we want to add hpad pixels to 1.5em
          # An em is normally 16px.
          left = hangIndent + hpad
          hang = "padding-left:" + str(left) + "px; text-indent:-" + str(hangIndent) + "px;"
        else:
          hang = ''

        # Minimize the size of our html so we don't blow up epubs; always use a class
        alignText = 'left' if align == 'hang' else align
        style = \
          "padding: " + str(vpad) + "px " + str(hpad) + "px; " + \
          "text-align:" + alignText + "; vertical-align:" + valign + ";" + \
          hang;
        if not style in self.styleClasses:
          styleClass = "tdStyle" + str(len(self.styleClasses))
          self.styleClasses[style] = styleClass
          self.css.addcss("[564] ." + styleClass + " {\n" + style + "\n}")
        else:
          styleClass = self.styleClasses[style]

        # If we have a leader for this column, add class=leader to the <td>
        # and surround the cell data with <span>...</span>
        leaderName = col.leaderName
        if leaderName != None and len(data) > 0:
          if class2 != '':
            class2 = class2 + ' '
          class2 += leaderName
          data = "<span>" + data + "</span>"
          leaderString = 150 * col.leaderChars
          self.css.addcss(leaderCSS.format(leaderName, leaderString.replace(' ', '\\00A0')))

        if class2 != '':
          class2 = class2 + ' '
        if colspan != '':
          colspan = ' ' + colspan
        line += "<td class='" + class1 + " " + class2 + styleClass + "'" +\
          colspan + ">" + data + "</td>"
      # End of column for loop

      line += "</tr>"
      t.append(line)
      rowNum += 1
    # end of row for loop
    t.append("</table>")

    return t

  def doTables(self):
    self.dprint(1,"doTables")
    parseStandaloneTagBlock(self.wb, "table", self.oneTableBlock)

  def dimension(self, opts, name):
    if not name in opts:
      return None

    opt = opts[name]
    if opt != "auto" and not opt.endswith("px") and not opt.endswith("%"):
      # A simple number is treated as pixels
      if re.match(r"^\d+$", opt):
        opt += "px"
      else:
        fatal("Illustration option " + name + \
          " must be auto, or a number ending in px or %: " + opt)
    return opt

  def doIllustrations(self):
    self.dprint(1,"doIllustrations")
    self.idcnt = 0 # auto id counter

    def oneIllustration(args, block):
      attr = parseTagAttributes("illustration", args, illustrationAttributes)

      # set i_filename ("content" or "src")
      i_filename = ""
      if "content" in attr:
        i_filename = attr["content"]
      elif "src" in attr:
        i_filename = attr["src"]
      if i_filename == "":
        self.fatal("no image filename specified in {}".format(args))

      # --------------------------------------------------------------------
      # pull rend string, if any
      i_rend = attr["rend"] if "rend" in attr else ""
      opts = parseOption("rend", i_rend, illustrationRendOptions)

      # --------------------------------------------------------------------
      # set i_id
      if "id" in attr:
        i_id = attr["id"]
      else:
        i_id = "iid-{:04}".format(self.idcnt)
        self.idcnt += 1

      # --------------------------------------------------------------------
      # set i_posn placement
      # Either left, right, or center; or align:left, align:right, or
      # align:center.
      #
      i_posn = "center" # default
      if "left" in opts:
        i_posn = "left"
      if "right" in opts:
        i_posn = "right"
      if "align" in opts:
        i_posn = opts['align']

      self.css.addcss(illustrationCSS[i_posn])

      # --------------------------------------------------------------------
      # set i_w, i_h width and height
      i_w = self.dimension(opts, 'w')
      i_h = self.dimension(opts, 'h')
      i_occupy = self.dimension(opts, 'occupy')

      if i_w == None:
        self.fatal("must specify image width\n{}".format(args))
      if i_h == None:
        i_h = "auto"
      if i_occupy != None:
        i_occupy = " style='width:" + i_occupy + "'"
      else:
        i_occupy = ""

      # --------------------------------------------------------------------
      # determine if link to larger image is requested.
      # if so, link is to filename+f in images folder.
      i_link = "" # assume no link
      if "link" in opts:
        i_link = re.sub(r"\.", "f.", i_filename)

      # --------------------------------------------------------------------
      # illustration may be on one line (/>) or three (>)
      i_caption = self.getCaption(block)
      i_caption = re.sub("<br>", "<br/>", i_caption) # honor hard breaks in captions

      # --------------------------------------------------------------------
      #
      t = []
      style="width:{};height:{};".format(i_w, i_h)
      t.append("<div class='fig{}'{}>".format(i_posn, i_occupy))

      # handle link to larger images in HTML only
      s0 = ""
      s1 = ""
      if 'h' == self.gentype and i_link != "":
        s0 = "<a href='{}'>".format(i_link)
        s1 = "</a>"
      t.append("{}<img src='{}' alt='' id='{}' style='{}'/>{}".format(s0, i_filename, i_id, style, s1))
      if i_caption != "":
        self.css.addcss("[392] p.caption { text-align:center; margin:0 auto; width:100%; }")
        # markPara will now tag each paragraph with class='caption'
        #t.append("<p class='caption'>" + i_caption + "</p>")
        t.append(i_caption)
      t.append("</div>")
      return t

    parseStandaloneTagBlock(self.wb, "illustration", oneIllustration, allowClose = True)


  sidenote = """[990]
    .sidenote {
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: smaller;
      background: #f0f0f0;
      display:block;
      position: absolute;
      text-align:right;
      max-width:9.5%;
      right:.2em;
      top:auto;
    }
  """

  sidenoteEmbedded = """[990]
    .sidenote {
      width: 15%;
      padding-bottom: 0.5em;
      padding-top: 0.5em;
      padding-left: 0.5em;
      padding-right: 0.5em;
      margin-left: 1em;
      float: right;
      clear: right;
      margin-top: 1em;
      font-size: smaller;
      color: black;
      background: #eeeeee;
      border: dashed 1px;
      text-align: center;
      text-indent: 0;
    }
  """

  sidenotePDF = """[990]
    .sidenote {
      overflow: hidden;
      text-overflow: ellipsis;
      font-size: smaller;
      background: #f0f0f0;
      display:block;
      position: absolute;
      text-align:right;
      max-width:65pt;
      right:4pt;
      top:auto;
    }
  """

  # Note: use display:none so it doesn't cause extra white-space between
  # paragraphs.  visibility:hidden creates white-space
  sidenoteOff = """[990]
    .sidenote { display: none; }
  """

  def doSidenotes(self):
    sawSidenote = False

    # footnote targets and text
    i = 0
    n = len(self.wb)
    while i < n:
      m = re.search("<sidenote>", self.wb[i])
      if m:
        sawSidenote = True
        startSidenote = i
        self.wb[i] = self.wb[i][0:m.start(0)] + "<a class='sidenote'>" + self.wb[i][m.end(0):]
        while i < n:
          m = re.search("<\/sidenote>", self.wb[i])
          if m:
            self.wb[i] = self.wb[i][0:m.start(0)] + "</a>" + self.wb[i][m.end(0):]
            break
          i += 1
        if i == n or i > startSidenote+20:
          fatal("<sidenote> not terminated or excessively long")
      i += 1

    if sawSidenote:
      style = config.uopt.getopt('sidenote-style')
      if style == "embedded":
        self.css.addcss(self.sidenoteEmbedded)
      elif style == "right" or style == "":
        # Sidenotes only in html and pdf
        if 'h' in self.gentype:
          self.css.addcss(self.sidenote)
        # Does not work
        #elif 'p' in self.gentype:
        #  self.css.addcss(self.sidenotePDF)
        #  if config.uopt.getopt('pdf-margin-right') == "":
        #    config.uopt.addopt('pdf-margin-right', '72')
        else:
          self.css.addcss(self.sidenoteOff)
      else:
        fatal("Option sidenote-style must be either embedded or right, not " +
          style)

  # setup the framework around the lines
  # if a rend option of mt or mb appears, it applies to the entire block
  # other rend options apply to the contents of the block
  def doLineGroups(self):
    self.dprint(1,"doLineGroups")

    # Note: preprocess.lgBlock has already run, and converted blank lines
    # inside the <lg> tags into <l></l>
    def lgBlock(args, lgblock):
      (opts, align) = parseLgOptions(args)

      # if a rend option of mt or mb is included, pull it out.
      # 16-Feb-2014 may be decimal
      blockmargin = "style='" + \
        self.parseMargins(opts, args, mm=self.lgMarginMap) + "'"

      # Remove the options we've processed
      # We'll be left with options like ``small'' or ``bold'',
      # all line-specific options, not block-specific;
      # which will become defaults for each <l> line within
      # the group.
      # It is a little confusing, you can't specify both center and
      # poetry; and yet you can override in <l> with center, but not
      # poetry.  Poetry is block-specific; while center is both block
      # and line.
      for o in [
          "mt", "mb",
          "center", "left", "right", "block", "poetry", "block-right",
        ]:
        if o in opts:
          del opts[o]

      # Recreate the string with the rest of the options
      # This will be emitted as a comment on the <div> line;
      # then m2h will find that comment and reparse it to handle the
      # rest of the options.
      lgopts = "rend=';"
      for o in opts:
        v = opts[o]
        if v != '' and v != None:
          lgopts += o + ":" + v
        else:
          lgopts += o
        lgopts += ';'
      lgopts += "'"

      # default is left
      if align == "left":
        divLine = "<div class='lgl' {}> <!-- {} -->".format(blockmargin,lgopts)
        self.css.addcss("[220] div.lgl { }")
        self.css.addcss("[221] div.lgl p { text-indent: -17px; margin-left:17px; margin-top:0; margin-bottom:0; }")
        divEndLine = "</div> <!-- end rend -->" # closing </lg>

      elif align == "center":
        divLine = "<div class='lgc' {}> <!-- {} -->".format(blockmargin,lgopts)
        self.css.addcss("[220] div.lgc { }")
        self.css.addcss("[221] div.lgc p { text-align:center; text-indent:0; margin-top:0; margin-bottom:0; }")
        divEndLine = "</div> <!-- end rend -->" # closing </lg>

      elif align == "right":
        divLine = "<div class='lgr' {}> <!-- {} -->".format(blockmargin,lgopts)
        self.css.addcss("[220] div.lgr { }")
        self.css.addcss("[221] div.lgr p { text-align:right; text-indent:0; margin-top:0; margin-bottom:0; }")
        divEndLine = "</div> <!-- end rend -->" # closing </lg>

      elif align == "block":
        divLine = "<div class='literal-container' {}><div class='literal'> <!-- {} -->".format(blockmargin,lgopts)
        self.css.addcss("[970] .literal-container { text-align:center; margin:0 0; }")
        self.css.addcss("[971] .literal { display:inline-block; text-align:left; }")
        divEndLine = "</div></div> <!-- end rend -->" # closing </lg>

      elif align == "block-right":
        divLine = """
          <div class='literal-container-right' {}>
          <div class='literal'> <!-- {} -->""".format(blockmargin,lgopts)
        self.css.addcss("[969] .literal-container-right { text-align:right; margin:1em 0; }")
        self.css.addcss("[971] .literal { display:inline-block; text-align:left; }")
        divEndLine = "</div></div> <!-- end rend -->" # closing </lg>

      elif align == "poetry":
        lgblock = addStanzas(lgblock)
        self.css.addcss(
            poetryLeftCSS
                if self.poetryIndent() == "left" else
            poetryCenterCSS
        )
        divLine = """
          <div class='poetry-container' {}>
          <div class='lgp'> <!-- {} -->""".format(blockmargin,lgopts)
        divEndLine = "</div></div> <!-- end poetry block --><!-- end rend -->" # closing </lg>
      return [ divLine ] + lgblock + [ divEndLine ]

    # All lines are surrounded by <l>...</l> at this point.
    # There are three types of lines:
    # 1) A piece of poetry. <l>text</l>
    # 2) A blank line. <l></l>
    # 3) Special lines, <l rend=>...</l>
    # A stanza is a grouping of poetry lines, and includes any following
    # blank lines and special lines. It would then end, when the following
    # poetry line is reached.
    # We need two levels of div around it, one inline-block, to get a size;
    # and the next block to be able to position the special lines.
    # In the event that we don't have any special lines, we only use one div,
    # the outer.
    def addStanzas(block):

      # Add markup for a single stanza
      def markupStanza(stanza):

        needsSizing = False
        for line in stanza:
          if not line.startswith("<l>"):
            needsSizing = True
            break

        if needsSizing:
          return [
              "<div class='stanza-outer'>",
              "<div class='stanza-inner'>",
            ] + stanza + [
              "</div>",
              "</div>",
            ]
        else:
          return [
              "<div class='stanza-outer'>",
            ] + stanza + [
              "</div>",
            ]

      # Break the lines in the linegroup up into a list of stanzas
      # returns a list of lists of lines
      def parseStanzas(lines):
        result = []
        stanza = []
        inStanza = False
        inBetween = False
        for line in block:

          if line == "<l></l>": # blank line
            inBetween = True
            stanza.append(line)

          elif line.startswith("<l>"): # poetry line
            if inStanza and not inBetween:
                stanza.append(line) # Just another line in existing stanza
            else:
              if inStanza:
                # End current stanza
                result.append(stanza)
                stanza = []
                inStanza = False
              # Start new stanza
              inStanza = True
              inBetween = False
              stanza.append(line)

          else: # must be <l rend=...>, i.e. special line
            inBetween = True
            stanza.append(line)

        if len(stanza) > 0:
          result.append(stanza)
        return result

      # Break the set of lines in the linegroup, into a set of stanzas;
      # then markup each stanza individually
      result = []
      stanzas = parseStanzas(block)
      for stanza in stanzas:
        result.extend(markupStanza(stanza))
      return result

    parseStandaloneTagBlock(self.wb, "lg", lgBlock)

  # process lines, in or outside a line group
  # At this point, the <lg> line has been turned into a <div>, with a comment
  # which contains the original rend argument; extract it again, pass it off
  # to m2h, which will apply it to each line
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
        self.lastLineRaw = None
      if re.search("<!-- end poetry block -->", self.wb[i]):
        inPoetry = False

      m = re.search("<l(.*?)>", self.wb[i]) and not re.search("<li", self.wb[i])
      if m: # we have a line to rend
        self.wb[i] = self.m2h(self.wb[i], inPoetry, rendopts)
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
          # Not HTML: No visible page numbers; however, still need anchor tags for index/toc
          self.wb[i]=re.sub("⪦.+?⪧","<a name='Page_{0}' id='Page_{0}'></a>".format(cpn), self.wb[i])
      if re.search("<\/p", line):
        inBlockElement = False

  # Emit html specific output for <chap-head> and <sub-head> tags
  def headers(self, chapHead, subHead, pn, id, emittitle, nobreak, book, usingBook):
    result = []
    if emittitle:
      title = self.umeta.get("DC.Title")
      result.append("<l rend='center mt:3em mb:2em fs:2.5em'>" + title + "</l>")
      result.append("")
    if book or not usingBook:
      level = '1'
    else:
      level = '2'
    h = "<heading level='" + level + "'"
    if emittitle or nobreak:
      h += " nobreak"
    if pn != None:
      h += " pn='" + pn + "'"
    if id != None:
      h += " id='" + id + "'"
    h += ">" + chapHead 
    if subHead != None:
      h += "<br/> <span class='sub-head'>" + subHead + "</span>"
      self.css.addcss("[250] .sub-head { font-size: smaller; }")
    h += "</heading>"
    result.append(h)
    result.append("")

    return result

  # HTML: Main logic
  def process(self):
    super().process()
    self.processPageNum()
    self.protectMarkup(self.wb)
    self.preprocess()
    self.tweakSpacing()
    self.userToc()
    self.doIndex()
    self.doMulticol()
    self.processLinks()
    self.processDropCaps()
    self.processTargets()
    from drama import DramaHTML
    DramaHTML(self.wb, self.css).doDrama();
    self.markPara()
    self.restoreMarkup(self.wb)
    self.startHTML()

    self.doHeadings()
    self.doBlockq()
    self.doSummary()
    self.doBreaks()
    self.doTables()
    self.doIllustrations()
    footnote.outOfBandFootnoteProcessing(self.processOneBlock)
    footnote.footnotesToTags(self.wb)
    self.doSidenotes()
    self.doLineGroups()
    self.doLines()

    self.processPageNumDisp()
    footnote.emitFootnotes(self.wb, self.css)
    self.placeCSS()
    self.placeMeta()
    self.cleanup()
    self.plinks()
    self.endHTML()

  # Footnotes may be removed from the main flow if they are converted to
  # sidenotes, and only added back during footnotesToTags.
  # Minimal processing here to handle only the allowed tags: i.e. textual ones
  def processOneBlock(self, block):
    self.preprocessOneBlock(block)
    self.protectMarkup(block)
    self.restoreMarkup(block)
    # Note cleanup will be called in the normal course of things
    return block

#}
# END OF CLASS HTML

# ===== class Text ============================================================

class Text(Book): #{
  def __init__(self, ifile, ofile, d, fmt):
    Book.__init__(self, ifile, ofile, d, fmt)
    self.srcfile = ifile
    self.dstfile = ofile

    self.qstack = [] # quote level stack

# Not used.  Used NO_WRAP_PREFIX instead
#    lw = config.uopt.getopt("text-line-wrap")
#    if lw != '':
#      try:
#        config.LINE_WRAP = int(lw)
#      except Exception as e:
#        fatal("<option> text-line-wrap must be an integer: " + lw)
#      if config.LINE_WRAP < 40 or config.LINE_WRAP > 500:
#        fatal("<option> text-line-wrap must be between 40 and 500: " + lw)
#      cprint("Text line width overridden to " + str(config.LINE_WRAP))

  # save file to specified dstfile
  # overload to do special wrapping for text output only
  def saveFile(self, fn):
    if len(self.wb) > 0:
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
    lineWidth = config.LINE_WRAP
    f1 = open(fn, "w", encoding='utf-8')
    for index,t in enumerate(self.wb):
      if t.startswith(config.NO_WRAP_PREFIX):
        # No wrapping permitted
        f1.write("{:s}{}".format(t[1:], lineEnd))
      elif len(t) < lineWidth:
        f1.write( "{:s}{}".format(t,lineEnd) ) # no wrapping required
      else:
        # Strip leading spaces, and figure out indent first
        m = re.match("( +)", t)
        if m:
          userindent = len(m.group(1))
        else:
          userindent = 0
        t = t.strip()
        lw = lineWidth - userindent
        if lw < 5:
          cprint("Warning: Line indented more than line width! [" + t + "]")
          userindent = 0
          lw = lineWidth

        # This is probably all wrong, and should be rewritten and tested
        # Or, we could just fix the rest of the code which lets long lines
        # through to here...
        sliceat = 0
        try:
          sliceat = t.rindex(" ", 0, lw) # should be 74?
        except:
          cprint("Cannot wrap text: Line longer than " + str(lw) + \
              " characters without a space.\n" + \
              t + "\nLine will be emitted without wrapping.")
          f1.write(" " * userindent + t + lineEnd)
          continue
        firstline = " " * userindent + t[0:sliceat].strip()
        f1.write( "{:s}{}".format(firstline,lineEnd) )
        cprint("warning: Wrapping line: [" + t + "]. ", end="")
        t = t[sliceat:].strip()
        nwrapped += 1
        while len(t) > 0:
          if len(t) < lw-3:
            f1.write( " " * userindent + "  {:s}{}".format(t,lineEnd) )
            t = ""
          else:
            try:
              sliceat = t.rindex(" ", 0, lw)
            except:
              sliceat = lw
              cprint("Line too long with no break. Chopping at line width. Line: " + t, end="")
            nextline = t[0:sliceat].strip()
            f1.write( " " * userindent + "  {:s}{}".format(nextline,lineEnd) )
            t = t[sliceat:].strip()
            nwrapped += 1
        cprint("")
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
      lowerSeen = False
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
          if c.isalpha() and not c.isupper():
            lowerSeen = True
        off += 1

      if not lowerSeen:
        cprint("warning: small-caps font does not have any lower-case letters. Small-caps of upper-case characters are unchanged; typically this warning means you need to lower-case the characters.  Line: " + line)
      line = line[:m.start()] + replace + line[m.end():]

    return line

  # Unused, fonts missing characters
  def doUnicodeItalic(self, line):
    upperZero = ord('A')
    lowerZero = ord('a')

    mathUpperZero = 0x1d434;
    mathLowerZero = 0x1d44e;
    mathUpperBoldZero = 0x1d400;
    mathLowerBoldZero = 0x1d41a;
    while True:
      m = re.search("<i>(.*?)<\/i>", line)
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
          if c.isupper():
            replace += chr(mathUpperZero + (ord(c)-upperZero))
          elif c.islower():
            replace += chr(mathLowerZero + (ord(c)-lowerZero))
          else:
            replace += c
        off += 1

      line = line[:m.start()] + replace + line[m.end():]

    return line


  # convert all inline markup to text equivalent at start of run
  # Text version
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
    regexFont = re.compile("<font:.+?>")
    regexFontEnd = re.compile("<\/?font>")

    # A set of characters to be removed.  In case somebody is tweaking
    # the spacing of the html output, we don't want it in the text output,
    # we don't want it part of the alignment.
    # 2009: thin space
    # 202f: narrow no-break space
    # 2060: word-joiner
    regexRemove = re.compile("[\u2009\u202f\u2060]")

    i = 0
    while i < len(self.wb):

        self.wb[i] = regexOL.sub("‾", self.wb[i]) # overline 10-Apr-2014

        self.wb[i] = regexRemove.sub("", self.wb[i])

        #self.wb[i] = self.doUnicodeItalic(self.wb[i]) # unicode italic
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
            replace += x[j] + config.HARD_SPACE # space after all but last character
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
        self.wb[i] = regexFont.sub("", self.wb[i])
        self.wb[i] = regexFontEnd.sub("", self.wb[i])

        # remove table super/subscript balance tokens
        self.wb[i] = re.sub('\^\{\}', '', self.wb[i])
        self.wb[i] = re.sub('_\{\}', '', self.wb[i])

        i += 1

  #
  def genToc(self):
    self.dprint(1,"genToc")
    tocrequest = False
    for index, line in enumerate(self.wb):
      if line.startswith("<tocloc"):
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
      if self.wb[i].startswith("<pn"):
        del self.wb[i]
        continue
      i += 1

  # strip links and targets and dropcaps
  def stripLinks(self):
    self.dprint(1,"stripLinks")
    i = 0
    while i < len(self.wb):
      self.wb[i] = re.sub("<\/?link.*?>", "", self.wb[i])
      self.wb[i] = re.sub("<target.*?>", "", self.wb[i])
      i += 1

  # Dropcap in text either is stripped or replaced with property text
  def processDropCaps(self):
    self.dprint(1,"DropCaps")

    def oneDrop(arg, letter, orig):

      if "drop-text-"+letter in self.uprop.prop:
        repl = self.uprop.prop["drop-text-"+letter]
      else:
        repl = letter
      return repl

    parseEmbeddedSingleLineTagWithContent(self.wb, "drop", oneDrop)

  # simplify footnotes, move <l> to left, unadorn page links
  # preformat hr+footnotemark
  def preProcess(self):
    self.dprint(1,"preProcess")

    i = 0
    matchFN = re.compile("<fn\s+(.*?)/?>")
    while i < len(self.wb):
      line = self.wb[i]

      # Remove all paragraph style tags, all ignored in text output
      for tag in paraTags:
        line = line.replace(tag, "")
      for tag in pstyleTags:
        line = line.replace(tag, "")

      line = re.sub("#(\d+)#", r'\1', line) # page number links
      line = re.sub("#(\d+):.*?#", r'\1', line) # page number links type 2 2014.01.14

      # Replace <fn> markers
      off = 0
      while True:
        m = matchFN.search(line, off)
        if not m:
          break
        opts = m.group(1)
        args = parseTagAttributes("fn", opts, [ "id", "target" ])
        fmid = args["id"]
        target = args["target"]
        l = line[0:m.start(0)] + fmid
        off = len(l)    # Next loop
        line = l + line[m.end(0):]
      self.wb[i] = line

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
      i += 1

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
      if len(s) > 0 and s[0] == config.FORMATTED_PREFIX:
        # Do not touch <lit>!
        i += 1
        continue
      s = re.sub("<(\/?i)>", r"[[\1]]", s) # italics
      s = re.sub("<(\/?b)>", r"[[\1]]", s) # bold
      s = re.sub("<(\/?sc)>", r"[[\1]]", s) # small caps
      s = re.sub("<(\/?g)>", r"[[\1]]", s) # gesperrt
      s = re.sub("<(\/?u)>", r"[[\1]]", s) # underline
      s = re.sub(r"\\ ", config.HARD_SPACE, s) # hard spaces
      s = re.sub(r"<thinsp>|<nnbsp>|<wjoiner>", "", s) # remove special tags
      s = re.sub(r" ", config.HARD_SPACE, s) # unicode 0xA0, non-breaking space
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
    def lgBlock(args, block):
      # For each line in the lg block.
      for i, line in enumerate(block):
        if not (re.match("<l", line) or re.match("<tb", line)):
          line = re.sub(" ", config.HARD_SPACE, line)
          line = "<l>{0}</l>".format(line)
          block[i] = line
      return [ "<lg " + args + ">" ] + block + [ "</lg>" ]

    self.dprint(1,"markLines")

    # Use parseStandalone to handle missing scenarios
    parseStandaloneTagBlock(self.wb, "lg", lgBlock)

  # illustrations
  def illustrations(self):
    self.dprint(1,"illustrations")
    def oneIllustration(args, block):
      attr = parseTagAttributes("illustration", args, illustrationAttributes)
      t = []
      if len(block) == 0:
        t.append("<l>[Illustration]</l>")
      else:
        caption = self.getCaption(block)

        # if there is a <br> in the caption, then user wants
        # control of line breaks. otherwise, wrap
        m = re.search("<br\/?>", caption)
        if m: # user control
          s = "[Illustration: " + caption + "]"
          s = re.sub("<br\/?>", "\n", s)
          t.append("▹.rs 1")
          u = s.split('\n')
          for x in u:
            t.append(config.FORMATTED_PREFIX+x) # may be multiple lines
          t.append("▹.rs 1")
        else: # fpgen wraps illustration line
          # TODO: In this form, if we are wrapped in an <lg>, the .rs comes out centered!
          s = "[Illustration: " + caption + "]"
          t.append("▹.rs 1")
          u = wrap2(s)
          for x in u:
            t.append(config.FORMATTED_PREFIX+x) # may be multiple lines
          t.append("▹.rs 1")
      return t

    parseStandaloneTagBlock(self.wb, "illustration", oneIllustration, allowClose = True)

  def oneSummary(self, openTag, block):
    if openTag != "":
      fatal("Badly formatted <summary>: <summary " + openTag + ">")
    if self.summaryStyle == summaryHang:
      lm = 2
      ti = 0
    elif self.summaryStyle == summaryIndent:
      lm = 0
      ti = 2
    else:
      lm = 0
      ti = 0
    result = wrap2(" ".join(block), 3, 3, lm, ti, breakOnEmDash=True)
    for i in range(0, len(result)):
      result[i] = config.FORMATTED_PREFIX + result[i]
    return result

  # In text form, we do nothing for multi-column.
  def oneMulticol(self, opentag, block):
    return block

  def oneIndex(self, openTag, block):

#    attributes = parseTagAttributes("index", openTag, [ "rend" ])
#    nCol = 2
#    if "rend" in attributes:
#      rend = attributes["rend"]
#      options = parseOption("index", rend, [ "ncol" ])
#      if "ncol" in options:
#        try:
#          nCol = int(options["ncol"])
#        except:
#          fatal("<index>: rend option ncol requires a number: " + options["ncol"])

    b = [ '<lg rend="left">' ]
    for i, l in enumerate(block):
      b.append("<l>" + l + "</l>")
    b.append('</lg>')
    return b

  # Look inside the <tb> tag for a rend='text:hidden'
  def isTbHidden(self, line):
    m = re.match("<tb\s+(.*?)\/?>", line)
    if m:
      args = m.group(1)
      attr = parseTagAttributes("tb", args, tbAttributes)
      if "rend" in attr:
        rend = attr["rend"]
        opts = parseOption("rend", rend, tbRendOptions)
        if "text" in opts and opts["text"] == "hidden":
          return True
    return False

  def removeSidenotes(self):
    regexSidenote = re.compile("<sidenote>")
    i = 0
    while i < len(self.wb):
      m = regexSidenote.search(self.wb[i])
      if m:
        m1 = re.search("<sidenote>.*<\/sidenote>", self.wb[i])
        if m1:
          # Remove <sidenote>...</sidenote>
          self.wb[i] = (self.wb[i][0:m1.start(0)] + self.wb[i][m1.end(0):]).strip()
          # Remove it completely if it was the whole line
          if self.wb[i] == "":
            del self.wb[i]
            continue
        else:
          # Remove <sidenote>...
          self.wb[i] = self.wb[i][0:m.start(0)]
          j = i+1
          while j < len(self.wb):
            m = re.search("<\/sidenote>", self.wb[j])
            if m:
              # Remove ...</sidenote>
              self.wb[j] = self.wb[j][m.end(0):]
              break
            # Remove line between <sidenote>\n...\n</sidenote>
            del self.wb[j]
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
    regexFootnote = re.compile(r"<footnote\s+(.*?)>")
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
        if len(self.qstack) == 0:
          fatal("</quote> encounted without matching open <quote>")
        del(self.wb[i])
        continue

      # Already formatted?
      if self.wb[i].startswith(config.FORMATTED_PREFIX):
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
        opts = m.group(1)
        args = parseTagAttributes("footnote", opts, [ "id", "target" ])
        id = args["id"]
        # Put the first line on the same line as the footnote number [#]
        # unless it is formatting itself, e.g. <lg>...</lg>
        fn = id + " "
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
          s1 = re.sub(r"<br(\/)?>", "|", s)
          t1 = s1.split("|")
          for s2 in t1:
            if s2 == "":
              t.append('▹.rs 1')
            else:
              result = alignLine(s2, 'center', config.LINE_WIDTH)
              for l in result:
                t.append('▹' + l)
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
      # but the text:hidden rend option makes it just go away in text
      if self.wb[i].startswith("<tb"):
        if self.isTbHidden(self.wb[i]):
          t = []
        else:
          t = ["▹.rs 1", textTbLine, "▹.rs 1" ]
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

      # ----- footnote marker ----------------------------------------------
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
        args = m.group(1).strip()
        contents = m.group(2)
        block = self.oneL({}, args, contents)
        self.wb[i:i+1] = block
        i += len(block)
        continue

      # ----- tables ----------------------------------------------------------

      m = regexTable.match(self.wb[i])
      if m:
        startloc = i
        j = i
        while not re.match("<\/table>", self.wb[j]):
          j += 1
        endloc = j
        block = self.makeTable(self.wb[startloc:endloc+1])
        self.wb[startloc:endloc+1] = block
        i += len(block)
        continue

      # ----- process line group ----------------------------------------------
      m = regexLg.match(self.wb[i])
      if m:
        startloc = i
        j = i
        while not self.wb[j].startswith("</lg>"):
          j += 1
        endloc = j
        self.wb[startloc:endloc+1] = self.oneLineGroup(m, self.wb[startloc:endloc+1])

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

      if (llen < 10):
        fatal("<quote> nesting too deep, remaining line length is " +
            str(llen) + " characters. Current nesting level is " +
            str(len(self.qstack)) +
            ".  Check for missing or malformed </quote> tags.");

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

  def getAlignment(self, opts):
    for o in [ "left", "right", "center", "ml", "mr" ]:
      if o in opts:
        return o, opts[o]
    return None, None

  # One single standalone <l> line.
  # therend is everything matching <l(.*)>
  # contents is everything matching <l>(.*)</l>
  def oneL(self, optionsLG, therend, contents):
    if contents == "":
      # Blank line, i.e. <lXX></l>
      return [ config.FORMATTED_PREFIX ]

    attributes = parseTagAttributes("l", therend, [ 'rend', 'id' ])
    rend = attributes['rend'] if 'rend' in attributes else ""
    optionsL = parseOption("<l>/rend=", rend, lRendOptions)

    # Only if there is no alignment on the <l> do we look for alignment on
    # the <lg>; so we can override alignment for a single line inside
    align, alignValue = self.getAlignment(optionsL)
    if align == None:
      align, alignValue = self.getAlignment(optionsLG)
    dprint(1, "Alignment: " + str(align) + ", " + str(alignValue))

    opts = optionsLG.copy()
    opts.update(optionsL)
    if len(opts) > 0:
      dprint(1, "Options: " + str(opts))

    handled = False
    thetext = self.detag(contents)
    block = [ contents ]
    i = 0

    if "sb" in opts: # text spaces before
      howmuch = opts["sb"]
      block.insert(0, ".rs {}".format(howmuch))
      i = 1

    if "sa" in opts: # text spaces after
      howmuch = opts["sa"]
      block.append(".rs {}".format(howmuch))

    howmuch = None
    if align == "left":
      howmuch = 0
    elif align == "ml":
      m = re.search("([\d\.]+)em", alignValue)
      if m:
        # indent left
        howmuch = int(float(m.group(1)))
      else:
        howmuch = 0

    if howmuch != None:
      block[i] = config.FORMATTED_PREFIX + self.qstack[-1] + " " * howmuch + thetext.rstrip()
      handled = True

    howmuch = None
    if align == "right":
      howmuch = 0
    elif align == "mr":
      m = re.search("([\d\.]+)em", alignValue)
      if m:
        # indent right
        howmuch = int(float(m.group(1)))
      else:
        howmuch = 0

    if howmuch != None:
      # rend="right" or rend="mr:#em"
      rmar = config.LINE_WIDTH - len(self.qstack[-1]) - howmuch
      fstr = config.FORMATTED_PREFIX + "{:>" + str(rmar) + "}"
      block[i] = fstr.format(thetext.strip())
      handled = True

    if align == "center":
      # center
      replacements = self.centerL(thetext.strip())
      block[i:i+1] = replacements
      i += len(replacements)-1
      handled = True

    if "triple" in opts:
      pieces = thetext.split("|")
      if len(pieces) != 3:
        fatal("<l> triple alignment does not have three pieces: " + thetext)
      left = pieces[0]
      center = pieces[1]
      right = pieces[2]

      # This makes it have even spacing on both sides.
      # Alternatively, we could try to center the middle with different spacing
      if False:
        extra = config.LINE_WIDTH - len(left) - len(right) - len(center)
        if extra <= 0:
          fatal("Triple alignment doesn't fit: " + str(extra) + "; Line:" + thetext)
        gapl = extra // 2
        gapr = gap + extra % 2      # Make sure we add up to LINE_WIDTH
      else:
        gapl = (config.LINE_WIDTH - len(center))//2 - len(left)
        gapr = (config.LINE_WIDTH - len(center))//2 - len(right)
        if gapl <= 0 or gapr <= 0:
          fatal("Triple alignment doesn't fit: left=" + str(gapl) + \
            ", right=" + str(gapr) + "; Line:" + thetext)

      block[i] = left + gapl * ' ' + center + gapr * ' ' + right
      handled = True

    # Must be left
    if not handled:
      block[i] = config.FORMATTED_PREFIX + self.qstack[-1] + thetext.strip()

    return block

  def oneLineGroup(self, m, block):
    # remove <lg>, and </lg>
    del block[0]
    del block[-1]

    # Isolate the attribute, and process the different styles:
    # center, left, right, poetry,
    # and block; all separately
    opts, align = parseLgOptions(m.group(1))
    self.formatLineGroup(m, block, opts, align)

    # Blank line, before and after
    block.insert(0, ".rs 1")
    block.append(".rs 1")
    return block

  # The whole file has already been processed by markLines().
  # This took each line in the line group, and if it didn't already have
  # a <l> or <tb>, it has added <l>...</l> around the line.
  # All spaces were turned into hard spaces.
  def formatLineGroup(self, m, block, opts, align):

    # <tb> is allowed as a special case inside a line group
    i = 0
    while i < len(block):
      # Only do a prefix match, we ignore potential the rend=
      if block[i].startswith("<tb"):
        if not self.isTbHidden(block[i]):
          block[i] = textTbLine
        else:
          del block[i]
          continue
      i += 1

    # ----- bold, italic markers -------------------------------------------
    marker = "".join([ textFontStyleMap[key] for key in opts if key in textFontStyleMap ])
    if len(marker) != 0:
      revMarker = marker[::-1]
      for i, line in enumerate(block):
        if line.startswith(config.FORMATTED_PREFIX):
          continue
        # Find first non-hard-space, and stick the marker in
        m = re.match("<l(.*?)>(.*?)</l>", line)
        if m:
          l = m.group(2)
          for off, c in enumerate(l):
            if c != config.HARD_SPACE:
              l = l[0:off] + marker + l[off:] + revMarker
              block[i] = "<l" + m.group(1) + ">" + l + "</l>"
              break

    # ----- left, right, center ---------------------------------------------
    fmt = None
    if align == "center":
      fmt = "^"
    elif align == "right":
      fmt = ">"
    elif align == "left":
      fmt = "<"

    if fmt != None:
      i = 0

      while i < len(block):
        # Note all lines except <tb> match, due to markLines()
        m = re.match(r"<l(.*?)>(.*?)</l>", block[i])
        if m:
          block[i:i+1] = self.oneL(opts, m.group(1), m.group(2))
        i += 1
      return

    # ----- begin poetry code ---------------------------------------------
    # poetry allows rends: ml:Nem, center, mr:0em
    if align == "poetry":
      # first determine maximum width in poetry block
      maxwidth = 0
      maxline = ""
      i = 0
      while i < len(block):
        block[i] = self.detag(block[i])
        theline = re.sub(r"<.+?>", "", block[i]) # centering tags, etc.
        if len(theline) > maxwidth:
          maxwidth = len(block[i])
          maxline = block[i]
        i += 1

      maxwidth -= 3
      if maxwidth > 70:
        cprint("warning (long poetry line {} chars)".format(maxwidth))
        self.dprint(1,"  " + maxline) # shown in debug in internal form

      lastLine = None
      i = 0
      while i < len(block):
        m = re.match("<l(.*?)>(.*?)</l>", block[i])
        if m:
          irend = m.group(1)
          itext = m.group(2)

          # center and right override ml
          if re.search("center", irend):
            tstr = "▹{0:^" + "{}".format(maxwidth) + "}"
            block[i] = tstr.format(itext)
            i += 1
            continue
          if re.search("mr:0em", irend) or re.search("mr:0", irend):
            tstr = "▹{0:>" + "{}".format(maxwidth) + "}"
            block[i] = tstr.format(itext)
            i += 1
            continue
          if re.search("align-last", irend):
            if lastLine == None:
              fatal("Use of rend='align-last' without a last line: " + itext)
            itext = " " * len(lastLine) + itext

          m = re.search("ml:(\d+)em", irend)
          if m:
            isml = True
            itext = config.HARD_SPACE * int(m.group(1)) + itext
          if not empty.match(itext):
            theline = self.detag(itext)
            lastLine = theline
            if len(theline) > config.LINE_WRAP:
              s = re.sub(config.HARD_SPACE, " ", theline)
              self.dprint(1,"warning: long poetry line:\n{}".format(s))
            if self.poetryIndent() == 'center':
                leader = " " * ((config.LINE_WIDTH - maxwidth) // 2)
            else:
                leader = " " * 4
            block[i] = config.FORMATTED_PREFIX + self.qstack[-1] + leader + "{:<}".format(theline)

          else:
            block[i] = config.FORMATTED_PREFIX

        i += 1
      return
    # ----- end of poetry code --------------------------------------------

    # block allows rends: ml, mr
    # block, or block-right
    if align.startswith("block"):
      # find width of block
      maxw = 0
      longline = ""
      i = 0
      while i < len(block):
        m = re.match("<l(.*?)>(.*?)</l>", block[i])
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
        elif block[i].startswith(config.FORMATTED_PREFIX):
          pass
        else:
          self.fatal(block[i])
        if totlen > maxw:
          maxw = totlen
          longline = thetext
        i += 1

      # Have maxw calculated
      # Now compute fixed left indent
      if maxw > config.LINE_WIDTH:
        self.dprint(1,"warning: long line: ({})\n{}".format(len(longline),longline))
        leader = ""
      elif align == "block-right":
        leader = config.HARD_SPACE * (config.LINE_WIDTH - maxw)
      else:     # block
        leader = config.HARD_SPACE * ((config.LINE_WIDTH - maxw) // 2)

      i = 0
      while i < len(block):
        m = re.match("<l(.*?)>(.*?)</l>", block[i]) # parse each line
        if m:
          s = m.group(2) # text part
          if not empty.match(s):
            thetext = self.detag(s) # expand markup
          else:
            thetext = ""
          irend = m.group(1)

          m = re.search("ml:([\d\.]+)em", irend) # padding on left?
          if m:
            thetext = config.HARD_SPACE * int(m.group(1)) + thetext

          m = re.search("mr:([\d\.]+)", irend) # right aligned
          if m:
            inright = int(m.group(1))
            fstr = "{:>"+str(maxw-inright)+"}"
            thetext = fstr.format(thetext)
            thetext = re.sub(" ", config.HARD_SPACE, thetext)

          m = re.search("center", irend) # centered in block
          if m:
            thetext = " " * ((maxw - len(thetext))//2) + thetext
            thetext = re.sub(" ", config.HARD_SPACE, thetext)

          # if not specified,
          block[i] = config.FORMATTED_PREFIX + leader + thetext
        elif block[i].startswith(config.FORMATTED_PREFIX):
          pass
        else:
          block[i] = config.FORMATTED_PREFIX
        i += 1
      return

    return

  # Center a single line enclosed in <l>...</l>
  # If it doesn't fit, break appropriately and center multiple lines
  def centerL(self, line):
    line = re.sub(config.HARD_SPACE, " ", line)
    result = []
    # For some reason, saveFile wraps at 75 chars; but we want to center within LINE_WIDTH(72)
    # chars instead.
    w = config.LINE_WIDTH+2
    remainder = line
    while True:
      try:
        if textCellWidth(remainder) <= w:
          # It all fits, done
          fits = remainder
          remainder = ""
        else:
          # Doesn't fit; find the last space in the
          # allocated width, and break into this line, and
          # subsequent lines
          if remainder[w] == ' ':
            # Exact fit?
            fits = remainder[0:w].rstrip()
            remainder = remainder[w:].strip()
          else:
            chopat = remainder.rindex(" ", 0, w)
            fits = remainder[0:chopat+1].rstrip()
            remainder = remainder[chopat+1:].strip()
      except:
        fits = remainder[0:w]
        remainder = remainder[w:]

      # Make sure we use the printable width
      pad = config.LINE_WIDTH - textCellWidth(fits)
      half = pad // 2
      content = config.FORMATTED_PREFIX + half * ' ' + fits + (pad-half) * ' '
      result.append(content)
      if remainder == "":
        break
    return result


  # make printable table from source code block
  def makeTable(self, t):

    for k, line in enumerate(t): # 11-Sep-2013
      t[k] = self.detag(line)
    tableLine = t[0]

    del t[0] # <table line
    del t[-1] # </table line

    tf = TableFormatter(tableLine, t, self.uprop)
    return tf.format()

  # merge all contiguous requested spaces
  def finalSpacing(self):
    self.dprint(1,"finalSpacing")

    # merge user-forced lines
    i = 0
    while i < len(self.wb):
      if config.FORMATTED_PREFIX == self.wb[i]:
        startloc = i
        spacecount = 1
        i += 1
        while i < len(self.wb) and config.FORMATTED_PREFIX == self.wb[i]:
          spacecount += 1
          i += 1
        self.wb[startloc:i] = [".rs {}".format(spacecount)]
        i -= 1
      i += 1

    for i in range(len(self.wb)):
      self.wb[i] = re.sub("\s+\.rs",".rs", self.wb[i])

    i = 0
    if len(self.wb) > 0:
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
          # ?? or start or end dropcap
          if c == config.FORMATTED_PREFIX:
            continue
          elif c == config.HARD_SPACE:
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
        l = l.replace(config.FORMATTED_PREFIX, "")
        l = l.replace(config.HARD_SPACE, " ")
        l = l.replace('⊐', '%') # escaped percent signs (macros)
        l = l.replace('⊏', '#') # escaped octothorpes (page links)
        l = l.replace("≼", "<") # <
        l = l.replace("≽", ">") # >

        l = l.replace("⨭", "<") # literal <
        l = l.replace("⨮", ">") # literal >

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

  def headers(self, chapHead, subHead, pn, id, emittitle, nobreak, book, usingBook):
    result = []
    if emittitle:
      title = self.umeta.get("DC.Title")
      result.append("<l rend='center'>" + title + "</l>")
    if book or not usingBook:
      level = '1'
    else:
      level = '2'
    h = "<heading level='" + level + "'>" + chapHead 
    if subHead != None:
      h += "<br/>" + subHead
    h += "</heading>"
    result.append(h)

    return result

  # TEXT: Main Logic
  def process(self):
    super().process()
    self.processInline()
    self.processPageNum()
    self.stripLinks()
    self.processDropCaps()
    self.preProcess()
    self.protectInline() # should be superfluous as of 19-Sep-13
    self.illustrations()
    self.genToc()
    from drama import DramaText
    DramaText(self.wb).doDrama()
    self.markLines()
    self.doSummary()
    self.doIndex()
    self.doMulticol()
    self.removeSidenotes()
    self.rewrap()
    self.finalSpacing()
    self.finalRend()
#}
# END OF CLASS Text

def textCellWidth(cell):
  # Hack: there must be a better way to figure size here
  if cell.startswith("<align="):
    cell = cell[9:]
  w = 0
  for c in cell:
    c = ord(c)
    # Do not count combining diacritical marks
    if c >= 0x0300 and c <= 0x036F:
      pass
    else:
      w += 1
  return w

class TableFormatter: #{

  FIRST_LINECHARS = "─┬┰━┯┳"
  MIDDLE_LINECHARS = "─┼╂━┿╋"
  LAST_LINECHARS = "─┴┸━┷┻"
  ISOLATED_LINECHARS = "───━━━"

  def __init__(self, tableLine, lines, uprop = None):
    self.uprop = uprop
    self.maxTableWidth = config.LINE_WRAP
    self.vpad = False
    self.tableLine = tableLine
    self.lines = lines
    self.parseFormat()
    self.splitLines = parseTableRows(self.lines, self.columns)
    self.nlines = len(self.splitLines)
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
      opts = parseOption("rend", rend, tableRendOptions)
      if 'pad' in opts:
        self.vpad = True
      if 'textwidth' in opts:
        try:
          self.maxTableWidth = int(opts['textwidth'])
        except:
          fatal("Table rend option textwidth must be an integer " + \
            opts['textwidth'] + " in table line " + self.tableLine)

    # pattern must be specified
    self.columns = parseTablePattern(self.tableLine, False, self.uprop)
    self.ncols = len(self.columns)

  #
  # Figure out how wide each column is going to be.
  #
  def computeWidths(self):
    totalwidth = tableWidth(self.columns)

    # if any cells missing a width we need to calculate
    computeMax = False
    for col in self.columns:
      if col.width == 0:
        computeMax = True

    if computeMax:
      # need to calculate max width on each column
      widths = [0 for i in range(len(self.columns))]
      for tableRow in self.splitLines:
        col = 0
        for tableCell in tableRow.getCells():
          if col >= len(self.columns):
            # Ignore if more cols than rows
            break
          item = tableCell.getData()
          w = textCellWidth(item)
          if w > widths[col]:
            widths[col] = w
          col += 1

      for i in range(len(self.columns)):
        if self.columns[i].width == 0:
          self.columns[i].width = widths[i]

    # Compute totalwidth against those maxes
    totalwidth = tableWidth(self.columns)
    dprint(1, "Computed table widths: " + toWidthString(self.columns) +
      ", total: " + str(totalwidth))

    maxTableWidth = self.maxTableWidth

    # for text, may have to force narrower to keep totalwidth < maxTableWidth
    tooWide = False
    if totalwidth > maxTableWidth:
      tooWide = True
      cprint("warning: Table " + self.tableLine + " too wide, " +
          str(totalwidth) + " columns; max " + str(maxTableWidth) +
          ". Reducing widest column by one; until it fits." +
          " Initial widths: " + toWidthString(self.columns), end="")

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

    if tooWide:
      cprint("; Resulting widths: " + toWidthString(self.columns))

    centreWidth = maxTableWidth
    if totalwidth <= config.LINE_WRAP:
      # calculate tindent from max table width
      self.tindent = (config.LINE_WRAP - totalwidth) // 2
    else:
      cprint("Wide table: " + str(totalwidth) + ": " + self.tableLine)
      self.tindent = 0


    dprint(1, "Table totalwidth: " + str(totalwidth) +
      ", indenting: " + str(self.tindent) + "; final widths: " +
      toWidthString(self.columns))

  #
  # Create a single horizontal line.
  #
  def drawLine(self, isSingle, lineno, lines):
    line = " " * self.tindent
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

      #cprint("lineno=" + str(lineno) +
      #    ", len(lines)=" + str(len(lines)) +
      #    ", nlines=" + str(self.nlines) +
      #    ", nextSpan=" + str(nextSpan) +
      #    ", lastSpan=" + str(lastSpan) +
      #    ", chars=" + chars)
      #uprint("Chars=" + chars)

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
  # Add the pre-formatted pass-through flag character; and add the
  # bypass wrap pass-through character
  #
  def output(self, l):
    l = l.rstrip()
    if len(l) >= config.LINE_WRAP:
      l = config.NO_WRAP_PREFIX + l
    self.u.append(config.FORMATTED_PREFIX + l.rstrip())

  def format(self):

    self.output(".rs 1")

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

    rowcells = tablerow.getCells()

    # Draw box characters with appropriate connectors for a line
    if tablerow.isSingle() or tablerow.isDouble():
      line = self.drawLine(tablerow.isSingle(), lineno, splitLines)
      # Add the box line to the output & finished with this row
      self.output(line)
      return

    nColData = len(rowcells)
    if nColData == 0:
      # A completely blank line has no data, so hasAnyData will be false
      # But we need column delimiters on empty lines
      rowcells = [ TableCell(" ") ]

    for n in range(nColData, len(self.columns)):
      rowcells.append(TableCell("", self.columns[n]))

    maxLines = 0
    for n, column in enumerate(self.columns):
      cell = rowcells[n]

      # If this cell was spanned by the previous, ignore it.
      if cell.isSpanned():
        continue;

      # Compute total column width, over all spanned columns
      w = column.width
      nspan = cell.getSpan()
      while nspan > 1:
        w += 1      # for the delimiter
        w += self.columns[n+nspan-1].width
        nspan -= 1
      if w <= 0 and len(cell.getData()) > 0:
        fatal("Unable to compute text table widths for " + self.tableLine + \
          ".  Specify them manually. (w=" + str(w) + ", nspan=" + str(nspan) + ")")

      cell.format(w)

      nline = cell.lineCount()
      if nline > maxLines:
        maxLines = nline

    #cprint(self.tableLine + ": MaxLines=" + str(maxLines))
    # Now that we know how many lines the largest cell is, we can do vertical
    # alignment
    for n, column in enumerate(self.columns):
      cell = rowcells[n]
      if not cell.isSpanned():
        cell.valign(maxLines)

    # Cells may be wrapped onto multiple lines.
    # As we emit each cell, we reduce its content by the line just emitted
    # When all cells have become empty, we're done
    # Always go through once, so blank lines are processed
    for i in range(0, maxLines):
      self.formatOneOutputLine(rowcells, i)

      if self.vpad:
        self.output(".rs 1")

  #
  # Output one real line of output.  The cells in rowcells are adjusted
  # for whatever was emitted
  # rowcells is an array of TableCell objects
  #
  def formatOneOutputLine(self, rowcells, lineNo):
    line = ""
    nColData = len(rowcells)
    for n, column in enumerate(self.columns):
      cell = rowcells[n]

      # If this cell was spanned by the previous, ignore it.
      if cell.isSpanned():
        continue;

      # Look ahead into the following cells, to see if this is supposed to span
      nspan = cell.getSpan()
      lastSpanningColumn = self.columns[n+nspan-1]

      content = cell.getLine(lineNo)
      line += content

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
    self.output(" " * self.tindent + line)

#} End of class TableFormatter

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
def parseTableRows(lines, columnDescriptions):
  ncols = len(columnDescriptions)

  # Split all the lines into cells
  splitLines = []

  colno = 0
  regex = re.compile(r"^<col=(\d+)>$")
  for line in lines:
    m = regex.match(line)
    if m:
      colno = int(m.group(1))
      if colno >= ncols:
        fatal("<table>: " + line + ": column too large; # of columns is " + str(ncols))
      lineOffset = 0
      continue

    # First column always creates a new row on the end
    if colno == 0:
      splitLines.append(TableRow(line, columnDescriptions))
      continue

    # Possibly more lines in this than first col.  Add enough lines to update
    while lineOffset >= len(splitLines):
      splitLines.append(TableRow("", columnDescriptions))
    row = splitLines[lineOffset]
    row.setCols(colno, line, columnDescriptions)
    lineOffset += 1

  return splitLines

class TableRow:#{
  SINGLE = 0
  DOUBLE = 1
  TEXT = 2

  # type: SINGLE, DOUBLE, or TEXT
  # columns: array of TableCell

  def __init__(self, line, columnDescriptions):
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
    nColDesc = len(columnDescriptions)
    for colno, col in enumerate(rowtext):
      if colno < nColDesc:
        self.columns.append(TableCell(col, columnDescriptions[colno]))
      # Give error? Probably lots of existing tables with trailing |
      # Give error if col is non-empty?

    self.resetSpans()

  # For each column, look at following columns and figure out
  # how many columns wide it is.
  # Set the spanning count variable inside each TableCell
  def resetSpans(self):
    nColData = len(self.columns)
    for n, col in enumerate(self.columns):
      nspan = 1
      for m in range(n+1, nColData):
        if self.columns[m].isSpanned():
          nspan += 1
        else:
          break
      col.spanning = nspan

  # Add columns from a line, starting at a given column number
  # Existing columns are overwritten
  def setCols(self, colno, line, columnDescriptions):
    if line == "":
      # Don't bother creating empty cells on the line
      return
    maxcol = len(columnDescriptions)
    rowtext = line.split("|")
    for data in rowtext:
      if colno == maxcol:
        fatal("<table>: <col=" + str(colno) + "> Too many columns of data: " + line)
      # Fill in any missing cells
      while colno >= len(self.columns):
        self.columns.append(TableCell("", columnDescriptions[len(self.columns)]))
      self.columns[colno] = TableCell(data, columnDescriptions[colno])
      colno += 1
    self.resetSpans()

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
# } End of class TableRow

class TableCell: #{
  SPAN = 0
  TEXT = 1

  # type: SPAN or TEXT
  # data: the text, or ""
  # spanning: number of cells across
  # align: 0, 'l', 'r', 'c', for default, left, right or centre
  def __init__(self, data, columnDescription):
    self.columnDescription = columnDescription
    if data == "<span>":
      self.type = self.SPAN
      data = ""
    else:
      self.type = self.TEXT
    self.spanning = 1
    if data.startswith("<align=c>"):
      self.align = 'center'
    elif data.startswith("<align=r>"):
      self.align = 'right'
    elif data.startswith("<align=l>"):
      self.align = 'left'
    elif data.startswith("<align=h>"):
      self.align = 'hang'
    else:
      self.align = '0'
    if not self.isDefaultAlignment():
      data = data[9:]

    self.data = self.convertData(data)

    m = re.match("<class=(.*?)>", data)
    if m:
      self.userClass = m.group(1)
      self.data = self.data[m.end():]
    else:
      self.userClass = None

  def convertData(self, data):
    if not self.columnDescription.preserveSpaces:
      return data.strip()

    # 2007=Figure Space
    # Replace all runs of spaces with Figure Space;
    # but leave all single spaces as break points;
    # treat leading spaces as run so even single leading is preserved
    # Remove trailing spaces
    data = data.rstrip()
    n = 2
    st = 0
    for i in range(0, len(data)):
      if data[i] == ' ':
        if n == 0:
          st = i # Begining of new run
        n += 1
      else: # End of run
        if n > 1: # More than one in run
          # Change the run
          data = data[0:st] + '\u2007' * (i-st) + data[i:]
        n = 0
    return data

  def getUserClass(self):
    return self.userClass

  def getVAlignment(self):
    return self.columnDescription.valign

  def getAlignment(self):
    if self.isDefaultAlignment():
      return self.columnDescription.align
    return self.align

  def getLeader(self):
    return self.columnDescription.leader;

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

  # Format up our data in `w' columns, using the alignment specified by the TableCell column
  # starts with getData(), and populates the lines[] variable with the results
  # After calling this method, you can use lineCount() and getLine()
  def format(self, w):
    # Figure out the alignment
    align = self.getAlignment()
    if self.isDefaultAlignment() and self.columnDescription.hang:
      align = "hang"

    if self.columnDescription.leaderChars != None:
      self.lines = alignLine(self.getData(), align, w, self.columnDescription.leaderChars)
    else:
      self.lines = alignLine(self.getData(), align, w)


  # Vertical align in N
  def valign(self, n):

    m = len(self.lines)
    if self.columnDescription.valign == "bottom":
      insert = n-m
    elif self.columnDescription.valign == "middle":
      insert = (n-m)//2
    elif self.columnDescription.valign == "top":
      insert = 0

    # Always have a line[0], use it for the width
    w = len(self.lines[0])

    for i in range(0, insert):
      self.lines.insert(0, ' ' * w)

    for i in range(len(self.lines), n):
      self.lines.append(' ' * w)

  def lineCount(self):
    return len(self.lines)

  def getLine(self, n):
    return self.lines[n] if n < len(self.lines) else ""
# } End of class TableCell

# legal attributes on <illustration>
illustrationAttributes = [
  "content", "src", "rend", "id",
]

# rend= options on <illustration>
illustrationRendOptions = [
  "w", "h",
  "align",
  "left", "right", "center",
  "occupy",
  "link",
]

# legal attributes on <tb>
tbAttributes = [
  "rend",
]

# rend= options for <tb>
tbRendOptions = [
  "text",       # text:hidden
  "mt", "mb", "ls", "lc", "thickness", "w", "right", "left", "align",
]

# Line used in text output for a <tb>
textTbLine = "▹                 *        *        *        *        *"

lRendOptions = [
  "center", "right", "left",
  "mr", "ml", "mt", "mb",
  "sa", "sb",
  "xlg", "xlarge", "lg", "large", "xsm", "xsmall", "sm", "small", "fs",
  "under", "bold", "sc", "smallcaps", "i", "italic",
  "align-last", "triple"
]

# <lg> is almost the same as <l>; but not quite.  Some of this all gets
# passed off to <l> and can be overridden in <l>
lgRendOptions = [
  "center", "right", "left", "poetry", "block", "block-right",
  "mr", "ml", "mt", "mb",
  "sa", "sb",
  "xlg", "xlarge", "lg", "large", "xsm", "xsmall", "sm", "small", "fs",
  "under", "bold", "sc", "smallcaps", "i", "italic",
]

# These are the font styles in the lgRendOptions, and their mapping to
# text letters
textFontStyleMap = {
  "bold"   : "=",
  "under"  : "=",
  "italic" : "_",
  "i"      : "_",
}

# Used in <lg> and <table> (currently); map from our keyword to css keyword
fontSizeMap = {
  "xlg"   : "x-large",
  "xlarge": "x-large",
  "lg"    : "large",
  "large" : "large",
  "xsm"   : "x-small",
  "xsmall": "x-small",
  "sm"    : "small",
  "small" : "small",
}


# rend= options for <quote>
quoteRendOptions = [
  "right", "w", "fs"
]

# rend= options for <table>
tableRendOptions = [
  # Text only
  "pad", "textwidth",

  # html only
  "vp", "hp", "border", "left", "flushleft", "hang",

  # html fontsize options
  "xlg", "xlarge", "lg", "large", "xsm", "xsmall", "sm", "small", "fs",

  # ignored, but the default
  "center",
]

# CSS uses for leaders; the table cell pattern character L, or L(name)
leaderCSS = """[561] td.{0} {{
  max-width:40em;
  overflow-x:hidden;
  display:block;
}}
td.{0}:after {{
  float:left;
  width:0;
  white-space:nowrap;
  content: "{1}";
  text-indent:0;
}}
td.{0} span {{
  background:white;
}}
"""

poetryLeftCSS = """[230]
div.lgp { }

div.lgp p {
  text-align:left; text-indent:0; margin-top:0; margin-bottom:0;
}

.poetry-container {
  display:block; text-align:left; margin-left:2em;
}

.stanza-inner {
  display:inline-block;
}

.stanza-outer {
  page-break-inside: avoid;
}

.stanza-inner .line0 {
  display:inline-block;
}
.stanza-outer .line0 {
  display:block;
}
"""

poetryCenterCSS = """[230]
div.lgp {
  display:inline-block;
  text-align: left;
}

div.lgp p {
  text-align:left;
  margin-top:0;
  margin-bottom:0;
}

.poetry-container {
  text-align:center;
}
"""

illustrationRightCSS = """[380]
.figright {
  float:right;
  clear:right;
  margin-left:1em;
  margin-bottom:1em;
  margin-top:1em;
  margin-right:0;
  padding:0;
  text-align:center;
}
"""

illustrationLeftCSS = """[383]
.figleft {
  float:left;
  clear:left;
  margin-right:1em;
  margin-bottom:1em;
  margin-top:1em;
  margin-left:0;
  padding:0;
  text-align:center;
}
"""

illustrationCenterCSS = """[386]
.figcenter {
  text-align:center;
  margin:1em auto;
  page-break-inside: avoid;
}
"""

illustrationCSS = {
    "right"  : illustrationRightCSS,
    "left"   : illustrationLeftCSS,
    "center" : illustrationCenterCSS,
}

headingCSS = {
  1 : """[250]
    h1 {
      text-align:center;
      font-weight:normal;
      page-break-before: always;
      font-size:1.2em; margin:2em auto 1em auto
    }
  """,

  2 : """[254]
    h2 {
      text-align:center;
      font-weight:normal;
      font-size:1.1em;
      margin:1em auto 0.5em auto;
    }
  """,

  3: """[258]
    h3 {
      text-align:center;
      font-weight:normal;
      font-size:1.0em;
      margin:1em auto 0.5em auto;
      page-break-after:avoid;
    }
  """,

  4 : """[260]
    h4 {
      text-align:center;
      font-weight:normal;
      font-size:1.0em;
      margin:1em auto 0.5em auto;
      page-break-after:avoid;
    }
  """
}

paragraphCSS = """[811]
.pindent { margin-top:0; margin-bottom:0; text-indent:1.5em; }
.noindent { margin-top:0; margin-bottom:0; text-indent:0; }
.hang { padding-left:1.5em; text-indent:-1.5em; }"""

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

summaryCSS = {
  # div only applies to the first para.  For multi-para, regular code
  # will emit <p class="pindent">
  summaryHang : """[1234]
  .summary {
    margin-top:1em;
    margin-bottom:1em;
    padding-left:3em;
    padding-right:1.5em;
    text-indent:-1.5em;
  }
  .summary .pindent {
    text-indent:-1.5em;
  }""",
  summaryIndent : """[1234]
  .summary {
    margin-top:1em;
    margin-bottom:1em;
    padding-left:1.5em;
    padding-right:1.5em;
    text-indent:1.5em;
  }""",
  summaryCenter : """[1234]
  .summary {
    margin-top:1em;
    margin-bottom:1em;
    padding-left:1.5em;
    padding-right:1.5em;
    text-indent:0em;
    text-align-last:center;
  }
  .summary .pindent {
    text-indent:0;
    text-align-last:center;
  }""",
  summaryBlock : """[1234]
  .summary {
    margin-top:1em;
    margin-bottom:1em;
    padding-left:1.5em;
    padding-right:1.5em;
  }
  .summary .pindent {
    text-indent: 0;
  }"""
}

dropCapCSS = """[3333]
  .dropcap {
    float:left;
    clear: left;
    margin:0 0.1em 0 0;
    padding:0;
    line-height: 1.0em;
    font-size: 200%;
  }
"""


if __name__ == '__main__':
  from main import main
  main()
