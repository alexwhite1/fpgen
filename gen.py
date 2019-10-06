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
]

EPUB_ARGS = [
  "--change-justification", "left",
  "--sr3-search", "\"@media handheld\"",
  "--sr3-replace", "\"@media all\"",
]

def convert(basename, targettype, targetOptions, commonArgs):
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

def fatal(line):
  sys.stderr.write("Error: " + line + "\n")
  exit(1)

def getMeta(tree, name, default):
  for n in name:
    meta = tree.xpath("//meta[@name='" + n + "']/@content")
    if meta:
      break
  if not meta:
    return default
  return meta[0]

def getTitle(tree):
  t = tree.xpath("//head/title/text()")[0]
  m = re.match(r".*eBook of (.*)", t, re.DOTALL)
  if m:
    t = m.group(1)
  m = re.match(r"(.*) by .*", t, re.DOTALL)
  if m:
    t = m.group(1)
  return t.strip()

def getCover(tree):
  # The cover could be in either
  #   <meta name='cover' content='page'>
  # or instead in
  #   <link rel="coverpage" href="page">
  cover = getMeta(tree, "cover", None)
  if cover == None:
    cover = tree.xpath("//head/link[@rel='coverpage']/@href")[0]
  if cover == None:
    return "images/cover.jpg"
  return cover

def removeFirstImage(tree, cover):

  # Find the first image in the file
  # i.e. <img src='page'>
  img = tree.xpath("//body/descendant::img[1]/@src")[0]
  return cover == img

# "--level1-toc \"//h:h1\" --level2-toc \"//h:h2\""
def tocLevels(tree):
  content = getMeta(tree, [ "fadedpage-toc" ], "h1,h2")
  tags = content.split(',')
  if len(tags) > 3:
    fatal("Meta tag fadedpage-toc contains more than three levels: " + str(tags))
  args = [ ]
  n = 1
  for tag in tags:
    args.append('--level' + str(n) + '-toc \"//h:' + tag + '\"')
    n += 1
  return args

def main(argv):
  # process command line
  parser = OptionParser()
  parser.add_option("-a", "--author", dest="author", default=None)
  parser.add_option("-t", "--title", dest="title", default=None)
  parser.add_option("-p", "--pubdate", dest="pubdate", default=None)
  parser.add_option("-g", "--tags", dest="tags", default=None)
  parser.add_option("-c", "--cover", dest="cover", default=None)
  parser.add_option("-r", "--remove-first-image", action="store_true",
      dest="removeFirstImage", default=None)

  (options, args) = parser.parse_args(argv[1:])

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
  if title == None:
    title = getTitle(tree)
  author = getMeta(tree, [ "DC.Creator" ], options.author)
  pubdate = getMeta(tree, [ "pss.pubdate", "DC.Created", "DC.date.created" ],
      options.pubdate)
  tags = getMeta(tree, [ "DC.Subject", "Tags" ], options.tags)

  if options.cover == None:
    options.cover = getCover(tree)

  if options.removeFirstImage == None:
    options.removeFirstImage = removeFirstImage(tree, options.cover)

  commonArgs = [ ]
  if author:
      commonArgs = commonArgs + [ "--authors \"" + author + "\"" ]
  if title != None:
      commonArgs = commonArgs + [ "--title \"" + title + "\"" ]
  if pubdate != None:
      commonArgs = commonArgs + [ "--pubdate \"" + pubdate + "\"" ]
  if tags != None:
      commonArgs = commonArgs + [ "--tags \"" + tags + "\"" ]
  if options.cover != "":
      commonArgs = commonArgs + [ "--cover", "\"" + options.cover + "\"" ]
  if options.removeFirstImage != False:
      commonArgs = commonArgs + [ "--remove-first-image" ]

  commonArgs = commonArgs + tocLevels(tree)

  print("Using args:\n" + str(commonArgs))

  convert(basename, ".epub", EPUB_ARGS, commonArgs)

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
  convert(basename, "-a5.pdf", pdfargs, commonArgs)

  #convert(basename, ".mobi", [
  #  "--mobi-file-type", "new"
  #  ]
  #, commonArgs)

  # Run kindlegen to create the .mobi file.
  # If you use ebook-convert, then it will work fine
  # on fire* devices; but not on kindle devices.
  commandLine = "kindlegen " + basename + ".epub"
  print("Running: " + commandLine)
  os.system(commandLine)

if __name__ == "__main__":
  main(sys.argv)
