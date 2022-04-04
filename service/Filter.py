#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   August 17, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         service/Filter.py
#   Purpose:        Filtering services applying the various filters that the user specifies from available
#                   options, stored in model/Filter.py, to various types of data, including text files,
#                   line oriented text log files (all Linux logs), and database tables.
#   Development:
#       2021-08-19:
#           Since filtering is also searching, filtering can also be applied to any XML file, such as HTML and
#           the MS Office docx and other 'x' application file types.  JSON can be searched and fliltered as well,
#           as can source code.  Where a parse tree is available, as with HTML, XML, ad Python via the Abstract
#           Syntax Tree module, then those also can be searched and filtered.  THis will work well in a
#           ttk.Treeview since branches containing matches can be expanded while those without can be collapsed.
#
#       2022-03-08:
#           For each SQLite DB table that can be displayed, a separate FilterManager object
#           must be constructed.
#           The DataPane in fileHero can only load tables from the Search.db
#           database, which has the scans of folders the user is interested in searching
#           or backing up.
#           The general SQLiteDB tool will work with any SQLite database, however.
#           The FilterManager will be able to store filters the user has used or just configured
#           for various tables in various databases, and will be able to apply stored filters
#           to compatible columns in any SQLite database.
#

from os.path import isfile
from sys import stderr
from collections import Counter, OrderedDict, ChainMap, namedtuple
from copy import deepcopy
from enum import Enum
import difflib
import re

#   import Levenshtein as closematcher
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
"""
fuzz.ratio("this is a test", "this is a test!")
fuzz.partial_ratio("this is a test", "this is a test!")
fuzz.ratio("fuzzy wuzzy was a bear", "wuzzy fuzzy was a bear")
fuzz.token_sort_ratio("fuzzy wuzzy was a bear", "wuzzy fuzzy was a bear")
fuzz.token_sort_ratio("fuzzy was a bear", "fuzzy fuzzy was a bear")
fuzz.token_set_ratio("fuzzy was a bear", "fuzzy fuzzy was a bear")

>>> choices = ["Atlanta Falcons", "New York Jets", "New York Giants", "Dallas Cowboys"]
>>> process.extract("new york jets", choices, limit=2)
    [('New York Jets', 100), ('New York Giants', 78)]
>>> process.extractOne("cowboys", choices)
    ("Dallas Cowboys", 90)

"""


from tkinter import Tk, messagebox

from model.DBInterface import TableDescriptor, ColumnAttrib

PROGRAM_TITLE = "Filter Services"


class ValueType:
    MATCH       = 'Match'
    LOWER       = 'Lower'
    UPPER       = 'Upper'
    RADIUS      = 'Radius'

    def __str__(self):
        return self.value


class SearchType(Enum):
    EXACT       = 'Exact'
    GREATER     = 'Greater'
    LESS        = 'Less'
    RADIUS      = 'Radius'
    FUZZY       = 'Fuzzy'
    GREP        = 'GREP'
    RANGE       = 'Range'

    def __str__(self):
        return self.value


class DataType(Enum):
    TEXT            = 'Text'
    INTEGER         = 'Integer'
    REAL            = 'Real'
    BOOLEAN         = "Boolean"
    DATE            = 'Date'
    TIME            = 'Time'
    DATE_TIME       = 'Date-Time'
    PHONE_NUMBER    = 'Phone NUmber'
    EMAIL_ADDR      = 'Email Address'
    URL             = "URL"
    POSTAL_CODE     = 'Postal Code'


class FilterDescriptor:
    pass


