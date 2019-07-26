#!python

# Fetch one or more book's html source from fadedpage,
# rerun gen, and send the resulting mobi/pdf/epub
# output back to fadedpage.
#
# scp should be setup to work without a password
#
# Args is a list of fadedpage book ids
# Old .mobi file is left in 20######.save.mobi
# New .mobi file is left in 20######.mobi

import sys
import os

def fatal(line):
  sys.stderr.write("ERROR " + line)
  exit(1)

def run(cmd):
  sys.stderr.write("-->" + cmd + "\n")
  exit = os.system(cmd)
  if exit != 0:
    fatal(f"Exit code {exit} for command {cmd}")

# Retrieve the source file, and all images
def fetch(id):
  run("rm -rf images")
  run(f"scp fadedpage@ssh.fadedpage.com:books/{id}/{id}.html {id}.html")
  run(f"scp -r fadedpage@ssh.fadedpage.com:books/{id}/images images")

# Retrieve the old file for backup purposes
def backup(id, format):
  if not os.path.exists(id + format + ".save"):
    run(f"scp fadedpage@ssh.fadedpage.com:books/{id}/{id}{format} {id}{format}.save")

# Send the new mobi file back to the server
def copyToFP(id, format):
  run(f"scp {id}{format} fadedpage@ssh.fadedpage.com:books/{id}/{id}{format}")


if len(sys.argv) < 2:
  fatal("Usage: rerun-html book-id ...")

formats = [ ".mobi", ".epub", "-a5.pdf" ]
for id in sys.argv[1:]:
  fetch(id)
  for format in formats:
    backup(id, format)
  run(f"gen {id}.html")
  for format in formats:
    copyToFP(id, format)
