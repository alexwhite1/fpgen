#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from optparse import OptionParser
import sys
import os
from msgs import cprint, uprint, dprint, fatal
from scipy import misc

from skimage import data
from skimage import color
from skimage import measure
from skimage import util
from scipy import misc

def contour(file):

  maxslices = int(options.maxslices)
  rightPixels = int(options.rightPixels)
  mergeDistancePixels = int(options.mergeDistancePixels)
  minHeightPixels = int(options.minHeightPixels)
  print("maxslices={}, rightPixels={}, mergeDistancePixels={}, minHeightPixels={}".format(maxslices, rightPixels, mergeDistancePixels, minHeightPixels))

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

  import matplotlib.pyplot as plt

  slices = []
  ry = 0
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
    print(str(ry) + "..." + str(ryEnd) + ": " + str(maxx))
    #left.vlines(maxx + 5, ry, ry+height, linestyles='dotted', color='r')
    width = int(maxx) + rightPixels

    distance = 0
    slices.append([ry, ryEnd, width])

    ry = ryEnd
    if ryEnd == imageHeight:
      break
  print("Slices: " + str(slices))

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
      if distance < mergeDistancePixels or w[1]-w[0] < minHeightPixels:
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
      cprint("Again")

  nslices = len(slices)
  print(str(nslices) + " Merged Slices: " + str(slices))

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
    plt.imsave(basename + "," + str(sliceNumber).zfill(2) + \
        ",w=" + str(width) + ".jpg", \
        slice, format="jpg")

    left = plt.subplot2grid((nslices, 2), (sliceNumber, 0))
    left.imshow(slice)

    sliceNumber += 1

  right = plt.subplot2grid((nslices, 2), (0, 1), rowspan=nslices)

  # All the x values, and all the y values
#  for contour in contours:
#    left.plot(contour[:, 1], contour[:, 0], linewidth=2)
#  cropped = T[0:200,100:300]
#  left.imshow(cropped)
  right.imshow(gT)
  plt.show()

  #plt.imsave("out", [])

parser = OptionParser(conflict_handler="resolve")
parser.add_option("-s", "--maxslices", dest="maxslices", default=30)
parser.add_option("-r", "--right", dest="rightPixels", default=5)
parser.add_option("-d", "--mergedistance", dest="mergeDistancePixels", default=50)
parser.add_option("-h", "--minheight", dest="minHeightPixels", default=100)

(options, args) = parser.parse_args()
for file in args:
  contour(file)
