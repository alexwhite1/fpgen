import argparse
import re


LEAVE_MARKER='x07'
GOOD_MARKER ='x08'


##########
# Generic output of warnings
##########
def print_warning(part, warning):
    part=part.replace('\n','')
    print(f'Text: \'{part}\'')
    print( '  - Warning: ', warning)


##########
# Tidy the French punctuation so fpgen can insert narrow-no-break spaces
##########
def tidy_punctuation(part, target, target_plus_space, leave, leave_warning):
    if part.count(target)==0:
        # Nothing to do
        return part

    # Sanity check
    if part.count(LEAVE_MARKER)>0:
        print('ERROR: Bell character in line')

    # Output warning regarding leave string
    if part.count(leave)>0:
        print_warning(part, leave_warning)

    # Hide items we do not want to change
    part=part.replace(leave, LEAVE_MARKER)
    
    # Tidy things up (i.e. remove the space)
    part=part.replace(target_plus_space, target)

    # Restore items
    part=part.replace(LEAVE_MARKER, leave)

    # Sanity check
    if part.count(LEAVE_MARKER)>0:
        print('ERROR: Bell character in line')

    return part


##########
# Update the French punctuation with no-break spaces
##########
def update_punctuation(part, target, target_plus_space, leave, good, leave_warning):
    if part.count(target)==0:
        # Nothing to do
        return part

    # Sanity check
    if part.count(LEAVE_MARKER)>0:
        print('ERROR: Bell character in line')
    if part.count(GOOD_MARKER)>0:
        print('ERROR: Backspace character in line')

    # Output warning regarding leave string
    if part.count(leave)>0:
        print_warning(part, leave_warning)

    # Hide items we do not want to change
    part=part.replace(good, GOOD_MARKER)
    part=part.replace(leave, LEAVE_MARKER)

    # Insert no-break spaces
    # target_plus_space must be done first
    part=part.replace(target_plus_space, GOOD_MARKER)
    part=part.replace(target, GOOD_MARKER)

    # Restore items 
    part=part.replace(LEAVE_MARKER, leave)
    part=part.replace(GOOD_MARKER, good)

    # Sanity check
    if part.count(LEAVE_MARKER)>0:
        print('ERROR: Bell character in string')
    if part.count(GOOD_MARKER)>0:
        print('ERROR: Backspace character in string')
    
    return part


##########
# Sanity check for start of line
##########
def check_start_of_line(line, target, warning):
    temp=line.lstrip()
    if temp.startswith(target):
        print_warning(line, warning)


##########
# Sanity check for end of line
##########
def check_end_of_line(line, target, warning):
    if line.count(target):
        print_warning(line, warning)


##########
# March through the file updating the French as needed
##########
def update_french_CA(args):
    with open(args.filename, 'r', encoding='utf-8') as file:
        lines=file.readlines()
        file.close()

    # Needs to be inserted into file so fpgen will do the narrow no-break space insertions
    FPGEN_LINE='<option name=\'french-with-typographic-spaces\' content=\'true\'>\n'

    out= open(args.output, 'w', encoding='utf-8')

    # Deterine if the FPGEN_LINE is already in the file
    add_fpgen=True
    for line in lines:
        if line.count(FPGEN_LINE)>0:
            add_fpgen=False
            break;

    skip=False
    # March through the file, line by line
    for line in lines:
        # Want to skip over the <lit section="head"> section
        # Just write it out lines, no processing
        if line.count('<lit')==1:
            skip=True
        if skip:
            out.write(line)
            if line.count('</lit>')==1:
                skip=False
            continue

        # Insert fpgen line at the start of other html options
        if line.count('<option name=')>0:
            if add_fpgen:
                print('Adding line to file:', FPGEN_LINE, end='')
                out.write(FPGEN_LINE)
                add_fpgen=False

        # Strip off leading white space
        temp=line.lstrip()

        # Remove all the html business
        pattern=re.compile('<.*?>')
        parts=re.split(pattern, temp)

        # Fix up punctuation in each part of the line
        for part in parts:
            new=part

            # Update part so fpgen can do the narrow no-break insertions
            new=tidy_punctuation(new, ';', ' ;', '  ;', 'too many spaces before semicolon')
            new=tidy_punctuation(new, '!', ' !', '  !', 'too many spaces before exclamation point')
            new=tidy_punctuation(new, '?', ' ?', '  ?', 'too many spaces before question mark')

            # Update part with no-break spaces
            new=update_punctuation(new, '«', '« ', '«  ', '«\\ ', 'too many spaces after left guillemet')
            new=update_punctuation(new, '»', ' »', '  »', '\\ »', 'too many spaces before right guilemet')
            new=update_punctuation(new, ':', ' :', '  :', '\\ :', 'too many spaces before colon')
            new=update_punctuation(new, '—', ' —', '  —', '\\ —', 'too many spaces before tiret')
            new=update_punctuation(new, '—', '— ', '—  ', '—\\ ', 'too many spaces after tiret')

            # Insert updated part back into the line
            line=line.replace(part,new)

        # Fix up case where tiret is the first non-white space character in the line
        temp=line.lstrip()
        if temp.startswith('\\ —'):
            line=line.replace('\\ —', '—', 1)

        # Sanity checks
        check_start_of_line(line, ';', 'semicolon at start of line')
        check_start_of_line(line, '!', 'exclamation mark at start of line')
        check_start_of_line(line, '?', 'question mark at start of line')
        check_start_of_line(line, '»', 'right guilemet at start of line')
        check_start_of_line(line, ':', 'colon at start of line')
        check_start_of_line(line, '\\ ', 'no-break space at start of line')

        # Fix up case where tiret is at the end of the line
        line=line.replace('—\\ \n', '—\n')

        # Fix up the case where there are two tirets in a row
        line=line.replace('—\\ —', '—-')

        # Sanity checks
        check_end_of_line(line, ' \n', 'space at end of line')
        check_end_of_line(line, '«\n', 'left guilemet at end of line')
        check_end_of_line(line, '\\ \n', 'no-break space at end of line')

        out.write(line)

    print('Finished writing:', args.output)


