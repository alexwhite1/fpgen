#!python

# Fetch one or more book's html source from fadedpage,
# rerun gen, and send the resulting mobi/pdf/epub
# output back to fadedpage.
# Do not use for fpgen projects, if there is a -src.txt file
# present on the server, you will get an error.
#
# Requires a fadedpage admin login.  Set your user and password
# either through the --user and --password options, or with
# the FPUSER and FPPASSWORD environment variables.
#
# Args is a list of fadedpage book ids
# Old format file is left in 20######.format.save
# New format file is left in 20######.format

import sys
import os
from optparse import OptionParser
from epub import get_epub_info
from FPSession import FPSession

def fatal(line):
  sys.stderr.write("ERROR " + line)
  exit(1)

parser = OptionParser()
parser.add_option("-u", "--user", dest="user", default=os.environ['FPUSER'] if 'FPUSER' in os.environ else None)
parser.add_option("-p", "--password", dest="password", default=os.environ['FPPASSWORD'] if 'FPPASSWORD' in os.environ else None)
parser.add_option("-s", "--sandbox", action="store_true", dest="sandbox",
  default=False)
parser.add_option("-g", "--get", action="store_true", dest="get", default=False)
parser.add_option("-z", "--put", action="store_true", dest="put", default=False)
(options, args) = parser.parse_args()

if (options.get and options.put) or (not options.get and not options.put):
  fatal("One and only one of --get or --put required.\n");

if options.password == None or options.user == None:
  fatal("Must specify an fp user or password.\n")

if len(args) < 1:
  fatal("Usage: fpsc [--user fpusername] [--password fppassword] (--get|--put) file ...\n")

with FPSession(options.user, options.password, sandbox=options.sandbox) as fps:
  for file in args:
    if options.put:
      fps.uploadSC(file)
    else:
      fps.downloadSC(file)
