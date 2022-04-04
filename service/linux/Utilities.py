#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 12, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         Utilities
#   Purpose:        GNU / Linux shell out command gui generator.
#   Development:
#       Linux includes as standard tools a number of command line programs useful, valuable, relevant, and already
#       written and used for digital forensic investigaiton purposes. Kali is an example of a collection of such tools
#       expressly implemented for this purpose.
#       About ten years ago, I started work on a means of automatically generating GUI's for Linux comand line utilities
#       using the Linux man pages, which to me appeared to be formatted well enough to parse out their options and
#       help text for generating a property sheet of option selection controls.  I soon started working on more
#       general application generation strategies, however.  With my digital forensics certification nearly complete,
#       I need to leverage Linux's built in forensics tools, and my advanced capabilities in Python can be leveraged
#       for this purpose, along with my application generation strategies (Python Learning Curve submitted to TX).
#
#       Java, among other standard languages, has the ability to start other processes passing to
#       them a string of options, and the ability to read the files that the utilities' output can
#       be piped to.  Python also has this capability, along with a simplified implementation of threading.
#       Where external files are to be created and read, perhaps in large quantities
#       for extensive analysis of a device, assigning shell processes to separate threads would be standard practice.
#
#       This module will NOT be a hand-coded attempt to implement GUI's for Linux command line tools, using the same
#       man pages for reference that an automatic GUI generator might also use.  Although the man pages are thorough
#       and precise, they are sometimes not complete in their coverage of the behaviors resulting from use of the various
#       command line options in their various semantically legitimate combinations.  Therefore more thorough technical
#       documentation of Linux itself is required in this effort to mobilize existing and standard resources
#       for digital forensics deployment.
#
#       2019-02-15:
#       Ideal strategy: since all of each command parameters are listed in the man(ual) page database entry for each
#       (other than undocumented ones, you know these Linux / Unix folks) the dialog / command configuration and
#       design view can be generated in part using the man page database entry for the command.  Man pages are
#       generated from the man page database, and are of a fairly strict format, so the text could be parsed to
#       obtain the parameters, the help text for each, and the allowable values where these are enumerated.
#       However, this is not necessary if the man database can be accessed through a shell Command which queries
#       it for the records (structured, with meta-data) pertinant to a particular command.  I have searched online
#       for documentation of such a command, API or other method briefly and found nothing.  This does not mean it does
#       not exist.
#       Even with this, it is impossible without semantic web style meta-data to validate argument values generally,
#       so a certain amount of hand coding will be necessary, and for my own educational purposes careful study of
#       each command to determine the possible and acceptable value and to attach the appropriate entry widgets to
#       argument entry workflows will be highly valuable.
#       Since particular combinations of values for each argument on particular commands serve particular purposes
#       which are definable as a working set for particular specialties, or particular subject matter interests in
#       the services provided by the GNU / Linux operating system shell, they must be savable as named objects.
#       This would destroy the typing skill cult that developed around the Unix shell by eliminating the repetitive
#       typing of commands with with similar argument value patterns, such being easy to develop templates for,
#       especially for those who are victims of this cult.  As a simple example, suppose someone wanted a table listing
#       the results of an 'ls' command with particular parameters on particular directories routinely.  These
#       can be designed using standard GUI widgets for the argument values and saved as a command template, which
#       can be used as they are or quickly modified for similar effects.
#       Irregardless of whether a man database API or access method other than the man command can be found, the
#       parameters and help for any command can be defined with a JSON statement, and the JSON command definition
#       used to generate the argument input frame and to control various behaviors of the design and launch
#       process.
#       Parsing Man Page Text:
#       Sections in order for 'ls' are:
#           NAME, SYNOPSIS, DESCRIPTION, AUTHOR, REPORTING BUGS, COPYRIGHT, SEE ALSO
#
#
#   Using the nroff input files in the source man/ folder by itself is impossible without a dictionary of the
#   escape sequences, which can have variable length parameters some of which are quoted, requiging a sophisticated
#   parser.  The resulting text, however, can be easily seen from the man page resulting, and since nroff is totally
#   lne orieented, the escape sequences can be completely stripped this way.
#   Since any of the section headers can be sections or subsections, to disambiguate the particular header,
#   the nroff input file can be scanned also to supplement and fill-out the structure I create using the man
#   page output only here.   Since there are typical headers for man pages and typical macros for man page
#   input nroff files, this should handle the vast majority of cases.  After all, if you want your work actually be
#   used in the GNU world, you conform to the standards which use the standard tool sets available on GNU Linux.
#   This much can be guaranteed, so a VERY useful tool set can be available via automatically generated GUI
#   property sheets (minimum, no particular semantic organization yet contemplated, although this would be simple
#   to add by hand to the JSON descriptor if the code is designed well.)
#
#       2019-02-16:
#       I researched and found that man pages for the GNU coreutils are not in a database, but rather are automatically
#       generrated from the utility source code into nroff files.  I then wrote a parser for the file format, using as
#       anchors the standard man nroff macros.  This is in module service.linux.NroffMan.py.  The next step is to
#       use the parse of the man page itself along with the parse of the nroff file to produce as complete a json
#       representation as possible usable for GUI dialog generation for the command / utility.
#
#       2019-02-17: ISSUES REMAINING:
#           Some flags / parameters can be used multiple times in a single invocation.
#               This can be solved by simply allowing the user to run the pre-configured command multiple times
#               keeping the other options the same while varying one.  Work flow will depend on what sort of
#               iterations on parameter variations are supported.
#               Example: grep -e PATTERN, --regexp=PATTERN
#           Same example, currently do not distinguish syntax difference between the primary name and the verbose name
#               when a Value is allowed or required.
#       2019-02-18: dd discovery
#           dd's man page does not use the - or -- format for its parameters, but does use a rigid format for most of
#           them and the nroff file uses the same macro, .TP, for all of them, so this command can be added.
#           The rigid fomrmat:  lowercase single word, '=', UPPER CASE SINGLE WORD
#               no spaces between the parts.
#               help text / description is on the next line, and the next empty line ends the text.
#           Two options for this type of formatting:
#               hand code the options into the json
#               recognise special formatting for particular commands.
#               This can change too easily, so use of the nroff .TP macro is likely a good idea with some kind of
#               user involvement for resolution of ambiguities.
#

