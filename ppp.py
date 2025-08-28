import argparse
import re


##########
# Convert boolean option to boolean value
##########
def convert_option( option):
    if 'T' in option:
       return True
    else:
       return False


##########
# Sanity check on input file
##########
def check_file(lines):

    bad_punctuation=[' :', '« ', ' »', ' —', '— ', ' \n', ' ?', ' !', ' ;']

    og =0
    ogb=0
    cg=0
    cgb=0
    ob =0
    cb =0
    os =0
    cs =0

    for line in lines:
        og +=line.count('«')
        ogb+=line.count('«\\ ')
        cg +=line.count('»')
        cgb+=line.count('\\ »')
        ob +=line.count('(')
        cb +=line.count(')')
        os +=line.count('[')
        cs +=line.count(']')
    
    if og!=cg:
        print(f'Warning: open guillemets does not equal closed guillemets:{og}:{cg}')
    if ogb!=cgb:
        print(f'Warning: open nobreak guillemets does not equal closed nobreak guillemets:{ogb}:{cgb}')
    if ob!=cb:
        print(f'Warning: open brackets does not equal closed brackets:{ob}:{cb}')
    if os!=cs:
        print(f'Warning: open square brackets does not equal closed square brackets:{ob}:{cb}')

    if ogb>0:
        return

    line_count=0
    for line in lines:
        line_count+=1
        bad_count=0
        for bad in bad_punctuation:
            bad_count+=line.count(bad)
        if bad_count>0:
            print(f'{line_count}:{line}', end='')
            if line.count(' :'):
                print( '  - Warning: space before colon will not be modified')
            if line.count('« '):
                print( '  - Warning:  space after open guillemet will not be modified')
            if line.count(' »'):
                print( '  - Warning: space before close guillemet will not be modified')
            if line.count(' —'):
                print( '  - Warning: space before tiret will not be modified')
            if line.count('— '):
                print( '  - Warning:  space after tiret will not be modified')
            if line.count(' \n'):
                print( '  - Warning: space at end of line will not be modified')
            if line.count(' ?'):
                print( '  - Warning: space before question mark will not be modified')
            if line.count(' !'):
                print( '  - Warning: space before exclamation mark will not be modified')
            if line.count(' ;'):
                print( '  - Warning: space before semicolon will not be modified')


##########
# Update the French punctuation
##########
def update_punctuation(part, target, leave, good, double):
    if part.count(target)==0:
        # Nothing to do
        return part

    # Sanity check
    if part.count('x08')>0:
        print('ERROR: bell character in string')

    # Hide items we do not want to change
    part=part.replace(leave,'x08')
    part=part.replace(good, 'x08x08')

    # Correct punctuation
    part=part.replace(target, good)

    # Restore items 
    part=part.replace('x08x08', good)
    part=part.replace('x08', leave)

    # Sanity check
    if part.count('x08')>0:
        print('ERROR: bell character in string')
    
    return part


##########
# March through the file updating the French as needed
##########
def update_french(args):
    with open(args.filename, 'r', encoding='utf-8') as file:
        lines=file.readlines()
        file.close()

    FPGEN_LINE='<option name=\'french-with-typographic-spaces\' content=\'true\'>'

    check_file(lines)

    out= open(args.output, 'w', encoding='utf-8')

    add_fpgen=True
    for line in lines:
        if line.count(FPGEN_LINE)>0:
            add_fpgen=False
            break;

    skip=False
    for line in lines:
        # Want to skip over the <lit section="head"> section
        if line.count('<lit ')==1:
            skip=True
        if skip:
            out.write(line)
            if line.count('</lit>')==1:
                skip=False
            continue

        # Insert fpgen line with other options
        if line.count('<option name=')>0:
            if add_fpgen:
                print('Adding line to file:', FPGEN_LINE)
                out.write(FPGEN_LINE)
                add_fpgen=False

        # Remove all the html business
        pattern=re.compile('<.*?>')
        parts=re.split(pattern, line)

        # Fix up punctuation in each part of the line
        for part in parts:
            new=part

            new=update_punctuation(new, '«', '« ', '«\\ ', '«\\ \\ ')
            new=update_punctuation(new, '»', ' »', '\\ »', '\\ \\ »')
            new=update_punctuation(new, ':', ' :', '\\ :', '\\ \\ :')
            new=update_punctuation(new, '—', ' —', '\\ —', '\\ \\ —')
            new=update_punctuation(new, '—', '— ', '—\\ ', '—\\ \\ ')

            # Insert updated part back into the line
            line=line.replace(part,new)

        # Fix up special cases for the tiret
        # - start of line
        if line.startswith('\\ —'):
            line=line.replace('\\ —', '—', 1)
        line=line.replace('—\\ \n', '—')

        out.write(line)

    print('Finished writing:', args.output)

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
    VERBOSE_HELP ='Show details'

    BOOLEAN_CHOICES=['True', 'T', 'False', 'F']
    LANGUAGE_CHOICES=['en', 'fr']

    parser=argparse.ArgumentParser(prog=PROGRAM_NAME, description=PROGRAM_DESCRIPTION, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename',                                                                  help=FILENAME_HELP)
    parser.add_argument('-l', '--language',  choices=LANGUAGE_CHOICES,      required=True,          help=LANGUAGE_HELP)
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

update_french(args)

