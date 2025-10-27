#!python

# Upload one or more files to a book directory on fadedpage.
# No relative paths are permitted; and only files ending in .jpg or .png
# are transferred.
# You must give the bookid using the --bookid option; and a list of files
# which exist locally, in the current directory, that are sent to the
# book directory on the server.
#
# Requires a fadedpage admin login.  Set your user and password
# either through the --user and --password options, or with
# the FPUSER and FPPASSWORD environment variables.
#

import sys
import os
import re
from optparse import OptionParser
from epub import get_epub_info
from FPSession import FPSession

def fatal(line):
  sys.stderr.write("ERROR " + line + "\n")
  exit(1)

def run(cmd):
  sys.stderr.write("-->" + cmd + "\n")
  exit = os.system(cmd)
  if exit != 0:
    fatal(f"Exit code {exit} for command {cmd}")

parser = OptionParser()
parser.add_option("-u", "--user", dest="user", default=os.environ['FPUSER'] if 'FPUSER' in os.environ else None)
parser.add_option("-p", "--password", dest="password", default=os.environ['FPPASSWORD'] if 'FPPASSWORD' in os.environ else None)
parser.add_option("-s", "--sandbox", action="store_true", dest="sandbox",
    default=False)
parser.add_option("-b", "--bookid", dest="bookid", default=None)
(options, args) = parser.parse_args()

if options.password == None or options.user == None:
  fatal("Must specify an fp user or password.")

if options.bookid == None:
  fatal("Must specify a book id!")

if not re.match(r"^20[012]\d[01]\d[0-9a-zA-Z][0-9a-zA-Z]$", options.bookid):
  fatal("Bookid doesn't look correct: " + options.bookid)

if len(args) < 1:
  fatal("Usage: upload-file [--user fpusername] [--password fppassword] [--bookid book-id] file ...")

imgFormats = { ".jpg", ".png" }
bookFormats = { ".epub", ".pdf", ".mobi" }

with FPSession(options.user, options.password, sandbox=options.sandbox) as fps:
  for file in args:
    found = False
    book = False
    for format in imgFormats:
      if file.endswith(format):
        found = True
        break
    if not found:
      for format in bookFormats:
        if file.endswith(format):
          book = True
          break
      if not book:
        fatal("File " + file + " must end in " + str(imgFormats) + " or " + str(bookFormats))
    dirname = os.path.dirname(file)
    basename = os.path.basename(file)
    if not re.match(r"^[\w \.]*$", dirname):
      fatal("Bad directory: " + dirname)
    if not re.match(r"^[\w \.]*$", basename):
      fatal("Bad filename: " + basename)

    if book:
      fps.uploadFormat(options.bookid, format[1:])
    else:
      fps.uploadOne(options.bookid, file)
