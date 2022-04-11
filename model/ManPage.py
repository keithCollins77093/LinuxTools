#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         view/ManPage.py
#   Date Started:   April 4, 2022
#   Purpose:        Read in a man page from a *.gz file ot text file, or other format for other operating system
#                   variants, and store the content in a format built from the standard man page macros.
#   Development:
#       2022-04-03:  Unique formats, e.g. NetworkManager
#           Commented out heading states:   Generator: DocBook XSL Stylesheets v1.79.1 <http://docbook.sf.net/>
#           Option include scripts and scrpts parameters which are in a section titled: DISPATCHER SCRIPTS and
#               are identified by being \fIunerlined\fR.
#           There is also a regularly formatted OPTIONS section.
#
#           Fallback strategy:
#               Provide manpage information as structured as possible, i.e. simply by section and whatever regular
#                   patterns exist inside each.
#               User can still use this to design and test their application of particular selections of arguments
#                   to the command.
#
#       2022-04-05:
#           Man page files used for testing and development so far:
#               accept.2.gz,    7z.1.gz,    GET.1p.gz
#           Next:   wireshark.1.gz
#               This file uses .IP like GET.1p.gz in the DESCRIPTION section, but uses it for bullet points,
#                   not for options.
#               Difference: When used for an option, .IP is followed on the next line by .IX which repeats
#                   the same content in a slightly different form as is on the .IP line above.
#               Working for both.
#
#               Next:   -z  <statistics> OPTION has numerous enumerated statistic type arguments listed
#                       under it, indented.  These need to be collected into an enum for a list selection
#                       in the PropertySheet for configuring tools.
#
"""
Man pages using the standard nroff macros for man pages are easy to scan and parse.
The macro names begin with a period and are at the beginning of a line.
The content qualified, or formally typed, by the macro follows on the same line and on all subsequent lines
    until another macro is found.
(Example:   acpi_listen.8)
The macros of interest for man pages are:
    .TH             Header, usually at the start.
    .SH             Beginning of a section.  Name of section follows on the same line.

The OPTIONS section appears to have only the following two macros:
    .TP             Line appears to be blank after macro name.
                        Repeated once for each option, followed each time by:
    .BI             Option help, followed on the same line by a structure like the following:
                        \-c "\fR, \fP" \--count " events"
                        Meaning -c and --count specify a particular option.
                        The next line or lines, until the next macro definition, is the explanation of
                        the option.

The FILES section has a sequence of macros, .PD, .B, .PD, with a file path specified after .B.

The AUTHORS section lists the authors, one on each line, followed on the next line by a '.br', meaning
    line break.

Sections present in a selection of command man pages include:
    NAME
    SYNOPSIS
    DESCRIPTION             (potentially complex internal formatting, see below)

    OPTIONS                 (These next 4 have command line options)
    COMMANDS
    SWITCHES
    DIAGNOSTICS

    EXAMPLE
    EXAMPLES                (User needs to see the use examples also)

    FILES
    SUPPORTED HARDWARE
    CONFIGURATION DETAILS
    BUGS
    SEE ALSO
    AUTHORS

    DESCRIPTION details (deb-changelog.5: dpkg source packages' changelog file format):
            NOTE:   deb-changelog.5 does not refer to a runnable, which is a command, a C library function, or
                    a DLL (*.so).
                    This is similar to deb-changes.5, which is a description of Debian changes file format.
                    All of the files in man5 appear to be NON-RUNNABLE, i.e. not directly subject matter of this
                    application. Example: ram.4
                        DESCRIPTION
                           The ram device is a block device to access the ram disk in raw mode.
                           It is typically created by:
                               mknod -m 660 /dev/ram b 1 1
                               chown root:disk /dev/ram
                    This is, however, useful information for configuring the commands mknod and chown for a particular
                    purpose when run in sequence.

        /f[Single Capital Letter]       formatting command, like emphasis or italic.
        The '.' with one or two capital letters following always happens at the start of a line.
        Examples include:
            .PP                     Paragraph
            .IP, .TP, .I, .BR       Lines following appear to be dates and times.
            .RI
        The .nf at the start of a line is followed by a number of lines with the /f form repeated which are
            always terminated by the .fi instruction.

There is frequently a section of text at the start of the file with the nroff instruction:
    .\" , at the start.  This should be treated as a file or man page header.
    In cpuid.4, for instance, this is not rendered by man.  It is a copyright notice and license statement.
    deb-changelog.5 is another example with this section at the start.

Section in a standard C library man page include:
    NAME
    SYNOPSIS
    DESCRIPTION
    RETURN VALUE
    ATTRIBUTES
    CONFORMING TO
    NOTES
    SEE ALSO
    COLOPHON

man2:   Linux Programmer's Manual, libraries / functions include-able in a C program via *.h header files.

Organization of man file folders on my Ubuntu 18 installation:

    Command line executables appear to be located in:
        HOME/.local/share/man/man1,
        /usr/share/man/man1,
        /usr/share/man/man6,
        /usr/share/man/man8

    Standard C Libraries are in (Linux Programmer's Manual):
        /usr/share/man/man2
        /usr/share/man/man3
        /usr/share/man/man4
        Also includes BSD File Format Manual:
                /usr/share/man/man5

    Miscellaneous application and system information:
        /usr/share/man/man7

"""
from collections import OrderedDict
from os.path import isdir, isfile
from gzip import open as gzOpen
from enum import Enum
from datetime import datetime

