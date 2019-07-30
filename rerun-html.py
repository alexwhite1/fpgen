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

def run(cmd):
  sys.stderr.write("-->" + cmd + "\n")
  exit = os.system(cmd)
  if exit != 0:
    fatal(f"Exit code {exit} for command {cmd}\n")

# Retrieve the source file, and all images
# **note destructive to the images directory**
def fetch(id):
  fps.downloadHTML(id)
  fps.downloadImages(id)

# Retrieve the old file for backup purposes
def backup(id, format):
  suffix = formats[format]
  if not os.path.exists(id + suffix + ".save"):
    fps.downloadFormat(id, format)
    os.rename(id + suffix, id + suffix + ".save")

# Send the new mobi file back to the server
def copyToFP(id, format):
  fps.uploadFormat(id, format)


parser = OptionParser()
parser.add_option("-g", "--tags", dest="tags", default=None)
parser.add_option("-u", "--user", dest="user", default=os.environ['FPUSER'] if 'FPUSER' in os.environ else None)
parser.add_option("-p", "--password", dest="password", default=os.environ['FPPASSWORD'] if 'FPPASSWORD' in os.environ else None)
parser.add_option("-s", "--sandbox", action="store_true", dest="sandbox",
    default=False)
(options, args) = parser.parse_args()

tags = "--tags \"" + options.tags + "\"" if options.tags != None else ""

if options.password == None or options.user == None:
  fatal("Must specify an fp user or password.\n")

if len(args) < 1:
  fatal("Usage: rerun-html [--user fpusername] [--password fppassword] [--tags tags] book-id ...\n")

formats = { "mobi" : ".mobi", "epub" : ".epub", "pdf" : "-a5.pdf" }
with FPSession(options.user, options.password, sandbox=options.sandbox) as fps:
  for id in args:
    fetch(id)
    for format in formats:
      backup(id, format)
    meta = get_epub_info(f"{id}.epub.save")
    subject = meta['subject']
    argv = [ "rerun-html" ]
    if subject:
      argv += [ "--tags", subject ]
    argv += [ f"{id}.html" ]
    sys.stderr.write("Invoking gen: " + str(argv) + "\n")
    import gen
    gen.main(argv)
    for format in formats:
      copyToFP(id, format)


