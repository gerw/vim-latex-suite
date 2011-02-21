#!/usr/bin/python

# Part of Latex-Suite
#
# Copyright: Srinath Avadhanula, Gerd Wachsmuth
# Description:
#   This file implements a simple outline creation for latex documents.

import re
import os
import sys
import StringIO

# getFileContents {{{
def getFileContents(fname):
    if type(fname) is not str:
        fname = fname.group(1)

    # If neither the file or file.aux exists, then we just give up.
    fname = re.sub('\.tex$','',fname)
    if not os.path.isfile(fname):
        if os.path.isfile(fname + '.aux'):
            fname += '.aux'
        else:
            return ''

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
# stripComments {{{
def stripComments(contents):
    # remove all comments
    # comment is a '%' preceeded by an even number of '\'
    uncomm = [re.sub(r'(?<!\\)(\\\\)*%.*', '', line) for line in contents.splitlines()]

    nonempty = [line for line in uncomm if line.strip()]

    return nonempty
# }}}
# getSectionLabels_Root {{{
def getSectionLabels_Root(lineinfo, section_prefix, label_prefix, label_value):
    inside_env = 0
    prev_env = ''
    outstr = StringIO.StringIO('')
    pres_depth = section_prefix

    #print '+getSectionLabels_Root: lineinfo = [%s]' % lineinfo
    for line in lineinfo.splitlines():
        prev_txt = ''
        if not line:
            continue

        # throw away leading white-space
        line = line.lstrip()

        # we found a label!
        m = re.search(r'\\newlabel{(%s.*?)}' % label_prefix, line)
        if m and not re.search(r'^tocindent-?[0-9]*$', m.group(1)):
            # add the text (without aliascounter:) in the pre-last {} to the text
            # which will be displayed below this label
            n = re.search(r'\\newlabel{(%s.*?)}{{(\\relax )?(.*?)}.*{(aliascounter:)?(.*)}{.*?}}' % label_prefix, line)
            if n:
              o = re.search(r'equation\.(.*)', n.group(5))
              if o:
                # Found an equation
                prev_txt += '(' + n.group(3) + ')'
              else:
                o = re.search(r'AMS\.(.*)', n.group(5))
                if o:
                  # Found an named equation
                  p = re.search(r'\\newlabel{(%s.*?)}{{{(.*?)}}' % label_prefix, line)
                  if p:
                    # Remove all "{" and "}" (for subequtaions)
                    equation_number = re.sub('[{}]', '',  p.group(2) )
                    prev_txt += '(' + equation_number + ')'
                  else:
                    prev_txt += n.group(5)
                else:
                  prev_txt += re.match(r'\w*', n.group(5)).group() + '.' + n.group(3)
            else:
              n = re.search(r'\\newlabel{(%s.*?)}{{(\\relax )?(.*)}{.*}}' % label_prefix, line)
              prev_txt += n.group(3)

            # print label_value
            # print prev_txt
            if re.match( label_value, prev_txt):
                # Print label and counter+number:
                print >>outstr, '>%s%s' % (' '*(2*pres_depth-2), m.group(1))
                print >>outstr, ':%s%s' % (' '*(2*pres_depth+0), prev_txt)

    return outstr.getvalue()
    
# }}}
# getSectionLabels {{{
def getSectionLabels(lineinfo, 
        sectypes=['part', 'chapter', 'section', 'subsection', 'subsubsection', 'paragraph', 'subparagraph'], 
        section_prefix=1, label_prefix='', label_value=''):

    if not sectypes:
        return getSectionLabels_Root(lineinfo, section_prefix, label_prefix, label_value)

    ##print 'sectypes[0] = %s, section_prefix = [%s], lineinfo = [%s]' % (
    ##        sectypes[0], section_prefix, lineinfo)

    sections = re.split(r'(\\@writefile{toc}{\\contentsline {%s}.*)' % sectypes[0], lineinfo)
    
    # there will 1+2n sections, the first containing the "preamble" and the
    # others containing the child sections as paris of [section_name,
    # section_text]

    rettext = getSectionLabels(sections[0], sectypes[1:], section_prefix, label_prefix, label_value)
 
    for i in range(1,len(sections),2):
        # print sections[i]
        o = re.search( r'{%s}{\\numberline {(\\relax )?(.*?)}(.*?)}' % sectypes[0] , sections[i])
        if o:
          section_name = o.group(3)
          sec_num = o.group(2) + ' '
        else:
          o = re.search( r'{%s}{(.*?)}' % sectypes[0] , sections[i])
          section_name = o.group(1)
          sec_num = ''

        section_label_text = getSectionLabels(sections[i] + sections[i+1], sectypes[1:], 
                                    section_prefix+1, label_prefix, label_value)

        if section_label_text:
            sec_heading = 2*' '*(section_prefix-1) # + section_prefix
            sec_heading += '%s%s' % (sec_num, section_name)
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

    lineinfo = ''
    for line in nonempty:
        lineinfo += line + '\n'

    
    o = re.match( '(\([0-9a-zA-Z.]*|\w*\.[0-9a-zA-Z.]*)' , prefix )
    if o:
        label_prefix = ''
        label_value = re.escape(prefix)
    else:
        label_prefix = prefix
        label_value = ''
    rettext = getSectionLabels(lineinfo, label_prefix=label_prefix, label_value=label_value)
    a = re.findall( r'(^|\n)> *([^ ]*)\n' , rettext)

    # Only one matching label? => return it
    if len(a) == 0:
        return ''
    elif len(a) == 1:
        return a[0][1]
    else:
        return rettext
# }}}

if __name__ == "__main__":
    if len(sys.argv) > 2:
        prefix = sys.argv[2]
    else:
        prefix = ''

    print main(sys.argv[1], prefix)


# vim: fdm=marker
