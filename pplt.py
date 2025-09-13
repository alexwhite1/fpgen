import language_tool_python
import ssl
import argparse

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


# Rules outside the proffing purview
IGNORE=[]
IGNORE.append('A_TRIP_TO')                           # a trip in -> a trip to
IGNORE.append('ABSORB_AT_IN')                        # absorbed at -> absorbed in; absorbed with; absorbed into
IGNORE.append('ACCOMPANY_WITH')                      # accompanied with -> accompanied by
IGNORE.append('ADJECTIVE_ADVERB')                    # fresh -> freshly
IGNORE.append('ADJECTIVE_IN_ATTRIBUTE')              # yellow in colour -> yellow
IGNORE.append('ADVERB_WORD_ORDER')                   # always I am happy -> I am always happy
IGNORE.append('AFTERWARDS_US')                       # 
IGNORE.append('ALL_OF_THE')                          # all of the -> all the
IGNORE.append('ALL_MOST_SOME_OF_NOUN')               # all of laughter -> all laughter, all of the laughter
IGNORE.append('AND_BUT')                             # remove and or but
IGNORE.append('ANY_MORE')                            # just on eleven o’clock -> just at eleven o’clock
IGNORE.append('APARTMENT-FLAT')                      # apartment -> flat
IGNORE.append('ARTICLE_ADJECTIVE_OF')                # Use a noun, not an adjective, between ‘the’ and ‘of’
IGNORE.append('AS_IS_VBG')                           # It appears that a pronoun is missing
IGNORE.append('ASK_NO_PREPOSITION')                  # tell to me -> tell me
IGNORE.append('ASK_THE_QUESTION')                    # ask the question -> ask
IGNORE.append('ASSOCIATE_TOGETHER')                  # associated together -> associate
IGNORE.append('AT_TIME')                             # ask the question -> ask
IGNORE.append('BALD-HEADED')                         # bald headed -> bald
IGNORE.append('BECAUSE_OF_THE_FACT_THAT')            # because of the fact that -> because
IGNORE.append('BEEN_PART_AGREEMENT')                 # suppose -> supposed, or supposing
IGNORE.append('BESTEST')                             # bestest -> best
IGNORE.append('BOTH_AS_WELL_AS')                     # as well as -> and
IGNORE.append('BRING_AT_TO')                         # brought it at -> brought it to
IGNORE.append('BROUGHT_THEM_IN_THE_AIRPORT')         # brought them in the airport -> brought them to the airport

IGNORE.append('CA_BRAND_NEW')                        # brand new -> brnad-new
IGNORE.append('CLOSE_SCRUTINY')                      # within close proximity to -> close to
#IGNORE.append('COMMA_AFTER_A_MONTH')                 # October, 1958 -> October 1958
#IGNORE.append('COMMA_COMPOUND_SENTENCE')             # 
#IGNORE.append('COMMA_COMPOUND_SENTENCE_2')           #
#IGNORE.append('COMMA_COMPOUND_SENTENCE_4')           # It's great but can't you further improve it? -> It's great but, can't you further improve it?
#IGNORE.append('COMMA_PARENTHESIS_WHITESPACE')        # We had coffee , cheese and crackers and grapes -> We had coffee, cheese and crackers and grapes
#IGNORE.append('COMMA_TAG_QUESTION')                  # She isn't coming is she? -> She isn't coming, is she?
IGNORE.append('CONCENTRATE_WITH_ON')                 # concentrated upon -> The usual preposition for “concentrate” is “on”, “in”, or “at”, not “upon”.
IGNORE.append('CONFUSION_OF_ME_I')                   # Tim and me -> Tim and I
IGNORE.append('CONSEQUENCES_OF_FOR')                 # consequence to -> consequence of; consequence for; consequence on
IGNORE.append('CRAVE_FOR')                           # crave for -> crave
IGNORE.append('DAT')                                 # dat -> that
IGNORE.append('DE_THE')                              # He is one of de best. -> He is one of the best.
IGNORE.append('DESCEND_DOWN')                        # descend down the back stairs -> descend the back stairs
IGNORE.append('DID_YOU_HAVE_VBN')                    # Did you mean to use the past perfect tense, or the simple past?
IGNORE.append('DIS')                                 # dis -> this
IGNORE.append('DISAPPOINTED_OF')                     # disappointed of -> disappointed with, disappointed at, disappointed by
IGNORE.append('DOUBLE_NEGATIVE')                     # sentence contains a double negative
IGNORE.append('DROP_DOWN')                           # drop down -> drop
IGNORE.append('DUNNO')                               # dunno -> don't know