class MatchManager:

    def __init__(self):
        self.matchesMap = {}

    def addMatch(self, searchString: str, matches: tuple):
        if searchString is None or not isinstance(searchString, str):
            raise Exception("MatchManager.addMatch - invalid searchString argument:\t" + str(searchString))
        matchesValid = True
        if matches is None or not isinstance(matches, tuple):
            matchesValid = False
        for match in matches:
            if not isinstance(match, StrMatch) or not isinstance(match.span, tuple) or not len(match.span) == 2:
                matchesValid = False
                break
        if not matchesValid:
            raise Exception("MatchManager.addMatch - invalid matches argument:\t" + str(matches))
        self.matchesMap[searchString] = deepcopy(matches)

    def findAllInText(self, searchString: str, text: str, caseSensitive: bool=True, wordsOnly: bool = False):
        if searchString is None or not isinstance(searchString, str):
            raise Exception("MatchManager.findAll - invalid searchString argument:\t" + str(searchString))
        if text is None or not isinstance(text, str):
            raise Exception("MatchManager.findAll - invalid text argument:\t" + str(text))
        matches = []
        """
        use "".find(string, start, end) incrementing start to after the previous find on each itteration, adding
        StrMatch objects tho a matches array.
        matches array is case as a tuple when logged into the MatchManager object.
        """
        if not caseSensitive:
            searchString = searchString.lower()
            text = text.lower()
        charIdx     = 0
        foundIdx    = 0
        strLen      = len(searchString)
        textLen     = len(text)
        while foundIdx != -1 and charIdx < len(text):
            foundIdx = text.find(searchString, charIdx)
            if foundIdx != -1:
                if wordsOnly:
                    if foundIdx == 0:
                        wordFound = text[foundIdx+strLen] in (' ', '\n', '\t')
                    elif foundIdx == textLen - strLen:
                        wordFound = text[foundIdx-1] in (' ', '\n', '\t')
                    else:
                        wordFound = text[foundIdx-1] in (' ', '\n', '\t') and text[foundIdx+strLen] in (' ', '\n', '\t')
                    if wordFound:
                        span = (foundIdx, foundIdx + strLen)
                        matches.append(StrMatch(span))
                    charIdx = foundIdx + len(searchString)
                else:
                    span = (foundIdx, foundIdx + strLen)
                    matches.append(StrMatch(span))
                    charIdx = foundIdx + len(searchString)
        self.matchesMap[searchString] = tuple(matches)
        return self.matchesMap[searchString]


    def findInTableCol(self, filterConfig: dict, tableData: list, columnIndex: int):
        if filterConfig is None or not isinstance(filterConfig, dict):
            raise Exception("MatchManager.findInTableCol - Invalid filterDescriptor argument:  " + str(filterConfig))
        if tableData is None or not (isinstance(tableData, list) or isinstance(tableData, tuple)):
            raise Exception("MatchManager.findInTableCol - Invalid tableData argument:  " + str(tableData))
        if columnIndex is None or not isinstance(columnIndex, int):
            raise Exception("MatchManager.findInTableCol - Invalid columnIndex argument:  " + str(columnIndex))
        print("\nMatchManager.findInTableCol is running\n")
        """
        Integer search filterConfig:
        filterConfig{'dataType': 'integer', 
                    'searchType': 'Value Range', 
                    'columnName': 'inode', 
                    'integerEntry': {
                        'matchType': 'Value Range', 
                        'lowValue': '0', 
                        'highValue': '0', 
                        'radius': None
                        }
                    }
        """
        """
        model.Filter:
        FILTER_DATA_TYPES       = ("dateTime", "date", "time", "timeStamp", "text", "integer", "real", "fuzzy match")
        TEXT_FILTER_TYPES       = ('Exact Match', 'Fuzzy Match', 'Regular Expression', 'Thesaurus')
        NUMERIC_FILTER_TYPES    = ('High Value', 'Low Value', 'Value Range', 'Equals', 'Equals with Radius')
        DATETIME_FILTER_TYPES   = ('Earliest', 'Latest', 'Date-Time Range', 'Equals', 'Equals with Radius')
        DATE_FILTER_TYPES   = ('Earliest', 'Latest', 'Date Range', 'Equals', 'Equals with Radius')
        TIME_FILTER_TYPES   = ('Earliest', 'Latest', 'Time Range', 'Equals', 'Equals with Radius')
        DATA_SET_TYPES          = ('table', 'list', 'lines', 'text stream', 'string')

        """

        self.tableData = tableData
        self.columnIndex = columnIndex

        self.fuzzyType   = filterConfig['fuzzyType']     #   'Percent' or 'grep'
        self.setType     = filterConfig['setType']       #   'List' or 'Set'
        self.dataType    = filterConfig['dataType']      #   'text' in initial case: filePath column, index = 1
        self.searchType  = filterConfig['searchType']    #   'Exact Match' in initial case.
        self.columnName  = filterConfig['columnName']    #   'folderPath' in initial case.
        filtered = []
        filteredRows = []

        if filterConfig['dataType'] == 'integer':
            if filterConfig['integerEntry']['lowValue'] is not None:
                self.lowValue = int(filterConfig['integerEntry']['lowValue'])
            else:
                self.lowValue = 0
            if filterConfig['integerEntry']['highValue'] is not None:
                self.highValue = int(filterConfig['integerEntry']['highValue'])
            else:
                self.highValue = 0
            if filterConfig['integerEntry']['radius'] is not None:
                self.radius = int(filterConfig['integerEntry']['radius'])
            else:
                self.radius = 0
            if self.searchType == 'High Value':
                filtered = filter(self.filterIntFieldHighValue, self.tableData)
            elif self.searchType == 'Low Value':
                filtered = filter(self.filterIntFieldLowValue, self.tableData)
            elif self.searchType == 'Value Range':
                filtered = filter(self.filterIntFieldRange, self.tableData)
            elif self.searchType == 'Equals':
                filtered = filter(self.filterIntFieldEqual, self.tableData)
            elif self.searchType == 'Equals with Radius':
                filtered = filter(self.filterIntFieldRadius, self.tableData)

        elif filterConfig['dataType'] == 'text':
            self.text        = filterConfig['stringEntry']['text'].split(',')
            if len(self.text) == 1:
                self.text = self.text[0]
            self.percentMatch    = int(filterConfig['stringEntry']['percentSpinner'])
            if self.fuzzyType == 'Percent':
                if self.percentMatch == 100:
                    if isinstance(self.text, str):
                        filtered = filter(self.filterTextField, self.tableData)
                    else:
                        if self.setType == 'List':
                            pass
                        elif self.setType == 'Set':
                            pass
                else:       #       fuzzy search
                    pass
            elif self.fuzzyType == 'grep':
                pass


        for row in filtered:
            filteredRows.append(row)

        #   Potential console output for filter feature:
        #
        #   print("\nOriginal:")
        #   for row in tableData:
        #       print(row[columnIndex])
        #   print("\nFiltered:")
        #   for row in filteredRows:
        #       print(row)
        return filteredRows

    def filterTextField(self, tableRow):
        return self.text in tableRow[self.columnIndex]

    def filterIntFieldEqual(self, tableRow):
        return self.lowValue == tableRow[self.columnIndex]

    def filterIntFieldHighValue(self, tableRow):
        return self.lowValue >= tableRow[self.columnIndex]

    def filterIntFieldLowValue(self, tableRow):
        return self.lowValue <= tableRow[self.columnIndex]

    def filterIntFieldRange(self, tableRow):
        return self.lowValue <= tableRow[self.columnIndex] <= self.highValue

    def filterIntFieldRadius(self, tableRow):
        return self.lowValue - self.radius <= tableRow[self.columnIndex] <= self.lowValue + self.radius

    def findString(self):
        pass

    def findDateTime(self):
        pass

    def findNumber(self):
        pass

    def findBoolean(self):
        pass


