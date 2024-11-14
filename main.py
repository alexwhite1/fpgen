from optparse import OptionParser
import re
import sys, os
import unittest
import zipfile
import fnmatch

import config
from fpgen import Lint, Text, HTML
from kindle import Kindle, EPub, PDF
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
    from testtext import TestTextInline, TestTextRewrap, TestTextoneL, \
        TestTextFormatLineGroup
    from footnote import TestFootnote
    from template import TestTemplate
    from testhtml import TestHTMLPara
    from testother import TestBookVarious
    for cl in [
      TestParseTableColumn, TestMakeTable, TestDrama, TestParsing,
      TestParseTagAttributes, TestOneDramaBlockMethod, TestTextRewrap,
      TestTextInline, TestTableCellFormat, TestTemplate, TestFootnote,
      TestHTMLPara, TestTextoneL, TestTextFormatLineGroup,
      TestBookVarious
    ]:
      tests.append(l.loadTestsFromTestCase(cl))
    tests = l.suiteClass(tests)
    unittest.TextTestRunner(verbosity=2).run(tests)
    exit(0)

  if options.ebookid != "":
    options.formats = "thkep"
    if not re.match("^20[012]\d[01]\d[0-9a-zA-Z][0-9a-zA-Z]$", options.ebookid):
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

def getConvertArgs(modelArgs, infile, outfile, hb):
  args = []
  args.append("ebook-convert")
  args.append(infile)
  args.append(outfile)
  if config.pn_cover != "":
    args.append("--cover")
    args.append(config.pn_cover)

  fonts = hb.getFonts()
  if len(fonts) > 0:
    args.append("--embed-all-fonts")

  args.extend(OPT_COMMON_ARGS)
  args.extend(modelArgs)

  if config.uopt.getopt('preserve-line-height', 'false') == 'true':
    args.append("--minimum-line-height")
    args.append("0")

  extra = config.uopt.getopt('extra-css')
  if extra:
    args.append("--extra-css")
    args.append("\"" + extra + "\"")

  # Normally have two levels of TOC, but allow for none, one or three
  tocLevels = config.uopt.getopt('toc-levels', '2')
  try:
    tocLevels = int(tocLevels)
  except Exception:
    fatal("Bad toc-levels option value: " + tocLevels)
  if tocLevels > 3 or tocLevels < 0:
    fatal("toc-levels option must be between 0 and 3: " + str(tocLevels))
  for level in range(tocLevels):
    # "--level1-toc", "\"//h:h1\"",
    l = str(level+1)
    args.append("--level" + l + "-toc")
    args.append("//h:h" + l)

  extra = os.environ.get('FPGEN_EBOOK_CONVERT_EXTRA_ARGS')
  if extra:
    print("Extra conversion args: " + extra)
    args.append(extra)
  return args

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
    hb = EPub(options.infile, outfile, options.debug)
    print("creating Epub")
    hb.run()

    preserveMargins = (config.uopt.getopt('preserve-margins', 'false') == 'true')
    args = getConvertArgs(OPT_EPUB_ARGS, outfile, "{}.epub".format(bn), hb)

    if config.uopt.getopt('epub-margin-left') != "": # added 27-Mar-2014
      args.append("--margin-left")
      args.append("{}".format(config.uopt.getopt('epub-margin-left')))
    elif preserveMargins:
      args.append("--margin-left -1")

    if config.uopt.getopt('epub-margin-right') != "": # added 27-Mar-2014
      args.append("--margin-right")
      args.append("{}".format(config.uopt.getopt('epub-margin-right')))
    elif preserveMargins:
      args.append("--margin-right -1")

    # call(OPT_EPUB_ARGS, shell=False)
    js = " ".join(args)
    msgs.dprint(1, js)
    os.system(js)

    if not options.saveint:
      os.remove(outfile)
    madeEpub = True

  if 'k' in options.formats:
    print("creating Kindle (.mobi & -k.epub)")
    # make epub as source for kindle
    outfile = "{}-e2.html".format(bn)
    hb = Kindle(options.infile, outfile, options.debug)
    hb.run()
    preserveMargins = (config.uopt.getopt('preserve-margins', 'false') == 'true')
    args = getConvertArgs(OPT_EPUB_ARGS, outfile, "{}-k.epub".format(bn), hb)
    if preserveMargins:
      args.extend(OPT_PRESERVE_MARGINS)

    # call(OPT_EPUB_ARGS, shell=False)
    js = " ".join(args)
    msgs.dprint(1, js)
    os.system(js)

    # generate mobi with Kindlegen based on epub made by ebook-convert
    # os.system("kindlegen {0}-k.html -o {0}.mobi".format(bn))
    msgs.dprint(1, "kindlegen {0}-k.epub -o {0}.mobi".format(bn))
    os.system("kindlegen {0}-k.epub -o {0}.mobi".format(bn))

    if not options.saveint:
      os.remove("{0}-e2.html".format(bn))

  if 'p' in options.formats:
    outfile = "{}-p.html".format(bn)
    hb = PDF(options.infile, outfile, options.debug)
    print("creating PDF")
    hb.run()
    preserveMargins = (config.uopt.getopt('preserve-margins', 'false') == 'true')
    args = getConvertArgs(OPT_PDF_ARGS, outfile, "{}-a5.pdf".format(bn), hb)

    if preserveMargins:
      args.extend(OPT_PRESERVE_MARGINS)
      args.append('--pdf-default-font-size')
      args.append(config.uopt.getopt('pdf-default-font-size', "13"))
    else:
      args.extend(OPT_PDF_ARGS_RL)
      # fpgen option -> [ebook-convert option, value]
      for k,v in PDF_CONFIG_OPTS.items():
        args.append(v[0])
        args.append(config.uopt.getopt(k, v[1]))

    extra = os.environ.get('FPGEN_EBOOK_CONVERT_EXTRA_ARGS_PDF')
    if extra:
      print("Extra pdf conversion args: " + extra)
      args.append(extra)

    # call(OPT_PDF_ARGS, shell=False)
    js = " ".join(args)

    msgs.dprint(0, js)
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
    for suffix in [ ".txt", ".html", ".mobi", ".epub", "-k.epub", "-a5.pdf" ]:
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

