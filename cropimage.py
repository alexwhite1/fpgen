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
from skimage import exposure
from skimage import restoration
from scipy import misc
import numpy as np
import matplotlib.pyplot as plt

def toGrey(image):
  if image.ndim == 2:
    return image
  R = image[:,:,0]
  G = image[:,:,1]
  B = image[:,:,2]
  return R * 299. / 1000 + G * 587. / 1000 + B * 114. / 1000

def crop(file):

  if file[-4:] != ".jpg":
    sys.stderr.write(file + ": File must end in .jpg\n")
    exit(1)
  (dirname, filename) = os.path.split(file)
  if not os.path.isdir(dirname + "-new"):
    os.mkdir(dirname + "-new")
  target = dirname + "-new" + "/" + filename
  print(file + " -> " + target)

  # Load the file, convert to greyscale, and find the contours
  T = misc.imread(file)

  # Tweak the contrast, up the gamma
  v_min, v_max = np.percentile(T, (.2, 90.0))
  contrasted = exposure.rescale_intensity(T, in_range=(v_min, v_max))
  adjusted = exposure.adjust_gamma(contrasted, 2)
  #adjusted = restoration.denoise_tv_chambolle(adjusted)
  #adjusted = restoration.denoise_bilateral(adjusted)
  #adjusted = restoration.denoise_tv_bregman(adjusted, .5)
  #adjusted = restoration.denoise_nl_means(adjusted, .5)
  #adjusted = restoration.denoise_wavelet(adjusted)
  print("({}, {}): ({},{}), ({},{}), ({},{})".format(v_min, v_max,
    T.min(), T.max(), contrasted.min(),
    contrasted.max(), adjusted.min(), adjusted.max()))

  grey_adjusted = color.colorconv.rgb2grey(adjusted)
  #grey_adjusted = toGrey(adjusted)
  grey_orig = color.colorconv.rgb2grey(T)

  # Note find_contours operates on a grayscale image
  # A larger number retains more of the light greys
  # Seems to be better working against the original image
  contours = measure.find_contours(grey_orig, .9)

  if options.gui:
    f, (full, contrast, gamma, grey, withcontours, equalized, new) = plt.subplots(nrows=1, ncols=7)
    full.imshow(T)
    full.set_title("Original")
    contrast.imshow(contrasted)
    contrast.set_title("Contrast")
    gamma.imshow(adjusted)
    gamma.set_title("Contrast+Gamma")
    equalized.imshow(grey_adjusted, cmap=plt.cm.Greys_r)
    equalized.set_title("C+G in Grey")
    grey.imshow(grey_adjusted, cmap='gray')
    grey.set_title("C+G cmap Grey")
    withcontours.imshow(grey_orig)
    withcontours.set_title("OrigGreyCont")
    for contour in contours:
      withcontours.plot(contour[:, 1], contour[:, 0], linewidth=2)

  # Find the min & max from the contours
  maxx = 0
  maxy = 0
  minx = 9999
  miny = 9999
  slop = 2
  for contour in contours:
    for a in contour:
      x = int(a[1])
      y = int(a[0])
      if x > maxx:
        maxx = x
      if y > maxy:
        maxy = y
      if x < minx:
        minx = x
      if y < miny:
        miny = y

  # Clip the image to the min/max contours
  if len(contours) == 0 or minx == maxx or miny == maxy:
    cropped = grey_adjusted
    print("****No contours, or clips to zero, not clipping")
  else:
    if miny > slop:
      miny -= slop
    else:
      miny = 0
    if minx > slop:
      minx -= slop
    else:
      minx = 0
    if maxy+slop < T.shape[0]:
      maxy += slop
    else:
      maxy = T.shape[0]
    if maxx+slop < T.shape[1]:
      maxx += slop
    else:
      maxx = T.shape[1]
    cropped = grey_adjusted[miny:maxy, minx:maxx]

  print("minx={}, maxx={}, miny={}, maxy={}".format(minx, maxx, miny, maxy) + \
    ", Original (w={}, h={})".format(T.shape[1], T.shape[0]) + \
    ", Cropped  (w={}, h={})".format(cropped.shape[1], cropped.shape[0]))
  print("Shorter by {}, narrower by {}".format(T.shape[1] - cropped.shape[1],
    T.shape[0] - cropped.shape[0]))

  if options.gui:
    new.imshow(cropped)
    new.set_title("C+G Cropped")
    plt.show()

  plt.imsave(target, cropped, format="jpg", cmap=plt.cm.Greys_r)



parser = OptionParser(conflict_handler="resolve")
parser.add_option("-g", "--gui", dest="gui", default=False, action="store_true")

(options, args) = parser.parse_args()
for file in args:
  crop(file)
