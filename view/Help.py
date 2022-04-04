#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   August 11, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/Help.py
#   Purpose:        Help sub-system dialog.
#   Development:
#
#       2021-08-11:
#           Need a popup menu that appears anywhere and shows the help dialog option along with context dependent
#           options.
#           The general help dialog will display help in a searchable tkinter.Text component and will have a list
#           of topics which the use can select from, each of which has its own text to display in the Text.
#           This will be in a tkinter.Toplevel so that the user can switch to it at any time, and which will
#           toggle with the same help menu item selection.
#
#           The help dialog should market the product by showing the user how it is used, what it can be used for,
#           the value of its features, and any caveats respecting where it is going to break depending on platform
#           idiosyncracies.  See the first page of "man ps" for for a good example of this.  The built in tools
#           will not work correctly on some versions of posix.  They should be guaranteed to work on any debian
#           installation, however, since debian is the best choice for security and general (mass market) usability.
#
#           This particular help dialog is context dependent, meaning it will not display any and every help topic
#           nor will it search the entire help database.  It will have topic selections particular to the context
#           in which the pop-up menu launching it was activated.  This ties the user's right click location to
#           the particular content.
#
#           This module will also be used to develop the general help dialog.
#           An SQLite database will contain all of the general help topics and text and will be searchable using
#           all of the search and filter methods available in the SQLiteDB view module for searching tables
#           in a forensic workflow.
#
#           Feature / Use:
#               Load linux man pages saved using view.Console.py and search them for particular content using all
#               filters available in the DB Table column filtering dashboard (view.SQLiteDB.py).
#               Design searches / filters which are frequently used to search through man pages using Linux
#               utilities like grep, sed, & awk.
#
#       2021-08-13:
#           Features needed in search tool bar:
#               case sensitive toggle, words only toggle, show matches count, messages label.
#                   these should be in a separate row below the main row and present in a pop-up check-menu with
#                   tearoff=1:
#                           messages bar        (default is False)
#                           case sensitive      (default is True)
#                           words only          (default is False)
#                           show count          (default is True)
#                           location spinner    (default is False)
#               "active" highlight on first match and a spinbox allowing user to go to next or previous match
#                   with index of match showing in spinbox
#               a popup menu for matches.
#                   links to other features which can use the output of this search.
#               a popup menu which is different for "active" matches.
#
#       2021-08-15:
#           More features needed in search tool bar:
#               Immediate update when any of the boolean search criteria are changed, e.g. case sensitivity or
#               whole words only, or regular Expressions.
#               Message bar can just show tool tip text for now.
#               Can tool tips be displayed for check menu items?  Mouse enter and leave events can only be
#               detected on components, and add_command does not create a separate component.  Mouse enter on
#               the menu itself can be detected.  This, however, would be a long tool tip.
#               Toggle for number search, integer and real.
#               Other types of data, like email addresses, urls, phone numbers, addresses.
#               This should be done with built in regular expressions and the user should be able to
#               add their own to the menu.
#               A line filtering mode wold also be useful.  Treat the text as a sequence of lines which are
#               rows in a table and remove those that do not meet the filter criteria.  Criteria can include
#               such constraints as: contains a date or has a time stamp before, after or between user provided
#               ones.  Any string, regex, time, date or numeric filter should be available or designable.
#
#       2021-08-16:
#           Question: How would you automate searching for any state, city, or other political or geographical
#           entity?
#
#       2021-08-17:
#           Add fuzzy string matching to token index only in this module, along with any tokenized text.
#           as long as the user selects "Words Only" for searching, fuzzy matches are possible on any text.
#           User will be able to specify a fuzzy ratio or percent match or percent distance, and since
#           most users are unfamiliar with fuzzy matching, a mouse over on the tag created for the match
#           in a tkinter.Text should show the fuzzy distance or closeness in a tool tip or message label.
#
#       2021-08-24:
#           The user should have the ability to live configure the search tool bar here, including more features
#           or fewer.  They can explore the search and filtering capabilities in a safe environment while
#           learning how to use them and studying any other content that the Help sub-system provides.
#           The access to live-configuration should not be included in the search bar itself, but should be a
#           separate menu item or button.
#           A configuration sus-system will include configuration of the search bar for various contexts, and
#           these should be identical to the live search bar configuration options.
#

import os, re
from copy import deepcopy