import os, json, string
from pathlib import Path

from service.linux.NroffMan import NroffScanner

class ManPageScanner:

    SECTION_HEADERS     = ('NAME', 'SYNOPSIS', 'DESCRIPTION', 'FILES', 'AUTHOR', 'REPORTING BUGS', 'COPYRIGHT',
                           'SEE ALSO', 'BUGS', 'OPTIONS', 'REGULAR EXPRESSIONS', 'ENVIRONMENT VARIABLES',
                           'EXIT STATUS', 'NOTES')

    TERMINALS               = ('-', '--', '[', '=', ']')
    MAN_PAGE_PACKAGE        = 'manPages/'
    DEFAULT_UTILITY_NAME    = 'grep'

    COMMAND_DESCRIPTORS     = {}

    @staticmethod
    def UtilDescriptorFolderUpdate():
        utilityFileList = NroffScanner.readNroffManFileList()
        for fileDescr in utilityFileList:
            ManPageScanner.parseManPage(fileDescr.getUtilityName())

    @staticmethod
    def parseManPage(utilityName):
        outputStream = os.popen('man ' + utilityName)
        manPageText = outputStream.read().strip()
        outputStream.close()
        if len(manPageText) == 0:
            raise Exception('ManPageScan constructor - unable to run command:\t' + utilityName)

        print('parseManPage:\t' + utilityName + ":")
        ManPageScanner.COMMAND_DESCRIPTORS[utilityName] = {}
        lsManPageLines  = manPageText.split('\n')
        lineIndex       = 0
        currentSection   = None
        sectionText     = {}

        #   Section header properties:
        #       All caps except for spaces between words
        #       starts at beginning of line
        #       One of sectionHeaders
        #
        while lineIndex < len(lsManPageLines):
            lineText = lsManPageLines[lineIndex].strip()
            if lineText in ManPageScanner.SECTION_HEADERS:
                #   print('Found section:\t' + lineText)
                currentSection  = lineText
                sectionText[ currentSection ] = ''
                #   print('STARTING SECTION:\t' + lineText)
                lineIndex += 1
                while lineIndex < len(lsManPageLines) and not lsManPageLines[lineIndex].strip() in ManPageScanner.SECTION_HEADERS:
                    line = lsManPageLines[lineIndex] + '\n'
                    if not line.startswith('GNU'):
                        sectionText[currentSection] += line
                    lineIndex += 1
            else:
                lineIndex += 1

            #   if currentSection != None:
                #   print(sectionText[currentSection])

        for key, text in sectionText.items():
            ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key] = {}
            if key == 'NAME':
                parts   = text.split('-')
                ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key]['name']   = parts[0].split(',')[0].strip()
                ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key]['help']   = ''
                while len(parts) > 1:
                    ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key]['help'] += parts[1]
                    parts.remove(parts[1])
                    ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key]['help'] = ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key]['help'].strip()
            elif key == 'DESCRIPTION' or key == 'OPTIONS':
                #   The first few lines under the DESCRIPTION heading are the general description text for the commands.
                #   The first line after DESCRIPTION which starts with a '-' is the first parameter description
                lines = text.split('\n')
                lineIndex = 0
                parameterCount = 0
                firstOption = True
                while lineIndex < len(lines):
                    #   description containing a line with a dash at the start:
                    #   my usual treatment will make it look like a flag with the description on the same line.
                    #   the indent is apparently the only way to distinguish between the option and the text.
                    #   hopefully this is a standard for all man pages.
                    #   is there a way to do a bulk check?
                    textLine        = False
                    if lines[lineIndex].strip().startswith('-'):
                        if firstOption:
                            optionIndent = 0
                            while optionIndent+1 < len(lines[lineIndex]) and \
                                    lines[lineIndex][optionIndent:optionIndent+1] in string.whitespace:
                                optionIndent += 1
                            firstOption = False
                            #   print('optionIndent:\t' + str(optionIndent) + '\t at line"\t' + lines[lineIndex])
                        else:
                            indent = 0
                            while indent+1 < len(lines[lineIndex]) and lines[lineIndex][indent:indent+1] in string.whitespace:
                                indent += 1
                            if indent > optionIndent:       #  this is text, not an option
                                textLine = True

                    if not textLine and lines[lineIndex].strip().startswith('-'):      #   a likely parameter definition
                        line = lines[lineIndex].strip()
                        #   flags with text / description on the same line:
                        #   these are distinguished as lines that start with '-' or '--' which have text after the last
                        #   token following the last ManPageScan.TERMINAL.
                        #   Split on ' ' after last terminal, and everything from  index = 1 on is description.
                        #
                        #   Problem:
                        #       look at --tag in b2sum.json
                        #       when a last terminal is found, check on either side o it for correct syntax.
                        #       if incorrect for a terminal, skip to next.
                        #       '-' will have a space before it if it is a TERMINAL
                        #       all others will have no space before them if they are TERMINAL
                        #
                        singleLineParm  = False
                        posLastTerm = len(line) - 1
                        description = 'NOT VALID'
                        found = False
                        while posLastTerm >= 0 and not found:
                            if not line[posLastTerm:posLastTerm+1] in ManPageScanner.TERMINALS:
                                posLastTerm -= 1
                            else:
                                if line[posLastTerm:posLastTerm+1] == '-':
                                    #   if the preceeding is a space then
                                    if posLastTerm >= 1 and line[posLastTerm-1:posLastTerm] == ' ':
                                        found = True
                                else:
                                    #   if the preceding character is not a space then
                                    if posLastTerm >= 1 and line[posLastTerm-1:posLastTerm] != ' ':
                                        found = True
                                if not found:
                                    posLastTerm -= 1
                        parmDefStub = line[:posLastTerm+1]
                        descriptionParts    = line[posLastTerm+1:].split(' ')
                        if len(descriptionParts) > 1:
                            description = ''
                            partIdx = 1
                            while partIdx < len(descriptionParts):
                                description += descriptionParts[partIdx] + ' '
                                partIdx += 1
                            line = lines[lineIndex] = parmDefStub + descriptionParts[0]
                            singleLineParm = True

                        #   the final detail is optional values, which are enclosed in brackets.
                        #       string = str()
                        #       position = string.find('[', 0, len(string))
                        #   will solve this, among other detailed parsing problems should they arise from variations
                        #   in man page format which occur over time and among different distributions.
                        #
                        valueOptional   = False
                        leftPos = line.find('[', 0, len(line))
                        #print('leftPos:\t' + str(leftPos))
                        if leftPos != -1:
                            rightPos = line.find(']', leftPos + 1, len(line))
                            #print('rightPos:\t' + str(rightPos))
                            if rightPos != -1:
                                bracketValue = line[leftPos + 1: rightPos].replace('=', '')
                                valueOptional = True

                        parameterCount  += 1
                        primaryName     = ''
                        verboseName     = ''
                        flagNames   = lines[lineIndex].strip().split(',')

                        #   remove all brackets if present
                        index = 0
                        while index < len(flagNames):
                            while flagNames[index].find('[') != -1 or flagNames[index].find(']') != -1:
                                flagNames[index]   = flagNames[index].replace('[', '').replace(']', '')
                            index += 1

                        flagNames[0]    = flagNames[0].strip()
                        if len(flagNames) > 1:
                            flagNames[1] = flagNames[1].strip()
                        #   sort out primary name and verbose name
                        if flagNames[0].startswith('--'):
                            primaryName = verboseName = flagNames[0]
                        elif flagNames[0].startswith('-'):
                            primaryName = flagNames[0]
                        if len(flagNames) > 1:
                            if flagNames[1].startswith('--'):
                                verboseName = flagNames[1]
                            elif flagNames[1].startswith('-'):
                                primaryName = flagNames[1]

                        #   check for values that the flag or parameter can be equal to.
                        #   if no "=[valueName]" is present, then the parameter is just a flag, to be represented
                        #   by a single checkbox with man page help text in the command's dialog / frame.
                        #   A value can be separated by '=' or by ' '
                        valuePresent    = False
                        valueParts      = primaryName.split('=')

                        if len(valueParts) == 1:
                            valueParts = primaryName.split(' ')
                        if len(valueParts) == 2:        #   a value is present in first parameter name
                            valuePresent    = True
                            value       = valueParts[1].strip()
                            primaryName = valueParts[0].strip()

                        valuePresent = False
                        valueParts = verboseName.split('=')
                        if len(valueParts) == 1:
                            valueParts = verboseName.split(' ')
                        if len(valueParts) == 2:  # a value is present in first parameter name
                            valuePresent = True
                            value = valueParts[1].strip()
                            verboseName = valueParts[0].strip()

                        ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName] = {}
                        ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['primaryName'] = primaryName
                        if verboseName     != '':
                            ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['verboseName'] = verboseName
                        if valuePresent:
                            ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['value']    = value
                            ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['valueOptional'] = valueOptional

                        ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['description'] = []
                        parameterStart = False
                        lineIndex += 1

                        if singleLineParm:
                            ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['description'] = \
                                [description, ]
                        else:
                            while lineIndex < len(lines) and not parameterStart:
                                textLine = False
                                if lines[lineIndex].strip().startswith('-'):
                                    indent = 0
                                    while indent + 1 < len(lines[lineIndex]) and lines[lineIndex][
                                                                                 indent:indent + 1] in string.whitespace:
                                        indent += 1
                                    if indent > optionIndent:  # this is text, not an option
                                        textLine = True

                                if textLine or not lines[lineIndex].strip().startswith('-'):
                                    ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key][primaryName]['description'].append(lines[lineIndex].strip())
                                    lineIndex += 1
                                else:
                                    parameterStart = True
                    else:
                        lineIndex += 1
                if parameterCount == 0:     #   no parameters found in this section, record text only
                    ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key] = lines


                #   print(ManPageScan.COMMAND_DESCRIPTORS[self.utilityName][key])

            elif key in ManPageScanner.SECTION_HEADERS:
                #   ManPageScan.COMMAND_DESCRIPTORS[utilityName][key] = tuple(text.split('\n'))
                ManPageScanner.COMMAND_DESCRIPTORS[utilityName][key] = text

        ManPageScanner.toFile(utilityName, manPageText)


    def __init__(self, manJsonPackageFolder):
        self.utilityDefinitions     = {}
        self.readUtilityDefinitions(manJsonPackageFolder)

    #   read the utility descriptor json's from the installation package / folder
    def readUtilityDefinitions(self, jsonPackagePath: str):
        #
        #   This assumes that this is running in the folder that contains MAN_PAGE_PACKAGE
        #
        if jsonPackagePath != None:
            manJsonPackagePath  = jsonPackagePath
        else:
            manJsonPackagePath  = ManPageScanner.MAN_PAGE_PACKAGE

        if os.path.exists(manJsonPackagePath) and os.path.isdir(manJsonPackagePath):
            fileList    = os.listdir(manJsonPackagePath)
            for name in fileList:
                if name.endswith('.json'):
                    utilityName     = name.split('.json')[0]
                    jsonFile    = open(str(Path(manJsonPackagePath + '/' + name).absolute()), 'r')
                    self.utilityDefinitions[utilityName] = json.load(jsonFile)

            return self.utilityDefinitions
        else:
            raise Exception('readUtilityDefinitions - invalid folder:\t' + manJsonPackagePath)


        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + '/' + self.utilityName + '.json').absolute()), 'r')
        file.write(json.dumps(ManPageScanner.COMMAND_DESCRIPTORS[self.utilityName], indent=4, sort_keys=True))
        file.close()
        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + '/' + self.utilityName + '_manPage.txt').absolute()), 'w')
        file.write(self.lsManPage)
        file.close()

        return self.utilityDefinitions

    def getUtilityDefinitions(self):
        return self.utilityDefinitions


    def list(self):
        print('ManPageScan:\t' + self.utilityName)
        for name, value in ManPageScanner.COMMAND_DESCRIPTORS[self.utilityName].items():
            print("\t" + name + ":\t" + str(value))

    def toFile(self):
        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + '/' + self.utilityName + '.json').absolute()), 'w')
        file.write(json.dumps(ManPageScanner.COMMAND_DESCRIPTORS[self.utilityName], indent=4, sort_keys=True))
        file.close()
        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + '/' + self.utilityName + '_manPage.txt').absolute()), 'w')
        file.write(self.lsManPage)
        file.close()

    @staticmethod
    def toFile(utilityName, lsManPage):
        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + utilityName + '.json').absolute()), 'w')
        file.write(json.dumps(ManPageScanner.COMMAND_DESCRIPTORS[utilityName], indent=4, sort_keys=True))
        file.close()
        file = open(str(Path(ManPageScanner.MAN_PAGE_PACKAGE + utilityName + '_manPage.txt').absolute()), 'w')
        file.write(lsManPage)
        file.close()