IGNORE.append('EACH_AND_EVERY')                      # each and every one -> each one
IGNORE.append('EN_UNPAIRED_QUOTES')                  # missing quote, but shows up when speaker does multiple paragraphs
IGNORE.append('ENGLISH_WORD_REPEAT_BEGINNING_RULE')  # multiple sentences in a row start with the same word
IGNORE.append('EVERY_NOW_AND_THEN')                  # Every now and then -> Sometimes, Occasionally, Sporatically
IGNORE.append('EXCEPTION_OF_TO')                     # exception of -> exception to
IGNORE.append('EXCITED_FOR')                         # excited at -> excited about
IGNORE.append('EXTREME_ADJECTIVES')                  # He is extremely angry -> He is furious
IGNORE.append('FILL_OF_WITH')                        # filled a page of - > filled a page with
#IGNORE.append('FINAL_ADVERB_COMMA')                  # It could work maybe. -> It could work, maybe.
IGNORE.append('FIRST_OF_ALL')                        # First of all -> First, Firstly, Foremost
IGNORE.append('FOLLOW_A_COURSE')                     # follow the course -> take the courses
IGNORE.append('FULL_WITH_OF')                        # full with -> full of
IGNORE.append('GATHER_UP')                           # gather up the documentation -> gather the documentation
IGNORE.append('GENERAL_XX')                          # general public -> public
IGNORE.append('GIMME')                               # gimme -> give me
IGNORE.append('GIT_GET')                             # git -> get
IGNORE.append('GONNA')                               # Gonna -> Going to
IGNORE.append('GOTTA')                               # Gotta go -> I've got to go
IGNORE.append('GOT_GOTTEN')                          # gotten -> got

IGNORE.append('HAND_AND_HAND')                       # hand and hand -> hand in hand
IGNORE.append('HAVE_A_LOOK')                         #
IGNORE.append('HAVE_A_SHOWER')                       #
IGNORE.append('I_NEVER_HAVE_BEEN')                   # I never have been -> I have never been
#IGNORE.append('IF_WE_CANT_COMMA')                    # If it wasn't it is now! -> If it wasn't, it is now!
IGNORE.append('IF_WOULD_HAVE_VBN')                   # would have brought -> had brought
IGNORE.append('IN_A_X_MANNER')                       # He did it in a hasty manner. -> He did it in a hastily.
IGNORE.append('IN_A_ISLAND')                         # in the island -> on the island
IGNORE.append('IN_FROM_THE_PERSPECTIVE')             # in the fair perspective -> from the fair perspective
IGNORE.append('IN_THE_INTERNET')                     # in the web -> on the web
IGNORE.append('IN_THIS_MOMENT')                      # in that moment -> at that moment
IGNORE.append('INSPIRED_WITH')                       # inspired with -> inspired by
IGNORE.append('INTERESTED_BY')                       # interested by -> interested in
IGNORE.append('IT_IS_SURE')                          # it is sure -> it is certain
IGNORE.append('KIND_OF_A')                           # What kind of a man is Bush? -> What kind of man is Bush?
IGNORE.append('LARGE_NUMBER_OF')                     # A large number of people -> Many people
IGNORE.append('LEMME')                               # lemme -> let me
IGNORE.append('LIGATURES')                           # contains a ligature (joined words)
IGNORE.append('LUNCH_ROOM')                          # lunchroom -> cafeteria

