#!/usr/bin/env python3
r"""
doclifter.py: translate man/mdoc/ms/me/mm sources to DocBook.

By Eric S. Raymond, copyright 2002, 2006, 2007.

This comment is addressed to you if you want to add support for another
macro package to doclifter.py.  Or if you have encountered a bug in doclifter.py
and need to understand the code in doclifter.py in order to fix it.  Or if
you just want to understand how it works.

This code has only one piece of global state: globalhints.  Two other
globals, stdout and stderr, don't retain state.  A global
prettyprinter instance named `pretty' may be created if you're debugging.

Internally, doclifter.py consists mainly of a framework class called
DocLifter.  This class is instantiated and told to do its stuff
by a routine called transfile, which handles all I/O to disk and gives
doclifter.py its cc-like invocation protocol.  Underneath, it passes
TroffInterpreter a string consisting of the entire text of the file to
be translated and accepts a translated string back.

TroffInterpreter provides I/O and other basic services for a stack of request
interpreters.  Interpreters get added to the stack when TroffInterpreter
recognizes certain patterns in the input; see the table interpreterDispatch
for details.  If a string pattern added to this table is length 2,
TroffInterpreter will assume it is a request name and check to make sure
that it's not a macro.

The interpreter stack always includes TroffInterpreter at the bottom.  This
request interpreter handles the small set of troff requests that we translate,
including .so, .nf, .fi, .if, etc.  It also handles macro and string expansion.

Note that commands are looked up in reverse order of class activation, e.g
most recent extension set first.  This means that definitions in a later
class override definitions in earlier ones.

Each request interpreter is a class that provides methods and members to be
used by the framework.  Here they are:

name
   The name of the macro set

exclusive
   Whether this is a "major" macro set like man, mdoc, mm, ms, or me --
as opposed to a minor one like pod2man or TkMan.  Whichever major macro
set is triggered earliest in the file gets a lock on it; trigger patterns
from other exclusive macros are subsequently ignored.

toptag
   The top-level tag in the type of DocBook that this request interpreter
generates.  The top tag for the generated XML will be the top tag of the only
exclusive macro set in the stack, if there is one; otherwise it will be the
top tag of the most recently added interpreter.

ignoreSet
   Tags to ignore.  List here any presentation-level tags that don't have
structural implications.  They will be silently discarded.
   Note: there is a potential subtle gotcha in the handling of ignore
sets.  The code presently assumes that no tag in any interpreter's
ignore set is handled by any other interpreter.

complainSet
   Tags to complain about.  Put here things that can't be translated out
of presentation level but that might have structural meaning (such as
indentation changes).  The user will be warned on stderr when these
come up.  Otherwise they're ignored.

parabreakSet
   The set of tags that forces a new paragraph without changing the
document section.  Used to recognize the end of lists.

sectionbreakSet
   The set of tags that forces a new document section.  Things that
are going to translate to a DocBook sect, refsect, or section tag
should go here.

listbreakSet
   The set of tags that forces an end to a list section.  Normally
includes everything in the sectionbreakSet.

scopedSet
   The set of list tags that is scoped, e.g has an end tag and should *not*
be interrupted by list breakers.

translations
   Special-character to ISO literal mappings.  These are applied late
in the translation, *after* string and macro evaluation.
   It's also useful to know that your request interpreter can call the
function declareBodyStart() to tell the framework class where the
body of the document starts (as opposed to the preamble full of troff
requests).  This infornation is used to restrict the scope of
character translations.

interpret
   The request interpreter.  Called on every input line that begins
with a command character, that is . or ' not followed by another ' on the
same line.
   This method needs to be careful about troff continuation (\c)
characters.  If you add trailing markup to a line, or entirely replace the
line, be sure to check for trailing \c first, remove it if present, and
paste it back on the end.

preprocess, postprocess
   Pre-processing and postprocessing hooks.  Each takes a string
(assumed to be the entire file text) and returns a string.

reductions:
   A list of pairs of macro names.  In each pair, the first is to be
replaced by the second if this macro set is active and the definition of
the first contains the second.  This member is useful for replacing
stereotyped wrapper macros with standard constructs that the translator
knows how to handle.
   Most frequent case: lots of man page authors define a .Pp macro that
does various funky things in troff but just expands to .PP in nroff.
If we replace this with .PP various nasty parsing situations suddenly
don't break.

The easiest way to write a full-blown new request interpreter is to
take an existing one and mutate it.  If the macro package you are
trying to support merely adds a few tags to an existing one, consider
writing an interpreter for just those tags and adding it to the stack
(this is the way the Pod2ManInterpreter code relates to
ManInterpreter).

Warning: much of this code is grubby.  Alas, the grubbiness is
intrinsic, because the troff request language is grubby.
"""
# SPDX-License-Identifier: BSD-2-Clause
# Runs under both Python 2 and Python 3; preserve this property!

import sys, os, glob, re, string, tempfile, time, pprint, subprocess, io

try:
    import exceptions
    BaseException = exceptions.Exception
except ImportError:
    pass

try:
    getstatusoutput = subprocess.getstatusoutput
except AttributeError:
    import commands
    getstatusoutput = commands.getstatusoutput

version = "2.20"

# This is a speed hack recommended by Armin Rigo.  It cuts runtime by about 33%
# and makes it possible for psyco 1.2 to reduce runtime another 33%.
reCache = {}
def reCompile(st, flags=0):
    try:
        return reCache[st]
    except KeyError:
        r = reCache[st] = re.compile(st, flags)
        return r

# In order: Dutch, English/German, French, Italian, Norwegian/Danish, Polish,
# Spanish, Swedish.
nameSynonyms = re.compile("^(naam|name|nom|nome|navn|nazwa|nombre|namn)$", re.I)

# How to detect synopses
synopsisLabel = re.compile("SYNOPSIS$", re.I)
synopsisHeader = re.compile(r'\.S[Hh]\s*"?(?:SYNOPSIS)"?$', re.I)
descriptionLabel = re.compile("DESCRIPTION$", re.I)

# Qt part descriptions.  It's OK to see these in function synopses, we just
# turn them into an info section.
qtHeaders = ("Public Members", "Public Slots", "Signals",
              "Static Public Members", "Properties", "Protected Members",)
# Used to distinguish first-level section headers from second-level ones
# when the Qt grotty hack is enabled.
capsHeader = re.compile("^[A-Z ]*$")
# These have to be messed with by the Qt grotty hack.
qtInvert = ("Property Documentation", "Member Type Documentation")

blankline = re.compile(r"^\s*$")

# Start tag on a line by itself
endtag = re.compile("<[^>]*>$")

# Used in C syntax recognition
cDeclarators = ("void", "char", "short", "int",
              "long", "float", "double", "signed",
              "unsigned", "typedef", "struct",
              "union", "enum", "const", "volatile",
              "inline", "restricted",	# C9X
              "virtual",)		# C++
cSourceRe = re.compile("|".join(cDeclarators))

# Used to strip headers off generated HTML documents.
xmlheader = re.compile(r"<\?.*\?>\n")
doctype = re.compile(r"<\!DOCTYPE[^>]*\>\n")

# These patterns are applied *after* special-character translation

# Match an RFC822 email address, possibly with surrounding <>.
# This is the right thing because the XSL stylesheets surround
# <email> content with <> on output.
emailRe = re.compile(r"\b(?:&lt;)?(?P<email>[-\w_.]+@[-\w_.]+)(?:&gt;)?\b")

# Match an URL. This pattern is carefully constructed not to eat
# a following period if (as is often the case) it occurs at the
# end of a sentence.
urlRe=re.compile(r"(?P<url>\b(http|ftp|telnet|mailto)://[-_%\w/&;.~]+[-_%\w/&;])")

# Match a xmlns URL in the top level tag, so that the urlRe does not try to ulink-ize it.
xmlnsRe=re.compile(r"\w xmlns='http://docbook.org/ns/docbook'")

# Match a troff highlight
troffHighlight = re.compile(r"(\\[fF]\([A-Z][A-Z])|(\\f\[[A-Z]*\])|(\\[fF][A-Z0-9])|(\\F\[\])")
troffHighlightStripper = re.compile(r"^\.[BI] ")

# Match a glue token with all preceding and following whitespace
hotglue = re.compile(r"\s*@GLUE@\s*")
cleantag = re.compile(r"</([a-z]+)><\1>")

# Match an identifier token in C or Python
idRe = re.compile("^[_a-zA-Z][_a-zA-Z0-9]*$")

# List how troff specials that can appear as list tags map into
# DocBook mark types.  According to Norm Walsh's DSSL and XSL
# stylesheets, both toolchains have two styles available; bullet and
# box.  An older version of the DocBook documentation said that in
# itemizedlists the attributes can be the three names HTML supports: "disc",
# "circle", and "square", with "bullet" as a synonym for "disc" and
# "box" as a synonym for "square".  We map dash to box here for consistency
# with the -dash/-bullet distinction in mdoc, where -dash can only
# reasonably be mapped to box rather than disc.
ipTagMapping = {
    r"\(bu":"bullet",
    r"\(sq":"box",
    "*" : "bullet",
    "-" : "box",
    }

# Add this to the V4 preamble when we have MathML elements
mathmlEntities = '''<!ENTITY % MATHML.prefixed "INCLUDE">
<!ENTITY % MATHML.prefix "mml">
<!ENTITY % equation.content "(alt?, (graphic+|mediaobject+|mml:math))">
<!ENTITY % inlineequation.content
                "(alt?, (graphic+|inlinemediaobject+|mml:math))">
<!ENTITY % mathml PUBLIC "-//W3C//DTD MathML 2.0//EN"
        "http://www.w3.org/Math/DTD/mathml2/mathml2.dtd">
%mathml;
'''

# Add this to the V5 preamble when we have entities
allent = '''<!DOCTYPE article [
<!ENTITY % allent SYSTEM "http://www.w3.org/2003/entities/2007/w3centities-f.ent">
%allent;
]>'''

# Convert empty man pages generated by POD, but be rude about it.
rudeness = """This empty page was brought to you by brain damage somewhere in POD,
the Perl build system, or the Perl maintainers' release procedures.\
"""
empty = """\
<refsect1><title>Description</title>
<para>""" + rudeness + """</para>
</refsect1>
</refentry>
"""

# Verbosity thresholds for debugging
generalVerbosity	= "g"	# More details on warnings
sectionVerbosity	= "s"	# Show section pushes and pops
classifyVerbosity	= "c"	# Show section classification details
parseVerbosity  	= "p"	# Show synopsis parse details
macroVerbosity  	= "m"	# Show expression evaluation details
highlightVerbosity	= 'h'	# Show highlight resolution details
ioVerbosity     	= "i"	# Show low-level I/O
interpreterVerbosity	= "z"	# Show low-level interpreter checks
bsdVerbosity 		= 'b'   # BSD macroexpansion
tokenizerVerbosity	= 'x'	# Tokenizer verbosity
timingVerbosity 	= 't'   # Execution profiling
supersubVerbosity	= 'u'	# Super/subscript recognition velocity.
namesectionVerbosity	= 'n'	# Name section parsing

def deemphasize(st):
    "Throw out highlighting info from a string."
    return troffHighlight.sub("", st)

def isCommand(line):
    # This works around a common bug -- string-enclosing ' at the left margin
    return len(line) > 1 and \
           (line[0] == TroffInterpreter.ctrl or (line[0] == TroffInterpreter.ctrlNobreak and line[1:].find(TroffInterpreter.ctrlNobreak) == -1))

def isComment(line):
    # The malformed crap people write as troff comments is amazing...
    line = line.replace(" ", "").replace("\t", "")
    return line == TroffInterpreter.ctrl or line == TroffInterpreter.ctrlNobreak or line[:3] in (r'.\"', r'/\"', r'./"', r".\'", '\'\\"', r'\'\"', r'\".', r"...", r"'''", r"\!.") or line[:2] in (r'."', r".'", r'\"', r"'#", r"\#") or line[:4] in (r'.\\"', r"'.\"")

def matchCommand(line, tag):
    # Cope with the possibility of spaces after the dot
    if not line or line[0] not in (TroffInterpreter.ctrl, TroffInterpreter.ctrlNobreak):
        return False
    tokens = line[1:].strip().split()
    return tokens and tokens[0] == tag

def quoteargs(tokens):
    "Quote argument tokens so that re-parsing them won't produce surprises."
    if len(tokens) == 0:
        return ""
    elif len(tokens) == 1:
        return tokens[0]
    else:
        return tokens[0] +  ' "' + '" "'.join([x.replace('"', '""') for x in tokens[1:]]) + '"'

#def untagged(pattern):
#    "Transform the pattern to guarantee that it won't match marked-up text."
#    # Warning!  Only really works with fixed-length patterns.
#    return reCompile("(?<!>)" + pattern.pattern + "(?!</)")

def fontclose(istr):
    "Make sure we exit interpretation of the given string in normal font."
    lastFontEscape = istr.rfind(r'\f')
    if lastFontEscape > -1 and istr[lastFontEscape+2] not in "R":
        istr += r"\fR"
    istr = reCompile(r"\f[^P]\fR$").sub(r"\fR", istr)
    lastFontEscape = istr.rfind(r'\F')
    if lastFontEscape > -1 and istr[lastFontEscape+2:lastFontEscape+4] != "[]":
        istr += r"\f[]"
    return istr

def getXmlChar(istr):
    "Extract a leading character or XML escape from the string."
    if len(istr) == 0:
        return ""
    elif istr[0] != "&":
        return istr[0]
    else:
        take = 1
        while istr[take] != ';':
            take += 1
    return istr[:take+1]

def makeComment(istr):
    if istr.startswith("."):
        istr = istr[1:]
    istr = istr.replace(r'\"', "").replace(r'\\"', "").replace(r'\(co', "(C)")
    istr = istr.strip()
    return "<!-- " + istr.replace("-", r"\\-") + " -->"

def lineparse(line):
    "Parse arguments of a dot macro."
    if not isCommand(line):
        return None
    #stderr.write("About to parse: " + line + "\n")
    tokens = [line[0]]
    state = 'dot'		# Start after the dot in dot state
    for c in line[1:]:
        if state == 'dot':		# accumulating a token
            if c in (" ", "\t"):
                continue
            else:
                tokens[-1] += c
                state = 'token'
        elif state == 'token':		# accumulating a token
            if c in (" ", "\t"):
                state = 'ws'
            elif c == '\\':
                tokens[-1] += '\\'
                state = 'tokencont'
            else:
                tokens[-1] += c
        elif state == 'tokencont':		# accumulating a token
            if c in (" ", "\t", "\n"):
                tokens[-1] = tokens[-1][:-1]
            tokens[-1] += c
            state = 'token'
        elif state == 'ws':	# in whitespace
            if c in (" ", "\t"):
                continue
            elif c == '"':
                tokens.append('"')
                state = 'string'
            elif c == '\\':
                state = 'leader?'
            else:
                tokens.append(c)
                state = 'token'
        elif state == 'string':		# in string
            tokens[-1] += c
            if c == '"':
                state = 'stringend'
        elif state == 'stringend':	# just saw end-of-string, what now?
            if c == '"':
                state = 'string'
            elif c in (" ", "\t", "\n"):
                state = 'ws'
            elif c == '\\':
                state = 'leader?'
            else:
                state = 'token'
                tokens.append(c)
        elif state == 'leader?':	#  possible comment leader
            if c == '"':
                break
            elif c in (" ", "\t", "\n"):
                tokens.append(c)
                state = 'token'
            else:
                tokens.append("\\" + c)
                state = 'token'
    # Special case: turn trailing brackets into an argument
    if len(tokens) == 1:
        trailer = tokens[0][3:5]
        if trailer in (r"\{", r"\}"):
            tokens[0] = tokens[0][:3]
            tokens.append(trailer)
    return tokens

def stripquotes(arg):
    "Perform quote-stripping appropriate for macros and .ds commands."
    if type(arg) == type([]):
        return list(map(stripquotes, arg))
    else:
        if arg and arg[0] == '"':
            arg = arg[1:]
        if arg and arg[-1] == '"':
            arg = arg[:-1]
        return arg

class LiftException(BaseException):
    def __init__(self, source, message, retval=1):
        self.source = source
        self.message = message
        self.retval = retval
    def __str__(self):
        legend = '"%s"' % (spoofname or self.source.file)
        if self.source.lineno:
            legend += ', line %d' % (self.source.lineno)
        if self.message:
            legend += ": " + self.message
        return legend

class Dropout(BaseException):
    pass

class SemanticHintsRegistry:
    "Represent all the semantic information gathered during a run."
    def __init__(self):
        self.dictionary = {}
    def post(self, token, ptype):
        "Post an association of a string with a semantic markup type."
        #stdout.write("Markup %s as %s\n" % (token, ptype))
        self.dictionary[token] = ptype
    def get(self, token):
        return self.dictionary.get(token)
    def apply(self, text):
        "Apply all known hints to lift tokens in a text string."
        # stderr.write("Marked tokens:" + repr(self.dictionary) + "\n")
        for (token, tag) in list(self.dictionary.items()):
            withHi = r"<emphasis\s+remap='[A-Z]+'>(%s)</emphasis>" % token
            #stdout.write("marking %s as %s via %s\n" % (token, tag, withHi))
            try:
                ender = tag.split()[0]	# discard attributes
                text = reCompile(withHi).sub(r"<%s>\1</%s>"%(tag,ender),text)
                text = reCompile(r"\b("+token+")\b").sub(r"<%s>\1</%s>" % (tag, ender), text)
            except re.sre_compile.error:
                pass
        return text
    def read(self, rinput):
        "Read in a hints string or file as dumped by __str__"
        if hasattr(rinput, "read"):
            fp = open(rinput)
            data = fp.readlines()
            fp.close()
        else:
            data = rinput.split('\n')
        for line in data:
            if line.startswith('.\\" | '):
                # Someday we'll have more declarations
                try:
                    (mark, token, asWord, markup) = line[5:].split()
                    if mark != "mark" or asWord != "as":
                        continue
                    self.post(token, markup)
                except ValueError:
                    continue
    def __repr__(self):
        "Dump a representation of hint info."
        out = '.\\" Begin doclifter.py hints.\n'
        for (token, tag) in list(self.dictionary.items()):
            out += '.\\" | mark %s as %s\n' % (token, tag)
        out += '.\\" End doclifter.py hints.\n'
        return out

class Frame:
    "Frame state for the list-markup stack."
    def __init__(self, command, ftype):
        self.command = command
        self.type = ftype
        self.count = 0
    def __repr__(self):
        return "<Frame: " + repr(self._dict__) + ">"

class DocLifter:
    "DocBook translation of generic troff macros."
    # In each tuple, the first element is an emphasis remap attribute.
    # The second element is a regexp to match to the tag content.
    # If the regexp matches, the bracketing emphasis tags are replaced
    # with the semantic tag in the third column.
    liftHighlights = [(reCompile(r"<emphasis\s+remap='%s'>(%s)</emphasis>" % (x[0], x[1])), x[2]) for x in (
        ("SM",	r"[A-Z.]*",	"acronym"),	# Historical -- SM is rare
        ("SM",	r"[A-Z]+_[A-Z_]+",	"envar"),	# In bison.1, cvs.1
        ("[BI]",r"-[^<]+",	"option"),	# likely command option man(7)
        ("[BI]",r"[0-9.]+",	"literal"),	# literal value
        ("[BI]",r"[a-zA-Z0-9.]+((\s|&nbsp;)--?[^<]+)+",	"userinput"),	# user command
        ("[BI]",r"\.[a-zA-Z][^<]*",	"markup"),	# roff markup
        ("[BI]",r"/[^<]+",	"filename"),	# Marked filenames
        ("[BI]",r"~/[^<]*",	"filename"),	# Home directory filenames
        ("[BI]",emailRe.pattern,"email"),	# email addresses
        ("[BI]",r"SIG[A-Z]+",	"constant"),	# signal
        ("[BI]",r"errno",	"varname"),	# variable
        ("[BI]",r"[a-z_]*_t",	"type"),
        ("[BI]",r"[a-z_]+(?:\(\))", "function"),
        # Error codes.  This is the Linux set.
        ("[BI]",r"E2BIG",	"errorcode"),
        ("[BI]",r"EACCES",	"errorcode"),
        ("[BI]",r"EAGAIN",	"errorcode"),
        ("[BI]",r"EBADF",	"errorcode"),
        ("[BI]",r"EBADMSG",	"errorcode"),
        ("[BI]",r"EBUSY",	"errorcode"),
        ("[BI]",r"ECANCELED",	"errorcode"),
        ("[BI]",r"ECHILD",	"errorcode"),
        ("[BI]",r"EDEADLK",	"errorcode"),
        ("[BI]",r"EDOM",	"errorcode"),
        ("[BI]",r"EEXIST",	"errorcode"),
        ("[BI]",r"EFAULT",	"errorcode"),
        ("[BI]",r"EFBIG",	"errorcode"),
        ("[BI]",r"EINPROGRESS",	"errorcode"),
        ("[BI]",r"EINTR",	"errorcode"),
        ("[BI]",r"EINVAL",	"errorcode"),
        ("[BI]",r"EIO",		"errorcode"),
        ("[BI]",r"EISDIR",	"errorcode"),
        ("[BI]",r"EMFILE",	"errorcode"),
        ("[BI]",r"EMLINK",	"errorcode"),
        ("[BI]",r"EMSGSIZE",	"errorcode"),
        ("[BI]",r"ENAMETOOLONG","errorcode"),
        ("[BI]",r"ENFILE",	"errorcode"),
        ("[BI]",r"ENODEV",	"errorcode"),
        ("[BI]",r"ENOENT",	"errorcode"),
        ("[BI]",r"ENOEXEC",	"errorcode"),
        ("[BI]",r"ENOLCK",	"errorcode"),
        ("[BI]",r"ENOMEM",	"errorcode"),
        ("[BI]",r"ENOSPC",	"errorcode"),
        ("[BI]",r"ENOSYS",	"errorcode"),
        ("[BI]",r"ENOTDIR",	"errorcode"),
        ("[BI]",r"ENOTEMPTY",	"errorcode"),
        ("[BI]",r"ENOTSUP",	"errorcode"),
        ("[BI]",r"ENOTTY",	"errorcode"),
        ("[BI]",r"ENXIO",	"errorcode"),
        ("[BI]",r"EPERM",	"errorcode"),
        ("[BI]",r"EPIPE",	"errorcode"),
        ("[BI]",r"ERANGE",	"errorcode"),
        ("[BI]",r"EROFS",	"errorcode"),
        ("[BI]",r"ESPIPE",	"errorcode"),
        ("[BI]",r"ESRCH",	"errorcode"),
        ("[BI]",r"ETIMEDOUT",	"errorcode"),
        ("[BI]",r"EXDEV",	"errorcode"),
        # Standard environment variables from environ(5).
        ("[BI]","USER",		"envar"),
        ("[BI]","LOGNAME",	"envar"),
        ("[BI]","HOME",		"envar"),
        ("[BI]","LANG",		"envar"),
        ("[BI]","PATH",		"envar"),
        ("[BI]","PWD",		"envar"),
        ("[BI]","SHELL",	"envar"),
        ("[BI]","TERM",		"envar"),
        ("[BI]","PAGER",	"envar"),
        ("[BI]","EDITOR",	"envar"),
        ("[BI]","VISUAL",	"envar"),
        ("[BI]","BROWSER",	"envar"),
        # Common library environment variables, also from environ(5)
        ("[BI]","LANG",		"envar"),
        ("[BI]","LANGUAGE",	"envar"),
        ("[BI]","NLSPATH",	"envar"),
        ("[BI]","LOCPATH",	"envar"),
        ("[BI]","LC_ALL",	"envar"),
        ("[BI]","LC_MESSAGES",	"envar"),
        ("[BI]","TMPDIR",	"envar"),
        ("[BI]","LD_LIBRARY_PATH",	"envar"),
        ("[BI]","LD_PRELOAD",	"envar"),
        ("[BI]","POSIXLY_CORRECT",	"envar"),
        ("[BI]","HOSTALIASES",	"envar"),
        ("[BI]","TZ",		"envar"),
        ("[BI]","TZDIR",	"envar"),
        ("[BI]","TERMCAP",	"envar"),
        ("[BI]","COLUMNS",	"envar"),
        ("[BI]","LINES",	"envar"),
        ("[BI]","PRINTER",	"envar"),
        ("[BI]","LPDEST",	"envar"),
    )]
    postTranslationPatterns = (
        # man(7)-style man-page references
        (re.compile(r"<emphasis (role='[a-z_]*' )?remap='[BI]'>([^ ]+)</emphasis>(?:&zerosp;|&thinsp;)?\(([0-9]+[A-Za-z]?)\)"),
         r"<citerefentry><refentrytitle>\2</refentrytitle><manvolnum>\3</manvolnum></citerefentry>"),
        # Here's where we fold all those continuation lines.
        (re.compile(r"\\c</emphasis>"), "</emphasis>\n"),
        (re.compile("\\\c\n"),	""),
        # Interpret attempts to fake up double quotes.  Should be safe as
        # these never occur in program listings.
        (re.compile("``([^`']+)''"), r"&ldquo;\1&rdquo;"),
        )
    postLiftPatterns = (
         # Find a highlight directly after an <option> makes it <replaceable>
        (re.compile(r"(<option>[^ ]+</option>\s*)<emphasis remap='[BI]'>([^<]+)</emphasis>"),
         r"\1<replaceable>\2</replaceable>"),
	# Find a replaceable in square brackets after an  option
        (re.compile(r"(<option>[^ ]+</option>\s*)\[<emphasis remap='[BI]'>([^<]+)</emphasis>\]"),
         r"\1<replaceable>\2</replaceable>"),
       )

    tabset       = re.compile(r"tab *\(?(.)\)?")

    pretranslations = (
     # The ultimate in decompiling presentation markup...
     (r"e\h'-\w:e:u'\`", r"\(`e"),	# gawk.1
     (r"e\h'-\w:e:u'\'", r"\('e"),	# gawk.1
     (r"T\h'-.1667m'\v'.224m'E\v'-.224m'\h'-.125m'X", r"TeX"),	# geqn.1
     (r"\h'-\w' 'u' ", r""),		# procmail.1
     (r"\l'\n(.lu'", ".DOCLIFTER-HR"),	# spax.1
     (r"L\h'-0.36'\v'-0.15'\s-2A\s+2\v'0.15'\h'-0.15'T\h'-0.1667'\v'0.2'E\v'-0.2'\h'-0.125'X", "LATEX"),		 # ctanify.1
     (r"T\h'-0.1667'\v'0.2'E\v'-0.2'\h'-0.125'X", "TeX"),	# ctanify.1
     (r"\h'-04'\(bu\h'+03'", r"\(bu"),	# Various systemd pages
     # Ugh.  These string definitions from inifile.1 and
     # elsewhere aren't used in the nroff mode we're emulating.
     # They have to be removed early because of the way they
     # interact with other transformations.
     (r"\*(T<",	""),
     (r"\*(T>",	""),
     )

    # In each tuple, the first element is an emphasis remap attribute.
    # The second element is a regexp to match to the tag content.
    # If the regexp matches, and the content grouped by parentheses
    # looks like an id that was created during translation, then the
    # emphasis tags are replaced with a link tag with the target being
    # the result of converting the tag contents to an XML id.
    liftLinks = (
        ("SM",	r"[A-Z ]+"),	# Used in RCS and others
        ("Em",	r"[A-Z ]+"),	# Used in csh.1
        ("B",	r"[A-Z ]+"),	# Used in java.1, refer.1
      )

    # These are entities that don't exist in the ISO set but are in Unicode.
    # They may be generated by our translation logic.  If so, the right
    # entity declaration has to get emitted into the preamble.
    pseudoEntities = (
        # These are from troff classic
        ("lh",	"&#x261E;"),	# Hand pointing left
        ("rh",	"&#x261C;"),	# Hand pointing right
        ("CR", 	"&#x240D;"),	# Carriage-return symbol
        ("fo", 	"&#x2039;"),	# Single left-pointing quotation mark
        ("fc", 	"&#x203a;"),	# Single right-pointing quotation mark
        ("an",  "&#x23af;"),	# horizontal line (arrow) extension
        # Troff classic pile brackets are in abbreviation order
        ("lb",	"&#x23a9;"),	# Left curly bracket lower hook
        ("lc",	"&#x23a1;"),	# Left square bracket upper corner
        ("lf",	"&#x23a3;"),	# Left square bracket lower corner
        ("lk",	"&#x23a8;"),	# Left curly bracket middle piece
        ("tlt",	"&#x23a7;"),	# Left curly bracket upper hook
        ("rb",	"&#x23ad;"),	# Right curly bracket lower hook
        ("rc",	"&#x23a4;"),	# Right square bracket upper corner
        ("rf",	"&#x23a6;"),	# Right square bracket lower corner
        ("rk",	"&#x23ac;"),	# Right curly bracket middle piece
        ("rt",	"&#x23ab;"),	# Right curly bracket upper hook
        # These are characters with diacriticals from groff
        ("yogh", "&#x021d;"),	# Small letter yogh
        ("ohook", "&#x01a1;"),	# Small letter o with hook or ogonek
        ("udot",  "&#x0323;"),	# Combining underdot.
        ("braceex", "&#x23aa;"),
        # These are groff pile brackets
        ("bracketlefttp", "&#x23a1;"),
        ("bracketleftbt", "&#x32a3;"),
        ("bracketleftex", "&#x23a2;"),
        ("bracketrighttp", "&#x23a4;"),
        ("bracketrightbt", "&#x32a6;"),
        ("bracketrightex", "&#x23a5;"),
        ("braceleftex", "&#x23aa;"),
        ("bracerightmid", "&#x23ac;"),
        ("bracerightex", "&#x23aa;"),
        ("parenlefttp", "&#x239b;"),
        ("parenleftbt", "&#x239d;"),
        ("parenleftex", "&#x239c;"),
        ("parenrighttp", "&#x239e;"),
        ("parenrightbt", "&#x23a0;"),
        ("parenrightex", "&#x239f;"),
        # These are groff radical extentions.  What we're doing here
        # is just mapping them to the Unicode macron. This is not
        # going to be great typesetting....
        ("radicalex", "&#x203e;"),
        ("sqrtex", "&#x203e;"),
        # jnodot exists in Unicode, but the DocBook stylesheets don't know it.
        # Someday we should be able to remove this.
        ("jnodot", "&#0237;"),
        # Bug: &numsp; should be included by the v4 DocBook DTD,
        # but apparently it isn't.
        ("numsp", "&#x2007;"),
        # Found in the BSD tree(3) page
        ("lp", "("),
        ("rp", ")"),
        )

    def __reinit__(self):
        "Null out the parser state."
        self.toptag = None
        self.ignoreSet = set([])
        self.listbreakSet = set([])
        self.scopedSet = set([])
        self.complainSet = set([])
        self.outsubst = []
        self.sectname = None
        self.nonblanks = 0
        self.idlist = {}
        self.listitem = False
        self.sectionhooks = []
        self.fontfamily = ""
        self.synopsis = None	# Never gets this value once one has been seen
        self.synopsisFlushed = False
        self.sectionCount = 0
        self.transplant = []
        self.complaints = {}
        self.stashIndents = []
        self.trapPrefix = None
        self.trapSuffix = None
        self.errorcount = 0
        self.stashId = None
        self.displaystack = []
        self.picSeen = False
        self.eqnSeen = False
        self.localentities = []
        self.lines = None
        self.eqnsub = None
        self.file = None
        self.lineno = 0
        self.pushdown = []		# Stack of input sources
        self.physlines = 0
        self.highlight = "R"
        self.oldhighlight = "R"
        self.inPreamble = True
        self.eqnProcessed = False
        self.bodyStart = 0
        self.needPara = False
        self.sectiondepth = 0
        self.output = []
        self.inclusions = []
        self.multiarg = False
        self.troff = None
        self.interpreters = []
        self.diversion = None
        self.name = None
        self.tabstops = None
        self.localhints = None
        self.basetime = None
        self.starttime = None

    def __init__(self, verbose="",
                 quiet=0,
                 portability=0,
                 includepath="",
                 inEncodings=(),
                 outEncoding='UTF-8',
                 docbook5=True):
        self.verbose = verbose
        self.quiet = quiet
        self.portability = portability
        self.includepath = includepath
        self.inEncodings = inEncodings
        self.outEncoding = outEncoding
        self.docbook5 = docbook5
        self.__reinit__()

    def bodySection(self):
        "Are we in a section that corresponds to a real refentry section?"
        return self.bodyStart
    def declareBodyStart(self):
        "Latch the location where the document body starts."
        if not self.bodyStart:
            self.bodyStart = len(self.output)
            if not self.quiet:
                self.emit(makeComment("body begins here"))

    # I/O utility code
    def popline(self):
        "Pop a line off the input source."
        self.physlines = 0
        line = ""
        while self.lines:
            physline = self.lines.pop(0)
            # Not clear why this is needed...
            if physline is None:
                return None
            self.physlines += 1
            # Perhaps we just hit a marker for end of macroexpansion
            if type(physline) == type(0):
                self.lineno = self.troff.linenos.pop()
                self.troff.macroargs.pop()
                self.troff.macronames.pop()
                continue
            # Folding lines after \{\ screws up the conditional-evaluation code
            if len(physline) > 0 and physline[-1] == '\\' and not (len(physline) > 1 and physline[-2] in ('\\', '{')):
                line += physline[:-1]
                continue
            else:
                line += physline
            if ioVerbosity in self.verbose:
                self.notify("popped: " + line)
            self.lineno += self.physlines
            return self.troff.expandStrings(line)
        return None
    def pushline(self, line):
        "Push a line back on to the input source"
        if ioVerbosity in self.verbose:
            self.notify("pushed: %s" % line)
        self.lines = [line] + self.lines
        self.lineno -= self.physlines
    def peekline(self):
        "Look ahead in the input stream."
        # Has to be done with a pop/push, in case we hit the end of a macro
        line = self.popline()
        self.pushline(line)
        return line
    def macroReturn(self):
        "Skip the remainder of the current macro."
        if not self.troff.macroargs:
            self.notify("warning: return outside of macro")
        else:
            while True:
                line = self.lines.pop(0)
                self.lineno += 1
                if type(line) == type(0):
                    self.lineno = self.troff.linenos.pop()
                    self.troff.macroargs.pop()
                    self.troff.macronames.pop()
                    break
    def notify(self, msg):
        "C-compiler-like error message format."
        if self.troff.macronames:
            msg = '%s:%d: expanding %s: %s\n' % (spoofname or self.file, self.lineno, self.troff.macronames[-1], msg)
        else:
            msg = '%s:%d: %s\n' % (spoofname or self.file, self.lineno, msg)
        stderr.write(msg)
        return msg
    def filewarn(self, msg):
        msg = '"%s": warning - %s\n' % (spoofname or self.file, msg)
        stderr.write(msg)
        return msg
    def warning(self, msg):
        msg = self.notify("warning - " + msg)
        return msg
    def error(self, msg):
        msg = self.notify("error - " + msg)
        self.errorcount += 1
        return msg
    def passthrough(self, tokens, complain=None):
        if complain == None:
            complain = not self.quiet
        if complain:
            self.emit(makeComment(" ".join(tokens)))
    def trapEmit(self, prefix, suffix=""):
        self.trapPrefix = prefix
        self.trapSuffix = suffix
        self.needPara = False
    def emit(self, line, trans=1):
        "Emit output."
        if ioVerbosity in self.verbose:
            self.notify("emit(%s, trans=%d)" % (repr(line), trans))
        # Perhaps we've set a line trap?
        if self.trapPrefix or self.trapSuffix:
            if not line.startswith("<!--") and not blankline.match(line):
                self.pushline(self.trapPrefix + line + self.trapSuffix)
                self.trapPrefix = self.trapSuffix = ""
            return
        # This test avoids a lot of expensive code on most lines
        if '\\' in line:
            # Where entity expansion gets done
            line = self.expandEntities(line)
            # Handle troff point changes.
            if self.inSynopsis():
                line = reCompile(r"\\s([+-]?[0-9]+)").sub("", line)
            else:
                line = reCompile(r"\\s([+-]?[0-9]+)").sub(r"<?troff ps \1?>",line)
            # Some escape translations should be done at this point.
            # This deals with some uses of \h for temporary indenting.
            # There's an example in tvtime-command.1.
            spacer = reCompile(r"\\h'([0-9]+)n'")
            while True:
                m = spacer.search(line)
                if m:
                    line = line[:m.start(0)] + ("&ensp;" * int(m.group(1))) + line[m.end(0):]
                else:
                    break
            # Interpolate numeric registers
            while '\\n' in line:
                before = line[:line.find('\\n')]
                after = line[line.find('\\n'):]
                (head, tail) = self.troff.evalTerm(after)
                line = before + head + tail
        # Check to see if output translation is enabled.
        if trans and self.outsubst:
            doXlate = True
            translated = ""
            i = 0
            while i < len(line):
                if line[i] == '<':
                    doXlate = 0
                if not doXlate:
                    if line[i] == '>':
                        doXlate = True
                    translated += line[i]
                    i += 1
                else:
                    substituted = False
                    for (old, new) in self.outsubst:
                        if line[i:i+len(old)] == old:
                            translated += new
                            i += len(old)
                            substituted = True
                    if not substituted:
                        translated += line[i]
                        i += 1
            line = translated
        # Last thing to do is tab expansion
        if '\t' in line and self.tabstops:
            expanded = ""
            for c in line:
                if c != '\t':
                    expanded += c
                else:
                    for stop in self.tabstops:
                        if stop > len(expanded):
                            break
                    if stop > len(expanded):
                        expanded += " " * (stop - len(expanded))
                    else:
                        expanded += '\t'
            line = expanded
        # And now we actually append it to the current diversion
        self.diversion.append(line)
        if line and not line.startswith("<!--"):
            self.nonblanks += 1
    def endswith(self, trailer):
        "Check for a match with the end of what we've emitted."
        return self.diversion and self.diversion[-1].strip().endswith(trailer)

    # Synopsis handling
    def flushTransplant(self):
        if self.synopsisFlushed:
            return
        else:
            self.synopsisFlushed = True
        if self.synopsis:
            (parsed, warnuser) = self.synopsis.transform()
            if self.docbook5:
                self.emit("<refsynopsisdiv xml:id='%s'>\n%s</refsynopsisdiv>\n" \
                        % (self.makeIdFromTitle('synopsis'), parsed))
            else:
                self.emit("<refsynopsisdiv id='%s'>\n%s</refsynopsisdiv>\n" \
                        % (self.makeIdFromTitle('synopsis'), parsed))
            if warnuser:
                self.warning("dubious content in Synopsis")
        # If there's a transplant, emit it now.
        self.declareBodyStart()
        self.output += self.transplant

    # Section-break handlers
    def endParagraph(self, label="random"):
        "Close the current paragraph, if we're in one."
        if sectionVerbosity in self.verbose:
            self.notify("endParagraph(%s)" % label)
        self.troff.nf = False
        self.needPara = False
    def needParagraph(self):
        "Cause <para> to be prepended to next text line."
        if sectionVerbosity in self.verbose:
            self.notify("needParagraph()")
        self.needPara = True
    def paragraph(self, remap=""):
        "Replace generic paragraph-start macro with blank line."
        if sectionVerbosity in self.verbose:
            self.notify("paragraph(remap='%s')" % remap)
        self.endParagraph("paragraph")
        if not self.quiet:
            if remap:
                self.emit(makeComment(remap))
            else:
                self.emit("")
        self.needParagraph()
    def popSection(self, depth):
        "Pop to new section level."
        if sectionVerbosity in self.verbose:
            self.notify("popSection(%d)" % depth)
        self.poplist()	# Terminate all list structure
        toplevel = (depth == 1) and (self.sectiondepth == 1)
        self.troff.nf = False
        self.endParagraph(label="popSection")
        self.needPara = False
        # Execute any traps user might have planted.
        for hook in self.sectionhooks:
            hook()
        # What does the divider look like?
        if self.toptag == "refentry":
            divider = "refsect"
        else:
            divider = "sect"
        try:
            # Detect blank top-level section and don't emit it.
            # Un-emit the header for it, too.
            if toplevel and self.nonblanks == 0:
                while True:
                    line = self.diversion.pop()
                    if line.startswith("\n<" + divider):
                        break
                return
            # If section wasn't blank, emit end of section
            for i in range(self.sectiondepth - depth + 1):
                self.emit("</%s%d>" % (divider, self.sectiondepth - i))
        finally:
            self.sectiondepth = depth
    def pushSection(self, depth, title, makeid=True):
        "Start new section."
        self.sectionCount += 1
        if sectionVerbosity in self.verbose:
            self.notify("pushSection(%d, %s)" % (depth, title))
        self.popSection(depth)
        if self.toptag == "refentry":
            ref = "ref"
        else:
            ref = ""
        if self.stashId:
            if self.docbook5:
                sid = " xml:id='%s'" % self.stashId
                self.stashId = None
            else:
                sid = " id='%s'" % self.stashId
                self.stashId = None
        elif makeid:
            if self.docbook5:
                sid = " xml:id='%s'" % self.makeIdFromTitle(title)
            else:
                sid = " id='%s'" % self.makeIdFromTitle(title)
        else:
            sid = ""
        self.emit("\n<%ssect%d%s><title>%s\\fR</title>" % (ref, depth, sid, title))
        self.needParagraph()
        self.sectiondepth = depth
        self.sectname = title
        self.sectionhooks = []
        self.nonblanks = 0
    def paragraphBreak(self, line):
        "Are we looking at a paragraph break command?"
        if line.startswith(TroffInterpreter.ctrl + "end"):
            return True
        elif not isCommand(line):
            return False
        else:
            tokens = lineparse(line)
            if tokens:
                for interpreter in self.interpreters:
                    if tokens[0][1:] in interpreter.parabreakSet:
                        return True
                    if tokens[0][1:] in interpreter.sectionbreakSet:
                        return True
        return False
    def sectionBreak(self, line):
        "Are we looking at a section break command?"
        if line.startswith(TroffInterpreter.ctrl + "end"):
            return True
        elif not isCommand(line):
            return False
        else:
            tokens = lineparse(line)
            if tokens:
                for interpreter in self.interpreters:
                    if tokens[0][1:] in interpreter.sectionbreakSet:
                        return True
        return False

    def indent(self):
        return len(self.stashIndents) * "  "

    def beginBlock(self, markup, remap=""):
        "Begin a block-context markup section."
        if ioVerbosity in self.verbose:
            self.notify("beginBlock(%s)" % markup)
        self.endParagraph(label="beginBlock")
        if remap and not self.quiet:
            remap = " remap='" + remap + "'"
        if markup in ("literallayout", "programlisting"):
            self.troff.nf = True
            if ioVerbosity in self.verbose:
                self.warning("begin display collection")
            self.displaystack.append((markup, remap, DisplayParser(self,
                                                                   True,
                                                                   True,
                                                                   {})))
        else:
            self.emit(self.indent() + "<" + markup + remap + ">")
            if markup != "inlineequation":
                self.needParagraph()

    def endBlock(self, markup, remap=""):
        "End a block-context markup section."
        # FIXME: use ends to ignore stray things that look like terminators
        if ioVerbosity in self.verbose:
            self.notify("endBlock(markup='%s', remap='%s')" % (markup, remap))
        if remap and not self.quiet:
            remap = " <!-- remap='" + remap + "' -->"
        self.troff.nf = False
        # Turn off all font highlights -- technically incorrect,
        # but almost always the right thing to do.  We also
        # probably need an end-paragraph here, but that will be
        # taken care of by closeTags() later on.
        if self.displaystack:
            (beginmarkup, beginremap, display) = self.displaystack.pop()
            (parsed, _) = display.transform()
            self.emit("<" + beginmarkup + beginremap + ">")
            self.emit(parsed + (r"\fR</%s>" % markup + remap))
        else:
            self.emit(self.indent() + r"\fR</%s>" % markup + remap)
        if markup != "inlineequation":
            self.needParagraph()

    def pushlist(self, cmd, ltype=None):
        if sectionVerbosity in self.verbose:
            self.notify("pushlist(%s, %s)" % (cmd, ltype))
        self.stashIndents.append(Frame(cmd, ltype))

    def poplist(self, backto=None, remap=""):
        "Pop levels off the list stack until we've removed specified command."
        if sectionVerbosity in self.verbose:
            self.notify("poplist(%s) %s" % (backto, self.stashIndents))
        while self.stashIndents:
            frame = self.stashIndents[-1]
            if frame.type == "variablelist":
                self.emitVariablelist("end")
            elif frame.type == "itemizedlist":
                self.emitItemizedlist("end")
            elif frame.type == "blockquote":
                self.endBlock("blockquote", remap=remap)
                self.stashIndents.pop()
            else:
                self.stashIndents.pop()
            if frame.command == backto:
                break
        if sectionVerbosity in self.verbose:
            self.notify("after popping %s" % (self.stashIndents,))

    def lastTag(self, lookfor):
        "What was the last actual tag emitted?"
        if not self.diversion:
            return False
        back = -1
        while True:
            backline = self.diversion[back].strip()
            if backline.startswith(lookfor):
                return back
            elif backline and backline.startswith("<!--"):
                pass
            elif backline and backline != '.blank':
                return False
            back -= 1

    def emitVariablelist(self, cmd, term=None):
        "Emit a portion of variable-list markup."
        if sectionVerbosity in self.verbose:
            self.notify("emitVariablelist(%s, %s) %s"%(cmd, repr(term), self.stashIndents))
        if cmd == "end":
            if self.stashIndents:
                indent = self.indent()
                self.stashIndents.pop()
                # Empty item with a bunch of .TP lines before it.
                # Retroactively hack this into an itemized list.
                if self.lastTag("<listitem"):
                    if self.verbose:
                        self.warning("variable-list header just before section break")
                    if sectionVerbosity in self.verbose:
                        self.notify("remaking as itemized")
                    backup = -1
                    while True:
                        line = self.diversion[backup]
                        if "<variablelist" in line:
                            self.diversion[backup] = line.replace("variable", "itemized")
                            break
                        elif "varlistentry" in line or "<listitem" in line:
                            self.diversion[backup] = ""
                        elif "term>" in line:
                            line = line.replace("<term>", "<listitem><para>")
                            line = line.replace("</term>", "</para></listitem>")
                            self.diversion[backup] = line
                        backup -= 1
                    self.emit("%s</itemizedlist>" % indent[2:])
                else:
                    # List has a <para> or something at start.
                    self.endParagraph()
                    self.emit("%s</listitem>" % indent)
                    self.emit("%s</varlistentry>" % indent)
                    self.emit("%s</variablelist>" % indent[2:])
            return
        # All cases below emit a <term> at least
        if not self.stashIndents or self.stashIndents[-1].command != cmd:
            if self.quiet:
                remap = ""
            else:
                remap = " remap='%s'" % cmd
            self.emit("%s<variablelist%s>" % (self.indent(), remap))
            self.pushlist(cmd, "variablelist")
        indent = self.indent()
        back = self.lastTag("<listitem")
        if back:
            self.diversion[back] = "<!-- DELETE ME! -->"
        else:
            if self.stashIndents[-1].count > 0:
                self.emit("%s</listitem>" % indent)
                self.emit("%s</varlistentry>" % indent)
            self.emit("%s<varlistentry>" % indent)
        if type(term) == type(""):
            self.emit("%s<term>%s</term>" % (indent, fontclose(term)))
        elif type(term) == type([]):
            for item in term:
                self.emit("%s<term>%s</term>" % (indent, fontclose(item)))
        self.emit("%s<listitem>" % indent)
        self.stashIndents[-1].count += 1
        self.needParagraph()

    def emitItemizedlist(self, cmd, bullet=None):
        "Emit a portion of itemized-list markup."
        if sectionVerbosity in self.verbose:
            self.notify("emitItemizedlist(%s) %s"%(cmd, self.stashIndents))
        if cmd == "end":
            if self.stashIndents:
                indent = self.indent()
                self.stashIndents.pop()
                if self.lastTag("<listitem"):
                    self.emit("<para> <!-- FIXME: blank list item -->")
                    self.warning("blank itemizedlist item, look for FIXME")
                self.endParagraph()
                self.emit("%s</listitem>" % indent)
                self.emit("%s</itemizedlist>" % indent[2:])
            return
        # All cases below emit a <listitem> at least
        if not self.stashIndents or self.stashIndents[-1].command != cmd:
            if self.quiet:
                remap = ""
            else:
                remap = " remap='%s'" % cmd
            self.emit("%s<itemizedlist%s>" % (self.indent(), remap))
            self.pushlist(cmd, "itemizedlist")
        indent = self.indent()
        back = self.lastTag("<listitem")
        if back:
            self.diversion[back] = "<!-- DELETE ME! -->"
        else:
            if self.stashIndents[-1].count > 0:
                self.emit("%s</listitem>" % indent)
        self.emit("%s<listitem override='%s'>" % (indent, bullet))
        self.stashIndents[-1].count += 1
        self.needParagraph()

    # Highlight handling
    def changeHighlight(self, htype, prefix='f'):
        if prefix == 'F':	# groff font family change
            if htype == 'T':
                htype = ''
            self.fontfamily = htype
            return ""
        else:			# ordinary font change
            real = htype
            pop = False
            if highlightVerbosity in self.verbose:
                log = "changeHighlight(%s) from %s" % (real, self.highlight)
            if htype == "0":
                pop = True
                htype = self.oldhighlight
            elif htype == "1" or htype == '[]':
                htype = "R"
            elif htype == "2":
                htype = "I"
            elif htype == "3":
                htype = "B"
            elif htype == "4":
                htype = "C"
            if htype == "P":
                pop = True
                htype = self.oldhighlight
            elif htype == self.highlight:
                if highlightVerbosity in self.verbose:
                    self.notify(log + " is a no-op")
                return ""
            if highlightVerbosity in self.verbose:
                log += ", mapped to %s" % htype
            if self.highlight == "R" or self.highlight == "[]":
                newhi = ""
            else:
                newhi = "</emphasis>"
            if htype != "R":
                role = ""
                if htype == "B":
                    role = "role='strong' " 
                if pop:
                    newhi += "<emphasis %sremap='P->%s%s'>" % (role, self.fontfamily,htype)
                else:
                    newhi += "<emphasis %sremap='%s%s'>" % (role, self.fontfamily,htype)
            self.oldhighlight = self.highlight
            self.highlight = htype
            if highlightVerbosity in self.verbose:
                self.notify(log + (", used %s, last = %s" % (newhi, self.oldhighlight)))
            return newhi
    def directHighlight(self, highlight, args, trailer=""):
        "Translate man(7)-style ordinary highlight macros."
        if not args:
            line = self.popline()
            # Deals with broken stuff like the
            # .B
            # .BI -G num
            # on the gcc.1 man page.
            if line is None or isCommand(line):
                self.pushline(line)
                return makeComment("%s elided" % highlight)
        else:
            line = " ".join(args)
        if not trailer and line[-2:] == "\\c":
            trailer = "\\c"
            line = line[:-2]
        if len(highlight) > 1:
            highlight = "(" + highlight
        transformed = r"\f" + highlight
        transformed += line
        if highlight != "R":
            # Occasionally we see \ at end-of-line as somebody's error.
            # Prevent it from screwing us up.
            if transformed[-1] == '\\':
                transformed = transformed[:-1]
            transformed += r"\fR"	# Yes, see the definition of an-trap.
        transformed += trailer
        return transformed
    def alternatingHighlight(self, highlight, words, trailer=""):
        "Translate the screwy man(7)-style alternating highlight macros."
        if not words:
            nextl = self.popline()
            # Deals with broken stuff like the
            # .BR
            # .SH CUSTOMIZATION
            # on the MAKEDEV.8 manual page.
            if nextl is None or isCommand(nextl) or blankline.search(nextl):
                if nextl is not None:
                    self.pushline(nextl)
                return makeComment("bogus %s elided" % highlight)
            else:
                words = nextl.split()
        if not trailer and words[-1][-2:] == "\\c":
            trailer = "\\c"
            words[-1] = words[-1][:-2]
        count = 0
        line = ""
        for word in words:
            line += r"\f" + highlight[count % 2]
            line += word
            count += 1
        # Occasionally we see \ at end-of-line as somebody's error.
        # Prevent it from screwing us up.
        if line[-1] == '\\':
            line = line[:-1]
        line += r"\fR" + trailer
        return line
    def index(self, args):
        "Generic index markup."
        # Some manpages (in LPRng, for example) pass blank index keys to IX
        # because macroexpansion will do funky things with them.  Foil this
        # in order to cut down on useless error messages.
        args = [x for x in args if x != ""]
        if len(args) == 0:
            self.error("index macro must have at least one argument.")
        elif len(args) == 1:
            return "<indexterm><primary>%s</primary></indexterm>" % args[0]
        elif len(args) == 2:
            return "<indexterm><primary>%s</primary><secondary>%s</secondary></indexterm>" % (args[0], args[1])
        elif len(args) == 3:
            return "<indexterm><primary>%s</primary><secondary>%s</secondary><tertiary>%s</tertiary></indexterm>" % (args[0], args[1], args[2])
        else:
            self.warning("index macro has more than three arguments.")
            return "<indexterm><primary>%s</primary><secondary>%s</secondary><tertiary>%s</tertiary></indexterm> <!-- %s -->" % (args[0], args[1], args[2], " ".join(args[3:]))

    def idFromTitle(self, istr):
        "Turn a string into a section ID usable in link declarations."
        # First, remove any trailing section of the title in parens
        istr = re.sub(r" \(.*", "", istr)
        istr = istr.replace("&nbsp;", "-")
        # Smash out all characters that aren't legal in SGML ids, except spaces
        squashed = ""
        for c in istr:
            if c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ ":
                squashed += c
        squashed = squashed.strip()
        if squashed:
            # IDs cannot begin with whitespace, a dash or digits
            if squashed[0] in "_0123456789":
                squashed = "x" + squashed
            # Hack spaces, smash case, and enforce jade's jength limit
            newid =  squashed.replace(" ", "_").lower()[:40]
        else:
            # This case gets hit sometimes on CJK character sets
            newid = "g" + repr(time.time())
        if self.multiarg:
            return self.name + "-" + newid
        else:
            return newid
    def makeIdFromTitle(self, st):
        sid = self.idFromTitle(st)
        # We allow duplicate sections, but warn about them
        if sid not in self.idlist:
            self.idlist[sid] = 1
            return sid
        else:
            self.idlist[sid] += 1
            #self.error("more than one section is named %s" % st)
            return sid + repr(self.idlist[sid])

    def idExists(self, sid):
        "Test whether an id already exists"
        return sid in self.idlist
    def TBL(self, enddelim=None):
        "Translate and emit a tbl section."
        if enddelim == None:
            enddelim = TroffInterpreter.ctrl + "TE"
        # If there was a bolded line just before this, treat it as a title.
        title = None
        while self.diversion and not self.diversion[-1]:
            self.diversion.pop()
        if self.diversion and self.diversion[-1]:
            match = re.search(r"\\fB(.*)\\f[PR]", self.diversion[-1])
            if match:
                title = match.group(1)
                self.diversion[-1] = self.diversion[-1][:match.start(0)]
        # Real table.  First process global options
        alignment = 'center'
        allbox = box = expand = False
        tab = "\t"
        lastheaderline = -1
        options = self.lines[0]
        if options.endswith("&semi;"):
            taboption = DocLifter.tabset.search(options)
            if taboption:
                tab = taboption.group(1)
            options = options.replace("&semi;", "").replace(",", " ").split()
            self.lines.pop(0)
            for x in options:
                if   x == 'allbox':      allbox = True
                elif x == 'box':         box = True
                elif x == 'frame':       box = True
                elif x == 'center':      alignment = x
                elif x == 'doublebox':   box = True
                elif x == 'doubleframe': box = True
                elif x == 'expand':      expand = True
                elif x == 'left':        alignment = x
                elif x == 'right':       alignment = x
        # Now parse table format lines
        tbl = []
        fmtwidth = 0
        while True:
            line = self.lines.pop(0)
            fline = []
            fmt = ""
            for ch in line:
                if ch in "lrcnds^," and fmt:
                    fline.append(fmt)
                    fmt = ""
                fmt += ch
            fline.append(fmt)
            tbl.append(fline)
            if len(fline) > fmtwidth:
                fmtwidth = len(fline)
            if "." in line:
                break
        # Fill in missing format elements as copies of the rightmost ones
        for i in range(len(tbl)):
            if len(tbl[i]) < fmtwidth:
                tbl[i] += [tbl[i][-1]] * (fmtwidth - len(tbl[i]))
        # Grab all the data -- critical step that lets us do vertical spanning.
        data = []
        rowsep = []
        datawidth = 0
        comments = []
        while self.lines:
            tline = self.lines.pop(0)
            if tline.strip() == enddelim:
                break
            elif tline == TroffInterpreter.ctrl + "TH":
                lastheaderline = len(data)
            elif tline[-2:] == "T{":
                while self.lines:
                    continuation = self.lines.pop(0)
                    tline += "\n" + continuation
                    if continuation[:2] == "T}" and continuation[-2:] != "T{":
                        break
            comments.append(None)
            if not tline in ("_", "="):
                if '\\"' in tline:
                    cstart = tline.find('\\"')
                    comments[-1] = tline[cstart:]
                    tline = tline[:cstart].strip()
                fields = tline.split(tab)
                if len(fields) > datawidth:
                    datawidth = len(fields)
                for i in range(len(fields)):
                    if fields[i][:3] == "T{\n":
                        fields[i] = fields[i][3:]
                    if fields[i][-3:] == "\nT}":
                        fields[i] = fields[i][:-3]
                data.append(fields)
                rowsep.append(len(self.lines)>0 and self.lines[0] in ("_","="))
        # This code only runs if there is no TH and the table has a multiline
        # format spec.
        if lastheaderline == -1 and len(tbl) > 1:
            # Deduce location of last header format line.  It's the
            # format line before the last format line not to contain a
            # ^.  DocBook vertical spans can't cross the
            # table-header/table-body boundary, so there has to be at
            # least one table body format line not containing ^.
            lastheaderline = len(tbl) - 2
            try:
                for tbli in range(len(tbl)):
                    for j in range(len(tbl[tbli])):
                        if tbl[tbli][j][0] == '^':
                            lastheaderline = tbli - 2
                            raise Dropout
            except Dropout:
                pass
            if lastheaderline < 0 and rowsep:
                # Our first fallback is the location of the first ruler line.
                lastheaderline = rowsep.index(True)
        # Fill in missing data elements to match the widest data width
        for i in range(len(data)):
            data[i] += [""] * (datawidth - len(data[i]))
        # Fill in missing format elements to match the widest data width
        for i in range(len(tbl)):
            tbl[i] += [tbl[i][-1]] * (datawidth - fmtwidth)
        # Now that we have the data, copy the last format line down
        # enough times to cover all rows.
        tbl += [tbl[-1]] * (len(data) - len(tbl))
        # import pprint
        # pp = pprint.PrettyPrinter(indent=4)
        # print "Formats (%d, %d): " % (fmtwidth, len(tbl)); pp.pprint(tbl)
        # print "Data    (%d, %d): " % (len(data), len(data[0])); pp.pprint(data)
        # Compute table header
        if title:
            tline = "\n<table "
        else:
            tline = "\n<informaltable "
        tline += "pgwide='%d'" % expand
	# The box, doublebox, frame, and doubleframe options
	# turn this on.  We can't actually do a doublebox,
	# so we map it into a single-thickness box instead.
        #
	# Unfortunately frame gives the wrong effect when using the
	# Norm Walsh's DSSSL and XSL modular stylesheets.  They set
	# BORDER=1 in the generated HTML if frame is anything other
	# than `none', which forces framing on all interior cells.
	# This is wrong -- according to the DocBook reference, it
        # looks like the frame attribute is only supposed to control
        # *exterior* framing.
        if allbox:
            tline += " frame='all'"
        elif box:
            tline += " frame='border'"
        else:
            tline += " frame='none'"
        tline += ">"
        self.emit(tline)
        if title:
            self.emit("  <title>%s</title>" % title)
        tline = "  <tgroup cols='%d' align='%s'" % (fmtwidth, alignment)
        if allbox:
            tline += " colsep='1' rowsep='1'"
        self.emit(tline + ">")
        for i in range(fmtwidth):
            self.emit("    <colspec colname='c%d'/>" % (i+1,))
        if lastheaderline == -1:
            self.emit("    <tbody>")
        else:
            self.emit("    <thead>")
        # OK, finally ready to emit the table
        for i in range(len(data)):
            if isComment(data[i][0]):
                self.emit(makeComment("\t".join(data[i])))
                continue
            if rowsep[i]:
                self.emit("      <row rowsep='1'>")
            else:
                self.emit("      <row>")
            for j in range(len(data[i])):
                if "^" in tbl[i][j] or "s" in tbl[i][j]:
                    continue
                colspec = 1
                for k in range(j+1, fmtwidth):
                    if "s" not in tbl[i][k]:
                        break
                    else:
                        colspec += 1
                rowspan = 1
                if i < len(data) - 1 and '^' in tbl[i+1][j]:
                    for k in range(i+1, len(data)):
                        if "^" in tbl[k][j]:
                            rowspan += 1
                line = "        <entry"
                if   "c" in tbl[i][j]: line += " align='center'"
                elif "n" in tbl[i][j]: line += " align='right'"
                elif "r" in tbl[i][j]: line += " align='right'"
                elif "l" in tbl[i][j]: line += " align='left'"
                if (j < fmtwidth) and "|" in tbl[i][j]:
                    line += " colsep='1'"
                if colspec > 1:
                    line += " namest='c%d' nameend='c%d'" % (j+1, j+colspec)
                if rowspan > 1:
                    line += " morerows='%d'" % (rowspan-1)
                    if "t" in tbl[i][j]:
                        line += " valign='top'"
                    elif "d" in tbl[i][j]:
                        line += " valign='bottom'"
                    else:
                        line += " valign='middle'"
                line += ">"
                if data[i][j] != r'^':
                    if 'b' in tbl[i][j]:
                        line += r"\fB"
                    content = str(data[i][j])
                    if '\n' in content:
                        interpreted = []
                        self.interpretBlock(content.split("\n"), interpreted)
                        content = "\n".join(interpreted)
                    line += content
                    if troffHighlight.search(line) is not None:
                        line += r"\fR"
                self.emit(self.troff.expandStrings(line) + "</entry>")
            comment = comments.pop(0)
            if comment is None:
                trailer = ""
            else:
                trailer = " " + makeComment(comment)
            self.emit("      </row>" + trailer)
            if i == lastheaderline:
                if lastheaderline > -1:
                    self.emit("    </thead>")
                self.emit("    <tbody>")
        # Done
        self.emit("    </tbody>")
        self.emit("  </tgroup>")
        if title:
            self.emit("</table>\n")
        else:
            self.emit("</informaltable>\n")

    def EQN(self, startline):
        "Wrap and emit an EQN section."
        eqnlines = []
        nondelimlines = 0
        while self.lines:
            line = self.popline()
            if not line.startswith("delim") and not matchCommand(line, "EN"):
                nondelimlines += 1
            else:
                tokens = line.split()
                if len(tokens) == 2:
                    if tokens[1] == "off":
                        self.eqnsub = None
                        if not self.quiet:
                            self.emit(makeComment("eqn delimiters off."))
                    else:
                        es = re.escape(tokens[1][0])
                        ee = re.escape(tokens[1][1])
                        self.eqnsub = reCompile("([^" + es + "]*)" + es + "([^" + ee + "]+)"+ ee +"(.*)")
                        if not self.quiet:
                            self.emit(makeComment("eqn delimiters set to %s%s" % (tokens[1][0],tokens[1][1])))
                else:
                    self.eqnsub = None
            if matchCommand(line, "EN"):
                break
            eqnlines.append(line)
        if nondelimlines:
            if self.inPreamble:
                self.emit(makeComment(startline.strip()))
                for line in eqnlines:
                    self.emit(makeComment(line))
                self.emit(makeComment(startline[0] + "EN"))
            else:
                # If we could not pretranslate to MathML, and there
                # are non-delimiter lines, and we're not in preamble
                # it's appropriate to issue a worning here.
                if not self.eqnProcessed:
                    if not self.eqnSeen:
                        self.eqnSeen = True
                        self.warning("eqn(1) markup not translated.")
                    self.beginBlock("literallayout", remap="EQN")
                else:
                    self.beginBlock("equation", remap="EQN")
                for line in eqnlines:
                    self.emit(line)
                if not self.eqnProcessed:
                    self.endBlock("literallayout")
                else:
                    self.endBlock("equation")

    def PIC(self, line):
        "Wrap and emit a PIC section."
        # Because xmlto(1) can't render SVG tables to PIC,
        # it's appropriate to issue a warning here.
        picDiagram = ".PS\n"
        while True:
            line = self.popline()
            if not line:
                self.error("missing .PE")
            picDiagram += line + "\n"
            if line[1:].startswith("PE"):
                break
        fp = tempfile.NamedTemporaryFile(prefix="doclifter.py")
        # This is high-byte-preserving
        try:
            fp.write(picDiagram.encode('latin-1'))
        except UnicodeDecodeError:
            fp.write(picDiagram)		# This means we're in Python2
        fp.flush()
        (status, svg) = getstatusoutput("pic2plot -T svg <" + fp.name)
        fp.close()
        if status == 0 and "<svg" in svg:
            self.emit("<mediaobject remap='PIC'><imageobject>")
            self.emit(svg)
            self.emit("</imageobject></mediaobject>")
        else:
            self.warning("pic(1) markup not translated.")
            self.emit("<literallayout remap='PIC'>")
            self.emit(picDiagram)
            self.emit("</literallayout>")

    def ignore(self, cmd):
        "Declare that we want to ignore a command."
        self.ignoreSet.add(cmd)

    def unignore(self, cmd):
        "Declare that we want to stop ignoring a command."
        if cmd in self.ignoreSet:
            self.ignoreSet.remove(cmd)

    def ignorable(self, command, nocomplaints=0):
        "Can this command be safely ignored?"
        if not command:
            return False
        command = command.split()[0]	# only look at first token
        if command[0] in (TroffInterpreter.ctrl,TroffInterpreter.ctrlNobreak):
            command = command[1:]
        return command in self.ignoreSet or (nocomplaints and command in self.complainSet)

    def execute(self, line, command, tokens):
        "Try to interpret this command using each interpreter in the stack."
        if command in self.ignoreSet:
            self.passthrough(tokens)
            return True
        if command in self.complainSet:
            self.complaints[command] = True
            if generalVerbosity in self.verbose:
                self.notify(command + " seen")
            self.passthrough(tokens, complain=True)
            return True
        listbreaker = (command in self.listbreakSet or command == 'end')
        if listbreaker:
            # So .TP+.SH doesn't hose us, basically...
            self.trapPrefix = self.trapSuffix = ""
        if interpreterVerbosity in self.verbose:
            self.notify("after ignore check, interpreter sees: " + repr(tokens))
        # Maybe this command closes a list?
        if self.stashIndents and listbreaker:
            if ioVerbosity in self.verbose:
                self.notify("list closer %s: %s"%(command,self.stashIndents))
            enclosing = self.stashIndents[-1].command
            if enclosing not in self.scopedSet and command in self.listbreakSet and enclosing != command:
                while len(self.stashIndents):
                    self.poplist(self.stashIndents[-1].command)
        # Here is where string expansion in command arguments gets done:
        stripped = []
        for arg in stripquotes(tokens):
            if arg in self.troff.strings:
                stripped += self.troff.strings[arg].split()
            else:
                # Single non-string args map to single args
                stripped.append(arg)
        # This has to be a separate loop from the listbreak check
        for interpreter in self.interpreters:
                # Macros string-strip their arguments, troff requests don't.
            if interpreter == self.troff:
                args = tokens
            else:
                args = stripped
            if interpreter.interpret(line, args, self):
                return True
        return False

    def inSynopsis(self):
        return self.sectname and synopsisLabel.match(self.sectname)

    def interpretBlock(self, lines, divert=None):
        # Line-by-line translation
        self.pushdown.append(self.lines)
        self.lines = lines
        self.lineno -= len(lines)
        if divert is not None:
            self.diversion = divert
        line = None	# In case we throw an error in popline()
        try:
            while self.lines:
                line = self.popline()
                if interpreterVerbosity in self.verbose:
                    self.notify("interpreter sees: %s" % line)
                if line is None:
                    break
                # Usually we want to treat blank lines in body
                # sections as paragraph breaks that don't change the
                # current indent. Man treats them that way all the
                # time, but we can't because we have structured
                # sections like Synopsis to cope with.  Also, they
                # have a different significance inside lists -- a
                # blank line is not expected to end a list item in
                # .TP, but .PP is. We'll make up our own command and
                # pass it through for the interpreters to munch on.
                if line == '':
                    if self.bodySection() and not self.troff.nf:
                        self.pushline(TroffInterpreter.ctrl + "blank")
                    # Treat blank lines in synopses as break commands;
                    # see cpio.1 for an example of why this is necessary.
                    elif self.inSynopsis():
                        self.pushline(TroffInterpreter.ctrl + "br")
                    else:
                        self.emit('')
                    continue
                # Handle eqn delimiters
                if self.eqnsub:
                    doit = True
                    while doit:
                        transformed = self.eqnsub.sub(r"\1<?start-eqn?>\2<?end-eqn?>\3", line)
                        doit = (line != transformed)
                        line = transformed
                # Could be a comment.  Handle various ugly undocumented things.
                if isComment(line):
                    if line[3:]:
                        line = makeComment(line)
                    else:
                        line = ""
                    self.emit(line)
                    continue
                # Ugh...this is a nasty kluge intended to deal with people
                # who forget that the closing bracket of a conditional is
                # a command.  It's probably going to bite us someday.
                if line == r"\}":
                    self.pushline(TroffInterpreter.ctrl + r"\}")
                    if macroVerbosity in self.verbose:
                        self.warning(r"adventitious \} should probably be .\}")
                    continue
                # If no command, emit, and go on.
                if not isCommand(line):
                    # Note: This should be the only place where plain text
                    # is emitted.  When in doubt, use pushline() rather
                    # emit -- that will send the generated text back through
                    # here.
                    if self.needPara and line and not line[:4] == "<!--":
                        line = "<para>" + line
                        self.needPara = False
                    self.emit(line)
                    continue
                # We've got a dot command.  Try to interpret it as a request.
                tokens = lineparse(line)
                # stderr.write("Command tokens:" + repr(tokens) + "\n")
                command = tokens[0][1:]
                # All macro sets accept TBL
                if command == "TS":
                    self.paragraph()
                    self.TBL()
                    self.paragraph()
                # All macro sets accept EQN
                elif command == "EQ":
                    self.paragraph()
                    self.EQN(line)
                    self.paragraph()
                # All macro sets accept PIC
                elif command == "PS":
                    self.paragraph()
                    self.PIC(line)
                    self.paragraph()
                # Our pseudo-troff end command.
                elif command == "end":
                    self.execute(line, "end", tokens)
                elif not self.execute(line, command, tokens):
                    # We were not able to find an interpretation
                    # stderr.write("Raw line:" + line + "\n")
                    # stderr.write("Tokens:" + repr(tokens) + "\n")
                    self.emit(makeComment(line))
                    self.error("uninterpreted '%s' command" % command)
        except LiftException as e:
            self.error('"%s on %s' % (str(e), repr(line)))
        except (SystemExit, KeyboardInterrupt):
            self.error('%s:%d: internal error.' % (spoofname or self.file,self.lineno))
        except:
            # Pass the exception upwards for debugging purposes
            if not self.quiet:
                self.error("exception %s on: %s" % (sys.excInfo()[0], line))
            raise
        self.lines = self.pushdown.pop()
        if divert is not None:
            self.diversion = self.output

    def find(self, st, backwards=False):
        "Does the string occur in text we haven't seen yet?"
        if backwards:
            lines = self.output + self.lines
        else:
            lines = self.lines
        for line in lines:
            if type(line) == type(""):
                if type(st) == type(""):
                    if st in line:
                        return True
                else:
                    if st.search(line):
                        return True
        return False

    def expandEntities(self, line):
        "Expand character entities."
        # Specials associated with troff and various macro sets
        for interpreter in self.interpreters:
            for prefix in interpreter.translations:
                if prefix in line:
                    for (special, trans) in interpreter.translations[prefix]:
                        line = line.replace(special, trans)
        # groff-style ASCII and Unicode escapes. Have to use a little
        # state machine here, trying to do this with regexps gives
        # the regexp compiler fits.
        oldstart = 0
        while oldstart < len(line):
            start = oldstart + line[oldstart:].find('\\')
            if start == -1:
                break
            elif line[start:].startswith("\\[char"):
                m = re.match(r"[0-9]+(?=\x5D)", line[start+6:])
                if m:
                    line = line[:start] + "&#" + m.group(0) + ";" + line[start + 6 + len(m.group(0)) + 1:]
                oldstart = start + 2
            elif line[start:].startswith("\\[u"):
                m = re.match(r"[0-9]+(?=\x5D)", line[start+3:])
                if m:
                    line = line[:start] + "&#" + m.group(0) + ";" + line[start + 3 + len(m.group(0)) + 1:]
                else:
                    m = re.match(r"[0-9A-F]+(?=\x5D)", line[start+3:])
                    if m:
                        line = line[:start] + "&#x" + m.group(0) + ";" + line[start + 3 + len(m.group(0)) + 1:]
                oldstart = start + 2
            else:
                oldstart += 1
        return line

    def hackTranslations(self, line):
        "Perform troff font-escape translations."
        if line[:4] != "<!--" and '\\' in line:
            # Translate font escapes.  We do this late in order to get
            # uniform handling of those that were generated either by
            # macros or by inline font escapes in the source text.
            while True:
                esc = troffHighlight.search(line)
                if not esc:
                    break
                else:
                    sl = esc.start()
                if line[sl+2:sl+4] == "[]":
                    line = line[:sl]+self.changeHighlight("P")+line[sl+4:]
                elif line[sl+2] == "[":
                    end = sl + 2 + line[sl+2:].find("]")
                    line = line[:sl]+self.changeHighlight(line[sl+3:end],line[sl+1])+line[end+1:]
                elif line[sl+2] == "(":
                    line = line[:sl]+self.changeHighlight(line[sl+3:sl+5],line[sl+1])+line[sl+5:]
                else:
                    line = line[:sl]+self.changeHighlight(line[sl+2:sl+3],line[sl+1])+line[sl+3:]
        return line

    def liftLink(self, line):
        "Checks highlighted content to see if it's an XML id which exists"
        # Currently, matches only <emphasis> highlights
        if not reCompile("<emphasis").match(line):
            return line
        for (linkHighlight, reContent) in self.liftLinks:
            lift = reCompile(r"<emphasis\s+remap='%s'>(%s)</emphasis>" % (linkHighlight, reContent))
            if lift.match(line):
                content = lift.sub(r"\1", line)
                trailer = ""
                if content.endswith("</para>"):
                    content = content[:-7]
                    trailer = "</para>"
                sid = self.idFromTitle(content)
                if self.idExists(sid):
                    return '<link linkend="%s">%s</link>%s' % (sid, content, trailer)
        return line

    def isActive(self, macroSet):
        "Is a given macro set (specified by name) active?"
        return macroSet in [x.__class__.name for x in self.interpreters]

    def activate(self, macroSet):
        "Activate a given macro set."
        # Don't put duplicate instances in the interpreter list.
        if not self.isActive(macroSet.name):
            if hasattr(macroSet, "requires"):
                for ancestor in macroSet.requires:
                    self.activate(ancestor)
            newinstance = macroSet(self, self.verbose)
            self.interpreters = [newinstance] + self.interpreters
            if generalVerbosity in self.verbose:
                stderr.write("%s uses %s macros...\n" % (spoofname or self.file, macroSet.name))

    def closeTags(self, before, tag, tight):
        "Generate close tags for a block-level open tag."
        state = 0
        after = ""
        # This is an RE in case a tag instance has attributes.
        opentag = reCompile("<" + tag + r"\b[^>]*>")
        closetag = "</" + tag + ">"
        closetaglength = len(closetag)
        closer = "\\fR" + closetag
        inline = set((
            "emphasis","literal","quote","varname", "keycap",
             "indexterm","primary","secondary","tertiary",
             #"entry","row","thead","tbody","tgroup",
             #"informaltable", "tgroup", "colspec",
             "subscript","superscript",
             "function","type","parameter","envar","constant",
             "option","command","replaceable","errorcode",
             "firstname","surname","othername","lineage",
             "orgname","affiliation","ulink","link","email",
             "citerefentry","refentrytitle","manvolnum",
             "citetitle","filename","productname",
             "phrase","anchor","acronym",
             "mediaobject","imageobject","imagedata",
             "arg", "group", "cmdsynopsis", "command",
             "funcsynopsis", "funcsynopsisinfo", "funcprototype", "funcdef",
             "paramdef", "parameter", "function", "void", "vaargs",
             "synopsis", "symbol", "inlineequation"))
        while True:
            if state == 0:	# Looking for <tag>
                # Find the next tag to be closed
                nexttag = opentag.search(before)
                if nexttag is None:
                    after += before
                    break		# We're done
                else:
                    after += before[:nexttag.end()]
                    before = before[nexttag.end():]
                    state = 1
                    continue
            elif state == 1:	# Found <tag>, looking for next tag
                nexttag = before.find("<")
                if nexttag == -1:
                    self.error("tag closer is confused by `%s`!" % before)
                    break
                after += before[:nexttag]
                before = before[nexttag:]
                # </tag> just closes the scope
                if before.startswith(closetag):
                    after += before[:closetaglength]
                    before = before[closetaglength:]
                    state = 0
                    continue
                # Any processing instruction means
                # keep looking for close of scope.
                elif before[1] in "?":
                    after += before[:2]
                    before = before[2:]
                    state = 1
                    continue
                # Comments require more handling, as they may contain < and >
                elif before.startswith("<!--"):
                    endc = before.find("-->") + 3
                    after += before[:endc]
                    before = before[endc:]
                    continue
                # Otherwise we know it's a real tag.  Grab it.
                else:
                    btag = before[1:before.find(">")]
                    # Throw away attributes
                    tagtype = btag.split()[0]
                    # Is it a close tag?
                    close = tagtype[0] == "/"
                    # is it contentless?
                    if tagtype[-1] == "/":
                        trim = -1
                    else:
                        trim = len(tagtype)
                    # If it's not inline, close scope and keep going
                    # We assume that anything with a namespace qualifier
                    # (thus the MaGiC%CoOkIe) cannot close scope on a
                    # DocBook tag.
                    if btag[close:trim] not in inline and "MaGiC%CoOkIe" not in btag:
                        # Back up over any whitespace in the end
                        if not tight:
                            after += closer
                        else:
                            # Skip back over whitespace and comments
                            alen = len(after)
                            leader = after
                            while True:
                                if leader[-1] in " \n\t":
                                    leader = leader.rstrip()
                                elif leader.endswith("-->"):
                                    leader = leader[:leader.rfind("<!--")]
                                else:
                                    break
                            if leader != after:
                                after = leader+closer+after[len(leader)-alen:]
                            else:
                                after += closer
                        state = 0
                        continue
                    # If it's inline, skip tag and keep looking for close
                    else:
                        after += before[:len(btag)]
                        before = before[len(btag):]
                        state = 1
                        continue
        return after

    @staticmethod
    def lynxprep(text, source):
        "Turn a text lynx dump into a manual page."
        lines = text.split("\n")
        # Drop everything before the NAME section header, this gets rid of
        # useless preamble lines in ppm pages.
        date = ""
        while not lines[0].title().startswith("Name"):
            source.lineno += 1
            if lines[0].find("Updated: ") > -1:
                date = lines[0][lines[0].find("Updated: ")+10:].strip()
            lines.pop(0)
            if not lines:
                raise LiftException(source, "plain text where manual page expected", 1)
        inoptions = False
        for i in range(len(lines)):
            if len(lines[i]) == 0:
                continue
            elif lines[i][0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                inoptions = lines[i].startswith("OPTIONS")
                lines[i] = TroffInterpreter.ctrl + "SH " + lines[i].strip()
            else:
                lines[i] = lines[i].strip()
                if lines[i].startswith("____________"):
                    lines = lines[:i]
                    break
                elif inoptions and lines[i][0] == '-':
                    lines[i] = TroffInterpreter.ctrl + "TP\n" + lines[i]
                elif lines[i][0] == TroffInterpreter.ctrl:
                    lines[i] = "\\&" + lines[i]
        name = section = ""
        if "." in os.path.basename(source.file):
            (name, section) = os.path.basename(source.file).split(".")
            name = os.path.basename(name)
        source.lines = 0
        th = '.TH "%s" "%s" "%s" "" ""\n' % (name,  section, date)
        return th + "\n".join(lines) + "\n"

    def __call__(self, name, cfile, text, multiarg):
        "Translate a string containing troff source to DocBook markup."
        self.__reinit__()
        self.name = name
        self.file = cfile
        self.multiarg = multiarg
        self.diversion = self.output
        self.starttime = self.basetime = time.time()
        # Set up the base troff interpreter
        self.troff = TroffInterpreter(self, self.verbose)
        self.interpreters = [self.troff]
        self.localhints = SemanticHintsRegistry()
        # Empty files pass through trivially.
        # (This is not a terribly uncommon defect...)
        if len(text) == 0:
            raise LiftException(self, "file is empty", 1)
        # Parse semantic hints from the text, if present.
        # Yes, they should go to the global registry.
        globalhints.read(text)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: hint processing = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Now determine which interpreter to use.  This code has the
        # elaborations it does because mixing macro sets (especially
        # using mdoc macros in a man page and vice-versa) is not an
        # uncommon error.
        triggers = []
        # Find uses of each trigger, sort by position of first occurrence
        for (pattern, consumer) in list(interpreterDispatch.items()):
            # If the file has an extension, we can exclude some possibilities
            if "." in cfile:
                required = requiredExtensions.get(consumer)
                if required and not cfile.endswith(required):
                    continue
            # Otherwise look for first uses of trigger patterns
            if len(pattern) <= 5:
                if text.find("\n.de " + pattern) > -1:
                    where= -1			# Defined as a macro
                if text[1:1+len(pattern)] == pattern:
                    where = 0			# Occurs as the first request
                else:
                    where = text.find("\n." + pattern)
            else:
                where = text.find(pattern)
            if where > -1:
                triggers.append((where, consumer))
        try:
            triggers.sort(lambda x, y: x[0] - y[0])	# Python 2
        except TypeError:
            triggers.sort(key=lambda x: x[0])		# Python 3
        triggered = [x[1] for x in triggers]
        # Now walk through the list from the front, doing exclusions
        if triggered:
            exclusionLock = False
            for consumer in triggered:
                # Only allow one exclusive macro set.  This is how we
                # avoid, e.g., the presence of mdoc macros after a man
                # page header causing confusion.
                if consumer.exclusive:
                    if exclusionLock:
                        continue
                    else:
                        exclusionLock = True
                        self.toptag = consumer.toptag
                # Troff commands get evaluated first
                self.activate(consumer)
        # Could still be a lynx dump like the ppm man pages.
        elif text.find("Table Of Contents") > -1 or text.find("   Updated: ") > -1:
            if self.verbose:
                stderr.write("Looks like a lynx dump...\n")
            text = DocLifter.lynxprep(text, self.troff)
            self.activate(ManInterpreter)
        # Default to a lynx dump even if unsure.
        else:
            if self.verbose:
                stderr.write("Unknown format so defaulting to a lynx dump...\n")
                text = DocLifter.lynxprep(text, self.troff)
                self.activate(ManInterpreter)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: macro identification = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # If no exclusive macro set asserted a top tag, pick the most recent.
        if not self.toptag:
            self.toptag = self.interpreters[-1].toptag
        # Nuke carriage returns (as in ogg123.1).
        text = re.sub(r"(?<!\\)\r", "", text)
        # Very grubby hack to get rid of some otherwise unfixable cases.
        for (ugly, entity) in DocLifter.pretranslations:
            text = text.replace(ugly, entity)
        # Allow the interpreters to preprocess the output.
        for interpreter in self.interpreters:
            self.listbreakSet |= interpreter.listbreakSet
            self.scopedSet |= interpreter.scopedSet
            self.ignoreSet |= interpreter.ignoreSet
            self.complainSet |= interpreter.complainSet
            text = interpreter.preprocess(text)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: preprocessing = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Split it into lines
        toplevel = text.split("\n")
        # Check for pure inclusions
        def isInclusion(x):
            return x[:4] == TroffInterpreter.ctrl + "so "
        nonempty = [x for x in toplevel if x != "" and not isComment(x)]
        if len(nonempty) == 1 and isInclusion(nonempty[0]):
            raise LiftException(self, "see " + nonempty[0].strip()[4:], 2)
        elif len(nonempty) > 1 and len(list(filter(isInclusion, nonempty))) == len(nonempty):
            raise LiftException(self, "consists entirely of inclusions", 2)
        # If it's not a pure inclusion, warn if we don't have a macro set.
        if len(self.interpreters) == 1:
            raise LiftException(self, "no macro set recognized", 1)
        # Strip off trailing blank lines, they interact badly with the
        # paragraphing logic.
        while toplevel and toplevel[-1] == "":
            toplevel.pop()
        # This actually happens with some generated Perl pages
        # that stop after .TH, without even a name section.
        if len(toplevel) <= 1:
            self.filewarn("%s has no content" % (spoofname or self.file))
            (stem, _) = os.path.splitext(self.file)
            toplevel.append(".SH NAME")
            toplevel.append("%s \\- bogus empty manual page" % os.path.basename(stem))
            toplevel.append(".SH DESCRIPTION")
            toplevel.append(rudeness)
        # Is there any text at all in this file?
        textcount = 0
        for line in toplevel:
            if not isCommand(line) and not isComment(line):
                textcount += 1
        if textcount == 0:
            raise LiftException(self, "warning: page has no text")
        # Plant a sentinel at the end to force paragraph and list closes
        i = -1
        if not toplevel[i] and isComment(toplevel[i]):
            i -= 1
        toplevel.insert(len(toplevel)-i, TroffInterpreter.ctrl + "end")
        # Emit the top-level tag, with an id that will direct the
        # DocBook toolchain to do the right thing.
        if self.toptag:
            if self.file != "stdin":
                if self.docbook5:
                    self.emit("<%s xmlns='http://docbook.org/ns/docbook' version='5.0' xml:lang='en' xml:id='%s'>" % (self.toptag, self.makeIdFromTitle(os.path.basename(cfile))))
                else:
                    self.emit("<%s id='%s'>" % (self.toptag, self.makeIdFromTitle(os.path.basename(cfile))))
            else:
                self.emit("<%s>" % self.toptag)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: preparation = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Now interpret all the commands in the block
        self.lineno = len(toplevel) + self.lineno
        self.interpretBlock(toplevel)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: block interpretation = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Wrap it up
        self.popSection(1)
        for interpreter in self.interpreters:
            if hasattr(interpreter, "wrapup"):
                interpreter.wrapup()
        if self.toptag:
            self.emit("</%s>\n" % self.toptag)
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: wrapup = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Close paragraphs properly.  Note: we're going to run
        # all the lines together for this and split them up
        # again afterwards.  Because bodyStart is a line index,
        # we have to not insert or delete lines here.
        before = "\n".join(self.output)
        after = self.closeTags(before, "para", tight=True)
        after = self.closeTags(after, "literallayout", tight=False)
        self.output = after.split("\n")
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: tag closing = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Maybe it's all comments and blanks (result of a bare hints file).
        # In that case return None to suppress output
        if not self.interpreters and not [x for x in self.output if x[:4]=="<!--" or blankline.match(x)]:
            return None
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: emptiness check = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Time for post-translations
        self.highlight = "R"
        if highlightVerbosity in self.verbose:
            self.filewarn("Highlight resolution begins")
        for j in range(self.bodyStart, len(self.output)):
            if highlightVerbosity in self.verbose:
                self.notify("Before: " + self.output[j])
            self.output[j] = self.hackTranslations(self.output[j])
            if highlightVerbosity in self.verbose:
                self.notify("After: " + self.output[j])
        if highlightVerbosity in self.verbose:
            self.filewarn("Highlight resolution ends")
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: translation hacks = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        for j in range(self.bodyStart, len(self.output)):
            self.output[j] = self.liftLink(self.output[j])
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: link lifting = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # OK, now do pattern-based markup lifting on the DocBook markup
        head = "\n".join(self.output[:self.bodyStart]) + "\n"
        body = "\n".join(self.output[self.bodyStart:]) + "\n"
        self.output = []
        for (pattern, substitute) in DocLifter.postTranslationPatterns:
            body = pattern.sub(substitute, body)
        for (r, s) in DocLifter.liftHighlights:
            ender = s.split()[0]	# discard attributes
            body = r.sub(r"<%s>\1</%s>" % (s, ender), body)
        for (pattern, substitute) in DocLifter.postLiftPatterns:
            body = pattern.sub(substitute, body)
        # Semantic lifting based on the hints dictionary
        text = head + self.localhints.apply(globalhints.apply(body))
        if timingVerbosity in self.verbose:
            now = time.time()
            stderr.write("timing: semantic lifting = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        # Allow the interpreters to postprocess the output
        for interpreter in self.interpreters:
            text = interpreter.postprocess(text)
        # Nuke the fake entity we created to represent zero-width space.
        text = text.replace("&zerosp;", "")
        # Remove filler lines.
        text = text.replace("<!-- DELETE ME! -->\n", "")
        # Check for bad escapes in the generated output only.
        # This avoids error messages based on (for example) untraversed
        # branches in .if and .ie constructs.
        badescapes = []
        commentless = reCompile("<!-- .* -->").sub("", text)
        if "<!-- .ig" in commentless:
            lines = commentless.split("\n")
            state = 0
            keep = []
            for line in lines:
                if line.startswith("<!-- .ig"):
                    state = 1
                if line.startswith(".. -->"):
                    state = 0
                if state == 0:
                    keep.append(line)
            commentless = "\n".join(keep)
        for k in range(0, len(commentless)-1):
            if commentless[k] == '\\' and commentless[k+1] != '\\':
                count = 1
                while k - count >= 0:
                    if commentless[k - count] == '\\':
                        count += 1
                    else:
                        break
                if not count % 2:
                    break
                # OK, there is an odd number of backslashes here
                if commentless[k+1:k+3] == '*[':
                    name = commentless[k+1:k+2+commentless[k+2:].find("]")+1]
                    badescapes.append(name)
                elif commentless[k+1] == '[':
                    glyph = commentless[k+1:k+1+commentless[k+1:].find("]")+1]
                    stderr.write("warning: unknown glyph %s\n" % glyph)
                elif commentless[k+1:k+3] == '*(':
                    badescapes.append(commentless[k+1:k+5])
                elif commentless[k+1] == '*':
                    badescapes.append(commentless[k+1:k+3])
                elif commentless[k+1] == '(':
                    badescapes.append(commentless[k+1:k+4])
                elif not commentless[k+1] in badescapes:
                    badescapes.append(commentless[k+1])
        badescapes = list(set(badescapes))
        if badescapes:
            self.filewarn("uninterpreted escape sequences \\" + ", \\".join(badescapes) + "\n")
        if self.complaints:
            self.filewarn(", ".join(list(self.complaints.keys())) + " seen\n")
        # Undo magic-cookification, no more tables to worry about.
        # This is where we force the MathML markup into a distinct namespace.
        text = text.replace("MaGiC%CoOkIe", "mml:m")
        # Optimize comments
        text = text.replace(" -->\n<!-- ", "\n")
        # We're done
        if timingVerbosity in self.verbose:
            now = time.time()
            self.filewarn("timing: post-processing = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
        preamble = ""
        preamble = "<?xml version=\"1.0\" encoding=\"%s\"?>\n" % self.outEncoding
        # Are there any entity references in this document?
        entities = ""
        for (entity, uni) in DocLifter.pseudoEntities + tuple(self.localentities):
            if text.find("&" + entity + ";") > -1:
                entities += "<!ENTITY %s '%s'>\n" % (entity, uni)
        # FIXME: if docbook5 is on, inclusions won't work.
        if self.docbook5:
            if entities:
                preamble += allent
        else:
            preamble += "<!DOCTYPE %s PUBLIC \"-//OASIS//DTD DocBook " % self.toptag
            preamble += "XML V4.4//EN\"\n                   \"http://www.oasis-open.org/docbook/xml/4.4/docbookx.dtd\""
            if entities or self.inclusions or "<mml:m" in text:
                preamble += " [\n"
                if "<mml:m" in text:
                    preamble += mathmlEntities
                for (entity, ifile) in self.inclusions:
                    preamble += "<!ENTITY %s SYSTEM '%s'>\n" % (entity, ifile)
                preamble += entities
                preamble += "]"
            preamble += ">\n"
        macros = [x.__class__.name for x in self.interpreters]
        #macros.reverse()
        preamble += "<!-- lifted from %s by doclifter.py -->\n" % "+".join(macros)
        # If there were accumulated errors during processing, time to bail.
        if self.errorcount:
            raise LiftException(self, "there were %d errors during translation" % self.errorcount)
        if timingVerbosity in self.verbose:
            now = time.time()
            self.filewarn("timing: document generation = %2.2f\n" % (now-self.basetime,))
            self.basetime = now
            self.filewarn("timing: total = %2.2f\n" % (now-self.starttime,))
        # Single-character "equations" can be hacked into emphasis tags.
        # (The X documentation has a lot of uses of this construct.)
        # This can substantially reduce the amount of manual hackery
        # needed to hand-translate the eqn.
        if self.eqnsub:
            text = re.sub(r"<\?start-eqn\?>(.)<\?end-eqn\?>", r"<emphasis role='eqn'>\1</emphasis>", text)
        # Also nuke hair-thin space, at this late stage it shouldn't make
        # any difference.  This avoids an apparent bug in the DocBook
        # stylesheets; &hairsp; is documented but not actually defined.
        text = text.replace("&hairsp;", "")
        # All done with markup translation...
        text = preamble + text
        # In order to avoid Python 2 vs. Python 3 incompatibilities,
        # we processed the text as a string, but in Python 3 this
        # is actually a Unicode object that has been faked into preserving
        # raw 0x80-0xff in the input as ISO-8859-1 characters.
        #
        # This worked because (a) ntroff markup is almost always in ASCII
        # or one of the ISO-8859 character sets, and (b) in the rare cases
        # where it isn't, all the parts we have to interpret are in ASCII
        # because that's all the stock macros are composed from. Any non-ASCII
        # bytes should have been preserved through markup translation.
        #
        # Now we need to do a fancy dance: (1) encode the string back to a byte
        # buffer, (2) adaptively interpret that back into Unicode, and then
        # (3) re-encode the Unicode to a byte stream, because our framework
        # code is expecting that.
        try:
            text = text.encode(binaryEncoding)
        except UnicodeDecodeError:
            pass		# Failure means we're in Oython 2
        for encoding in self.inEncodings:
            try:
                text = text.decode(encoding)
                break
            except UnicodeDecodeError:
                pass
        else:
            self.troff.lineno = 0
            raise LiftException(self, "Unicode decoding error")
        return text.encode(self.outEncoding)

class TroffInterpreter:
    "Interpret troff requests (does macroexpansion)."
    name = "troff"
    exclusive = False
    toptag = ""
    immutableSet = set([])
    ignoreSet = set([
        # Ignore .. outside macro context, some people use it as a no-op.
        ".",
        # Just ignore most font/character-size/page controls
        "ps","ss","cs","bd","fp","pl","pn","po","ne",
        # Ignore most text filling and vertical spacing controls.
        "ad","na","vs","ls","sv","os","ns","rs",
        # Line length, tabs,leaders, fields, ligature mode, hyphenation.
        "ll","tc","lc","fc","lg","nh","hy","hc","hw",
        # Ignore commands for page titles, exit, miscellanea
        "tl","pc","lt","ex","mc","fl",
        # Also ignore diversions and register operations.
        "di","da","wh","ch","dt","af",
        # This is some nonstandard extension (see access.1) safe to ignore
        "rb",
        # Ignore groff debugging stuff
        "lf",
        # Weird groff extensions.
        "hcode", "hym", "hys", "hla", "shc", "cp","fam",
        # Better to pass through glyphs defined by char than try to expand
        # them; we'll translate most into entities and flag the rest as
        # errors.
        "char",
        # Policy decision; don't do font remapping, on the theory that
        # passing through the font names the user specified into remap
        # attributes probably carries forward more information.
        "ftr",
        # We can't do anything with the groff defcolor or it requests, alas.
        "defcolor", "it",
        ])
    complainSet = set([
        # Complain about stuff that produces gross motions.
        "ne","mk","rt","ce",
        # We could do much of section 10, but these are a sign of trouble.
        "ec","eo","uf",
        # We can't handle environments, insertions, or next file.
        "ev","rd","nx","pi",
	])
    parabreakSet = set(["bp","ti"])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    entityTranslations = (
        # The entire list of characters described in the groff/troff reference
        # is included here. Where there is no ISO equivalent, the second
        # member will be an alias for a Unicode literal.  This transformation
        # is done late, at output-emission time.
        #
        # Troff escapes (not handled here: \. \! \" \$ \* \[a-zA-Z]. \{, \})
        ("\\",     "&bsol;"),	# Double slash to single slash
        (r"&amp;", "&zerosp;"),
        (r"&lt;",  "&lt;"),	# Prevent spurious messages about \&
        (r"&gt;",  "&gt;"),	# Prevent spurious messages about \&
        (r"&apos;", "&apos;"),	# Prevent spurious messages about \&
        (r"&semi;","&semi;"),	# Prevent spurious messages about \&
        (r")",     "&zerosp;"),	# groff extension
        (r"~",     "&nbsp;"),	# This isn't quite right, alas.
        (r" ",     "&nbsp;"),
        (r"0",     "&numsp;"),	# ISOpub
        (r"^",     "&hairsp;"),	# ISOpub
        (r"`",     "&grave;"),	# ISOdia
        (r"e",     "&bsol;"),	# ISOnum
        (r"\\",    "&bsol;"),	# ISOnum
        (r"|",     "&thinsp;"),	# ISOpub
        (r":", ""),		# No hyphenation in XML
        (r"/", ""),		# No kerning in XML
        (r",", ""),		# No kerning in XML
        (r"-", "-"),
        (r"+", "+"),
        (r".", "."),
        (r"#", "#"),
        (r"=", "="),
        (r"_", "_"),
        (r"t", "\t"),
        # groff/troff special characters.  Listed in the order given on the
        # groff_char(7) manual page. Characters from old troff are marked with
        # a + in the comment.
        (r"-D",	"&ETH;"),	# ISOlat: Icelandic uppercase eth
        (r"Sd",	"&eth;"),	# ISOlat1: Icelandic lowercase eth
        (r"TP",	"&THORN;"),	# ISOlat1: Icelandic uppercase thorn
        (r"Tp",	"&thorn;"),	# ISOlat1: Icelandic lowercase thorn
        (r"ss",	"&szlig;"),	# ISOlat1
        ## Ligatures
        (r"ff", "&fflig;"),	# ISOpub +
        (r"fi", "&filig;"),	# ISOpub +
        (r"fl", "&fllig;"),	# ISOpub +
        (r"Fi", "&ffilig;"),	# ISOpub +
        (r"Fl", "&ffllig;"),	# ISOpub +
        (r"AE",	"&AElig;"),	# ISOlat1
        (r"ae",	"&aelig;"),	# ISOlat1
        (r"OE",	"&OElig;"),	# ISOlat2
        (r"oe",	"&oelig;"),	# ISOlat2
        (r"IJ",	"&ijlig;"), 	# ISOlat2: Dutch IJ ligature
        (r"ij",	"&IJlig;"), 	# ISOlat2: Dutch ij ligature
        (r".i", "&inodot;"),	# ISOlat2,ISOamso
        (r".j", "&jnodot;"),	# ISOamso
        ## Accented characters
        (r"'A",	"&Aacute;"),	# ISOlat1
        (r"'C",	"&Cacute;"),	# ISOlat2
        (r"'E",	"&Eacute;"),	# ISOlat1
        (r"'I",	"&Iacute;"),	# ISOlat1
        (r"'O",	"&Oacute;"),	# ISOlat1
        (r"'U",	"&Uacute;"),	# ISOlat1
        (r"'Y",	"&Yacute;"),	# ISOlat1
        (r"'a",	"&aacute;"),	# ISOlat1
        (r"'c",	"&cacute;"),	# ISOlat2
        (r"'e",	"&eacute;"),	# ISOlat1
        (r"'i",	"&iacute;"),	# ISOlat1
        (r"'o",	"&oacute;"),	# ISOlat1
        (r"'u",	"&uacute;"),	# ISOlat1
        (r"'y",	"&yacute;"),	# ISOlat1
        (r":A",	"&Auml;"),	# ISOlat1
        (r":E",	"&Euml;"),	# ISOlat1
        (r":I",	"&Iuml;"),	# ISOlat1
        (r":O",	"&Ouml;"),	# ISOlat1
        (r":U",	"&Uuml;"),	# ISOlat1
        (r":Y",	"&Yuml;"),	# ISOlat2
        (r":a",	"&auml;"),	# ISOlat1
        (r":e",	"&euml;"),	# ISOlat1
        (r":i",	"&iuml;"),	# ISOlat1
        (r":o",	"&ouml;"),	# ISOlat1
        (r":u",	"&uuml;"),	# ISOlat1
        (r":y",	"&yuml;"),	# ISOlat1
        (r"^A",	"&Acirc;"),	# ISOlat1
        (r"^E",	"&Ecirc;"),	# ISOlat1
        (r"^I",	"&Icirc;"),	# ISOlat1
        (r"^O",	"&Ocirc;"),	# ISOlat1
        (r"^U",	"&Ucirc;"),	# ISOlat1
        (r"^a",	"&acirc;"),	# ISOlat1
        (r"^e",	"&ecirc;"),	# ISOlat1
        (r"^i",	"&icirc;"),	# ISOlat1
        (r"^o",	"&ocirc;"),	# ISOlat1
        (r"^u",	"&ucirc;"),	# ISOlat1
        (r"`A",	"&Agrave;"),	# ISOlat1
        (r"`E",	"&Egrave;"),	# ISOlat1
        (r"`I",	"&Igrave;"),	# ISOlat1
        (r"`O",	"&Ograve;"),	# ISOlat1
        (r"`U",	"&Ugrave;"),	# ISOlat1
        (r"`a",	"&agrave;"),	# ISOlat1
        (r"`e",	"&egrave;"),	# ISOlat1
        (r"`i",	"&igrave;"),	# ISOlat1
        (r"`o",	"&ograve;"),	# ISOlat1
        (r"`u",	"&ugrave;"),	# ISOlat1
        (r"~A",	"&Atilde;"),	# ISOlat1
        (r"~N",	"&Ntilde;"),	# ISOlat1
        (r"~O",	"&Otilde;"),	# ISOlat1
        (r"~a",	"&atilde;"),	# ISOlat1
        (r"~n",	"&ntilde;"),	# ISOlat1
        (r"~o",	"&otilde;"),	# ISOlat1
        (r"vS",	"&Scaron;"),	# ISOlat2
        (r"vs",	"&scaron;"),	# ISOlat2
        (r"vZ",	"&Zcaron;"),	# ISOlat2
        (r"vz",	"&zcaron;"),	# ISOlat2
        (r",C",	"&Ccedil;"),	# ISOlat1
        (r",c",	"&ccedil;"),	# ISOlat1
        (r"/L",	"&Lstrok;"),	# ISOlat2: Polish L with a slash
        (r"/l",	"&lstrok;"),	# ISOlat2: Polish l with a slash
        (r"/O",	"&Oslash;"),	# ISOlat1
        (r"/o",	"&oslash;"),	# ISOlat1
        (r"oA",	"&Aring;"),	# ISOlat1
        (r"oa",	"&aring;"),	# ISOlat1
        # Accents
        (r'a"', "&dblac;"),	# ISOdia: double acute accent (Hungarian umlaut)
        (r"a-",	"&macr;"),	# ISOdia: macron or bar accent
        (r"a.",	"&dot;"),	# ISOdia: dot above
        (r"a^",	"&circ;"),	# ISOdia: circumflex accent
        (r"aa",	"&acute;"),	# ISOdia: acute accent +
        (r"ga",	"&grave;"),	# ISOdia: grave accent +
        (r"ab",	"&breve;"),	# ISOdia: breve accent
        (r"ac",	"&cedil;"),	# ISOdia: cedilla accent
        (r"ad",	"&uml;"),	# ISOdia: umlaut or dieresis
        (r"ah",	"&caron;"),	# ISOdia: caron (aka hacek accent)
        (r"ao",	"&ring;"),	# ISOdia: ring or circle accent
        (r"a~",	"&tilde;"),	# ISOdia: tilde accent
        (r"ho",	"&ogon;"),	# ISOdia: hook or ogonek accent
        (r"ha",	"^"),		# ASCII circumflex, hat, caret
        (r"ti",	"~"), 		# ASCII tilde, large tilde
        ## Quotes
        (r"Bq",	"&lsquor;"),	# ISOpub: low double comma quote
        (r"bq",	"&ldquor;"),	# ISOpub: low single comma quote
        (r"lq",	"&ldquo;"),	# ISOnum
        (r"rq",	"&rdquo;"),	# ISOpub
        (r"oq",	"&lsquo;"),	# ISOnum: single open quote
        (r"cq",	"&rsquo;"),	# ISOnum: single closing quote (ASCII 39)
        (r"aq",	"&apos;'"),	# apostrophe quote
        (r"dq",	"\""),		# double quote (ASCII 34)
        (r"Fo",	"&laquo;"),	# ISOnum
        (r"Fc",	"&raquo;"),	# ISOnum
        (r"fo",	"&fo;"),	# Internal pseudo-entity
        (r"fc",	"&fc;"),	# Internal pseudo-entity
        ## Punctuation
        (r"r!",	"&iexcl;"),	# ISOnum
        (r"r?",	"&iquest;"),	# ISOnum
        (r"em", "&mdash;"),	# ISOpub +
        (r"en",	"&ndash;"),	# ISOpub: en dash
        (r"hy", "&hyphen;"),	# ISOnum +
        ## Brackets
        (r"lB",	"&lsqb;"),	# ISOnum: left (square) bracket
        (r"rB",	"&rsqb;"),	# ISOnum: right (square) bracket
        (r"lC",	"&lcub;"),	# ISOnum: left (curly) brace
        (r"rC",	"&rcub;"),	# ISOnum: right (curly) brace
        (r"la",	"&lang;"),	# ISOtech: left angle bracket
        (r"ra",	"&rang;"),	# ISOtech: right angle bracket
        (r"bv", "&verbar;"),	# ISOnum +
        # Bracket-piles.  These are all
        # internal pseudo-entities that we map to Unicode literals
        # rather than ISO entities.
        (r"braceex", "&braceex;"),
        (r"bracketlefttp", "&bracketlefttp;"),
        (r"bracketleftbt", "&bracketleftbt;"),
        (r"bracketleftex", "&bracketleftex;"),
        (r"bracketrighttp", "&bracketrighttp;"),
        (r"bracketrightbt", "&bracketrightbt;"),
        (r"bracketrightex", "&bracketrightex;"),
        (r"lt", "&tlt;"),
        (r"bracelefttp", "&tlt;"),
        (r"lk", "&lk;"),
        (r"braceleftmid", "&lk;"),
        (r"lb", "&lb;"),
        (r"braceleftbt", "&lb;"),
        (r"braceleftex", "&braceleftex;"),
        (r"rt", "&rt;"),
        (r"bracerighttp", "&rt;"),
        (r"rk", "&rk;"),
        (r"bracerightmid", "&bracerightmid;"),
        (r"rb", "&rb;"),
        (r"bracerightbt", "&rb;"),
        (r"bracerightex", "&bracerightex;"),
        (r"parenlefttp", "&parenlefttp;"),
        (r"parenleftbt", "&parenleftbt;"),
        (r"parenleftex", "&parenleftex;"),
        (r"parenrighttp", "&parenrighttp;"),
        (r"parenrightbt", "&parenrightbt;"),
        (r"parenrightex", "&parenrightex;"),
        ## Arrows
        (r"&lt;-", "&larr;"),	# ISOnum (XMLified) +
        (r"-&gt;", "&rarr;"),	# ISOnum (XMLified) +
        (r"&lt;&gt;",	"&harr;"),	# ISOamsa (XMLified)
        (r"da",	"&darr;"),	# ISOnum +
        (r"ua",	"&uarr;"),	# ISOnum +
        (r"va",	"&varr;"),	# ISOamsa
        (r"lA",	"&lArr;"),	# ISOtech
        (r"rA",	"&rArr;"),	# ISOtech
        (r"hA", "&iff;"),	# ISOtech: horizontal double-headed arrow
        (r"dA",	"&dArr;"),	# ISOamsa
        (r"uA",	"&uArr;"),	# ISOamsa
        (r"vA",	"&vArr;"), 	# ISOamsa: vertical double-headed double arrow
        (r"an", "&an;"),	# Internal pseudo-entity
        # Lines
        (r"ba",	"&verbar;"),	# ISOnum
        (r"br", "&boxv;"),	# ISObox +
        (r"ul", "_"),   	# +
        (r"rn", "&macr;"),	# ISOdia +
        (r"ru", "&lowbar;"),	# ISOnum +
        (r"bb",	"&brvbar;"),	# ISOnum
        (r"sl", "/"),   	# +
        (r"rs",	"&bsol;"),	# ISOnum
        ## Text markers
        # Old troff \(ci, \(bu, \(dd, \(dg go here
        (r"ci", "&cir;"),	# ISOpub +
        (r"bu", "&bull;"),	# ISOpub +
        (r"dd", "&Dagger;"),	# ISOpub +
        (r"dg", "&dagger;"),	# ISOpub +
        (r"lz",	"&loz;"),	# ISOpub
        (r"sq", "&squf;"),	# ISOpub +
        (r"ps",	"&para;"),	# ISOnum: paragraph or pilcrow sign
        (r"sc",	"&sect;"),	# ISOnum +
        (r"lh", "&lh;"),	# Internal pseudo-entity +
        (r"rh", "&rh;"), 	# Internal pseudo-entity +
        (r"at",	"&commat;"),	# ISOnum
        (r"sh",	"&num;"),	# ISOnum
        (r"CR",	"&CR;"),	# Internal pseudo-entity
        (r"OK",	"&check;"),	# ISOpub
        # Legal symbols
        (r"co", "&copy;"),	# ISOnum +
        (r"rg", "&trade;"),	# ISOnum +
        (r"tm",	"&trade;"),	# ISOnum
        (r"bs", "&phone;"),	# ISOpub (for the Bell logo) +
        # Currency symbols
        (r"Do",	"&dollar;"),	# ISOnum
        (r"ct",	"&cent;"),	# ISOnum +
        (r"eu",	"&euro;"),
        (r"Eu",	"&euro;"),
        (r"Ye",	"&yen;"),	# ISOnum
        (r"Po",	"&pound;"),	# ISOnum
        (r"Cs",	"&curren;"),	# ISOnum: currency sign
        (r"Fn",	"&fnof;"),	# ISOtech
        # Units
        (r"de", "&deg;"),	# ISOnum +
        (r"%0",	"&permil;"),	# ISOtech: per thousand, per mille sign
        (r"fm", "&prime;"),	# ISOtech +
        (r"sd",	"&Prime;"),	# ISOtech
        (r"mc",	"&micro;"),	# ISOnum
        (r"Of",	"&ordf;"),	# ISOnum
        (r"Om",	"&ordm;"),	# ISOnum
        # Logical symbols
        (r"AN",	"&and;"),	# ISOtech
        (r"OR",	"&or;"),	# ISOtech
        (r"no", "&not;"),	# ISOnum +
        (r"tno","&not;"),	# ISOnum
        (r"te",	"&exist;"), 	# ISOtech: there exists, existential quantifier
        (r"fa",	"&forall;"), 	# ISOtech: for all, universal quantifier
        (r"st",	"&bepsi;"),	# ISOamsr: such that
        (r"3d",	"&there4;"),	# ISOtech
        (r"tf",	"&there4;"),	# ISOtech
        (r"or", "&verbar;"),	# ISOnum +
        # Mathematical symbols
        (r"12", "&frac12;"),	# ISOnum +
        (r"14", "&frac14;"),	# ISOnum +
        (r"34", "&frac34;"),	# ISOnum +
        (r"18", "&frac18;"),	# ISOnum
        (r"38", "&frac38;"),	# ISOnum
        (r"58", "&frac58;"),	# ISOnum
        (r"78", "&frac78;"),	# ISOnum
        (r"S1",	"&sup1;"),	# ISOnum
        (r"S2",	"&sup2;"),	# ISOnum
        (r"S3",	"&sup3;"),	# ISOnum
        (r"pl", "&plus;"),	# ISOnum +
        (r"mi", "&minus;"),	# ISOtech +
        (r"-+",	"&mnplus;"),	# ISOtech
        (r"+-", "&plusmn;"),	# ISOnum +
        (r"t+-", "&plusmn;"),	# ISOnum
        (r"pc",	"&middot;"),	# ISOnum
        (r"md",	"&middot;"),	# ISOnum
        (r"mu", "&times;"),	# ISOnum +
        (r"tmu", "&times;"),	# ISOnum
        (r"c*",	"&otimes;"),	# ISOamsb: multiply sign in a circle
        (r"c+",	"&oplus;"),	# ISOamsb: plus sign in a circle
        (r"di", "&divide;"),	# ISOnum +
        (r"tdi", "&divide;"),	# ISOnum
        (r"f/",	"&horbar;"),	# ISOnum: horizintal bar for fractions
        (r"**", "&lowast;"),	# ISOtech +
        (r"&lt;=",	"&le;"),	# ISOtech (XMLified) +
        (r"&gt;=",	"&ge;"),	# ISOtech (XMLified) +
        (r"&lt;&lt;", "&Lt;"),	# ISOamsr (XMLified)
        (r"&gt;&gt;", "&Gt;"),	# ISOamsr (XMLified)
        (r"!=",	"&ne;"),	# ISOtech +
        (r"==", "&equiv;"),	# ISOtech +
        (r"ne",	"&nequiv;"),	# ISOamsn
        (r"=~",	"&cong;"),	# ISOamsr
        (r"|=",	"&asymp;"),	# ISOamsr +
        (r"ap", "&sim;"),	# ISOtech +
        (r"~~",	"&ap;"),	# ISOtech
        (r"pt", "&prop;"),	# ISOtech +
        (r"es", "&empty;"),	# ISOamso +
        (r"mo", "&isin;"),	# ISOtech +
        (r"nm",	"&notin;"),	# ISOtech
        (r"sb", "&sub;"),	# ISOtech +
        (r"nb",	"&nsub;"),	# ISOamsr
        (r"sp", "&sup;"),	# ISOtech +
        (r"nc",	"&nsup;"),	# ISOamsn
        (r"ib", "&sube;"),	# ISOtech +
        (r"ip", "&supe;"),	# ISOtech +
        (r"ca", "&cap;"),	# ISOtech +
        (r"cu", "&cup;"),	# ISOtech +
        (r"/_",	"&ang;"),	# ISOamso
        (r"pp",	"&perp;"),	# ISOtech
        (r"is", "&int;"),	# ISOtech
        (r"integral", "&int;"),	# ISOtech
        (r"sum", "&sum;"),	# ISOamsb
        (r"product", "&prod;"),	# ISOamsb
        (r"coproduct", "&coprod;"),	# ISOamsb
        (r"gr", "&nabla;"),	# ISOtech +
        (r"sr", "&radic;"),	# ISOtech +
        (r"sqrt", "&radic;"),	# ISOtech
        (r"radicalex", "&radicalex;"),	# Internal pseudo-entity
        (r"sqrtex", "&sqrtex;"),	# Internal pseudo-entity
        (r"lc", "&lc;"),	# Internal pseudo-entity +
        (r"rc", "&rc;"),	# Internal pseudo-entity +
        (r"lf", "&lf;"),	# Internal pseudo-entity +
        (r"rf", "&rf;"),	# Internal pseudo-entity +
        (r"if", "&infin;"),	# ISOtech +
        (r"Ah",	"&aleph;"),	# ISOtech
        (r"Im",	"&image;"),	# ISOamso: Fraktur I, imaginary
        (r"Re",	"&real;"),	# ISOamso: Fraktur R, real
        (r"wp",	"&weierp;"),	# ISOamso
        (r"pd",	"&part;"),	# ISOtech: partial differentiation sign
        (r"-h",	"&planck;"),	# ISOamso: h-bar (Planck's constant) +
        (r"hbar","&planck;"),	# ISOamso: h-bar (Planck's constant)
        # Greek glyphs
        (r"*A", "&Agr;"),	# ISOgrk1 +
        (r"*B", "&Bgr;"),	# ISOgrk1 +
        (r"*G", "&Ggr;"),	# ISOgrk1 +
        (r"*D", "&Dgr;"),	# ISOgrk1 +
        (r"*E", "&Egr;"),	# ISOgrk1 +
        (r"*Z", "&Zgr;"),	# ISOgrk1 +
        (r"*Y", "&EEgr;"),	# ISOgrk1 +
        (r"*H", "&THgr;"),	# ISOgrk1 +
        (r"*I", "&Igr;"),	# ISOgrk1 +
        (r"*K", "&Kgr;"),	# ISOgrk1 +
        (r"*L", "&Lgr;"),	# ISOgrk1 +
        (r"*M", "&Mgr;"),	# ISOgrk1 +
        (r"*N", "&Ngr;"),	# ISOgrk1 +
        (r"*C", "&Xi;"),	# ISOgrk1 +
        (r"*O", "&Ogr;"),	# ISOgrk1 +
        (r"*P", "&Pgr;"),	# ISOgrk1 +
        (r"*R", "&Rgr;"),	# ISOgrk1 +
        (r"*S", "&Sgr;"),	# ISOgrk1 +
        (r"*T", "&Tgr;"),	# ISOgrk1 +
        (r"*U", "&Ugr;"),	# ISOgrk1 +
        (r"*F", "&PHgr;"),	# ISOgrk1 +
        (r"*X", "&KHgr;"),	# ISOgrk1 +
        (r"*Q", "&PSgr;"),	# ISOgrk1 +
        (r"*W", "&OHgr;"),	# ISOgrk1 +
        (r"*W", "&OHgr;"),	# ISOgrk1 +
        (r"*a", "&agr;"),	# ISOgrk1 +
        (r"*b", "&bgr;"),	# ISOgrk1 +
        (r"*g", "&ggr;"),	# ISOgrk1 +
        (r"*d", "&dgr;"),	# ISOgrk1 +
        (r"*e", "&egr;"),	# ISOgrk1 +
        (r"*z", "&zgr;"),	# ISOgrk1 +
        (r"*y", "&eegr;"),	# ISOgrk1 +
        (r"*h", "&thgr;"),	# ISOgrk1 +
        (r"*i", "&igr;"),	# ISOgrk1 +
        (r"*k", "&kgr;"),	# ISOgrk1 +
        (r"*l", "&lgr;"),	# ISOgrk1 +
        (r"*m", "&mgr;"),	# ISOgrk1 +
        (r"*n", "&ngr;"),	# ISOgrk1 +
        (r"*c", "&xi;"),	# ISOgrk1 +
        (r"*o", "&ogr;"),	# ISOgrk1 +
        (r"*p", "&pgr;"),	# ISOgrk1 +
        (r"*r", "&rgr;"),	# ISOgrk1 +
        (r"ts", "&sfgr;"),	# ISOgrk1 +
        (r"*s", "&sgr;"),	# ISOgrk1 +
        (r"*t", "&tgr;"),	# ISOgrk1 +
        (r"*u", "&ugr;"),	# ISOgrk1 +
        (r"*f", "&phgr;"),	# ISOgrk1 +
        (r"*x", "&khgr;"),	# ISOgrk1 +
        (r"*q", "&psgr;"),	# ISOgrk1 +
        (r"*w", "&ohgr;"),	# ISOgrk1 +
        (r"+h",	"&b.thetas;"),	# ISOgrk4: variant theta
        (r"+f",	"&b.phiv;"),	# ISOgrk4: variant phi
        (r"+p",	"&b.omega;"),	# ISOgrk4: variant pi, looking like omega
        (r"+e",	"&b.epsiv;"),	# ISOgrk4: variant epsilon
        # Card symbols
        (r"CL",	"&clubs;"),	# ISOpub: club suit
        (r"SP",	"&spades;"),	# ISOpub: spade suit
        (r"HE",	"&hearts;"),	# ISOpub: heart suit
        # u2661 is listed at this point in the groff table
        (r"DI",	"&diams;"),	# ISOpub: diamond suit
        # u2662 is listed at this point in the groff table
        # Classic troff special characters not in groff
        (r"%", "&shy;"),	# ISOnum
        (r"'", "&acute;"),	# ISOdia
        (r"bl", "&phonexb;"),	# ISOpub
        (r"eq", "&equals;"),	# ISOnum
        (r"ge", "&ge;"),	# ISOtech
        (r"le", "&le;"),	# ISOtech
        (r"~=",	"&cong;"),	# ISOamsr
        # This is a mechanically hacked copy of the "Accented characters"
        # table section above.  Note, letters followed by ' have been
        # omitted because that's the troff string delimiter.
        (r"o'A:'",	"&Auml;"),	# ISOlat1
        (r"o'E:'",	"&Euml;"),	# ISOlat1
        (r"o'I:'",	"&Iuml;"),	# ISOlat1
        (r"o'O:'",	"&Ouml;"),	# ISOlat1
        (r"o'U:'",	"&Uuml;"),	# ISOlat1
        (r"o'Y:'",	"&Yuml;"),	# ISOlat2
        (r"o'a:'",	"&auml;"),	# ISOlat1
        (r"o'e:'",	"&euml;"),	# ISOlat1
        (r"o'i:'",	"&iuml;"),	# ISOlat1
        (r"o'o:'",	"&ouml;"),	# ISOlat1
        (r"o'u:'",	"&uuml;"),	# ISOlat1
        (r"o'y:'",	"&yuml;"),	# ISOlat1
        (r"o'A^'",	"&Acirc;"),	# ISOlat1
        (r"o'E^'",	"&Ecirc;"),	# ISOlat1
        (r"o'I^'",	"&Icirc;"),	# ISOlat1
        (r"o'O^'",	"&Ocirc;"),	# ISOlat1
        (r"o'U^'",	"&Ucirc;"),	# ISOlat1
        (r"o'a^'",	"&acirc;"),	# ISOlat1
        (r"o'e^'",	"&ecirc;"),	# ISOlat1
        (r"o'i^'",	"&icirc;"),	# ISOlat1
        (r"o'o^'",	"&ocirc;"),	# ISOlat1
        (r"o'u^'",	"&ucirc;"),	# ISOlat1
        (r"o'A`'",	"&Agrave;"),	# ISOlat1
        (r"o'E`'",	"&Egrave;"),	# ISOlat1
        (r"o'I`'",	"&Igrave;"),	# ISOlat1
        (r"o'O`'",	"&Ograve;"),	# ISOlat1
        (r"o'U`'",	"&Ugrave;"),	# ISOlat1
        (r"o'a`'",	"&agrave;"),	# ISOlat1
        (r"o'e`'",	"&egrave;"),	# ISOlat1
        (r"o'i`'",	"&igrave;"),	# ISOlat1
        (r"o'o`'",	"&ograve;"),	# ISOlat1
        (r"o'u`'",	"&ugrave;"),	# ISOlat1
        (r"o'A~'",	"&Atilde;"),	# ISOlat1
        (r"o'N~'",	"&Ntilde;"),	# ISOlat1
        (r"o'O~'",	"&Otilde;"),	# ISOlat1
        (r"o'a~'",	"&atilde;"),	# ISOlat1
        (r"o'n~'",	"&ntilde;"),	# ISOlat1
        (r"o'o~'",	"&otilde;"),	# ISOlat1
        (r"o'Sv'",	"&Scaron;"),	# ISOlat2
        (r"o'sv'",	"&scaron;"),	# ISOlat2
        (r"o'Zv'",	"&Zcaron;"),	# ISOlat2
        (r"o'zv'",	"&zcaron;"),	# ISOlat2
        (r"o'C,'",	"&Ccedil;"),	# ISOlat1
        (r"o'c,'",	"&ccedil;"),	# ISOlat1
        (r"o'L/'",	"&Lstrok;"),	# ISOlat2: Polish L with a slash
        (r"o'l/'",	"&lstrok;"),	# ISOlat2: Polish l with a slash
        (r"o'O/'",	"&Oslash;"),	# ISOlat1
        (r"o'o/'",	"&oslash;"),	# ISOlat1
        (r"o'Ao'",	"&Aring;"),	# ISOlat1
        (r"o'ao'",	"&aring;"),	# ISOlat1
      )
    xmlifyPatterns = [(reCompile(x[0]), x[1]) for x in (
        # Order of these & substitutions is significant.
        # These have to go early, otherwise you mess up tags
        # generated by requests.
        (r";",		"&semi;"),		# Not a real entity
        (r"&",		"&amp;"),
        (r"&amp;semi;",	"&semi;"),
        (r"<--",	"&lt;&mdash;&mdash;"),
        (r"-->",	"&mdash;&mdash;&gt;"),
        (r"<",		"&lt;"),
        (r">",		"&gt;"),
        # Blank lines go away
        (r'^\.\\"\s+-*$',  ""),
        )]
    prefixLifts = [(reCompile("%s <emphasis remap='[BI]'>([^<]+)</emphasis>"  % x[0]), r"file <%s>\1</%s>" % (x[1], x[1])) for x in (
        ("file", "filename"),
        ("command", "command"),
        ("option", "option"),
        )]

    # These are interpreter state which can be modified by the .cc command
    ctrl = "."
    ctrlNobreak = "'"

    def __init__(self, source, verbose):
        self.source = source
        self.verbose = verbose
        self.strings = {}	# String table for ds, as, rm, rn
        self.macros = {}	# String table for de, ae, rm, rn
        self.macroend = ".."	# Macro ender character as set by .em
        self.macroargs = []	# Macro argument stack
        self.macronames = []	# Macro name stack (only used in error msgs)
        self.rsin = False	# Within synthetic .RS created by .in +4
        self.linenos = []	# Line number stack (only used in error msgs)
        self.nf = False		# Initially we're filling and adjusting
        self.screen = False	# Initially we're not in a screen context
        self.inBlock = False	# Initially we're not in a block context
        self.ifstack = []
        self.evaldepth = ""
        self.longnames = []
        self.groffFeatures = []
        self.nonportableFeatures = []
        self.entitiesFromStrings = False
        self.ignoreOutdent = None
        self.registers = {	# Register table for nr, rr, rnn
            ".g": '0',
            ".$": lambda: str(len([x for x in self.macroargs and self.macroargs[-1] if x])),
            ".T": "XML-DocBook",
            }
        TroffInterpreter.translations = {}
        def tmerge(instance, prefix, glyph, entity):
            if prefix not in instance.translations:
                instance.translations[prefix] = []
            instance.translations[prefix].append((glyph, entity))
        for (glyph, entity) in TroffInterpreter.entityTranslations:
            if glyph.startswith("o'"):
                tmerge(TroffInterpreter, "\\o", r"\%s" % glyph, entity)
            else:
                # Treat XML entities as the single characters they translate
                if len(glyph) == 1 or glyph[0] == '&':
                    tmerge(TroffInterpreter, "\\", r"\%s" % glyph, entity)
                if len(glyph) == 2 or '&' in glyph:
                    tmerge(TroffInterpreter, "\\(", r"\(%s" % glyph,entity)
                if len(glyph) >= 2:
                    tmerge(TroffInterpreter, "\\[", r"\[%s]" % glyph,entity)

    def expandStrings(self, line):
        "Expand strings in the given line."
        if '\\' not in line:
            return line
        # Expand all known strings
        for (key, value) in list(self.strings.items()):
            line = line.replace(r"\*["+key+"]", value)
            if len(key) == 1:
                line = line.replace(r"\*"+key, value)
            elif len(key) == 2:
                line = line.replace(r"\*("+key, value)
        # Expand unknown strings as empty
        line = re.sub(r"\\\*[a-zA-Z]", "", line)
        line = re.sub(r"\\\*\([a-zA-Z][a-zA-Z]", "", line)
        # Maybe we're in a macro eval?
        if self.macroargs:
            for argnum in range(1, 9):
                line = line.replace(r"\$%d" % argnum, self.macroargs[-1][argnum-1])
            line = line.replace(r"\$*", " ".join(self.macroargs[-1]))
            line = line.replace(r"\$@", " ".join(['"%s"' % s for s in self.macroargs[-1]]))
        return line

    def evalRegister(self, key):
        val = self.registers[key]
        if type(val) in (type(""), type(0)):
            return val
        else:
            return apply(val)

    def evalTerm(self, exp):
        "Pop a term off an expression string and evaluate it."
        if exp == "":
            return ("", "")
        # Evaluate built-in conditions
        elif exp[0] == 'n':
            return ("1", exp[1:])	# We're an nroff-like device
        elif exp[0] == 't':
            return ("0", exp[1:])	# Not a troff-like device
        elif exp[0] == 'o':
            return ("1", exp[1:])	# Forever on page 1
        elif exp[0] == 'e':
            return ("0", exp[1:])	# No page breaks
        elif exp[0] == 'v':
            return ("0", exp[1:])	# This isn't vroff either
        elif exp[0] == "m":
            return ("0", exp[1:])	# We are colorless, alas
        elif exp[0] == "r":
            exp = exp[1:]
            if ')' in exp:
                regname = exp[:exp.find(')')]
                tail = exp[exp.find(')'):]
            else:
                regname = exp
                tail = ""
            if regname in self.registers:
                return ("1", tail)
            else:
                return ("0", tail)
        elif exp[0] == 'c':
            # This ring-around-the-rosy is necessary to defeat some
            # machinery that groff uses to define tty graphics.  We
            # need to be sure, for example, that c\[if] evaluates
            # to 1.  To make this work, \[if] has to be canonicalized
            # to \(if and looked up in the translation tables of the
            # active interpreters.  Otherwise including tty-char.tmac
            # will cause grave confusion.
            if exp[1:3] == r"\*":
                glyph = exp[2]
                exp = exp[3:]
            elif exp[1:3] == r"\(":
                glyph = exp[2:4]
                exp = exp[4:]
            else: # exp[1:3] == r"\["
                rbracket = exp.find("]")
                glyph = exp[2:rbracket]
                exp = exp[rbracket+1:]
            if len(glyph) == 1:
                glyph = r"\*" + glyph
            elif len(glyph) == 2:
                glyph = r"\(" + glyph
            else:
                glyph = r"\[" + glyph + "]"
            for interpreter in self.source.interpreters:
                if glyph in interpreter.translations:
                    return ("1", exp[len(glyph):])
                else:
                    return ("0", exp[len(glyph):])
        # Treat dEQ and dEN as always defined, because we're only going
        # to encounter them in inclusions generated by eqn because
        # of an EQ/EN.
        elif exp[:2] in ("dEQ", "dEN"):
            return ("1", exp[1:])
        elif exp[0] == "d":
            # Supposed to be true if there's a "string, macro, diversion,
            # or request" with the specified name. We ignore diversions.
            # Alas, since there's no list of requests anywhere we're
            # going to lose if that case is ever used; fortunately it
            # doesn't seem to be.
            if ')' in exp:
                name = exp[:exp.find(')')]
                tail = exp[exp.find(')'):]
            else:
                name = exp
                tail = ""
            if name in self.strings or exp[1:] in self.macros:
                return ("1", tail)
            else:
                return ("0", tail)
        # Evaluate numeric registers
        elif exp.startswith(r"\n"):
            exp = exp[2:]
            increment = None
            if exp[0] == '+':
                increment = 1
                exp = exp[1:]
            elif exp[0] == '-':
                increment = -1
                exp = exp[1:]
            # ...with two-character names
            if exp[0] == '(':
                end = 3
                register = exp[1:3]
            # ...with longnames
            elif exp[0] == '[':
                end = exp.find("]")+1
                register = exp[1:end-1]
            # ...with one-character names
            else:
                end = 1
                register = exp[0]
            if register in self.registers:
                if increment is not None:
                    self.registers[register] = str(int(self.evalRegister(register))  + increment)
                return (self.evalRegister(register), exp[end:])
            else:
                if increment is not None:
                    self.registers[register] = str(increment)
            return ("0", exp[end:])
        # Half-assed job of evaluating \w, without the side effects.
        # Our 'basic units' are the width of a monospace character
        elif exp.startswith(r"\w"):
            e = exp[3:].find(exp[2])+3
            istr = exp[3:e]
            if istr in self.strings:
                istr = self.strings[istr]
            elif istr.startswith(r"\*("):
                istr = ""
            entity = None
            val = 0
            for c in istr:
                if entity == None:
                    if c == '&':
                        entity = ""
                    else:
                        val += 1
                elif entity != None and c == ';':
                    # In groff an en is supposed to be half an em.
                    # &zerosp;, &emsp13; and &emsp14; are also obvious.
                    # The rest of these are from eyeballing the %isopub
                    # page in the on-line DocBook reference.
                    val += {"ensp" : 0.5,
                            "emsp13" : 0.33,
                            "emsp14" : 0.25,
                            "puncsp" : 0.33,
                            "thinsp" : 0.16,
                            "hairsp" : 0.01,
                            "zerosp" : 0,
                        }.get(entity, 1)
                    entity = None
            #self.source.warning("%s evaluated to %d" % (exp[:e+1], val))
            return (repr(val), exp[e+1:])
        # Numeric literal may stand alone or be followed by an operator
        elif exp[0] in '-0123456789':
            v = ""
            expcopy = exp
            if expcopy[0] in "+-":
                v += expcopy[0]
                expcopy = expcopy[1:]
            while expcopy:
                if expcopy[0] in '0123456789':
                    v += expcopy[0]
                    expcopy = expcopy[1:]
                else:
                    break
            return (v, expcopy)
        # Some groff pages actually use this!
        elif exp.startswith(r"\B'") and "'" in exp[3:]:
            self.groffFeatures.append(r"\B")
            end = 3 + exp[3:].find("'")
            if re.compile("[0-9]+$").match(exp[3:end]):
                return ('1', exp[:end+1])
            else:
                return ('0', exp[:end+1])
        # Could be a string comparison
        elif exp.count(exp[0]) >= 3:
            count = 0
            for i in range(len(exp)):
                if exp[i] == exp[0]:
                    count += 1
                if count == 3:
                    break
            remainder = exp[i+1:]
            exp = exp[:i]
            expparts = exp[1:].split(exp[0])
            return (repr(int(expparts[0]==expparts[1])), remainder)
        # Maybe it's a parenthesized expression
        elif exp[0] == '(':
            depth = 0
            for end in range(len(exp)):
                if exp[i] == '(':
                    depth += 1
                if exp[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end += 1
                        break
            else:
                end = -1
            if end == -1:
                self.source.error("unterminated parenthetical %s" % exp)
            return (self.evalExpr(exp[1:end]), exp[end+1:])
        # Maybe we couldn't do anything with it.
        else:
            return ("", exp)

    def evalExpr(self, exp):
        "Evaluate expressions for use in groff conditionals."
        if macroVerbosity in self.source.verbose:
            self.evaldepth += " "
            self.source.notify("%s->evalExpr(%s)" % (self.evaldepth, exp))
        # Accept ! prefix
        if exp and exp[0] == "!":
            v = self.evalExpr(exp[1:])
            v = str(int(len(v)==0 or v == '0'))
        elif exp and exp[0] == "(":
            v = self.evalExpr(exp[1:-1])
        else:
            # Expression can consist of a single term only
            (head, tail) = self.evalTerm(exp)
            if macroVerbosity in self.source.verbose:
                self.source.notify("%s(hd, tail)=(%s, %s)" % (self.evaldepth,head, tail))
            if tail == "":
                v = head
            # Arithmetic
            elif tail.startswith("+"):
                v = repr(int(head) + int(self.evalExpr(tail[1:])))
            elif tail.startswith("-"):
                v = repr(int(head) - int(self.evalExpr(tail[1:])))
            elif tail.startswith("*"):
                v = repr(int(head) * int(self.evalExpr(tail[1:])))
            elif tail.startswith("/"):
                v = repr(int(head) / int(self.evalExpr(tail[1:])))
            elif tail.startswith("%"):
                v = repr(int(head) % int(self.evalExpr(tail[1:])))
            # Logical operators
            elif tail.startswith("&amp;"):
                v = repr(int(int(head) and int(self.evalExpr(tail[5:]))))
            elif tail.startswith(":"):
                v = repr(int(int(head) or int(self.evalExpr(tail[5:]))))
            # Relationals
            elif tail.startswith("=="):
                v = repr(int(int(head) == int(self.evalExpr(tail[2:]))))
            elif tail.startswith("="):
                v = repr(int(int(head) == int(self.evalExpr(tail[1:]))))
            elif tail.startswith("&gt;"):
                v = repr(int(int(head) > int(self.evalExpr(tail[4:]))))
            elif tail.startswith("&lt;"):
                v = repr(int(int(head) < int(self.evalExpr(tail[4:]))))
            elif tail.startswith("&gt;="):
                v = repr(int(int(head) >= int(self.evalExpr(tail[5:]))))
            elif tail.startswith("&lt;="):
                v = repr(int(int(head) <= int(self.evalExpr(tail[5:]))))
            # Max/min
            elif tail.startswith("&gt;?"):
                v = repr(max(int(head), int(self.evalExpr(tail[5:]))))
            elif tail.startswith("&lt;?"):
                v = repr(min(int(head), int(self.evalExpr(tail[5:]))))
            # We don't know what's going on, just call it true.
            else:
                self.source.error("bogus-looking expression %s" % exp)
                v = '1'
        if macroVerbosity in self.source.verbose:
            self.source.notify("%s<-evalExpr(%s) -> %s" % (self.evaldepth, exp, v))
            self.evaldepth = self.evaldepth[:-1]
        return v

    def skiptoend(self, tokens):
        "Skip command lines in a conditional arm we're going to ignore"
        if macroVerbosity in self.verbose:
            self.source.notify("skiptoend(%s) started" % repr(tokens))
        wholeline = "".join(tokens)
        brace = wholeline.find("{")
        if brace > -1 and (brace == len(wholeline)-1 or wholeline[brace+1] != "}"):	# If there's an unbalanced { on the line.
            elsedepth = 1		# Eat lines until balancing \}
            while self.source.lines:
                line = self.source.popline()
                if line[1:3] in ("if", "ie", "el") and line.find(r"\{") > -1:
                    elsedepth += 1
                elif line.find(r"\}") > -1:
                    elsedepth -= 1
                    if elsedepth == 0:
                        break
        if macroVerbosity in self.verbose:
            self.source.notify("skiptoend(%s) finished" % repr(tokens))

    def interpret(self, line, tokens, _):
        command = tokens[0][1:]
        args = tokens[1:]
        if len(command) > 2:
            self.nonportableFeatures.append(command)
        # .nl is apparently an undocumented synonym for .br in groff(1).
        if command == "br" or command == "nl":
            if self.source.inSynopsis():
                self.source.emit("<sbr/>")
            elif self.source.bodySection() and not self.nf:
                self.source.paragraph()
        elif command == "ti":
            if self.source.inSynopsis():
                pass
            elif self.source.troff.macronames:
                self.source.warning(".ti seen in macro body")
                self.source.passthrough([command] + args)
            elif self.source.peekline().startswith("."):
                self.source.warning(".ti with following command")
                self.source.passthrough([command] + args)
            else:
                if args[0].startswith("-"):
                    self.source.warning(".ti with negative indent.")
                self.source.emit("<blockquote remap='.ti'><para>")
                self.source.emit(self.source.popline())
                self.source.emit("</para></blockquote>")
        elif command == "in":
            if self.source.inSynopsis():
                pass
            # Hacky way of dealing with
            # .in +4n
            # .sp
            # .nf
            # We can just ignore .sp in this context and fall through
            # to the next case..
            if self.source.peekline().startswith(".sp"):
                self.source.passthrough([command] + args)
                self.source.popline()
            # Also ignore a blank line here, as in cpuset.7
            if not self.source.peekline():
                self.source.popline()
            # Hacky way of dealing with
            # .in +4n
            # .EX
            # That is, we tell it to expect a closing .in and ignore
            # it as though the .EX had come first.  This way we avoid
            # emitting a warning about an unstructured .in call. This
            # case fiores on a lot of the Linux core manpages.
            if self.source.peekline().startswith(".EX") and args and args[0].startswith("+"):
                self.ignoreOutdent = args[0]
                self.source.passthrough([command] + args)
            # Hacky way of dealing with
            # .in +4n
            # .nf
            # That is, we tell it to expect a closing .in and ignore
            # it as though the .nf had come first.  This way we avoid
            # emitting a warning about an unstructured .in call.
            elif self.source.peekline().startswith(".nf") and args and args[0].startswith("+"):
                self.ignoreOutdent = args[0]
                self.source.passthrough([command] + args)
            # Some .in pairs associated with displays can be ignored
            elif self.source.troff.nf and args and self.ignoreOutdent is None:
                self.ignoreOutdent = args[0]
            elif self.ignoreOutdent is not None:
                if not args:
                    pass	# bare .in outdenting a display
                elif args[0][0]=='-' and args[0][1:]==self.ignoreOutdent[1:]:
                    pass	# matching outdent
                else:
                    self.source.warning("closing %s %s doesn't match opener %s" % (command, args.join(" "), self.ignoreOutdent))
                    self.source.passthrough([command] + args)
                self.ignoreOutdent = None
            elif not self.source.inSynopsis():
                if args[0] == "+4" and not self.rsin:
                    self.source.emit(".RS")
                    self.rsin = True
                elif self.rsin and len(args) == 0:
                    self.source.emit(".RE")
                    self.rsin = False
                else:
                    self.source.warning(".in seen in body section")
                    self.source.passthrough([command] + args)
        elif command == "ta":
            # We only try to interpret a very restricted subset of tab
            # stop settings here, for three reasons: (1) the only
            # thing we can do with tabs is space-expand them when a
            # fixed-width font is set, (2) man pages do not in general
            # use sophisticated tab stopping, (3) the full semantics
            # is hairy enough that we'd probably get it wrong.
            parseable = True
            if not args:
                self.source.tabstops = None
            else:
                try:
                    tabstops = []
                    for arg in args:
                        if arg.endswith("m") or arg.endswith("n"):
                            arg = arg[:-1]
                        if arg[0] == '+':
                            arg = arg[1:]
                            offset = -sum(tabstops)
                        else:
                            offset = 0
                        tabstops.append(offset + int(arg))
                    self.source.tabstops = tabstops
                except ValueError:
                    parseable = False
            while self.source.ignorable(self.source.peekline()):
                # Ignore following .ne and similar crap
                self.source.passthrough(self.source.popline().split())
            # Decompile ad-hoc tables.  But don't be fooled by C source listings
            # that happen to have embedded tabs.
            if not cSourceRe.search(self.source.peekline()) \
                   and '\t' in self.source.peekline():
                # Aha, it's a table line
                table = []
                maxtabs = 0
                while True:
                    bodyline = self.source.peekline()
                    if matchCommand(bodyline, "br"):
                        self.source.popline()
                    elif '\t' in bodyline and not isCommand(bodyline):
                        if len(args) == 1:
                            # Wacky special case. Some pages, like
                            # enscript.1, have an ad-hoc table intended
                            # to be two-column.  Only one tab stop is
                            # set, but the gutter may consist of more
                            # than one tab. Cope with this.
                            bodyline = re.sub("\t+", "\t", bodyline)
                        maxtabs = max(maxtabs, bodyline.count("\t"))
                        table.append(bodyline)
                        self.source.popline()
                    else:
                        self.source.pushline(bodyline)
                        break
                table = [".TS"," ".join(["l"]*(maxtabs+1))+"."]+table+[".TE"]
                # Queue up the generated table to be turned into DocBook.
                self.source.lines = table + self.source.lines
            else:
                if not self.source.inSynopsis() and not parseable and [s for s in self.source.lines if '\t' in s]:
                    self.source.warning("uninterpretable .ta seen in body section")
                self.source.passthrough([command] + args)
        elif command == "sp":
            # Treat this as a paragraph break in body text.
            if self.source.bodySection() and not self.nf:
                self.source.endParagraph(label="sp")
            # Always insert the space, it can't hurt and may help
            # (e.g in function synopses).
            lines = 1
            if len(args) > 0 and args[0]:
                try:
                    lines = int(args[0])
                except ValueError:
                    pass
            for i in range(lines):
                self.source.diversion.append("")
            if self.source.bodySection() and not self.nf:
                self.source.needPara = True
        elif command == "Sp" and "Sp" not in self.longnames:
            # Catches a common error.  See for example mono.1
            self.source.pushline(".sp")
        elif command == "bp":
            self.nonportableFeatures.append("bp")
            if self.nf:
                # Breaking up display markup causes too many problems
                # at validation time to be worth it.
                self.source.passthrough([".bp"] + args)
            else:
                self.source.emit("<beginpage/>")
                self.source.paragraph()
        elif command == "ft":
            # Ugh...this deals with sequences like
            # .ft CW
            # .in +4n
            # .nf
            # which frequently occur in attemps to simulate .DS/.DE and
            # are going to turn into <para><emphasis remap="CW"></para>
            # which is guaranteed to lose because the scope of <emphasis>
            # can't cross a paragraph boundary.  To fix this we
            # must swap the .ft and .nf...
            if args and args[0]!="R" and self.source.peekline():
                # skip any number of things like .in
                while self.source.ignorable(self.source.peekline(), nocomplaints=1):
                    self.source.emit(makeComment(self.source.popline()))
                if self.source.peekline()[1:3] == "nf":
                    self.source.popline()
                    self.source.endParagraph(label="ft")
                    if self.source.quiet:
                        trailer = ""
                    else:
                        trailer = ' remap=".ft %s .nf"' % args[0]
                    self.source.emit("<literallayout%s>" % trailer)
                    self.nf = True
            # The actual highlight change
            if self.nf:
                if len(tokens) == 1:
                    self.source.emit(r"\fP")
                elif len(tokens[1]) == 1:
                    self.source.emit(r"\f" + tokens[1])
                else:
                    self.source.emit(r"\f(" + tokens[1])
        elif command in ("fi", "FI"):	# .FI is an oddly common typo
            if self.nf or self.screen:
                # Flip side of the above.  Sequences like
                # .fi
                # .in +4n
                # .ft
                # have to be inverted.
                fontswitch = ""
                if self.source.peekline():
                    while blankline.match(self.source.peekline()):
                        self.source.popline()
                        while self.source.ignorable(self.source.peekline(), nocomplaints=1):
                            self.source.emit(makeComment(self.source.popline()))
                    nextl = self.source.peekline()
                    if nextl and nextl[0:3] == TroffInterpreter.ctrl + "ft":
                        fontswitch = nextl
                        cmd = lineparse(self.source.popline())
                        if len(cmd) == 1:
                            self.source.emit(r"\fR")
                        else:
                            self.source.emit(r"\f" + cmd[1])
                # End the literal layout.
                # Because emphasis can't cross a block-layout boundary,
                # we need to turn off highlights here.
                if self.source.quiet:
                    trailer = ""
                else:
                    trailer = " <!-- .fi%s -->" % fontswitch
                if self.screen:
                    self.source.emit(r"\fR</screen>" + trailer)
                    self.screen = False
                else:
                    self.source.emit(r"\fR</literallayout>" + trailer)
                    self.nf = False
                self.source.needParagraph()
        elif command in ("nf", "NF"):	# .NF is an oddly common typo
            self.source.endParagraph(label="nf")
            if self.source.peekline() == TroffInterpreter.ctrl + "ft CW":
                self.source.popline()
                self.source.endParagraph()
                self.source.emit("<screen remap='.nf .ft CW'>")
                self.screen = True
                self.nf = True
            else:
                self.source.emit("<literallayout remap='.nf'>")
                self.source.endParagraph()
                self.nf = True
        elif command in ("ul", "cu"):
            self.nonportableFeatures.append(command)
            if args:
                try:
                    forlines = int(args)
                except (ValueError, TypeError):
                    forlines = 1
                    self.source.error("nonnumeric %s argument" % command)
            else:
                forlines = 1
            for i in range(min(forlines, len(self.source.lines))):
                self.source.lines[i] = r"\fU" + self.source.lines[i] + r"\fP"
        elif command == "tr":
            self.nonportableFeatures.append("tr")
            args[0] = self.source.expandEntities(args[0])
            while True:
                frompart = getXmlChar(args[0])
                args[0] = args[0][len(frompart):]
                topart = getXmlChar(args[0])
                args[0] = args[0][len(topart):]
                if not frompart:
                    break
                if frompart and not topart:
                    topart = " "
                # Each interpreter may have its own translation of the to part.
                for interpreter in self.source.interpreters:
                    for prefix in interpreter.translations:
                        for (special, translation) in interpreter.translations[prefix]:
                            if topart == special:
                                topart = translation
                if generalVerbosity in self.source.verbose:
                    self.source.notify("tr: %s -> %s" % (frompart, topart))
                self.source.outsubst.append((frompart, topart))
        elif command == "tm":
            stderr.write(" ".join(args) + "\n")
        elif command == "mso" and args[0] in msoDispatch:
            self.source.activate(msoDispatch[args[0]])
        elif command in ("so", "mso"):
            # Should we report mso as a groff feature?  Unclear...
            # non-groff implementations are supposed to ignore these.
            ifile = tokens[1]
            path = ""
            if command == "so":
                searchpath = self.source.includepath
            elif command == "mso":
                searchpath = glob.glob("/usr/share/groff/*/tmac")
            # First, search by straight filename
            for idir in searchpath:
                maybe = os.path.join(idir, ifile)
                if os.access(maybe, os.R_OK):
                    path = maybe
                    break
            # Next, on an mso, by macro-set name
            if not path and command == "mso":
                for idir in searchpath:
                    maybe = os.path.join(idir, ifile + ".tmac")
                    if os.access(maybe, os.R_OK):
                        path = maybe
                        break
            # Found the file.  If it's all comments and commands, include it
            if path:
                try:
                    text = self.preprocess(open(path).read())
                    lines = list(map(string.rstrip, text.split("\n")))
                    if [x for x in lines if x and not (isComment(x) or isCommand(x))]:
                        self.source.warning(ifile + " contains text -- generating entity reference.")
                        path = None
                    else:
                        if generalVerbosity in self.verbose:
                            self.source.notify("including" + path)
                        lines = ["<!-- *** start include from %s *** -->" % path] \
                                + lines \
                                + ["<!-- *** end include from %s *** -->" % path]
                        self.source.lines = lines + self.source.lines
                except (IOError, OSError):
                    self.source.warning(ifile + " not found -- generating entity reference.")
                    path = None
            if not path:
                if self.source.docbook5:
                    # FIXME: This alone is probably not sufficient.
                    self.source.emit('<xi:include href="%s"/>' % ifile)
                else:
                    entity = tokens[1].replace("/", "_")
                    while entity[0] == "_":
                        entity = entity[1:]
                    self.source.inclusions.append((entity, ifile))
                    self.source.emit("&" + entity + ";")
        # String and macro interpretation
        elif command == "ds":
            # Interpreters get the raw command line as an argument because
            # this code needs to look at it.
            ct = line.find('\\"')
            if ct != -1:
                line = line[:ct]
            i = line.find("ds")+2
            while line[i] in (" ", "\t"):
                i += 1
            stringname = ""
            while line[i] not in (" ", "\t"):
                stringname += line[i]
                i += 1
                if i >= len(line):
                    break
            value = ""
            if i < len(line):
                while line[i] in (" ", "\t"):
                    i += 1
                    if i >= len(line):
                        break
                if len(line) > i and line[i] == '"':
                    i += 1
            value = line[i:]
            value = value.replace(r"\'", "&apos;")
            value = value.replace("'", "&apos;")
            if self.source.inPreamble and self.entitiesFromStrings:
                self.source.localentities.append((stringname, value))
                self.strings[stringname] = "&" + stringname + ";"
            else:
                self.strings[stringname] = value
        elif command == "as":
            if len(tokens) == 3:
                if self.macronames:
                    self.strings[tokens[1]] += tokens[2]
                else:
                    self.strings[tokens[1]] += tokens[2]
        elif command == "rm":
            if tokens[1] in self.strings:
                del self.strings[tokens[1]]
            if tokens[1] in self.macros:
                del self.macros[tokens[1]]
        elif command == "rn":
            oldname = tokens[1]
            newname = tokens[2]
            suppressed = False
            for interpreter in self.source.interpreters:
                if oldname in interpreter.immutableSet:
                    suppressed = True
                    break
            if suppressed:
                # Warning rather than error because redefining an imutable
                # is invariably a presentation hack.
                self.source.warning("attempt to rename immutable macro %s" % oldname)
            else:
                if oldname in self.strings:
                    self.strings[newname] = self.strings[oldname]
                    del self.strings[oldname]
                if oldname in self.macros:
                    self.macros[newname] = self.macros[oldname]
                    del self.macros[oldname]
        elif command == "em":
            self.nonportableFeatures.append("em")
            if len(tokens) == 1:
                self.macroend = ".."
            else:
                self.macroend = tokens[1]
        elif command in ("de", "de1", "am"):
            if macroVerbosity in self.verbose:
                self.source.notify("macro definition begins")
            name = tokens[1]
            if len(name) > 2:
                self.longnames.append(name)
            if len(tokens) >= 3:
                endon = newname
            else:
                endon = self.macroend
            if command==TroffInterpreter.ctrl+"de" or not name in self.macros:
                self.macros[name] = []
            isused = [x for x in self.source.lines if type(x) == type("") and x[0:len(name)+1]==TroffInterpreter.ctrl+name]
            suppressed = False
            for interpreter in self.source.interpreters:
                if name in interpreter.immutableSet:
                    suppressed = True
                    break
            # We don't want macro listings showing up in the Synopsis section.
            # They play hell with the Synopsis parser...
            listing = isused and self.source.bodySection() and not suppressed and not self.source.quiet
            if listing:
                self.source.emit("<!-- Macro definition:")
                self.source.emit("%s %s" % (command, name))
            while self.source.lines:
                line = self.source.popline()
                if line.replace(" ", "") == endon:
                    break
                # Filter out commands we're going to ignore anyway
                linetoks = lineparse(line)
                if linetoks:
                    for interpreter in self.source.interpreters:
                        command = linetoks[0][1:]
                        if command in interpreter.ignoreSet:
                            line += '\t.\\" IGNORED'
                        elif command in interpreter.complainSet:
                            line += '\t.\\" IGNORED'
                            if not suppressed:
                                self.source.warning("untranslatable %s in %s definition" % (command, name))
                if listing:
                    self.source.emit(line)
                # Simulate troff's first round of \ interpretation (at
                # read time).  We simulate the second one (at
                # evaluation time) by looking for macro names *with*
                # the preceding backslash and processing \ just before
                # output.  This isn't quite right, but we're unlikely
                # to run into the edge cases where it breaks.
                line = line.replace("\\\\", "\\")
                self.macros[name].append(line)
            if listing:
                self.source.emit("-->", trans=0)
            if suppressed:
                del self.macros[name]
                self.source.emit(makeComment("%s listing suppressed (immutable)"%name))
            elif not isused:
                self.source.emit(makeComment("%s listing suppressed (not used)"%name))
            # OK, now perform macro reduction.  Recognize macros that are
            # presentation-level hacks around various standard constructs
            # that we want to be able to recognize and elide.
            for interpreter in self.source.interpreters:
                if hasattr(interpreter, "reductions"):
                    list(map(lambda x: self.conditionallyReplace(x[0], x[1]), list(interpreter.reductions.items())))
        # Implementation of numeric registers
        elif command == "nr":
            reg = args[0]
            if len(args) == 1:	# Ignore brain damage found on some pages
                if self.source.portability:
                    self.source.warning("bogus .nr %s call" % reg)
                return True
            val = args[1]
            if val[0] in "-+":
                if reg in self.macros:
                    baseval = self.macros[reg]
                else:
                    baseval = '0'
                val = str(eval(baseval+val))
            if macroVerbosity in self.verbose:
                self.source.warning("register %s = %s" % (reg, val))
            self.registers[reg] = val
        elif command == "rr":
            reg = args[0]
            if reg in self.registers:
                del self.registers[reg]
        elif command == "rnn":		# Groff extension
            self.groffFeatures.append("rnn")
            reg = args[0]
            new = args[1]
            if reg and new in self.registers:
                val = self.registers[reg]
                del self.registers[reg]
                self.registers[new] = val
        # OK, now process conditionals
        elif command in ("ie", "if"):
            if command == "if" and not args:
                self.source.error("'.if' without arguments is probably a typo for '.fi.'")
                self.source.pushline(".fi")
                return True
            if len(tokens) == 1:
                # Cope with a transposition typo...see vmstat(8) for example.
                if command == "if" and self.nf:
                    self.source.pushline(TroffInterpreter.ctrl + "fi")
                else:
                    self.source.error("malformed conditional %s" % command)
                return True
            # Evaluate the guard
            guardval = self.evalExpr(tokens[1])
            guardval = len(guardval) and guardval != '0'
            if macroVerbosity in self.verbose:
                self.source.notify("if condition stack push %s from: %s" % (guardval, repr(tokens)))
            self.ifstack.append(guardval)
            if command == "ie":
                if macroVerbosity in self.verbose:
                    self.source.notify("else condition stack %s push from: %s" % (guardval, repr(tokens)))
                self.ifstack.append(guardval)
            # If it's a one-liner and condition true, push back remaining text,
            # *unless* the first token past the guard is an .if command.  The
            # latter test deals with a nasty piece of boilerplate created
            # by Perl documentation tools that looks like this:
            #
            # .if \n(.H>23 .if \n(.V>19 \
            #
            # Evidently this is somebody's way of getting "and" into
            # conditionals.  Ugh...
            if guardval:
                if len(tokens) > 2 and not tokens[2].startswith(r"\{") and tokens[2] != TroffInterpreter.ctrl + "if":
                    if macroVerbosity in self.verbose:
                        self.source.notify("if or ie does one-line pushback")
                    self.source.pushline(TroffInterpreter.ctrl + r"\}")
                    if tokens[2].startswith(r"\{"):
                        tokens[2] = tokens[2][2:]
                    if macroVerbosity in self.verbose:
                        self.source.notify("pushing back: " + repr(tokens[2:]))
                    self.source.pushline(" ".join(tokens[2:]))
            else:
                # Kluge -- we don't want to trip on .ig terminators
                for i in range(1, len(args)):
                    if args[i] == '.ig' and len(args) > i+1:
                        self.source.ignore(args[i+1])
            # There may be a hanging { on the next line; if so, nuke it
            if self.source.peekline() in ("\\{", "\\{\\"):
                self.source.popline()
            # If condition is false we need to do a skip now
            if not guardval:
                self.skiptoend(tokens)
        elif command == "el":
            if not self.ifstack:
                # Urggh.  The way this happens is that when somebody who
                # should know better (such as Larry Wall) writes something
                # like
                #
                # .if n .Sh """Considerations"""
		# .el .Sh "``Considerations''"
                #
                # in the a2p man page, forgetting that this needs an .ie
                # rather than .if in order for the stack operations to
                # balance.  Let's not pop the stack and die.
                if generalVerbosity in self.verbose:
                    self.source.warning("unbalanced condition-stack operation")
                condition = True	# Works out right if the guard was true.
            else:
                condition = self.ifstack[-1]
            if macroVerbosity in self.verbose:
                self.source.notify(".el is %s" % condition)
            # If it's a one-liner and condition false, push back remaining text
            oneliner = len(tokens) > 1 and tokens[1][:2] != r"\{"
            if not condition and oneliner:
                self.source.pushline(TroffInterpreter.ctrl + r"\}")
                self.source.pushline(" ".join(tokens[1:]))
            # If condition is true we need to do a skip now
            if condition and not oneliner:
                self.skiptoend(tokens)
            if macroVerbosity in self.verbose:
                self.source.notify("stack state after .el: %s" % self.ifstack)
        elif command == r"\}" or command == r".\}":
            if self.ifstack:	# See above note on a2p
                if macroVerbosity in self.verbose:
                    self.source.notify("stack pop from: " + repr(tokens))
                self.ifstack.pop()
        elif command == "nop":	# groff extension
            self.groffFeatures.append("nop")
            if args:
                self.source.pushline(" ".join(args))
        elif command == "return":	# groff extension
            self.groffFeatures.append("return")
            self.source.macroReturn()
        elif command == "ig":
            if not args:
                args = ['.']
            if self.source.bodySection():
                self.source.endParagraph(label="ft")
            self.source.emit("<!-- " + " ".join(tokens))
            while self.source.lines:
                line = self.source.popline()
                if line.startswith(TroffInterpreter.ctrl + args[0]):
                    self.source.emit(".%s -->" % args[0], trans=0)
                    break
                line = line.replace(r"\^", "&ndash;&ndash;")
                line = line.replace(r"\-", "&mdash;")
                line = line.replace("-", "&mdash;")
                self.source.emit(line)
            if self.source.bodySection():
                self.source.needParagraph()
        # Debugging
        elif command == "pm":	# For debugging
            stderr.write("Strings: " + repr(self.strings) + "\n")
            stderr.write("Macros: " + repr(self.macros) + "\n")
            stderr.write("Registers: " + repr(self.registers) + "\n")
        elif command in self.macros:
            self.macroargs.append(stripquotes(tokens[1:]) + ([""] * 9))
            self.macronames.append(command)
            self.linenos.append(self.source.lineno)
            self.source.lineno = 0
            self.source.lines = self.macros[command] + [self.source.lineno] + self.source.lines
        # Extended groff macros
        elif command == "do":
            self.groffFeatures.append("do")	# Only ever used within macro packages.
        elif command == "cc":
            self.nonportableFeatures.append("cc")
            TroffInterpreter.ctrl = args[0]
        elif command == "c2":
            self.nonportableFeatures.append("c2")
            TroffInterpreter.ctrlBreak = args[0]
        elif command == "ab":
            if not args:
                args = ["User Abort"]
            raise LiftException(self.source, " ".join(args), 1)
        elif command == "rj":
            if not args:
                self.source.pushline(".br")
            else:
                self.source.warning(".rj with arguments seen.")
        elif command == "als":
            # Implements soft link rather than hard; hard would be difficult
            # because the target would be the old macro name.
            if args[1] in self.strings:
                self.strings[args[0]] = self.strings[args[1]]
            elif args[1] in self.macros:
                self.macros[args[0]] = self.macros[args[1]]
            else:
                self.source.error("attempt to alias undefined name %s"%args[1])
        elif command == "shift":
            self.groffFeatures.append("shift")
            if len(args):
                shiftby = int(args[0])
            else:
                shiftby = 1
            self.macroargs[-1] = self.macroargs[-1][shiftby:]
        elif command == "PSPIC":
            self.groffFeatures.append("PSPIC")
            ifile = args[0]
            self.source.pushline('<mediaobject>\n<imageobject><imagedata fileref="%s" format="EPS"/></imageobject>\n</mediaobject>' % ifile)
        elif command == "DOCLIFTER-HR":
            self.source.emit("<!-- horizontal rule -->")
        # We're done
        else:
            return False
        # Was there a trailing close bracket?  Then push it back.
        if len(tokens) > 1 and tokens[-1] == r"\}":
            if macroVerbosity in self.verbose:
                self.source.notify("pushing back a trailing bracket")
            self.source.pushline(TroffInterpreter.ctrl + r"\}")
        return True
    def conditionallyReplace(self, wrapper, standard):
        "Replace a wrapper with a standard macro if the wrapper contains it."
        if wrapper in self.macros and [x for x in self.macros[wrapper] if x.find(standard) > -1]:
            if not self.source.quiet:
                self.source.emit(makeComment("%s reduced to %s" % (wrapper, standard)))
            m = reCompile("^." + wrapper)
            self.source.lines = [m.sub(TroffInterpreter.ctrl+standard, x) for x in self.source.lines]
    def xmlifyLine(self, line):
        "XMLify a line of text, replacing magic characters with escapes."
        for (pattern, substitute) in TroffInterpreter.xmlifyPatterns:
            line = pattern.sub(substitute, line)
        return line
    def preprocess(self, text):
        if r'\*[' in text:
            self.groffFeatures.append(r"\*[")
        # Fixes an error found in OpenLDAP pages that night be generic.
        # This substitution enables a later stage to detect formations
        # that should turn into literallayout tag pairs.
        text = text.replace("\n.ft tt\n", "\n.ft CW\n")
        # The X.org pages use \N'34' to generate a double quote that
        # is stable everywhere.  We can't translate \N a priori in general
        # because it indexes into fonts that might have variable glyphs
        # at particular positions, but this one seems pretty safe.
        text = text.replace(r"\N'34'", '"')
        # Turn trailing \}, such as in rnews.1, into something we can process.
        # This is meatball surgery which might introduce an unwanted \n if
        # we happen to be in a literal-layout context.
        text = text.replace("\\}\n", "\n\\}\n")
        # We may need to pre-filter with eqn and pic.
        if "\n.EQ" in text:
            fp = tempfile.NamedTemporaryFile(prefix="doclifter.py")
            fp.write(text)
            fp.flush()
            (status, mathml) = getstatusoutput("eqn -TMathML <" + fp.name)
            fp.close()
            if status == 0 and "<math" in mathml and not "<merror" in mathml:
                self.source.eqnProcessed = True
                # Reduce trivial equations
                mathml = reCompile(r"<math><m[ion]>(\w*)</m[ion]></math>").sub(r'\\fI\1\\fP', mathml)
                # Now make sure there is a newline before trailing .ENs
                mathml = mathml.replace("</math>.EN", "</math>\n.EN")
                # FIXME: this optimization should be done in eqn, really
                mathml = mathml.replace("</mi><mi>","").replace("</mn><mn>","")
                # FIXME: maybe there's some way for eqn -TMathML to do these?
                mathml = reCompile(r"\\f[BIRP0-9]").sub("", mathml)
                # Mark MathML markup so we can put it in in the right namespace
                # before validation.  We can't put the "mml:" prefix in here,
                # : in inline-equation markup has a bad interaction with the
                # common use of : as a TBL delimiter.
                text = mathml.replace("<m", "<MaGiC%CoOkIe").replace("</m", "</MaGiC%CoOkIe")
                # Lose empty pair where delimiter declarations used to be.
                # This will mess with error-line numbers.
                text = text.replace(".EQ\n.EN\n", "")
        # db2man generates ISO-8859-n non-break spaces
        text = text.replace(chr(0xa0), r'\~')
        text = re.sub(r"\n\.([A-Z]+)\\~", r"\n.\1 ", text)
        # Fix some line-by-line errors and .
        expanded=[]
        enclosed = None
        for line in text.split("\n"):
            # Fix a common error -- beginning a line with a string quote
            # that isn't supposed to be a non-breaking request (example at
            # eject.1).
            if line and line[0]=="'" and not isComment(line) and len(line)>3:
                if line[1] not in string.letters or line[2] not in string.letters:
                    line = r"\&" + line
            # Don't allow ellipses to be mistaken for
            # commands (TCLEvalTokens.3).
            ellipsis = reCompile(r"^(\s+)(\.\.\..*)")
            seen = ellipsis.match(line)
            if seen:
                line = seen.group(1) + r"\&" + seen.group(2)
            # Compute our enclosure status
            if isCommand(line):
                if line[1:].startswith("EQ") and self.source.eqnProcessed:
                    enclosed = "EQ"
                elif line[1:].startswith("PS"):
                    enclosed = "PS"
                elif line[1:].startswith("EN") or line[1:].startswith("PE"):
                    enclosed = None
            # XMLify everything outside enclosures, except for inline
            # balanced MathML expressions in the mml namespace.
            if not enclosed:
                if "<MaGiC%CoOkIeath>" not in line or "</MaGiC%CoOkIeath>"not in line:
                    line = self.xmlifyLine(line)
                else:
                    before = line
                    filtered = ""
                    while True:
                        s = before.find("<MaGiC%CoOkIeath")
                        if s == -1:
                            break
                        filtered += self.xmlifyLine(before[:s])
                        filtered += "<inlineequation>"
                        before = before[s:]
                        t = before.find("</MaGiC%CoOkIeath>") + 18
                        if t == -1:
                            self.source.error("unbalanced MathML inline")
                            break
                        filtered += before[:t]
                        filtered += "</inlineequation>"
                        before = before[t:]
                    line = filtered + before
            expanded.append(line)
        return "\n".join(expanded)
    def postprocess(self, text):
        # We turned ; into a fake XML entity early on, in order to make
        # tokenization of synopses easier.  Turn it back.
        text = text.replace("&semi;", ";")
        # Convert vertical motions to superscript/subscript operations.
        # Protecct double backslashes first.
        text = text.replace(r"\\", r"@\\@")
        upmotion   = reCompile(r"\\v'\-\.[0-9]+[mnv]'|\\u(\.[0-9]+[mnv])?")
        downmotion = reCompile(r"\\v'\+?\.[0-9]+[mnv]'|\\d(\.[0-9]+[mnv])?")
        direction = None
        while True:
            upward = upmotion.search(text)
            downward = downmotion.search(text)
            if not (upward or downward):
                break
            if upward and downward:
                if upward.start() < downward.start():
                    downward = None
                else:
                    upward = None
            if direction is None:
                if upward:
                    text = text[:upward.start()] \
                           + r"<superscript>" \
                           + text[upward.end():]
                    direction = 'up'
                    if supersubVerbosity in self.verbose:
                        self.source.notify("Starting from None, I see upward %s at %d" % (upward.string[upward.start(0):upward.end(0)], upward.start(0)))
                elif downward:
                    text = text[:downward.start()] \
                           + r"<subscript>" \
                           + text[downward.end():]
                    direction = 'down'
                    if supersubVerbosity in self.verbose:
                        self.source.notify("Starting from None, I see downward %s at %d" % (downward.string[downward.start(0):downward.end(0)], downward.start(0)))
                else:
                    self.source.error("error in vertical-motion match")
            elif direction == 'up':
                if upward:
                    self.source.error("two upward motions in a row")
                    raise SystemExit
                elif downward:
                    text = text[:downward.start()] \
                           + r"</superscript>" \
                           + text[downward.end():]
                    direction = None
                    if supersubVerbosity in self.verbose:
                        self.source.notify("Starting from up, I see downward %s at %d" % (downward.string[downward.start(0):downward.end(0)], downward.start(0)))
                else:
                    self.source.error("error in vertical-motion match (up)")
            elif direction == 'down':
                if upward:
                    text = text[:upward.start()] \
                           + r"</subscript>" \
                           + text[upward.end():]
                    direction = None
                    if supersubVerbosity in self.verbose:
                        self.source.notify("Starting from down, I see upward %s at %d" % (upward.string[upward.start(0):upward.end(0)], upward.start(0)))
                elif downward:
                    self.source.error("two downward motions in a row")
                    raise SystemExit
                else:
                    self.source.error("error in vertical-motion match (down)")
        text = text.replace(r"@\\@", r"\\")
        # These get generated when ad-hoc tables are wrapped with .nf/.fi;
        # the table-compilation code tried to close the display begun by
        # the .nf.
        text = re.sub("<literallayout remap='.nf'>[ \t\n]*</literallayout>", "", text)
        # Our highlight tracking logic sometimes generates emphasis pairs with
        # nothing in scope.  Remove these.
        text = re.sub("<emphasis remap='[^']+'>[ \t\n]*</emphasis>", "", text)
        # Ugh. Another bug is that we sometimes generate too many font closes
        # in table entries.  This fixes the problem in a klugey way.
        text = re.sub(r"(\\fR)+</para></entry>", "</para></entry>", text)
        text = re.sub(r"(\\fR)+</entry>", "</entry>", text)
        # Now some pattern lifting to be applied after all macro sets.
        # This transforms literallayouts with program text inside them
        # into programlistings.
        keywordLifter = \
            r"(<(?:literallayout|screen)(?: remap='([^']*)')?>(?:\n*<emphasis remap='[A-Z]*'>)?)" \
            r"([^<]*(%s)[^<]*)" \
            r"((</emphasis>\n?)?</(?:literallayout|screen)>)"
        # Continue by recognizing source-code listings and screenshots
        # of command examples.
        literalLifts = (
            (r"char|bool|int|float|struct|union|typedef|#define|#undef",	"programlisting"),	# C
            (r"@_",			"programlisting"),	# Perl
            (r"\ndef|elif|try|except",	"programlisting"),	# Python
            (r"mov|jmp",			"programlisting"),	# Assembler
            (r"\nbash\$|\n\$",		"screen")
            )
        for (keywords, ltype) in literalLifts:
            listing = reCompile(keywordLifter % keywords)
            ender = ltype.split()[0]
            text = listing.sub(r"<%s remap='\2'>\3</%s>" % (ltype,ender), text)
        # Here is another hack to lift filenames and similar things.
        # Also, handle groff color extension.  Alas, no tag-balance checking.
        colorLifts = [(reCompile(x[0]), x[1]) for x in (
            ("\\\\m\[\]",		r"</phrase>"),
            ("\\\\m\[([a-z]+)\]",	r"<phrase remap='color:\1'>"),
            )]
        for (regexp, inline) in TroffInterpreter.prefixLifts + colorLifts:
            text = regexp.sub(inline, text)
        # And we may need to emit some compatibility warnings
        if self.source.portability:
            if self.nonportableFeatures:
                self.nonportableFeatures = list(set(self.nonportableFeatures))
                self.source.filewarn("portability warning: nonportable requests '%s' seen.\n" % ", ".join(self.nonportableFeatures))
            if self.source.portability >= 2:
                if self.longnames:
                    self.source.filewarn("portability warning: groff-style long macro names '%s' seen." % ", ".join(self.longnames))
                if self.groffFeatures:
                    self.groffFeatures = list(set(self.groffFeatures))
                    self.source.filewarn(
                        "portability warning: groff extension%s '%s'." % \
                        (("", "s")[len(self.groffFeatures) > 0],
                        ", ".join(self.groffFeatures)))
        return text

#
# Some formatting functions are common across more than one macro set.
#

def skipIgnorables(source):
    "Skip blank lines and ignorable commands."
    while source.lines:
        line = source.popline()
        if line == TroffInterpreter.ctrl + "end":
            source.pushline(TroffInterpreter.ctrl + "end")
            break
        elif line == None:
            break
        elif line in ("", TroffInterpreter.ctrl, TroffInterpreter.ctrlNobreak):		# Skip blank or null lines
            continue
        elif source.paragraphBreak(line):	# Skip ordinary paragraphs
            continue
        else:
            if not isCommand(line):		# Non-blank text line
                source.pushline(line)
                break
            else:
                tokens = lineparse(line)
                if source.ignorable(tokens[0]):
                    continue
                source.pushline(" ".join(tokens))
                break

def gatherLines(source):
    "Gather text lines until we hit a command."
    res = []
    while source.lines:
        line = source.popline()
        if isCommand(line) and line[1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            source.pushline(line)
            break
        if not (isCommand(line) and source.ignorable(line)):
            res.append(line)
    return res

def gatherItem(source, tag=None):
    "Gather item, emitting opening and closing listitem tags."
    if sectionVerbosity in source.verbose:
        source.notify("gatherItem(%s)\n" % tag)
    if tag:
        source.emit("<" + tag + ">")
    source.needParagraph()
    savesect = []
    outlines = []
    # Discard commands that generate nothing
    skipIgnorables(source)
    # Now gather the list item proper
    source.listitem = True
    if sectionVerbosity in source.verbose:
        stderr.write("gathering list item\n")
    while source.lines:
        line = source.popline()
        # Maybe we're looking at a commented-out entry
        if line == TroffInterpreter.ctrl + "ig":
            savesect.append(TroffInterpreter.ctrl + "ig")
            while True:
                line = source.popline()
                savesect.append(line)
                if line == TroffInterpreter.ctrl + ".":
                    break
            continue
        elif line is None:
            break
        elif line.startswith(TroffInterpreter.ctrl + "blank"):
            # The point is not to end the list on these.
            savesect.append(TroffInterpreter.ctrl + "blank")
        elif source.sectionBreak(line):
            # Push back any blank lines before the section break.
            # This avoids generating some spurious paragraph()
            # calls that can litter the output with extra close tags.
            while savesect and blankline.match(savesect[-1]):
                source.pushline(savesect[-1])
                savesect.pop()
            source.pushline(line)
            break
        elif source.paragraphBreak(line):
            source.pushline(line)
            break
        else:
            savesect.append(line)
    if interpreterVerbosity in source.verbose:
        source.notify("interpreting savesect: " + repr(savesect))
    source.interpretBlock(savesect, outlines)
    if interpreterVerbosity in source.verbose:
        source.notify("interpretation of savesect complete\n")
    if [x for x in outlines if not not x and x[:4] != "<!--"]:
        list(map(source.emit, outlines))
    else:
        source.warning("empty list item, see FIXME")
        source.emit("<para>&nbsp;</para> <!-- FIXME: empty list item -->")
    source.listitem = False
    source.endParagraph(label="gatherItem")
    if tag:
        source.emit(r"</" + tag + ">")
    if sectionVerbosity in source.verbose:
        source.notify("gatherItem(%s)\n" % tag)

def gatherSimplelist(cmd, source):
    "Gather listitems, terminate when you see a dot command."
    while len(source.lines):
        line = source.popline()
        if not line.startswith(cmd):
            source.pushline(line)
            break
        else:
            gatherItem(source, "listitem")

def gatherItemizedlist(cmd, source, bullet):
    "Translate to bullet-list markup -- used in both man and me macros."
    source.emit("<itemizedlist mark='%s'>" % bullet)
    gatherSimplelist(cmd, source)
    source.emit("</itemizedlist>\n")

def gatherOrderedlist(cmd, source, bullet):
    "Translate to numbered-list markup."
    source.emit("<orderedlist mark='%s'>" % bullet)
    gatherSimplelist(cmd, source)
    source.emit("</orderedlist>\n")

def parseNameSection(nameline):
    "Parse a NAME -- description line."
    nameline = deemphasize(nameline)
    nameline = nameline.replace("\t", r' ')
    # Unicode en dash - E2 80 93 or 342 200 223.
    nameline = nameline.replace("\342\200\223", r'-')
    nameline = nameline.replace(r" \[en] ", r' \- ')
    nameline = nameline.replace(r" \-\- ", r' \- ')
    nameline = nameline.replace(r" \&amp;\- ", r' \- ')
    nameline = nameline.replace(" - ", r' \- ')
    nameline = nameline.replace(r" \(hy ", r' \- ')
    # Apparent pod2man breakage...
    nameline = nameline.replace(r"&zerosp;-", r"\-")
    if nameline.find(r" \- ") == -1:
        nameline = nameline.replace(r" \(em ", r' \- ')
        nameline = nameline.replace(r" &mdash; ", r' \- ')
        # SDL pages make this kluge necessary
        nameline = nameline.replace("--", r' \- ')
        nameline = nameline.replace(r"\-", r" \- ")
    return nameline.split(r' \- ')

#
# Display-parsing machinery.
#

class ParseNode:
    def __init__(self, ntype, token=None, choice="plain", repeat=0):
        self.type = ntype
        self.token = token
        self.choice = choice
        self.righthand = None
        self.repeat = repeat
        self.glue = None
        self.children = []
    def __repr__(self):
        if self.type == "option":
            if self.righthand:
                return "%s=<replaceable>%s</replaceable>" % (self.token, self.righthand)
            else:
                return self.token + self.glue
        elif self.type == "replaceable":
            return "<replaceable>%s</replaceable>" % (self.token)
        elif self.type in ("arg", "group"):
            pre = "<%s"  % self.type
            if self.choice:
                pre += " choice='%s'" % self.choice
            if self.repeat:
                pre += " rep='repeat'"
            pre += ">"
            post = "</%s>" % self.type
            res = ""
            for child in self.children:
                res += repr(child)
            return pre + res + post
        elif self.type == "@GLUE@":
            return "@GLUE@"
        elif self.type == "redirect":
            return "<arg>" + self.token + "</arg>"
        elif self.type == "sbr":
            return "<sbr/>"
        elif self.type == "\n":
            return ""
        else:
            res = ""
            for child in self.children:
                res += repr(child)
            return ("<%s>" % self.type) + res + ("</%s>" % self.type)

def isFileOrCommandName(tok):
    # Yes, some legitimate commands begin with digits;
    # 411toppm is a good example.
    if not tok:
        return None
    # Deals with some section 3 pages
    if tok in ('link', 'with'):
        return False
    else:
        return tok[0].islower() or tok[0] == "/" or (tok[0] in string.digits and tok[-1] in string.letters)

def detroff(ln):
    # Remove markup generated by the Mdoc document macros.  It may seem
    # a bit screwy to generate this stuff just to throw it away, but
    # we actually want these expansions everywhere outside of a synopsis.
    ln = ln.replace("<replaceable>", "").replace("</replaceable>", "")
    ln = ln.replace("<literal>", "").replace("</literal>", "")
    ln = ln.replace("<command>", "").replace("</command>", "")
    ln = ln.replace("<command remap='Ic'>", "")
    ln = ln.replace("<command remap='Nm'>", "")
    ln = re.sub(r"<option>\s*", "-", ln).replace("</option>", "")
    # Deal with pod2man droppings.
    if ln.startswith(r"&zerosp; "):
        ln = ln[9:]
    # Some man pages (like afmtodit.1) run options together with their
    # following arguments together on the man page, with the boundary
    # marked by a highlight change.  Replace these with a glue token so
    # there will be a parseable boundary there.
    ln=DisplayParser.oldStyleOptionGlue.sub(r"\1 @GLUE@ \2",ln)
    # We have now extracted all the semantic information we can from
    # highlight boundaries.
    ln = deemphasize(ln)
    # Throw out the entity results of translating some confusing troff
    # characters.  Yes, some man pages (notably several associated with
    # nmh) throw soft hyphens in there for no obvious reason.
    ln = ln.replace("&thinsp;","").replace("&hairsp;","").replace("&zerosp;","")
    ln = ln.replace("&nbsp;"," ").replace("&shy;", "").replace("\\", "")
    ln = ln.replace(r"-^-", "--").replace("&mdash;", "--")
    return ln

class LineTokenizer:
    "Make a collection of lines available either as lines or tokens."
    def __init__(self, lines, verbose=False):
        self.lines = lines
        self.verbose = verbose
        self.pretokenizer = None
        self.tokenIndex = 0
        self.lookahead = []
        self.lookbehind = []
        self.savedlines = []
        self.mark = 0
        self.tokenize()
    def popline(self):
        "Grab the next line and make it the token buffer."
        if not self.lines:
            if self.verbose:
                stdout.write("popline: returns None\n")
            return None
        else:
            if self.verbose:
                stdout.write("popline: starts with: %s\n" % self)
            res = self.lines[0]
            self.savedlines.append(self.lines.pop(0))
            self.lookahead = []
            if self.lines:
                self.tokenize(self.pretokenizer)
            if self.verbose:
                stdout.write("popline: returns: %s %s\n" % (repr(res), self))
            return res
    def pushline(self, line):
        "Replace the token buffer with the current line."
        self.lines = [line] + self.lines
        self.tokenize(self.pretokenizer)
        if self.verbose:
            stdout.write("pushline: leaves: %s\n" % self)
    def peekline(self):
        "Return the token buffer"
        if not self.lines:
            return None
        else:
            return self.lines[0]
    def tokenize(self, newPretokenizer=None):
        "Split a line on whitespace, but preserve \n as a token."
        if self.verbose:
            stdout.write("tokenize: %s\n" % (newPretokenizer,))
        self.pretokenizer = newPretokenizer
        if self.lines:
            if self.pretokenizer:
                line = self.pretokenizer(self.lines[0])
            else:
                line = self.lines[0]
            self.lookahead = line.strip().split()
            if line.endswith('\n'):
                self.lookahead.append('\n')
            if self.verbose:
                stdout.write("tokenize: split %s to get %s\n"%(repr(line),self))
    def tokenPop(self, count=1):
        "Get a token."
        res = self.tokenPeek(count)
        self.lookbehind += self.lookahead[:count]
        self.lookahead = self.lookahead[count:]
        self.tokenIndex += count
        if self.verbose:
            stdout.write("tokenPop: returns %s, from %s\n" % (repr(res), self))
        return res
    def tokenPush(self, tok):
        "Put back a token."
        if self.verbose:
            stdout.write("tokenPush: %s, to %s\n" % (repr(tok), self))
        if not self.lines:
            self.lines = [tok]
        elif not self.lookahead:
            self.lines = [tok] + self.lines
        self.lookahead = [tok] + self.lookahead
        if self.verbose:
            stdout.write("tokenPush: ends with %s\n" % self)
    def tokenPeek(self, count=1):
        "Peek at the next token.  The count argument can only index into the next line."
        if not self.lookahead and not self.lines:
            return None
        if self.verbose:
            stdout.write("tokenPeek: I see " + repr(self) + '\n')
        while len(self.lookahead) == 0:
            if not self.lines:
                if self.verbose:
                    stdout.write("tokenPeek: I return None: "+repr(self)+'\n')
                return None
            self.popline()
        if self.verbose:
            stdout.write("tokenPeek: I return %s from %s\n" % (repr(self.lookahead[count-1]), self))
        return self.lookahead[count-1]

    def checkpoint(self):
        "Restart saving of lines from this point."
        self.savedlines = []
        if self.verbose:
            stdout.write("checkpoint: done\n")
    def unroll(self):
        "Restore all saved lines, used to undo parsing effects on error."
        self.lines = self.savedlines + self.lines
        self.savedlines = []
        self.tokenize(self.pretokenizer)
        if self.verbose:
            stdout.write("unroll: restores to %s\n" % (self))

    def __str__(self):
        "Display the state of the object."
        return "<lookahead=%s, lines=%s>" % (self.lookahead, pretty.pformat(self.lines[:5]))
    __repr__ = __str__

    def text(self):
        return "".join(self.lines)

class FunctionSynopsisParser:
    "Consume a function synopsis and return markup."
    # Candidate lines for FuncSynopsisInfo
    languageLines = (
        (reCompile(r"^\s*#\s*(define|undef|include|if\s|ifn?def|endif)"), "C"),
        (reCompile(r"^\s*extern.*;$"),		"C"),
        (reCompile(r"^\s*typedef.*;$"),	"C"),
        (reCompile(r"^\s*import\s"),		"Python"),
        (reCompile(r"^\s*use\s.*;"),		"Perl"),
        (reCompile(r"#\s*perl"),		"Perl"),
        # Allow lines that resemble variable settings
        # This isn't actually limited to C...
        (reCompile(r"[a-z_]+ = "),		"C"),
        )
    # This patterns identify lines that are probably code
    languageFragments = (
        # This is looking for the stuff that one finds around the left
        # paren of a C declaration.  This is something we're quite unlikely
        # to see in running text.
        (reCompile(r"[a-z][a-z][a-z]\([_a-zA-Z][_a-zA-Z0-9]+[, ]"), "C"),
        # Look for lines led with C declarations
        (reCompile(r"^\s*(int|char|long)\s"),	"C"),
        # Someday, use these
        #(reCompile(r"^\s*def\s"),	"Python"),
        #(reCompile(r"^\s*class\s"),	"Python"),
        )
    tokenPairs = (
        (reCompile(r"^\s*/\*"), reCompile(r"\*/$"),         "C","C comment"),
        # typedef/struct/union end only on ^} because they can have {} inside
        (reCompile(r"^\s*typedef.*{$"), reCompile(r"^}"),  "C","C typedef"),
        (reCompile(r"^\s*typedef.*enum.*{$"), reCompile(r"^}"),  "C","C typedef enum"),
        (reCompile(r"^\s*struct.*{$"), reCompile(r"^}"),   "C","C struct"),
        (reCompile(r"^\s*union.*{$"),  reCompile(r"^}"),   "C","C union"),
        # With enum we can be a bit more relaxed
        (reCompile(r"^\s*enum\b"),   reCompile(r"};?"),     "C","C enum"),
        (reCompile(r"^\s*extern\b"), reCompile(r"&semi;$"), "C","C extern"),
        )
    opensslStackLine = reCompile(r"STACK_OF[A-Z_]*\([A-Za-z, ]+\)(&semi;)?$")
    opensslLhashLine = reCompile(r"LHASH_OF\([A-Za-z, ]+\)(&semi;)?$")
    def __init__(self, iop, source):
        self.io = iop
        self.source = source
        self.output = ""
        self.language = None
        self.error = None
        self.seenAnsi = False
        # Shortcut:  assume | and ') (' and ] [ can never occur in a function
        # synopsis (middle two filters out some Perl code examples).
        # Make an exception for || as this never occurs in those but may mean
        # there is code for a disjunction of feature macros, as in logf(3).
        # Look for these and return immediately if we find them.
        if [x for x in self.io.lines if ("||" not in x and "|" in x) or "('" in x or "')" in x or "] [" in x]:
            if classifyVerbosity in self.source.verbose:
                self.source.notify("can't be a function synopsis, contains |  or '] ['")
            self.error = "<!-- contains |  or '] [' -->"
            return
        # Shortcut: to  be parseable C, headers must contain (.
        # Command synopses generally have neither.
        # (We used to test for ; but XML entity expansions messed that up.)
        if not self.io.lines[0].startswith("#include"):
            if not [x for x in self.io.lines if "(" in x]:
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("can't be a function synopsis, does not contain (")
                self.error = "<!-- does not contain ( -->"
                return
        # Otherwise time for a normal parse
        self.io.tokenize(self._Pretokenizer)
        try:
            try:
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("beginning function synopsis parse: " + repr(self.io))
                self.output = ""
                while self.io.lines:
                    info = self._ParseFunctionSynopsisInfo()
                    proto = self._ParseFunctionPrototype()
                    if info or proto:
                        self.output += info + proto
                    else:
                        break
                if self.output:
                    self.output = "<funcsynopsis>\n"+self.output+"</funcsynopsis>\n"
            finally:
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("ending function synopsis parse: " + self.output)
        except LiftException as e:
            self.error = "function synopsis parse failed "
            if self.io.tokenPeek() is None:
                self.error += "at end of synopsis: %s" % (e.message)
            else:
                self.error += "on `%s' (%d): %s" % \
                         (self.io.tokenPeek(), self.io.tokenIndex, e.message)
            if classifyVerbosity in self.source.verbose:
                self.source.notify(self.error)
            # Since we can detect function synopses reliably, check here
            # and make self.output nonempty so we'll error out and not try
            # doing a command parse.
            if list(filter(self.isSourcecode, self.io.lines)):
                self.output = "<!-- invalid function synopsis -->"
        self.io.tokenize()

    def isSourcecode(self, text):
        "Recognize that a line is source code."
        if blankline.search(text):
            return True
        for (pattern, dummy) in FunctionSynopsisParser.languageLines:
            if pattern.search(text):
                return True
        for (pattern, dummy) in FunctionSynopsisParser.languageFragments:
            if pattern.search(text):
                return True
        return False

    def _Pretokenizer(self, line):
        line = detroff(line)
        # OpenSSL pages have some weird type-macro generation stuff going on. 
        line = re.sub(r'STACK_OF([A-Z_]*)\(([A-Za-z_]*)\)', r"STACK_OF\1@GLUE1@\2@GLUE2@", line)
        line = re.sub(r'LHASH_OF([A-Z_]*)\(([A-Za-z_]*)\)', r"LHASH_OF\1@GLUE1@\2@GLUE2@", line)
        line = line.replace(")", " ) ").replace("(", " ( ")
        line = line.replace(",", " , ").replace("*", " * ")
        line = line.replace("[", " [ ").replace("]", " ] ")
        line = line.replace("&semi;", " &semi; ").replace("~", " ~ ")
        line = line.replace("@GLUE1@", "(").replace("@GLUE2@", ")")
        return line

    def _Detokenize(self, line):
        return line.replace("[ ]", "[]").replace("* ", "*") \
               .replace(" &semi; ", "&semi;").replace(" ~ ", "~")

    def _ParseParamdef(self, arg):
        "We've been handed a formal argument; parse it into a ParamDef."
        if not arg:	# Triggered by ,) which can be generated by mdoc
            return ""
        if len(arg) == 1:
            return "    <paramdef><parameter>"+arg[0]+"</parameter></paramdef>\n"
        # If there is a function prototype in the declaration, strip it.
        # No, this won't handle nested prototypes.
        def rindex(x, lst):
            last = len(lst) - 1
            for i in range(0, last+1):
                if lst[last - i] == x:
                    return last - i
            return -1
        last = len(arg) - 1
        if arg[-1] == ')':
            last = rindex("(", arg)
        # Now look for the rightmost token that resembles a name.
        # There's your parameter.
        paramInd = -1
        for i in range(last):
            if arg[last - i][0].isalpha():
                paramInd = last - i
                break
        if paramInd == -1:
            prolog = " ".join(arg)
            var = ""
            epilog = ""
        else:
            prolog = " ".join(arg[:paramInd])
            var = arg[paramInd]
            epilog = " ".join(arg[paramInd+1:])
        prolog = self._Detokenize(prolog)
        epilog = self._Detokenize(epilog)
        self.source.localhints.post(var, "varname role='parameter'")
        return "    <paramdef>" + prolog + " <parameter>" + var + "</parameter>" + epilog + "</paramdef>\n"

    def _ParseFunctionPrototype(self):
        "Parse a C or C++ function prototype."
        if classifyVerbosity in self.source.verbose:
            self.source.notify("beginning function prototype parse, language %s" % self.language)
        try:
            if classifyVerbosity in self.source.verbose:
                self.source.notify("parseFunctionPrototype() sees: " + repr(self.io))
            # Seek the name token.
            parendepth = 0
            name = None
            prolog = []
            hintDict = {}
            seentype = False
            self.io.checkpoint()
            # Munch the part before the formals
            while True:
                tok = self.io.tokenPop()
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("looking at %s" % repr(tok))
                tnext = self.io.tokenPeek()
                # The sequence \n( should be treated like (, so a function
                # prototype with a line break just after the name is detected.
                if tnext == '\n':
                    self.io.tokenPop()
                    second = self.io.tokenPeek()
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("newline special case sees %s" % repr(second))
                    if second != '(':
                        self.io.tokenPush('\n')
                    else:
                        tnext = second
                # We shouldn't run out of tokens here
                if tok is None:
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("C prototype parse failed while looking for (")
                    self.io.unroll()
                    return ""
                # Cope with obnoxious Tcl sidebar marks as well as newlines
                elif tok in ("\n", "|"):
                    continue
                # And with spurious breaks
                elif tok == "<sbr/>":
                    continue
                # Accumulate C keywords. STACK_OF is part of a kludge to pass
                # though a weird construction that the OpenSSL pages use.
                if tok in cDeclarators or tok.startswith('operator') or "STACK_OF" in tok:
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("Treating %s as declarator" % tok)
                elif not idRe.match(tok) and not tok in ("(", ")", "*", "&", "~"):
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("illegal token %s while looking for declaration specifiers" % tok)
                    self.io.unroll()
                    return ""
                # Assume that any identifier followed by a non-identifier ia
                # the function name, rather than some flukey typedef in the
                # declaration.  This will do the right thing with
                #	struct foo *bar(x, y)
                elif not name and idRe.match(tok):
                    if tnext and not idRe.match(tnext) and tnext != '\n':
                        name = tok
                        if classifyVerbosity in self.source.verbose:
                            self.source.notify("name is %s, non-identifier is %s" % (name, repr(tnext)))
                    elif seentype:
                        if classifyVerbosity in self.source.verbose:
                            self.source.notify("looks like text, not a function declaration: %s" % tok)
                        self.io.unroll()
                        return ""
                    else:		# Could be a typedef
                        if classifyVerbosity in self.source.verbose:
                            self.source.notify("treating %s as a type" % tok)
                        hintDict[tok] = "type"
                        seentype = True
                elif name and parendepth == 0 and tok == "(":
                    break
                elif tok == '(':
                    parendepth += 1
                elif tok == ')':
                    parendepth -= 1
                elif tok in ("struct", "union", "enum"):
                    hintDict[tok + " " + tnext] = "type"
                    prolog.append(tok)
                    tok = self.io.tokenPop()
                    tnext = self.io.tokenPeek()
                prolog.append(tok)
            # Kluge to deal with C++ declarators
            if self.io.lookahead[:2] == [")", "("]:
                self.io.tokenPop(2)
                prolog += " ()"
            if not name:
                if generalVerbosity in self.source.verbose:
                    self.source.notify("no name in apparent function declaration.")
                self.io.unroll()
                return ""
            if parseVerbosity in self.source.verbose:
                self.source.notify("Function name: " + name)
            prolog[prolog.index(name)] = "<function>" + name + "</function>"
            hintDict[name] = "function"
            prolog = self._Detokenize(" ".join(prolog))
            # Is this an old-style or a new-style declaration?
            firstformal = self.io.tokenPop()
            argcount = parendepth = 0
            formalArgs = ""
            newstyle = False
            if firstformal == ')':
                # No formals at all.  Treat as K&R style
                if parseVerbosity in self.source.verbose:
                    self.source.notify("no formals")
            else:
                if self.io.tokenPeek() in (")", ","):
                    # Just one token in the formal.  This case is ambiguous;
                    # could be a K&R-style declaration, or could be an ANSI
                    # declaration like
                    #	virtual void setToggleAction ( bool )
                    # where the single formal is a typedef rather than a name.
                    # This is why we track whether we've seen ANSI C constructions.
                    # We also want to catch the case of
                    #	int foo(void)
                    # here, that's what the cDeclarators check is about.
                    self.io.tokenPush(firstformal)
                    newstyle = self.seenAnsi or firstformal in cDeclarators or self.io.lines[0].strip().endswith("&semi;")
                else:
                    # More than one identifier in the formal
                    self.io.tokenPush(firstformal)
                    self.seenAnsi = newstyle = True
                if parseVerbosity in self.source.verbose:
                    if newstyle:
                        self.source.notify("ANSI-style declaration of %s"% name)
                    else:
                        self.source.notify("K&R-style declaration of %s" % name)
                # If it's an old-style declaration, count and skip the
                # formal names.  Save them in case there are no argument
                # declarations at all.
                if newstyle:
                    terminator = ','
                else:
                    terminator = '&semi;'
                    formalnames = [[]]
                    if self.io.tokenPeek() == ")":	# Excludes no-args case
                        self.io.tokenPop()
                    else:
                        while True:
                            tok = self.io.tokenPop()
                            if not tok:
                                # If we ran out of tokens without seeing a
                                # balancing ), this isn't a C prototype at all.
                                # Bail out.
                                if generalVerbosity in self.source.verbose:
                                    self.source.warning("no balancing )")
                                self.io.unroll()
                                return ""
                            if tok == '(':
                                parendepth += 1
                            if tok == ')':
                                parendepth -= 1
                            if tok == ",":
                                formalnames.append([])
                                argcount += 1
                                continue
                            elif tok == ")":
                                argcount += 1
                                if parendepth == -1:
                                    break
                            formalnames[-1].append(tok)
                    # We just ate the terminating paren on what looks like a
                    # K&R-style declaration.  Danger lurks here.
                    # Are we looking at an old-style declaration with *nothing*
                    # but formals? If so, head off any attempt to parse them,
                    # it will only come to grief.
                    noDeclarations = False
                    maybeSemi = self.io.tokenPop()
                    if maybeSemi == "&semi;":
                        noDeclarations = True
                    elif maybeSemi != "\n":
                        if classifyVerbosity in self.source.verbose:
                            self.source.warning("suspicious token %s after )" \
                                                  % maybeSemi)
                        self.io.tokenPush(maybeSemi)
                    else:
                        # A second newline here means there is whitespace where
                        # we're expecting the parameter declarations.  This
                        # happens a lot on the Tcl pages.  Give up.
                        maybeNewline = self.io.tokenPeek()
                        if maybeNewline in ("\n", "<sbr/>", None):
                            noDeclarations = True
                        else:
                            # We're probably looking at the first declarator.
                            self.io.tokenPush(maybeSemi)
                    # If there are no declarations, use the formal names we
                    # stashed away.  It's better than nothing.
                    if noDeclarations:
                        if parseVerbosity in self.source.verbose:
                            self.source.notify("no parameter declarations")
                        for param in formalnames:
                            formalArgs += "<paramdef><parameter>%s</parameter></paramdef>\n" % " ".join(param)
                        formalArgs = self._Detokenize(formalArgs)
                        argcount = 0
                # Go get the prototype formals.  If this is a new-style
                # declaration, terminate on seeing a top-level ).  If it's
                # old style, we've skipped past the formals and we want to
                # grab parameter definitions until we've counted the right
                # number of terminating semicolons.
                parendepth = 0
                while newstyle or argcount:
                    formal = []
                    while True:
                        tok = self.io.tokenPop()
                        if parseVerbosity in self.source.verbose:
                            self.source.notify("Token (%d): %s %s" % (parendepth, tok, self.io.lookahead))
                        if tok is None:
                            if parseVerbosity in self.source.verbose:
                                self.source.warning("unexpected end of token list")
                            self.io.unroll()
                            return ""
                        elif tok in ("\n", "<sbr/>"):
                            continue
                        elif tok == "(":
                            parendepth += 1
                        elif tok == ')':
                            if newstyle and parendepth == 0:
                                newstyle = False
                                argcount = 1	# Terminate outer loop,
                                break		# end of formal and prototype
                            else:
                                parendepth -= 1
                        elif tok == terminator:
                            if parendepth == 0:
                                break		# End of formal
                        formal.append(tok)
                    # Formal argument should be complete. Hand it off for analysis
                    if parseVerbosity in self.source.verbose:
                        self.source.notify("Formal: %s" % formal)
                    formalArgs += self._ParseParamdef(formal)
                    argcount -= 1
            # We've gatherered all the argument markup
            if formalArgs == "<paramdef><parameter>void</parameter></paramdef>":
                formalArgs = "  <void%/>"
            if formalArgs == "<paramdef><parameter>...</parameter></paramdef>":
                formalArgs =  "  <vaargs/>\n"
            if not formalArgs:
                if newstyle:
                    formalArgs = "<varargs/>"
                else:
                    formalArgs = "<void/>"
            # Consume optional semicolons following the close paren
            if self.io.tokenPeek() in ("&semi;", ";"):
                self.io.tokenPop()
                if parseVerbosity in self.source.verbose:
                    self.source.notify("ate trailing semi")
            if self.io.tokenPeek() not in (None, "\n", "<sbr/>"):
                if parseVerbosity in self.source.verbose:
                    self.source.warning("trailing junk '%s' after prototype" % self.io.tokenPeek())
                self.io.unroll()
                return ""
            else:
                # If we're at end of line, consume the line so the next
                # go-around of the function synopsis parser won't see it.
                while self.io.tokenPeek() == "\n":
                    self.io.tokenPop()
                    if parseVerbosity in self.source.verbose:
                        self.source.notify("ate trailing newline")
                # Now we can assemble the actual prolog...
                prolog = "<funcdef>" + prolog + "</funcdef>\n"
                # Now assemble and return it.
                if prolog or formalArgs:
                    output="<funcprototype>\n"+prolog+formalArgs+"</funcprototype>\n"
                # Since the parse succeeded, the semantic hints we gathered
                # are good
                #stdout.write("Hint dictionary from function synopsis is %s\n" % hintDict)
                for (hid, htype) in list(hintDict.items()):
                    self.source.localhints.post(hid, htype)
        finally:
            if classifyVerbosity in self.source.verbose:
                self.source.notify("ending function prototype parse")
        return output

    def _DetectPassthroughs(self, line=None):
        # Detect language-specific line pattern
        if line is None:
            line = self.io.peekline()
        for (pattern, lang) in FunctionSynopsisParser.languageLines:
            if pattern.search(line):
                return lang
        return None
    def _ParseFunctionSynopsisInfo(self):
        # Accept any number of lines as a FuncSynopsisInfo
        if classifyVerbosity in self.source.verbose:
            self.source.notify("beginning function synopsis info parse")
        synopsisinfo = ""
        while True:
            skipIgnorables(self.source)
            line = self.io.peekline()
            if classifyVerbosity in self.source.verbose:
                self.source.notify("candidate line: %s" % repr(line))
            if line is None:
                break
            line = detroff(line)
            # Pass through blank lines
            if blankline.match(line):
                synopsisinfo += line
                self.io.popline()
                continue
            # Pass through breaks
            if line.startswith("<sbr/>"):
                self.io.popline()
                synopsisinfo += "\n"
                continue
            # Pass through C compiler invocation lines.  Some libraries
            # insert these in command synopses.  If we don't do this explicitly
            # here, it will look like a command synopsis and cause an error
            # at a later parse stage.
            if line.startswith("cc") or line.startswith("gcc"):
                synopsisinfo += line
                self.io.popline()
                continue
            # Also pass through anything that looks like a Qt section header
            if line.strip() in qtHeaders:
                synopsisinfo += line
                self.io.popline()
                continue
            # Other things, like cpp directives, should pass through as well.
            # Test for single-line typedefs here so as not to have a bad
            # interaction with the token-pair code below.
            lang = self._DetectPassthroughs(line)
            if lang:
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("from %s language identified as %s\n"% (repr(line), lang))
                self.language = lang
                synopsisinfo += line
                self.io.popline()
                continue
            # Pass through funky OpenSSL macro prototypes
            if FunctionSynopsisParser.opensslStackLine.search(line):
                synopsisinfo += line
                self.io.popline()
                continue
            if FunctionSynopsisParser.opensslLhashLine.search(line):
                synopsisinfo += line
                self.io.popline()
                continue
            # On the other hand, seeing ( means we have run into what should be
            # a function synopsis.  Throw it back.
            if "(" in line:
                break
            # Pass through any line ending with semicolon.
            # This catches single-line C declarations that don't have an
            # obvious keyword up front.
            if line.endswith(";\n"):
                synopsisinfo += line
                self.io.popline()
                continue
            # This catches things like "DEPRECATED:" in the libpng pages
            # and "Deprecated:" in the OpenSSL pages
            if line.lower().endswith("deprecated:\n"):
                synopsisinfo += line
                self.io.popline()
                continue
            # Avoid spurious warnings on X509 pages
            if "aliases" in line.lower():
                synopsisinfo += line
                self.io.popline()
                continue
            # Pass through #endif.  Occurs in Pod2man pages with 
            # deprecated sections conditionalized out. 
            if not self.source.diversion[-1].strip() and line.startswith("#endif"):
                synopsisinfo += line
                self.io.popline()
                continue
            # Pass through line sequences bracketed by specified token pairs.
            # This is where we catch stuff like multiline struct declarations.
            for (start,end,lang,errmsg) in FunctionSynopsisParser.tokenPairs:
                if start.match(line):
                    if parseVerbosity in self.source.verbose:
                        self.source.notify("Declaration starts with %s, should end with %s" % (start.pattern, end.pattern))
                    while self.io.lines:
                        line = detroff(self.io.popline())
                        if parseVerbosity in self.source.verbose:
                            self.source.notify(repr(line))
                        synopsisinfo += line
                        # This is the magic that allows us to avoid elaborate
                        # tokenization rules.  Look for the terminator as the
                        # suffix of a token.
                        if end.search(line):
                            break
                    else:
                        raise LiftException(self.source, "missing end token for " + errmsg)
            else:
                # Nothing we recognize.  Stop, and don't pop the current line
                break
        if classifyVerbosity in self.source.verbose:
            self.source.notify("ending function synopsis info parse")
        if synopsisinfo:
            return "<funcsynopsisinfo>\n"+synopsisinfo+"</funcsynopsisinfo>\n"
        else:
            return ""

class CommandSynopsisSequenceParser:
    "Parse a sequence of command synopses."
    optFileExt = reCompile(r"\[\.([a-zA-Z|.]+)\]")
    forceText = reCompile(r"\s[a-z]+\s[a-z]+\s[a-z]+\s[a-z]+\s")

    def __init__(self, iop, source, refnames):
        self.io = iop
        self.source = source
        self.refnames = refnames
        self.output = ""
        self.confirmed = False
        self.error = None
        self.context = None
        self.callnest = ""
        self.groupnest = 0
        self.lastnest = []
        # Arrange for lexical analysis to work
        self.io.tokenize(self._Pretokenize)
        if bsdVerbosity in self.source.verbose:
            self.source.notify("before reexpansion:" + repr(self.io))
        while True:
            nextl = self.io.peekline()
            if nextl is None:
                break
            elif nextl.startswith("<sbr/>") or blankline.search(nextl):
                self.io.popline()
                continue
            else:
                nextpart = []
                for line in self.io.lines:
                    if line.startswith("<sbr/>"):
                        break
                    nextpart.append(line)
                if not list(filter(self.isCommandSynopsisLine, nextpart)):
                    break
                output = self.parseCommandSynopsis()
                if not output:
                    break
                self.output += output
                if self.error:
                    break
        self.io.tokenize()	# Restore normal tokenization

    def _Pretokenize(self, ln):
        ln = detroff(ln)
        # Fix a perldoc problem
        ln = ln.replace(r"\*(--", "--")
        # Remove ordinary troff highlight macros
        ln = troffHighlightStripper.sub("", ln)
        # Convert . . . to ...
        ln = re.sub(r"\.\s+\.\s+\.", r"...", ln)
        # Grotty little hack to make lexical analysis trivial.  I got
        # this idea from something I read about the first FORTRAN compiler.
        ln = CommandSynopsisSequenceParser.optFileExt.sub(r".@LB@\1@RB@", ln)
        ln = ln.replace(r"|.", r"&verbar;.")
        ln = ln.replace("][", "] @GLUE@ [")
        ln = ln.replace("|", " | ").replace("...", " ... ")
        ln = ln.replace("[", " [ ").replace("]", " ] ")
        ln = ln.replace("{", " { ").replace("}", " } ")
        ln = ln.replace("@LB@", "[").replace("@RB@", "]")
        # Identify and split up redirections
        # Ooops...have to be smarter than this!
        #ln = ln.replace(" &lt;", " &lt; ").replace("&gt;", " &gt; ")
        return ln

    def isCommandSynopsisLine(self, rawline):
        "Does this look like a command synopsis, not just a string of words?"
        line = detroff(rawline)
        # Pipe bar is a sure sign.  So is equals, for GNU-style declarations.
        if '|' in line or '=' in line or "..." in line or "[-" in line:
            return 1
        # Don't be fooled by {}[] that are actually part of C declarations.
        # Otherwise we can end up trying to parse as command synopses some
        # things that should be treated as plain text. cph(1) is an example.
        hasCKeywords = False
        for keyword in cDeclarators:
            if re.search(r"\b" + keyword + r"\b", line):
                hasCKeywords = True
                break
        # Look for special characters that could be part of either
        # function or command synopsis.
        ambiguous = False
        for c in ("{", "[", "]", "}"):
            if c in line:
                ambiguous = True
                break
        if ambiguous and not hasCKeywords:
            return 2
        # We don't want to be fooled by text lines or option lists that
        # begin with a dash but continue with running text.
        if CommandSynopsisSequenceParser.forceText.search(line):
            return 0
        # If the line begins with one of the command's aliases, always treat
        # as a synopsis line.  This catches the important special case where
        # the command name occurs alone on the line, followed by lines
        # describing options.  Also catches cases like "pf2afm fontfilename".
        # Check the global hints database, too.
        tokens = line.split()
        if len(tokens):
            if len(tokens[0]) and tokens[0] in self.refnames:
                return 3
            if globalhints.get(tokens[0]) == "command":
                return 4
        # If we see <command, it means this line was generated by Nm
        # during the first pass and does indeed start a synopsis.
        if line.find("<command") > -1:
            return 6
        # In mdoc, synopsis sections aren't allowed to contain running text.
        if self.source.inSynopsis() and self.source.isActive("mdoc"):
            return 7
        # Look for option starts in syntax sections only.
        if line[0] == '-' or line.find(" -") > -1:
            return 8
        # Now it gets iffy.  We don't have many tokens on this line, or the
        # forcetext regexp would have caught it. Look at the raw line.
        # If the first token is bolded, that probably means it's a command
        # name that doesn't happen to match anything in the name section.
        # Apply this test only when we're in a synopsis section.
        if self.source.inSynopsis() and rawline.startswith(r"\fB") or rawline.startswith(TroffInterpreter.ctrl + r"B "):
            return 9
        # Nope, doesn't look like a command synopsis line
        if classifyVerbosity in self.source.verbose:
            self.source.notify("'%s' does not look like a synopsis line" % line.rstrip())
        return 0

    def parseCommandSynopsis(self):
        "Translate a synopsis line -- here is where the heavy work starts."
        if classifyVerbosity in self.source.verbose:
            self.source.notify("parseCommandSynopsis begins: refnames are %s" % list(self.refnames.keys()))
        output = ""
        try:
            self.callnest = ""
            self.groupnest = 0
            command = self.io.tokenPop()
            if command is None:
                return ""
            self.refnames[command] = True
            if parseVerbosity in self.source.verbose:
                self.source.notify("Command is %s" % command)
            if command in self.refnames or isFileOrCommandName(command):
                globalhints.post(command, "command")
                output += ("  <command>%s</command>" % command)
            else:
                self.io.tokenPush(command)
                raise LiftException(self.source, "first token %s in synopsis looks wrong." % command)
            self.io.checkpoint()
            while self.io.lines:
                if isNltextLine(self.io.lines[0]):
                    break
                arg = self._CompileArg()
                if arg == None:
                    break
                output += "    " + repr(arg) + "\n"
                # This is where we short-stop the command-synopsis parser
                # from eating trailing text sections.
                if repr(arg) == "<sbr/>" and self.io.lines and \
                       not self.isCommandSynopsisLine(self.io.lines[0]):
                    break                
            if output:
                return "<cmdsynopsis>\n"+output+"</cmdsynopsis>\n"
            else:
                return ""
        except LiftException as e:
            self.error = "command synopsis parse failed "
            if self.io.tokenPeek() is None:
                self.error += "at end of synopsis: %s" % (e.message)
            else:
                self.error += "on `%s' (%d): %s" % \
                         (self.io.tokenPeek(), self.io.tokenIndex, e.message)
            self.io.unroll()
            # Generate a useful error message:
            self.context = "\n"
            if self.lastnest:
                self.context += " ".join(self.io.lookbehind[:self.lastnest[-1]])
                self.context += " $ "
                self.context += " ".join(self.io.lookbehind[self.lastnest[-1]:])
            else:
                self.context += " ".join(self.io.lookbehind[:self.io.tokenIndex])
                self.context += " ^ "
                self.context += " ".join(self.io.lookbehind[self.io.tokenIndex:])
            return "\n" + makeComment("\n" + self.error + "\n" + self.context) + "\n"

    # Lexical tests
    def _IsNextSpecial(self):
        if self.io.tokenPeek() in ("[", "]", "{", "}", "|", "...", "*"):
            self.confirmed = True
            return True
        else:
            return False
    def _IsNextCommand(self):
        return self.io.tokenPeek() in self.refnames or globalhints.get(self.io.tokenPeek()) == "command"
    def _IsNextOption(self):
        tnext = self.io.tokenPeek()
        if tnext and tnext[0] in ('-', '+') or tnext.startswith("&plusmn;"):
            self.confirmed = True
            return True
        elif tnext and self.lastnest and tnext in ('&amp;', '&bsol;'):	# See tex.1
            return True
        else:
            return False
    def _IsNextNumeric(self):
        try:
            int(self.io.tokenPeek())
            return True
        except (ValueError, TypeError):
            return False
    def _IsNextReplaceable(self):
        tnext = self.io.tokenPeek()
        if tnext is None:
            return False
        # Good reasons for accepting funky leader characters:
        # @, % -- dig.1
        # :, ', " -- perlrun.1 and other manual pages
        # = -- as.1
        # , -- chmod.1
        # . -- date.1
        # # -- gphoto.1
        # ? -- cdecl.1 and other places where ? invokes help.
        # / -- dummy filename arguments
        # \ -- TeX commands such as luatex.1
        # & -- TeX commands such as luatex.1
        elif tnext[0].isalpha() or tnext[0] in "./=:'\"@%,#?\\&" or (tnext[:4] == "&lt;" and tnext != "&lt;") or self._IsNextNumeric() or isFileOrCommandName(tnext):
            return True
        # nm.1
        elif re.match("[0-9]+_[0-9]+", tnext):
            self.source.warning("suspicious replaceable %s in synopsis" % tnext)
            return True
        else:
            return False
    # Manual-synopsis grammar
    def _CompileArg(self):
        try:
            self.callnest += "  "
            if parseVerbosity in self.source.verbose:
                self.source.notify(self.callnest + "compileArg(" + repr(self.io.tokenPeek()) + ")")
            res = self._CompileArg1()
            if res == None:
                res = None	# Failure is signaled by throwing an exception
            else:
                while self.io.tokenPeek() == "\n":
                    self.io.tokenPop()
                if self.io.tokenPeek() in ("...", "*"):
                    self.io.tokenPop()
                    res.repeat = 1
                elif self.io.tokenPeek() == "|":
                    self.io.tokenPop()
                    first = res
                    res = ParseNode("group")
                    res.children.append(first)
                    self.callnest += "  "
                    if parseVerbosity in self.source.verbose:
                        self.source.notify("%sentering alternation"%self.callnest)
                    while True:
                        if self.io.tokenPeek() in ("|", "\n"):
                            self.io.tokenPop()
                            continue
                        if self.io.tokenPeek() not in ("]", "}")  and not self._IsNextCommand():
                            element = self._CompileArg1()
                            if element:
                                res.children.append(element)
                            else:
                                return res
                            continue
                        break
                    if parseVerbosity in self.source.verbose:
                        self.source.notify("%sexiting alternation"%self.callnest)
                    self.callnest = self.callnest[:-2]
                elif self.io.tokenPeek() == "@GLUE@":
                    res = ParseNode(self.io.tokenPop())
                if parseVerbosity in self.source.verbose:
                    self.source.notify("%scompileArg() returns %s: tokens are %s" % (self.callnest, repr(res), self.io.lookahead))
        finally:
            self.callnest = self.callnest[:-2]
        return res
    def _CompileArg1(self):
        try:
            self.callnest += "  "
            if parseVerbosity in self.source.verbose:
                self.source.notify(self.callnest + "compileArg1(%s, %s)" % (repr(self.io.tokenPeek()), self.io.lookahead))
            # Now get an argument
            if self.io.tokenPeek() is None:
                if self.groupnest == 0:
                    res = None
                else:
                    raise LiftException(self.source, "unbalanced group in synopsis markup")
            elif self.io.tokenPeek() == "<sbr/>":
                self.io.tokenPop()
                while self.io.tokenPeek() == '\n':
                    self.io.tokenPop()
                if not self._IsNextCommand():
                    res = ParseNode("sbr")
                elif self.groupnest == 0:
                    res = None
                else:
                    raise LiftException(self.source, "unterminated group in synopsis")
            elif self.io.tokenPeek() == "\n":
                self.io.tokenPop()
                if self.groupnest == 0 and self._IsNextCommand():
                    res = None
                else:
                    res = ParseNode("\n")
            elif self._IsNextOption():
                option = self.io.tokenPop()
                oldstyle = self.io.tokenPeek() == "@GLUE@"
                if oldstyle:
                    self.io.tokenPop()
                res = ParseNode("arg")
                gnustyle = option.split("=")
                if len(gnustyle) > 1:
                    optnode = ParseNode("option", gnustyle[0])
                    res.children.append(optnode)
                    optnode.righthand = gnustyle[1]
                else:
                    optnode = ParseNode("option", option)
                    res.children.append(optnode)
                    if self.io.lookahead and self._IsNextReplaceable():
                        res.children.append(ParseNode("replaceable",self.io.tokenPop()))
                if oldstyle:
                    optnode.glue = ""
                else:
                    optnode.glue = " "
                self.source.localhints.post(re.escape(optnode.token), "option")
            elif self._IsNextReplaceable():
                res = ParseNode("arg")
                res.children.append(ParseNode("replaceable", self.io.tokenPop()))
            elif self.io.tokenPeek() and self.io.tokenPeek()[:4] in ("&lt;", "&gt;"):
                res = ParseNode("redirect", None, "plain")
                res.token = self.io.tokenPop()
            elif self.io.tokenPeek() in ("[", "{"):
                self.callnest += "  "
                if parseVerbosity in self.source.verbose:
                    self.source.notify("%sentering group"%self.callnest)
                self.groupnest += 1
                self.lastnest.append(self.io.tokenIndex)
                self.io.tokenPop()
                if self.io.tokenPeek() == "{":
                    required = "req"
                else:
                    required = "opt"
                lst = []
                while True:
                    if self.io.tokenPeek() == '\n':
                        self.io.tokenPop()
                        continue
                    if self.io.tokenPeek() not in (None, "]", "}"):
                        lst.append(self._CompileArg())
                        continue
                    break
                if len(lst) == 1:
                    res = lst[0]
                else:
                    res = ParseNode("arg")
                    res.children = lst
                res.choice = required
                if self.io.tokenPeek() is None or self.io.tokenPeek() == "<sbr/>":
                    raise LiftException(self.source, "expecting ] or }")
                else:
                    self.io.tokenPop()
                self.lastnest.pop()
                self.groupnest -= 1
                if parseVerbosity in self.source.verbose:
                    self.source.notify("%sexiting group"%self.callnest)
                self.callnest = self.callnest[:-2]
            else:
                raise LiftException(self.source, "expecting argument")
            if parseVerbosity in self.source.verbose:
                self.source.notify("%scompileArg1() returns %s: tokens are %s" % (self.callnest, res, " ".join(self.io.lookahead)))
        finally:
            self.callnest = self.callnest[:-2]
        return res


def isNltextLine(line):
    "Are there patterns here that must be natural language?"
    if line is None:
        return False
    line = line.strip()
    if not line or len(line) < 2:
        return False
    # Line ending with period that is not part of an ellipsis has to be a
    # NL sentence, because lone periods can't occur in command
    # synopses and periods can't occur at all in function synopses.
    if line[-1] == '.' and line[-2].isalpha():
        return True
    # Line ending with semicolon has to be a NL sentence. Note that
    # embedded colons can occur as argument leaders in, e.g.,
    # port suffixes for some network commands.
    if line[-1] == ':':
        return True
    words = line.split()
    if len(line) < 8:
        return False
    if len(words) < 3:
        return False
    # Look for giveaway words.
    for word in ("the", "and", "with", "whitespace", "abbreviated"):
        if word in words:
            return True
    return False

class DisplayParser:
    "Parse a block into function synopsis, command synopsis or display text."
    oldStyleOptionGlue = reCompile(r"([^A-Za-z]-[A-Za-z]*)(?:\f.)([A-Za-z])")
    unparseable = reCompile(r"\$[A-Za-z]|=&gt;|[^:]//|@load")	# Perl, Awk, and other nightmares
    def __init__(self, source, trySynopsis, literal, refnames=None):
        "Arrange the interpreter to accumulate synopsis lines in this object."
        self.source = source
        self.trySynopsis = trySynopsis
        self.literal = literal
        self.refnames = refnames
        if self.refnames is None:
            self.refnames = {}
        self.synopses = []
        source.diversion = self.synopses
        self.io = None
        source.ignore("nf")
        source.ignore("fi")
        source.ignore("ft")
        source.ignore("ti")
        # Some pages (e.g. xdrChar.3) use this inside .EX/.EE pairs
        source.ignore("PP")
        # .ta conveys no information in a Synopsis section,
        # but outside one it may be our only clue that the man page
        # author kluged up a table inline. So don't disable
        # processing it in that case.
        if source.inSynopsis():
            source.ignore("ta")
        source.ignore("ce")
        source.unignore("br")
        source.unignore("nl")
        source.unignore("in")
    def _Wrap(self):
        # Re-enable normal commands
        self.source.diversion = self.source.output
        self.source.unignore("nf")
        self.source.unignore("fi")
        self.source.unignore("ft")
        self.source.unignore("ti")
        self.source.unignore("PP")
        if self.source.inSynopsis():
            self.source.unignore("ta")
        self.source.unignore("ce")
        self.source.ignore("br")
        self.source.ignore("nl")
        self.source.ignore("in")
    def _DetectUnparseableSynopsis(self):
        "Detect stuff we just shouldn't try to parse."
        # Blank sections
        text = self.io.text().strip()
        if not text:
            return True
        # Or anything with Perl identifiers or an Awk library load in it...
        if DisplayParser.unparseable.search(text):
            return True
        # Or Fortran synopses (as in the pvm bindings)
        if "Fortran" in text:
            return True
        # Also detect things that look like SQL synopses
        if text.split()[0].isupper() and self.source.find("SQL", backwards=True):
            return True
        return False
    def _EmitText(self, lines):
        if not lines:
            return ""
        if ioVerbosity in self.source.verbose:
            self.source.notify("_EmitText('''%s''')\n" % "".join(lines))
        for i in range(len(lines)):
            if lines[i].startswith("<sbr"):
                lines[i] = "\n"
        # All set up.  Now block-interpret this like ordinary running
        # text, so ordinary commands will work.
        tempout = []
        if self.source.inSynopsis():
            self.source.needParagraph()
        self.source.interpretBlock(lines, tempout)
        if self.source.inSynopsis():
            self.source.endParagraph()
        if classifyVerbosity in self.source.verbose:
            self.source.notify("got unknown section")
        lines = []
        text = "".join(tempout)
        if text.startswith("<para>") and text.endswith("\n"):
            text = text[:-1] + "</para>\n"
        return text
    def transform(self):
        "Parse and transform the display section we've gathered."
        if classifyVerbosity in self.source.verbose:
            self.source.notify("display parse begins, refnames = %s"%self.refnames)
        # Undo redirection and re-enable normal commands.
        self._Wrap()
        # First, fold the lines.  We have to handle continuations
        # explicitly, since we may be outside the body section.
        processed = []
        for line in self.synopses:
            if line[:4] != "<!--":
                line = self.source.expandEntities(line)
                if processed and processed[-1][-2:] == "\\c":
                    processed[-1] = processed[-1][:-2] + line
                else:
                    processed.append(line+"\n")
        # Translate troff characters and XMLlify everything.
        if classifyVerbosity in self.source.verbose:
            self.source.notify("Before tokenization: %s\n" % processed)
        self.io = LineTokenizer(processed,
                                tokenizerVerbosity in self.source.verbose)
        if classifyVerbosity in self.source.verbose:
            self.source.notify("After tokenization: \n" + "".join(self.io.lines))

        # This code is failure-prone.  It is coping as best it can with a mess.
        #
        # The underlying problem is that from DocBook's point of view,
        # Synopsis sections in man pages come in three different flavors
        # that need to be marked up differently -- command synopses,
        # function synopses, and plain old text.
        #
        # Trying to analyze Synopsis sections raises three problems.
        # The first and worst problem is that there are no airtight syntactic
        # ways to distinguish between the three different section types.
        #
        # The second problem is that there is stuff we shouldn't even bother
        # trying to parse because it's hopeless -- Perl synopses are the
        # largest subcategory of these.  We should detect these and pass
        # them through as plain-text Synopsis sections.
        #
        # Unfortunately, we can't resolve the problem before doing
        # first-pass macrointerpretation of the whole synopsis
        # section.  That's how we get mdoc macros evaluated -- and
        # there may be others the man-page author created.  This
        # means the text we're interpreting may contain <. >, and tags.
        #
        # The strategy we use is to repeatedly look for function synopses,
        # command synopses, or lines that we can unambiguously identify as
        # natural language.  When we fail to find one starting on a
        # given line, we stash that line away and advance to the next.
        # Each time we find one of the structured things we can detect
        # reliably, we flush the accumulated stash before emitting the
        # structured stuff.
        parsepass = errors = 0
        out = ""
        if not self.trySynopsis or self._DetectUnparseableSynopsis():
            err = None
            out += "<synopsis>\n" + self.io.text().replace("<sbr/>", "\n") + "</synopsis>\n"
            if classifyVerbosity in self.source.verbose:
                self.source.notify("got unparseable synopsis ")
        else:
            classified = False
            stash = []
            while self.io.lines:
                parsepass += 1
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("pass %d begins"% parsepass)
                # Try to get a function synopsis
                obj = FunctionSynopsisParser(self.io, self.source)
                err = obj.error
                if not err and obj.output:
                    out += self._EmitText(stash)
                    out += obj.output.replace("<sbr/>", "\n")
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("got function synopsis")
                    continue
                elif obj.output and obj.language:
                    if self.source.inSynopsis():
                        self.source.error(obj.error)
                    elif classifyVerbosity in self.source.verbose:
                        self.source.warning(obj.error)
                # Look for unambiguous natural language.  This has to be
                # done first because synopses for libraries not infrequently
                # contain link instructions that can be mistaken for command
                # synopses.
                while isNltextLine(self.io.peekline()):
                    classified = True
                    nextl = self.io.popline()
                    if classifyVerbosity in self.source.verbose:
                        self.source.warning("stashing '%s' (NL)" % repr(nextl))
                    stash.append(nextl)
                # Now perhaps try for a command synopsis
                if self.source.inSynopsis():
                    obj = CommandSynopsisSequenceParser(self.io, self.source, self.refnames)
                    err = obj.error
                    if not err and obj.output:
                        out += self._EmitText(stash)
                        out += obj.output
                        if classifyVerbosity in self.source.verbose:
                            self.source.notify("got command synopsis '%s'"%out)
                        continue
                    elif obj.output and obj.confirmed:
                        errors += 1
                        out += obj.output
                        if self.source.inSynopsis():
                            self.source.error(obj.error)
                            if self.source.verbose:
                                self.source.error("error context: %s" % obj.context)
                        elif classifyVerbosity in self.source.verbose:
                            self.source.warning(obj.error)
                # Look for a filename - some manual pages for
                # configuration files just give the full path of the
                # file as the synopsis.  This case doesn't do anything
                # very interesting, but it does avoid throwing a
                # warning.
                line = self.io.peekline()
                if classifyVerbosity in self.source.verbose:
                    self.source.notify("checking for plain filename")
                if line and re.match(r"/[\S]*$", line):
                    out += self._EmitText(stash)
                    fnpart = "<filename>" + line.strip() + "</filename>"
                    if self.literal:
                        out += fnpart + "\n"
                    else:
                        out += "<para>" + fnpart + "</para>\n"
                    if classifyVerbosity in self.source.verbose:
                        self.source.notify("found plain filename")
                    self.io.popline()
                    classified = True
                    continue
                # None of the above.  Stash the current line and try again on
                # the next one.
                nextl = self.io.popline()
                if nextl:
                    classified = False
                    if classifyVerbosity in self.source.verbose:
                        self.source.warning("stashing %s" % repr(nextl))
                    stash.append(nextl)
            # We've pulled as much of the section as we can into structured
            # markup.  If there's anything left, treat it as plain text.
            if stash:
                if classifyVerbosity in self.source.verbose:
                    self.source.warning("emitting stash %s" % repr(stash))
                out += self._EmitText(stash)
        # Postprocess the output to remove glue and clean up empty tags
        out = hotglue.sub("", out)
        out = cleantag.sub("", out)
        out = re.sub(r"<funcsynopsisinfo>\s*</funcsynopsisinfo>", "", out)
        out = re.sub(r"<funcsynopsis>\s*</funcsynopsis>", "", out)
        return (out, parsepass > 1 and errors == 0 and not classified)

#
# Macro interpreters.
#

class Author:
    "Represents an Author object."
    def __init__(self, iname=None, iaffil=None):
        self.firstname = None
        self.middle = None
        self.surname = None
        self.lineage = None
        self.orgname = None
        self.orgdiv = None
        self.jobtitle = None
        if iname:
            self.name(iname)
        if iaffil:
            self.orgname = iaffil
    def nonempty(self):
        return self.firstname or self.surname or self.orgname or self.orgdiv
    def name(self, name):
        "Parse a single name from a text line (English-language rules)."
        trial = name.split()
        if len(trial) >= 4:
            self.lineage = trial[3]
        if len(trial) >= 3:
            (self.firstname, self.middle, self.surname) = trial[:3]
        elif len(trial) >= 2:
            (self.firstname, self.middle, self.surname) = (trial[0], None, trial[1])
        else:
            self.middle = trial[0]
    def __repr__(self):
        res  = "<author>\n"
        if self.firstname:
            res += "    <firstname>%s</firstname>\n" % self.firstname
        if self.middle:
            if self.middle[-1] == '.':
                role = " role='mi'"
            else:
                role = ""
            res += "    <othername%s>%s</othername>\n" % (role, self.middle)
        if self.surname:
            res += "    <surname>%s</surname>\n" % self.surname
        if self.lineage:
            res += "    <lineage>%s</lineage>\n" % self.lineage
        if self.orgname or self.jobtitle or self.orgdiv:
            res += "    <affiliation>\n"
            if self.orgname:
                res += "        <orgname>%s</orgname>\n" % self.orgname
            if self.jobtitle:
                res += "        <jobtitle>%s</jobtitle>\n" % self.jobtitle
            if self.orgdiv:
                res += "        <orgdiv>%s</orgdiv>\n" % self.orgdiv
            res += "    </affiliation>\n"
        res += "</author>"
        return res

class ManInterpreter:
    "Interpret man(7) macros."
    name = "man"
    exclusive = True
    toptag = "refentry"
    immutableSet = set(["B", "I","R" ,"SM","CB","CR",
                     "BI","BR","IB","IR",
                     "IL","RB","RI","RL","SB","LB","LI","LR",
                     "P" ,"PP","LP","HP",
                     "IP","RS","RE","SH","SS","TP",
                     "UE","UN","UR","IX","BY",])
    ignoreSet = set(["PD", "DT",
                  # Undocumented and obscure
                  "LO", "PU", "UC", "l",
                  # Extensions from mtools doc set; we can safely ignore them
                  "iX", "lp",
                  # fm is some kind of attribution extension in MIT pages
                  "FM",
                  # Undocumented, used in the attr(3) man pages
                  "Op",
                  # Occurs in X Consortium manpages redundant with .ta,
                  # but not all such man pages have an identifiable X header.
                  "TA",])
    complainSet = set([])
    parabreakSet = set(["blank","P","PP","LP","HP","IP","TP",])
    sectionbreakSet = set(["SH","SS",])
    listbreakSet = set(["P","PP","LP","HP","SH","SS",])
    scopedSet = set(["RS"])
    translations = {
        "\\*" : [
        (r"\*R",  "&reg;"),
        (r"\*S",  "<?troff ps 0?>"),
        (r"\*(Tm", "&trade;"),
        ],
        "\\*(" : [
        (r"\*(lq", "&ldquo;"),
        (r"\*(rq", "&rdquo;"),
        (r"\*(Aq", "&apos;"),
        # tetex pages use these without defining them.
        (r"\*(TX", "TeX"),
        (r"\*(WB", "WEB"),
        # Some BSD pages use this without defining it
        (r"\*(Ps", "Postscript"),
        ],
        "\\*[" : [
        # Some groff pages use this with a conditional
        # definition that we can't handle gracefully.
        (r"\*[tx]", "TeX"),
        # A rather understandable typo
        (r"\*[tex]", "TeX"),
        ]
      }
    # Tricky interaction with pod2man here; the Ip reduction will get called if
    # there is an explicit Ip macro, but if pod2man is recognized there will
    # be no explicit definition.
    reductions = {"Pp":"PP", "Tp":"TP", "Ip":"IP", "TQ":"TP",
                  # catch some mdoc-influenced mistakes we see occasionally...
                  "Nm":"B", "Sh":"SH", "Ss":"SS"}
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.hackUrls = True
        self.authors = None
        self.volnum = []
        self.refnames = {}
        self.seenDS = False
        self.haveName = False
        self.stashLinkender = None
        self.manual = ""
        self.msrc = ""
	#self.systype = None
        # .Id is used to embed RCS IDs in pages like ci.1.  The
        # effect we're after here is to make it a no-op, but allow it
        # to be locally overridden (which wouldn't be possible if it
        # were on the ignore list.)
        self.source.troff.macros["Id"] = []
    def foldHighlights(self, cmd, args):
        # We need this to be a separate entry point for TP tag processing.
        # .R is not one of the documented font-change macros, but it is
        # occasionally used anyway (eg by sz.1) -- derived from Ultrix.
        # .CB and .CR are groff extensions.
        if cmd in ("B", "I", "R", "L", "SM", "CB", "CR"):
            return self.source.directHighlight(cmd, args)
        elif cmd in ("BI","BR","BL",
                     "IB","IR","IL",
                     "RB","RI","RL",
                     "LI","LR","LB",
                     "SB"):
            return self.source.alternatingHighlight(cmd, args)
        else:
            return None
    @staticmethod
    def startSynopsis(args):
        "Are we looking at a start odf synopsis?"
        # Must accept "SYNOPSIS" but reject "SYNOPSIS AND DESCRIPTION",
        # otherwise xdr(3) abd related pages will be misparsed.
        return list(filter(synopsisLabel.search, args)) \
               and not list(filter(descriptionLabel.search, args))
    def endSynopsis(self):
        self.source.sectionhooks.remove(self.endSynopsis)
        self.source.flushTransplant()
        self.source.unignore("Ve")	# For Perl generated man pages
        self.source.unignore("Vb")	# For Perl generated man pages
        self.source.unignore("Ip")	# For Perl generated man pages
        self.source.unignore("HP")
        self.source.unignore("RS")
        self.source.unignore("RE")
    def interpret(self, dummyLine, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        # Highlighting
        highlighted = self.foldHighlights(cmd, args)
        if highlighted:
            self.source.pushline(highlighted)
        # Sectioning
        elif cmd in ("blank", "P","PP","LP","HP") or (cmd=="IP" and (not args or not args[0])):
            if self.source.bodySection():
                self.source.paragraph()
            elif self.source.inSynopsis():
                self.source.emit("<sbr/>")
            return True
        elif cmd == "SH":
            self.source.diversion = self.source.output
            if not args:
                args = self.source.popline().split()
            # Ignore '.SH ""' -- yes, this actually happens on passwd.1,
            # apparently as a half-assed way to resume paragraphing after
            # a list.
            elif args[0] == "":
                self.source.needParagraph()
                return True
            # Handle nasty perversity in cvsversion.1 that might be repeated
            elif args[0].find("--") > -1:
                tokens = args[0].split()
                args[0] = tokens[0]
                self.source.pushline(" ".join(tokens))
            self.source.troff.nf = False
            # Skip blank lines and paragraph commands
            while True:
                line = self.source.popline()
                # Can't use paragraphBreak() here lest we skip .TP or .IP
                if line and not line[:3] in (TroffInterpreter.ctrl + "PP", TroffInterpreter.ctrl + "LP", TroffInterpreter.ctrl + "P"):
                    self.source.pushline(line)
                    break
            #self.source.pushline(line)
            # Now do processing that is specific to the section type.
            # The self.source.synopsis check avoids croaking on CrtImgType(3)
            # and other pages that use NAME as a body section name
            if nameSynonyms.match(deemphasize(args[0])) and len(args)==1 and not self.source.synopsis:
                self.source.sectname = "NAME"
                if namesectionVerbosity in self.verbose:
                    self.source.notify("I see a name section")
                self.haveName = True
                namesects = [""]
                self.source.ignore("nf")
                self.source.ignore("fi")
                # Cope with initial .TP
                while self.source.peekline().startswith(".TP"):
                    self.source.popline()
                while True:
                    line = self.source.popline()
                    # Here's how we exit processing name sections
                    if line is None or self.source.sectionBreak(line):
                        self.source.pushline(line)
                        break
                    # Cope with man pages generated by Texinfo that have a
                    # start-of-page troff comment and macros after the
                    # name line
                    if line.startswith("'\\\" t"):
                        self.source.pushline(line)
                        break
                    # Discard other blank lines and comments
                    if not line or isComment(line):
                        continue
                    # Discard lines consisting only of a command leader
                    # (as in groff_mdoc(7)).
                    if line == TroffInterpreter.ctrl:
                        continue
                    # Maybe we ought to generate something here?
                    if matchCommand(line, "IX"):
                        continue
                    # Cope with some Pod2Man brain-death.  It issues lines like
                    # .IP "\fBfoo\fR \- foo the bar" 4
                    # using .IP as a crude presentation-level hack
                    m = re.match('.IP "([^"]*)".*', line)
                    if m:
                        line = m.group(1)
                    # Cope with .TP in name sections
                    if matchCommand(line, "TP"):
                        continue
                    if isCommand(line) and self.source.ignorable(line):
                        continue
                    # Dash on a line means we start a new namediv,
                    # providing some previous line has started one.
                    if namesectionVerbosity in self.verbose:
                        self.source.notify("Before section test: %s\n" % repr(line))
                    if r"\-" in line and r"\-" in namesects[-1] and not namesects[-1].endswith(r"\-"):
                        if namesectionVerbosity in self.verbose:
                            self.source.notify("New name section")
                        namesects.append("")
                    # So does a break or paragraphing command
                    if line.startswith(".br") or self.source.paragraphBreak(line):
                        namesects.append("")
                        continue
                    # Some selinux pages require this:
                    if re.match("\.[BI] ", line):
                        line = line[2:]
                    # groff perversely inserts macro definitions here
                    if line.startswith(".de co") or line.startswith(".de au"):
                        self.source.pushline(line)
                        break
                    # All other commands have to be ignored;
                    # this is necessary to throw out Pod2Man generated crud
                    if isCommand(line):
                        continue
                    # Finally, something we can append to the current namesect
                    namesects[-1] += " " + line
                if namesectionVerbosity in self.verbose:
                    self.source.notify("Assembled name sections: %s\n" % repr(namesects))
                self.source.unignore("nf")
                self.source.unignore("fi")
                for namesect in namesects:
                    if not namesect:
                        continue
                    # Split the name section on "-".  If it
                    # only contains one of these, the part before
                    # could be a multi-line list of entry points
                    # (which is OK).  If it contains more than one
                    # "-", it consists of multiple name lines and
                    # we don't have enough marker information to parse
                    # it, so just barf.
                    try:
                        (name, description) = parseNameSection(namesect)
                    except (TypeError, ValueError):
                        self.source.error("ill-formed NAME section '%s' in %s, giving up." % (namesect, self.source.file))
                        return
                    self.source.emit("<refnamediv>")
                    for nid in [x.strip() for x in name.split(",")]:
                        nid = troffHighlightStripper.sub("", nid)
                        self.refnames[nid] = True
                        self.source.emit("<refname>%s</refname>" % nid)
                    self.source.emit("<refpurpose>%s</refpurpose>"%description)
                    self.source.emit("</refnamediv>")
            elif ManInterpreter.startSynopsis(args) and not self.source.synopsis:
                self.source.endParagraph()
                self.source.sectname = "SYNOPSIS"
                self.source.ignore("RS")
                self.source.ignore("RE")
                self.source.ignore("HP")
                self.source.ignore("Ve")	# For Perl generated man pages
                self.source.ignore("Vb")	# For Perl generated man pages
                self.source.ignore("Ip")	# For Perl generated man pages
                self.source.sectionhooks.append(self.endSynopsis)
                trySynopsis = self.volnum != "3pm" and self.manual.find("Perl") == -1 or self.msrc.find("perl ") == -1
                self.source.synopsis = DisplayParser(self.source,
                                                     trySynopsis,
                                                     False,
                                                     self.refnames)
            elif not self.source.synopsis and self.source.find(synopsisHeader):
                if sectionVerbosity in self.source.verbose:
                    self.source.notify("transplanting section...")
                self.source.diversion = self.source.transplant
                self.source.pushSection(1, " ".join(args))
            else:
                self.source.declareBodyStart()
                self.source.pushSection(1, " ".join(args))
        elif cmd == "SS":
            self.source.diversion = self.source.output
            if not args:
                args = self.source.popline().split()
            if self.source.bodySection():
                # Normally SS sections are at depth 2,
                # but there are exceptions...
                if not self.source.nonblanks:
                    if self.source.sectiondepth > 1:
                        self.source.warning("possible section nesting error")
                    newdepth = self.source.sectiondepth + 1
                else:
                    newdepth = 2
                # Now that we've calculated the new depth...
                self.source.pushSection(newdepth, " ".join(args).strip())
            elif args[0] in qtHeaders:
                self.source.pushline(args[0])
            else:
                # In case the Synopsis section contains a subsection,
                # as in cph.1, we want to start a new *first* level section.
                self.source.pushSection(1, " ".join(args))
        elif cmd == "TH":
            args = args[:5]
            args += (5 - len(args)) * [""]
            (title, self.volnum, date, self.msrc, self.manual) = args
            self.source.inPreamble = False
            if ioVerbosity in self.source.verbose:
                self.source.notify("exiting preamble")
            # The .TH fields are often abused.  Check that the date at
            # least has a number in it; if not, assume the date field was
            # skipped and it's actually a source.
            if re.match("[0-9]", date):
                self.source.emit("<refentryinfo><date>%s</date></refentryinfo>" % date)
            else:
                self.manual = self.msrc
                self.msrc = date
                date = None
            self.source.emit("<refmeta>")
            self.source.emit("<refentrytitle>%s</refentrytitle>" % title)
            self.source.emit("<manvolnum>%s</manvolnum>" % self.volnum)
            if date:
                self.source.emit("<refmiscinfo class='date'>%s</refmiscinfo>" % date)
            if self.msrc:
                self.source.emit("<refmiscinfo class='source'>%s</refmiscinfo>"% self.msrc)
            if self.manual:
                self.source.emit("<refmiscinfo class='manual'>%s</refmiscinfo>"% self.manual)
            self.source.emit("</refmeta>")
            # Ugh...some pages put text or macros here; ftpcopy(1) is one;
            # Divert it so we don't break validation.
            discard = []
            self.source.diversion = discard
        # Lists
        elif cmd == "IP":
            # Ignore this if in a Synopsis section.
            if self.source.inSynopsis():
                self.source.pushline(" ".join(args))
            else:
                self.source.endParagraph(label=cmd)
                # Discard second argument of IP tag
                args = args[:1]
                # Some tags can turn into an ItemizedList.  Give
                # each type a different name, otherwise the lower-level
                # machinery gets confused about list boundaries.
                # perlhack(1) and gcc(1) are pages where this actually matters.
                bullet = None
                if len(args):
                    bullet = ipTagMapping.get(args[0])
                if bullet:
                    self.source.emitItemizedlist("IP+"+bullet, bullet)
                # Otherwise, emit a variable list
                else:
                    self.source.emitVariablelist(cmd, " ".join(args))
        elif cmd == "TP":
            # Ignore this if in a Synopsis section.
            if self.source.inSynopsis():
                self.source.pushline(" ".join(args))
            elif blankline.match(self.source.peekline()):
                pass	# Common malformation at end of lists
            elif self.source.paragraphBreak(self.source.peekline()):
                pass	# Another common malformation at end of lists
            else:
                self.source.endParagraph(label=cmd)
                # Can't process this until one more text line has been emitted
                self.source.trapEmit(".TPINTERNAL ")
        elif cmd == "TPINTERNAL":
            self.source.emitVariablelist("TP", " ".join(args))
        # Relative indent changes
        elif cmd == "RS":
            # Check for no-ops generated by pod2man.
            if self.source.peekline().startswith(TroffInterpreter.ctrl + "RE"):
                self.source.popline()
                return True
            # We may be able issue no markup for these.
            # Notably, if we're looking at .RS+.nf, this is
            # just an indented block with no structural significance.
            # Mark it on the stack so a following RE will pop it.
            nextl = self.source.peekline()
            if nextl and nextl.startswith(TroffInterpreter.ctrl + "nf"):
                self.source.pushlist("RS")
                return True
            # No markup for .nf+.RS, too, but note it on the stack
            elif self.source.lastTag("<literallayout"):
                self.source.pushlist("RS")
                return True
            # If we're in list content, nest the list a level deeper
            elif self.source.stashIndents:
                if nextl.startswith(".TP") or nextl.startswith(".IP"):
                    self.source.pushlist("RS", None)
                else:
                    self.source.beginBlock("blockquote", remap='RS')
                    self.source.pushlist("RS", "blockquote")
                self.source.needParagraph()
                return True
            # Next check for single-line .RS/.RE blocks.
            # This will fail if the line has a highlight.
            elif not isCommand(self.source.peekline()):
                text = self.source.popline()
                if self.source.peekline() == TroffInterpreter.ctrl + "RE":
                    self.source.popline()
                    self.source.beginBlock("literallayout", remap='RS')
                    self.source.emit(text)
                    self.source.endBlock("literallayout", remap='RE')
                    return True
                else:
                    self.source.pushline(text)
                    # Fall through
            # None of the special cases fired.  Punt; treat as blockquote
            self.source.pushlist("RS", "blockquote")
            self.source.beginBlock("blockquote", remap='RS')
        elif cmd == "RE":
            self.source.poplist("RS", remap="RE")
            self.source.needParagraph()
        # FSF extension macros
        elif cmd == "UE":	# End of link text
            if self.source.bodySection():
                self.source.pushline(self.stashLinkender)
        elif cmd == "UN":	# Anchor for a hyperlink target
            if not args:
                self.source.error("UN macro requires an argument")
            elif self.source.bodySection():
                if self.source.peekline()[:3] in (TroffInterpreter.ctrl + "SH", TroffInterpreter.ctrl + "SS"):
                    self.source.stashId = args[0]
                else:
                    if self.source.docbook5:
                        self.source.pushline("<anchor xml:id='%s'/>" % self.source.makeIdFromTitle(tokens[1]))
                    else:
                        self.source.pushline("<anchor id='%s'/>" % self.source.makeIdFromTitle(tokens[1]))
        elif cmd == "UR":	# Start of link text
            if not args:
                self.source.error("UR macro requires an argument")
            elif self.source.bodySection():
                if args[0][0] == "#":
                    self.source.pushline("<link linkend='%s'>" % self.source.idFromTitle(args[0][1:]))
                    self.stashLinkender = "</link>"
                else:
                    self.source.pushline("<ulink url='%s'>" % args[0])
                    self.stashLinkender = "</ulink>"
            self.hackUrls = False
        elif cmd == "ME":	# End of link text
            if self.source.bodySection():
                self.source.pushline(self.stashLinkender)
        elif cmd == "MT":	# Start of mail address text
            if not args:
                self.source.error("MT macro requires an argument")
            elif self.source.bodySection():
                self.source.pushline("<ulink url='mailto:%s'>" % args[0])
                self.stashLinkender = "</ulink>"
        # Indexing
        elif cmd == "IX":
            if self.source.bodySection() and len(tokens) > 1:
                # Discard Perl section indicators
                if tokens[1] in ("Name","Title","Header","Subsection","Item"):
                    tokens = tokens[2:]
                self.source.pushline(self.source.index(list(map(deemphasize, args))))
        # Ultrix extensions.  Taken from groff's man.ultrix file
        # Some of these (like EX/EE) appear in Linux manual pages.
        # The special guards on some of these avoid problems if, as is
        # sometimes the case, the macros are defined specially in the file.
        # See http://www.geocrawler.com/archives/3/377/1992/10/0/2062814/
        # for an interesting historical sidelight.
        elif cmd == "CT":
            self.source.pushline("&lt;CTRL/%s&lt;" % args[0])
        elif cmd == "Ds":
            if not self.source.inSynopsis():
                self.source.beginBlock("literallayout", remap="Ds")
        elif cmd == "De":
            if not self.source.inSynopsis():
                self.source.endBlock("literallayout", remap="De")
        elif cmd == "EX" and "EX" not in self.source.troff.macros:
            if not self.source.inSynopsis():
                self.source.beginBlock("literallayout", remap="EX")
        elif cmd == "EE" and "EE" not in self.source.troff.macros:
            if not self.source.inSynopsis():
                self.source.endBlock("literallayout", remap="EE")
        elif cmd == "NT" and "NT" not in self.source.troff.macros:
            self.source.beginBlock("note", remap="NT")
        elif cmd == "NE" and "NE" not in self.source.troff.macros:
            self.source.endBlock("note", remap="NE")
        elif cmd == "RN":
            self.source.pushline("<keycap>RETURN</keycap>")
        elif cmd == "PN":
            self.source.pushline("<filename>%s</filename>" % args[0])
        elif cmd == "MS":
            self.source.pushline("<citerefentry><refentrytitle>%s</refentrytitle><manvolnum>%s</manvolnum></citerefentry>" % args[:2])
        # Undocumented -- interpret args as comma-separated list of authors
        elif cmd == "BY":
            self.authors = " ".join(args).split(",")
        # Undocumented -- hangover from old Bell Labs and Berkeley macros
        elif cmd == "UX":
            self.source.pushline("Unix")
        # Used in former times to declare the system type
        elif cmd == "AT":
            pass
#            self.systype = "7th Edition"	# Also .AT 3
#            if len(args) > 0:
#                if args[0] == "4":
#                    self.systype = "System III"
#                elif args[0] == "5":
#                    if len(args) > 1:
#                        self.systype = "System V Release 2"
#                    else:
#                        self.systype = "System V"
        elif cmd == "UC":
            pass
#            self.systype = "3rd Berkeley Distribution":
#            if len(args) > 0:
#                if args[0] == "4":
#                    self.systype = "4th Berkeley Distribution"
#                elif args[0] == "5":
#                    self.systype = "4.2 Berkeley Distribution"
#                elif args[0] == "6":
#                    self.systype = "4.3 Berkeley Distribution"
#                elif args[0] == "7":
#                    self.systype = "4.4 Berkeley Distribution"
        # DS/DE isn't part of the man macros.  Interpret it anyway,
        # as there is an obvious meaning that people try to use.
        elif cmd == "DS":
            # Catch an odd, pointless use of .DS that pops up on a number
            # of SANE manual pages (probably generated from something).
            if self.source.peekline() == TroffInterpreter.ctrl + "sp\n":
                self.source.popline()
                self.source.popline()
            elif self.source.find("DE"):
                self.source.beginBlock("literallayout", remap='DS')
                self.seenDS = True
        elif cmd == "DE":
            if self.seenDS:
                self.source.endBlock("literallayout", remap='DE')
            else:
                return False
        # Groff extensions
        elif cmd == "SY":
            if args:
                self.source.pushline(args[0])
        elif cmd == "OP":
            self.source.pushline("[" + " ".join(args) + "]")
        elif cmd == "YS":
            pass
        # Use our reductions as fallbacks
        elif cmd in ManInterpreter.reductions:
            replaceWith = ManInterpreter.reductions[cmd]
            self.source.pushline(TroffInterpreter.ctrl + replaceWith + " " + quoteargs(args))
        # Recover from some common typos
        elif cmd[0] in "BIR" and cmd[1].islower() and len(cmd) > 3:
            newtokens = [TroffInterpreter.ctrl + cmd[:1]] + [cmd[1:]] + tokens[1:]
            self.source.warning("rewriting %s as %s" % (tokens, newtokens))
            self.source.pushline(newtokens[0]+" "+quoteargs(newtokens[1:]))
        else:
            return False
        return True
    def wrapup(self):
        if self.authors:
            # Assumes man pages with "BY" don't have explicit AUTHOR parts.
            self.source.emit("<refsect1><title>Author</title>")
            self.source.emit("<para>" + ", ".join(self.authors) + "</para>")
            self.source.emit("</refsect1>")
    def preprocess(self, text):
        # Strip the Perl code from man pages that self-unpack
        perltrailer = text.find("END PERL/TROFF TRANSITION")
        if perltrailer > -1:
            text = text[perltrailer:]
            text = text[text.find("\n"):]
        # Ugh.  Some ISC man pages (for lwres*) actually make this necessary!
        # Who knew that troff allowed this?
        text = text.replace("\n\\fR.SH", "\n.SH").replace("\n\\fR.PP", "\n.PP")
        # This bizarre thing happens on snmpnetstat(1).
        # groff(1) accepts it, groffer(1) complains and accepts it.
        text = text.replace("\n.I&nbsp;", "\n.I ")
        # Some versions of db2man.xsl have a bad bug.  Work around it.
        text = reCompile("(\\.TH.*)\\.SH NAME").sub(r"\1\n.SH NAME", text)
        # Some versions of netpbm makeman have a bad bug.  Work around it.
        text = reCompile("(\\.UN.*)\\.SH").sub(r"\1\n.SH", text)
        # Reverse a transformation that db2man does when translating <note>.
        # FIXME: turn the following paragraph into a <note>.
        text = text.replace(".it 1 an-trap\n.nr an-no-space-flag 1\n.nr an-break-flag 1\n.br\n", "")
        # Brain-damage emitted often by Pod2Man, occasionally by humans
        text = reCompile("\\.PD.*\n+(.S[hHsS])").sub("\n\n\\1", text)
        text = reCompile("\\.RS.*\n+(.S[hHsS])").sub("\n\n\\1", text)
        # Cheating way to avoid some annoying warnings on function pages
        if "NAME\nfeatureTest_macros" not in text:
            text = reCompile("(\\.in [+-][0-9]*n)?(\nFeature Test)", re.I).sub("\n.SH FEATURE TEST\n\n\\2", text)
        return text
    def postprocess(self, text):
        # Page might be generated crap with no sections, which can't be lifted.
        # This happens with some pod2man pages.
        if not self.source.sectionCount:
            if self.source.verbose:
                self.source.warning("Pod2Man page with no body.")
            text = text.replace("</refentry>", "") + empty
        elif not self.haveName:
            raise LiftException(self.source, "no name section in %s, can't be lifted." % self.source.file)
        # If there was no explicit URL markup, process implicit ones
        if self.hackUrls and not self.source.isActive("mwww") and not xmlnsRe.search(text):
            text = urlRe.sub(r"<ulink url='\g<url>'>\g<url></ulink>", text)
        foundit = text.rfind("SEE ALSO")
        if foundit > -1:
            before = text[:foundit]
            after = text[foundit:]
            after = re.sub(r'([a-zA-Z0-9_-]+)\(([0-9].?)\)', r'<citerefentry><refentrytitle>\1</refentrytitle><manvolnum>\2</manvolnum></citerefentry>', after)
            text = before + after
        foundit = text.rfind("FILES")
        if foundit > -1:
            before = text[:foundit]
            after = text[foundit:]
            following = ""
            endit = after.find("<refsect1")
            if endit > -1:
                following = after[endit:]
                after = after[:endit]
            after = re.sub(r'<term>([^<]*)</term>', r'<term><filename>\1</filename></term>', after)
            text = before + after + following
        return text

class Pod2ManInterpreter:
    "Interpret pod2man emulation macros."
    name = "pod2man"
    exclusive = False
    toptag = "refentry"
    immutableSet = set(["Sp","Ip","Sh","Vb","Ve",])
    ignoreSet = set([])
    complainSet = set([])
    parabreakSet = set(["Sp", "Ip",])
    sectionbreakSet = set(["Sh",])
    listbreakSet = set(["Sh",])
    scopedSet = set([])
    translations = {
        "\\*" : [
        (r'\*`', "&acute;"),
        (r"\*'", "&grave;"),
        (r'\*:', "&uml;"),
        (r'\*~', "&tilde;"),
        (r'\*^', "&circ;"),
        (r'\*8', "&szlig;"),
        ],
        "\\*(" : [
        (r'\*(--',"&mdash;"),
        (r'\*(PI',"&pgr;"),
        (r'\*(L"',"&ldquo;"),
        (r'\*(R"',"&rdquo;"),
        (r'\*(C+',"C++;"),
        (r"\*(C'","'"),
        (r'\*(C`',"`"),
        (r"\*(Aq","&apos;"),
        ]
      }
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummyLine, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        # Sectioning
        if cmd == "Sp" or cmd=="Ip" and (not args or not args[0] or args[0][0] in string.digits):
            if self.source.bodySection():
                self.source.paragraph()
            elif self.source.inSynopsis():
                self.source.emit("<sbr/>")
        elif cmd == "Sh":
            self.source.pushline(quoteargs([TroffInterpreter.ctrl + "SS"] + args))
        elif cmd == "Vb":
            if self.source.bodySection():
                self.source.beginBlock("literallayout", remap="Vb")
        elif cmd == "Ve":
            if self.source.bodySection():
                self.source.endBlock("literallayout", remap="Ve")
        elif cmd == "Ip":
            if tokens[1]:
                self.source.emitVariablelist("Ip", tokens[1])
            else:
                self.source.emitItemizedlist("Ip", 'bullet')
        else:
            return False
        return True
    def preprocess(self, text):
        # Detect and strip out a pod2man header.  It does some very funky and
        # random stuff that is too hard for our troff emulation to cope with.
        # We can easily simulate the structural effect of its macros.
        # We'll emulate Sh, Sp, Ip, Vb, Ve, and provide translations for the
        # special characters \*(--, \*(PI, \*(L", \*(R", \*(C+, \*(C',
        # and \*(`.S
        lines = text.split("\n")
        starter = reCompile(r"\.[ST]H")
        while not starter.match(lines[0]):
            lines.pop(0)
            self.source.lineno += 1
        if len(lines) == 1:
            raise LiftException(self.source, "warning: empty pod2man page")
        text = "\n".join(lines)
        # Strip out junk generated by pod2man that confuses list processing
        text = text.replace("\n.RS 4\n.RE\n", '\n.\\" .RS 4\n.\\" .RE\n')
        text = re.sub(r".RS 4\n$", "", text)
        # We're done
        return text
    def postprocess(self, text):
        return text

class reStructuredTextInterpreter:
    "Interpret documents generated by reStructuredText."
    name = "reStructuredText"
    exclusive = False
    toptag = "refentry"
    immutableSet = set([])
    ignoreSet = set([])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummyLine, tokens, dummyCaller):
        cmd = tokens[0][1:]
        # Ignore indent commands for now. It's possible we might want
        # to map them to .RS/.RE later (and put INDENT in the scoped
        # set).
        if cmd == "INDENT":
            pass
        elif cmd == "UNINDENT":
            pass
        else:
            return False
        return True
    def preprocess(self, text):
        # Detect and strip out what reStructuredText wedges into the
        # NAME section. All it does is define INDENT and UNINDENT; we
        # can emulate those easily enough.
        lines = text.split("\n")
        savelines = []
        cookie = reCompile(r"nr rst2man-indent-level 0")
        starter = reCompile(r"\.SH")
        while lines and not cookie.search(lines[0]):
            savelines.append(lines.pop(0))
        if savelines:
            savelines.pop()
        if lines:
            lines.pop(0)
            while not starter.match(lines[0]):
                lines.pop(0)
        savelines += lines
        if len(savelines) == 1:
            raise LiftException(self.source, "empty reStructuredText page")
        text = "\n".join(savelines)
        return text
    def postprocess(self, text):
        return text

class DocBookInterpreter:
    "Interpret man pages generated by DocBook XSL stylesheets."
    name = "DocBook"
    exclusive = False
    toptag = "refentry"
    immutableSet = set([])
    ignoreSet = set([])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummy, tokens, dummyCaller):
        cmd = tokens[0][1:]
        # The generated inclusion defines some new commands.
        # We might want or need to interpret these sometime.
        if cmd in ("BB", "BE", "SH-xref", "BM", "EM"):
            self.source.error("uninterpreted '%s' extension command" % cmd)
        else:
            # The generated inclusion also redefines .SH and .SS for
            # better presentation, but we're interpreting them
            # structurally and can ignore that.
            return False
        return True
    def preprocess(self, text):
        # Clean up a horizontal-motion case we can handle.
        text = text.replace(r"\h'-04'\(bu\h'+03'", r"\(bu")
        # Comment out macro definitions in the stylesheet-generated inclusion.
        # Better than removing them, because line numbers won't be perturbed.
        lines = text.split("\n")
        th = reCompile(r"\.TH")
        starter = reCompile(r"(MAIN CONTENT STARTS HERE|^\.SH)")
        i = 0
        while not th.search(lines[i]):
            i += 1
        while not starter.search(lines[i]):
            if not lines[i].startswith(r'.\"'):
                lines[i] = '.\"' + lines[i]
            i += 1
        text = "\n".join(lines)
        return text
    def postprocess(self, text):
        return text

class FoojzsInterpreter:
    "Interpret man pages with Rick Richardson's foojzs profile."
    name = "foojzs"
    exclusive = False
    toptag = "refentry"
    immutableSet = set([])
    ignoreSet = set([])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummy, dummyTokens, dummyCaller):
        return False
    def preprocess(self, text):
        # Replace macro definitions in the header with blank lines.
        # Better than removing them, because line numbers won't be perturbed.
        lines = text.split("\n")
        th = reCompile(r"\.TH")
        starter = reCompile(r"\.SH")
        i = 0
        while not th.search(lines[i]):
            i += 1
        while not starter.search(lines[i]):
            if not lines[i].startswith(r'.\"'):
                lines[i] = '.\"'
            i += 1
        text = "\n".join(lines)
        return text
    def postprocess(self, text):
        return text

class XManInterpreter:
    "Interpret local macros used in X documentation."
    name = "XMan"
    exclusive = False
    toptag = "refentry"
    # Some of the X local macros (Ds, De, NT, NE, PN) are Ultrix extensions
    # already handled by ManInterpreter.
    immutableSet = set(["FD","FN","IN","ZN","hN"])
    ignoreSet = set(["IN"])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    reductions = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.source.troff.entitiesFromStrings = True
    def interpret(self, dummy, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        # .Ds and .De are already handled by ManInterpreter
        if cmd == "FD":
            # This wants to be a keep, but DocBook can't express that.
            self.source.beginBlock("literallayout", remap="FD")
        elif cmd == "FN":
            self.source.endBlock("literallayout", remap="FN")
        elif cmd == "ZN":
            self.source.pushline("<symbol role='ZN'>%s</symbol>%s" % (args[0], "".join(args[1:])))
        elif cmd == "Pn":
            self.source.pushline("%s<symbol role='Pn'>%s</symbol>%s" % (args[0], args[1], "".join(args[2:])))
        elif cmd == "hN":
            self.source.pushline("<symbol>&lt;%s&gt;</symbol>%s" % (args[0], "".join(args[1:])))
        elif cmd == "C{":
            self.source.beginBlock("programlisting", remap="C{")
        elif cmd == "C}":
            self.source.endBlock("programlisting", remap="C}")
        elif cmd == "NT":
            self.source.beginBlock("note", remap="NT")
        elif cmd == "NE":
            self.source.endBlock("note", remap="NE")
        else:
            return False
        return True
    def preprocess(self, text):
        # Detect and strip out standard X macro preamble.
        if text.find(TroffInterpreter.ctrl + "na") > -1:
            stripped = []
            lines = text.split("\n")
            while not lines[0].startswith(TroffInterpreter.ctrl + "na"):
                stripped.append(lines.pop(0))
                self.source.lineno += 1
            while not lines[0].startswith(TroffInterpreter.ctrl + "ny0"):
                lines.pop(0)
                self.source.lineno += 1
            # Eat trailing .ny0
            lines.pop(0)
            self.source.lineno += 1
            return "\n".join(stripped + lines)
        else:
            return text
    def postprocess(self, text):
        return text

class ASTInterpreter:
    "Interpret macros used in Bell Labs AST and the derived version at CERN."
    name = "AST/CERN"
    exclusive = False
    toptag = "refentry"
    immutableSet = set(["FN", "DS", "DE"])
    ignoreSet = set(["SP"])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    reductions = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.source.troff.entitiesFromStrings = True
        self.headerset = set([])
        assert self.source.interpreters[0].name == "man"
    def interpret(self, dummy, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        if cmd in ("H0", "H1", "H2", "H3", "H4"):
            self.headerset.add(cmd)
            self.source.pushSection(len(self.headerset)+1, " ".join(args))
        elif cmd == "OP":
            # Here's what we're emulating:
            #
            # .de OP
            # .nr mH 0
            # .ie !'\\$1'-' \{
            # .ds mO \\fB\\-\\$1\\fP
            # .ds mS ,\\0
            # .\}
            # .el \{
            # .ds mO \\&
            # .ds mS \\&
            # .\}
            # .ie '\\$2'-' \{
            # .if !'\\$4'-' .as mO \\0\\fI\\$4\\fP
            # .\}
            # .el \{
            # .as mO \\*(mS\\fB\\-\\-\\$2\\fP
            # .if !'\\$4'-' .as mO =\\fI\\$4\\fP
            # .\}
            # .in 5n
            # \\*(mO
            # .in 9n
            # ..
            #
            # And here's how I interpret it:
            #
            # 1. Takes exactly three or four arguments.
            #
            # 2. The first argument is interpreted as a
            # single-character option name; should be given without
            # the preceding '-', but is emitted in the resulting
            # output with a preceding '-'.
            #
            # 3. If the second and fourth arguments are '-', no
            # further output is emitted.
            #
            # 4. If the second argument is '-' but the fourth is not,
            # a space followed by the fourth argument set in italics is emitted.
            #
            # 5. If the second argument is not '-', it is omitted with
            # '--' prepended (as the name of a long option) after a
            # comma and space. Then, if the fourth argument is not
            # null, it is interpreted as a metavariable name
            # describing a long-option value and emitted in italics
            # following a '='.
            #
            # 6. The third argument is ignored and serves only as
            # documentation of the option type.
            if len(args) < 3:
                self.source.error("expected at least three arguments for .OP")
            elif len(args) < 4:
                args.append("-")
            options = ['-' + args[0]]
            if args[1] == '-':
                if args[3] != '-':
                    options[0] += " <emphasis>%s</emphasis>" % args[3]
            else:
                options.append("--" + args[1])
                if args[3] != '-':
                    options[1] += "=<emphasis>%s</emphasis>" % args[3]
            self.source.emitVariablelist("OP", options)
        elif cmd in ("SH", "SS"):
            self.headerset = set([])
            self.source.interpreters[1].interpret(dummy, tokens, dummyCaller)
        else:
            return False
        return True
    def preprocess(self, text):
        # Detect and strip out standard X macro preamble.
        if text.find(".de H0\n") == -1:
            self.source.error("AST/CERN preamble not found where expected.")
        else:
            stripped = []
            lines = text.split("\n")
            while not lines[0].startswith(TroffInterpreter.ctrl + "de H0"):
                stripped.append(lines.pop(0))
                self.source.lineno += 1
            while not lines[0].startswith(TroffInterpreter.ctrl + "SH NAME"):
                lines.pop(0)
                self.source.lineno += 1
            return "\n".join(stripped + lines)
    def postprocess(self, text):
        return text

class TkManInterpreter:
    "Interpret Tk manual emulation macros."
    name = "tkman"
    exclusive = False
    toptag = "refentry"
    immutableSet = set(["AP","AS","BS","BE","CS","CE",
                     "VS","VE","DS","DE","SO","SE","OP",
                     "UL","^B","QW","PQ"])
    ignoreSet = set([])
    complainSet = set([])
    parabreakSet = set(["AP",])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    requires = [ManInterpreter]
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummy, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        # Documentation for these is taken from the wish.1 header.
        #
	# .AP type name in/out ?indent?
	#   Start paragraph describing an argument to a library procedure.
	#   type is type of argument (int, etc.), in/out is either "in", "out",
	#   or "in/out" to describe whether procedure reads or modifies arg,
	#   and indent is equivalent to second arg of .IP (shouldn't ever be
	#   needed;  use .AS below instead)
        if cmd == "AP":
            if not self.source.bodySection(): return True
            self.source.endParagraph(label="AP")
            self.source.emit("<informaltable>\n<tgroup cols='3'>\n<tbody>\n")
            self.source.pushline(quoteargs(tokens))
            while self.source.lines:
                line = self.source.popline()
                tokens = lineparse(line)
                while len(tokens) < 4:
                    tokens.append("")
                self.source.emit("<row><entry>%s</entry><entry>%s</entry><entry>%s</entry>" % (tokens[1], tokens[2], tokens[3]))
                if tokens[1] not in cDeclarators:
                    globalhints.post(tokens[1], "type")
                gatherItem(self.source, "entry")
                self.source.emit("</row>")
                if self.source.sectionBreak(self.source.peekline()):
                    break
            self.source.emit("</tbody>\n</tgroup>\n</informaltable>\n")
	# .AS ?type? ?name?
	#   Give maximum sizes of arguments for setting tab stops.  Type and
	#   name are examples of largest possible arguments that will be passed
	#   to .AP later.  If args are omitted, default tab stops are used.
        elif cmd == "AS":
            self.source.passthrough(tokens)
	# .BS
	#   Start box enclosure.  From here until next .BE, everything will be
	#   enclosed in one large box.
        elif cmd == "BS":
            self.source.passthrough(tokens)
	# .BE
	#   End of box enclosure.
        elif cmd == "BE":
            self.source.passthrough(tokens)
	# .CS
	#   Begin code excerpt.
        elif cmd == "CS":
            self.source.beginBlock("programlisting", remap="CS")
	# .CE
	#   End code excerpt.
        elif cmd == "CE":
            self.source.endBlock("programlisting", remap="CE")
	# .VS ?version? ?br?
	#   Begin vertical sidebar, for use in marking newly-changed parts
	#   of man pages.  The first argument is ignored and used for recording
	#   the version when the .VS was added, so that the sidebars can be
	#   found and removed when they reach a certain age.  If another
	#   argument is present, then a line break is forced before starting
        #   the sidebar.
        elif cmd == "VS":
            # It's tempting to try translating this as a <sidebar>.
            # Problem is the usage pattern really is presentation-level;
            # .VS/.VE is frequently wrapped around entire major sections.
            # There are also nasty interactions with list markup.
            self.source.passthrough(tokens)
	# .VE
	#   End of vertical sidebar.
        elif cmd == "VE":
            self.source.passthrough(tokens)
	# .DS and .DE are handled by ManInterpreter
	# .SO
	#   Start of list of standard options for a Tk widget.  The
	#   options follow on successive lines, in four columns separated
	#   by tabs.
	# .SE
	#   End of list of standard options for a Tk widget.
        elif cmd == "SO":
            self.source.pushSection(1, 'STANDARD OPTIONS')
            self.source.pushline("l l l l.")
            self.source.TBL(TroffInterpreter.ctrl + "SE")
        elif cmd == "OP":
	# .OP cmdName dbName dbClass
	#   Start of description of a specific option.  cmdName gives the
	#   option's name as specified in the class command, dbName gives
	#   the option's name in the option database, and dbClass gives
	#   the option's class in the option database.
            self.source.emit("<synopsis>")
            self.source.emit("Command-Line Name:    \\fB\\%s\\fR" % args[0])
            self.source.emit("Database Name:        \\fB\\%s\\fR" % args[1])
            self.source.emit("Database Class:       \\fB\\%s\\fR" % args[2])
            self.source.emit("</synopsis>")
	# .UL arg1 arg2
	#   Print arg1 underlined, then print arg2 normally.
        elif cmd == "UL":
            self.source.pushline("<emphasis remap='U'>%s</emphasis>%s"%(args[0],args[1]))
	# .QW arg1 ?arg2?
	#   Print arg1 in quotes, then arg2 normally (for trailing punctuation).
	#
        elif cmd == "QW":
            if len(args) == 1:
                args.append("")
            self.source.emit("<quote>%s</quote>%s" % (args[0], args[1]))
	# .PQ arg1 ?arg2?
	#   Print an open parenthesis, arg1 in quotes, then arg2 normally
	#   (for trailing punctuation) and then a closing parenthesis.
        elif cmd == "PQ":
            if len(args) == 1:
                args.append("")
            self.source.emit("(<quote>%s</quote>%s)" % (args[0], args[1]))
        else:
            return False
        return True
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        return text

class MdocInterpreter:
    "Interpret mdoc(7) macros."
    name = "mdoc"
    exclusive = True
    toptag = "refentry"
    immutableSet = set([])
    ignoreSet = set(["blank", "Bk", "Ek",])
    complainSet = set(["Db",])
    parabreakSet = set(["Pp",])
    sectionbreakSet = set(["Sh", "Ss"])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {
        "\\*" : [
        (r"\*q",	'"'),
        ],
        "\\*(" : [
        (r"\*(Lq",	"&ldquo;"),	# ISOnum
        (r"\*(Rq",	"&rdquo;"),	# ISOpub
        (r"\*(Pi",	"&pgrk;"),
        (r"\*(Ne",	"&ne;"),
        (r"\*(Le",	"&le;"),
        (r"\*(Ge",	"&ge;"),
        (r"\*(Lt",	"&lt;"),
        (r"\*(Gt",	"&gt;"),
        (r"\*(Pm",	"&plusmn;"),
        (r"\*(If",	"&infin;"),
        (r"\*(Am",	"&amp;"),
        (r"\*(Na",	"NaN"),
        (r"\*(Ba",	"&verbar;"),
        (r"\*(ga",	"&grave;"),
        (r"\*(aa",	"&acute;"),
        (r"\*(ua",	"&uarr;"),
        (r"\*(ua",	"&uarr;"),
        (r"\*(&gt;=",	"&ge;"),
        (r"\*(&lt;=",	"&le;"),
        ],
        "\\*[" : [
        (r"\*[Lq]",	"&ldquo;"),	# ISOnum
        (r"\*[Rq]",	"&rdquo;"),	# ISOpub
        (r"\*[Pi]",	"&pgrk;"),
        (r"\*[Ne]",	"&ne;"),
        (r"\*[Le]",	"&le;"),
        (r"\*[Ge]",	"&ge;"),
        (r"\*[Lt]",	"&lt;"),
        (r"\*[Gt]",	"&gt;"),
        (r"\*[Pm]",	"&plusmn;"),
        (r"\*[If]",	"&infin;"),
        (r"\*[Am]",	"&amp;"),
        (r"\*[Na]",	"NaN"),
        (r"\*[Ba]",	"&verbar;"),
        (r"\*[ga]",	"&grave;"),
        (r"\*[aa]",	"&acute;"),
        (r"\*[ua]",	"&uarr;"),
        (r"\*[q]",	"'"),
        (r"\*[ua]",	"&uarr;"),
        (r"\*[&gt;=]",	"&ge;"),
        (r"\*[&lt;=]",	"&le;"),
        (r"\*[operating-system]", "BSD"),
        (r"\*[volume-operating-system]", "BSD"),
        (r"\*[volume-as-i386]", "i386"),
        (r"\*[volume-ds-1]", "1"),
        (r"\*[volume-ds-2]", "2"),
        (r"\*[volume-ds-3]", "3"),
        (r"\*[volume-ds-4]", "4"),
        (r"\*[volume-ds-5]", "5"),
        (r"\*[volume-ds-6]", "6"),
        (r"\*[volume-ds-7]", "7"),
        (r"\*[volume-ds-8]", "8"),
        (r"\*[volume-ds-9]", "9"),
        (r"\*[volume-ds-USD", "User's Supplementary Documents"),
        (r"\*[volume-ds-PS1", "Programmer's Supplementary Documents"),
        (r"\*[volume-ds-AMD", "Ancestral Manual Documents"),
        (r"\*[volume-ds-SMM", "System Manager's Manual"),
        (r"\*[volume-ds-URM", "User's Reference Manual"),
        (r"\*[volume-ds-PRM", "Programmer's Manual"),
        (r"\*[volume-ds-KM", "Kernel Manual"),
        (r"\*[volume-ds-IND", "Manual Master Index"),
        (r"\*[volume-ds-LOCAL", "Local Manual"),
        (r"\*[volume-ds-CON", "Contributed Software Manual"),
        ],
        }
    # These are listed in the order they appear on the mdoc(7) man page,
    # except for .Fl, .Nd, %N, %C, %D, %O, Lb, St, Ms, which are missing from
    # those tables. Ai and Px are not documented at all.
    # Also we have to treat Sm as parseable even through it isn't.
    parsed = set(["Ad","Ai","An","Ar","Cm","Dv","Er","Ev","Fa",
              "Fl","Ic","Lb","Li","Nd", "Ms",
              "Nm","Op","Oo","Oc","Ot","Pa","Va",
              "Vt","Xr","%A","%B","%C","%D","%J","%N","%O","%Q",
              "%R","%T","Ac","Ao","Ap","Aq","Bc","Bo","Bq",
              "Brq","Bx","Dc","Do","Dq","Ec","Em","Eo","Eq",
              "No","Mt","Ns","Pc","Pf","Po","Pq","Px","Qc",
              "Ql","Qo","Qq","Sc","Sm","So","Sq","St",
              "Sx","Sy","Ta","Tn","Ux","Xc","Xo"])
    callable = set(["Ad","Ai","An","Ar","Cm","Dv","Er","Ev",
                "Fa","Fd","Fl","Fo","Fc","Ic","Lb","Li","Ms","Nm",
                "Oc","Oo","Op","Ot","Pa","Va","Vt","Xr",
                "%B","%T","Ac","Ao","Ap","Aq","Bc","Bo",
                "Bq","Bx","Dc","Do","Dq","Ec","Em","Eo",
                "Mt","No","Ns","Pc","Po","Pq","Px","Qc","Ql",
                "Qo","Qq","Sc","So","Sq","St","Sx","Sy",
                "Ta","Tn","Ux","Xc","Xo",])
    # Substitution strings for the St request
    stDict = {
            # ANSI/ISO C
            "-ansiC-89":	"ANSI X3.159-1989 (ANSI C)",
            "-ansiC":		"ANSI X3.159-1989 (ANSI C)",
            "-isoC":		"ISO/IEC 9899:1990 (ISO C 89)",
            "-isoC-90":		"ISO/IEC 9899:1999 (ISO C 90)",
            "-isoC-99":		"ISO/IEC 9899:1999 (ISO C 99)",
            "-isoC-2011":       "ISO/IEC 9899:2011 (\"ISO C11\")",
            # POSIX Part 1: System API
            "-p1003.1":		"IEEE Std 1003.1 (POSIX.1)",
            "-p1003.1-88":	"IEEE Std 1003.1-1988 (POSIX.1)",
            "-p1003.1-90":	"IEEE Std 1003.1-1990 (POSIX.1)",
            "-iso9945-1-90":	"IEEE Std 1003.1-1990 (POSIX.1)",
            "-p1003.1b-93":	"IEEE Std 1003.1b-1993 (POSIX.1)",
            "-p1003.1c-95":	"IEEE Std 1003.1c-1995 (POSIX.1)",
            "-p1003.1i-95":	"IEEE Std 1003.1i-1995 (POSIX.1)",
            "-p1003.1-96":	"ISO/IEC 9945-1:1996 (POSIX.1)",
            "-iso9945-1-96":	"ISO/IEC 9945-1:1996 (POSIX.1)",
            "-p1003.1g-2000":	"IEEE Std 1003.1g-2000 (POSIX.1)",
            "-p1003.1-2001":	"IEEE Std 1003.1-2001 (POSIX.1)",
            "-p1003.1-2004":	"IEEE Std 1003.1-2004 (POSIX.1)",
            "-p1003.1-2008":	"IEEE Std 1003.1-2008 (POSIX.1)",

            # POSIX Part 2: Shell and Utilities
            "-p1003.2":		"IEEE Std 1003.2 (POSIX.2)",
            "-p1003.2-92":	"IEEE Std 1003.2-1992 (POSIX.2)",
            "-p1003.2a-92":	"IEEE Std 1003.2a-1992 (POSIX.2)",
            "-iso9945-2-93":	"ISO/IEC 9945-2:1993",

            # X/Open
            "-susv2":	"Version 2 of the Single UNIX Specification (SuSv2)",
            "-susv3":	"Version 3 of the Single UNIX Specification (SuSv2)",
            "-svid4":	"System V Interface Definition, Fourth Edition (SVID)",
            "-xbd5":	"X/Open System Interface Definitions Issue 5 (XBD 5)",
            "-xcu5":	"X/Open Commands and Utilities Issue 5 (XCU 5)",
            "-xcurses4.2":	"X/Open Curses Issue 4.2 (XCURSES 4.2)",
            "-xns5":		"X/Open Networking Services Issue 5 (XNS 5)",
            "-xns5.2":	"X/Open Networking Services Issue 5.2 (XNS 5.2)",
            "-xpg3":	"X/Open Portability Guide Issue 3 (XPG 3)",
            "-xpg4":	"X/Open Portability Guide Issue 4 (XPG 4)",
            "-xpg4.2":	"X/Open Portability Guide Issue 4.2 (XPG 4.2)",
            "-xsh5":	"X/Open System Interfaces and Headers Issue 5 (XSH 5)",

            # Miscellaneous
            "-ieee754":		"IEEE Std 754-1985",
            "-iso8802-3":	"ISO/IEC 8802-3:1989",
            "-iso8601":		"ISO 8601",
            }

    lbDict = {
        "libarchive":   "Reading and Writing Streaming Archives Library (libarchive, -larchive)",
        "libarm":	"ARM Architecture Library (libarm, -larm)",
        "libarm32":	"ARM32 Architecture Library (libarm32, -larm32)",
        "libbluetooth": "Bluetooth Library (libbluetooth, -lbluetooth)",
        "libbsd":	"BSD Library Functions Manual",
        "libbsm":       "Basic Security Module Library (libbsm, -lbsm)",
        "libc":		"Standard C Library (libc, -lc)",
        "libc_r":       "Reentrant C Library (libc_r, -lc_r)",
        "libcalendar":  "Calendar Arithmetic Library (libcalendar, -lcalendar)",
        "libcam":       "Common Access Method User Library (libcam, -lcam)",
        "libcdk":       "Curses Development Kit Library (libcdk, -lcdk)",
        "libcipher":    "FreeSec Crypt Library (libcipher, -lcipher)",
        "libcompat":	"Compatibility Library (libcompat, -lcompat)",
        "libcrypt":	"Crypt Library (libcrypt, -lcrypt)",
        "libcurses":	"Curses Library (libcurses, -lcurses)",
        "libdevinfo":   "Device and Resource Information Utility Library (libdevinfo, -ldevinfo)",
        "libdevstat":   "Device Statistics Library (libdevstat, -ldevstat)",
        "libdisk":      "Interface to Slice and Partition Labels Library (libdisk, -ldisk)",
        "libdwarf":     "DWARF Access Library (libdwarf, -ldwarf)",
        "libedit":	"Command Line Editor Library (libedit, -ledit)",
        "libelf":       "ELF Access Library (libelf, -lelf)",
        "libevent":     "Event Notification Library (libevent, -levent)",
        "libfetch":     "File Transfer Library for URLs (libfetch, -lfetch)",
        "libform":      "Curses Form Library (libform, -lform)",
        "libgeom":      "Userland API Library for kernel GEOM subsystem (libgeom, -lgeom)",
        "libgpib":      "General-Purpose Instrument Bus (GPIB) library (libgpib, -lgpib)",
        "libi386":	"i386 Architecture Library (libi386, -li386)",
        "libintl":      "Internationalized Message Handling Library (libintl, -lintl)",
        "libipsec":	"IPsec Policy Control Library (libipsec, -lipsec)",
        "libipx":       "IPX Address Conversion Support Library (libipx, -lipx)",
        "libiscsi":     "iSCSI protocol library (libiscsi, -liscsi)",
        "libjail":      "Jail Library (libjail, -ljail)",
        "libkiconv":    "Kernel side iconv library (libkiconv, -lkiconv)",
        "libkse":       "N:M Threading Library (libkse, -lkse)",
        "libkvm":       "Kernel Data Access Library (libkvm, -lkvm)",
        "libm":		"Math Library (libm, -lm)",
        "libmd":        "Message Digest (MD4, MD5, etc.) Support Library (libmd, -lmd)",
        "libm68k":      "m68k Architecture Library (libm68k, -lm68k)",
        "libmagic":     "Magic Number Recognition Library (libmagic, -lmagic)",
        "libmemstat":   "Kernel Memory Allocator Statistics Library (libmemstat, -lmemstat)",
        "libmenu":	"Curses Menu Library (libmenu, -lmenu)",
        "libnetgraph":  "Netgraph User Library (libnetgraph, -lnetgraph)",
        "libnetpgp":    "Netpgp signing, verification, encryption and decryption (libnetpgp, -lnetpgp)",
        "libossaudio":  "OSS Audio Emulation Library (libossaudio, -lossaudio)",
        "libpam":       "Pluggable Authentication Module Library (libpam, -lpam)",
        "libpcap":      "Packet Capture Library (libpcap, -lpcap)",
        "libpci":       "PCI Bus Access Library (libpci, -lpci)",
        "libpmc":       "Performance Counters Library (libpmc, -lpmc)",
        "libposix":	"POSIX Compatibility Library (libposix, -lposix)",
        "libprop":      "Property Container Object Library (libprop, -lprop)",
        "libpthread":   "POSIX Threads Library (libpthread, -lpthread)",
        "libpuffs":     "puffs Convenience Library (libpuffs, -lpuffs)",
        "librefuse":    "File System in Userspace Convenience Library (librefuse, -lrefuse)",
        "libresolv":    "DNS Resolver Library (libresolv, -lresolv)",
        "librpcsec_gss":"RPC GSS-API Authentication Library (librpcsec_gss, -lrpcsec_gss)",
        "librpcsvc":    "RPC Service Library (librpcsvc, -lrpcsvc)",
        "librt":        "POSIX Real-time Library (librt, -lrt)",
        "libsdp":       "Bluetooth Service Discovery Protocol User Library (libsdp, -lsdp)",
        "libssp":       "Buffer Overflow Protection Library (libssp, -lssp)",
        "libSystem":    "System Library (libSystem, -lSystem)",
        "libtermcap":	"Termcap Access Library (libtermcap, -ltermcap)",
        "libterminfo":  "Terminal Information Library (libterminfo, -lterminfo)",
        "libthr":       "1:1 Threading Library (libthr, -lthr)",
        "libufs":       "UFS File System Access Library (libufs, -lufs)",
        "libugidfw":    "File System Firewall Interface Library (libugidfw, -lugidfw)",
        "libulog":      "User Login Record Library (libulog, -lulog)",
        "libusbhid":    "USB Human Interface Devices Library (libusbhid, -lusbhid)",
        "libutil":	"System Utilities Library (libutil, -lutil)",
        "libvgl":       "Video Graphics Library (libvgl, -lvgl)",
        "libx86_64":    "x86_64 Architecture Library (libx86_64, -lx86_64)",
        "libz":		"Compression Library (libz, -lz)",
        }
    openers = set(["(", "["])
    closers = set([".", ",", "&semi;", ")", "]",])
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        # State collected by the header macros
        self.month = None	# .Dd
        self.day   = None	# .Dd
        self.year  = None	# .Dd
        self.title = None	# .Dt
        self.os    = None	# .Os
        self.name  = None	# .Nm
        self.desc  = None	# .Nd
        self.manual = ""
        self.msrc  = ""
        # Other internal state
        self.tokens    = []
        self.liststack = []
        self.bdstack = []
        self.itemcount = []
        self.suppressCallables = False
        self.spacemode = True
        self.biblio = []
        self.inref = False
        self.refnames = {}
        self.volnum = None
        self.refmetaFlushed = False
        self.stashLinkender = None
        self.rowcount = 0	# Implicit assumption that we never nest tables
    def flushRefmeta(self):
        if not self.refmetaFlushed:
            self.source.emit("<refmeta>")
            self.source.emit("<refentrytitle>%s</refentrytitle>" % self.title[0])
            self.source.emit("<manvolnum>%s</manvolnum>"%self.volnum)
            self.source.emit("</refmeta>")
            self.source.emit("")
            if self.source.docbook5:
                self.source.emit("<refnamediv xml:id='%s'>" % self.source.makeIdFromTitle('purpose'))
            else:
                self.source.emit("<refnamediv id='%s'>" % self.source.makeIdFromTitle('purpose'))
            self.source.emit("<refname>%s</refname>" % self.name)
            self.source.emit("<refpurpose>%s</refpurpose>" % self.desc)
            self.source.emit("</refnamediv>")
            self.manual = "BSD"
            self.refmetaFlushed = True
    def hasargs(self, cmd, args):
        "Check to see if there is an macro argument available."
        if not args:
            self.source.error("the %s macro requires arguments." % cmd)
            return False
        else:
            return True
    def interpret(self, dummy, tokens, dummyCaller):
        tokens[0] = tokens[0][1:]
        # First, collect any additional arguments implied by o/c enclosures.
        for c in ("A", "B", "D", "O", "P", "Q", "S", "X"):
            if c + "o" in tokens and c + "c" not in tokens:
                while True:
                    line = self.source.popline()
                    newtokens = lineparse(line)
                    #tokens.append("\n")
                    if newtokens is None:
                        tokens.append("No")
                        tokens.append(line)
                    else:
                        for fld in newtokens:
                            if fld[0] == '.':
                                tokens.append(fld[1:])
                            else:
                                tokens.append(fld)
                        if c + "c" in newtokens or "." + c + "c" in newtokens:
                            break
        # Now that we've folded ?o/?c pairs, interpret resulting command
        command = tokens[0]
        args = tokens[1:]
        # First, check parsed/callable macros
        if command in MdocInterpreter.parsed:
            self.source.pushline(self.macroeval(tokens))
        # These are only documented in mdoc.samples(7). They are rarely used.
        elif command == "Bf":
            self.source.pushline("<emphasis remap='Bf %s'>" % args[0])
        elif command == "Ef":
            self.source.pushline("</emphasis> <!-- remap='Be' -->")
        # These aren't in the parsed/callable set in mdoc(7)
        elif command == "At":
            self.source.pushline("<productname>AT&amp;T Unix</productname>")
        elif command == "Bsx":
            if args:
                bversion = " " + args[0]
            else:
                bversion = ""
            self.source.pushline("<productname>BSD/OS%s</productname>" % bversion)
        elif command == "Bt":
            self.source.emit("is currently in beta test.")
        elif command == "Cd":

            if self.source.inSynopsis():
                self.source.pushline(".br")
                self.source.pushline(" ".join(args))
                self.source.pushline(".br")
            else:
                self.source.pushline(r"\fB" + " ".join(args) + r"\fP")
        elif command == "Fx":
            if args:
                fversion = " " + args[0]
            else:
                fversion = ""
            self.source.pushline("<productname>FreeBSD%s</productname>" % fversion)
        elif command == "Nx":
            if args:
                nversion = " " + args[0]
            else:
                nversion = ""
            self.source.pushline("<productname>NetBSD%s</productname>" % nversion)
        elif command == "Ox":
            if args:
                oversion = " " + args[0]
            else:
                oversion = ""
            self.source.pushline("<productname>OpenBSD%s</productname>" % oversion)
        elif command == "Dx":
            if args:
                dversion = " " + args[0]
            else:
                dversion = ""
            self.source.pushline("<productname>DragonFly%s</productname>" % dversion)
        elif command in ("Dl", "D1"):
            if self.hasargs(command, args):
                self.source.pushline("<phrase role='%s'>%s</phrase>" % (command, self.macroeval(["No"] + args)))
        elif command == "In":
            self.source.pushline("#include &lt;%s&gt;" % args[0])
        # Ex, Fa, Fd, Fn, Rv are not in the non-parseable exception list,
        # but usage on the groff_mdoc(7) list shows they should be.
        elif command == "Ex":
            if self.hasargs("Ex", args):
                if args[0] == "-std":
                    self.source.pushline("<para>The %s utility exits 0 on success, and >0 if an error occurs.</para>" % self.name)
        elif command == "Fc":
            self.source.pushline(");")
        elif command == "Fd":
            self.source.pushline(" ".join(args))
        elif command == "Fn":
            self.source.pushline(args[0] + "(" + ", ".join(args[1:]) + ")&semi;")
        elif command == "Fo":
            self.source.pushline(args[0] + "(")
        elif command == "Ft":
            if self.hasargs("Ft", args):
                if self.source.bodySection():
                    self.source.pushline(string.join(self.encloseargs(args,
                                     "<type remap='Ft'>", "</type>")))
                else:
                    self.source.pushline(" ".join(args))	# Feed the parser
        elif command == "Rv":
            if self.hasargs("Rv", args):
                if args[0] == "-std":
                    self.source.pushline("The %s() function returns the value 0 if successful; otherwise the value -1 is returned and the global variable errno is set to indicate the error." % args[1])
        # Hyperlinks
        elif command == "UE":
            if not self.stashLinkender:
                self.source.error(".UE with no preceding .UR")
            else:
                self.source.emit(self.stashLinkender)
        elif command == "UN":
            if self.source.docbook5:
                self.source.pushline("<anchor xml:id='%s'>" % self.source.makeIdFromTitle(args[0]))
            else:
                self.source.pushline("<anchor id='%s'>" % self.source.makeIdFromTitle(args[0]))
        elif command == "UR":
            if args[0][0] != "#":
                self.source.pushline("<ulink url='%s'>" % self.source.idFromTitle(args[0]))
                self.stashLinkender = "</ulink>"
            else:
                self.source.pushline("<link linkend='%s'>" % self.source.idFromTitle(args[0][1:]))
                self.stashLinkender = "</link>"
        # Structure requests
        elif command == "Dd":
            if args[0] == "$Mdocdate$":
                args.pop(0)
            else:
                # acpiFakekey.1 has an ISO date that doesn't conform to mdoc.
                if re.compile("[0-9]+-[0-9]+-[0-9]+").search(args[0]):
                    (self.year, self.month, self.day) = args[0].split("-")
                # synctex.1 does this - might happen elsewhere
                elif re.compile("[0-9]+/[0-9]+/[0-9]+").search(args[0]):
                    (self.day, self.month, self.year) = args[0].split("/")
                else:
                    (self.month, self.day, self.year) = args[:3]
                if len(self.year) == 2:
                    thisyear = int(time.strftime("%Y", time.localtime(int(time.time()))))
                    if thisyear > 2069:
                        self.source.warning("unresolvable two-digit year in .Dd macro.")
                    else:
                        low2 = int(self.year)
                        if low2 >= 70:
                            self.year = str(1900 + low2)
                        else:
                            self.year = str(2000 + low2)
                self.day = self.day[:-1]
        elif command == "Dt":
            self.title = args
            self.volnum = args[1]
        elif command == "Lk":
             self.source.pushline("<ulink url='%s'>%s</ulink>" % (args[0], args[1]))
        elif command == "Os":
            if args:
                self.os = args
            else:
                self.os = "BSD"
        elif command == "Sh":
            self.source.diversion = self.source.output
            if not args:
                args = self.source.popline().split()
            if nameSynonyms.match(args[0]):
                self.source.sectname = "Name"
                # Copes with lines that are blank or a dot only (groff_mdoc...)
                while self.source.peekline() in ("", TroffInterpreter.ctrl, TroffInterpreter.ctrlNobreak):
                    self.source.popline()
                # Kluge -- it turns out that some web pages (like ash.1)
                # don't use the mandoc macros.  Instead they use a Linux-
                # style "NAME - description" header.  Test for this.
                line = self.source.popline()
                if isCommand(line):
                    # Macros will handle it
                    self.source.pushline(line)
                else:
                    # Parse it explicitly.
                    (self.name, self.desc) = parseNameSection(line)
            else:
                self.flushRefmeta()
                if synopsisLabel.search(args[0]):
                    self.source.endParagraph()
                    self.source.sectname = "Synopsis"
                    self.source.synopsis = DisplayParser(self.source,
                                                         True,
                                                         False,
                                                         self.refnames)
                    self.source.sectionhooks.append(self.source.flushTransplant)
                    return True	# Declaration macros will do the work
                elif not self.source.synopsis and self.source.find(synopsisHeader):
                    if sectionVerbosity in self.source.verbose:
                        self.source.notify("transplanting section...")
                    self.source.diversion = self.source.transplant
                    self.source.pushSection(1, " ".join(args))
                else:
                    self.flushRefmeta()
                    self.source.declareBodyStart()
                    # in case someone forgets to close a list (see mktemp.1).
                    for _ in self.liststack:
                        self.source.pushline(TroffInterpreter.ctrl + "El")
                    self.source.pushSection(1, " ".join(args))
        elif command == "Ss":
            self.source.diversion = self.source.output
            # in case someone forgets to close a list
            for _ in self.liststack:
                self.source.pushline(TroffInterpreter.ctrl + "El")
            self.source.pushSection(2, " ".join(args))
        elif command == "Pp":
            if self.source.bodySection():
                self.source.paragraph()
            else:
                self.source.emit("<sbr/>")
        elif command == "Bd":
            # Possible args are:
            # -ragged = left-justify only (treat as blockquote)
            # -centered = center (we throw a warning)
            # -unfilled = don't fill (we map this to literallayout)
            # -filled = fill normally (treat as blockquote)
            # -literal = no fill, use constant width (map to programlisting)
            # -file = insert file (throw a warning)
            # -offset = set indent (we ignore this)
            # -compact = Suppress vertical space before display (we ignore this)
            if "-centered" in args or "-file" in args:
                self.source.warning("can't process -center or -file in .Bd")
            enclosuretype = None
            if self.source.peekline() and self.source.peekline()[0:3] == TroffInterpreter.ctrl + "Bl":
                enclosuretype = None
            elif '-ragged' in args or '-filled' in args:
                enclosuretype = "blockquote"
            elif '-unfilled' in args:
                enclosuretype = 'literallayout'
                self.source.beginBlock("literallayout", remap="Bd")
            elif '-literal' in args:
                enclosuretype = 'programlisting'
                self.source.beginBlock("programlisting", remap="Bd")
            self.bdstack.append(enclosuretype)
        elif command == "Ed":
            dtype = self.bdstack.pop()
            if dtype == 'blockquote':
                self.source.poplist("Bd", remap="Ed (list)")
            elif dtype is not None:
                self.source.endBlock(dtype, remap="Ed (block)")
            self.source.needParagraph()
        # List markup
        elif command == "Bl":
            header = " ".join(tokens)
            # There may  be leading text here that's not part of an item
            # (as in ash(1)).  Pass it through before emitting the list header.
            while True:
                nextl = self.source.popline()
                if matchCommand(nextl, "It"):
                    self.source.pushline(nextl)
                    break
                else:
                    self.source.interpretBlock([nextl])
            self.source.endParagraph(label="Bl")
            hasbodies = xoskip = False
            depth = 1
            for future in self.source.lines:
                if matchCommand(future, "El"):
                    depth -= 1
                    if depth == 0:
                        break
                elif matchCommand(future, "Bl"):
                    depth += 1
                nextl = future.strip()
                if isComment(nextl):
                    continue
                elif 'Xo' in nextl:
                    xoskip = True
                elif matchCommand("Xc", nextl):
                    xoskip = False
                if not xoskip and not matchCommand(nextl, "It"):
                    hasbodies = True
            if bsdVerbosity in self.source.verbose:
                self.source.notify("%s has bodies? %s" % (header, hasbodies))
            self.itemcount.append(0)
            if "-column" in tokens[1:]:
                self.source.emit("<table remap=%s><title></title>"% repr(header))
                self.liststack.append("</table>")
                self.rowcount = 0
            elif not hasbodies:
                self.source.emit("<itemizedlist remap='%s'> <!-- no bodies -->" % header)
                self.liststack.append("</itemizedlist>")
            elif "-bullet" in tokens[1:]:
                self.source.emit("<itemizedlist remap='%s' mark='bullet'>" % header)
                self.liststack.append("</itemizedlist>")
            elif "-dash" in tokens[1:] or "-hyphen" in tokens[1:]:
                # See the comment near ipTagMapping
                self.source.emit("<itemizedlist remap=%s mark='box'>" % repr(header))
                self.liststack.append("</itemizedlist>")
            elif "-item" in tokens[1:]:
                self.source.emit("<itemizedlist remap=%s>"% repr(header))
                self.liststack.append("</itemizedlist>")
            elif "-enum" in tokens[1:]:
                self.source.emit("<orderedlist remap=%s>" % repr(header))
                self.liststack.append("</orderedlist>")
            elif "-tag" in tokens[1:]:
                self.source.emit("<variablelist remap=%s>"% repr(header))
                self.liststack.append("</variablelist>")
            elif "-diag" in tokens[1:]:
                self.source.emit("<variablelist remap=%s>"% repr(header))
                self.liststack.append("</variablelist>")
                self.suppressCallables = True
            elif "-hang" in tokens[1:]:
                self.source.emit("<variablelist remap=%s>"% repr(header))
                self.liststack.append("</variablelist>")
            elif "-ohang" in tokens[1:]:
                self.source.emit("<variablelist remap=%s>"% repr(header))
                self.liststack.append("</variablelist>")
            elif "-inset" in tokens[1:]:
                self.source.emit("<variablelist remap=%s>"% repr(header))
                self.liststack.append("</variablelist>")
        elif command == "It":
            if self.liststack[-1] == "</table>":
                # Columns into tables
                segments = [[]]
                for fld in args:
                    if fld == "Ta":
                        segments.append([])
                    else:
                        segments[-1].append(fld)
                for (i, seg) in enumerate(segments):
                    if seg[0] in MdocInterpreter.callable:
                        segments[i] = self.macroeval(seg)
                    else:
                        segments[i] = " ".join(segments[i])
                self.rowcount += 1
                if self.rowcount == 1:
                    self.source.emit("<tgroup cols='%d'><tbody>" % len(args))
                self.source.emit("    <row>")
                for seg in segments:
                    self.source.emit("      <entry>%s</entry>" % fontclose(seg))
                self.source.emit("    </row>")
            else:
                # Otherwise we may have to close a previous entry
                if args:
                    tagline = self.macroeval(["No"] + args)
                else:
                    tagline = ""
                if self.itemcount[-1]:
                    self.source.endParagraph(label="It")
                    self.source.emit("</listitem>")
                    if self.liststack[-1] == "</variablelist>":
                        self.source.emit("</varlistentry>")
                self.itemcount[-1] += 1
                termlines = [tagline]
                while True:
                    nextl = self.source.popline()
                    if matchCommand(nextl, "It"):
                        digested = lineparse(nextl)
                        digested = self.macroeval(["No"] + digested[1:])
                        termlines.append(digested)
                    else:
                        self.source.pushline(nextl)
                        break
                # We certainly have to open a new entry.
                if self.liststack[-1] == "</variablelist>":
                    self.source.emit("<varlistentry>")
                    self.source.emit("<term>%s</term>" % fontclose("</term>\n<term>\n".join(termlines)))
                    self.source.emit("<listitem>")
                elif self.liststack[-1] == "</itemizedlist>":
                    body = "\n".join(termlines)
                    if body:
                        self.source.emit("<listitem><para>%s</para></listitem>" % body)
                    else:
                        self.source.emit("<listitem>")
                elif self.liststack[-1] == "</orderedlist>":
                    self.source.emit("<listitem>")
                self.source.needParagraph()
        elif command == "El":
            if self.liststack[-1] == "</table>":
                self.source.emit("  </tbody></tgroup>")
            else:
                self.source.endParagraph(label="El")
                if self.liststack[-1] == "</variablelist>":
                    self.source.emit("</listitem>")
                    self.source.emit("</varlistentry>")
                elif self.liststack[-1] == "</orderedlist>":
                    self.source.emit("</listitem>")
                elif self.liststack[-1] == "</itemizedlist>":
                    if not self.source.endswith("</listitem>"):
                        self.source.emit("</listitem>")
            self.source.emit(self.liststack.pop())
            self.itemcount.pop()
            self.source.needParagraph()
        elif command == "Rs":
            self.biblio.append({})
            self.biblio[-1]["id"] = repr(len(self.biblio))
            self.inref = True
        elif command == "Re":
            self.inref = False
            if self.source.output[-1] == "</variablelist>":
                self.source.output = self.source.output[:-1]
            else:
                self.source.endParagraph(label="Re")
                self.source.emit("<variablelist>")
            # We'd like to emit a <bibliography> here, but the DocBook DTD
            # doesn't permit it.
            if self.source.docbook5:
                self.source.emit("<varlistentry xml:id='%s'>" % self.source.makeIdFromTitle("ref" + repr(len(self.biblio))))
            else:
                self.source.emit("<varlistentry id='%s'>" % self.source.makeIdFromTitle("ref" + repr(len(self.biblio))))
            self.source.emit("<term>[%s]</term>" % len(self.biblio))
            self.source.emit("<listitem><para>")
            for (fld, tag) in ( \
                ("A", None), \
                ("Q", None), \
                ("B", "citetitle"), \
                ("V", None), \
                ("J", None), \
                ("N", None), \
                ("P", None), \
                ("R", None), \
                ("T", "citetitle"), \
                ("D", None), \
                ("I", None), \
                ("C", None), \
                ("O", None), \
                ):
                if fld in self.biblio[-1]:
                    line = ""
                    if tag:
                        line += "<%s>" % tag
                    line += ", ".join(self.biblio[-1][fld])
                    if tag:
                        line += "</%s>" % tag
                    line += ";"
                    self.source.emit(line)
            self.source.emit("</para></listitem>")
            self.source.emit("</varlistentry>\n")
            self.source.emit("</variablelist>\n")
        # Not documented, but present in the macro files
        elif command == "Ud":
            self.source.pushline("currently under development")
        else:
            return False
        return True
    # Machinery for evaluating parsed macros begins here
    def evalmacro(self, args):
        "Pop args off the stack and evaluate any associated macro."
        if bsdVerbosity in self.source.verbose:
            self.source.notify("evalmacro(%s)" % ", ".join(map(repr, args)))
        cmd = args.pop(0)
        if cmd in self.ignoreSet:	# In case we get keeps with .Oo/Oc
            while True:
                end = args.pop(0)
                if end == '\n':
                    break
            return ""
        elif cmd == "Ad":
            # We don't care.  We're translating it...
            #self.source.warning("the Ad macro is deprecated.")
            return self.encloseargs(args,"<phrase role='address'>","</phrase>")
        elif cmd == "Ai":
            return ["<acronym>ANSI</acronym>"]
        elif cmd == "An":
            if self.hasargs("An", args):
                return self.encloseargs(args, "phrase", "role='author'")
        elif cmd == "Ap":
            return self.replacemacro(args, "'@GLUE@")
        elif cmd == "Aq":
            return self.encloseargs(args, "&lt;@GLUE@", "@GLUE@&gt;")
        elif cmd == "Ac":
            return self.replacemacro(args, "@GLUE@&gt;")
        elif cmd == "Ao":
            return self.replacemacro(args, "&lt;@GLUE@")
        elif cmd == "Ar":
            if not args:
                return ["<replaceable>file...</replaceable>"]
            else:
                return self.styleargs(args, "replaceable")
        elif cmd == "At":
            return ["<productname>AT&T Unix</productname>"]
        elif cmd == "Bc":
            return self.replacemacro(args, "@GLUE@]")
        elif cmd == "Bo":
            return self.replacemacro(args, "[@GLUE@")
        elif cmd == "Bq":
            return self.encloseargs(args, "[@GLUE@", "@GLUE@]")
        elif cmd == "Brq":
            return self.encloseargs(args, "{@GLUE@", "@GLUE@}")
        elif cmd == "Bx":
            def bxhelper(args):
                if not args:
                    return ["BSD UNIX"]
                else:
                    return ["-".join(["%sBSD" % args[0]] + args[1:])]
            return self.processPunct(args, bxhelper, True)
        elif cmd == "Cm":
            if self.hasargs("Cm", args):
                return self.styleargs(args, "command")
        elif cmd == "Dc":
            return self.replacemacro(args, "@GLUE@&rdquo;")
        elif cmd == "Do":
            return self.replacemacro(args, "&ldquo;@GLUE@")
        elif cmd == "Dq":
            return  self.encloseargs(args, "&ldquo;@GLUE@", "@GLUE@&rdquo;")
        elif cmd == "Dv":
            if self.hasargs("Dv", args):
                return self.styleargs(args, "constant")
        elif cmd == "Em":
            if self.hasargs("Em", args):
                return self.styleargs(args, "emphasis", "remap='Em'")
        elif cmd == "Eq":
            return  self.encloseargs(args[2:],
                                     args[0]+"@GLUE@", "@GLUE@&"+args[1])
        elif cmd == "Er":
            if self.hasargs("Er", args):
                return self.styleargs(args, "errorcode")
        elif cmd == "Ev":
            if self.hasargs("Ev", args):
                return self.styleargs(args, "envar")
        elif cmd == "Fa":
            if self.source.inSynopsis():
                return [x+"," for x in self.processPunct(args)]
            else:
                return self.styleargs(args, "emphasis", "remap='Fa'")
        elif cmd == "Fl":
            if not args:
                return ["-"]
            else:
                dashes = '-'
                while args and args[0] == 'Fl':
                    dashes += '-'
                    args.pop(0)
                if args:
                    args[0] = dashes + args[0]
                else:
                    args = [dashes]
                return self.styleargs(args, "option", "", "")
        elif cmd == "Ic":
            if self.hasargs("Ic", args):
                return self.styleargs(args, "command", "remap='Ic'")
        elif cmd == "Lb":
            return self.processPunct(args, self.lbhook, True)
        elif cmd == "Li":
            return self.styleargs(args, "literal")
        elif cmd == "Ms":
            return self.styleargs(args,"literal")
        elif cmd == "Mt":
            return self.encloseargs(args,"<email>","</email>")
        elif cmd == "Nd":
            savesect = [" ".join(self.encloseargs(args, "", ""))]
            while True:
                line = self.source.popline()
                if matchCommand(line, "Sh"):
                    self.source.pushline(line)
                    break
                else:
                    savesect.append(line)
            lines = []
            self.source.interpretBlock(savesect, lines)
            self.desc = " ".join(lines)
            if not self.source.bodySection():
                return []
            else:
                return self.desc
        elif cmd == "Nm":
            name = " ".join(self.encloseargs(args, "", ""))
            if not self.name:
                self.name = name
            self.refnames[name] = True
            if self.source.sectname and nameSynonyms.match(self.source.sectname):
                return []
            else:
                if not name:
                    name = self.name
                return ["<command remap='Nm'>%s</command>" % self.name]
        elif cmd == "No":
            return self.replacemacro(args, "")
        elif cmd == "Ns":
            return self.replacemacro(args, "@GLUE@")
        elif cmd == "Oc":
            return self.replacemacro(args, "@GLUE@]")
        elif cmd == "Oo":
            return self.replacemacro(args, "[@GLUE@")
        elif cmd == "Op":
            return self.styleargs(args, ("[@GLUE@", "@GLUE@]"))
        elif cmd == "Pa":
            if self.source.inSynopsis():
                return self.styleargs(args, "replaceable")
            else:
                return self.styleargs(args, "filename")
        elif cmd == "Pc":
            return self.replacemacro(args, "@GLUE@)")
        elif cmd == "Pf":
            # We don't want punctuation processing here
            operands = []
            while args:
                if args[0] in MdocInterpreter.callable:
                    break
                this = args.pop(0)
                operands.append(this)
                if this == '\n':
                    break
            if len(operands) > 1:
                return [operands[0],"@GLUE@"] + operands[1:]
            else:
                return [operands[0],"@GLUE@"]
        elif cmd == "Po":
            return self.replacemacro(args, "(@GLUE@")
        elif cmd == "Pq":
            return self.encloseargs(args, "(@GLUE@", "@GLUE@)")
        elif cmd == "Px":
            return ["<acronym>POSIX</acronym>"]
        elif cmd == "Ql":
            return self.encloseargs(args, "'", "'")
        elif cmd == "Qc":
            return self.replacemacro(args, "@GLUE@\"")
        elif cmd == "Qo":
            return self.replacemacro(args, "\"@GLUE@")
        elif cmd == "Qq":
            return self.encloseargs(args, '"@GLUE@', '@GLUE@"')
        elif cmd == "Sc":
            return self.replacemacro(args, "@GLUE@\'")
        elif cmd == "So":
            return self.replacemacro(args, "\'@GLUE@")
        elif cmd == "Sq":
            return self.encloseargs(args, "`@GLUE@", "@GLUE@\'")
        elif cmd == "St":
            return self.processPunct(args, self.sthook, True)
        elif cmd == "Sx":
            #title = " ".join(args)
            return self.processPunct(args, lambda x: ["<link role='Sx' linkend='%s'>%s</link>" % (self.source.idFromTitle(" ".join(x)), " ".join(x))], False)
        elif cmd == "Sy":
            return self.styleargs(args, "emphasis", 'remap="Sy"')
        elif cmd == "Ta":
            return self.replacemacro(args, "\t")
        elif cmd == "Tn":
            # We used to set this with an acronym tag, following an older
            # version of the mdoc manual, but that won't work - among
            # other things, groff_mdoc(7) uses it at presentation level
            # to set contents items in small caps.
            return self.styleargs(args, "phrase", "remap='Tn'")
        elif cmd == "Ux":
            return ["<productname>Unix</productname>"]
        elif cmd == "Va":
            return self.styleargs(args, "varname")
        elif cmd == "Vt":
            return self.styleargs(args, "type")
        elif cmd == "Xc":
            return self.replacemacro(args, "")
        elif cmd == "Xo":
            return self.replacemacro(args, "")
        elif cmd == "Xr":
            return self.processPunct(args, self.xrhook, False)
        elif cmd[0] == "%":
            lst = self.processPunct(args, lambda x: self.bibliohook(cmd[1], x), True)
            if self.inref:
                return []
            else:
                return lst
        # Sm is not officially parseable, but we have to treat it that way
        # in order for it to work inside Oo/Oc pairs (as in slogin.1).
        elif cmd == "Sm":
            enable = self.extractargs(args)
            if "on" in enable:
                self.spacemode = True
            elif "off" in enable:
                self.spacemode = False
            else:
                self.source.error("unknown argument to Sm")
            return []
        else:
            self.source.error("unknown parseable macro " + repr(cmd))
            return []
    def bibliohook(self, field, lst):
        ref = " ".join(lst)
        if self.inref:
            # If we're within the scope of an Rs/Re, accumulate entry.
            if field not in self.biblio[-1]:
                self.biblio[-1][field] = []
            self.biblio[-1][field].append(ref)
        # Unresolved titles can simply turn into a title citation
        if field == "T":
            return ["<citetitle>%s</citetitle>" % (ref)]
        # Otherwise return the reference.
        else:
            for entry in self.biblio:
                if field in entry and ref in entry[field]:
                    return ["<link linkend='ref%s'>[%s]</link>" % (entry["id"], entry["id"])]
            else:
                raise LiftException(self.source, "unresolved reference to '%s'" % ref)
    def sthook(self, args):
        if args[0] in MdocInterpreter.stDict:
            return["<citetitle>" + MdocInterpreter.stDict[args[0]] + "</citetitle>"]
        else:
            raise LiftException(self.source, "unknown St macro '%s'" % args[0])
    def lbhook(self, args):
        if args[0] in MdocInterpreter.lbDict:
            return["<citetitle>" + MdocInterpreter.lbDict[args[0]] + "</citetitle>"]
        else:
            raise LiftException(self.source, "unknown Lb macro '%s'" % args[0])
    def xrhook(self, args):
        if len(args) < 2:
            return ["<citerefentry><refentrytitle>%s</refentrytitle></citerefentry>" % args[0]]
        else:
            return ["<citerefentry><refentrytitle>%s</refentrytitle><manvolnum>%s</manvolnum></citerefentry>" % (args[0], args[1])]
    def extractargs(self, args, stopOnCallable=0):
        operands = []
        while args:
            if stopOnCallable and args[0] in MdocInterpreter.callable:
                break
            this = args.pop(0)
            operands.append(this)
            if this == '\n':
                break
        return operands
    def processPunct(self, args, hook=None, stopOnCallable=False):
        "Wrap required processing of punctuation around an evaluation."
        prepunct = []
        postpunct = []
        # Save leading punctuation
        while args and args[0] in MdocInterpreter.openers:
            prepunct.append(args.pop(0))
        while args and args[-1] in MdocInterpreter.closers:
            postpunct = [args.pop()] + postpunct
        operands = []
        while args:
            if stopOnCallable and args[0] in MdocInterpreter.callable:
                break
            this = args.pop(0)
            operands.append(this)
            if this == '\n':
                break
        if hook:
            operands = prepunct + hook(operands) + postpunct
        else:
            operands = prepunct + operands + postpunct
        result = []
        for arg in operands:
            if arg in MdocInterpreter.closers:
                result.append("@GLUE@" + arg)
            elif arg in MdocInterpreter.openers:
                result.append(arg + "@GLUE@")
            else:
                result.append(arg)
        return result
    def encloseargs(self, args, opener, closer):
        "Grab and process arguments for an enclosure macro."
        return self.processPunct(args, lambda x: [opener] + x + [closer], False)
    def stylehook(self, args, tag, attr, dummyPrefix):
        "Wrap non-punctuation characters in given tag pair."
        result = []
        if attr:
            attr = " " + attr
        if len(tag) == 2:
            start = tag[0] + attr
            end = tag[1]
        else:
            start = "<" + tag + attr + ">"
            end =  "</" + tag + ">"
        for arg in args:
            if arg == "|" or arg in self.openers or arg in self.closers:
                result.append(arg)
            else:
                result.append(start + arg + end)
        return result
    def styleargs(self, args, tag, attribute="", prefix=""):
        return self.processPunct(args, lambda x: self.stylehook(x, tag, attribute, prefix), 1)
    def replacemacro(self, args, withmac):
        return self.processPunct(args, lambda x: [withmac] + x, 1)
    def macroeval(self, args):
        "Evaluate a macro, returning a list."
        if bsdVerbosity in self.source.verbose:
            self.source.notify("macroeval%s\n" % (tuple(args),))

        if args[0][0] == '.':
            args[0] = args[0][1:]
        # Consume arguments and macro calls until none are left
        result = []
        while args:
            nextpart = [x for x in self.evalmacro(args) if x]
            if not self.spacemode and len(nextpart) > 1:
                for ind in range(len(nextpart)):
                    nextpart.insert(2*ind+1, "@GLUE@")
            if bsdVerbosity in self.source.verbose:
                self.source.notify("evalmacro -> %s" % nextpart)
            result += nextpart
        # Glue the results together
        result = " ".join(result)
        result = hotglue.sub("", result)
        result = cleantag.sub("", result)
        if bsdVerbosity in self.source.verbose:
            self.source.notify("macroeval -> %s\n" % repr(result))
        return result
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        # It's not an error for Sx references to point elsewhere
        linkRe = reCompile("<link role='Sx' linkend='([A-Za-z_]*)'>([A-Za-z_]*)</link>")
        while True:
            m = linkRe.search(text)
            if m:
                linkstart =  m.start(0)
                linkend =  m.end(0)
                mid = m.group(1)
                label = m.group(2)
                if self.source.idExists(mid):
                    text = text[:linkstart+6] + text[linkstart+15:]
                else:
                    self.source.warning("unresolved Sx label %s" % label)
                    text = text[:linkstart] + \
                           "<emphasis role='Sx'>%s</emphasis>" % label + \
                           text[linkend:]
            else:
                break
        # Ugh...this can be produced by ,It .Xo/Xc; there's an example on
        # groff_mdoc(7).
        text = text.replace("<listitem>\n</listitem>", "")
        # Sanity check
        if not self.source.sectionCount:
            raise LiftException(self.source, "no mdoc section structure, can't be lifted.")
        return text

class MsInterpreter:
    "Interpret ms(7) macros."
    name = "ms"
    exclusive = True
    toptag = "article"
    immutableSet = set([])
    ignoreSet = set([
        # Ignore presentation-level-only requests from Bell Labs.
        "RP", "ND", "DA", "1C", "2C", "MC",
        "BX", "KS", "KE", "KF",
        # Also ignore the Berkeley thesis-mode extension
        "TM", "CT", "XS", "XE", "XA", "PX", "AM",
        "EH", "OH", "EF", "OF",
        # These are not documented in the ms reference, but
        # they occur in ms papers, probably as relics from mm.
        "MH", "CS", "D3"
        ])
    complainSet = set(["RS", "RE",])
    parabreakSet = set(["blank","PP", "LP", "XP", "IP",])
    sectionbreakSet = set(["NH", "SH", "SC",])
    listbreakSet = set(["PP", "LP", "XP", "NH", "SH", "SC",])
    scopedSet = set([])
    translations = {
        "\\*" : [
        # The Bell Labs prefix diacriticals
        (r"\*'", "&acute;"),
        (r"\*`", "&grave;"),
        (r"\*:", "&uml;"),
        (r"\*^", "&circ;"),
        (r"\*~", "&tilde;"),
        (r"\*C", "&caron;"),
        (r"\*,", "&cedil;"),
        # Berkeley extensions
        #(r"\**(_", "&mdash;"),	# Input text was "\e\(**\^\u_\d" in original
        (r"\**(Q", "&ldquo;"),
        (r"\**(U", "&rdquo;"),
        # Berkeley postscript diacriticals
        (r"\**('", "&grave;"),
        (r"\**(`", "&acute;"),
        (r"\**(^", "&circ;"),
        (r"\**(,", "&cedil;"),
        (r"\**(?", "&iquest;"),
        (r"\**(!", "&iexcl;"),
        (r"\**(v", "&caron;"),
        (r"\**(_", "&macr;"),
        (r"\**.",  "&udot;"),	# Internal pseudo-entity
        (r"\**/",  "&oslash;"),
        (r"\**o",  "&Aring;"),
        (r"\**(3t", "&yogh;"),	# Internal pseudo-entity
        (r"\**(Th", "&THORN;"),
        (r"\**(th", "&thorn;"),
        (r"\**(D-", "&ETH;"),
        (r"\**(d-", "&eth;"),
        (r"\**q",   "&ohook;"),	# Internal pseudo-entity
        (r"\**(ae", "&aelig;"),
        (r"\**(Ae", "&AElig;"),
        (r"\**(oe", "&oelig;"),
        (r"\**(Oe", "&Oelig;"),
        ]
        }
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.font = "R"
        self.pointsize = 0
        self.fmt = "R"
        self.author = Author()
        self.TL = None
        self.AU = None
        self.AI = []
        self.AB = None
        self.flushed = False
    def interpret(self, dummy, tokens, caller):
        command = tokens[0][1:]
        args = tokens[1:]
        if command in ("B", "I", "R", "UL", "SM", "LG", "NL"):
            # Get our remap attribute in sync with other macro sets.
            if command == "UL":
                command="U"
            # Could be a change along either axis
            newpointsize = self.pointsize
            newfont = self.font
            if command == "NL":
                newpointsize = 0
            elif command == "LG":
                newpointsize += 1
            elif command == "SM":
                newpointsize += -1
            else:
                newfont = command
            # If no actual change (as with two successive .NLs), we're done.
            if self.font == newfont and self.pointsize == newpointsize:
                return True
            if newpointsize == 0:
                fmt = newfont
            else:
                fmt = newfont + repr(newpointsize)
            if self.fmt == "R":
                if not args:
                    self.source.emit(r"\f%s" % fmt)
                else:
                    self.source.emit(r"\f%s%s\fP" % (fmt, args[0]))
            elif fmt == "R":
                if not args:
                    self.source.emit(r"\fP")
                else:
                    self.source.emit(r"\fP%s\f%s" % (args[0], self.fmt))
            if not args:
                self.font = newfont
                self.pointsize = newpointsize
                self.fmt = fmt
            return True
        elif command == "B1":
            self.source.emit(r"<sidebar>")
        elif command == "B2":
            self.source.emit(r"</sidebar>")
        # Commands for front matter
        elif command == "TL":
            self.source.declareBodyStart()
            self.TL = gatherLines(self.source)
            return True
        elif command == "OK":	# Undocumented -- probably some Bell Labs thing
            gatherLines(self.source)
            return True
        elif command == "AU":
            self.AU = gatherLines(self.source)
            return True
        elif command == "AI":
            self.AI = gatherLines(self.source)
            return True
        elif command == "AB":
            self.AB = []
            while self.source.lines:
                line = self.source.popline()
                tokens = lineparse(line)
                if tokens and tokens[0][1:3] == "AE":
                    break
                if not (isCommand(line) and self.source.ignorable(line)):
                    self.AB.append(line)
            return True
        # Here's where we analyze the front matter and generate the header
        if not self.flushed:
            self.source.inPreamble = False
            if ioVerbosity in self.source.verbose:
                self.source.notify("exiting preamble")
            self.flushed = True
            # If there's only one line of authors, try to break it up by
            # looking for " and ".  There are a couple of historical examples
            # of this, notably in the EQN docs.
            if self.AU:
                if len(self.AU) == 1:
                    trial = self.AU[0].split(" and ")
                    if trial > 1:
                        self.AU = trial
                    else:
                        # We'll also try splitting on commas
                        trial = self.AU[0].split(", ")
                        if trial > 1:
                            self.AU = trial
                # Now we have one author per line.  Try to analyze each name.
                digested = []
                for name in self.AU:
                    author = Author(name)
                    if self.AI:
                        author.orgname = " ".join(self.AI)
                    digested.append(author)
            # OK, we've got enough info to generate the header
            if self.TL or self.AU or self.AI or self.AB:
                self.source.endParagraph(label="ms header")
                self.source.emit("<articleinfo>")
                if self.TL:
                    self.source.emit("<title>")
                    caller.interpretBlock(self.TL)
                    self.source.emit("</title>")
                for self.author in digested:
                    if self.author.nonempty():
                        self.source.emit(repr(author))
                if self.AB:
                    self.source.emit("<abstract>")
                    self.source.needParagraph()
                    caller.interpretBlock(self.AB)
                    self.source.endParagraph(label="AB")
                    self.source.emit("</abstract>")
                self.source.emit("</articleinfo>")
        if command in ("blank","PP","LP","XP") or command == "IP" and len(tokens) == 1:
            self.source.paragraph()
        elif command in ("NH", "SH"):
            title = self.source.popline()
            try:
                newdepth = int(tokens[1])
            except ValueError:
                newdepth = 1
            self.source.pushSection(newdepth, title)
        elif command == "IP":
            # If no tag is specified, treat as ordinary paragraph.
            self.source.endParagraph(label="IP")
            # Some tags can turn into an itemized list.
            if tokens[1] in ipTagMapping:
                self.source.pushline(quoteargs(tokens))
                gatherItemizedlist(TroffInterpreter.ctrl + "IP", self.source,
                                    ipTagMapping[tokens[1]])
            # Otherwise, emit a variable list
            else:
                self.source.emitVariablelist(command, tokens[1])
        elif command == "QP":
            self.source.beginBlock("blockquote", remap="QP")
            while self.source.lines:
                line = self.source.popline()
                if isCommand(line):
                    self.source.pushline(line)
                    break
                self.source.emit(line)
            self.source.endBlock("blockquote", remap="QE")
        elif command == "DS":
            self.source.beginBlock("literallayout", remap='DS')
        elif command == "DE":
            self.source.endBlock("literallayout", remap='DE')
        elif command == "FS":
            self.source.beginBlock("footnote", remap='FS')
        elif command == "FE":
            self.source.endBlock("footnote", remap='FE')
        elif command == "QS":
            self.source.beginBlock("blockquote", remap='QS')
        elif command == "QE":
            self.source.endBlock("blockquote", remap='QE')
	# Undocumented Bell Labs-isms begin here
        elif command == "UX":
            self.source.pushline("<productname>Unix</productname>")
            return True
        elif command == "UC":
            self.source.pushline("<productname>%s</productname>" % args[0])
            return True
        elif command == "SC":
            self.source.pushSection(1, args[0])
        elif command == "P1" and self.source.find("P2"):
            self.source.beginBlock("programlisting", remap='P1')
        elif command == "P2":
            self.source.endBlock("programlisting", remap='P2')
        else:
            return False
        return True
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        return text

class MeInterpreter:
    "Interpret me macros."
    name = "me"
    exclusive = True
    toptag = "article"
    immutableSet = set([])
    ignoreSet = set(["1c","2c","bc","bl","ef","eh","ep","fo",
                  "he","hx","m1","m2","m3","m4","n1","n2",
                  "of","oh","tp","xl","xp","sk","(z",")z",
                  "sz","(l",")l",
                  ])
    complainSet = set(["ba","bx","ix","(b",")b","(c",")c","pa",
                    "sx","uh",".$p",".$c",".$f",".$h",".$s",
                    "+c","(x",")x",
                    ])
    parabreakSet = set(["blank","lp","pp","ip","np",])
    sectionbreakSet = set(["sh",])
    listbreakSet = set(["lp","pp","np","sh",])
    scopedSet = set([])
    translations = {
        "\\*" : [
        (r"\*-", "&ndash;"),	# Not quite right, supposed to be 3/4 dash
        (r"\*:", "&uml;"),
        (r"\*<", "<subscript>"),
        (r"\*>", "</subscript>"),
        (r"\*{", "<superscript>"),
        (r"\*}", "</superscript>"),
        (r"\*('", "&acute;"),
        (r"\*(`", "&grave;"),
        (r"\*^", "&circ;"),
        (r"\*,", "&cedil;"),
        (r"\*~", "&tilde;"),
        (r"\*(qe", "&exist;"),
        (r"\*(qa", "&forall;"),
        ],
        "\\(" : [
        (r"\('", "&acute;"),
        (r"\(`", "&grave;"),
        (r"\(lq", "&ldquo;"),
        (r"\(rq", "&rdquo;"),
        ]
      }
    # List how .IP tags map into DocBook mark types
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.delay = []
        self.inAbstract = False
        self.source.inPreamble = False
        if ioVerbosity in self.source.verbose:
            self.source.notify("exiting preamble")
    def interpret(self, dummy, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        if cmd in ("b", "bi", "i", "r", "rb", "sm", "u"):
            if len(args) <= 2:
                trailer = ""
            else:
                trailer = args[1]
            self.source.pushline(self.source.directHighlight(cmd.upper(), [args[0]], trailer))
        elif cmd == "q":
            if len(args) <= 2:
                trailer = ""
            else:
                trailer = args[1]
            self.source.pushline("<quote>%s</quote>%s" % (args[0], trailer))
        elif cmd in ("blank", "lp", "pp"):
            self.source.declareBodyStart()
            self.source.paragraph()
        elif cmd == "ip":
            self.source.emitVariablelist("ip", args[1])
        elif cmd == "bp":
            self.source.pushline(quoteargs(tokens))
            gatherItemizedlist(TroffInterpreter.ctrl + "bp", self.source, "bullet")
        elif cmd == "np":
            self.source.pushline(quoteargs(tokens))
            gatherOrderedlist(TroffInterpreter.ctrl + "np", self.source, "bullet")
        elif cmd == "(q":
            self.source.beginBlock("blockquote", remap='(q')
        elif cmd == ")q":
            self.source.endBlock("blockquote", remap=')q')
        elif cmd == "(f":
            self.source.beginBlock("footnote", remap='(q')
        elif cmd == ")f":
            self.source.endBlock("footnote", remap=')q')
        elif cmd == "(d":
            self.source.diversion = self.delay
        elif cmd == ")d":
            self.source.diversion = self.source.output
        elif cmd == "pd":
            self.source.output += self.delay
            self.delay = []
        elif cmd == "sh":
            self.source.pushSection(int(tokens[1]), tokens[2])
        elif cmd == "++":
            if tokens[1] == "AB":
                self.inAbstract = True
                self.source.emit("<abstract>")
            elif self.inAbstract:
                self.inAbstract = False
                self.source.emit("</abstract>")
        else:
            return False
        return True
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        return text

class MmInterpreter:
    "Interpret mm(7) macros."
    name = "mm"
    exclusive = True
    toptag = "article"
    immutableSet = set(["B", "I", "R",
                     "BI", "BR", "IB", "IR", "RB", "RI",
                     "AE", "AF", "AL", "RL", "APP", "APPSK",
                     "AS", "AT", "AU", "B1", "B2", "BE",
                     "BL", "ML", "BS", "BVL", "VL", "DE", "DL",
                     "DS", "FE", "FS", "H", "HU", "IA", "IE",
                     "IND", "LB", "LC", "LE", "LI", "P",
                     "RF", "SM", "TL", "VERBOFF", "VERBON",
                     "WA", "WE", ])
    ignoreSet = set([")E", "1C", "2C", "AST", "AV", "AVL",
                  "COVER", "COVEND", "EF", "EH", "EDP",
                  "EPIC", "FC", "FD", "HC", "HM",
                  "GETR", "GETST",
                  "INITI", "INITR", "INDP", "ISODATE",
                  "MT", "NS", "ND", "OF", "OH", "OP",
                  "PGFORM", "PGNH", "PE", "PF", "PH",
                  "RP", "S", "SA", "SP",
                  "SG", "SK", "TAB", "TB", "TC", "VM", "WC"])
    complainSet = set(["EC", "EX",
                    "GETHN", "GETPN", "GETR", "GETST",
                    "LT", "LD", "LO",
                    "MOVE", "MULB", "MULN", "MULE", "NCOL",
                    "nP", "PIC", "RD", "RS", "RE", "SETR", ])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {
        "\\*" : [
        (r"\*F", ""),	# Assumes that footnote marks are adjacent to footnotes
        ]
      }
    reductions = {}
    # Specific to this interpreter
    markdict = {"1":"arabic",
                "A":"upperalpha",
                "a":"loweralpha",
                "I":"upperroman",
                "i":"lowerroman"}
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
        self.liststack = []
        self.listcount = []
        self.flushed = False
        self.author = Author()
        self.TL = self.AS = self.FG = None
    def endList(self):
        if self.listcount[-1]:
            self.source.endParagraph(label="endList")
            self.source.emit("</listitem>")
            if self.liststack[-1] == "</variablelist>":
                self.source.emit("</varlistentry>")
        self.source.emit(self.liststack.pop())
        self.listcount.pop()
    def foldHighlights(self, cmd, args):
        # We need this to be a separate entry point for TP tag processing.
        if cmd in ("B", "I", "R"):
            return self.source.alternatingHighlight(cmd + "P", args)
        elif cmd in ("BI", "BR", "IB", "IR", "RB", "RI"):
            return self.source.alternatingHighlight(cmd, args)
        else:
            return None
    def interpret(self, dummy, tokens, caller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        # Highlighting
        highlighted = self.foldHighlights(cmd, args)
        if highlighted:
            self.source.emit(highlighted)
            return True
        # Commands for front matter
        elif cmd == "TL":
            self.source.declareBodyStart()
            self.TL = gatherLines(self.source)
            return True
        elif cmd == "AF":
            self.author.orgname = args[0]
            return True
        elif cmd == "AU":
            self.author.name(args[0])
            self.author.orgdiv = " ".join(args[1:])
            return True
        elif cmd == "AT":
            self.author.jobtitle = args[0]
            return True
        elif cmd == "AS":
            self.AS = []
            while self.source.lines:
                line = self.source.popline()
                tokens = lineparse(line)
                if tokens and tokens[0][1:3] == "AE":
                    break
                if not (isCommand(line) and self.source.ignorable(line)):
                    self.AS.append(line)
            return True
        # Here's where we analyze the front matter and generate the header
        if not self.flushed:
            self.source.inPreamble = False
            if ioVerbosity in self.source.verbose:
                self.source.notify("exiting preamble")
            self.flushed = True
            # OK, we've got enough info to generate the header
            if self.TL or self.AS or self.author.nonempty():
                self.source.endParagraph(label="mm header")
                self.source.emit("<articleinfo>")
                if self.TL:
                    self.source.emit("<title>")
                    caller.interpretBlock(self.TL)
                    self.source.emit("</title>")
                if self.author.nonempty():
                    self.source.emit(repr(self.author))
                if self.AS:
                    self.source.emit("<abstract>")
                    self.source.needParagraph()
                    caller.interpretBlock(self.AS)
                    self.source.endParagraph(label="AS")
                    self.source.emit("</abstract>")
                self.source.emit("</articleinfo>")
        # Ordinary formatting comands.
        if cmd == "AE":
            pass	# Already handled by AS
        elif cmd == "AL" or cmd == "RL":
            enumeration = 'arabic'
            spacing = 'normal'
            if args:
                spec = MmInterpreter.markdict.get(args[0])
                if not spec:
                    self.source.error("unknown enumeration type %s in AL" % args[0])
                else:
                    enumeration = spec
                if len(args) >= 3:
                    spacing = 'compact'
            self.source.emit("<orderedlist numeration='%s' spacing='%s'>" % (enumeration, spacing))
            self.liststack.append("</orderedlist>")
            self.listcount.append(0)
        elif cmd == "APP" or cmd == "APPSK":
            name = args[0]
            text = args[1 + (cmd == "APPSK")]
            self.source.troff.strings["Apptxt"] = " ".join(text)
            self.source.emit("<appendix><title>%s</title>" % name)
        elif cmd == "AS":
            self.source.emit("<abstract>")
            self.source.needParagraph()
        elif cmd == "B1":
            self.source.beginBlock("sidebar", remap="B1")
        elif cmd == "B2":
            self.source.endBlock(r"sidebar", remap="B2")
        elif cmd == "BE":
            self.source.paragraph("End of BS/BE block")
        elif cmd == "BL" or cmd == "ML":
            if len(args) == 2:
                spacing = 'compact'
            else:
                spacing = 'normal'
            self.source.emit("<itemizedlist spacing='%s' mark='bullet'>" % spacing)
            self.liststack.append("</itemizedlist>")
            self.listcount.append(0)
        elif cmd == "BS":
            self.source.warning("BS/BE block may need to be moved, see FIXME")
            self.source.paragraph("FIXME: BS/BE block may need to be moved")
        elif cmd == "BVL" or cmd == "VL":
            self.source.emit("<variablelist>")
            self.liststack.append("</variablelist>")
            self.listcount.append(0)
        elif cmd == "DE":
            self.source.endBlock("literallayout", remap="DE")
            if self.FG:
                self.emit("<caption><phrase>%s</phrase></caption>" % self.FG)
            self.source.emit("</informalfigure>")
        elif cmd == "DL":
            if len(args) == 2:
                spacing = 'compact'
            else:
                spacing = 'normal'
            self.source.emit("<itemizedlist spacing='%s' mark='dash'>" % spacing)
            self.liststack.append("</itemizedlist>")
        elif cmd == "DS" or cmd == "DF":
            self.source.emit("<informalfigure>")
            self.source.beginBlock("literallayout", remap=cmd)
        elif cmd == "FE":
            self.source.endBlock("footnote", remap="FE")
        elif cmd == "FG":
            self.source.FG = args[0]
        elif cmd == "FS":
            self.source.beginBlock("footnote", remap="FE")
        elif cmd == "H":
            for level in self.liststack:
                self.endList()
            level = int(args[0])
            headingText = headingSuffix = ""
            if len(args) > 1:
                headingText = args[1]
                if len(args) > 2:
                    headingSuffix = args[1]
            self.source.pushSection(level, headingText + headingSuffix)
        elif cmd == "HU":
            headingText = args[0]
            for level in self.liststack:
                self.endList()
            self.source.pushSection(self.source.sectiondepth, headingText, makeid=0)
        # We can ignore H[XYZ] as they are user-defined exits
        elif cmd == "IA":
            self.source.emit("<!-- Start IA address spec: " + repr(args))
        elif cmd == "IE":
            self.source.emit("End IE address spec. -->")
        elif cmd == "IND":
            self.source.pushline(self.source.index(list(map(deemphasize, args))))
        elif cmd == "LB":
            itype = int(args[3])
            mark = "1"
            if len(args) > 4:
                mark = args[4]
            if itype == 0:
                # Not strictly correct -- what LB really wants us to do
                # is generate a mark from the mark argument.
                self.source.emit("<itemizedlist spacing='%s' mark='bullet'>" % spacing)
                self.liststack.append("</itemizedlist>")
            else:
                spec = MmInterpreter.markdict.get(mark)
                if not spec:
                    self.source.error("unknown enumeration type %s in LB"%mark)
                    enumeration = 'arabic'
                else:
                    enumeration = spec
                self.source.emit("<orderedlist numeration='%s'>" % enumeration)
                self.liststack.append("</orderedlist>")
                self.listcount.append(0)
        elif cmd == "LC":
            for level in self.liststack:
                self.endList()
        elif cmd == "LE":
            self.endList()
        elif cmd == "LI":
            mark = ""
            if len(args) > 0:
                mark = args[0]	# FIXME: process second argument
            # End previous entry
            if self.listcount[-1]:
                self.source.endParagraph(label="LI")
                self.source.emit("</listitem>")
                if self.liststack[-1] == "</variablelist>":
                    self.source.emit("</varlistentry>")
            # Begin this entry
            if self.liststack[-1] == "</variablelist>":
                self.source.emit("<varlistentry>")
                self.source.emit("<term>%s</term>" % fontclose(mark))
            self.source.emit("<listitem>")
            self.source.needParagraph()
            # Bump counter
            self.listcount[-1] += 1
        elif cmd == "P" or cmd == "blank":
            self.source.paragraph()
        elif cmd == "RF":
            self.source.emit("Reference end -->")
        elif cmd == "SM":
            if len(args) > 2:
                self.source.pushline(r"%s\fS%s\fP%s" % args)
            else:
                self.source.pushline(r"\fS%s\fP%s" % args)
        # We can ignore user exits, TP, TX, TY.
        elif cmd == "VERBOFF":
            self.source.endBlock("literallayout", remap='VERBOFF')
        elif cmd == "VERBON":
            self.source.beginBlock("literallayout", remap='VERBON')
        elif cmd == "WA":
            self.source.emit("<!-- Start WA address spec: " + repr(args))
        elif cmd == "WE":
            self.source.emit("End WA address spec. -->")
        # Unknown command.
        else:
            return False
        return True
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        return text

class MwwwInterpreter:
    "Interpret mwww(7) macros."
    name = "mwww"
    exclusive = False
    toptag = "article"
    immutableSet = set(["HX", "BCL", "BGIMG",
                     "URL", "MTO", "FTP", "IMG", "HTML",
                     "TAG", "HR",])
    ignoreSet = set(["HX", "BCL", "BGIMG",
                  "HTML", "HR", "LK", "NHR",
                  "HnS", "HnE", "DC", "HTL", "LINKSTYLE"])
    complainSet = set([])
    parabreakSet = set([])
    sectionbreakSet = set([])
    listbreakSet = set([])
    scopedSet = set([])
    translations = {}
    reductions = {}
    def __init__(self, source, verbose=0):
        self.source = source
        self.verbose = verbose
    def interpret(self, dummyLine, tokens, dummyCaller):
        cmd = tokens[0][1:]
        args = tokens[1:]
        if len(args) == 1:
            args.append("")
        if len(args) == 2:
            args.append("")
        def makeUrl(url, txt, after):
            return '<ulink url="%s">%s</ulink>%s' % (url,txt,after)
        # Ordinary formatting comands.
        if cmd == "URL":
            self.source.pushline(makeUrl(args[0], args[1], args[2]))
        elif cmd == "MTO":
            self.source.pushline(makeUrl("mailto:"+args[0], args[1], args[2]))
        elif cmd == "FTP":
            self.source.pushline(makeUrl(args[0], args[1], args[2]))
        elif cmd == "IMG":
            ifile = args[1]
            self.source.pushline('<mediaobject>\n<imageobject><imagedata fileref="%s"/></imageobject>\n</mediaobject>' % ifile)
        elif cmd == "PIMG":
            ifile = args[1]
            self.source.pushline('<mediaobject>\n<imageobject><imagedata fileref="%s"/></imageobject>\n</mediaobject>' % ifile)
        elif cmd == "TAG":
            if self.source.docbook5:
                self.source.pushline('<anchor xml:id="%s"/>' % (self.source.makeIdFromTitle(args[0]),))
            else:
                self.source.pushline('<anchor id="%s"/>' % (self.source.makeIdFromTitle(args[0]),))
        elif cmd == "ULS":
            self.source.pushline("<itemizedlist>")
        elif cmd == "ULE":
            self.source.pushline("</itemizedlist>")
        elif cmd == "LI":
            self.source.error("LI is not yet supported, because it's not documented.")
        # Unknown command.
        else:
            return False
        return True
    def preprocess(self, text):
        return text
    def postprocess(self, text):
        return text

# This is how we autodetect the right macro set:

interpreterDispatch = {
    "pp": MeInterpreter,
    "Dt": MdocInterpreter,
    "Dd": MdocInterpreter,
    "Nm": MdocInterpreter,
    "AU": MsInterpreter,
    "NH": MsInterpreter,
    "TH": ManInterpreter,
    "MT": MmInterpreter,
    "SA": MmInterpreter,
    "COVER": MmInterpreter,
    # Extension macro sets
    "supplemental macros used in Tcl/Tk": TkManInterpreter,
    "BS": TkManInterpreter,
    "the F register is turned on": Pod2ManInterpreter,
    "Automatically generated by Pod::Man": Pod2ManInterpreter,
    "ZN": XManInterpreter,
    "Pn": XManInterpreter,
    "ny0": XManInterpreter,
    "reStructuredText": reStructuredTextInterpreter,
    "reStructeredText": reStructuredTextInterpreter,
    "DocBook XSL Stylesheets" : DocBookInterpreter,
    "pdfdest" : FoojzsInterpreter,
    "H0": ASTInterpreter,
    # These are all of the supported Mwww tags
    "URL": MwwwInterpreter,
    "FTP": MwwwInterpreter,
    "MTO": MwwwInterpreter,
    "PIMG": MwwwInterpreter,
    "IMG": MwwwInterpreter,
    "TAG": MwwwInterpreter,
    }

msoDispatch = {
    "e.tmac":    MeInterpreter,
    "doc.tmac":  MdocInterpreter,
    "s.tmac":    MsInterpreter,
    "an.tmac":   ManInterpreter,
    "m.tmac":    MmInterpreter,
    "www.tmac":  MwwwInterpreter,
    }

requiredExtensions = {
    MeInterpreter: "me",
    MsInterpreter: "ms",
    MmInterpreter: "mm",
    }

#
# Invocation machinery starts here
#

binaryEncoding = 'latin-1'

def stringize(o):
    "Turn a byte string into Unicode that preserves 0x80..0xff."
    if isinstance(o, str):
        return o
    if isinstance(o, bytes):
        return str(o, encoding=binaryEncoding)
    raise ValueError

def makeStdWrapper(stream):
    "Standard input/output wrapper factory function for binary I/O"
    if isinstance(stream, io.TextIOWrapper):
        # newline="\n" ensures that Python 3 won't mangle line breaks
        # lineBuffering=True ensures that interactive command sessions work as expected
        return io.TextIOWrapper(stream.buffer, encoding=binaryEncoding, newline="\n", line_buffering=True)
    return stream

sys.stdin = makeStdWrapper(sys.stdin)
sys.stdout = makeStdWrapper(sys.stdout)
sys.stderr = makeStdWrapper(sys.stderr)

def transfile(name, arguments, translateData, transFilename=None):
    "Read input sources entire and transform them in memory."
    if not arguments:
        outdoc = translateData(name, "stdin", sys.stdin.read(), False)
        if outdoc:
            stdout.write(stringize(outdoc))
    else:
        for ifile in arguments:
            infp = open(ifile, "rb")
            indoc = infp.read()
            infp.close()
            tmpfile = ifile + ".~%s-%d~" % (name, os.getpid())
            try:
                outfp = open(tmpfile, "wb")
            except OSError:
                stderr.write("%s: can't open tempfile" % name)
                return True
            try:
                outdoc = translateData(name,
                                        ifile,
                                        stringize(indoc),
                                        len(arguments)>1)
            except:
                os.remove(tmpfile)
                # Pass the exception upwards
                raise
            if outdoc == indoc:
                os.remove(tmpfile)
            if outdoc is None:
                continue
            else:
                outfp.write(outdoc)
                outfp.close()	# under Windows you can't rename an open file
                if not transFilename:
                    os.rename(tmpfile, ifile)
                elif type(transFilename) == type(""):
                    os.rename(tmpfile, ifile + transFilename)
                else:
                    os.rename(tmpfile, transFilename(ifile))

stdout = sys.stdout
stderr = sys.stderr
pretty = pprint.PrettyPrinter(indent=4)
globalhints = SemanticHintsRegistry()
spoofname = None

def main(args, dummyMainout=stdout, mainerr=stderr):
    #global globalhints, pretty
    global spoofname
    import getopt
    (options, arguments) = getopt.getopt(args, "d:e:i:D:I:h:qsS:xvwV")
    includepath = ["."]
    hintfile = None
    quiet = False
    portability = 0
    docbook5 = False
    verbosityLevel = 0
    verbosity = None
    inEncodings = ('UTF-8', 'ISO-8859-1')
    outEncoding = "UTF-8"
    for (switch, val) in options:
        if switch == "-d":
            verbosity = val
        elif switch == "-e":
            outEncoding = val
        elif switch == "-i":
            inEncodings = val.split(',')
        elif switch == "-D":
            globalhints.post(*val.split("="))
        elif switch == "-I":
            includepath = val.split(":")
        elif switch == '-h':
            hintfile = val
        elif switch == '-q':
            quiet += 1
        elif switch == '-x':
            docbook5 += 1
        elif switch == '-v':
            verbosityLevel += 1
        elif switch == '-w':
            portability += 1
        elif switch == '-S':
            spoofname = val
        elif switch == '-V':
            sys.stdout.write("doclifter.py version %s\n" % version)
            sys.exit(0)
    if not verbosity:
        verbosity = "gpscmibz"[:verbosityLevel]
    try:
        lifter = DocLifter(verbosity,
                           quiet,
                           portability,
                           includepath,
                           inEncodings,
                           outEncoding,
                           docbook5)
        transfile("doclifter.py", arguments, lifter, ".xml")
        if hintfile:
            fp = open(hintfile, "w")
            fp.write(str(globalhints))
            fp.close()
        return 0
    except LiftException as e:
        mainerr.write("%s\n" % str(e))
        return e.retval
    except IOError as e:
        mainerr.write("doclifter.py: file I/O error: %s\n" % e)
        return 3
    except KeyboardInterrupt:
        mainerr.write("doclifter.py: bailing out...\n")
        return 5
    except:
        if verbosity:
            raise
        else:
            mainerr.write("doclifter.py: internal error\n")
            return 4

if __name__ == "__main__":
    # Run the main sequence
    sys.exit(main(sys.argv[1:]))

# The following sets edit modes for GNU EMACS
# Local Variables:
# mode:python
# End:

