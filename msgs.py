#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

# safe print of possible UTF-8 character strings on ISO-8859 terminal
def cprint(s, end=None):
  s = re.sub("◻","-ENSP-", s)
  s = re.sub("◻"," ", s)
  t = "".join([x if ord(x) < 128 else '?' for x in s])
  if end != None:
    print(t, end=end)
  else:
    print(t)

# Emit the UTF-8 chars as \uXXXX hex strings
def uprint(s):
  #s = re.sub("◻"," ", s)
  t = "".join([x if ord(x) < 128 else ("\\u"+hex(ord(x))) for x in s])
  print(t)

def dprint(level, msg):
  from config import debug
  if int(debug) >= level:
    cprint("{}".format(msg))

def fatal(message):
  sys.stderr.write("fatal: " + message + "\n")
  exit(1)

warningTag = {}

def wprint(tag, message, end=None):
  if giveWarning(tag):
    cprint(message, end=end)

def setWarnings(tagList):
  tags = tagList.split()
  for tag in tags:
    warningTag[tag] = False

# Give a warning if tag is **not** in the list of suppressed warnings
def giveWarning(tag):
  return tag not in warningTag
