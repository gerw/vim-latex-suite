#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Part of Latex-Suite
#
# Copyright: Srinath Avadhanula, Gerd Wachsmuth
# Description:
#   This file implements a simple outline creation for latex documents.

import re
import os
import sys
if sys.version_info <= (3, 0):
    from StringIO import StringIO
else:
    from io import StringIO


# getFileContents {{{
def getFileContents(fname):
    if type(fname) is not str:
        fname = fname.group(1)

    # Strategy for determining the name of the aux file:
    # If the suffix is '.tex' then throw it away.
    # If the suffix is not '.aux' then add '.aux'.
    fname = re.sub(r'\.tex$','',fname)
    if not re.search(r'\.aux$', fname):
        fname += '.aux'
    if not os.path.isfile(fname):
        return ''

    # Now we are in position to scan the file.
    try:
        # This longish thing is to make sure that all files are converted into
        # \n seperated lines.
        contents = '\n'.join(open(fname).read().splitlines())
    except IOError:
        return ''

    # TODO what are all the ways in which an aux file can include another?
    pat = re.compile(r'^\\@input{(.*?)}', re.M)
    # pat = re.compile(r'^\\(@?)(include|input){(.*?)}', re.M)
    contents = re.sub(pat, getFileContents, contents)

    return contents

# }}}
# utfify {{{
def utfify(text):
	for (pat,rep) in [['"a','ä'],['"o','ö'],['"u','ü'],['"A','Ä'],['"O','Ö'],['"U','Ü'], ['\'e', 'é']]:
		text = [re.sub(r'\\IeC {\\' + pat + '}', rep, line) for line in text]
	return text
# }}}
# stripComments {{{
def stripComments(contents):
    # remove all comments
    # comment is a '%' preceeded by an even number of '\'
    uncomm = [re.sub(r'(?<!\\)(\\\\)*%.*', '', line) for line in contents.splitlines()]

    nonempty = [line for line in uncomm if line.strip()]

    return nonempty
# }}}
# getSectionLabels_Root {{{
def getSectionLabels_Root(lineinfo, section_prefix, label_prefix, value_prefix):
    outstr = StringIO('')
    indent = ' ' * (2*section_prefix - 2)

    # Check for cleveref
    if re.search(r'\\newlabel{.*@cref}' , lineinfo ):
      cleveref = True
    else:
      cleveref = False

    for line in lineinfo.splitlines():
        prev_txt = ''
        if not line:
            continue

        # throw away leading white-space
        line = line.lstrip()

        # we found a label!
        m = re.search(r'\\newlabel{(%s.*?)(@cref)?}' % label_prefix, line)
        if m and not re.search(r'^tocindent-?[0-9]*$', m.group(1)):
            label = m.group(1)

            if cleveref:
              # Cleveref was detected.
              n = re.search(r'\\newlabel{(%s.*?)@cref}{{\[(.*)\]\[.*\]\[.*\](.*)}{.*}}' % label_prefix, line)
              if n:
                if n.group(2) == 'equation' or n.group(2) == 'subequation':
                  # Found an equation
                  prev_txt += '(' + n.group(3) + ')'
                else:
                  # Found something different
                  prev_txt += n.group(2) + '.' + n.group(3)
            else:
              # add the text (without aliascounter:) in the pre-last {} to the text
              # which will be displayed below this label
              n = re.search(r'\\newlabel{(%s.*?)}{{(\\relax )?(.*?)}.*{(aliascounter:)?(.*)}{.*?}}' % label_prefix, line)
              if n:
                # Hyperref was detected.
                o = re.search(r'equation\.(.*)', n.group(5))
                if o:
                  # Found an equation
                  prev_txt += '(' + n.group(3) + ')'
                else:
                  o = re.search(r'AMS\.(.*)', n.group(5))
                  if o:
                    # Found an named equation => try to find the name
                    # After the name, there is the page number (assumed to be of the form [0-9a-zA-Z]* )
                    p = re.search(r'\\newlabel{(%s.*?)}{{{(.*?)}}{[0-9a-zA-Z]*}' % label_prefix, line)
                    if p:
                      equation_number = p.group(2)
                      prev_txt += '(' + equation_number + ')'
                    else:
                      prev_txt += n.group(5)
                  else:
                    prev_txt += re.match(r'^\w*', n.group(5)).group() + '.' + n.group(3)
              else:
                # Hyperref was not detected.
                n = re.search(r'\\newlabel{(%s.*?)}{{(\\relax )?(.*)}{.*}}' % label_prefix, line)
                prev_txt += n.group(3)

            if prev_txt != "" and re.match( value_prefix, prev_txt):
                # Remove all curly braces in prev_txt:
                prev_txt = re.sub(r'[{}]', '', prev_txt);
                # Print label and counter+number:
                outstr.write('>%s%s\n'   % (indent, label))
                outstr.write(':%s  %s\n' % (indent, prev_txt))

    return outstr.getvalue()