#   This works:
#   import pyshark

from tkinter import Tk, messagebox

PROGRAM_TITLE = "Man Page - Parsed"


class ManSection(Enum):
    NONE            = 'None'
    Name            = 'NAME'
    Synopsis        = 'SYNOPSIS'
    Description     = 'DESCRIPTION'
    Details         = 'DETAILS'

    #   These next 4 have command line options
    Options         = 'OPTIONS'
    Commands        = 'COMMANDS'
    Switches        = 'SWITCHES'
    Diagnostics     = 'DIAGNOSTICS'
    #   Also very important for the user to see these:
    Example         = 'EXAMPLE'
    Examples        = 'EXAMPLES'

    Files           = 'FILES'
    Supported       = 'SUPPORTED'
    Hardware        = 'HARDWARE'
    Configuration   = 'CONFIGURATION'
    Bugs            = 'BUGS'
    SeeAlso         = 'SEE ALSO'
    Authors         = 'AUTHORS'

    def __str__(self):
        return self.value


class LinxC_Section(Enum):
    Name            = 'NAME'
    Synopsis        = 'SYNOPSIS'
    Description     = 'DESCRIPTION'
    ReturnValue     = 'RETURN VALUE'
    Attributes      = 'ATTRIBUTES'
    ConformingTo    = 'CONFORMING TO'
    Notes           = 'NOTES'
    SeeAlso         = 'SEE ALSO'
    Colophon        = 'COLOPHON'

    def __str__(self):
        return self.value


