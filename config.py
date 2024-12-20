from userOptions import userOptions

from time import gmtime, strftime

#uopt = userOptions()

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
# 4.30     Adds <pstyle=hang>; patternhtml/text; hang:#px
# 4.30a    Fixes text table measurement by including all combining diacriticals
# 4.30b    Fixes <l rend='center'> to break and center
# 4.30c    .meta information: add tags; fix display title; add generator
# 4.31     Adds --ebookid flag to create fadedpage zip file
# 4.31a    Fix more french-with-typo cases; extend lint to <l>&<heading>; fix trace at end of file
# 4.31b    Proper error with unmatched <lg>
# 4.31c    Break and center headers correctly in text output
# 4.31d    Emit level 1 headers before page number in non-html
# 4.31e    Fix display title; duplicated generator & publisher
# 4.32     Allow text tables to be wider
# 4.32a    Error on non-terminated caption & sidenote
# 4.33     <l rend='poetry'> adds new align-last option
# 4.33a    Enhance unbalanced msgs inside linegroup
# 4.33b    Add drop-text-X property for text drop-cap substitution
# 4.34     triple alignment option; text:hidden rend option to tb
# 4.35     Add occupy: option to rend in <illustration>
# 4.35a    Break summary lines on em-dash
# 4.35b    Warning on <sc> of uppercase; Fix sidenote visibility
# 4.35c    Fix alignment override on hang column in text output
# 4.35d    Table css generation interaction with calibre fix
# 4.36     Add <index> tag
# 4.36a    Allow arbitrary spaces in <fn and <footnote
# 4.37     Templates; macro/lit ordering bug fix; lg/l fontsize ordering bug fix
# 4.37a    <illustration>&<tb>: use common parsing; <chap-head>&<sub-head>
# 4.37b    &amp; in meta; change syntax for id in headers to fix warning
# 4.37c    text: give error when extra </quote>
# 4.37d    text: Fix <lit> to not convert backslash-space
# 4.37e    Fix 4.37: Don't try to expand a macro starting with space
# 4.37f    Fix <footnote id='#'> broken recently
# 4.37g    Rewrite <link> and <target> using new parsing methods
# 4.37h    Fix comment on line following multi-line comment
# 4.38     Relocate footnote options
# 4.38a    Enclose footnotes in div with class footnote
# 4.39     Add embedded sidenote-style option
# 4.40     Add <multicol> tag
# 4.40a    Rewrite <lg> using new parsing methods
# 4.40b    Add break='no' tag to <chap-head>
# 4.40c    Expose poetry-style option
# 4.41     Add type='book' to <chap-head>
# 4.41a    Parse <meta> tags correctly
# 4.41b    Add summary-style indent
# 4.42     Add fontsizes to <table> & new parsing methods
# 4.42a    Error when too many nested <quote> in text
# 4.42b    <align=h> for table cell hang
# 4.42c    Fix tdStyle when multiple formats are generated
# 4.42d    Fix multiple footnote reference test
# 4.43     New <lg rend='block-right'> and <quote rend='right w:XX%'>
# 4.43a    Fix 4.42d: broke footnote asterisk style
# 4.43b    Allow fn/footnote id tags to be special characters, e.g. *, dagger
# 4.43c    <if> for kindle works again; --ebookid allow years prior to 2010
# 4.43d    Missing TOC for pdf output
# 4.43e    page-break-after:avoid for h3, h4, footnotemark
# 4.44     Add leaders to table cells
# 4.44a    Fix leaders for firefox
# 4.44b    Rewrite paragraph recognition; many para starts being lost
# 4.44c    Observe font changes specified by <lg rend=''> in text output
# 4.45     Add footnote-style, with new paragraph style
# 4.45a    <index>: don't justify, handle indentation
# 4.45b    Rewrite the html poetry code to keep stanza on a page & not truncate
# 4.45c    Fixup error msgs in arg parsing code; find file automatically
# 4.45d    Add page-break-inside:avoid to centered figures
# 4.45e    Fix various <l> and <lg> related bugs in text output
# 4.46     Add summary-style center and add footnote-style sidenote
# 4.46a    Better errors for <heading>
# 4.47     Rewrite paragraph styles; introduce list style
# 4.47a    Remove leading quote in <drop> without property
# 4.47b    Move dropcap css from style to class
# 4.47c    Handle missing comment close with an error message, not stacktrace
# 4.48     Add custom font support
# 4.48a    Fix PDF margins broken by calibre 2.83
# 4.48b    Fix PDF margins in gen.py as well
# 4.48c    Add drop-width; cycles in drop-X
# 4.49     Rewrite drop-cap code to allow src&rend
# 4.50     Drop-cap slicing
# 4.51     Illustration slicing, preserve-margins option
# 4.52     <shy>, couple of minor bugs
# 4.53     embeddedcaption in <illustration>
# 4.54     Add property font-XXX-class
# 4.54a    font-XXX-class had a bug.
# 4.54b    table column width rounding; warning suppression
# 4.54c    page-break-inside: avoid for tables
# 4.54d    option preserve-line-height
# 4.54e    fix option bug: options preserved over multiple formats
# 4.54f    add option sidenote-breaks-paragraphs, default true
# 4.54g    fix 4.54f: sidenote break broke other cases
# 4.54h    Unknown macro names no longer fatal, in case just two % signs
# 4.55     Add <pnprefix='XX'> for multiple books
# 4.55a    Fix <br> in filled table cell for text output
# 4.55b    Disable sandbagging if caption except for html
# 4.55c    Emit a page-break before emitting title in <chap-head>
# 4.56     Add url= attribute to <link>
# 4.56a    Fix inconsistent behaviour when multiple downloaded fonts
# 4.56b    @media subsitute for gen only
# 4.56c    Illustration looks for -omit file
# 4.56d    Multi-line sidenote caused break in text output
# 4.56e    special substitution for <ol> replaced with private use area
# 4.57     Add ability to use an image for a thought break
# 4.57a    Fix last rev
# 4.57b    Add dropcap class to dropcap images
# 4.57c    triple: handle zero length center better
# 4.58     Add <ditto> tag; add <figsp>
# 4.58a    Use hard spaces to align <ditto> in txt output
# 4.58b    Another tweak to the illustration omission code
# 4.59     Add drop-after property for automatic drop caps
# 4.60     Add <credit> tag within <illustration>
# 4.60a    Error msg when missing alignment in table column pattern
# 4.60b    Fix caption inside <lg> block
# 4.60c    Add curly-single to auto drop caps
# 4.61     Add lead-in-after and pstyle-noindent-after properties
# 4.61a    Refactor paragraph code. No functional changes
# 4.61b    sa and sb on lg should apply to lg only, not each line.
# 4.61c    Triple inside lg produced paragraph break in txt output
# 4.61d    Add version check: fatal if we want newer version
# 4.61e    Disable table leaders on kindle; refactor classes
# 4.61f    Generate different code for triple on kindle
# 4.61g    Disable dropcaps on kindle
# 4.61h    Fix syntax error
# 4.61i    Again, new code for kindle triple; fix triple center to 1/3
# 4.61j    gen.py: Use contains for nobreak in classes
# 4.61k    Add --preserve-cover-aspect-ratio to ebook-convert
# 4.61l    Escape dot for leading .tags
# 4.62     gen: Add fadedpage-toc meta
# 4.62a    Blank line between credit/caption in text output
# 4.62b    Clear float in drop-caps
# 4.63     Add alt tag to <illustration>
# 4.63a    Fix poetry-container css bug
# 4.63b    Fix caption in sliced float
# 4.64     gesperrt in text no longer spaced; treat like italic.
# 4.64a    --ebookid validation for the third decade!
# 4.64b    Generate -k.epub file
# 4.64c    <html> tag use the DC.Language value
# 4.65     Add <alt>...</alt> within <illustration>
# 4.66     Add option toc-levels
# 4.67     Support for python 3.13 (Strings that should be regexs)

VERSION="4.67"

NOW = strftime("%Y-%m-%d %H:%M:%S", gmtime()) + " GMT"

# TEXT: Lines are justified & centered within this number of columns
# NOTE: Not a constant, can be set with a property
LINE_WIDTH = 72

# TEXT: Lines passed through are wrapped at this number of columns.
LINE_WRAP = 75

debug = 0
FORMATTED_PREFIX = "▹"
NO_WRAP_PREFIX = "\u2135"
HARD_SPACE = "□"
pn_cover = ""

# Used for <font:xx>...</font>
# <font:xx> becomes FONT_BASE + font index
# </font> becomes FONT_END
FONT_BASE = 0xEF00
FONT_END = "\uEFFF"

# Lots of special characters currently in use.  Should all be using
# the Private Use Areas, since sooner or later somebody is going to
# try to use the characters in the text.
OL_START = "\uEE00"
OL_END   = "\uEE01"
