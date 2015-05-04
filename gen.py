#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
import re, sys, string, os, shutil

# | //h:hr[@class='chap']

ARGS = [
 "--publisher", "\"Distributed Proofreaders Canada\"",
 "--change-justification", "\"left\"",
 "--chapter-mark", "\"none\"",
 "--disable-remove-fake-margins",
 "--page-breaks-before", "\"//h:div[@style='page-break-before:always'] | //*[(name()='h1' or name()='h2') and not(@class='nobreak')] | //h:p[@class='chapter']\"",
 "--extra-css", "\".pagenum {visibility: hidden;} .totoc {visibility:hidden;} " +
    ".footnote .label {position:static; float:left; width:auto; text-align:left;}\"",
 "--sr1-search", "\"<hr class=.pbk./>\"",
 "--sr1-replace", "\"<div style='page-break-before:always'></div>\"",
 "--sr2-search", "\"<hr class=.chap./>\"",
 "--sr2-replace", "\"<div style='page-break-before:always'></div>\"",
# "--sr1-search", "\"<br\/><br\/>\"",
# "--sr1-replace", "—",
 "--chapter", "\"//*[(name()='h1' or name()='h2')]\"",
 "--level1-toc \"//h:h1\" --level2-toc \"//h:h2\""
]

def convert(basename, targettype, targetOptions):
  html = basename + ".html"
  target = basename + targettype
  command = [ "ebook-convert", html, target] + commonArgs + ARGS + targetOptions
  commandLine = " ".join(command)
  print("Running: " + commandLine);
  os.system(commandLine)
  return;

def usage():
  print("Usage: gen [--author author] [--title title] [--pubdate pubdate] " +
      "[--tags tags] [--cover cover] [--remove-first-image] file.html")
  print("--cover \"\" to indicate no cover page; one will be generated.");
  exit(1)
  return;

# process command line
parser = OptionParser()
parser.add_option("-a", "--author", dest="author", default="unknown")
parser.add_option("-t", "--title", dest="title", default="unknown")
parser.add_option("-p", "--pubdate", dest="pubdate", default="unknown")
parser.add_option("-g", "--tags", dest="tags", default="unknown")
parser.add_option("-c", "--cover", dest="cover", default="images/cover.jpg")
parser.add_option("-r", "--remove-first-image", action="store_true", dest="removeFirstImage", default=False)

(options, args) = parser.parse_args()

commonArgs = [
    "--authors \"" + options.author + "\"",
    "--title \"" + options.title + "\"",
    "--pubdate \"" + options.pubdate + "\"",
    "--tags \"" + options.tags + "\"",
]
if options.cover != "":
    commonArgs = commonArgs + [ "--cover", "\"" + options.cover + "\"" ]
if options.removeFirstImage != False:
    commonArgs = commonArgs + [ "--remove-first-image" ]

if len(args) != 1:
  usage()

# check input filename
m = re.match('(.*?)\.html$', args[0])
if not m:
  print("source filename must end in \".html\".")
  exit(1)
else:
  basename = m.group(1)

convert(basename, ".epub", [
  "--change-justification", "left"
  ]
)

convert(basename, "-a5.pdf", [
  "--paper-size", "a5",
  "--margin-left", "20",
  "--margin-right", "20",
  "--margin-top", "20",
  "--margin-bottom", "20",
  "--change-justification", "left",
  ]
)

#convert(basename, ".mobi", [
#  "--mobi-file-type", "new"
#  ]
#)

# Run kindlegen to create the .mobi file.  If you use ebook-convert, then it will work fine
# on fire* devices; but not on kindle devices.
commandLine = "kindlegen " + basename + ".epub"
print("Running: " + commandLine)
os.system(commandLine)
