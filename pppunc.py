import argparse
import re


LEAVE_MARKER='x07'
GOOD_MARKER ='x08'
FORMAT_EMDASH_MARKER ='x0b'
#FORMAT_EMDASH_MARKER ='^'

line_number=0


##########
# Generic output of warnings
##########
def print_warning(part, warning):
    part=part.replace('\n','')
    print(f'Line {line_number}. Text: \'{part}\'')
    print( '  - Warning: ', warning)


##########
# Tidy the French punctuation so fpgen can insert narrow-no-break spaces
##########
def tidy_punctuation(part, target, target_plus_space, target_plus_nbspace, leave, leave_warning):
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
    
    # Tidy things up (i.e. remove the spaces)
    part=part.replace(target_plus_nbspace, target)
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
# Hide more than 1 groups of characters (e.g. format related emdash)
##########
def hide_doubles(line, target, replace, warning):
    src=target+target
    if line.count(src)==0:
        return line

    if line.count(replace)>0:
        print('ERROR: vertical tab character in line')

    # Let the user know we are skipping these chracters
    print_warning(line, warning)

    dst=replace+replace
    line=line.replace(src, dst)
    line=line.replace(replace+target, replace+replace)

    return line


##########
# Restore hidden characters
##########
def restore_doubles(line, target, replace):
    if line.count(target)==0:
        return line
    return line.replace(target,replace)


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
    global line_number
    line_number=0
    for line in lines:
        line_number+=1

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

        # Hide tiret based formatting (i.e. ——)
        # This also includes unspoken names
        line=hide_doubles(line, '—', FORMAT_EMDASH_MARKER, 'tiret formatting will be ignored')

        # Strip off leading white space
        temp=line.lstrip()

        # Remove all the html business
        pattern=re.compile('<.*?>', re.NOFLAG)
        parts=re.split(pattern, temp)

        # Fix up punctuation in each part of the line
        for part in parts:
            new=part

            # Update part with no-break spaces
            new=update_punctuation(new, '«', '« ', '«  ', '«\\ ', 'too many spaces after left guillemet')
            new=update_punctuation(new, '»', ' »', '  »', '\\ »', 'too many spaces before right guilemet')
            new=update_punctuation(new, ':', ' :', '  :', '\\ :', 'too many spaces before colon')
            new=update_punctuation(new, '—', ' —', '  —', '\\ —', 'too many spaces before tiret')
            new=update_punctuation(new, '—', '— ', '—  ', '—\\ ', 'too many spaces after tiret')

            # Update part so fpgen can do the narrow no-break insertions
            # Has to be done after update_punctuation calls
            new=tidy_punctuation(new, ';', ' ;', '\\ ;', '  ;', 'too many spaces before semicolon')
            new=tidy_punctuation(new, '!', ' !', '\\ !', '  !', 'too many spaces before exclamation point')
            new=tidy_punctuation(new, '?', ' ?', '\\ ?', '  ?', 'too many spaces before question mark')

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
        line=line.replace('—\\ —', '——')

        # Restore any tiret based formatting
        line=restore_doubles(line, FORMAT_EMDASH_MARKER, '—')

        # Sanity checks
        check_end_of_line(line, ' \n', 'space at end of line')
        check_end_of_line(line, '«\n', 'left guilemet at end of line')
        check_end_of_line(line, '\\ \n', 'no-break space at end of line')

        out.write(line)

    print('Finished writing:', args.output)


LANGUAGE_CHOICES=['fr-CA']

##########
# Get program arguments
##########
def get_args():

    PROGRAM_NAME='pppunc.py'
    PROGRAM_DESCRIPTION='''This program adds punctuation for non-English languages.
                           It takes as input the file provided to PP after the proofing and formatting.
                           For French, this includes adding non-break spaces for the following:
                           \':\', \'«\', \'»\', and \'—\' (tiret, an em dash).
                           And some fgen preparation by removing any preceding space from the following:
                           \';\', \'?\', \'!\'.
                           '''
    # Required options
    FILENAME_HELP='Name of text file containing the PP book'
    LANGUAGE_HELP='Set of language rules to use: fr-CA (Canadian French)'
    OUTPUT_HELP  ='Name of output file'
    INFO_HELP    ='The rules followed insert no-break spaces'
    VERBOSE_HELP ='Show details'

    BOOLEAN_CHOICES=['True', 'T', 'False', 'F']

    parser=argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_DESCRIPTION)
    parser.add_argument('filename',                                                                 help=FILENAME_HELP)
    parser.add_argument('-l', '--language',  action='store',      type=str, required=True,          help=LANGUAGE_HELP)
    parser.add_argument('-o', '--output',    action='store',      type=str, required=True,          help=OUTPUT_HELP)
    parser.add_argument('-v', '--verbose',   action='store_true',           default='store_false',  help=VERBOSE_HELP)

    args=parser.parse_args()
    if args.verbose==True:
        print('args.filename: ', args.filename)
        print('args.language: ', args.language)
        print('args.output:   ', args.output)
        print('args.verbose:  ', args.verbose)

    return args


##########
# MAIN
##########

# Get program arguments
args = get_args()

if args.language in LANGUAGE_CHOICES:
    update_french_CA(args)
    exit()

print('Language not supported: args.language')
print('Supported languages are:', LANGUAGE_CHOICES)

