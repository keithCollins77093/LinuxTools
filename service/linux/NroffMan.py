#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 15, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         NroffMan
#   Purpose:        GNU / Linux shell out command gui generator.
#   Development:
#       Read in nroff input files into a class instance and be able to use the class instance to interpret the
#       nroff file contents as a Linux coreutils man page, so that a GUI for the util which the man page is for
#       can be generated.
#   2019-02-16
#       If a line starts with a dot, then it is a markup instruction, refered to in the nroff documentation as a request.
#       If the rest of the line is a one or two capital letters, then it is a nroff macro.  Most macros in man page
#       nroff files are specialized for man pages.  A list of the common ones is included as NroffScanner class constants.
#       Since lines starting with dots have requests only on them, they are easily recognized.  These can be placed
#       into a sequential list with the text they affect as properties of the structure or object that they format.
#       Text can have embedded in it escape sequences, which are composed of a backslash followed by a sequence of
#       charaters that can be one, two, three, ... characters in length.  A complete catalog of these is impossible
#       to find online.  I tried yesterday.  Therefore, no attempt will be made to account for them or catalog them.
#       They can only be separated with either knowledge of the text content displayed when nroff is run on the file
#       to display the man page, or with knowledge of all of the possible sequences.  The display text can be obtained
#       either by running man on the command name, or by running nroff on the man page nroff input file.  For the
#       GNU coreutils, these are located currently in the unzipped source folder named coreutils-8.30/man/.
#       nroff on my installation prints out all of the text as a stream with all of the control requests stripped out.
#       Each file is a sequence of formatted text.
#
#       .\" appears to be the request at the beginning of a comment line.
#       The man macros appear to have particular formats:
#           .TH is the title header and is followed by the command name in upper case and then some descriptive text.
#               The first three elements are separated by spaces.
#           All of the section heading macros have the macro name and the section name in caps on a single line, with
#               the section text following.  The section heading is capitalized.
#               A section heading may be quoted.  The quotes can be removed.
#           man page section headings will always have this format, and are only in this format.
#
#   2019-02-22
#       Consider using regular expressions to find relevant secitons and escape sequences to identify the various
#       parts of a man page in these files.
#       A regular expression to strip all escape sequences leaving only macros would be a helpful initial step,
#       with the possibility of further analysis preserved by recording them and their locaitons in the original
#       document stream.
#

"""
Source: https://www.oreilly.com/library/view/unix-text-processing/9780810462915/Chapter04.html:

The nroff and troff markup commands (often called requests) typically consist of one or two lowercase letters and
stand on their own line, following a period or apostrophe in column one.
"""
#   macros are in upper case, start with a dot at the beginning of a line, and can be followed by parameters on the
#   same line.

import os, datetime

class FormattedText:
    def __init__(self, lineNumber: int, formatter: str, title: str, text: str):
        self.lineNumber = lineNumber
        self.formatter  = formatter
        self.title      = title
        self.text       = text

    def getLineNumber(self):
        return self.lineNumber

    def getFormatter(self):
        return self.formatter

    def getText(self):
        return self.text

    def __str__(self):
        string =    'FormattedText:'
        string +=   '\tlineNumber:\t' + str(self.lineNumber) + '\n'
        string +=   '\tformatter:\t' + str(self.formatter) + '\n'
        string +=   '\ttitle:\t' + str(self.title) + '\n'
        string +=   '\ttext:\t' + str(self.text) + '\n'
        return string

class UtilityNroffFileDescr:
    #   extendable utility file descriptor.
    #   use keyWordArguments to add custom properties to any instance
    def __init__(self, utilityName: str, fileName: str, **keyWordArguments):
        if utilityName == None or fileName == None:
            raise Exception('UtilityNroffFileDescr construcor - null in arguments')
        self.utilityName    = utilityName
        self.fileName       = fileName
        for name, value in keyWordArguments.items():
            self.__dict__[name]     = value

    def getAttr(self, name):
        if name in self.__dict__.keys():
            return self.__dict__[name]

    def getUtilityName(self):
        return self.utilityName

    def getFileName(self):
        return self.fileName

    def list(self):
        print("UtilityNroffFileDescr:")
        for name, value in self.__dict__.items():
            print( '\t' + name + ':\t' + str(value))


