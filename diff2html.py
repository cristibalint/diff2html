#! /usr/bin/python
# coding=utf-8
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Transform a unified diff from stdin to a colored
# side-by-side HTML page on stdout.
#
# Authors: Olivier Matz <zer0@droids-corp.org>
#          Alan De Smet <adesmet@cs.wisc.edu>
#          Sergey Satskiy <sergey.satskiy@gmail.com>
#          scito <info at scito.ch>
#
# Inspired by diff2html.rb from Dave Burt <dave (at) burt.id.au>
# (mainly for html theme)
#
# TODO:
# - The sane function currently mashes non-ASCII characters to "."
#   Instead be clever and convert to something like "xF0"
#   (the hex value), and mark with a <span>.  Even more clever:
#   Detect if the character is "printable" for whatever definition,
#   and display those directly.

import sys, re, htmlentitydefs, getopt, StringIO, codecs, datetime
try:
    from simplediff import diff, string_diff
except ImportError:
    sys.stderr.write("info: simplediff module not found, only linediff is available\n")
    sys.stderr.write("info: it can be downloaded at https://github.com/paulgb/simplediff\n")

# minimum line size, we add a zero-sized breakable space every
# LINESIZE characters
linesize = 20
tabsize = 8
show_CR = False
encoding = "utf-8"
lang = "en"
algorithm = 0

diff_id = 0
prev_change = None
actual_change = None
files = {}

desc = "File comparison"
dtnow = datetime.datetime.now()
modified_date = "%s+01:00"%dtnow.isoformat()

html_hdr = """<!DOCTYPE html>
<html lang="{5}" dir="ltr"
    xmlns:dc="http://purl.org/dc/terms/">
<head>
    <meta charset="{1}" />
    <meta name="generator" content="diff2html.py (http://git.droids-corp.org/gitweb/?p=diff2html)" />
    <!--meta name="author" content="Fill in" /-->
    <title>HTML Diff{0}</title>
    <link rel="shortcut icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQAgMAAABinRfyAAAACVBMVEXAAAAAgAD///+K/HwIAAAAJUlEQVQI12NYBQQM2IgGBQ4mCIEQW7oyK4phampkGIQAc1G1AQCRxCNbyW92oQAAAABJRU5ErkJggg==" type="image/png" />
    <meta property="dc:language" content="{5}" />
    <!--meta property="dc:date" content="{3}" /-->
    <meta property="dc:modified" content="{4}" />
    <meta name="description" content="{2}" />
    <meta property="dc:abstract" content="{2}" />
    <style>
        table {{ border:1px; border-collapse:collapse; width: 100%; font-size:0.75em; font-family: Lucida Console, monospace }}
        td.line {{ color:#8080a0 }}
        tr.diffunmodified td {{ background: #D0D0E0 }}
        tr.diffhunk td {{ background: #A0A0A0 }}
        tr.diffadded td {{ background: #CCFFCC }}
        tr.diffdeleted td {{ background: #FFCCCC }}
        tr.diffchanged td {{ background: #FFFFA0 }}
        span.diffchanged2 {{ background: #E0C880 }}
        span.diffponct {{ color: #B08080 }}
        tr.diffmisc td {{}}
        tr.diffseparator td {{}}
        tr.header {{ cursor: pointer }}
        
       .floating-menu {{
            font-family: sans-serif;
            background: yellowgreen;
            width: 130px;
            z-index: 100;
            position: fixed;
            margin-top: 45vh;
            right: 0px;
            padding: 5px;
       }}        
            
       .floating-menu a, 
       .floating-menu h3 {{
            font-size: 0.9em;
            display: block;
            margin: 0 0.5em;
            color: white;
       }}
   
       .button {{
            width: 10em;  height: 2em
       }}
    </style>
    <script type="text/javascript" src="/home/ecrisba/scripts/jquery.js"></script>
    <script type="text/javascript">
      {7}      
            
      var diffId = -1;
      var lastDiffId = -1;
      
      function jumpToFirstAnchor() {{
         console.log("Jumping to first diff");
         diffId = -1;
         jumpToAnchor(1);
      }}
      
      function jumpToAnchor(offset) {{
         if(document.getElementById(diffId + offset) == null) return;
         diffId += offset;
         console.log("Jumping to diff:", diffId);
         document.getElementById(diffId).scrollIntoView({{block: "start", behavior: "smooth"}});
         document.getElementById('status').innerHTML = 'Difference: ' + (diffId + 1) + '/' + (lastDiffId+1);
      }}
            
      function updateTable() {{
         var e = document.getElementById("elementId");
         var value = e.options[e.selectedIndex].value;
         var text = e.options[e.selectedIndex].text;
         document.getElementById('difftable').innerHTML = diffs[value];
            
         lastDiffId = -1;
         while(document.getElementById(lastDiffId + 1) != null) lastDiffId = lastDiffId + 1;
      }}
            
      function jumpToTop() {{
         $('html, body').animate({{ scrollTop: 0 }}, 'fast'); 
         document.getElementById('status').innerHTML = '';     
      }}
      
      function init() {{
          updateTable();
      }}
            
      window.onload = init;
    </script>    
</head>
<body>
            
<select id="elementId" onchange="updateTable()">
  {6}
</select>
<nav class="floating-menu">
		 <input class="button" type="button" name="first" value="first diff block" onclick="jumpToFirstAnchor()">
		 <input class="button" type="button" name="prev" value="prev diff block" onclick="jumpToAnchor(-1)" style="widht:20em">
		 <input class="button" type="button" name="next" value="next diff block" onclick="jumpToAnchor(1)" style="widht:20em">
		 <input class="button" type="button" name="top" value="jump to top" onclick="jumpToTop()" style="widht:20em">
                 <div id="status" align=left></div>
</nav>
<div id="difftable"></div>
"""            
            
