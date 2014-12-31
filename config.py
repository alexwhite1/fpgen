from fpgen import userOptions

from time import gmtime, strftime

uopt = userOptions()
VERSION="4.23d"
NOW = strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " GMT"
LINE_WIDTH = 72
debug = 0
FORMATTED_PREFIX = "▹"
pn_cover = ""
