import unittest

import config
from fpgen import Text
from fpgen import userOptions

class TestFootnote(unittest.TestCase):
  def setUp(self):
    self.text = Text(None, None, 0, 't')

  def tearDown(self):
    config.uopt = userOptions()

  def seq1(self):
    self.text.wb = [
      "l1",
      "w1<fn id='1'> w2",
      "w3",
      "<footnote id='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]

  def seq2(self):
    self.text.wb = [
      "l1",
      "w1<fn id='#'> w2",
      "w3",
      "<footnote id='#'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]

  def test_footnote_none_auto(self):
    self.seq2()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_none_auto2(self):
    self.seq2()
    self.text.wb += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[2]' target='2'>",
      "<footnote id='[2]' target='2'>",
      "fn",
      "</footnote>",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_none_auto_same_line(self):
    self.text.wb = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1'>, more words, <fn id='[2]' target='2'>, another <fn id='[3]' target='3'>",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_reset_auto_same_line(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    self.text.wb = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1_1'>, more words, <fn id='[2]' target='2_1'>, another <fn id='[3]' target='3_1'>",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_reset_auto_same_line_and_reset(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    self.text.wb = [
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
      "<footnote id='1'>",
      "fn",
      "</footnote>",
      "<genfootnotes>",
      "blah<fn id='#'>, more words, <fn id='#'>, another <fn id='#'>",
    ]
    result = [
      "blah<fn id='[1]' target='1_1'>, more words, <fn id='[2]' target='2_1'>, another <fn id='[3]' target='3_1'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_1'>",
      "fn",
      "</footnote>",
      "",
      "blah<fn id='[1]' target='1_2'>, more words, <fn id='[2]' target='2_2'>, another <fn id='[3]' target='3_2'>",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_none_unchanged(self):
    self.seq1()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_heading(self):
    self.seq1()
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
    ]
    config.uopt.addopt("footnote-location", "heading")
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  # Emit early if marker hit
  def test_footnote_heading_marker(self):
    self.seq1()
    self.text.wb[-2] = "<genfootnotes>"
    self.text.wb += [ "l2", "<heading level='1'>h1</heading>", "more text" ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "text",
      "l2",
      "<heading level='1'>h1</heading>",
      "more text",
    ]
    config.uopt.addopt("footnote-location", "heading")
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_heading_auto2(self):
    config.uopt.addopt("footnote-location", "heading")
    self.seq2()
    self.text.wb += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[2]' target='2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[2]' target='2'>",
      "fn",
      "</footnote>",
      "",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  def test_footnote_heading_reset_auto2(self):
    config.uopt.addopt("footnote-location", "heading-reset")
    self.seq2()
    self.text.wb += [
      "blah<fn id='#'>",
      "<footnote id='#'>",
      "fn",
      "</footnote>",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1_1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_1'>",
      "foot",
      "</footnote>",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "blah<fn id='[1]' target='1_2'>",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1_2'>",
      "fn",
      "</footnote>",
      "",
    ]
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  # No <heading> tag? Emit at end of file
  def test_footnote_heading_end(self):
    self.seq1()
    del self.text.wb[-2]     # remove heading
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "text",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",
    ]
    config.uopt.addopt("footnote-location", "heading")
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)

  # Emit at marker, not heading
  def test_footnote_marker(self):
    self.seq1()
    self.text.wb += [
      "<genfootnotes>",
      "more text",
    ]
    result = [
      "l1",
      "w1<fn id='[1]' target='1'> w2",
      "w3",
      "",
      "More text",
      "",
      "<heading level='1'>h1</heading>",
      "text",
      "<hr rend='footnotemark'>",
      "<footnote id='[1]' target='1'>",
      "foot",
      "</footnote>",
      "",       # blank line after footnotes
      "more text",
    ]
    config.uopt.addopt("footnote-location", "marker")
    self.text.relocateFootnotes()
    self.assertSequenceEqual(self.text.wb, result)
