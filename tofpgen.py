#!python

#
# tofpgen: Do the easy things to convert the output of F* (or guiguts)
#      into fpgen input.  Try not to do anything that will be wrong.
#      Output is simply stuck into a file called out
# -- character set to UTF-8
# -- em-dashes
# -- curly quotes
# -- /##/ -> <quote>...</quote>
# -- [#] -> <fn id='#'>
# -- [Footnote:] -> <footnote>...</footnote>
# -- [Sidenote:] -> <sidenote>...</sidenote>
# -- [Illustration:] -> <illustration>...</illustration>
# -- \n\n\n\nXXX -> <chap-head>XXX</chap-head>
#

import sys
import re
import os
import fnmatch
import chardet

def fatal(line):
  sys.stderr.write("ERROR " + line)
  exit(1)

if len(sys.argv) > 2:
  fatal("Too many args; Usage: tofpgen [xxx-src.txt]\n")
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

regexFootnote = re.compile("^\[Footnote ([ABC0-9][0-9]*): (.*)$")
regexIllStart = re.compile("^\[Illustration: *")
regexIllOne = re.compile("^\[Illustration: (.*)\]$")
regexIllNoCap = re.compile("^\[Illustration]$")
regexFNRef = re.compile("\[([ABCD0-9][0-9]*)\]")
sidenoteRE = re.compile("\[Sidenote: (.*)\]$")


postamble = """
<l rend='center mt:3em'>THE END</l>

<heading level='1'>TRANSCRIBER NOTES</heading>

Mis-spelled words and printer errors have been fixed.

Inconsistency in hyphenation has been retained.

Inconsistency in accents has been fixed.
Inconsistency in accents has been retained.

Because of copyright considerations, the illustrations by X (y-z) have been omitted from this etext.

Illustrations have been relocated due to using a non-page layout.

Some photographs have been enhanced to be more legible.

When nested quoting was encountered, nested double quotes were
changed to single quotes.

Space between paragraphs varied greatly. The thought-breaks which
have been inserted attempt to agree with the larger paragraph
spacing, but it is quite possible that this was simply the methodology
used by the typesetter, and that there should be no thought-breaks.

<nobreak>[End of TITLE, by AUTHOR]

/* end of work-src */
"""

preamble = """/* This is file-src as of 02-Sep-2017 */

<property name="cover image" content="images/cover.jpg">

<option name="pdf-default-font-size" content="16">
<option name="pstyle" content="indent">
<option name="footnote-location" content="heading-reset">

<meta name="DC.Creator" content="AUTHOR">
<meta name="DC.Title" content="TITLE">
<meta name="DC.Language" content="en">
<meta name="DC.Created" content="DATE">
<meta name="DC.date.issued" content="DATE">
<meta name="DC.Subject" content="SUBJECT">
<meta name="Tags" content="SUBJECT">
<meta name="Series" content="SERIES [15]">
<meta name="generator" content="fpgen 4.54h">

<lit section="head">
    <style type="text/css">
	.poetry-container { margin-top:.5em; margin-bottom:.5em }
	.literal-container { margin-top:.5em; margin-bottom:.5em }
	div.lgc { margin-top:.5em; margin-bottom:.5em }
	p { margin-top:0em; margin-bottom:0em; }
    </style>
</lit>

<if type='h'>
<illustration rend="w:80%" src="images/cover.jpg"/>

<pb>

</if>


"""



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

def sidenote(line):
  m = sidenoteRE.match(line)
  if m:
    return "<sidenote>" + m.group(1) + "</sidenote>"
  return line

def footnote(line):
  global inFN

  # Replace [12] footnote references
  line = regexFNRef.sub(r"<fn id='#'>/*\1*/", line)

  m = regexFootnote.match(line)
  if not m:
    if inFN:
      if line.endswith("]"):
        line = line[:-1] + "</footnote>"
        inFN = False
    return line

  if inFN and m:
    fatal("ERROR already in FN at " + line)

  fn = m.group(1)
  rest = m.group(2)
  inFN = True
  if rest.endswith("]"):
    rest = rest[:-1] + "</footnote>"
    inFN = False
  return "<footnote id='#'>/*" + fn + "*/" + rest

def illustration(line):
  global inIll, illStartLine

  if inIll and line.endswith("]"):
    inIll = False
    illStartLine = None
    return line[:-1] + "\n</caption>\n</illustration>"

  mOne = regexIllOne.match(line)
  mStart = regexIllStart.match(line)
  mNoCap = regexIllNoCap.match(line)

  if (mStart or mNoCap) and inIll:
    fatal("already in ill at " + line + ", which started at " + illStartLine)

  # One line illustration with caption
  if mOne:
    caption = mOne.group(1)
    line = "<illustration rend='w:WW%' src='images/XXX.jpg'>\n<caption>\n" + \
      caption + "\n</caption>\n</illustration>\n"
    return line

  # Illustration with caption starts, but does not end on this line
  if mStart:
    captionStart = line[15:].strip()
    inIll = True
    illStartLine = line
    return "<illustration rend='w:WW%' src='images/XXX.jpg'>\n<caption>\n" + \
      captionStart 

  # Illustration without caption
  if mNoCap:
    return "<illustration rend='w:WW%' src='images/XXX.jpg'/>"

  return line

inFN = False
inIll = False
illStartLine = None

rawdata = open(src, "rb").read()
encoding = chardet.detect(rawdata)['encoding']
if encoding[:3] == "ISO":
  encoding = "ISO-8859-1"
sys.stderr.write("Source file encoding: " + encoding + "\n")
sys.stderr.write("converting " + src + " into file out\n")

with open(src, "r", encoding=encoding) as input:
  with open("out", "w", encoding="UTF-8") as output:
    output.write(preamble)
    blanks = 0
    for line in input:
      line = line.rstrip()

      if line == "":
        blanks += 1
        output.write("\n")
        continue

      line = line.replace("--", "—")
      line = quote(line)

      if blanks >= 4:
        if line != "/*" and not regexIllOne.match(line) and not regexIllNoCap.match(line):
          line = "<chap-head pn='XXX'>" + line + "</chap-head>"
      if line == "/#":
        line = "<quote>"
      elif line == "#/":
        line = "</quote>"
      else:
        line = footnote(line)
        line = illustration(line)
        line = sidenote(line)

      blanks = 0
      output.write(line + "\n")
    output.write(postamble)

if inFN:
  sys.stderr.write("END OF FILE in a footnote\n")
  exit(1)
if inIll:
  sys.stderr.write("END OF FILE in an illustration\n")
  exit(1)