##########
# Get program arguments
##########
def output_french_CA_info():
    print('')
    print('List of things this program will, and will not, do')
    print('')
    print('1. Will report the following as a possible issue for fpgen:')
    print('   (i.e. no changes)')
    print('   a. \'<space><space>;\'')
    print('   b. \'<space><space>!\'')
    print('   c. \'<space><space>?\'')
    print('')
    print('2. Update the following to assist fpgen to insert narrow-no-break spaces:')
    print('   (i.e. remove the space)')
    print('   a. \'<text><space>;\' -> \'<text>;\'')
    print('   b. \'<text><space>!\' -> \'<text>!\'')
    print('   c. \'<text><space>?\' -> \'<text>?\'')
    print('')
    print('3. Will report the following:')
    print('   (i.e. no changes)')
    print('   a. \'«<space><space>\'')
    print('   b. \'<space><space>»\'')
    print('   c. \'<space><space>:\'')
    print('   d. \'<space><space>—\'')
    print('   e. \'—<space><space>\'')
    print('')
    print('4. Update the following with a no-break space')
    print('   (i.e. replace space with non-break space)')
    print('   a. \'«<space><text>\' -> \'«<nbsp><text>\'')
    print('   b. \'<text><space>»\' -> \'<text><nbsp>»\'')
    print('   c. \'<text><space>:\' -> \'<text><nbsp>:\'')
    print('   d. \'<text><space>—<space><text>\' -> \'<text><nbsp>—<nbsp><text>\'')
    print('')
    print('5. Insert nobreak space')
    print('   a. \'«<text>\' -> \'«<nbsp><text>\'')
    print('   b. \'<text>»\' -> \'<text><nbsp>»\'')
    print('   c. \'<text>:\' -> \'<text><nbsp>:\'')
    print('   d. \'<text>—<text>\' -> \'<text><nbsp>—<nbsp><text>\'')
    print('')
    print('6. Special handling for the tiret')
    print('   a. No <nbsp> at the start of the line')
    print('   b. No <nbsp> at the end of the line')
    print('   c. remove all <nbsp> between a double tiret')
    print('   d. remove space between a double tiret')
    print('')


##########
# Get program arguments
##########
def get_args():

    PROGRAM_NAME='python3 ppp.py'
    PROGRAM_DESCRIPTION='''This program adds punctuation for non-english languages.
                           It takes as input the file provided to PP after the proofing and formating.
                           For French, this includes: adding non-break spaces for the following: \':\', \'«\', \'»\', and \'—\' (tiret).
                           '''
    # Required options
    FILENAME_HELP='Name of text file containing the PP book'
    LANGUAGE_HELP='Set of language rules to use: fr (French)'
    OUTPUT_HELP  ='Name of output file'
    INFO_HELP    ='The rules followed insert no-break spaces'
    VERBOSE_HELP ='Show details'

    BOOLEAN_CHOICES=['True', 'T', 'False', 'F']
    LANGUAGE_CHOICES=['fr-CA']

    parser=argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_DESCRIPTION, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename',                                                                  help=FILENAME_HELP)
    parser.add_argument('-l', '--language',  choices=LANGUAGE_CHOICES,      required=True,          help=LANGUAGE_HELP)
    parser.add_argument('-o', '--output',    action='store',      type=str, required=True,          help=OUTPUT_HELP)
    parser.add_argument('-v', '--verbose',   action='store_true',           default='store_false',  help=VERBOSE_HELP)
    parser.add_argument(      '--info',      action='store_true',           default='store_false',  help=INFO_HELP)

    args=parser.parse_args()
    if args.verbose==True:
        print('args.filename: ', args.filename)
        print('args.language: ', args.language)
        print('args.output:   ', args.output)
        print('args.info:     ', args.info)
        print('args.verbose:  ', args.verbose)

    return args


##########
# MAIN
##########

# Get program arguments
args = get_args()

if args.language=='fr-CA':
    if args.info==True:
        output_french_CA_info()
        exit()

    update_french_CA(args)
    exit()

print('Language not supported: args.language')

