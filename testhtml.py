import unittest

import config
from fpgen import HTML
from fpgen import userOptions
from msgs import cprint
import para

# Test the method HTML.markPara
class TestHTMLPara(unittest.TestCase):
  def setUp(self):
    self.html = HTML(None, None, 0, 'h')
    config.uopt.setGenType('h')

  def tearDown(self):
    config.uopt = userOptions()

  # TOTEST:
  # - preformatted, <lg>, <table>
  # - dropcap
  # - multiple blank lines

  def test_html_start_file(self):
    wb = [
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
      "",
    ]);

  def test_html_end_file(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "",
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
    ]);

  def test_html_simple(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p>p2l1</p>",
      "",
    ]);

  def test_html_noblank(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "<l rend='center'>lll</l>",
        "p2l1w1, p2l1w2",
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "",
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "<l rend='center'>lll</l>",
      "<p>p2l1w1, p2l1w2</p>",
    ]);

  def test_html_indent_nobreak(self):
    config.uopt = userOptions();
    config.uopt.addopt("pstyle", "indent");
    config.uopt.setGenType('h')
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
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<nobreak>p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='noindent'>p2l1</p>",
      "",
    ]);

  def test_html_indent(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<indent>p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='pindent'>p2l1</p>",
      "",
    ]);

  def test_html_list(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<list>p2l1 p2l1w2",
        "p2l2",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<div class='listEntry'>",
      "<span class='listTag'>p2l1</span><p class='listPara'>p2l1w2",
      "p2l2</p>",
      "</div>",
      "",
    ]);

  def test_html_hang(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<hang>p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  def test_html_hang_blank(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<hang>",
        "p2l1",
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

  def test_html_hang_multi_blank(self):
    self.html.wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<hang>",
        "",
        "",
        "p2l1",
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

  def test_html_last_wins(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<nobreak>",
        "",
        "<hang>",
        "",
        "p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
    ]);

  def test_html_last_wins2(self):
    wb = [
        "",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "<hang>",
        "",
        "<nobreak>",
        "",
        "p2l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='noindent'>p2l1</p>",
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
    wb = [
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
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p class='hang'>p1l1w1, p1l1w2",
      "p1l2w1</p>",
      "",
      "<p class='hang'>p2l1</p>",
      "",
      "<p>p3l1</p>",
      ""
    ]);

  def test_html_pstyle_with_override(self):
    wb = [
        "",
        "<pstyle=hang>",
        "<nobreak>",
        "p1l1w1, p1l1w2",
        "p1l2w1",
        "",
        "p2l1",
        "",
        "<pstyle=default>",
        "p3l1",
        ""
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p class='noindent'>p1l1w1, p1l1w2",
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
    config.uopt.setGenType('h')
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
      "⪦23,23⪧",
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
      "⪦23,23⪧</p>",
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
    self.html.protectMarkup(self.html.wb)
    self.html.markPara()
    self.html.restoreMarkup(self.html.wb)
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

  def test_html_illustration_with_one_line_caption_and_credit(self):
    self.html.wb = [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>paragraph</caption>",
      "<credit>credit paragraph</credit>",
      "</illustration>",
      "",
      "<pb>",
    ]
    self.html.markPara();
    self.assertSequenceEqual(self.html.wb, [
      "",
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'>",
      "<caption>",
      "<p class='credit'>credit paragraph</p>",
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
      "<illustration id='frontis' rend='w:100%' src='images/frontis.jpg'/>",
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
    wb = [
        "",
        "",
        "",
        "l1",
        "l3",
        "l4",
        "",
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>l1",
      "l3",
      "l4</p>",
      ""
    ]);

  def test_html_multi_blank(self):
    wb = [
        "l1",
        "",
        "",
        "l3",
        "l4",
        "",
    ]
    result = para.markParaArray(self.html, wb, "line");
    self.assertSequenceEqual(result, [
      "<p>l1</p>",
      "",
      "<p>l3",
      "l4</p>",
      ""
    ]);

  def test_lead_in_normal(self):
    wb = [
        "<heading level='1'>heading</heading>",
        "",
        "word1 w2 w3",
        "w4 w5",
        "",
        "w1 w2 w3",
        "w4 w5",
    ]
    self.html.uprop.addprop("lead-in-after", "h1")
    result = para.markParaArray(self.html, wb, "line")
    self.assertSequenceEqual(result, [
      "<heading level='1'>heading</heading>",
      "",
      "<p>⩤span class='lead-in'⩥word1⩤/span⩥ w2 w3",
      "w4 w5</p>",
      "",
      "<p>w1 w2 w3",
      "w4 w5</p>",
    ])

  def test_lead_in_simple(self):
    line = "word1 w2 w3"
    word, line = para.getLeadIn(line)
    self.assertEqual(word, "word1")
    self.assertEqual(line, " w2 w3")

  # lead-in takes all leading words starting with caps
  def test_lead_in_multi_word(self):
    line = "word1 W2 W3 wx wy wz"
    word, line = para.getLeadIn(line)
    self.assertEqual(word, "word1 W2 W3")
    self.assertEqual(line, " wx wy wz")

  # No lead-in if <sc> in first word
  def test_lead_in_sc(self):
    line = "⩤sc⩥word1 W2⩤/sc⩥ W3 wx wy wz"
    word, line = para.getLeadIn(line)
    self.assertEqual(word, "")
    self.assertEqual(line, "⩤sc⩥word1 W2⩤/sc⩥ W3 wx wy wz")

  # lead-in does not stop due to a space in a tag
  def test_lead_in_include_dropcap(self):
    line = "⩤drop src='xxx'⩥w⩤/drop⩥1 w2 w3"
    word, line = para.getLeadIn(line)
    self.assertEqual(word, "⩤drop src='xxx'⩥w⩤/drop⩥1")
    self.assertEqual(line, " w2 w3")

  # lead-in of one letter includes the next word
  def test_lead_in_short_word(self):
    line = "w w2 w3"
    word, line = para.getLeadIn(line)
    self.assertEqual(word, "w w2")
    self.assertEqual(line, " w3")

  def test_wordlen1(self):
    w = "I"
    l = para.wordlen(w)
    self.assertEqual(l, 1)

  def test_wordlen(self):
    w = "“I"
    l = para.wordlen(w)
    self.assertEqual(l, 1)

  def test_wordlenA(self):
    w = "“’I,"
    l = para.wordlen(w)
    self.assertEqual(l, 1)

  def test_wordlen2(self):
    w = "“In"
    l = para.wordlen(w)
    self.assertEqual(l, 2)

  def test_drop_cap_after(self):
    wb = [
        "<heading level='1'>heading</heading>",
        "",
        "w1 w2 w3",
        "w4 w5",
        "",
        "w1 w2 w3",
        "w4 w5",
    ]
    self.html.uprop.addprop("drop-after", "h1")
    result = para.markParaArray(self.html, wb, "line")
    self.assertSequenceEqual(result, [
      "<heading level='1'>heading</heading>",
      "",
      "<p>⩤span class='dropcap'⩥w⩤/span⩥1 w2 w3",
      "w4 w5</p>",
      "",
      "<p>w1 w2 w3",
      "w4 w5</p>",
    ])

  def test_drop_cap_simple(self):
    word = "w1"
    word = para.autoDropCap(word)
    self.assertEqual(word, self.html.dropCapMarker + "⩤span class='dropcap'⩥w⩤/span⩥1")

  # No auto-drop-cap if font-change
  def test_drop_cap_no_italics(self):
    word = "⩤sc⩥w1⩤/sc⩥"
    word = para.autoDropCap(word)
    self.assertEqual(word, "⩤sc⩥w1⩤/sc⩥")

  # Drop cap includes double and single quotes
  def test_drop_cap_quote(self):
    word = "“w1"
    word = para.autoDropCap(word)
    self.assertEqual(word, self.html.dropCapMarker + "⩤span class='dropcap'⩥“w⩤/span⩥1")

  def test_drop_cap_apostrophe(self):
    word = "‘w1"
    word = para.autoDropCap(word)
    self.assertEqual(word, self.html.dropCapMarker + "⩤span class='dropcap'⩥‘w⩤/span⩥1")

  # No change if dropcap and leadin both false
  def test_decoration_no_no(self):
    wb = [
      "w1 w2 w3",
      "w4 w5",
    ]
    result = para.decoration(wb, False, False)
    self.assertSequenceEqual(result, [
      "w1 w2 w3",
      "w4 w5",
    ])

  # drop cap true, leadin false
  def test_decoration_yes_no(self):
    wb = [
      "w1 w2 w3",
      "w4 w5",
    ]
    result = para.decoration(wb, True, False)
    self.assertSequenceEqual(result, [
      self.html.dropCapMarker + "⩤span class='dropcap'⩥w⩤/span⩥1 w2 w3",
      "w4 w5",
    ])

  # drop cap false, leadin true
  def test_decoration_no_yes(self):
    wb = [
      "word1 w2 w3",
      "w4 w5",
    ]
    result = para.decoration(wb, False, True)
    self.assertSequenceEqual(result, [
      "⩤span class='lead-in'⩥word1⩤/span⩥ w2 w3",
      "w4 w5",
    ])

  # drop cap true, leadin true
  def test_decoration_yes_yes(self):
    wb = [
      "word1 w2 w3",
      "w4 w5",
    ]
    result = para.decoration(wb, True, True)
    self.assertSequenceEqual(result, [
      "⩤span class='lead-in'⩥" +
        self.html.dropCapMarker +
        "⩤span class='dropcap'⩥w⩤/span⩥ord1⩤/span⩥ w2 w3",
      "w4 w5",
    ])