html_footer = """
<footer>
    <p>Modified at {1}. HTML formatting created by <a href="http://git.droids-corp.org/gitweb/?p=diff2html;a=summary">diff2html</a>.    </p>
</footer>
</body></html>
"""

table_hdr = """
		<table class="diff">
"""

table_footer = """
</table>
"""

DIFFON = "\x01"
DIFFOFF = "\x02"

buf = []
add_cpt, del_cpt = 0, 0
line1, line2 = 0, 0
hunk_off1, hunk_size1, hunk_off2, hunk_size2 = 0, 0, 0, 0


# Characters we're willing to word wrap on
WORDBREAK = " \t;.,/):-"

def sane(x):
    r = ""
    for i in x:
        j = ord(i)
        if i not in ['\t', '\n'] and (j < 32):
            r = r + "."
        else:
            r = r + i
    return r

def linediff(s, t):
    '''
    Original line diff algorithm of diff2html. It's character based.
    '''
    if len(s):
        s = unicode(reduce(lambda x, y:x+y, [ sane(c) for c in s ]))
    if len(t):
        t = unicode(reduce(lambda x, y:x+y, [ sane(c) for c in t ]))

    m, n = len(s), len(t)
    d = [[(0, 0) for i in range(n+1)] for i in range(m+1)]


    d[0][0] = (0, (0, 0))
    for i in range(m+1)[1:]:
        d[i][0] = (i,(i-1, 0))
    for j in range(n+1)[1:]:
        d[0][j] = (j,(0, j-1))

    for i in range(m+1)[1:]:
        for j in range(n+1)[1:]:
            if s[i-1] == t[j-1]:
                cost = 0
            else:
                cost = 1
            d[i][j] = min((d[i-1][j][0] + 1, (i-1, j)),
                          (d[i][j-1][0] + 1, (i, j-1)),
                          (d[i-1][j-1][0] + cost, (i-1, j-1)))

    l = []
    coord = (m, n)
    while coord != (0, 0):
        l.insert(0, coord)
        x, y = coord
        coord = d[x][y][1]

    l1 = []
    l2 = []

    for coord in l:
        cx, cy = coord
        child_val = d[cx][cy][0]

        father_coord = d[cx][cy][1]
        fx, fy = father_coord
        father_val = d[fx][fy][0]

        diff = (cx-fx, cy-fy)

        if diff == (0, 1):
            l1.append("")
            l2.append(DIFFON + t[fy] + DIFFOFF)
        elif diff == (1, 0):
            l1.append(DIFFON + s[fx] + DIFFOFF)
            l2.append("")
        elif child_val-father_val == 1:
            l1.append(DIFFON + s[fx] + DIFFOFF)
            l2.append(DIFFON + t[fy] + DIFFOFF)
        else:
            l1.append(s[fx])
            l2.append(t[fy])

    r1, r2 = (reduce(lambda x, y:x+y, l1), reduce(lambda x, y:x+y, l2))
    return r1, r2


def diff_changed(old, new):
    '''
    Returns the differences basend on characters between two strings
    wrapped with DIFFON and DIFFOFF using `diff`.
    '''
    con = {'=': (lambda x: x),
           '+': (lambda x: DIFFON + x + DIFFOFF),
           '-': (lambda x: '')}
    return "".join([(con[a])("".join(b)) for a, b in diff(old, new)])


def diff_changed_ts(old, new):
    '''
    Returns a tuple for a two sided comparison based on characters, see `diff_changed`.
    '''
    return (diff_changed(new, old), diff_changed(old, new))


def word_diff(old, new):
    '''
    Returns the difference between the old and new strings based on words. Punctuation is not part of the word.

    Params:
        old the old string
        new the new string

    Returns:
        the output of `diff` on the two strings after splitting them
        on whitespace (a list of change instructions; see the docstring
        of `diff`)
    '''
    separator_pattern = '(\W+)';
    return diff(re.split(separator_pattern, old, flags=re.UNICODE), re.split(separator_pattern, new, flags=re.UNICODE))


def diff_changed_words(old, new):
    '''
    Returns the difference between two strings based on words (see `word_diff`)
    wrapped with DIFFON and DIFFOFF.

    Returns:
        the output of the diff expressed delimited with DIFFON and DIFFOFF.
    '''
    con = {'=': (lambda x: x),
           '+': (lambda x: DIFFON + x + DIFFOFF),
           '-': (lambda x: '')}
    return "".join([(con[a])("".join(b)) for a, b in word_diff(old, new)])


def diff_changed_words_ts(old, new):
    '''
    Returns a tuple for a two sided comparison based on words, see `diff_changed_words`.
    '''
    return (diff_changed_words(new, old), diff_changed_words(old, new))


def convert(s, linesize=0, ponct=0):
    i = 0
    t = u""
    for c in s:
        # used by diffs
        if c == DIFFON:
            t += u'<span class="diffchanged2">'
        elif c == DIFFOFF:
            t += u"</span>"

        # special html chars
        elif htmlentitydefs.codepoint2name.has_key(ord(c)):
            t += u"&%s;" % (htmlentitydefs.codepoint2name[ord(c)])
            i += 1

        # special highlighted chars
        elif c == "\t" and ponct == 1:
            n = tabsize-(i%tabsize)
            if n == 0:
                n = tabsize
            t += (u'<span class="diffponct">&raquo;</span>'+'&nbsp;'*(n-1))
        elif c == " " and ponct == 1:
            t += u'<span class="diffponct">&middot;</span>'
        elif c == "\n" and ponct == 1:
            if show_CR:
                t += u'<span class="diffponct">\</span>'
        else:
            t += c
            i += 1

        if linesize and (WORDBREAK.count(c) == 1):
            t += u'&#8203;'
            i = 0
        if linesize and i > linesize:
            i = 0
            t += u"&#8203;"

    return t


def add_comment(s, file_name):
    files[file_name] = "%s%s" % (files[file_name], ('<tr class="diffmisc"><td colspan="4">%s</td></tr>\n'%convert(s)).encode(encoding))

def add_filename(f1, f2, file_name):
    files[file_name] = "%s%s" % (files[file_name], ("<tr><th colspan='2'>%s</th>"%convert(f1, linesize=linesize)).encode(encoding))
    files[file_name] = "%s%s" % (files[file_name], ("<th colspan='2'>%s</th></tr>\n"%convert(f2, linesize=linesize)).encode(encoding))

def add_hunk(show_hunk_infos, file_name):
    if show_hunk_infos:
        files[file_name] = "%s%s" % (files[file_name], '<tr class="diffhunk"><td colspan="2">Offset %d, %d lines modified</td>'%(hunk_off1, hunk_size1))
        files[file_name] = "%s%s" % (files[file_name], '<td colspan="2">Offset %d, %d lines modified</td></tr>\n'%(hunk_off2, hunk_size2))
    else:
        # &#8942; - vertical ellipsis
        files[file_name] = "%s%s" % (files[file_name], '<tr class="diffhunk"><td colspan="2">&#8942;</td><td colspan="2">&#8942;</td></tr>')


