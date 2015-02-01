from optparse import OptionParser
import re
import sys, os
import unittest

import config
from fpgen import Lint, Text, HTML
from fpgen import TestParseTableColumn, TestMakeTable, TestParsing
from parse import TestParseTagAttributes
from drama import TestDrama, TestOneDramaBlockMethod
from testtext import TestTextInline, TestTextRewrap

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
  (options, args) = parser.parse_args()

  print("fpgen {}".format(config.VERSION))

  if options.unittest:
    sys.argv = sys.argv[:1]
    l = unittest.TestLoader();
    tests = []
    for cl in [
      TestParseTableColumn, TestMakeTable, TestDrama, TestParsing,
      TestParseTagAttributes, TestOneDramaBlockMethod, TestTextRewrap,
      TestTextInline
    ]:
      tests.append(l.loadTestsFromTestCase(cl))
    tests = l.suiteClass(tests)
    unittest.TextTestRunner(verbosity=2).run(tests)
    exit(0)

  tmp = options.formats
  tmp = re.sub('a|h|t|k|e|p', '', tmp)
  if not tmp == '':
    print("format option {} not supported".format(tmp))
    exit(1)

  # 'a' format is 'all'
  if options.formats == 'a':
    options.formats = "htpek"

  # check input filename
  m = re.match('(.*?)-src.txt', options.infile)
  if not m:
    print("source filename must end in \"-src.txt\".")
    print("example: midnight-src.txt will generate midnight.html, midnight.txt")
    exit(1)
  else:
    bn = m.group(1)

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
   "--sr1-replace", "—"
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
    os.system(js)

    if not options.saveint:
      os.remove(outfile)
    madeEpub = True

  if 'k' in options.formats:
    print("creating Kindle")
    # make epub as source for kindle
    outfile = "{}-e2.html".format(bn)
    hb = HTML(options.infile, outfile, options.debug, 'e')
    hb.run()
    OPT_EPUB_ARGS[1] = "{}-e2.html".format(bn)
    OPT_EPUB_ARGS[2] = "{}-e2.epub".format(bn)
    if config.pn_cover != "":
      OPT_EPUB_ARGS[4] = config.pn_cover
    # call(OPT_EPUB_ARGS, shell=False)
    js = " ".join(OPT_EPUB_ARGS)
    os.system(js)

    # generate mobi with Kindlegen based on epub made by ebook-convert
    # os.system("kindlegen {0}-k.html -o {0}.mobi".format(bn))
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
    os.system(js)

    if not options.saveint:
      os.remove(outfile)

if __name__ == '__main__':
  main()