IGNORE.append('MIGHT_PERHAPS')                       # might possibly -> might, perhaps
#IGNORE.append('MISSING_COMMA_AFTER_INTRODUCTORY_PHRASE')  # or years I have been travelling. -> or years, I have been travelling.
IGNORE.append('MISSING_TO_BEFORE_A_VERB')            # need be -> need to be
IGNORE.append('MODAL_OF')                            # Might of -> Might have; Might've
IGNORE.append('MONTH_OF_XXXX')                       # February of 1995 -> February 1995
IGNORE.append('MORE_EASY_N_CLEAR')                   # is more easy than -> is easier than
#IGNORE.append('MORFOLOGIK_RULE_EN_GB')               # 
#IGNORE.append('MORFOLOGIK_RULE_EN_US')               #
IGNORE.append('NEEDNT_TO_DO_AND_DONT_NEED_DO')       # to fear -> fear
IGNORE.append('NEITHER_NOR')                         # Use “nor” with neither.
#IGNORE.append('NO_COMMA_BEFORE_INDIRECT_QUESTION')   # I asked Tom, where he lives. -> I asked Tom where he lives.
#IGNORE.append('NO_COMMA_BEFORE_SO')                  # Carl studied hard, so he -> Carl studied hard so he
IGNORE.append('NONE_THE_LESS')                       # none the less -> nonetheless
IGNORE.append('NOUN_AROUND_IT')                      # the protesters around him -> the surrounding protesters
IGNORE.append('OF_ANY_OF')                           # of any of -> of
IGNORE.append('ON_IN_THE_AFTERNOON')                 # On the afternoon -> In the afternoon
IGNORE.append('OUTSIDE_OF')                          # outside of -> outside
IGNORE.append('OXFORD_SPELLING_Z_NOT_S')             # 

IGNORE.append('PAST_EXPERIENCE_MEMORY')              # past experience -> experience
IGNORE.append('PERS_PRONOUN_AGREEMENT')              # I is at -> I am at
IGNORE.append('POSSIBILTY_POSSIBLE')                 # Before ‘possible’, use a word such as “chance” or “opportunity”.
IGNORE.append('PRP_JJ')                              # A verb may be missing after “he”.
#IGNORE.append('PRP_COMMA')                           # with you I can -> with you, I can
IGNORE.append('PRP_PAST_PART')                       # A verb (‘be’ or ‘have’) is missing before the past participle.
IGNORE.append('PRP_VBG')                             # You going -> Are you going; You are going
IGNORE.append('RETURN_IN_THE')                       # returned in -> returned to
IGNORE.append('RIGHT_OVER')                          # right over there -> over there
IGNORE.append('SENT_START_ARE_NOT_ARENT_FORMAL')     # Are not you the cause -> Aren't you the cause 
#IGNORE.append('SENT_START_CONJUNCTIVE_LINKING_ADVERB_COMMA')  # Nonetheless you should -> Nonetheless, you should 
IGNORE.append('SHORT_COMPARATIVES')                  # a more old lady -> an older lady
IGNORE.append('SO_AS_TO')                            # so as to -> to
IGNORE.append('SUBJECT_DROP')                        # She caught his meaning and she could feel -> She caught his meaning and could feel
IGNORE.append('SUBJECT_MATTER')                      # What is the subject matter -> What is the subject
IGNORE.append('SUBSEQUENT_TO')                       # subsequent to -> after
IGNORE.append('SUFFER_OF_WITH')                      # suffering of -> suffering from; suffering with
IGNORE.append('SUMMER_TIME')                         # summer time -> summer
IGNORE.append('SUMMON_AT_TO')                        # summoned at an examination -> summoned to an examination