def add_line(s1, s2, file_name):
    global line1
    global line2
    global prev_change
    global actual_change
    global diff_id
    
    orig1 = s1
    orig2 = s2

    if s1 == None and s2 == None:
        type_name = "unmodified"
    elif s1 == None or s1 == "":
        type_name = "added"
    elif s2 == None or s1 == "":
        type_name = "deleted"
    elif s1 == s2:
        type_name = "unmodified"
    else:
        type_name = "changed"
        if algorithm == 1:
            s1, s2 = diff_changed_words_ts(orig1, orig2)
        elif algorithm == 2:
            s1, s2 = diff_changed_ts(orig1, orig2)
        else: # default
            s1, s2 = linediff(orig1, orig2)
    actual_change = type_name

    if actual_change != prev_change and (actual_change == "deleted" or actual_change == "added" or actual_change == "changed"):
       files[file_name] = "%s%s" % (files[file_name], ('<tr id="%s" class="diff%s">' % (diff_id, type_name)).encode(encoding))
       diff_id += 1
    else:
       files[file_name] = "%s%s" % (files[file_name], ('<tr class="diff%s">' % type_name).encode(encoding))
       
    if s1 != None and s1 != "":
       files[file_name] = "%s%s" % (files[file_name], ('<td class="diffline">%d </td>' % line1).encode(encoding))
       files[file_name] = "%s%s" % (files[file_name], '<td class="diffpresent">'.encode(encoding))
       files[file_name] = "%s%s" % (files[file_name], convert(s1, linesize=linesize, ponct=1).encode(encoding))
       files[file_name] = "%s%s" % (files[file_name], '</td>')
    else:
       s1 = ""
       files[file_name] = "%s%s" % (files[file_name], '<td colspan="2"> </td>')

    if s2 != None and s2 != "":
       files[file_name] = "%s%s" % (files[file_name], ('<td class="diffline">%d </td>'%line2).encode(encoding))
       files[file_name] = "%s%s" % (files[file_name], '<td class="diffpresent">')
       files[file_name] = "%s%s" % (files[file_name], convert(s2, linesize=linesize, ponct=1).encode(encoding))
       files[file_name] = "%s%s" % (files[file_name], '</td>')
              
    else:
       s2 = ""
       files[file_name] = "%s%s" % (files[file_name], '<td colspan="2"></td>')

    files[file_name] = "%s%s" % (files[file_name], '</tr>\n')

    if s1 != "":
        line1 += 1
    if s2 != "":
        line2 += 1
    
    prev_change = actual_change

def empty_buffer(file_name):
    global buf
    global add_cpt
    global del_cpt

    if del_cpt == 0 or add_cpt == 0:
        for l in buf:
            add_line(l[0], l[1], file_name)

    elif del_cpt != 0 and add_cpt != 0:
        l0, l1 = [], []
        for l in buf:
            if l[0] != None:
                l0.append(l[0])
            if l[1] != None:
                l1.append(l[1])
        max_len = (len(l0) > len(l1)) and len(l0) or len(l1)
        for i in range(max_len):
            s0, s1 = "", ""
            if i < len(l0):
                s0 = l0[i]
            if i < len(l1):
                s1 = l1[i]
            add_line(s0, s1, file_name)

    add_cpt, del_cpt = 0, 0
    buf = []


def parse_input(input_file, input_file_name,
                exclude_headers, show_hunk_infos):
    global add_cpt, del_cpt
    global line1, line2
    global hunk_off1, hunk_size1, hunk_off2, hunk_size2
    global diff_id
    file_name = ''
    is_git_diff = 0

    while True:
        l = input_file.readline()
        if l == "":
            break

        m = re.match('diff --git a.*/([^/]*) b.*/([^/]*)$', l)
        if m:
           is_git_diff = 1
           fNameA = m.group(1)
           fNameB = m.group(2)
           if fNameA.strip() == fNameB.strip():
              if file_name == '':
                 file_name = fNameA
                 files[file_name] = table_hdr.encode(encoding);
                 
              elif not file_name == fNameA:
                 empty_buffer(file_name)
                 files[file_name] = "%s %s" % ( files[file_name], table_footer.encode(encoding))
                 file_name = fNameA
                 files[file_name] = table_hdr.encode(encoding);
                 
           else:
              file_name = fNameA
           
        m = re.match('^--- (.*/)?([^ \t]+).*', l)
        if m:
            empty_buffer(file_name)
            
            fNameA = (m.groups()[1]).strip()
            diff_id = 0
            
            file_name = fNameA
            if(is_git_diff != 1):
                files[file_name] = table_hdr.encode(encoding);
            
            while True:
                l = input_file.readline()
                m = re.match('^\+\+\+ (.*/)?([^ \t]+).*', l)
                if m:
                    fNameB = (m.groups()[1]).strip()
                    break
                
            add_filename(fNameA, fNameB, file_name)            
            hunk_off1, hunk_size1, hunk_off2, hunk_size2 = 0, 0, 0, 0
            continue

        m = re.match("@@ -(\d+),?(\d*) \+(\d+),?(\d*)", l)
        if m:
            empty_buffer(file_name)
            hunk_data = map(lambda x:x=="" and 1 or int(x), m.groups())
            hunk_off1, hunk_size1, hunk_off2, hunk_size2 = hunk_data
            line1, line2 = hunk_off1, hunk_off2
            add_hunk(show_hunk_infos, file_name)
            continue

        if hunk_size1 == 0 and hunk_size2 == 0:
            empty_buffer(file_name)
            add_comment(l, file_name)
            continue

        if re.match("^\+", l):
            add_cpt += 1
            hunk_size2 -= 1
            buf.append((None, l[1:]))
            continue

        if re.match("^\-", l):
            del_cpt += 1
            hunk_size1 -= 1
            buf.append((l[1:], None))
            continue

        if re.match("^\ ", l) and hunk_size1 and hunk_size2:
            empty_buffer(file_name)
            hunk_size1 -= 1
            hunk_size2 -= 1
            buf.append((l[1:], l[1:]))
            continue

        empty_buffer(file_name)
        add_comment(l, file_name)

    empty_buffer(file_name)
        
    files[file_name] = "%s %s" % ( files[file_name], table_footer.encode(encoding))
  

