#!python

#
# curlyq: convert a file with straight quotes to have curly quotes.
#   Output is simply stuck into a file called curly.
# * character set converted to UTF-8
# * double dashes converted to em-dashes
# * straight quotes and apostrophes converted to their curly equivalents
# * two adjacent quotes or apostrophes will have <nnbsp> inserted between
#   them.
#
# Note many restrictions:
# * Some cases will not convert, and the line must be done manually
#   A message will generate CHECK QUOTE: line text
# * Leading contractions will have an open curly apostrophe(‘). It is suggested
#   that you manually search for all open curly apostrophes, and
#   convert them to closes (’). This is a pain for texts which are using
#   single-quotes for dialog; but isn't bad for normal texts using
#   double-quotes.  Well, unless there is a lot of dialect, but in that case
#   there there tend to be lots of leading contractions. Some common
#   leading contractions, e.g. ’Twas are handled as special cases.
# * There are a few error cases where it will silently generate
#   the wrong thing, e.g. if I recall correctly <i>' gets
#   converted into <i>’.


import sys
import re
import os
import fnmatch
import chardet

def fatal(line):
  sys.stderr.write("ERROR " + line)
  exit(1)

if len(sys.argv) > 2:
  fatal("Too many args; Usage: curlyq [xxx-src.txt]\n")
if len(sys.argv) < 2:
  src = None
  for file in os.listdir('.'):
    if fnmatch.fnmatch(file, '*-src.txt'):
      if src != None:
        fatal("Multiple *-src.txt files in current directory\n")
      src = file
  if src == None:
    fatal("No *-src.txt file found in current directory\n")
else:
  src = sys.argv[1]


def quote(line):
  if line == "<pn='+1'>":
    return line;

  # Leading or trailing double or single quotes on the line
  if line[0] == '"':
    line = '“' + line[1:]
  if line[-1] == '"':
    line = line[0:-1] + '”'
  if line[0] == "'":
    line = '‘' + line[1:]
  if line[-1] == "'":
    line = line[0:-1] + '’'

  # space quote starts sentence, opening quote
  line = re.sub('" ', '” ', line)

  # space quote, starts sentence
  # em-dash quote, starts sentence?
  # open paren, quote starts sent
  line = re.sub('([ —(])"', r'\1“', line)

  # Punctuation or lower-case letter, followed by quote, ends a sentence
  line = re.sub(r'([\.,!?a-z])"', r'\1”', line)

  # quote, open-square is probably a footnote ref at the end of a quote
  line = re.sub(r'"\[', '”[', line)

  # quote, close-square is the end of a quote
  line = re.sub(r'"]', '”]', line)

  # single between two letters is a contraction
  line = re.sub(r"(\w)'(\w)", r"\1’\2", line)

  # Match the direction if single/double
  line = re.sub(r"“'", r"“‘", line)
  line = re.sub(r"'”", r"’”", line)

  # End of sentence for single
  line = re.sub(r"' ", r"’ ", line)

  # Start single after dash
  line = re.sub("([ —])'", r"\1‘", line)

  # End single after letters
  line = re.sub(r"([\.,!?a-z])'", r"\1’", line)

  # Common, non-ambiguous contractions
  for word in [ "em", "Twas", "twas", "Tis", "tis", "Twould", "twould", "Twill", "twill" ]:
    line = re.sub(r'([ “]|^)‘' + word + r'([ !,\.?—:]|$)', r'\1’' + word + r'\2', line)

  # Insert narrow non-breaking space between adjacent quotes
  line = re.sub(r'([\'"‘’“”])([\'"‘’“”])', r'\1<nnbsp>\2', line)

  if "'" in line or '"' in line:
    sys.stderr.write("CHECK QUOTE: " + line + '\n')

  return line



inFN = False
inIll = False
illStartLine = None

rawdata = open(src, "rb").read()
encoding = chardet.detect(rawdata)['encoding']
if encoding[:3] == "ISO":
  encoding = "ISO-8859-1"
sys.stderr.write("Source file encoding: " + encoding + "\n")
sys.stderr.write("converting " + src + " into file curly\n")

with open(src, "r", encoding=encoding) as input:
  with open("curly", "w", encoding="UTF-8") as output:
    for line in input:
      line = line.rstrip()

      if line == "":
        output.write("\n")
        continue

      line = line.replace("--", "—")
      line = quote(line)

      output.write(line + "\n")

  exit(1)