from tkinter import Tk, Toplevel, Frame, LabelFrame, Button, Label, Entry, Checkbutton, Listbox, Text, Menu, \
                    Scrollbar, Spinbox, messagebox, scrolledtext, \
                    NONE, X, Y, BOTH, TOP, BOTTOM, LEFT, RIGHT, SINGLE, MULTIPLE, BROWSE, EXTENDED, END,  \
                    FLAT, SUNKEN, RIDGE, RAISED, GROOVE, VERTICAL, HORIZONTAL,  \
                    StringVar, IntVar, BooleanVar, \
                    DISABLED, NORMAL, WORD, \
                    StringVar

from model.HelpContent import HelpContent
from model.Util import pathFromList, INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER
from service.Filter import MatchManager, StrMatch
from view.SearchComponents import SearchEntryBar

PROGRAM_TITLE = "Help Dialog"


class HelpAndApproval(Toplevel):

    def __init__(self, container, title: str, helpText: str, geometry: str, listener=None, **keyWordArguments):
        Toplevel.__init__(self, container, keyWordArguments)
        if listener is not None and callable(listener):
            self.listener = listener
        else:
            self.listener = None
        if geometry is None:
            self.geometry("800x300+200+150")
        elif isinstance(geometry, str):
            self.geometry(geometry)
        else:
            raise Exception("HelpAndApproval constructor - Invalid geometry argument:\t" + str(geometry))
        if isinstance(title, str):
            self.title(title)
            self._title = title
        else:
            self.title("Help - I need your approval")
            self._title = "Help - I need your approval"
        lineCount = max(len(helpText.split('\n'))-5, 10)
        scrolledHelpText = scrolledtext.ScrolledText(self, border=5, relief=SUNKEN, wrap=WORD,
                                                     width=50, height=lineCount)
        scrolledHelpText.insert(END, helpText)
        scrolledHelpText.configure(state=DISABLED)

        goButton = Button(self, text="Go", command=self.sendGoMessage)
        cancelButton = Button(self, text="Cancel", command=self.sendCancelMessage)

        scrolledHelpText.pack(expand=True, fill=BOTH, padx=10, pady=10)
        goButton.pack(expand=True, fill=X, padx=10, pady=10)
        cancelButton.pack(expand=True, fill=X, padx=10, pady=10)

    def sendGoMessage(self):
        if self.listener is not None:
            self.listener({'sender': "HelpAndApproval.sendGoMessage",
                           'title': self._title})

    def sendCancelMessage(self):
        if self.listener is not None:
            self.listener({'sender': "HelpAndApproval.sendCancelMessage",
                           'title': self._title})