def usage():
    print '''
diff2html.py [-e encoding] [-i file] [-o file] [-x]
diff2html.py -h

Transform a unified diff from stdin to a colored side-by-side HTML
page on stdout.
stdout may not work with UTF-8, instead use -o option.

   -i file     set input file, else use stdin
   -e encoding set file encoding (default utf-8)
   -o file     set output file, else use stdout
   -x          exclude html header and footer
   -t tabsize  set tab size (default 8)
   -l linesize set maximum line size is there is no word break (default 20)
   -r          show \\r characters
   -k          show hunk infos
   -a algo     line diff algorithm (0: linediff characters, 1: word, 2: simplediff characters) (default 0)
   -h          show help and exit
'''

def main():
    global linesize, tabsize
    global show_CR
    global encoding
    global algorithm

    input_file_name = ''
    output_file_name = ''
    index_file_name = ''

    exclude_headers = False
    show_hunk_infos = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "he:i:o:xt:l:rka:",
                                   ["help", "encoding=", "input=", "output=",
                                    "exclude-html-headers", "tabsize=",
                                    "linesize=", "show-cr", "show-hunk-infos", "algorithm="])
    except getopt.GetoptError, err:
        print unicode(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    verbose = False
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-e", "--encoding"):
            encoding = a
        elif o in ("-i", "--input"):
            input_file = codecs.open(a, "r", encoding)
            input_file_name = a
        elif o in ("-o", "--output"):
            output_file = codecs.open(a, "w")
            output_file_name = a
        elif o in ("-x", "--exclude-html-headers"):
            exclude_headers = True
        elif o in ("-t", "--tabsize"):
            tabsize = int(a)
        elif o in ("-l", "--linesize"):
            linesize = int(a)
        elif o in ("-r", "--show-cr"):
            show_CR = True
        elif o in ("-k", "--show-hunk-infos"):
            show_hunk_infos = True
        elif o in ("-a", "--algorithm"):
            algorithm = int(a)
        else:
            assert False, "unhandled option"

    # Use stdin if not input file is set
    if not ('input_file' in locals()):
        input_file = codecs.getreader(encoding)(sys.stdin)

    # Use stdout if not output file is set
    if not ('output_file' in locals()):
        output_file = codecs.getwriter(encoding)(sys.stdout)

    parse_input(input_file, input_file_name,
                exclude_headers, show_hunk_infos)
                
    select = ""
    javascript_vars = "var diffs = new Array(" + str(len(files)) + ")"
    for k, v in files.items():
       select = "%s %s" % (select, '<option value="' + k + '">' + k + '</option>') 
       javascript_vars = "%s;\n diffs['%s'] = [`%s`] " % (javascript_vars, k, v.replace("`", "\`").replace("$", "\$"))
    javascript_vars = "%s;\n" % javascript_vars   
    output_file.write(html_hdr.format(output_file_name, encoding, desc, "", modified_date, lang, select, javascript_vars).encode(encoding))

    output_file.write(html_footer.format("", dtnow.strftime("%d.%m.%Y")).encode(encoding))	

def parse_from_memory(txt, exclude_headers, show_hunk_infos):
    " Parses diff from memory and returns a string with html "
    input_stream = StringIO.StringIO(txt)
    output_stream = StringIO.StringIO()
    parse_input(input_stream, output_stream, '', '', exclude_headers, show_hunk_infos)
    return output_stream.getvalue()


if __name__ == "__main__":
    main()