# }}}
# getSectionLabels {{{
def getSectionLabels(lineinfo, 
        sectypes=['part', 'chapter', 'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph'], 
        section_prefix=1, label_prefix='', value_prefix=''):

    if not sectypes:
        return getSectionLabels_Root(lineinfo, section_prefix, label_prefix, value_prefix)

    sections = re.split(r'(\\@writefile{toc}{\\contentsline {%s}.*)' % sectypes[0], lineinfo)
    
    # there will 1+2n sections, the first containing the "preamble" and the
    # others containing the child sections as paris of [section_name,
    # section_text]

    rettext = getSectionLabels(sections[0], sectypes[1:], section_prefix, label_prefix, value_prefix)
 
    for i in range(1,len(sections),2):

        section_label_text = getSectionLabels(sections[i+1], sectypes[1:], section_prefix+1, label_prefix, value_prefix)

        if section_label_text:
          # This section contains labels
          # Let us determine the section number and the section heading
          o1 = re.search( r'{%s}{\\numberline {(\\relax )?(.*?)}(.*?)}{[^{}]*}{[^{}]*}}$' % sectypes[0] , sections[i]) # With hyperref
          o2 = re.search( r'{%s}{\\numberline {(\\relax )?(.*?)}(.*?)}' % sectypes[0] , sections[i]) # Without hyperref
          o3 = re.search( r'{%s}{\\toc(section|chapter) {(.*?)}{(.*?)}{(.*?)}' % sectypes[0] , sections[i]) # amsart,amsbook
          o4 = re.search( r'{%s}{(.*?)}' % sectypes[0] , sections[i])
          if o1:
            section_name = o1.group(3)
            section_number = o1.group(2) + ' '
          elif o2:
            section_name = o2.group(3)
            section_number = o2.group(2) + ' '
          elif o3:
            section_name = o3.group(4)
            if o3.group(2) == "":
              section_number =  o3.group(3) + ' '
            else:
              section_number =  o3.group(2) + ' ' + o3.group(3) + ' '
          elif o4:
            section_name = o4.group(1)
            section_number = ''
          else:
            print('Unknown heading format "%s"' % sections[i])
            section_name = "Unknown Name"
            section_number = "??"
          sec_heading = 2*' '*(section_prefix-1)
          sec_heading += '%s%s' % (section_number, section_name)
          sec_heading += '<<<%d\n' % section_prefix

          rettext += sec_heading + section_label_text

    return rettext
    
# }}}

# main {{{
def main(fname, prefix):
    [head, tail] = os.path.split(fname)
    if head:
        os.chdir(head)

    contents = getFileContents(fname)
    nonempty = stripComments(contents)
    utftext = utfify(nonempty)

    lineinfo = ''
    for line in utftext:
        lineinfo += line + '\n'

    
    # Does prefix look like a label or a value?
    o = re.match( '(\([0-9a-zA-Z.]*|\w*\.[0-9a-zA-Z.]*)' , prefix )
    if o:
        label_prefix = ''
        value_prefix = re.escape(prefix)
    else:
        label_prefix = prefix
        value_prefix = ''

    rettext = getSectionLabels(lineinfo, label_prefix=label_prefix, value_prefix=value_prefix)
    a = re.findall( r'(^|\n)> *([^ ]*)\n' , rettext)

    if len(a) == 0:
        return ''
    elif len(a) == 1:
        # Only one partial match
        # Check, if prefix matches exactly
        if value_prefix != '' and re.search( r'\n: *%s\n' % value_prefix, rettext):
          # Value_prefix matches _exactly_ counter.number => return only this matching label
          return a[0][1]
        elif label_prefix != '':
          # Prefix matches the beginning of the label => return only this matching label
          return a[0][1]
        else:
          return rettext
    else:
        return rettext
# }}}

if __name__ == "__main__":
    if len(sys.argv) > 2:
        prefix = sys.argv[2]
    else:
        prefix = ''

    sys.stdout.write(main(sys.argv[1], prefix))


# vim: fdm=marker
