#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re

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

def dprint(level, msg):
  from config import debug
  if int(debug) >= level:
    cprint("{}".format(msg))

def fatal(message):
  sys.stderr.write("fatal: " + message + "\n")
  exit(1)