# set defaults
#  --remove-paragraph-spacing removed
#  --remove-first-image removed
OPT_EPUB_ARGS = [
 #"--flow-size", "500",
 "--change-justification", "\"justify\"",
 "--embed-all-fonts",
 "--epub-flatten",
]

OPT_PDF_ARGS = [
 "--paper-size", "\"a5\"",
 "--pdf-page-margin-top", "20",
 "--pdf-page-margin-bottom", "20",
# "--pdf-serif-family", "tahoma",
]

OPT_PDF_ARGS_RL = [
 "--pdf-page-margin-right", "20",
 "--pdf-page-margin-left", "20",
]

PDF_CONFIG_OPTS = {
  # fpgen option             : [ebook-convert option, value]
  'pdf-default-font-size'     : [ '--pdf-default-font-size', "13" ],
  'pdf-margin-left'           : [ '--pdf-page-margin-left', "20" ],
  'pdf-margin-right'          : [ '--pdf-page-margin-right', "20" ],
}

OPT_COMMON_ARGS = [
 "--chapter-mark", "\"none\"",
 "--preserve-cover-aspect-ratio",
 "--disable-remove-fake-margins",
 "--page-breaks-before", "\"//h:div[@style='page-break-before:always'] | //*[(name()='h1' or name()='h2') and not(contains(@class, 'nobreak'))]\"",
 "--sr1-search", "\"<hr class=.pbk./>\"",
 "--sr1-replace", "\"<div style='page-break-before:always'></div>\"",
 "--sr1-search", "\"<br\/><br\/>\"",
 "--sr1-replace", "—",
 "--chapter", "\"//*[(name()='h1' or name()='h2')]\"",
]

OPT_PRESERVE_MARGINS = [
 "--margin-left", "-1",
 "--margin-right", "-1",
]

if __name__ == '__main__':
  main()