class NroffScanner:

    #   2021-08-21:   Change user folder of installation:
    MANROFF_FOLDER_SPEC        = '/home/keith/Cybersecurity/Linux Tools/coreutils-8.30/man/'
    #   MANROFF_FOLDER_SPEC        = '/home/keithcollins/Cybersecurity/Linux Tools/coreutils-8.30/man/'
    NROFF_FILE_EXTENSION    = '.1'

    #   nroff standard man page macros
    PAGE_               = '.TH'
    SECTION_            = '.SH'
    SUB_SECTION_        = '.SS'
    START_PARAGRAPH_    = '.PP'
    FOOTNOTE_STARTS_    = '.FS'
    FOOTNOTE_ENDS_      = '.FE'
    NO_DATE_            = '.ND'
    TITLE_              = '.TL'
    PARAMETER           = '.TP'     #   2018-02-18: This has not been done yet
    UNKNOWN_2           = '.B'


    @staticmethod
    def readNroffManFileList():
        if os.path.exists(NroffScanner.MANROFF_FOLDER_SPEC) and os.path.isdir(NroffScanner.MANROFF_FOLDER_SPEC):
            utilityFileList     = []
            fileList    = os.listdir(NroffScanner.MANROFF_FOLDER_SPEC)
            for name in fileList:
                if name.endswith(NroffScanner.NROFF_FILE_EXTENSION) and name != 'coreutils.1':
                    utilityFileList.append(UtilityNroffFileDescr(name.split(NroffScanner.NROFF_FILE_EXTENSION)[0],
                                                                      name, timeStemp=datetime.datetime.now()))
                    #   utilityFileList[len(utilityFileList)-1].list()
            return utilityFileList
        else:
            raise Exception('readNroffManFileList - invalid folder:\t' + NroffScanner.MANROFF_FOLDER_SPEC)

    def __init__(self, fileSpec: str = None):
        self.utilityFileList     = NroffScanner.readNroffManFileList()
        self.nroffStatements = {}
        self.nroffStatementsSectioned = {}
        for nroffManFile in self.utilityFileList:
            self.nroffStatementsSectioned[nroffManFile.utilityName] = \
                self.sectionNroffFile(NroffScanner.MANROFF_FOLDER_SPEC + nroffManFile.fileName)
            #   self.nroffStatements[ nroffManFile.utilityName ]   = self.scanNroffFile(NroffScanner.TEST_FOLDER_SPEC + nroffManFile.fileName )


    def scanNroffFile(self, filePath):
        nroffStatements = []  # the list of formatted text lines in the nroff file
        nroffFp = open(filePath, 'r')
        nroffLines = nroffFp.read().split('\n')
        nroffFp.close()
        lineNumber = 1
        formatter = ''
        text = ''
        sectionStart = False
        textStarted = False
        sectionHeadingLineNum = None
        for line in nroffLines:
            if line.startswith(NroffScanner.SECTION_):
                #   Is this the end of a previous section?
                if textStarted == True and sectionHeadingLineNum != None:
                    nroffStatements.append(FormattedText(sectionHeadingLineNum, formatter,
                                                                           headerText.strip(), text.strip()))
                    text = ''
                    textStarted == False
                sectionHeadingLineNum = lineNumber
                print("section found at line number:\t" + str(lineNumber))
                line = line.replace('"', '')
                parts = line.split(' ')
                formatter = parts[0]
                if parts[0] == NroffScanner.SECTION_:
                    sectionStart = True
                    headerText = ''
                    partIdx = 1
                    while partIdx < len(parts):
                        headerText += parts[partIdx]
                        if partIdx < len(parts):
                            headerText += ' '
                        partIdx += 1

            else:
                sectionStart = False
                if sectionHeadingLineNum != None:
                    textStarted = True
                    text += line + '\n'

            lineNumber += 1
        return nroffStatements

    def sectionNroffFile(self, filePath):
        nroffFp = open(filePath, 'r')
        nroffText = nroffFp.read()
        nroffFp.close()
        nroffFormattedSections  = {}
        nroffTextSections = nroffText.split(NroffScanner.SECTION_)
        for section in nroffTextSections:
            #print(nroffTextSections)
            sectionLines    = section.split('\n')
            if len(sectionLines) > 0:
                sectionName     = sectionLines[0].strip().replace('"', '')
                #print('Section Name:\t*' + sectionName + "*")
                text = ''
                firstLine   = True
                for line in sectionLines:
                    if firstLine:
                        firstLine   = False
                    else:
                        text += line + '\n'
                nroffFormattedSections[sectionName]  = FormattedText(-1, NroffScanner.SECTION_, sectionName, text)
        #   for name, formattedText in nroffFormattedSections.items():
            #   print(formattedText)
        return nroffFormattedSections


    def getNroffStatements(self):
        return self.nroffStatements

    def list(self):
        for key, manPage in self.nroffStatements.items():
            print( 'coreutil:\t' + key)
            for formattedText in manPage:
                print(formattedText)


if __name__ == "__main__":
    nroffMan = NroffScanner(None)
    # print()
    # nroffMan.list()


