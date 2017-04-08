#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import urllib.request
import re
from msgs import cprint, uprint, dprint, fatal

def formatFonts(fonts):
  if len(fonts) == 0:
    return []
  block = []
  for localname,googlename in fonts.items():
    dprint(1, localname + ": " + googlename)
    googlename = googlename.replace(' ', '+')
    localFile = getGoogleFont(googlename)
    block.append("@font-face {\n  font-family: '" + localname + "';\n  font-style: normal;\n  src: url('" + localFile + "');\n}")
  return block

def getGoogleFont(name):
  cssurl = "http://fonts.googleapis.com/css?family=" + name

  try:
    with urllib.request.urlopen(cssurl) as r:
      contents = r.read().decode('utf-8')
    #contents = """
      #@font-face {
      #  font-family: 'Tangerine';
      #  font-style: normal;
      #  font-weight: 700;
      #  src: local('Tangerine Bold'), local('Tangerine-Bold'), url(http://fonts.gstatic.com/s/tangerine/v7/UkFsr-RwJB_d2l9fIWsx3onF5uFdDttMLvmWuJdhhgs.ttf) format('truetype');
      #}"""
  except urllib.error.URLError as e:
    fatal("Cannot find google font " + name + ": " + e.reason)
  dprint(1, str(contents))

  m = re.search("url\((.*?)\)[ ;]", str(contents))
  if not m:
    fatal("Bad font file " + cssurl + " from google: " + str(contents))
  url = m.group(1)
  dprint(1, "Remote ttf: " + url)
  with urllib.request.urlopen(url) as r:
    ttf = r.read()

  # Turn something like Tangerine:bold into Tangerine-bold
  #basename = re.sub(":", "-", name)
  basename = name.replace(":", "-")
  localFile = "font-" + basename + ".ttf"
  with open(localFile, "wb") as f:
    f.write(ttf)
    f.close()
  dprint(1, "Brought google font into " + localFile)

  return localFile
