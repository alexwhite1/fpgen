#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
import sys
import os
from scipy import misc

from skimage import data
from skimage import color
from skimage import measure
from skimage import util
from scipy import misc
import matplotlib.pyplot as plt

def manualMerge(slices):
  print("Manual Merge: " + options.merge)
  directives = options.merge.split(",")
  newSlices = []
  for oneDirective in directives:
    l = oneDirective.split("-")
    if len(l) == 1:
      # Single slice
      n = int(oneDirective)
      print("Slice {} from {}: {}".format(len(newSlices), n, slices[n]))
      newSlices.append(slices[n])
    elif len(l) == 2:
      # Range of slices
      start = int(l[0])
      end = int(l[1])
      newSlice = [ slices[start][0], slices[end][1], slices[start][2] ]
      for i in range(start, end+1):
        slice = slices[i]
        newSlice[2] = max(newSlice[2], slice[2])
      print("Slice {} from {} through {}: {}".format(len(newSlices), start, end, newSlice))
      newSlices.append(newSlice)
    else:
      print("Incorrect merge range: " + oneDirective)
  return newSlices

def merge(slices):
  mergeDistancePixels = int(options.mergeDistancePixels)
  minHeightPixels = int(options.minHeightPixels)
  mod = True
  while mod:
    i = 0
    mod = False
    while True:
      if i+1 == len(slices):
        break
      w = slices[i]
      w1 = slices[i+1]
      distance = abs(w[2] - w1[2])
      if distance < mergeDistancePixels \
      or w[1]-w[0] < minHeightPixels:
        print("Merge: " + str(w) + "::" + str(w1) + \
            " (distance=" + str(distance) + \
            ", height=" + str(w[1]-w[0]) + ")")
        w[1] = w1[1]
        w[2] = max(w[2], w1[2])
        del slices[i+1]
        mod = True
      else:
        print("NO Merge: " + str(w) + "::" + str(w1))
        i += 1
    if mod:
      print("Again")
  print(str(len(slices)) + " Merged Slices: " + str(slices))
  return slices

def contour(file):

  maxslices = int(options.maxslices)
  rightPixels = int(options.rightPixels)
  print("maxslices={}, rightPixels={}, mergeDistancePixels={}, minHeightPixels={}".format(maxslices, rightPixels, options.mergeDistancePixels, options.minHeightPixels))

  print(file + ":")
  if file[-4:] != ".jpg":
    sys.stderr.write(file + ": File must end in .jpg\n")
    exit(1)
  basename = file[0:-4]
  print("Basename: " + basename)

  # Load the file, convert to greyscale, and find the contours
  T = misc.imread(file)
  gT = color.colorconv.rgb2grey(T)
  contours = measure.find_contours(gT, .8)

  imageHeight = gT.shape[0]
  print("Image height: " + str(imageHeight))
  sliceHeight = int(gT.shape[0] / maxslices)
  print(str(maxslices) + " slices each with height: " + str(sliceHeight))

  slices = []
  ry = 0
  i = 0
  while True:
    ryEnd = ry + sliceHeight
    if ryEnd + maxslices > imageHeight:
      ryEnd = imageHeight
    maxx = 0
    for contour in contours:
      for a in contour:
        x = a[1]
        y = a[0]
        if y >= ry and y < ryEnd:
          if x > maxx:
            maxx = x
    print("Slice {}: Start Y: {}, End Y: {}, Width: {}".format(i, ry, ryEnd, maxx))
    #left.vlines(maxx + 5, ry, ry+height, linestyles='dotted', color='r')
    width = int(maxx) + rightPixels

    distance = 0
    slices.append([ry, ryEnd, width])

    ry = ryEnd
    if ryEnd == imageHeight:
      break
    i += 1

  if options.merge:
    slices = manualMerge(slices)
  elif not options.manual:
    slices = merge(slices)

  nslices = len(slices)

  # Delete any old files we created from a previous run
  import glob
  root, ext = os.path.splitext(file)
  pattern = root + ",[0-9][0-9],w=*" + ext
  for file in glob.glob(pattern):
    print("Deleting old slice: " + file)
    os.remove(file)

  if nslices == 1:
    print("Not slicing, only one.")
    return

  sliceNumber = 0
  for slice in slices:
    ry = slice[0]
    ryEnd = slice[1]
    width = slice[2]
    slice = T[ry:ryEnd, 0:width]

    # Assume no more than 99 slices, fill with leading zero, so fpgen can
    # sort without alpha.  ,w=size allows figuring out width percent
    file = basename + "," + str(sliceNumber).zfill(2) + \
        ",w=" + str(width) + ".jpg"
    print("Writing new slice: " + file)
    plt.imsave(file, slice, format="jpg")

    if options.gui:
      left = plt.subplot2grid((nslices, 2), (sliceNumber, 0))
      plt.ylabel("Slice " + str(sliceNumber))
      left.imshow(slice)

    sliceNumber += 1


  if options.gui:
    right = plt.subplot2grid((nslices, 2), (0, 1), rowspan=nslices)
    right.imshow(gT)
    plt.title("Original")
    plt.suptitle("Slices")
    plt.show()

usage = """
usage: sliceimage [options] image-file

Example usage would be

    sliceimage -g --maxslices 10 --manual images/p123.jpg

decide which of the 10 slices you want to merge; then rerun
telling the tool the slice ranges you want to merge, each
becomes a slice file:

    sliceimage -g --maxslices 10 --merge 1-6,7-9 images/p123.jpg
"""
parser = OptionParser(conflict_handler="resolve", usage=usage)
parser.add_option("-g", "--gui", dest="gui", default=False,
  action="store_true", help="Show results in a GUI")
parser.add_option("-m", "--manual", dest="manual", default=False,
  action="store_true",
  help="Don't merge; bring up the GUI; run --merge later")
parser.add_option("--merge", dest="merge",
  help="Slices to merge: #-#,#,#-#...")
parser.add_option("-s", "--maxslices", dest="maxslices", default=30,
  help="Start by slicing image vertically into this number of images")
parser.add_option("-r", "--right", dest="rightPixels", default=5,
  help="Number of pixels to add to right of contour")
parser.add_option("-d", "--mergedistance", dest="mergeDistancePixels",
  default=50,
  help="Two slices within this number of pixels of width are merged")
parser.add_option("-h", "--minheight", dest="minHeightPixels", default=100,
  help="Slice must be at least this height or it will merge anyway")

(options, args) = parser.parse_args()
for file in args:
  contour(file)