class HelpDialog(LabelFrame):

    DEFAULT_GEOMETRY    = "1100x550+50+50"
    DEFAULT_TITLE       = "Help Dialog"

    FOUND_FOREGROUND   = "blue"
    FOUND_BACKGROUND   = "yellow"

    ACTIVE_FOREGROUND = "#DDDDDD"
    ACTIVE_BACKGROUND = "#003333"

    SEARCH_FEATURE_SETS = ('all', 'default', 'console', 'jsonTree', 'squlitetable', 'text', 'textlist', 'tree', 'helpdialog')

    def __init__(self, container, helpContent: HelpContent, searchFeatureSet: str, geometryString: str, **keyWordArguments):
        if helpContent is None:
            raise Exception("HelpDialog constructor - help descriptor is null:\t" + str(helpContent))
        self.validDescriptor = True
        if not isinstance(helpContent, HelpContent):
            self.validDescriptor = False
        for key, value in helpContent.contentMap.items():
            if not isinstance(key, str) or not isinstance(value, str):
                self.validDescriptor = False
                break
        if not self.validDescriptor:
            raise Exception("HelpDialog constructor - invalid descriptor argument:\t" + str(helpContent))
        if searchFeatureSet is None or not isinstance(searchFeatureSet, str) or \
                not searchFeatureSet in HelpDialog.SEARCH_FEATURE_SETS:
            raise Exception("HelpDialog constructor - invalid searchFeatureSet argument:\t" + str(searchFeatureSet))
        LabelFrame.__init__(self, container, keyWordArguments)

        self.helpContent = deepcopy(helpContent)      #   thread safe
        self.matchManager = MatchManager()
        self.searchFeatureSet = searchFeatureSet

        self.topicSelected = None
        self.textLineIndex = None
        self.findTags = {}

        """
        AVAILABLE_FEATURES  = ("Case Toggle", "Words Toggle", "Messages", "Location Spinner", "Match Count",
                               "Regex Toggle", "Numeric", "Number", "Integer", "Real", "Data Type Regular Expressions",
                               "Auto-Update", "Line Filtering", "Search Type", "Tool Tips")
        DEFAULT_FEATURES    = ("Case Toggle", "Words Toggle", "Messages", "Regex Toggle", "Auto-Update", "Tool Tips",
                               "Line Filtering")
        
        """
        if self.searchFeatureSet == 'all':
            self.features = SearchEntryBar.AVAILABLE_FEATURES
        elif self.searchFeatureSet == 'default':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'console':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'jsonTree':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'squlitetable':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'text':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'textlist':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'tree':
            self.features = SearchEntryBar.DEFAULT_FEATURES
        elif self.searchFeatureSet == 'helpdialog':
            self.features = SearchEntryBar.HELP_FEATURES

        geometryParts = geometryString.split('x')
        geometryParts = [geometryParts[0],] + geometryParts[1].split('+')
        geometryParts = [int(dim) for dim in geometryParts]


        self.searchEntryBar = SearchEntryBar(self, listener=self.messageReceiver, dialogWidth=geometryParts[0],
                                             features=self.features, border=3, relief=SUNKEN)
        self.topics = list(self.helpContent.contentMap.keys())
        self.topicListbox = Listbox(self, border=4, relief=RAISED, selectmode=SINGLE)
        self.topicListbox.insert(END, *self.topics)
        self.topicListbox.bind('<<ListboxSelect>>', self.topicSelectionHandler)

        self.helpTextFrame  = Frame(self, width=geometryParts[0]-250, height=400)
        self.helpText   = Text(self.helpTextFrame, border=4, relief=SUNKEN, state=DISABLED, wrap=WORD,
                               fg="#000088", padx=10, pady=10)

        self.vertScrollBar    = Scrollbar(self, command=self.helpText.yview, orient=VERTICAL)
        self.horzScrollBar    = Scrollbar(self, command=self.helpText.xview, orient=HORIZONTAL)
        self.helpText.config(yscrollcommand=self.vertScrollBar.set,
                               xscrollcommand=self.horzScrollBar.set)

        self.buttonBar = Frame(self, border=3, relief=RIDGE, padx=5, pady=5)

        self.searchToggleVar    = BooleanVar()
        self.searchButton = Checkbutton(self.buttonBar, text="Search", variable=self.searchToggleVar)
        self.generalHelpButton = Button(self.buttonBar, text="General Help", command=self.generalHelpLaunch)
        self.notesButton = Button(self.buttonBar, text="Notes", command=self.notesLaunch)
        self.lineNumToggleVar = BooleanVar()
        self.lineNumbersToggle = Checkbutton(self.buttonBar, text="Line Numbers", variable=self.lineNumToggleVar)
        self.highliteToggleVar  = BooleanVar()
        self.highlightToggle = Checkbutton(self.buttonBar, text="Highlight", variable=self.highliteToggleVar)

        self.searchToggleVar.trace('w', self.toggleSearchEntry)
        self.lineNumToggleVar.trace('w', self.toggleLineNumbers)
        self.highliteToggleVar.trace('w', self.toggleHighliting)

        self.searchButton.grid(row=0, column=0, padx=5, pady=2)
        self.generalHelpButton.grid(row=0, column=1, padx=5, pady=2)
        self.notesButton.grid(row=0, column=2, padx=5, pady=2)
        self.lineNumbersToggle.grid(row=0, column=3, padx=5, pady=2)
        self.highlightToggle.grid(row=0, column=4, padx=5, pady=2)

        self.topicListbox.grid(row=1, column=0, columnspan=1, padx=5, pady=5, ipadx=5, ipady=5, sticky="nw")

        self.helpTextFrame.grid(row=1, column=1, columnspan=5, padx=5, pady=5, ipadx=5, ipady=5, sticky="nsew")
        self.helpTextFrame.columnconfigure(0, weight=10)
        self.helpTextFrame.grid_propagate(False)
        #   self.helpText.grid(row=1, column=1, columnspan=5, padx=5, pady=5, ipadx=5, ipady=5, sticky="nsew")
        self.helpText.grid(sticky="nsew")

        self.vertScrollBar.grid(row=1, column=7, rowspan=2, sticky="ens")
        #   self.vertScrollBar.pack(side=RIGHT, fill=Y)
        #   self.horzScrollBar.pack(side=BOTTOM, fill=X)
        self.buttonBar.grid(row=3, column=0, columnspan=5, padx=5, pady=5, ipadx=5, ipady=5, sticky="swe")

    def findMatches(self, all: bool=True):
        lineIdx = 1
        colIdx = 0
        charIdx = 0
        matches = []
        match = {}
        match['span'] = (4,5)
        #   print(str(match.span))

    def messageReceiver(self, message: dict):
        if message is not None and isinstance(message, dict) and "target" in message:
            if message["target"] == "updateFind":
                results = self.updateFind(message["searchEntry"], message["regex"],
                                          message["caseSensitive"], message["wordsOnly"])
                if "updateResultsReceiver" in message and callable(message["updateResultsReceiver"]):
                    message["updateResultsReceiver"]({"results": results})
            elif message["target"] == "searchEntryKeyHandler":
                results = self.searchEntryKeyHandler(message["event"], message["searchEntry"], message["regex"],
                                          message["caseSensitive"], message["wordsOnly"])
                if "updateResultsReceiver" in message and callable(message["updateResultsReceiver"]):
                    message["updateResultsReceiver"]({"results": results})

            elif message["target"] == "searchEntryVarTrace":
                results = self.searchEntryVarTrace(message["searchEntry"], message["regex"], message["autoUpdate"],
                                          message["caseSensitive"], message["wordsOnly"])
                if "updateResultsReceiver" in message and callable(message["updateResultsReceiver"]):
                    message["updateResultsReceiver"]({"results": results})
            elif message["target"] == "updateActiveLocation":
                if "tagName" in message and "state" in message:
                    self.helpText.see( message["tagName"] + ".first")
                    if message["state"] == "normal":
                        self.helpText.tag_delete(message["tagName"])
                    elif message["state"] == "found":
                        self.helpText.tag_config(message["tagName"], background=HelpDialog.FOUND_BACKGROUND,
                                                 foreground=HelpDialog.FOUND_FOREGROUND)
                    elif message["state"] == "active":
                        self.helpText.tag_config(message["tagName"], background=HelpDialog.ACTIVE_BACKGROUND,
                                                 foreground=HelpDialog.ACTIVE_FOREGROUND)

    def updateFind(self, searchText, regex, caseSensitive, wordsOnly):
        print("updateFind:\t" + searchText)
        return self.searchUpdate(searchText, regex, caseSensitive, wordsOnly)

    def searchEntryKeyHandler(self, event, searchText, regex, caseSensitive, wordsOnly):
        #   print("searchEntryKeyHandler:\t" + searchText)
        if event.keysym == "Return":      #   immediate update of highlighting of matches in display
            return self.searchUpdate(searchText, regex, caseSensitive, wordsOnly)
        return None

    def searchEntryVarTrace(self, searchText, regex, autoUpdate, caseSensitive, wordsOnly):
        #   print("searchEntryVarTrace:\t" + searchText)
        if autoUpdate:
            return self.searchUpdate(searchText, regex, caseSensitive, wordsOnly)

    def searchUpdate(self, searchText, regex, caseSensitive, wordsOnly):
        result = {"count": None}
        if self.topicSelected is not None and searchText is not None and \
                isinstance(searchText, str):
            for key in list(self.findTags.keys()):
                self.helpText.tag_delete(key)
            #   self.helpText.tag_delete(*list(self.findTags.keys()))
            if len(searchText) == 0:
                return result
            self.findTags = {}
            #   The text character index in the original text stream of the start of each line.
            #   self.textLineIndex[lineIndex]
            matchesAdapter = []
            textMatchLocations = []
            if regex:
                matches = re.finditer(searchText, self.helpContent.contentMap[self.topicSelected])
                for match in matches:
                    span = (match.span()[0], match.span()[1])
                    matchesAdapter.append(StrMatch(span))
                matches = tuple(matchesAdapter)
            else:       #   ordinary string search
                matches = matchManager.findAllInText(searchText, self.helpContent.contentMap[self.topicSelected],
                                                     caseSensitive=caseSensitive, wordsOnly=wordsOnly)
            #   matches is ordered, so:
            lastMatchIdx = [1, 0, 0, 0]  # line index, start character index, end character index
            matchCount = 0
            for match in matches:
                matchCount += 1
                lineIdx = lastMatchIdx[0]
                while lineIdx < len(self.textLineIndex) and match.span[0] > self.textLineIndex[lineIdx]:
                    lineIdx += 1
                if lineIdx <= len(self.textLineIndex):
                    if lineIdx > 1:
                        lastMatchIdx[0] = lineIdx - 1
                        lastMatchIdx[1] = match.span[0] - self.textLineIndex[lineIdx - 1]
                    else:
                        lastMatchIdx[0] = lineIdx
                        lastMatchIdx[1] = match.span[0] - self.textLineIndex[lineIdx]
                    lastMatchIdx[2] = lastMatchIdx[1] + match.span[1] - match.span[0]

                    startIdx = str(lastMatchIdx[0]) + '.' + str(lastMatchIdx[1])
                    endIdx = str(lastMatchIdx[0]) + '.' + str(lastMatchIdx[2])
                    tagName = searchText + ": " + startIdx
                    lastMatchIdx[3] = tagName
                    self.findTags[tagName] = (startIdx, endIdx)
                    self.helpText.tag_add(tagName, startIdx, endIdx)
                    self.helpText.tag_config(tagName, background="yellow", foreground="blue")

                    textMatchLocations.append(tuple(lastMatchIdx))
            result = {"count": matchCount, "textMatchLocations": tuple(textMatchLocations)}
        return result

    def generalHelpLaunch(selft):
        print("generalHelpLaunch")

    def notesLaunch(self):
        print("notesLaunch")

    def toggleSearchEntry(self, *argv):
        #   print("toggleSearchEntry:\t" + str(self.searchToggleVar.get()))
        if self.searchToggleVar.get():
            self.searchEntryBar.grid(row=0, column=0, columnspan=5, pady=3, ipady=3, sticky="nwe")
        else:
            self.searchEntryBar.grid_forget()

    def toggleLineNumbers(self, *argv):
        print("toggleLineNumbers:\t" + str(self.lineNumToggleVar.get()))

    def toggleHighliting(self, *argv):
        print("toggleHighliting:\t" + str(self.highliteToggleVar.get()))

    def topicSelectionHandler(self, event):
        selection = self.topicListbox.selection_get()
        #   print("topicSelection:\t" + selection)
        self.helpText.config(state=NORMAL)
        self.helpText.delete('1.0', 'end')
        self.helpText.insert('end', self.helpContent.contentMap[selection])
        self.helpText.config(state=DISABLED)
        self.topicSelected = selection

        lines = self.helpContent.contentMap[selection].split('\n')
        self.textLineIndex = {}
        lineIndex = 1
        self.textLineIndex[lineIndex] = 0
        #   record the text character position of the start of each line.
        #   a Text index of '1.0' is the start of the displayed text.
        for line in lines:
            lineIndex += 1
            self.textLineIndex[lineIndex] = self.textLineIndex[lineIndex-1] + len(line) + 1
        #   print("self.textLineIndex:\t" + str(self.textLineIndex))
        #   self.helpText.tag_add("highlight", '1.0', '2.0')
        #   self.helpText.tag_config("highlight", background="yellow", foreground="blue")


    def ExitHelpDialot(self):
        answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?", parent=self)
        if answer:
            self.destroy()


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == '__main__':
    mainView = Tk()
    geometryString = "900x600+300+50"
    mainView.geometry(geometryString)
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    #   helpLaunchButton = Button(mainView, text="Launch Help Dialog", command=lambda: launchHelpDialog(mainView))
    #   helpLaunchButton.grid(row=0, column=0, columnspan=10, padx=5, pady=5, sticky="we")

    helpMap = None
    helpContent = HelpContent("Application Description and Purpose", helpMap)
    #   helpContent.list()
    helpDialog = HelpDialog(mainView, helpContent, 'all', geometryString)
    helpDialog.pack(expand=True, fill=BOTH)

    manPythonFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                      "2021-08-11 12:15:11.618555 man ('python',).cmd_out"))
    if os.path.isfile(manPythonFileName):
        manPythonFile   = open(manPythonFileName, 'r')
        manPythonText = manPythonFile.read()
        manPythonFile.close()
    else:
        manPythonText = "ERROR READING FILE:\t" + manPythonFileName
    matchManager = MatchManager()
    matchManager.findAllInText("in", manPythonText, caseSensitive=True, wordsOnly=True)
    print("\n\tCount of matches:\t" + str(len(matchManager.matchesMap["in"])))
    #for string, matchEntry in matchManager.matchesMap.items():
    #    for strMatch in matchEntry:
    #        print(string + ":\t" + str(strMatch))

    mainView.mainloop()
