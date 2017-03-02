import unittest
from fpgen import ColDescr, Text, Book, \
  TableCell, parseTableRows, parseTablePattern
import config

class TestParseTableColumn(unittest.TestCase):
  expect = ColDescr('r')
  expect.isLast = True;

  def test_empty(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("pattern=''", False)
    self.assertEqual(cm.exception.code, 1)

  def test_nopattern(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("atern='r c l'", False)
    self.assertEqual(cm.exception.code, 1)

  def test_simple(self):
    assert parseTablePattern("pattern='r'", False) == [ TestParseTableColumn.expect ]

  def test_simple1(self):
    assert parseTablePattern("pattern='   r   '", False) == [ TestParseTableColumn.expect ]

  def test_simple2(self):
    with self.assertRaises(SystemExit) as cm:
      parseTablePattern("pattern='   rx   '", False)
    self.assertEqual(cm.exception.code, 1)

  def test_valignB(self):
    c = ColDescr("lB")
    self.assertEqual(c.align, "left")
    self.assertEqual(c.valign, "bottom")

  def test_valignT(self):
    c = ColDescr("cT")
    self.assertEqual(c.align, "center")
    self.assertEqual(c.valign, "top")

  def test_valignC(self):
    c = ColDescr("rC")
    self.assertEqual(c.align, "right")
    self.assertEqual(c.valign, "middle")
    self.assertEqual(c.preserveSpaces, False)

  def test_colS(self):
    c = ColDescr("rS")
    self.assertEqual(c.align, "right")
    self.assertEqual(c.preserveSpaces, True)

  def test_colh(self):
    c = ColDescr("h")
    self.assertEqual(c.align, "left")
    self.assertEqual(c.hang, True)

  def test_colL(self):
    uprop = Book.userProperties()
    c = ColDescr("lL", uprop=uprop)
    self.assertEqual(c.align, "left")
    self.assertEqual(c.leaderName, "leader-dots")
    self.assertEqual(c.leaderChars, ".")

  def test_colLfollowed(self):
    uprop = Book.userProperties()
    c = ColDescr("lL33", uprop=uprop)
    self.assertEqual(c.align, "left")
    self.assertEqual(c.leaderName, "leader-dots")
    self.assertEqual(c.leaderChars, ".")
    self.assertEqual(c.userWidth, True)
    self.assertEqual(c.width, 33)

  def test_colL1(self):
    with self.assertRaises(SystemExit) as cm:
      uprop = Book.userProperties()
      c = ColDescr("lL(dash)", uprop=uprop)
    # Should be property leader-dash doesn't exist
    self.assertEqual(cm.exception.code, 1)

  def test_colL2(self):
    with self.assertRaises(SystemExit) as cm:
      c = ColDescr("lL(dash")
    # Syntax error
    self.assertEqual(cm.exception.code, 1)

  def test_colL3(self):
    uprop = Book.userProperties()
    uprop.addprop("leader-dash", "x-y-z")
    c = ColDescr("lL(dash)", uprop=uprop)
    self.assertEqual(c.align, "left")
    self.assertEqual(c.leaderName, "leader-dash")
    self.assertEqual(c.leaderChars, "x-y-z")
    self.assertEqual(c.userWidth, False)

  def test_colL3followed(self):
    uprop = Book.userProperties()
    uprop.addprop("leader-dash", "x-y-z")
    c = ColDescr("lL(dash)99", uprop=uprop)
    self.assertEqual(c.align, "left")
    self.assertEqual(c.leaderName, "leader-dash")
    self.assertEqual(c.leaderChars, "x-y-z")
    self.assertEqual(c.userWidth, True)
    self.assertEqual(c.width, 99)

  def test_simple3(self):
    result = parseTablePattern("pattern='   r   l33 c5 '", False)
    assert len(result) == 3
    assert result[0].align == "right"
    assert result[1].align == "left"
    assert result[2].align == "center"
    assert result[0].width == 0
    assert result[1].width == 33
    assert result[2].width == 5
    assert result[0].userWidth == False
    assert result[1].userWidth == True
    assert result[2].userWidth == True
    assert result[0].isLast == False
    assert result[1].isLast == False
    assert result[2].isLast == True

  def test_bar1(self):
    with self.assertRaises(SystemExit) as cm:
      result = parseTablePattern("pattern='|'", False)
    self.assertEqual(cm.exception.code, 1)

  def test_bar2(self):
    result = parseTablePattern("pattern='|r| c55||| |||l ||r99||'", False)
    assert len(result) == 4
    assert result[0].lineBefore == 1
    assert result[0].lineAfter == 1
    assert result[0].lineBeforeStyle == '|'
    assert result[0].lineAfterStyle == '|'
    assert result[1].lineBefore == 0
    assert result[1].lineAfter == 3
    assert result[1].lineBeforeStyle == '|'
    assert result[1].lineAfterStyle == '|'
    assert result[2].lineBefore == 3
    assert result[2].lineAfter == 0
    assert result[2].lineBeforeStyle == '|'
    assert result[2].lineAfterStyle == '|'
    assert result[3].lineBefore == 2
    assert result[3].lineAfter == 2
    assert result[3].lineBeforeStyle == '|'
    assert result[3].lineAfterStyle == '|'

  def test_bar3(self):
    with self.assertRaises(SystemExit) as cm:
      result = parseTablePattern("pattern='|r|c'", False)
    self.assertEqual(cm.exception.code, 1)

  def test_hash(self):
    result = parseTablePattern("pattern='r# #l'", False)
    assert len(result) == 2
    assert result[0].lineAfter == 4
    assert result[0].lineAfterStyle == '#'
    assert result[1].lineBefore == 4
    assert result[1].lineBeforeStyle == '#'

class TestTableCellFormat(unittest.TestCase):

  colDesc1 = [ ColDescr("l") ]
  colDesc2 = [ ColDescr("l"), ColDescr("l") ]
  colDesc3 = [ ColDescr("l"), ColDescr("l"), ColDescr("l") ]

  # TODO: test the setting of spanning on TableCell

  def testParseTableRows(self):
    t = parseTableRows([ "r1", "r2" ], self.colDesc2)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r1")
    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

  def testParseTableRows_tooMany(self):
    t = parseTableRows([ "r1", "r2|xyzzy" ], self.colDesc1)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r1")
    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

  def testParseTableRows_strip(self):
    t = parseTableRows([ "   r1    " ], self.colDesc1)
    self.assertEqual(len(t), 1)
    l = t[0].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r1")

  def testParseTableRows_preserve(self):
    t = parseTableRows([ "   r1    " ], [ ColDescr("lS") ])
    self.assertEqual(len(t), 1)
    l = t[0].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "\u2007\u2007\u2007r1")

  # Don't want to break existing tables with trailing or-bars
  @unittest.expectedFailure
  def testParseTableRows_ncol(self):
    with self.assertRaises(SystemExit) as cm:
      parseTableRows([ "r1|r1c2" ], self.colDesc1)
    self.assertEqual(cm.exception.code, 1)

  def testParseTableRows_col1(self):
    t = parseTableRows([ "r1", "r2", "<col=1>", "r1c2"], self.colDesc2)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 2)
    self.assertEquals(l[0].getData(), "r1")
    self.assertEquals(l[1].getData(), "r1c2")
    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

  def testParseTableRows_col1_failure(self):
    with self.assertRaises(SystemExit) as cm:
      parseTableRows([ "r1", "<col=1>", "r1c2" ], self.colDesc1)
    self.assertEqual(cm.exception.code, 1)

  def testParseTableRows_col1_toomany(self):
    with self.assertRaises(SystemExit) as cm:
      parseTableRows([ "r1", "<col=1>", "r1c2|r1c3" ], self.colDesc2)
    self.assertEqual(cm.exception.code, 1)

  def testParseTableRows_col1_split(self):
    t = parseTableRows([ "r1", "r2", "<col=1>", "r1c2|r1c3"], self.colDesc3)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r1")
    self.assertEquals(l[1].getData(), "r1c2")
    self.assertEquals(l[2].getData(), "r1c3")
    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

  def testParseTableRows_3col(self):
    t = parseTableRows(
      [ "r1", "r2", "<col=1>", "r1c2", "r2c2", "<col=2>", "r1c3", "r2c3" ], self.colDesc3)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r1")
    self.assertEquals(l[1].getData(), "r1c2")
    self.assertEquals(l[2].getData(), "r1c3")
    l = t[1].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r2")
    self.assertEquals(l[1].getData(), "r2c2")
    self.assertEquals(l[2].getData(), "r2c3")

  def testParseTableRows_3col_span(self):
    t = parseTableRows(
      [ "r1", "r2", "<col=1>", "r1c2", "<span>", "<col=2>", "<span>", "r2c3" ], self.colDesc3)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r1")
    self.assertEquals(l[1].getData(), "r1c2")
    assert l[2].isSpanned()
    l = t[1].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r2")
    assert l[1].isSpanned()
    self.assertEquals(l[2].getData(), "r2c3")

  def testParseTableRows_col_skip(self):
    t = parseTableRows([ "r1", "r2", "<col=2>", "r1c3"], self.colDesc3)
    self.assertEqual(len(t), 2)
    l = t[0].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "r1")
    self.assertEquals(l[1].getData(), "")
    self.assertEquals(l[2].getData(), "r1c3")
    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

  def testParseTableRows_row_skip(self):
    t = parseTableRows([ "r1", "r2", "<col=2>", "", "", "", "r4c3"], self.colDesc3)
    self.assertEqual(len(t), 4)

    l = t[0].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r1")

    l = t[1].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "r2")

    l = t[2].getCells()
    self.assertEquals(len(l), 1)
    self.assertEquals(l[0].getData(), "")

    l = t[3].getCells()
    self.assertEquals(len(l), 3)
    self.assertEquals(l[0].getData(), "")
    self.assertEquals(l[1].getData(), "")
    self.assertEquals(l[2].getData(), "r4c3")

  def testL(self):
    col = ColDescr('l')
    cell = TableCell("w1", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 1)
    self.assertEqual(cell.getLine(0), "w1   ")

  def testR(self):
    col = ColDescr('r')
    cell = TableCell("w1", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 1)
    self.assertEqual(cell.getLine(0), "   w1")

  def testC(self):
    col = ColDescr('c')
    cell = TableCell("w1", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 1)
    self.assertEqual(cell.getLine(0), " w1  ")

  def testLwrap(self):
    col = ColDescr('l')
    cell = TableCell("w1 word234 w2 w3 w4 w5", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 5)
    self.assertEqual(cell.getLine(0), "w1   ")
    self.assertEqual(cell.getLine(1), "word2")
    self.assertEqual(cell.getLine(2), "34 w2")
    self.assertEqual(cell.getLine(3), "w3 w4")
    self.assertEqual(cell.getLine(4), "w5   ")

  def testLwrap_space(self):
    col = ColDescr('l')
    cell = TableCell("  w1 word234 w2  ", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 3)
    self.assertEqual(cell.getLine(0), "w1   ")
    self.assertEqual(cell.getLine(1), "word2")
    self.assertEqual(cell.getLine(2), "34 w2")

  def testLwrap_space_preserve(self):
    col = ColDescr('lS')
    cell = TableCell("  w1 word234 w2  ", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 3)
    self.assertEqual(cell.getLine(0), "\u2007\u2007w1 ")
    self.assertEqual(cell.getLine(1), "word2")
    self.assertEqual(cell.getLine(2), "34 w2")

  def testLwrap_space_preserve_run(self):
    col = ColDescr('lS')
    cell = TableCell("  w1    w2 w3 w4 ", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 3)
    self.assertEqual(cell.getLine(0), "\u2007\u2007w1\u2007")
    self.assertEqual(cell.getLine(1), "\u2007\u2007\u2007w2")
    self.assertEqual(cell.getLine(2), "w3 w4")

  def testLB(self):
    col = ColDescr('lB')
    cell = TableCell("word1 w2", col)
    cell.format(5)
    cell.valign(5)
    self.assertEqual(cell.lineCount(), 5)
    self.assertEqual(cell.getLine(0), "     ")
    self.assertEqual(cell.getLine(1), "     ")
    self.assertEqual(cell.getLine(2), "     ")
    self.assertEqual(cell.getLine(3), "word1")
    self.assertEqual(cell.getLine(4), "w2   ")

  def testLBEmpty(self):
    col = ColDescr('lB')
    cell = TableCell("", col)
    cell.format(5)
    cell.valign(5)
    self.assertEqual(cell.lineCount(), 5)
    self.assertEqual(cell.getLine(0), "     ")
    self.assertEqual(cell.getLine(1), "     ")
    self.assertEqual(cell.getLine(2), "     ")
    self.assertEqual(cell.getLine(3), "     ")
    self.assertEqual(cell.getLine(4), "     ")

  def testLC(self):
    col = ColDescr('lC')
    cell = TableCell("word1 w2", col)
    cell.format(5)
    cell.valign(5)
    self.assertEqual(cell.lineCount(), 5)
    self.assertEqual(cell.getLine(0), "     ")
    self.assertEqual(cell.getLine(1), "word1")
    self.assertEqual(cell.getLine(2), "w2   ")
    self.assertEqual(cell.getLine(3), "     ")
    self.assertEqual(cell.getLine(4), "     ")

  def testHwrap(self):
    col = ColDescr('h')
    cell = TableCell("w1 word234 w2 w3 w4 w5", col)
    cell.format(5)
    self.assertEqual(cell.lineCount(), 8)
    self.assertEqual(cell.getLine(0), "w1   ")
    self.assertEqual(cell.getLine(1), "  wor")
    self.assertEqual(cell.getLine(2), "  d23")
    self.assertEqual(cell.getLine(3), "  4  ")
    self.assertEqual(cell.getLine(4), "  w2 ")
    self.assertEqual(cell.getLine(5), "  w3 ")
    self.assertEqual(cell.getLine(6), "  w4 ")
    self.assertEqual(cell.getLine(7), "  w5 ")

