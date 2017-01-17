import unittest

import config
from fpgen import HTML
from fpgen import userOptions
from msgs import cprint

# Test the method HTML.markPara
class TestHTMLPara(unittest.TestCase):
  def setUp(self):
    self.html = HTML(None, None, 0, 'h')

  def tearDown(self):
    config.uopt = userOptions()

  # TOTEST:
  # - preformatted, <lg>, <table>
  # - dropcap
  # - multiple blank lines

  def test_html_start_file(self):
    self.html.wb = [
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
      "",
    ]);

  def test_html_end_file(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
    ]);

  def test_html_simple(self):
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
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
      "",
    ]);

  def test_html_indent_nobreak(self):
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
      "<p class='pindent'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='noindent'>p2l1</p>",
      "",
    ]);

  def test_html_nobreak(self):
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

  def test_html_hang(self):
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
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  def test_html_pstyle_bad(self):
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

  def test_html_default_hang(self):
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

  def test_html_hang_and_revert(self):
    self.html.wb = [
        "",
        "<pstyle=hang>",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        "",
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

  #@unittest.expectedFailure
  def test_html_hang_and_revert_immediate(self):
    self.html.wb = [
        "",
        "<pstyle=hang>",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        "",
        "p3l1",
        # Note no blank line, should still terminate paragraph
        "<pstyle=default>",
        ""
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p class='hang'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
      "<p class='hang'>p3l1</p>",
      "",
    ]);

  def test_html_indent_hang(self):
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
      "<p class='pindent'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  def test_html_page(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "<pn='23'>",
        "p1l2w1",
        "",
    ]
    self.html.processPageNum();
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>p1l1w1, p1l1w2",
      "⪦23⪧",
      "p1l2w1</p>",
      "",
    ]);

  # See ocean-src.txt
  def test_html_page_hang(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "<pn='23'>",
        "<hang>p1l2w1",
        "",
    ]
    self.html.processPageNum();
    self.html.markPara();
    # Is this correct? Probably, page number is just considered part of
    # the text, and if they did it before a <hang>, then it is indeed part
    # of an empty paragraph
    self.assertSequenceEqual(self.html.wb, [
      "<p>p1l1w1, p1l1w2",
      "⪦23⪧</p>",
      "<p class='hang'>p1l2w1</p>",
      "",
    ]);

  # Must not put a tag around the illustration caption.
  def test_html_illustration_with_caption(self):
    self.html.wb = [
      "<pb>",
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "Photogravure. Annan. Glasgow.<br>",
      "JACQUES CARTIER<br>",
      "From the painting at St Malo",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.protectMarkup()
    self.html.markPara()
    self.html.restoreMarkup()
    self.assertSequenceEqual(self.html.wb, [
      "<pb>",
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>Photogravure. Annan. Glasgow.<br>",
      "JACQUES CARTIER<br>",
      "From the painting at St Malo</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  # Must not put a tag around the illustration caption.
  def test_html_illustration_with_multipara_caption(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "first line",
      "",
      "second line",
      "third line",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>first line</p>",
      "",
      "<p class='caption'>second line",
      "third line</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  # Must tag a caption which is on the same line
  def test_html_illustration_with_one_line_caption(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>paragraph</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>paragraph</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_with_caption_and_text(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>paragraph",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>paragraph</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_with_caption_and_text_and_end(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>paragraph",
      "more paragraph</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>paragraph",
      "more paragraph</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_with_caption_newline_and_text_and_end(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "paragraph</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>paragraph</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_no_caption(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_empty_caption(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption></caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_empty_caption2(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_empty_caption3(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption> </caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_empty_caption4(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_illustration_br_not_para_break(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "word1",
      "<br/>",
      "word2",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='caption'>word1",
      "<br/>",
      "word2</p>",
      "</caption>",
      "</illustration>",
      "",
      "<pb>",
    ]);

  def test_html_wrong_code_using_own_para(self):
    self.html.wb = [
        "",
        "<p style='text-indent:-2cm; padding-left:2cm;'>p1l1w1, p1l1w2",
        "p1l2w1",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p style='text-indent:-2cm; padding-left:2cm;'>p1l1w1, p1l1w2",
      "<p>p1l2w1</p>",
      "",
    ]);

  # Make sure we don't rely on blank lines to close the para
  def test_html_no_blank_before_quote(self):
    self.html.wb = [
        "",
        "l1",
        "<quote>",
        "l2",
        "</quote>",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "<quote>",
      "<p>l2</p>",
      "</quote>",
      ""
    ]);

  # Make sure we don't rely on blank lines to close the para
  def test_html_quote_break(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "<quote>",
        "<hang>l2",
        "</quote>",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<quote>",
      "<p class='hang'>l2</p>",
      "</quote>",
      ""
    ]);

  def test_html_no_table(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "<table pattern='foo'>",
        "l1",
        "",
        "l2",
        "</table>",
        "l3",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<table pattern='foo'>",
      "l1",
      "",
      "l2",
      "</table>",
      "<p>l3</p>",
      ""
    ]);

  def test_html_no_lg(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "<lg rend='foo'>",
        "l1",
        "",
        "l2",
        "</lg>",
        "l3",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<lg rend='foo'>",
      "l1",
      "",
      "l2",
      "</lg>",
      "<p>l3</p>",
      ""
    ]);

  def test_html_no_sidenote_multi(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "<sidenote>",
        "l1",
        "",
        "l2",
        "</sidenote>",
        "l3",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<sidenote>",
      "l1",
      "",
      "l2",
      "</sidenote>",
      "<p>l3</p>",
      ""
    ]);

  def test_html_no_sidenote_two(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "<sidenote>",
        "l1",
        "",
        "l2</sidenote>",
        "l3",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<sidenote>",
      "l1",
      "",
      "l2</sidenote>",
      "<p>l3</p>",
      ""
    ]);

  def test_html_l_tag_breaks_para(self):
    self.html.wb = [
        "",
        "l1",
        "",
        "l2",
        "<l rend='center'>xxx</l>",
        "l3",
        "l4",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<p>l2</p>",
      "<l rend='center'>xxx</l>",
      "<p>l3",
      "l4</p>",
      ""
    ]);

  def test_html_leading_blanks(self):
    self.html.wb = [
        "",
        "",
        "",
        "l1",
        "l3",
        "l4",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1",
      "l3",
      "l4</p>",
      ""
    ]);

  def test_html_multi_blank(self):
    self.html.wb = [
        "l1",
        "",
        "",
        "l3",
        "l4",
        "",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "<p>l1</p>",
      "",
      "<p>l3",
      "l4</p>",
      ""
    ]);
