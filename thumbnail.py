#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
import sys
import os

from PIL import ImageFont, ImageDraw, Image, ImageOps

def omit(file):

  print(file + ":")
  if file[-4:] != ".jpg":
    sys.stderr.write(file + ": File must end in .jpg\n")
    exit(1)
  basename = file[0:-4]
  print( basename[-5:])
  if basename[-5:] == '-omit':
    basename = basename[0:-5]
  print("Basename: " + basename)
  file = basename + ".jpg"
  newfile = basename + "-omit.jpg"

  white = 255
  black = 0

  # Parameters
  scale = .15
  framesize = 50
  fontmax = 50
  leading = 20
  bordercolour = white    ## Colour of frame
  fill = 128              ## Colour outside thumbnail
  textcolour = white      ## Colour of text
  msg = "Image thumbnail\nNot yet in the public domain"

  # - Load the file
  # - convert to Greyscale
  # - reduce size to thumbnail by scale factor
  # - Set the size of the image back to the original, i.e. thumbnail in
  #   a large black box
  # - Put a frame around the image
  T = Image.open(file)
  print(str(T.size))
  w = T.size[0]
  h = T.size[1]

  T = ImageOps.grayscale(T)

  T = T.resize((int(w * scale), int(h * scale)))

  w1 = T.size[0]
  h1 = T.size[1]
  left = (w - w1) // 2 - framesize
  top = (h - h1) // 2 - framesize

  X = Image.new("L", (w-framesize*2, h-framesize*2), color=fill)
  X.paste(T, (left, top))
  T = X

  T = ImageOps.expand(T, border=framesize, fill=bordercolour)
  print(str(T.size))

  draw = ImageDraw.Draw(T)
  size = top//3
  if size > fontmax:
    size = fontmax
  font = ImageFont.truetype("arial.ttf", size)
  size = draw.textsize(msg, font=font)
  print(str(size))
  left = (w - size[0]) / 2
  top = h - framesize - size[1] - leading
  draw.multiline_text((left, top), msg, font=font, align="center",
      fill=textcolour)

  T.save(newfile, "JPEG")


usage = """
This tool takes an image file, and creates a new image file, with
the basename ending in -omit.
The new file is a thumbnail of the original, inside a frame, so the
resulting image is the same size as the original.
A message indicating this is included in the frame.

usage: thumbnail [options] image-file [...]

Example usage would be

    omitimage images/p123.jpg

"""
parser = OptionParser(conflict_handler="resolve", usage=usage)
#parser.add_option("--mode", dest="mode", default="swirl",
#  help="mode is shrink, swirl, or line")

(options, args) = parser.parse_args()
for file in args:
  omit(file)