class TestMakeTable(unittest.TestCase):
  t = Text('ifile', 'ofile', 0, 'fmt')

  def test_simple(self):
    with self.assertRaises(SystemExit) as cm:
      u = self.t.makeTable([ "<table>", "</table>" ])
    self.assertEqual(cm.exception.code, 1)

  def test_rendOptionError(self):
    with self.assertRaises(SystemExit) as cm:
      self.t.makeTable([ "<table rend='foo' pattern='r10'>", "</table>" ])
    self.assertEqual(cm.exception.code, 1)

  def common_assertions(self, u, n, textN):
    assert len(u) == n
    assert u[0] == '▹.rs 1' and u[n-1] == '▹.rs 1'
    #for l in u:
    #  t.uprint("Line: " + l)
    # 11 + 11 = 22, 75-22=53//2 = 26.
    # Should be 26 + 1 + 10 + 1 + 10 
    self.assertEquals(len(u[textN]), 48)
    self.assertEquals(u[textN][0], '▹')

  def test_toowide(self):
    l = 'x' * 74
    # Column width truncated to 74
    u = self.t.makeTable([ "<table pattern='r99'>", l, "</table>" ])
    self.assertEquals(u[1], config.FORMATTED_PREFIX + l)

  def test_toowide1(self):
    l = 'x' * 80
    # Column width truncated to 74
    u = self.t.makeTable([ "<table pattern='r99'>", l, "</table>" ])
    # Chop-wrap onto two lines
    self.assertEquals(u[1], config.FORMATTED_PREFIX + 'x'*74)
    self.assertEquals(u[2], config.FORMATTED_PREFIX + ' '*68 + 'x'*6)

  def test_toowide2(self):
    l = 'x' * 80
    # Column width not truncated
    u = self.t.makeTable([ "<table rend='textwidth:99' pattern='r99'>", l, "</table>" ])
    # Right justified in 99 columns, with special no wrap
    self.assertEquals(u[1], config.FORMATTED_PREFIX + config.NO_WRAP_PREFIX +
      ' '*18 + 'x'*80)

  def test_t1(self):
    u = self.t.makeTable([ "<table pattern='r10 r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1          2")

  def test_t2(self):
    u = self.t.makeTable([ "<table pattern='l10 r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1                   2")

  def test_t3(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         │         2")

  def test_t3hash(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         ┃         2")

  def test_t4(self):
    u = self.t.makeTable([ "<table pattern='l10|| r10'>", "1|2", "</table>" ])
    self.common_assertions(u, 3, 1)
    assert u[1].endswith("1         ┃         2")

  def test_t5(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "_", "1|2", "_", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("──────────┬──────────")
    assert u[2].endswith("1         │         2")
    assert u[3].endswith("──────────┴──────────")

  def test_t6(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "=", "1|2", "=", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("━━━━━━━━━━┯━━━━━━━━━━")
    assert u[2].endswith("1         │         2")
    assert u[3].endswith("━━━━━━━━━━┷━━━━━━━━━━")

  def test_t6_col(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "=", "1", "=", "<col=1>", "", "2", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("━━━━━━━━━━┯━━━━━━━━━━")
    assert u[2].endswith("1         │         2")
    assert u[3].endswith("━━━━━━━━━━┷━━━━━━━━━━")

  def test_t7(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "=", "1|2", "=", "</table>" ])
    self.common_assertions(u, 5, 2)
    assert u[1].endswith("━━━━━━━━━━┳━━━━━━━━━━")
    assert u[2].endswith("1         ┃         2")
    assert u[3].endswith("━━━━━━━━━━┻━━━━━━━━━━")

  def test_span1(self):
    u = self.t.makeTable([ "<table pattern='l10# r10'>", "=", "1|<span>", "=", "</table>" ])
    assert u[1].endswith("━━━━━━━━━━━━━━━━━━━━━")
    assert u[2].endswith("1")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━")

  def test_span2(self):
    u = self.t.makeTable([ "<table pattern='l10| r10'>", "_", "1|<span>", "=", "</table>" ])
    assert u[1].endswith("─────────────────────")
    assert u[2].endswith("1")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━")

  def test_span3(self):
    u = self.t.makeTable([ "<table pattern='l10# r10 |l1'>", "=", "1|<span>|A", "=", "2|<span>|B", "=", "</table>" ])
    assert len(u) == 7
    assert u[1].endswith("━━━━━━━━━━━━━━━━━━━━━┯━")
    assert u[2].endswith("1                    │A")
    assert u[3].endswith("━━━━━━━━━━━━━━━━━━━━━┿━")
    assert u[4].endswith("2                    │B")
    assert u[5].endswith("━━━━━━━━━━━━━━━━━━━━━┷━")

  def test_indent_of_horiz_line(self):
    u = self.t.makeTable([ "<table pattern='l1 r1'>", '_', 'A|B', '_', "</table>" ])
    # 75-3=72//2 = 36.
    # Should be 36 + 3
    assert len(u) == 5
    assert len(u[1]) == 39
    assert u[1].endswith("                                   ───")
    assert u[2].endswith("                                   A B")
    assert u[3].endswith("                                   ───")

  def test_blank_line(self):
    u = self.t.makeTable([ "<table pattern='l1 |r1'>", '_', '', '_', "</table>" ])
    # 75-3=72//2 = 36.
    # Should be 36 + 3
    #for l in u:
    #  uprint("Line: " + l + "$")
    assert len(u) == 5
    assert len(u[1]) == 39
    assert u[1].endswith("                                   ─┬─")
    assert u[2].endswith("                                    │")
    assert u[3].endswith("                                   ─┴─")

  def test_span4(self):
    u = self.t.makeTable([
      "<table pattern='l10# r10 ||l1'>",
        "_",
        "1|<span>|A",
        "_",
        "2|<span>|B",
        "_",
      "</table>"
    ])
    assert len(u) == 7
    assert u[1].endswith("─────────────────────┰─")
    assert u[2].endswith("1                    ┃A")
    assert u[3].endswith("─────────────────────╂─")
    assert u[4].endswith("2                    ┃B")
    assert u[5].endswith("─────────────────────┸─")

  def test_span5(self):
    u = self.t.makeTable([
      "<table pattern='l10# r10 ||l1'>",
        "_",
        "1|<span>|A",
        "_",
        "2|3|B",
        "_",
      "</table>"
    ])
    assert len(u) == 7
    assert u[1].endswith("─────────────────────┰─")
    assert u[2].endswith("1                    ┃A")
    assert u[3].endswith("──────────┰──────────╂─")
    assert u[4].endswith("2         ┃         3┃B")
    assert u[5].endswith("──────────┸──────────┸─")

  def test_2span1(self):
    u = self.t.makeTable([
      "<table pattern='r5# r5| r5| |l1'>",
        "_",
        "1|<span>|<span>|A",
        "_",
      "</table>" ])
    assert len(u) == 5
    self.assertRegexpMatches(u[1], "────────────────┰─$")
    assert u[2].endswith("               1┃A")
    assert u[3].endswith("────────────────┸─")

  def test_2span5(self):
    u = self.t.makeTable([
      "<table pattern='l5# r5| r5| l1'>",
        "_",
        "1|<span>|<span>|A",
        "_",
        "2|<span>|3|B",
        "_",
      "</table>"
    ])
    #for l in u:
    #  self.t.uprint("Line: " + l)
    assert len(u) == 7
    assert u[1].endswith("─────────────────┬─")
    assert u[2].endswith("1                │A")
    assert u[3].endswith("───────────┬─────┼─")
    assert u[4].endswith("2          │    3│B")
    assert u[5].endswith("───────────┴─────┴─")

  def test_wrap1(self):
    u = self.t.makeTable([
      "<table pattern='r8 r1'>",
        "word longer test w1|B",
      "</table>"
    ])
    self.assertEquals(len(u), 5)
    assert u[1].endswith("    word B")
    assert u[2].endswith("  longer")
    assert u[3].endswith(" test w1")

  def test_wrap_align(self):
    u = self.t.makeTable([
      "<table pattern='r8 r1'>",
        "<align=l>word longer test w1|B",
      "</table>"
    ])
    assert len(u) == 5
    assert u[1].endswith("word     B")
    assert u[2].endswith("longer")
    assert u[3].endswith("test w1")

  def test_wrap_align2(self):
    u = self.t.makeTable([
      "<table pattern='r8 r2'>",
        "<align=l>word longer test w1|<align=l>B",
        "word longer test w2|C",
      "</table>"
    ])
#    for l in u:
#      uprint("Line: " + l)
    assert len(u) == 8
    assert u[1].endswith("word     B")
    assert u[2].endswith("longer")
    assert u[3].endswith("test w1")
    assert u[4].endswith("    word  C")
    assert u[5].endswith("  longer")
    assert u[6].endswith(" test w2")

  # TODO: Tests for computing widths
  # TODO: Tests for computing some widths
