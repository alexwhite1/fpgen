from optparse import OptionParser
import re
import sys, os
import unittest
import zipfile
import fnmatch

import config
from fpgen import Lint, Text, HTML
import msgs
from msgs import fatal

def main():
  # process command line
  parser = OptionParser()
  parser.add_option("-i", "--infile",
      dest="infile", default="",
      help="input file")
  parser.add_option("-f", "--format",
      dest="formats", default="th",
      help="format=thkep (text,HTML,Kindle,Epub,PDF)")
  parser.add_option("-d", "--debug",
      dest="debug", default="0",
      help="set debug mode level")
  parser.add_option("", "--save",
      action="store_true", dest="saveint", default=False,
      help="save intermediate file")
  parser.add_option("--unittest",
      action="store_true", dest="unittest", default=False, help="run unittests")
  parser.add_option("", "--ebookid",
      dest="ebookid", default="",
      help="Create fadedpage zip file")
  (options, args) = parser.parse_args()

  print("fpgen {}".format(config.VERSION))

  if options.unittest:
    sys.argv = sys.argv[:1]
    l = unittest.TestLoader();
    tests = []
    from testtable import TestParseTableColumn, TestMakeTable, TestTableCellFormat
    from parse import TestParseTagAttributes, TestParsing
    from drama import TestDrama, TestOneDramaBlockMethod
    from testtext import TestTextInline, TestTextRewrap
    from footnote import TestFootnote
    from template import TestTemplate
    from testhtml import TestHTMLPara
    for cl in [
      TestParseTableColumn, TestMakeTable, TestDrama, TestParsing,
      TestParseTagAttributes, TestOneDramaBlockMethod, TestTextRewrap,
      TestTextInline, TestTableCellFormat, TestTemplate, TestFootnote,
      TestHTMLPara
    ]:
      tests.append(l.loadTestsFromTestCase(cl))
    tests = l.suiteClass(tests)
    unittest.TextTestRunner(verbosity=2).run(tests)
    exit(0)

  if options.ebookid != "":
    options.formats = "thkep"
    if not re.match("^20[01]\d[01]\d[0-9a-zA-Z][0-9a-zA-Z]$", options.ebookid):
      fatal("Ebookid doesn't look correct: " + options.ebookid)

  tmp = options.formats
  tmp = re.sub('a|h|t|k|e|p', '', tmp)
  if not tmp == '':
    fatal("format option {} not supported".format(tmp))

  # 'a' format is 'all'
  if options.formats == 'a':
    options.formats = "htpek"

  # Can either use -i file, or just file.
  if len(args) > 1:
    fatal("Too many positional options")

  if len(args) == 1:
    if options.infile == '':
      options.infile = args[0]
    else:
      fatal("Positional argument is incompatible with the file option -i/--infile")

  # Nothing specified? See if exactly one file matching *-src.txt in current dir
  if options.infile == '':
    for file in os.listdir('.'):
      if fnmatch.fnmatch(file, '*-src.txt'):
        if options.infile != '':
          fatal("Input file not specified; multiple found in the current directory.")
        options.infile = file
    if options.infile == '':
      fatal("Missing source file option -i/--infile")

  # check input filename
  m = re.match('(.*?)-src.txt', options.infile)
  if not m:
    print("source filename must end in \"-src.txt\".")
    print("example: midnight-src.txt will generate midnight.html, midnight.txt")
    exit(1)
  else:
    input = m.group(1)

  try:
    processFile(options, input)
  except FileNotFoundError:
    fatal(options.infile + ": File not found")