class StrMatch:
    """
    This is for "".find() feature.
    So that all literal strings are not treated as regular expressions, which happens when the user wants to use
    regex control or special characters in a literal string search, the python str.find() method must be applied.
    So that the tkinter.Text display is updated with the same method in the Help and other searchable text dialogs,
    a functionally equivalent structure must be used for the re module's match and matches structures.
    In the case of a literal string search, the matches list will contain as elements instances of this StrMatch class.
    To keep previous results readily available without having to repeat the work of repeated string searches,
    there also needs to be a Matches class which stores instances of matches, the lists of find()s.
    """
    def __init__(self, span: tuple):
        if span is None or not isinstance(span, tuple) or not len(span) == 2 or not isinstance(span[0], int) \
                or not isinstance(span[1], int):
            raise Exception("StrMatch constructor - invalid span argument:\t" + str(span))
        self.span = span        #   two entry tuple, same as re package's match.span

    def __str__(self):
        return "span:\tlocation = " + str(self.span[0]) + "\tlength=" + str(self.span[1]-self.span[0])


class FilterDescriptor:

    def __init__(self, filterConfig: dict ):
        print("FilterDescriptor constructor - filterConfig" + str(filterConfig))
        if  not isinstance(filterConfig, dict):
            raise Exception("FilterDescriptor constructor - Invalid filterConfig argument:  " + str(filterConfig))

        self.filterConfig = deepcopy( filterConfig)
        self.matchValues = {}
        if 'stringEntry' in self.filterConfig:
            self.matchValues[ValueType.MATCH]  = self.filterConfig['stringEntry']['text']
        #   percent match?, radius?, thesaurus depth?,
        self.searchDescriptor = {}
        self.matchManager = MatchManager()

    def getFilterConfig(self):
        return self.filterConfig

    def getValue(self, valueType: ValueType):
        if isinstance(valueType, ValueType):
            return self.matchValues[valueType]

    def getMatchManager(self):
        return self.matchManager

    #   Only allow setting of the value to be searched on.
    #   This includes single values, upper and lower values of ranges, and radius.
    def setValue(self, valueType: ValueType, value):
        if isinstance(valueType, ValueType):
            #   Check type, then:
            self.matchValues[valueType]     = value