IGNORE.append('THE_FALL_SEASON')                     # the fall season -> fall
IGNORE.append('THE_MOST')                            # most -> the most
IGNORE.append('THE_SUPERLATIVE')                     # Kyoto is an oldest city -> Kyoto is the oldest city
IGNORE.append('THERE_MISSING_VERB')                  # 
IGNORE.append('THERE_S_MANY')                        # There’s laws -> There are laws 
IGNORE.append('TOO_EITHER')                          # For negated sentences, use “either” instead of ‘too’.
#IGNORE.append('UPPERCASE_SENTENCE_START')            # it was built in 1950. -> It was built in 1950.
IGNORE.append('VERY_UNIQUE')                         # very unique -> unique
IGNORE.append('WANNA')                               # wanna -> want to
#IGNORE.append('WHETHER')                             # whether -> weather
IGNORE.append('WHITESPACE_RULE')                     # whitespace repetition
IGNORE.append('WHOLE_LOT')                           # read a whole lot -> read a lot
IGNORE.append('WITH_THE_EXCEPTION_OF')               # With the exception of Bob -> Except fpr Bob
IGNORE.append('WORRY_FOR')                           # Don't worry for -> Don't worry about
#IGNORE.append('WORTH_WHILE')                         # It was a worth while endeavor -> It was a worthwhile endeavor


HIGH_LIGHT=[]
HIGH_LIGHT.append('ACCESS_EXCESS')                 # We need excess to the sheet -> We need access to the sheet
HIGH_LIGHT.append('DT_RB_IN')                      # adverb instead of noun: the functionally in place -> the functionality in place
HIGH_LIGHT.append('EG_SPACE')                      # e. g. -> e.g.
HIGH_LIGHT.append('EMIGRATE_IMMIGRATE_CONFUSION')  # immigrate to, emigrate from
HIGH_LIGHT.append('EN_MULTITOKEN_SPELLING_THREE')  # Ossama Bin Laden -> Osama bin Laden
HIGH_LIGHT.append('INCORRECT_CONTRACTIONS')        # do'nt -> don't
HIGH_LIGHT.append('LESS_MORE_THEN')                # then -> than
HIGH_LIGHT.append('PUBIC_X')                       # pubic -> public
HIGH_LIGHT.append('QUESTION_MARK')                 # sentence may need a question mark


##########
# Read file and split into paragrpahs
##########
def add_rule_to_ignore(doc, double, single, rule):
    a=doc.count(double)
    b=doc.count(double.capitalize())
    if a+b>0:
        a=doc.count(single)
        b=doc.count(single.capitalize())
        if a+b==0:
            IGNORE.append(rule)


##########
# Read file and split into paragrpahs
##########
def add_rules_to_ignore_based_on_usage(doc):
    add_rule_to_ignore(doc, 'worth while', 'worthwhile', 'WORTH_WHILE')
    add_rule_to_ignore(doc, 'short cut',   'shortcut',   'SHORT_CUT')
    add_rule_to_ignore(doc, 'near by',     'nearby',     'NEAR_BY')


##########
# Read file and split into paragrpahs
##########
def get_file_paragraphs(args):
    with open(args.filename, 'r', encoding='utf-8') as file:
        doc=file.read()
        file.close()

    # Remove italics
    doc=doc.replace('_', '')

    add_rules_to_ignore_based_on_usage(doc)

    # Language tool does not like spaced ellipses
    doc=doc.replace('. . . .', '....')
    doc=doc.replace('. . .', '...')

    # Remove leading spaces from lines
    while True:
        doc=doc.replace('\n ', '\n')
        if doc.count(   '\n ')==0:
            break

    # Remove trailing spaces from lines
    while True:
        doc=doc.replace(' \n','\n')
        if doc.count(   ' \n')==0:
            break

    # Remove blank lines
    while True:
        doc=doc.replace('\n\n\n', '\n\n')
        if doc.count(   '\n\n\n')==0:
            break

    # Temporary marker for paragraph break
    PP='<^>'

    # Replace paragraph breaks
    doc=doc.replace('\n\n',   PP)

    # Remove rest of carriage returns
    doc=doc.replace('\n', ' ')

    # Return the paragraphs
    return doc.split(PP)


##########
# Convert boolean option to boolean value
##########
def convert_option( option):
    if 'T' in option:
       return True
    else:
       return False


