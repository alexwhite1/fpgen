from fpgen import userOptions

from time import gmtime, strftime

uopt = userOptions()

# 20140214 bugfix: handle mixed quotes in toc entry
#          added level='3' to headings for subsections
# 20140216 lg.center to allow mt/b decimal value
# 20140217 windows path bugfix; rend=block propogate error
# 20140220 switch mobi generator from ebook-convert to kindlegen
# 20140221 changes to OPT_PDF_ARGS
# 20140226 allows specifying .8em in addition to 0.8em margins
# 20140228 --disable-remove-fake-margins added to PDF and mobi
# 20140304 TESTING. wide spaces as nbsp. mobi from epub.
# 20140307 TESTING for Ross. XP compatibile build test.
# 20140316 added lg rend='right'
# 4.04     bugfix. illustration links. kindle added to !t.
#          --level1-toc "//h:h1" --level2-toc "//h:h2" added for epub
#          <br> in heading handled in text
# 4.05/6   epub margin user option. Alex's "nobreak" option
# 4.07     fractional thought breaks
# 4.08     overline <ol>line over text</ol>
# 4.09     tags in <lit> blocks
# 4.10     alternate comment form "//"
# 4.11     <br><br> converts to "—" in tablet versions
# 4.12     meta line restrictions imposed for PGC
# 4.13     <hang> tag (alex)
# 4.14     allow <pn=''> anywhere on line
# 4.15     used &ensp; instead of &nbsp; as leader for indented poetry lines
# 4.16     drop cap property to use an image
# 4.17     pagenum->pageno, so not part of copy/paste
# 4.17A    <l rend='right'> now works like <l rend='mr:0'>
# 4.17B    level 4 headers
# 4.17C    Error msg for word >75 chars; error msg for text output table w/o width
# 4.18     Use nbsp instead of ensp for ellipsis
# 4.19     Uppercase <sc> output for text; add sc=titlecase option
# 4.19a    Various text output table width bug fixes
# 4.20     Add <table> line drawing in text and html both
# 4.20a    Add <table> double-lines & column <span>ing
# 4.20b    text table bug fix
# 4.20c    empty line produce bars in text; spanned cols in html end in correct border
# 4.20d    table rule lines throw off count; add cell alignment
# 4.20e    Minor bug fix with trailing spaces in text output
# 4.21     Leading \<sp> not in <lg> is nbsp; also unicode nbsp(0xA0)
# 4.21a    Bug with level 4 headers
# 4.22     Text footnote output change to [#] same line
# 4.23     <drama> tag
# 4.23a    Fix bug from 4.22: <lg> starting a footnote (text output)
# 4.23b    Fix bug with gesperrt inside <sc>
# 4.23c    Fix pn_cover usage broken in 4.23
# 4.23d    Fix .verse-align-noindent with hang
# 4.23e    Fix implicit speech recognition in text
# 4.23f    Give error if <fs:xx> value is not matched
# 4.24     Remove special unicode spaces from text formatting input
# 4.24a    french-with-typographic-spaces option added
# 4.24b    unicode space tags
# 4.25     <l> uses proper option parser with errors
# 4.25a    Multiple <link> or <target> on the same line fixed
# 4.25b    Fix multiple <fn id='#"> same id for reverse at the first
# 4.26     Add <summary> tag
# 4.26a    Fixes to text table widths: non-spacing chars & align
# 4.27     Add hang column for table; flushleft
# 4.27a    text table widths: use any specified width
# 4.27b    Vertical alignment for table; hang column for text table
# 4.28     <col=#> for table
# 4.28a    New column pattern S for preserve spaces
# 4.29     Adds sidenotes; html table style as class; hang bug fixes
# 4.29a    Fixes <tb> tag inside <lg> for text output
VERSION="4.29a"

NOW = strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " GMT"
LINE_WIDTH = 72
debug = 0
FORMATTED_PREFIX = "▹"
pn_cover = ""