class ManPage:

    def __init__(self, filePath: str, listener=None):
        if not (isinstance(filePath, str) and isfile(filePath)):
            raise Exception("ManPage constructor - Invalid filePath argument:  " + str(filePath))
        if listener is not None and not callable(listener):
            raise Exception("ManPage constructor - Invalid listener argument:  " + str(listener))
        self.listener = listener
        self.filePath = filePath
        self.name = filePath.split('/').pop().split('.')[0]
        #   unknown section names are placed in this map.
        #   key is section name and value is a list of text lines in the section.
        self.unknownsToDo = OrderedDict()
        self.timeStamp  = datetime.now()
        self.manSectionMap = ManPage.__initSectionNameMap()
        self.content = self.parse_roff(self.filePath)
        #   Examples of .TH line when man page is not for a command:
        #       .TH ACCEPT 2 2016-10-08 "Linux" "Linux Programmer's Manual"     (2)
        #       .TH DateTime::Locale::el_CY 3pm "2017-11-11" "perl v5.26.1" "User Contributed Perl Documentation"   (3)
        #       .TH VMWARE 4 "xf86-video-vmware 13.2.1" "X Version 11"          (4)
        #       .TH WACOM 4 "xf86-input-wacom 0.36.1" "X Version 11"            (4)
        #       .TH american-english 5 "16 June 2003" "Debian" "Users' Manual"  (5)
        #       .TH "BINFMT\&.D" "5" "" "systemd 237" "binfmt.d"                (5)
        #   Will still display it in a man-page-by-sections list-detail frame.
        self.commandDoc     = True
        self.headingLine    = self.content['Heading'][0].lower()
        headingLower        = self.headingLine.lower()
        if "linux programmer" in headingLower or "perl documentation" in headingLower or \
                "x version" in headingLower or 'debian' in headingLower:
            self.commandDoc = False

        print("ManPage constructed for:\t" + filePath)
        #   self.list()
        if self.listener is not None:
            self.listener({
                'application event': "ManPage constructed",
                '_source': 'ManPage.__init__()',
                'timeStamp': self.timeStamp,
                'eventType': 'Class',
                'eventName': 'ManPage Constructed',
                'eventAttributes': {'filePath': self.filePath}
            })

    def getName(self):
        return self.name

    def getContent(self):
        return self.content

    def list(self):
        print("\nContent of man page file:\t" + self.filePath)
        for contentClass, contentMap in self.content.items():
            print("\nContent Class:\t" + contentClass)
            if contentClass == "Options":
                #   manPageContent['Options'][section] = optionDefs
                for section, optionDefs in contentMap.items():
                    print("\nOptions in Section:\t" + str(section))
                    for option in optionDefs:
                        if 'text' in option:
                            print("\n\ttext:\t" + str(option['text']))
                        if 'argument' in option:
                            print("\targument:\t" + str(option['argument']))
                        if 'description' in option:
                            print("\tdescription:\t" + str(option['description']))

            if contentClass == 'Sections':
                for manSection, sectionContent in contentMap.items():
                    print("\nSection:\t" + str(manSection))
                    print("\tContent:")
                    for item in sectionContent:
                        print("\nITEM:\t" + str(item))
            print("\nContent:\n" + str(contentMap))


    @staticmethod
    def __initSectionNameMap():
        map = {}
        map['NAME']         = ManSection.Name
        map['SYNOPSIS']     = ManSection.Synopsis
        map['DESCRIPTION']  = ManSection.Description
        map['DETAILS']      = ManSection.Details
        map['OPTIONS']      = ManSection.Options
        map['COMMANDS']     = ManSection.Commands
        map['SWITCHES']     = ManSection.Switches
        map['DIAGNOSTICS']  = ManSection.Diagnostics
        map['EXAMPLE']      = ManSection.Example
        map['EXAMPLES']     = ManSection.Examples
        map['FILES']        = ManSection.Files
        map['SUPPORTED']    = ManSection.Supported
        map['HARDWARE']     = ManSection.Hardware
        map['CONFIGURATION']    = ManSection.Configuration
        map['BUGS']         = ManSection.Bugs
        map['SEE ALSO']     = ManSection.SeeAlso
        map['AUTHORS']      = ManSection.Authors
        return map

    @staticmethod
    def stripAllRoff(line: str):
        #
        #   This could be more efficient:
        #   Consider writing a C++ or Rust function to use with ctypes package, using my text,
        #   character-by-character indexing structure and methods.
        #
        return line.replace("\\fB", '').replace("\\fR", '').replace("\\fP", '').replace("\\fI", '')  \
                    .replace("\\-", '-').replace("\\s-1", '').replace("\\s0", '').replace("\\s-2", '') \
                    .replace("\\s+1", '').replace("\\s+2", '').replace('"', '') \
                    .replace('.\\}', '').replace('\\{\\', '').replace('.if', '') \
                    .replace('.ds', '').replace('.el', '').replace('.ie', '').replace('\'br\\', '') \
                    .replace('.tr', '').replace('..', '').replace('.fi', '').replace('.de', '') \
                    .replace('.ne', '').replace('.nf', '').replace('.ft', '').replace('.rm', '')
    @staticmethod
    def stripRoff(line, chList, new):
        for ch in chList:
            line = line.replace(ch, new)
        return line

    @staticmethod
    def formatSection(section: ManSection, sectionLines: list):
        """
        :param sectionMap:
        :return:
        """
        if not isinstance(section, ManSection):
            raise Exception("ManPage.formatSection - Invalid section argument:  " + str(section))
        if not isinstance(sectionLines, list) and not isinstance(sectionLines, tuple):
            raise Exception("ManPage.formatSection - Invalid sectionLines argument:  " + str(sectionLines))
        roffLines = sectionLines
        textLines = []
        options = []
        #   Line content:   '\-' == '-'     double quotes are generally ignored in print out.
        #       '\fB' starts line with '\fR' at end.  Emphasis: \fB == bright, \fR == regular.
        #       '\fI' starts line with '\fR' at end.  Emphasis: \fI == underline, \fR == regular.
        #       Single quote is a single quote in the output.
        textLine = ''
        optionDef = None
        inIP    = False
        inTP    = False
        IPtextParts  = None
        for roffLine in roffLines:
            #   Initial:    Eliminate the format string and accumulate the remainder of the line, along with
            #               lines with no format string, into a single line until a
            #               '.br' is found.
            #               '.br' found:    start a new line.
            if len(roffLine.strip()) == 0:
                continue

            if roffLine.split()[0] in ['.br', '.PP']:  # <br> is new line,  .PP os new paragraph
                textLine = textLine.replace('\\n', '\n')
                textLine = textLine.replace('\\', ' ')
                textLines.append(ManPage.stripAllRoff(textLine))
                textLine = ''
            else:
                roffLine = roffLine.replace('\\n', '\n')
                roffLine = roffLine.replace('\\', ' ')
                roffLine = ManPage.stripAllRoff(roffLine)
                roffParts = roffLine.split()
                if len(roffParts) > 0:
                    if roffParts[0].startswith('.'):
                        textLine += ' ' + ' '.join(roffParts[1:]) + ' '
                    else:
                        textLine += ' '.join(roffParts[0:])

            if section in [ManSection.Description, ManSection.Options, ManSection.Commands, ManSection.Switches, ManSection.Diagnostics]:
                #   .TP starts the option definition, on a line by itself.
                #   .B or .BI is on the next line, followed by the option letter(s)
                #   The nest line contains the description text, until the next .TP or other begin "section" instruction.
                roffLine = ManPage.stripAllRoff(roffLine)
                if roffLine.startswith('.TP'):
                    if optionDef is not None:
                        options.append(optionDef)
                    optionDef = {}
                    inTP = True
                elif roffLine.startswith('.IP'):        # Wireshark: merely a bullet point in DESCRIPTION, not an option
                    inIP = True
                    inTP = False
                    IPtextParts = roffLine.split()[1:]
                #   Repetition of content if .IP line in options specified in DEFINITION sections:
                elif roffLine.startswith('.IX'):
                    if inIP and IPtextParts is not None:
                        #   Confirm text match
                        IXtextParts  = roffLine.split()[1:]
                        if len(IPtextParts) > 1 and len(IXtextParts) > 1 and \
                                IPtextParts[0] == IXtextParts[1]:
                            if optionDef is not None:
                                options.append(optionDef)
                            optionDef = {}
                            if '"' in roffLine:
                                roffLine = roffLine.replace('"', '')
                            optionDef['text'] = ' '.join(roffLine.split()[2])
                            if len(IXtextParts) > 2:
                                optionDef['argument'] = ' '.join(roffLine.split()[3:])

                        inIP    = False
                        inTP    = False
                        IPtextParts = None
                elif roffLine.startswith('.BI') and optionDef is not None:
                    if inTP:
                        optionDef['text'] = ' '.join(roffLine.split()[1:])
                        inTP = False
                elif roffLine.startswith('.B') and optionDef is not None:
                    if inTP:
                        optionDef['text'] = ' '.join(roffLine.split()[1:])
                        inTP = False
                elif roffLine.startswith('.RS'):
                    inTP = False
                elif roffLine.startswith('.PP'):        #   Paragraph divider in description, ignore.
                    inTP = False
                #   Text can be mixed in with options, already recorded above.
                elif optionDef is not None:
                    if inTP:        #   This is an option text with possible '=[parm]' following.
                        optionDef['text'] = roffLine
                        inTP = False        #   Assumes a single line of option text
                    elif 'text' in optionDef:
                        if 'description' in optionDef:
                            optionDef['description'] += '\n' + roffLine
                        else:
                            optionDef['description'] = roffLine

            #   print(textLine)

            """
            elif roffLine.startswith('.IX'):  # Appears to be ignored in output
                pass
            elif roffLine.startswith('.PD'):  # If in FILES section
                pass
            elif roffLine.startswith('.PP'):  # New paragraph
                pass
            elif roffLine.startswith('.ie'):  # ignored
                pass
            elif roffLine.startswith('.el'):  # ignored
                pass
            elif roffLine.startswith('.nh'):  # disable hyphenation
                pass
            elif roffLine.startswith('.ad l'):  # disable justification (adjust text to left margin only)
                pass
            elif roffLine.startswith('.\\"'):  # Comment line: .\"
                pass
            """
        textLines.append(textLine)
        if section in [ManSection.Description, ManSection.Options, ManSection.Commands, ManSection.Switches, ManSection.Diagnostics]:
            if optionDef is not None and 'text' in optionDef:
                options.append(optionDef)
        return tuple(textLines), tuple(options)

    def parse_roff(self, filePath: str):
        """
        Catalog of used macros and nroff instructions:
            Left off on accept.8 - SYNOPSIS - vary important format parse for command line template.
        :param filePath:
        :return:
        """
        manPageContent = OrderedDict()
        if isfile((filePath)):
            manPageContent['Heading']   = None
            manPageContent['Title']     = None
            manPageContent['Sections'] = OrderedDict()
            manPageContent['Options']   = OrderedDict()
            manPageContent['Comments'] = []
            manPageContent['Unclassified'] = []
            manPageContent['Synopsis'] = []
            #   Assumes all man files are in gzip format.  Not necessarily true on all Linux distros.
            if filePath.endswith('.gz') or filePath.endswith('.gzip'):
                gzFile = gzOpen(filePath, mode='rb')
                roffText = gzFile.read().decode('utf-8')
                gzFile.close()
            else:
                file = open(filePath, 'r')
                roffText = file.read()
                file.close()
            roffLines = roffText.split('\n')
            currentSection = None
            inHeader = False
            inSection = False
            inComment = False
            prevInstrucion = None
            for line in roffLines:
                if not line.startswith('.SH') and currentSection == ManSection.Synopsis:
                    if not line.startswith('.IX') and not line.startswith('\\&'):
                        #   Again, this could be more efficient:
                        manPageContent['Synopsis'].append(line.replace('\\ ', ' ').replace('\\-', '-') \
                                                          .replace('\\fB', '').replace('\\fR', '').replace('.B', '') \
                                                          .replace('.RB', '').replace('.PP', ''))
                elif line.startswith('.TH'):
                    #   Collect lines until .SH found
                    inHeader = True
                    currentSection = None
                    manPageContent['Heading'] = []
                    manPageContent['Heading'].append(line.replace('.TH', '').strip())
                    prevInstrucion = '.TH'
                elif line.startswith('.SH'):
                    #   Section, name follows in same line, may be in double quotes, remove if so.
                    #   OPTIONS sections are also subdivided with a name before the OPTIONS'.
                    #       Examples: APPLICATION, LOGGING, TEST
                    #   print("Found Section:\t" + line)
                    inSection = True
                    inHeader = False
                    lineParts = line.strip().split()
                    #   Only process known section names for now.
                    #   Place unknowns in to-do log.
                    #   NOTE:   EXAMPLE sections can be numbered, e.g.:
                    #       .SH EXAMPLE 1
                    sectionName     = lineParts[1].strip()
                    if sectionName.startswith('"'):
                        sectionName = sectionName.replace('"', '')
                    if sectionName in self.manSectionMap:
                        #   'EXAMPLE':  Check for number or other indexing identifier following EXAMPLE
                        currentSection = self.manSectionMap[sectionName]
                        manPageContent['Sections'][currentSection] = []
                    else:
                        #   Just collect text lines for now, process formatting instructions (out) before using.
                        currentSection = sectionName
                        self.unknownsToDo[currentSection] = []
                    prevInstrucion = '.SH'

                elif line.startswith('.IP'):
                    prevInstrucion = '.IP'
                    if currentSection is not None:
                        if currentSection in manPageContent['Sections']:
                            manPageContent['Sections'][currentSection].append(ManPage.stripAllRoff(line))
                        elif currentSection in self.unknownsToDo:
                            self.unknownsToDo[currentSection].append(ManPage.stripAllRoff(line))

                elif line.startswith('.IX'):
                    #   This is a heading if it directly follows an '.SH'
                    if prevInstrucion == '.SH':
                        #   This will simply have the same text for the section heading as the previous line.
                        pass
                    elif prevInstrucion == None:    # This is a file / man page Title
                        manPageContent['Title'] = ' '.join(line.split()[1:])

                    elif prevInstrucion == '.IP':   #   This line is an option definition
                        if currentSection is not None:
                            if currentSection in manPageContent['Sections']:
                                manPageContent['Sections'][currentSection].append(ManPage.stripAllRoff(line))
                            elif currentSection in self.unknownsToDo:
                                self.unknownsToDo[currentSection].append(ManPage.stripAllRoff(line))

                    prevInstrucion = '.IX'

                elif line.startswith('.\\\"'):
                    inComment = True
                    lineParts = line.split("\"")
                    #   print("\tComment Line:\t" + lineParts[1].strip())
                    manPageContent['Comments'].append(lineParts[1].strip())
                    prevInstrucion = '.\\\"'
                else:
                    if currentSection is not None:
                        if currentSection in manPageContent['Sections']:
                            manPageContent['Sections'][currentSection].append(ManPage.stripAllRoff(line))
                        elif currentSection in self.unknownsToDo:
                            self.unknownsToDo[currentSection].append(ManPage.stripAllRoff(line))
                    else:
                        if inHeader:
                            manPageContent['Heading'].append(ManPage.stripAllRoff(line))
                        elif not line.startswith('.el') and \
                                line.split()[0] not in ('.', '.\\}', '\\{\\', '.if', '.ds', '.el', '.ie', '\'br\\}',
                                                     '.tr', '..', '.fi', '.de', '.ne', '.nf', '.ft', '.rm'):
                            manPageContent['Unclassified'].append(ManPage.stripAllRoff(line))
                    continue
                    prevInstrucion = None

                if ManSection.Name in (manPageContent['Sections']):
                    #print(str(manPageContent['Sections'][ManSection.Name]))
                    #print()
                    pass

        if manPageContent['Synopsis'] is not None:
            manPageContent['Synopsis'] = tuple(manPageContent['Synopsis'])
        for section, sectionLines in manPageContent['Sections'].items():
            textLines, optionDefs = ManPage.formatSection(section, sectionLines)
            manPageContent['Sections'][section] = textLines
            if section in [ManSection.Description, ManSection.Options, ManSection.Commands, ManSection.Switches, ManSection.Diagnostics]:
                manPageContent['Options'][section] = optionDefs
        return manPageContent


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":
    print(__doc__)
    exit(0)
    mainView = Tk()
    mainView.geometry("700x400+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())
    mainView.mainloop()