##########
# Start a session with the language tool server
##########
def get_language_tool(args):
    cache=convert_option(args.cache)

    if cache:
        return language_tool_python.LanguageTool(args.language, config={'cacheSize': 1000, 'pipelineCaching': True})

    return language_tool_python.LanguageTool(args.language)


##########
# March through paragraphs, finding specified rules
##########
def language_tool_find(args, rules ):

    match_count=0
    pp_count=0
    print_count=0

    # Read file before starting language tool
    paragraphs=get_file_paragraphs(args)

    # Get language tool
    lt=get_language_tool(args)

    for paragraph in paragraphs:
        pp_count+=1

        # See if there are any issues at all
        matches = lt.check(paragraph)
        if len(matches)==0:
            # Nothing to do, go to next paragraph
            continue

        # March through the matches
        output_header=True
        match_count+=len(matches)
        for match in matches:
            if match.ruleId in rules:

                print_count+=1

                # Output header for this paragraph 
                if output_header:
                    print(f'{print_count}. Paragraph:{pp_count}')
                    print(f'  {paragraph}')
                    print('')
                    output_header=False

                print('  Category:', match.category, '  Rule Issue:', match.ruleIssueType)
                print('  ', match)

    print('')
    print('Total matches in file:', match_count)
    print('Total matches printed:', print_count)

    lt.close()


##########
# March through paragraphs, skipping specified rules
##########
def language_tool_skip(args):

    match_count=0
    pp_count=0
    print_count=0

    skip_comma      =convert_option(args.comma)
    skip_compound   =convert_option(args.compound)
    skip_diacritic  =convert_option(args.diacritic)
    skip_hyphen     =convert_option(args.hyphen)
    skip_ignore     =convert_option(args.ignore)
    skip_punctuation=convert_option(args.punctuation)
    skip_spelling   =convert_option(args.spelling)

    # Read file before starting language tool
    paragraphs=get_file_paragraphs(args)

    # Get language tool
    lt=get_language_tool(args)

    for paragraph in paragraphs:
        pp_count+=1

        # See if there are any issues at all
        matches = lt.check(paragraph)
        if len(matches)==0:
            # Nothing to do, go to next paragraph
            continue

        # March through the matches
        output_header=True
        match_count+=len(matches)
        for match in matches:
            if match.category=='COLLOCATIONS':
                # e.g. AT_THE_JOB: at the job -> on the job
                continue
            if match.category=='BRITISH_ENGLISH':
                if match.ruleIssueType=='locale-violation':
                    # e.g. GROUND_FIRST_FLOOR: ground floor -> first floor
                    continue
            if match.category=='AMERICAN_ENGLISH':
                if match.ruleIssueType=='locale-violation':
                    # e.g. TAKE_A_BATH: take a bath -> have a bath
                    continue
            if match.ruleIssueType=='style':
                if match.category=='REDUNDANCY':
                    # e.g. WHETHER: the question whether -> whether
                    continue
                if match.category=='STYLE':
                    # e.g. FOR_EVER_GB: for ever -> forever
                    continue
                if match.category=='AMERICAN_ENGLISH_STYLE':
                    # e.g. FOR_EVER_GB: for ever -> forever
                    continue
            if match.ruleId in IGNORE:
                if skip_ignore:
                    continue
            if '_SIMPLE_REPLACE_' in match.ruleId:
                # e.g. EN_GB_SIMPLE_REPLACE_TURNPIKE, EN_US_SIMPLE_REPLACE_LORRY 
                continue
            if 'COMMA' in match.ruleId:
                # e.g. GOD_COMMA, MISSING_COMMA_WITH_TOO
                if skip_comma:
                    continue
            if 'COMPOUND' in match.ruleId:
                # e.g. EN_COMPOUNDS_DOUBLE_SPACED, EN_COMPOUNDS_OLD_FASHIONED, RECOMMENDED_COMPOUNDS
                # e.g. CAR_POOL_COMPOUND
                if skip_compound:
                    continue
            if 'DIACRITIC' in match.ruleId:
                # e.g. 
                if skip_diacritic:
                    continue
            if 'HYPHEN' in match.ruleId:
                # e.g. UP_AND_COMING_HYPHEN, ROLL_OUT_HYPHEN, MISSING_HYPHEN
                if skip_hyphen:
                    continue
            if 'UPPERCASE_SENTENCE_START' in match.ruleId:
                if skip_punctuation:
                    continue
            if 'THE_PUNCT' in match.ruleId:
                if skip_punctuation:
                    continue
            if 'FR_SPELLING_RULE' in match.ruleId:
                if skip_spelling:
                    continue
            if 'GERMAN_SPELLER_RULE' in match.ruleId:
                if skip_spelling:
                    continue
            if 'MORFOLOGIK_RULE_EN' in match.ruleId:
                # e.g. MORFOLOGIK_RULE_EN_GB and MORFOLOGIK_RULE_EN_US
                if skip_spelling:
                    continue

            print_count+=1

            # Output header for this paragraph 
            if output_header:
                print(f'{print_count}. Paragraph:{pp_count}')
                print(f'  {paragraph}')
                print('')
                output_header=False

            print('  Category:', match.category, '  Rule Issue:', match.ruleIssueType)
            print('  ', match)

    print('')
    print('Total matches in file:', match_count)
    print('Total matches printed:', print_count)

    lt.close()



