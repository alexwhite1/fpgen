#!python

# Get or put a file into the special collections directory.
# No relative paths are permitted; and only files ending in .php or .jpg
# are transferred.
# For --put, the files are retrieved from the current directory and sent
# to the server sc directory.
# For --get, the files are retrieved from the server's sc directory, and
# placed into the current directory locally.
#
# Requires a fadedpage admin login.  Set your user and password
# either through the --user and --password options, or with
# the FPUSER and FPPASSWORD environment variables.
#

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