class FilterManager:
    """
    Stores and manages the filters designed for and applied to an SQLite database table.
    """
    def __init__(self, tableDescriptor: TableDescriptor):
        if tableDescriptor is None or not isinstance(tableDescriptor, TableDescriptor):
            raise Exception("FilterManager constructor - Invalid tableDescriptor argument:  " + str(tableDescriptor))
        self.tableDescriptor = deepcopy( tableDescriptor )
        self.filters = OrderedDict()

    def checkArguments(self, name: str, filterDescriptor: FilterDescriptor):
        if name is None or not isinstance(name, str):
            raise Exception("FilterManager.checkArguments - Invalid name argument:  " + str(name))
        if filterDescriptor is None or not isinstance(filterDescriptor, FilterDescriptor):
            raise Exception("FilterManager.checkArguments - Invalid filterDescriptor argument:  " + str(filterDescriptor))

    def addFilter(self, name: str, filterDescriptor: FilterDescriptor):
        self.checkArguments(name, filterDescriptor)
        if name in self.filters:
            #   raise Exception("FilterManager.addFilter - Invalid name argument:  " + str(name))
            print("FilterManager.addFilter - replacing existing filter with new one with same name:\t" + str(name), file=stderr)
        self.filters[name] = deepcopy( filterDescriptor )

    def replaceFilter(self, name: str, filterDescriptor: FilterDescriptor):
        self.checkArguments(name, filterDescriptor)
        if name not in self.filters:
            raise Exception("FilterManager.replaceFilter - Invalid name argument:  " + str(name))
        self.filters[name] = deepcopy( filterDescriptor )

    def removeFilter(self, name):
        if name in self.filters:
            del(self.filters[name])

    def runFilter(self, name: str, tableData: list):
        if name not in self.filters:
            raise Exception("FilterManager.runFilter - Invalid name argument:  " + str(name))
        if tableData is None or not (isinstance(tableData, list) or isinstance(tableData, tuple)):
            raise Exception("FilterManager.runFilter - Invalid name argument:  " + str(name))

        colIdx = self.tableDescriptor.tableInfo['columns'][self.filters[name].filterConfig['columnName']][ColumnAttrib.INDEX]
        return self.filters[name].getMatchManager().findInTableCol(self.filters[name].filterConfig, tableData, colIdx)


