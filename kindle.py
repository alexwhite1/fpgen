#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import re
from msgs import cprint, uprint, dprint, fatal
from fpgen import HTML

class NonHTML(HTML): #{
  def __init__(self, ifile, ofile, d, letter):
    HTML.__init__(self, ifile, ofile, d, letter)

  # No page numbers on any non-html
  def getPageNumberCSS(self):
    return [
      "[105] .pageno { display:none; }"
    ]

  # No margins on any non-html
  def getMargins(self):
    return "0", "0"

class Kindle(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'k')

  # On Kindle, leaders, at least the way we do them, don't work, so
  # never do them.
  def getLeaderName(self, col):
    return None

  # epub ragged right
  def getTextAlignment(self):
    return "left"
#}

class EPub(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'e')

  # epub ragged right
  def getTextAlignment(self):
    return "left"
#}

class PDF(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'p')
#}
