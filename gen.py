#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# For lxml html parsing package, need to do: python -m pip install lxml

from optparse import OptionParser
import re, sys, string, os, shutil
from lxml import html

# | //h:hr[@class='chap']

ARGS = [
 "--publisher", "\"Distributed Proofreaders Canada\"",
 "--change-justification", "\"left\"",
 "--chapter-mark", "\"none\"",
 "--preserve-cover-aspect-ratio",
 "--disable-remove-fake-margins",
 "--page-breaks-before", "\"//h:div[@style='page-break-before:always'] | //*[(name()='h1' or name()='h2') and not(contains(@class, 'nobreak'))] | //h:p[@class='chapter']\"",
 "--extra-css", "\".pagenum, .totoc, .pb {visibility: hidden;} " +
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

EPUB_ARGS = [
  "--change-justification", "left",
  "--sr3-search", "\"@media handheld\"",
  "--sr3-replace", "\"@media all\"",
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

def getMeta(tree, name, default):
  for n in name:
    meta = tree.xpath("//meta[@name='" + n + "']/@content")
    if meta:
      break
  if not meta:
    return default
  return meta[0]

# process command line
parser = OptionParser()
parser.add_option("-a", "--author", dest="author", default="unknown")
parser.add_option("-t", "--title", dest="title", default="unknown")
parser.add_option("-p", "--pubdate", dest="pubdate", default="unknown")
parser.add_option("-g", "--tags", dest="tags", default="unknown")
parser.add_option("-c", "--cover", dest="cover", default="images/cover.jpg")
parser.add_option("-r", "--remove-first-image", action="store_true", dest="removeFirstImage", default=False)

(options, args) = parser.parse_args()

if len(args) != 1:
  usage()

# check input filename
htmlfile = args[0]
m = re.match('(.*?)\.html$', htmlfile)
if not m:
  print("source filename must end in \".html\".")
  exit(1)
else:
  basename = m.group(1)

with open(htmlfile, "r", encoding="utf-8") as input:
  tree = html.parse(input)
  title = getMeta(tree, [ "DC.Title" ], options.title)
  author = getMeta(tree, [ "DC.Creator" ], options.author)
  pubdate = getMeta(tree, [ "pss.pubdate", "DC.Created", "DC.date.created" ],
      options.pubdate)
  meta = tree.xpath("//link[@rel='coverpage']/@href")
  if meta:
    cover = meta[0] if meta else options.cover

commonArgs = [
    "--authors \"" + author + "\"",
    "--title \"" + title + "\"",
    "--pubdate \"" + pubdate + "\"",
]
if options.tags != "unknown":
    commonArgs = commonArgs + [ "--tags \"" + options.tags + "\"" ]
if cover != "":
    commonArgs = commonArgs + [ "--cover", "\"" + cover + "\"" ]
if options.removeFirstImage != False:
    commonArgs = commonArgs + [ "--remove-first-image" ]

convert(basename, ".epub", EPUB_ARGS)

pdfargs = [
  "--paper-size", "a5",
  "--pdf-page-margin-left", "20",
  "--pdf-page-margin-right", "20",
  "--pdf-page-margin-top", "20",
  "--pdf-page-margin-bottom", "20",
  "--change-justification", "left",
  ]
extra = os.environ.get('FPGEN_EBOOK_CONVERT_EXTRA_ARGS_PDF')
if extra:
  print("Extra pdf conversion args: " + extra)
  pdfargs.append(extra)
convert(basename, "-a5.pdf", pdfargs)

#convert(basename, ".mobi", [
#  "--mobi-file-type", "new"
#  ]
#)

# Run kindlegen to create the .mobi file.  If you use ebook-convert, then it will work fine
# on fire* devices; but not on kindle devices.
commandLine = "kindlegen " + basename + ".epub"
print("Running: " + commandLine)
os.system(commandLine)
