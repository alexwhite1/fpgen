#
# Contains the FPSession class, which maintains an authenticated
# session with the fadedpage server.
# Need to install the requests package.
#

import requests
import json
from os import mkdir, path, rmdir, listdir, remove
import os

class FPSession(object): #{

  def __init__(self, user, password, sandbox=False):
    self.site = "https://www.sandbox.fadedpage.com/" if sandbox else \
                "https://www.fadedpage.com/"
    print("Operating against " + self.site)
    self.session = requests.Session()
    content = self.request("login2.php", data = {
      'myusername' : user,
      'mypassword' : password
    })
    # Result is english html saying whether we logged in or not
    if 'wrong' in str(content):
      raise Exception(content.decode('utf-8'))

  def __enter__(self):
    return self

  def __exit__(self, type, value, t):
    self.request("logout.php", {})
    self.session.close()

  def request(self, page, data):
    r = self.session.post(self.site + page, data,
        headers = { 'user-agent' : 'Mozilla/5.0' })
    r.raise_for_status()
    return r.content

  def requestStream(self, page, data):
    # Note that setting the agent is supposed to make apache not think
    # we are a bot, but it isn't working, the sleep(.5) below seems to work.
    r = self.session.post(self.site + page, data, stream=True,
        headers = { 'user-agent' : 'Mozilla/5.0' })
    r.raise_for_status()
    #print(str(r))
    #print(str(r.cookies))
    #print(str(r.headers))
    #print(str(r.content))
    return r

  def writeFileJSON(self, filename, bytes):
    f = open(filename, 'wb')
    f.write(bytearray(bytes))
    f.close()

  def writeFile(self, filename, response):
    print("Downloading: " + filename)
    with open(filename, 'wb') as f:
      for chunk in response.iter_content(chunk_size=8192):
        if chunk:
          f.write(chunk)
    
    # Next download fails with a 403 if we don't sleep
    # Apache thinks we are a bot
    import time
    time.sleep(1)

  def downloadSC(self, file):
    with self.requestStream("admin/file_rmi.php", {
      'operation' : 'fetch-sc',
      'file' : file
    }) as response:
      self.writeFile(file, response)

  def downloadHTML(self, bookid):
    with self.requestStream("admin/file_rmi.php", {
      'operation' : 'fetch-html',
      'bookid' : bookid
    }) as response:
      self.writeFile(bookid + ".html", response)

  formats = {
    'mobi' : '.mobi',
    'pdf' : '-a5.pdf',
    'epub' : '.epub',
  }

  def downloadFormat(self, bookid, format):
    with self.requestStream("admin/file_rmi.php", {
      'operation' : 'fetch-format',
      'bookid' : bookid,
      'format' : format
    }) as response:
      self.writeFile(bookid + self.formats[format], response)

    #results = json.loads(content)
    #print(results['msg'] + "\n")
    #for f, v in results.items():
    #  if bookid in f:
    #    self.writeFile(f, v)

  # Download all image files. Deletes any current images directory
  # and rebuilds it!
  def downloadImages(self, bookid):
    content = self.request("admin/file_rmi.php", {
      'operation' : 'fetch-images',
      'bookid' : bookid
    })
    results = json.loads(content)
    dir = results['dir']
    if path.isdir('images'):
      for f in listdir('images'):
        remove("images/" + f)
      rmdir('images')
    mkdir('images')
    print("Image download:")
    for f in dir:
      print("\t" + f + ": " + str(len(dir[f])))
      self.writeFileJSON("images/" + f, dir[f])

  def uploadFormat(self, bookid, format):
    file = bookid + self.formats[format]
    print("Uploading: " + file)
    with open(file, 'rb') as f:
      r = self.session.post(self.site +
          "admin/file_rmi.php?operation=upload-format&bookid=" +
          bookid + "&format=" + format, f)
      r.raise_for_status()

  def uploadOne(self, bookid, file):
    print("Uploading: " + file)
    with open(file, 'rb') as f:
      r = self.session.post(self.site +
          "admin/file_rmi.php?operation=upload-file&bookid=" +
          bookid + "&file=" + file, f)
      r.raise_for_status()

  def uploadSC(self, file):
    print("Uploading to special collections: " + file)
    with open(file, 'rb') as f:
      r = self.session.post(self.site +
          "admin/file_rmi.php?operation=upload-sc&file=" + file, f)
      r.raise_for_status()

#}

if False:
  from http.client import HTTPConnection
  HTTPConnection.debuglevel = 1
  import logging
  logging.basicConfig()
  logging.getLogger().setLevel(logging.DEBUG)
  requests_log = logging.getLogger('urllib3')
  requests_log.setLevel(logging.DEBUG)
  requests_log.propagate = True

# Test code
if False:
  with FPSession(os.environ['FPUSER'], os.environ['FPPASSWORD']) as fps:
    bookid = '20190750'
    if False:
      fps.downloadHTML(bookid)
      fps.downloadImages(bookid)
      print("Mobi...")
      fps.downloadFormat(bookid, 'mobi')
      print("Epub...")
      fps.downloadFormat(bookid, 'epub')
      print("PDF...")
      fps.downloadFormat(bookid, 'pdf')
      fps.uploadFormat(bookid, 'pdf')
