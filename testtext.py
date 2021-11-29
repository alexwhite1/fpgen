import unittest

import config
from fpgen import Text
from fpgen import userOptions

# Test the method Text.processInline
class TestTextInline(unittest.TestCase):
  def setUp(self):
    self.text = Text(None, None, 0, 't')

  def tearDown(self):
    config.uopt = userOptions()

  def test_text_inline_sc(self):
    line = self.text.smallCaps("<sc>Testing, one two</sc>")
    self.assertEqual(line, "TESTING, ONE TWO")

  def test_text_inline_sc1(self):
    line = self.text.smallCaps("abc<sc>Testing, one two</sc>def")
    self.assertEqual(line, "abcTESTING, ONE TWOdef")

  def test_text_inline_sc_with_other(self):
    line = self.text.smallCaps("abc<sc><i>Testing, one</i> two</sc>def")
    self.assertEqual(line, "abc<i>TESTING, ONE</i> TWOdef")

  # If the internal tag is screwed up, just stops matching (no error)
  def test_text_inline_sc_with_other_no_close(self):
    line = self.text.smallCaps("abc<sc><i>Testing, one</i two</sc>def")
    self.assertEqual(line, "abc<i>TESTING, ONE</i twodef")

  # Unterminated <sc> does nothing.
  def test_text_inline_sc2(self):
    self.text.wb = [
      "abc<sc>Testing, one twodef"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc<sc>Testing, one twodef" ])

  def test_text_inline_sc_uopt_titlecase(self):
    # With titlecase option, just deletes the tags
    config.uopt.addopt("sc", "titlecase")
    line = self.text.smallCaps("abc<sc>Testing, one two</sc>def")
    self.assertSequenceEqual(line, "abcTesting, one twodef")

  """
  def test_text_inline_gesperrt(self):
    self.text.wb = [
      "abc<g>Testing, one two</g>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abcT□e□s□t□i□n□g□,□ □o□n□e□ □t□w□odef" ])
  """

  def test_text_inline_gesperrt(self):
    self.text.wb = [
      "abc<g>Testing, one two</g>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_Testing, one two_def" ])

  def test_text_inline_italic(self):
    self.text.wb = [
      "abc<i>Testing, one two</i>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_Testing, one two_def" ])

  def test_text_inline_italic_sc(self):
    self.text.wb = [
      "abc<sc><i>Testing, one two</i></sc>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_TESTING, ONE TWO_def" ])

  def test_text_inline_sc_italic(self):
    self.text.wb = [
      "abc<i><sc>Testing, one two</sc></i>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_TESTING, ONE TWO_def" ])

  """
  def test_text_inline_sc_gesperrt(self):
    self.text.wb = [
      "abc<g><sc>Testing, one two</sc></g>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abcT□E□S□T□I□N□G□,□ □O□N□E□ □T□W□Odef" ])

  def test_text_inline_gesperrt_sc(self):
    self.text.wb = [
      "abc<sc><g>Testing, one two</g></sc>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abcT□E□S□T□I□N□G□,□ □O□N□E□ □T□W□Odef" ])
  """

  def test_text_inline_sc_gesperrt(self):
    self.text.wb = [
      "abc<g><sc>Testing, one two</sc></g>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_TESTING, ONE TWO_def" ])

  def test_text_inline_gesperrt_sc(self):
    self.text.wb = [
      "abc<sc><g>Testing, one two</g></sc>def"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abc_TESTING, ONE TWO_def" ])

  def test_text_inline_fs(self):
    self.text.wb = [
      "abc<fs:s>Testing, one twodef</fs>"
    ]
    self.text.processInline()
    self.assertSequenceEqual(self.text.wb, [ "abcTesting, one twodef" ])

# Test the method Text.rewrap
class TestTextRewrap(unittest.TestCase):
  def setUp(self):
    self.text = Text(None, None, 0, 't')
    config.LINE_WIDTH = 25

  def test_text_rewrap_footnote1(self):
    self.text.wb = [
      "l1", "<footnote id='[1]'>", "l2", "l3", "</footnote>", "l4"
    ]
    self.text.rewrap();
    self.assertSequenceEqual(self.text.wb, [
      ".rs 1", "l1", ".rs 1", ".rs 1",
      "[1] l2 l3", ".rs 1", ".rs 1", "l4", ".rs 1",
    ])

  def test_text_rewrap_footnote_l(self):
    self.text.wb = [
      "l1", "<footnote id='[1]'>", "<l rend='center'>l2</l>", "l3", "</footnote>", "l4"
    ]
    self.text.rewrap();
    self.assertSequenceEqual(self.text.wb, [
      ".rs 1", "l1", ".rs 1", ".rs 1",
      "[1]", ".rs 1",
      config.FORMATTED_PREFIX + "           l2            ",
      ".rs 1", "l3", ".rs 1", ".rs 1", "l4", ".rs 1",
    ])

# Test the method Text.oneL
class TestTextoneL(unittest.TestCase):
  def setUp(self):
    self.text = Text(None, None, 0, 't')
    self.text.qstack = [""]
    self.P = config.FORMATTED_PREFIX
    config.LINE_WIDTH = 20

  def test_text_onel_left(self):
    result = self.text.oneL({}, "rend='left'", "line")
    self.assertSequenceEqual(result, [ self.P+"line" ])

  def test_text_onel_left_q(self):
    self.text.qstack.append("   ")
    result = self.text.oneL({}, "rend='left'", "line")
    self.assertSequenceEqual(result, [ self.P+"   line" ])

  def test_text_onel_no_align(self):
    result = self.text.oneL({}, "", "line")
    self.assertSequenceEqual(result, [ self.P+"line" ])

  def test_text_onel_ml(self):
    result = self.text.oneL({}, "rend='ml:3em'", "line")
    self.assertSequenceEqual(result, [ self.P+"   line" ])

  def test_text_onel_right(self):
    result = self.text.oneL({}, "rend='right'", "line")
    self.assertSequenceEqual(result, [ self.P+" "*16+"line" ])

  def test_text_onel_mr(self):
    result = self.text.oneL({}, "rend='mr:3em'", "line")
    self.assertSequenceEqual(result, [ self.P+" "*13+"line" ])

  def test_text_onel_right_from_LG(self):
    result = self.text.oneL({'right':None}, "", "line")
    self.assertSequenceEqual(result, [ self.P+" "*16+"line" ])

  def test_text_onel_center_override_LG(self):
    result = self.text.oneL({'right':None}, "rend='center'", "line")
    self.assertSequenceEqual(result, [ self.P+" "*8+"line"+" "*8 ])

  def test_text_onel_center(self):
    result = self.text.oneL({}, "rend='center'", "line")
    self.assertSequenceEqual(result, [ self.P+" "*8+"line"+" "*8 ])

  def test_text_onel_sa(self):
    result = self.text.oneL({}, "rend='left sa:5'", "line")
    self.assertSequenceEqual(result, [ self.P+"line", ".rs 5" ])

  def test_text_onel_sb(self):
    result = self.text.oneL({}, "rend='left sb:5'", "line")
    self.assertSequenceEqual(result, [ ".rs 5", self.P+"line" ])

  def test_text_onel_sb_sa(self):
    result = self.text.oneL({}, "rend='left sa:3 sb:5'", "line")
    self.assertSequenceEqual(result, [ ".rs 5", self.P+"line", ".rs 3" ])

  def test_text_onel_triple(self):
    result = self.text.oneL({}, "rend='triple'", "a|b|c")
    self.assertSequenceEqual(result, [ self.P+"a        b        c" ])

  def test_text_onel_triple_lr(self):
    result = self.text.oneL({}, "rend='triple'", "a||c")
    self.assertSequenceEqual(result, [ self.P+"a" + " "*18 + "c" ])

class TestTextFormatLineGroup(unittest.TestCase):
  def setUp(self):
    self.text = Text(None, None, 0, 't')
    self.text.qstack = [""]
    self.P = config.FORMATTED_PREFIX
    self.H = config.HARD_SPACE
    config.LINE_WIDTH = 20

  def test_text_LG_left(self):
    block = [ '<l>line</l>' ]
    self.text.formatLineGroup(block, {}, 'left')
    self.assertSequenceEqual(block, [ self.P+'line' ])

  def test_text_LG_right(self):
    block = [ '<l>line</l>' ]
    self.text.formatLineGroup(block, {'right':None}, 'right')
    self.assertSequenceEqual(block, [ self.P+16*" "+'line' ])

  # Note bug wasn't protecting triple, causing extra paragraph line.
  def test_text_LG_left_triple(self):
    block = [ '<l>l1</l>', '<l rend="triple">a|b|c</l>', '<l>l2</l>' ]
    self.text.formatLineGroup(block, {'left':None}, 'left')
    self.assertSequenceEqual(block, [
      self.P+"l1",
      self.P+"a        b        c",
      self.P+"l2",
    ])

  def test_text_LG_block(self):
    block = [ '<l>l1</l>', '<l>longer</l>' ]
    self.text.formatLineGroup(block, {'block':None}, 'block')
    self.assertSequenceEqual(block, [
      self.P+7*self.H+'l1',
      self.P+7*self.H+'longer'
    ])

  def test_text_LG_block_right(self):
    block = [ '<l>l1</l>', '<l>longer</l>' ]
    self.text.formatLineGroup(block, {'block-right':None}, 'block-right')
    self.assertSequenceEqual(block, [
      self.P+14*self.H+'l1',
      self.P+14*self.H+'longer'
    ])

  def test_text_LG_block_right_tag(self):
    block = [ '<l>l1</l>', '<l>lo[[i]]ng[[/i]]er</l>' ]
    self.text.formatLineGroup(block, {'block-right':None}, 'block-right')
    self.assertSequenceEqual(block, [
      self.P+12*self.H+'l1',
      self.P+12*self.H+'lo_ng_er'
    ])