class FilterBase:

    COMPARE_RESULTS = ("is less", "is equal", "is greater")
    IS_LESS = "is less"
    IS_EQUAL = "is equal"
    IS_GREATER = "is greater"

    DATA_SET_TYPES = ("Set", "Series", "Map", "Index")
    """
    If the type is a Set, a reference to the actual matching elements must be returned.
    If it is a Series, only an ordered list of indices of the matching elements needs to be returned.
    For a map, a set or list of keys is the return value.
    An index is used to reference an ordered list of values.  Unlike a map, it is ordered, and for type
    security must be passed in as an OrderedDict, The values themselves can reside anywhere, since only 
    references to them are passed in for filtering.
    Indexed filtering returns an identically typed index with only the indexes of those elements which
    passed the filter.  
    For this service to be thread safe, it would have to make deepcopy()'s of all of the dataset being filtered. 
    All dataSetType's are passed in as references to lists, tuples, sets, or maps.
    """

    def __init__(self, dataSet, dataSetType: str, filterMethod = None, compareMethod=None):
        if dataSetType is None or not isinstance(dataSetType, str) or dataSetType not in FilterBase.DATA_SET_TYPES:
            raise Exception("FilterBase constructor - invalid dataSetType argument:\t" + str(dataSetType))
        if dataSet is None:
            raise Exception("FilterBase constructor - dataSet argument is None")
        if dataSetType == "Set":
            if not isinstance(dataSet, set) and not isinstance(dataSet, tuple) and \
                    not isinstance(dataSet, list) and not isinstance(dataSet, dict):
                raise Exception("FilterBase constructor - dataSet argument type, Set,  is incompatible with "
                                "dataSetType:\t" +  str(type(dataSet)))
        elif dataSetType == "Series":
            if not isinstance(dataSet, tuple) and not isinstance(dataSet, list):
                raise Exception("FilterBase constructor - dataSet argument type, Series, is incompatible with "
                                "dataSetType:\t" + str(type(dataSet)))
        elif dataSetType == "Map":
            if not isinstance(dataSet, dict):
                raise Exception("FilterBase constructor - dataSet argument type, Map,  is incompatible with "
                                "dataSetType:\t" +  str(type(dataSet)))
        elif dataSetType == "Index":
            if not isinstance(dataSet, OrderedDict):
                raise Exception("FilterBase constructor - dataSet argument type, Index,  is incompatible with "
                                "dataSetType:\t" +  str(type(dataSet)))
        if filterMethod is not None and not callable(filterMethod):
            raise Exception("FilterBase constructor - invalid filterMethod argument:\t" + str(filterMethod))
        if compareMethod is not None and not callable(compareMethod):
            raise Exception("FilterBase constructor - invalid compareMethod argument:\t" + str(compareMethod))
        self.dataSetType = dataSetType
        self.dataSet = dataSet
        self.filterMethod = filterMethod
        if compareMethod == None:
            self.compareMethod = self.compare
        else:
            self.compareMethod = compareMethod

    def compare(self, leftElement, rightElement):
        """
        This base method does only a standard string or numeric comparison and must be overridden for other types.
        :param elemet_1:
        :param element_2:
        :return:
        """
        if leftElement > rightElement:
            return FilterBase.IS_GREATER
        elif leftElement < rightElement:
            return FilterBase.IS_LESS
        return FilterBase.IS_EQUAL

    def setCompareMethod(self, compareMethod):
        """
        A valid compare method compares a left value to a right value and returns IS_LESS if the left is
        before the right in the sorting order being constructed, IS_EQUAL if they belong in the same location,
        and IS_GREATER if the left belongs after the right.
        This is the better method to use to find all elements that belong either after or before a reference
        element in a particular sorting order, e.g. dates, times, numbers, ...
        :param compareMethod:
        :return:
        """
        if compareMethod is not None and callable(compareMethod):
            self.compareMethod = compareMethod
            return True
        return False

    def setFilterMethod(self, filterMethod):
        """
        A valid filter method returns tru if the element should pass the filter and false if it should not.
        :param filterMethod:
        :return:
        """
        if filterMethod is not None and callable(filterMethod):
            self.filterMethod = filterMethod
            return True
        return False

    def process(self):
        """
        Filter the dataSet and return an "index" of the filtered elements.
        :return:
        """
        pass