##########
# Get program arguments
##########
def get_args():

    PROGRAM_NAME='python3 pplt.py'
    PROGRAM_DESCRIPTION='''This program is a thin front end calling the python language tool library
                           which has 6000+ rules for flagging potential documentation issues.
                           Each paragraph in the file will be passed to the language tool server and
                           a list of rules (i.e. potential issues) returned that need to be investigated.
                           By default, the program will ignore rules outside the proofing purview,
                           which can be tweaked using the different boolean-based options.
                           Other options allow you to add to the rules to ignore using the
                           -e option, or limit the display to a list of particular rules using
                           the -f option. 
                           '''
    PROGRAM_EPILOG='''Note that the language tool was primarily developed for creating a new document
                      rather than proofing a published document. Hence, the majority of the rules will
                      not be actionable. There has been roughly, on average, for a book containing
                      \'proper\' language, one potential issue per book.
                      However, most books have no potential issues with the rest having single digit
                      potential issues.
                      '''

    # Required options
    FILENAME_HELP='Name of text file containing the PP book'
    LANGUAGE_HELP='''Set of language rules to use: de (German), en (English), fr (French).
                     With different variants for spell checking:
                     AT (Austria), AU (Australia), BE (Belgium),
                     CA (Canada), CH (Switzerland), DE (German),
                     GB (Great Britain), NZ (New Zealand),
                     US (United States), ZA (South Africa)
                     '''

    EXTRA_HELP   ='Name of text file containing extra language-tool rules to ignore (see pplt_example.txt)'

    # Optional options
    CACHE_HELP      ='Speed up processing for multiple runs'
    COMMA_HELP      ='Skip rules containing \'COMMA\' (e.g. COMMA_AFTER_A_MONTH)'
    COMPOUND_HELP   ='Skip rules containing \'COMPOUND\' (e.g. CAR_POOL_COMPOUND)'
    DIACRITIC_HELP  ='Skip rules containing \'DIACRITIC\' (e.g. )'
    HYPHEN_HELP     ='Skip rules containing \'HYPHEN\' (e.g. MISSING_HYPHEN)'
    IGNORE_HELP     ='Skip rules in hard-coded array  (e.g. rule \'GIMME\' suggests \'gimme\' be changed to \'give me\')'
    PUNCTUATION_HELP='Skip rules related to lower case word after period (e.g UPPERCASE_SENTENCE_START, )'
    SPELLING_HELP   ='Skip rules related to spelling (e.g., MORFOLOGIK_RULE_EN_GB and MORFOLOGIK_RULE_EN_US)'

    FIND_HELP    ='Name of text file containing rules to display (see pplt_example.txt)'
    VERBOSE_HELP ='Show details: operation, language-tool rules'

    BOOLEAN_CHOICES=['True', 'T', 'False', 'F']
    LANGUAGE_CHOICES=['de', 'de-AT', 'de-DE', 'de-CH', 'en', 'en-AU', 'en-CA', 'en-GB', 'en-NZ', 'en-US', 'en-ZA', 'fr', 'fr-BE', 'fr-CA']

    parser=argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_DESCRIPTION, epilog=PROGRAM_EPILOG, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename',                                                                   help=FILENAME_HELP)
    parser.add_argument('-l', '--language',    choices=LANGUAGE_CHOICES,      required=True,          help=LANGUAGE_HELP)
    parser.add_argument('-e', '--extra',       action='store',      type=str, default='none',         help=EXTRA_HELP)
    parser.add_argument('-c', '--comma',       choices=BOOLEAN_CHOICES,       default='True',         help=COMMA_HELP)
    parser.add_argument('-d', '--diacritic',   choices=BOOLEAN_CHOICES,       default='False',        help=DIACRITIC_HELP)
    parser.add_argument('-i', '--ignore',      choices=BOOLEAN_CHOICES,       default='True',         help=IGNORE_HELP)
    parser.add_argument('-k', '--compound',    choices=BOOLEAN_CHOICES,       default='True',         help=COMPOUND_HELP)
    parser.add_argument('-p', '--punctuation', choices=BOOLEAN_CHOICES,       default='True',         help=PUNCTUATION_HELP)
    parser.add_argument('-s', '--spelling',    choices=BOOLEAN_CHOICES,       default='True',         help=SPELLING_HELP)
    parser.add_argument('-y', '--hyphen',      choices=BOOLEAN_CHOICES,       default='True',         help=HYPHEN_HELP)
    parser.add_argument(      '--cache',       choices=BOOLEAN_CHOICES,       default='False',        help=CACHE_HELP)
    parser.add_argument('-f', '--find',        action='store',      type=str, default='none',         help=FIND_HELP)
    parser.add_argument('-v', '--verbose',     action='store_true',           default='store_false',  help=VERBOSE_HELP)

    args=parser.parse_args()
    if args.verbose==True:
        print('args.filename:   ', args.filename)
        print('args.language:   ', args.language)
        print('args.extra:      ', args.extra)
        print('args.comma:      ', args.comma)
        print('args.diacritic:  ', args.diacritic)
        print('args.ignore:     ', args.ignore)
        print('args.compound:   ', args.compound)
        print('args.punctuation:', args.punctuation)
        print('args.spelling:   ', args.spelling)
        print('args.hyphen:     ', args.hyphen)
        print('args.cache:      ', args.cache)
        print('args.find:       ', args.find)
        print('args.verbose:    ', args.verbose)

    return args


##########
# Read file containing LT rules
##########
def get_file_rules(filename):
    # Read in all the lines
    with open(filename, 'r') as file:
        lines = file.readlines()
        file.close()

    # Extract all the rules; ignoring possible comments
    rules=[]
    for line in lines:
        words=line.split()
        if len(words)>0:
            rules.append(words[0])

    return rules


##########
# MAIN
##########

# Get program arguments
args = get_args()

# Find rules specified by user file
if args.find!='none':
    find_rules=get_file_rules(args.find)
    if args.verbose==True:
        print('Looking the following rules specified by the user:')
        print('    ', find_rules)
        print('')
    language_tool_find(args, find_rules)
    exit()

# Add on any user specified rules to ignore
if args.extra!='none':
    extra_rules=get_file_rules(args.extra)
    if args.verbose==True:
        print('Extra ignore rules to ignore:')
        print('    ', extra_rules)
        print('')
    IGNORE.extend(extra_rules)

if args.verbose==True:
    print('Ignoring the following rules:')
    print('    ', IGNORE)
    print('')

language_tool_skip(args)