def processFile(options, bn):

  # run Lint for every format specified
  # user may have included conditional code blocks
  if 't' in options.formats:
    lint = Lint(options.infile, "", options.debug, 't')
    lint.run()
  # all HTML derivatives
  if re.search('h|k|e|p', options.formats):
    lint = Lint(options.infile, "", options.debug, 'h')
    lint.run()

  # set defaults
  #  --remove-paragraph-spacing removed
  #  --remove-first-image removed
  OPT_EPUB_ARGS = [
   "ebook-convert",
   "",
   "",
   "--cover", "\"images/cover.jpg\"",
   #"--flow-size", "500",
   "--change-justification", "\"left\"",
   "--chapter-mark", "\"none\"",
   "--disable-remove-fake-margins",
   "--page-breaks-before", "\"//h:div[@style='page-break-before:always'] | //*[(name()='h1' or name()='h2') and not(@class='nobreak')]\"",
   "--sr1-search", "\"<hr class=.pbk./>\"",
   "--sr1-replace", "\"<div style='page-break-before:always'></div>\"",
   "--sr1-search", "\"<br\/><br\/>\"",
   "--sr1-replace", "—",
   "--chapter", "\"//*[(name()='h1' or name()='h2')]\"",
   "--level1-toc \"//h:h1\" --level2-toc \"//h:h2\""
  ]

  # unused kindle options
  # "--change-justification", "left", (destroys centered blocks)
  # "--mobi-file-type", "new",
  #
  OPT_KINDLE_ARGS = [
    "ebook-convert",
    "",
    "",
    "--cover", "\"images/cover.jpg\"",
    "--no-inline-toc",
    "--sr1-search", "\"<hr class=.pbk./>\"",
    "--sr1-replace", "\"<div style='page-break-before:always'></div>\"",
    "--sr1-search", "\"<br\/><br\/>\"",
    "--sr1-replace", "—",
    "--chapter", "\"//*[(name()='h1' or name()='h2')]\""
  ]

  OPT_PDF_ARGS = [
   "ebook-convert",
   "",
   "",
   "--cover", "\"images/cover.jpg\"",
   "--paper-size", "\"a5\"",
   "--pdf-default-font-size", "\"13\"",
   "--margin-left", "\"20\"",
   "--margin-right", "\"20\"",
   "--margin-top", "\"20\"",
   "--margin-bottom", "\"20\"",
   "--chapter-mark", "\"none\"",
   "--disable-remove-fake-margins",
   "--page-breaks-before", "\"//h:div[@style='page-break-before:always'] | //*[(name()='h1' or name()='h2') and not(@class='nobreak')]\"",
   "--sr1-search", "\"<hr class=.pbk./>\"",
   "--sr1-replace", "\"<div style='page-break-before:always'></div>\"",
   "--sr1-search", "\"<br\/><br\/>\"",
   "--sr1-replace", "—",
   "--level1-toc \"//h:h1\"", "--level2-toc \"//h:h2\"",
  ]

  # generate desired output formats

  if 't' in options.formats:
    outfile = "{}.txt".format(bn)
    tb = Text(options.infile, outfile, options.debug, 't')
    print("creating UTF-8 text")
    tb.run()

  if 'h' in options.formats:
    outfile = "{}.html".format(bn)
    hb = HTML(options.infile, outfile, options.debug, 'h')
    print("creating HTML")
    hb.run()

  madeEpub = False
  if 'e' in options.formats:
    outfile = "{}-e.html".format(bn)
    hb = HTML(options.infile, outfile, options.debug, 'e')
    print("creating Epub")
    hb.run()
    OPT_EPUB_ARGS[1] = "{}-e.html".format(bn)
    OPT_EPUB_ARGS[2] = "{}.epub".format(bn)
    if config.pn_cover != "":
      OPT_EPUB_ARGS[4] = config.pn_cover

    if config.uopt.getopt('epub-margin-left') != "": # added 27-Mar-2014
      OPT_EPUB_ARGS.append("--margin-left")
      OPT_EPUB_ARGS.append("{}".format(config.uopt.getopt('epub-margin-left')))

    if config.uopt.getopt('epub-margin-right') != "": # added 27-Mar-2014
      OPT_EPUB_ARGS.append("--margin-right")
      OPT_EPUB_ARGS.append("{}".format(config.uopt.getopt('epub-margin-right')))

    # call(OPT_EPUB_ARGS, shell=False)
    js = " ".join(OPT_EPUB_ARGS)
    msgs.dprint(1, js)
    os.system(js)

    if not options.saveint:
      os.remove(outfile)
    madeEpub = True

  if 'k' in options.formats:
    print("creating Kindle")
    # make epub as source for kindle
    outfile = "{}-e2.html".format(bn)
    hb = HTML(options.infile, outfile, options.debug, 'k')
    hb.run()
    OPT_EPUB_ARGS[1] = "{}-e2.html".format(bn)
    OPT_EPUB_ARGS[2] = "{}-e2.epub".format(bn)
    if config.pn_cover != "":
      OPT_EPUB_ARGS[4] = config.pn_cover
    # call(OPT_EPUB_ARGS, shell=False)
    js = " ".join(OPT_EPUB_ARGS)
    msgs.dprint(1, js)
    os.system(js)

    # generate mobi with Kindlegen based on epub made by ebook-convert
    # os.system("kindlegen {0}-k.html -o {0}.mobi".format(bn))
    msgs.dprint(1, "kindlegen {0}-e2.epub -o {0}.mobi".format(bn))
    os.system("kindlegen {0}-e2.epub -o {0}.mobi".format(bn))

    if not options.saveint:
      os.remove("{0}-e2.epub".format(bn))
      os.remove("{0}-e2.html".format(bn))

  if 'p' in options.formats:
    outfile = "{}-p.html".format(bn)
    hb = HTML(options.infile, outfile, options.debug, 'p')
    print("creating PDF")
    hb.run()
    OPT_PDF_ARGS[1] = "{}-p.html".format(bn)
    OPT_PDF_ARGS[2] = "{}-a5.pdf".format(bn)

    if config.uopt.getopt('pdf-default-font-size') != "":
      OPT_PDF_ARGS.append("--pdf-default-font-size")
      OPT_PDF_ARGS.append("{}".format(config.uopt.getopt('pdf-default-font-size')))

    if config.uopt.getopt('pdf-margin-left') != "":
      OPT_PDF_ARGS.append("--margin-left")
      OPT_PDF_ARGS.append("{}".format(config.uopt.getopt('pdf-margin-left')))

    if config.uopt.getopt('pdf-margin-right') != "":
      OPT_PDF_ARGS.append("--margin-right")
      OPT_PDF_ARGS.append("{}".format(config.uopt.getopt('pdf-margin-right')))

    if config.pn_cover != "":
      OPT_PDF_ARGS[4] = config.pn_cover

    # call(OPT_PDF_ARGS, shell=False)
    js = " ".join(OPT_PDF_ARGS)

    msgs.dprint(1, js)
    os.system(js)

    if not options.saveint:
      os.remove(outfile)

  # Create a zip file with the ebook id, and all the output formats
  # appropriately named
  if options.ebookid != "":
    epubid = options.ebookid
    zipname = epubid + ".zip"
    print("Writing zip file " + zipname)
    zip = zipfile.ZipFile(zipname, "w", compression = zipfile.ZIP_DEFLATED)
    print("Adding " + bn + "-src.txt")
    zip.write(bn + "-src.txt")
    for suffix in [ ".txt", ".html", ".mobi", ".epub", "-a5.pdf" ]:
      src = bn + suffix
      target = epubid + suffix
      print("Adding " + src + " as " + target)
      zip.write(src, target)
    for dir, subdirs, files in os.walk("images"):
      for file in files:
        image = dir + "/" + file
        print("Adding image: " + image)
        zip.write(image)
    zip.close()

if __name__ == '__main__':
  main()
