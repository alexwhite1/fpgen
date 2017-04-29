from msgs import fatal

# class to save user options
class userOptions(object):
  def __init__(self):
    self.opt = {}

  def setGenType(self, fmt):
    self.gentype = fmt

  def getGenType(self):
    return self.gentype

  def addopt(self,k,v):
    # print("adding {}:{}".format(k, v))
    self.opt[k] = v

  def getopt(self,k,v = ""):
    if k in self.opt:
      return self.opt[k]
    else:
      return v

  def getOptEnum(self, k, map, default):
    tagValue = self.getopt(k)
    if tagValue == '':
      return default
    elif tagValue in map:
      return map[tagValue]
    else:
      fatal("Option " + k + ": Illegal value '" + tagValue +
          "'. Legal values are: " + ', '.join(k for k in map))
    return None

  def isOpt(self, k, default):
    if k in self.opt:
      if self.opt[k] == "true":
        return True
      elif self.opt[k] == "false":
        return False
      else:
        fatal("Option " + k + ": must be true or false, not " + self.opt[k])
    return default
