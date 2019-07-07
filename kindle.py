#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fpgen import HTML

class NonHTML(HTML): #{
  def __init__(self, ifile, ofile, d, letter):
    HTML.__init__(self, ifile, ofile, d, letter)

  # No page numbers on any non-html
  def getPageNumberCSS(self):
    return [
      "[105] .pageno { display:none; }"
    ]

  # No page numbers shown, but still need to have the link target
  def showPageNumber(self, pn, displayPN):
    return f"<a name='Page_{pn}' id='Page_{pn}'></a>"

  # No margins on any non-html
  def getMargins(self):
    return "0", "0"

class Kindle(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'k')

  # On Kindle, leaders, at least the way we do them, don't work, so
  # never do them.
  def getLeaderName(self, col):
    return None

  # kindle&epub ragged right
  def getTextAlignment(self):
    return "left"

  # Kindle doesn't appear to pay attention to the text-align on the <td>
  # So we stick in an extra <div>, with the text-align on that.
  def tripleAlign(self, style, id, left, center, right):
    return """
      <div class='center' {} {}>
        <table border="0" cellpadding="4" cellspacing="0" summary="triple" width="100%">
        <tr>
          <td><div style='text-align:left;'>{}</div></td>
          <td><div style='text-align:center;'>{}</div></td>
          <td><div style='text-align:right;'>{}</div></td>
        </tr>
        </table>
      </div>
    """.format(style, id, left, center, right)

  # Floating dropcaps aren't particularly well aligned on kindles, so don't
  # do anything special with them.
  def getDropcapCSS(self):
    return "[3333] .dropcap { }"
#}

class EPub(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'e')

  # epub ragged right
  def getTextAlignment(self):
    return "left"
#}

class PDF(NonHTML): #{
  def __init__(self, ifile, ofile, d):
    NonHTML.__init__(self, ifile, ofile, d, 'p')
#}
