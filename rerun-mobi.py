#!python

# Fetch one or more book's fpgen source from fadedpage,
# rerun fpgen, and send the resulting mobi
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

def repair(id):
  # Retrieve the .mobi file for backup purposes
  if not os.path.exists(id + ".save.mobi"):
    os.system("scp fadedpage@ssh.fadedpage.com:books/{0}/{0}.mobi {0}.save.mobi".format(id))

  # Retrieve the source file, and all images
  os.system("rm -rf images")
  os.system("scp fadedpage@ssh.fadedpage.com:books/{0}/{0}-src.txt {0}-src.txt".format(id))
  os.system(f"scp -r fadedpage@ssh.fadedpage.com:books/{id}/images images")

  # Rerun fpgen just for mobi output
  exit = os.system(f"fpgen -f k {id}-src.txt")
  if exit != 0:
    fatal(f"{0}: fpgen failed with exit code {exit}")

  # Send the new mobi file back to the server
  os.system("scp {0}.mobi fadedpage@ssh.fadedpage.com:books/{0}/{0}.mobi".format(id))


if len(sys.argv) < 2:
  fatal("Usage: rerun-mobi book-id ...")

for src in sys.argv[1:]:
  repair(src)
