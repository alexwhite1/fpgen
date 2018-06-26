#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
import sys
import os
#from scipy import misc
#import imageio
from numpy import zeros
from skimage import io

from skimage import data
from skimage import color
from skimage import measure
from skimage import util
from skimage import img_as_ubyte, img_as_float
from skimage.transform import swirl, resize, rescale
from skimage.color import rgb2gray, convert_colorspace
#from scipy import misc
import matplotlib.pyplot as plt

from PIL import ImageFont, ImageDraw

def frame(T, val):
  height = T.shape[0]
  width = T.shape[1]
  framesize = 20
  if T.ndim == 2:
    # grayscale
    T[0:framesize, 0:width] = val
    T[height-framesize:height, 0:width] = val
    T[0:height, 0:framesize] = val
    T[0:height, width-framesize:width] = val
  else:
    T[0:framesize, 0:width, :] = val
    T[height-framesize:height, 0:width, :] = val
    T[0:height, 0:framesize, :] = val
    T[0:height, width-framesize:width, :] = val

# Shrink the given image, and return it inside an image of the full size
def shrink(T, size):
  height = T.shape[0]
  width = T.shape[1]

  # Shrink by given size
  small = rescale(T, size, mode='wrap')
  h = small.shape[0]
  w = small.shape[1]
  #full = resize(small, (height, width), cval=0, mode='constant')
  small = img_as_ubyte(small)
  print(str(small))
  print(str(T))

  # create a new image, center resized image in it
  if T.ndim == 2:
    full = zeros((height, width))
  else:
    full = zeros((height, width, 3))
  full = (full + 1) * 150 # make white, didn't work
  top = int((height - h)/2)
  left = int((width - w)/2)
  full[top:top+h, left:left+w] = small

  return full

def blank(T, n, v1, v2):
  T = T.copy()
  height = T.shape[0]
  width = T.shape[1]
  stripe = int(width / n)
  for i in range(n):
    #if int(i%2) == 1:
    if i > 0 and i < n-1:
      #T[0:height, stripe * i:stripe * (i+1)] = (v1 if int(i%2)==1 else v2)
      T[0:height, stripe * i:stripe * (i+1)] = v1
  return T

def twist(T):
  T = T.copy()
  T = img_as_float(T)
  height = T.shape[0]
  width = T.shape[1]
  full = swirl(T, center=(height/2, width/2),
      rotation=0, strength=10, radius=max(height,width),
      mode='wrap')
  return img_as_ubyte(full)

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

  # Load the file, convert to greyscale
  T = io.imread(file)
  if True:
    T = rgb2gray(T)
    T = img_as_ubyte(T)
  print(str(T.shape))
  height = T.shape[0]
  width = T.shape[1]

  if options.mode == 'shrink':
    # Used .15 for Leacock’s Canada
    full = shrink(T, .15)
  elif options.mode == 'swirl':
    full = twist(T)
  else:
    full = blank(T, 5, 200, 0)

  #print(str(T))
  #print(str(small))
  #print(str(full))

  if T.ndim == 2:
    frame(full, 255)
  else:
    frame(full, [1, 255, 1])

  file = basename + "-omit.jpg"
  if T.ndim == 2:
    plt.imsave(file, full, cmap='gray', format="jpg")
  else:
    plt.imsave(file, full, format="jpg")


usage = """
usage: omitimage [options] image-file

Example usage would be

    omitimage images/p123.jpg

--mode=swirl: Image is greyscaled and swirled
--mode=shrink: Image is greyscaled, and shrunk to 1/10th size within original
--mode=blank: Blank center of image

"""
parser = OptionParser(conflict_handler="resolve", usage=usage)
parser.add_option("--mode", dest="mode", default="swirl",
  help="mode is shrink, swirl, or line")

(options, args) = parser.parse_args()
for file in args:
  omit(file)