class TextLineFilter(FilterBase):

    def __init__(self, dataSet):
        FilterBase.__init__(self, dataSet, "Series")


class DBTableFilter(FilterBase):

    def __init__(self, dataSet):
        FilterBase.__init__(self, dataSet, "Series")


class DBTableColumnFilter(FilterBase):

    def __init__(self, dataSet):
        FilterBase.__init__(self, dataSet, "Series")


class FileMetaDataFilter(FilterBase):

    def __init__(self, dataSet):
        if isinstance(dataSet, set):
            FilterBase.__init__(self, dataSet, "Set")
        elif isinstance(dataSet, tuple) or  isinstance(dataSet, list):
            FilterBase.__init__(self, dataSet, "Series")
        elif isinstance(dataSet, dict):
            FilterBase.__init__(self, dataSet, "Map")
        elif isinstance(dataSet, OrderedDict):
            FilterBase.__init__(self, dataSet, "Index")


class ExifDataFilter(FilterBase):

    def __init__(self, dataSet):
        if isinstance(dataSet, set):
            FilterBase.__init__(self, dataSet, "Set")
        elif isinstance(dataSet, tuple) or  isinstance(dataSet, list):
            FilterBase.__init__(self, dataSet, "Series")
        elif isinstance(dataSet, dict):
            FilterBase.__init__(self, dataSet, "Map")
        elif isinstance(dataSet, OrderedDict):
            FilterBase.__init__(self, dataSet, "Index")


class Token:

    def __init__(self, text: str, lineIdx: int, colIdx: int, charIdx: int=None):
        if text is None or not isinstance(text, str) or lineIdx is None or not isinstance(lineIdx, int) \
                or colIdx is None or not isinstance(colIdx, int):
            raise Exception("Token constructor - invalid token argument")
        self.text = text
        self.lineIdx = lineIdx
        self.colIdx = colIdx
        Attributes = namedtuple('Attributes', ('text', 'lineIdx', 'colIdx'))
        self.attrTuple = Attributes(text=self.text, lineIdx=self.lineIdx, colIdx=self.colIdx)

    #   immutable
    def __setattr__(self, key, value):
        if key not in self.__dict__:
            self.__dict__[key] = value
        else:
            print("Immutable Token attribute already set:\t" + key, file=stderr)

    def __str__(self):
        text = "Token:\t\ttext:\t" + str(self.text) + "\t\tlineIdx:\t" + str(self.lineIdx) + "\t\tcolIdx:\t" + \
               str(self.colIdx)
        if "charIdx" in self.__dict__:
            text += "\t\tcharIdx:\t" + str(self.charIdx)
        return text


