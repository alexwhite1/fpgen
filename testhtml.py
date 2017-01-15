import unittest

import config
from fpgen import HTML
from fpgen import userOptions

# Test the method HTML.markPara
class TestHTMLPara(unittest.TestCase):
  def setUp(self):
    self.html = HTML(None, None, 0, 'h')

  def tearDown(self):
    config.uopt = userOptions()

  def test_text_simple(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
      "",
    ]);

  def test_text_indent_nobreak(self):
    config.uopt = userOptions();
    config.uopt.addopt("pstyle", "indent");
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<nobreak>p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<p class='pindent'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='noindent'>p2l1</p>",
      "",
    ]);

  def test_text_nobreak(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<nobreak>p2l1",
        ""
    ]
    # <nobreak> only legal with option pstyle set to indent.
    with self.assertRaises(SystemExit) as cm:
      self.html.markPara();

  def test_text_hang(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<hang>p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  def test_text_pstyle_bad(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<pstyle=hnag>p2l1",
        ""
    ]
    # Bad pstyle: hnag
    with self.assertRaises(SystemExit) as cm:
      self.html.markPara();

  def test_text_default_hang(self):
    self.html.wb = [
        "",
        "<pstyle=hang>",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p class='hang'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  @unittest.expectedFailure
  def test_text_hang_and_revert(self):
    self.html.wb = [
        "",
        "<pstyle=hang>",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
        "<pstyle=default>",
        "p3l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p class='hang'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
      "<p>p3l1</p>",
      ""
    ]);

  def test_text_indent_hang(self):
    config.uopt = userOptions();
    config.uopt.addopt("pstyle", "indent");
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<pstyle=hang>",
        "p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<p class='pindent'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);