if __name__ == "__main__":
    print("Linux Utilities Module is Running")
    print("Refreshing GNU coreutils man page package")

    #   Pope'n (os.popen) is the safe way to shell out:

    #   type of return value of os.popen(shell command with args) is _io.TextIOWrapper
    outputStream 	= os.popen( 'date' )
    now 			= outputStream.read().strip()       #   carriage return is appended by os.popen.read()
    outputStream.close()
    print( "Current date and time:\t" + now )

    outputStream 	= os.popen( 'echo $PATH' )
    path 			= outputStream.read().strip()
    outputStream.close()
    print( "$PATH:\t" + path )

    #outputStream 	    = os.popen( 'ls -l' )
    #directoryList 		= outputStream.read() # .strip()
    #print( "Directory:\n" + directoryList )
    #print()

    print('os.getcwd():\t' + os.getcwd() )

    #   grepManPageScan     = ManPageScanner('b2sum')
    #   grepManPageScan.toFile()
    #   grepManPageScan.list()

    #   ManPageScanner.UtilDescriptorFolderUpdate()

    utilityDefinitions  = ManPageScanner().readUtilityDefinitions(None)
    print('readUtilityDefinitions:')
    for name, jsonStatement in utilityDefinitions.items():
        print( name)
        print('\tJSON:\n' + str(jsonStatement))