class LineSequence:

    def __init__(self, dataRef):
        """

        :param dataRef: Must be an ordered list, tuple, or set of lines.  A dict is not ordered, nor is a set,
        so for a dict to be used it must be an OrderedDict .
        The only valid types for the dataRef are therefore text file path, str, list, tuple, or OrderedDict.
        """
        self.lines = ()
        self.tokens = None
        self.text = None
        if isfile(dataRef):
            #   Check somehow to see if the content is all text.

            file = open(dataRef, "r")
            #   store a reference to the text
            self.text = file.read()
            self.lines = tuple(self.text.split("\n"))
            file.close()
        elif isinstance(dataRef, str):
            self.text = dataRef
            self.lines = tuple(self.text.split("\n"))
        elif isinstance(dataRef, list) or isinstance(dataRef, tuple):
            self.lines = ()
            strings = True
            for element in dataRef:
                if not isinstance(element, str):
                    strings = False
                    break
            if strings:
                #   For efficiency, only the reference is copied.
                #   A secure mode can be used but requires local deepcopy()s of everything, including large
                #   data sets.
                self.lines = dataRef
        elif isinstance(dataRef, OrderedDict):
            self.lines = ()
            strings = True
            for key, element in dataRef.items():
                if not isinstance(element, str):
                    strings = False
                    break
            if strings:
                self.lines = []
                for key, element in dataRef.items():
                    self.lines.append(element)
                self.lines = tuple(self.lines)

    def tokenize(self):
        """
        Produce a map in which line numbers are the keys and a tuple of Token's are the values.
        The Token's store the character index in the line, referred to as the colIdx, starting at 0 for the
        first character. This is designed to be easily used with the tkinter.Text component.
        A flat tuple of Token's with the absolute character position of each in the text might also
        be required.  This is only possible if the tokenization was done on a text rather than a list, tuple,
        or dict whose elements were lies.  This is done in a separate step by an in-order scan of the map
        storing the tokens, taking into account the implied newline characters removed by the original
        split('\n').

        This does not yet take into account separator characters, such as punctuation, parentheses, brackets,
        curly braces, etc.  This should be an option in the arguments to this method.
        :return:
        """
        self.tokens = {}
        lineIdx = 1
        for line in self.lines:
            tokenList = line.split()
            colIdx = 0
            lineTokens = []
            for token in tokenList:
                foundIdx = line.find(token, colIdx)
                lineTokens.append(Token(token, lineIdx, colIdx))
                colIdx = foundIdx + len(token)
            self.tokens[lineIdx] = tuple(lineTokens)
            lineIdx += 1

        #   Now record the absolute character position if possible
        if self.text is not None:
            lineIdx = 1
            charSum = 0
            while lineIdx in self.tokens and lineIdx <= len(self.lines):
                for token in self.tokens[lineIdx]:
                    token.charIdx = charSum + token.colIdx
                charSum += len(self.lines[lineIdx-1]) + 1
                lineIdx += 1


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


def stringMatchFilter(searchString, text, matchType):
    """
    Does searchString exist in the text using the matchType.
    if so, return a start location, column index, and a last location as a tuple.
    If not return None.
    :param searchString:
    :param text:
    :param matchType:
    :return:
    """
    if searchString in text:
        return True
    return None


#   for testing only
from model.Util import pathFromList, INSTALLATION_FOLDER, APP_DATA_FOLDER

if __name__ == '__main__':

    ages    = [5, 12, 17, 18, 24, 32]
    def myFunc(x):
        return x >= 18
    adults = filter(myFunc, ages)
    print("adults:\t" + str(adults))
    for x in adults:
        print(x)
    exit(0)


    mainView = Tk()
    mainView.geometry("800x500+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    fileRef = pathFromList((INSTALLATION_FOLDER, APP_DATA_FOLDER, "dmesg.2021-07-10.log"))
    print("\nText source:\t" + fileRef)

    dmesgLogSequence = LineSequence(fileRef)
    dmesgLogSequence.tokenize()
    for lineIdx, lineTokens in dmesgLogSequence.tokens.items():
        text = ''
        for token in lineTokens:
            text += str(token) + ',\t'
        print("Line Tokens:\t(" + text + ')')

    matchManager = MatchManager()
    lineNumber = 1
    filteredElements = []
    for line in dmesgLogSequence.lines:
        matches = matchManager.findAllInText('usb', line, caseSensitive=True)
        if len(matches) > 0:
            print("\n" + str(lineNumber) + ":\t" + line)
            filteredElements.append((lineNumber, matches))
            for match in matches:
                print("\t" + str(match))
        lineNumber += 1

    """
    next: apply fuzzy matching to a tokenized text from a source typically used for investigation of the 
    activities of a linux os.
    Need a tokenizer that records each token's position in the text, both by line (1..n) and character (0..n-1)
    address and absolute character count addressing.
    """
    """
    Also need to make use of python's built in filter() method and compare performance of it and a "pure" python
    solutions written by me.
    """

    mainView.mainloop()

