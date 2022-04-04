#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   August 18, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/SearchComponents.py
#   Purpose:        Provide pluggable search controls to any data display in the application.
#   Development:
#       2022-03-09:
#           Need a general popup property sheet component which can have any content for selection by the user.
#           Application:    grep expression list with names for each for both supplied expressions and ones
#                           the user enters and saves.  Needed for simple things like date and time formats,
#                           phone numbers, emails and URLs.
#                           Date and time formats should show a standard example in the name column.
#
#       2022-03-10:
#           With date, time, and timestamp columns a means is required to select and search for only the
#           year, or only the month, or only the day, ..., or any combination of:
#               year, month, day, hour, minute, second
#           A panel with a vertical list of checkboxes will work.
#


import re
from copy import deepcopy
from functools import partial
import datetime
from enum import Enum
from collections import OrderedDict

from tkinter import Tk, Menu, Spinbox, Label, Button, Frame, LabelFrame, Entry, Checkbutton, Menubutton, \
                    Listbox, Radiobutton, Toplevel, messagebox, \
                    StringVar, BooleanVar, IntVar, DoubleVar, \
                    GROOVE, RIDGE, FLAT, SUNKEN, RAISED, NORMAL, DISABLED, CENTER, LEFT, RIGHT, \
                    X, Y, BOTH, END, W, E, N, S, \
                    SINGLE, BROWSE, MULTIPLE, EXTENDED


PROGRAM_TITLE = "Search Components"


class DateTimeField(Enum):
    YEAR        = 'Year'
    MONTH       = 'Month'
    DAY         = 'Day'
    HOUR        = "Hour"
    MINUTE      = 'Minute'
    SECOND      = 'Second'

class ToolTip(Menu):

    def __init__(self, container, toolTipText: str):
        Menu.__init__(self, container, tearoff=0)
        self.add_checkbutton(label=toolTipText, command=self.doNothing())

    def replaceTip(self, newTipText: str):
        self.delete(0, 1)
        self.add_checkbutton(label=newTipText, command=self.doNothing())

    def doNothing(self):
        pass


class SearchEntryBar(Frame):

    DEFAULT_MESSAGE     = "Right click for more options"
    DEFAULT_MESSAGE_COLOR    = "#552255"
    #   User can specify a particular list of features depending on what their text component supports, or
    #   on which features they need in a particular workflow context.

    AVAILABLE_FEATURES  = ("Save Filter", "Select Filters", "Case Toggle", "Words Toggle", "Fuzzy Toggle", "Messages", "Location Spinner", "Match Count",
                           "Regex Toggle", "Select Type", "Number", "Integer", "Real", "Date", "Time", "Date-Time",
                           "Data Type Regular Expressions",
                           "Auto-Update", "Line Filtering", "Search Type", "Tool Tips")
    DEFAULT_FEATURES    = ("Case Toggle", "Words Toggle", "Messages", "Regex Toggle", "Auto-Update", "Tool Tips",
                           "Line Filtering")
    HELP_FEATURES       = ("Case Toggle", "Words Toggle", "Messages", "Regex Toggle", "Auto-Update", "Tool Tips")

    DEFAULT_SETTINGS    = {"case sensitive": False, "words only": False, "fuzzy search": False,
                           "regular expression": False, "auto update": True, "line filtering": False,
                           "search type": "Text", "messages": False}

    def __init__(self, container, listener, dialogWidth, features: tuple = None, settings: dict = None, **keyWordArguments):
        if listener is None or not callable(listener):
            raise Exception("SearchEntryBar constructor - invalid listener argument:\t" + str(listener))
        if dialogWidth is None or not isinstance(dialogWidth, int):
            raise Exception("SearchEntryBar constructor - invalid dialogWidth argument:\t" + str(dialogWidth))

        if features is not None:
            if not isinstance(features, tuple):
                raise Exception("SearchEntryBar constructor - invalid features argument:\t" + str(features))
            else:
                for feature in features:
                    if feature not in SearchEntryBar.AVAILABLE_FEATURES:
                        raise Exception("SearchEntryBar constructor - invalid features argument:\t" + str(features))
                self.features = deepcopy(features)
        else:
            self.features = SearchEntryBar.DEFAULT_FEATURES

        self.initialSettings = {}
        if settings is not None:
            for name, setting in settings.keys():
                if name not in SearchEntryBar.DEFAULT_SETTINGS:
                    raise Exception("SearchEntryBar constructor - invalid setting argument:\t" + str(name))
                else:
                    self.initialSettings[name] = setting
        else:
            self.initialSettings = SearchEntryBar.DEFAULT_SETTINGS

        Frame.__init__(self, container, keyWordArguments)
        self.listener       = listener
        self.dialogWidth = dialogWidth

        self.searchType = None
        if "Search Type" in self.features:
            if "search type" in self.initialSettings:
                self.searchType = self.initialSettings["search type"]
            else:
                self.searchType = 'Text'

        self.toolTip = None
        self.toolTips = None
        if "Tool Tips" in self.features:
            self.toolTip = ToolTip(self, "Hello Tipper")
        if "Tool Tips" in self.features or "Messages" in self.features:
            self.toolTips = {
                "searchEntryLabel": "Search the text for ...",
                "searchTextEntry": "Enter search term(s) or regular expression",
                "updateButton": "Update search results if auto-update is off",
                "toggleUpdateCheckButton": "Turn on or off auto-update feature",
                "toggleRegexCheckButton": "Turn on or off regular expression handling",
                "messagesLabel": "Instructions and error messages",
                "matchLocationSpinner": "Set the location in the list of matches in the text",
                "matchCountLabel": "The number of matches currently",
                "countLabel": "The number of matches currently",
                "optionsButton": "More search and filter options in a popup menu",
                "toggleLineFilterCheckButton": "Line filtering removes all lines that do not match from display"
            }

        self.textMatchLocations = None
        self.activeLocaitonTag = None

        self.searchEntryLabel = Label(self, text="Search for: ", width=len("Search for: "))
        self.searchEntryLabel.__dict__["compName"] = "searchEntryLabel"
        self.searchEntryLabel.bind('<Button-3>', self.rightClickHandler)
        self.searchEntryLabel.bind('<Enter>', self.mouseEnter)
        self.searchEntryLabel.bind('<Leave>', self.mouseLeave)

        self.entryTypeLabel = None
        if "Search Type" in self.features:
            self.entryTypeLabel = Label(self, text="(Text)", width=10, foreground="#005522")
            self.entryTypeLabel.__dict__["compName"] = "entryTypeLabel"
            self.entryTypeLabel.bind('<Button-3>', self.rightClickHandler)
            self.entryTypeLabel.bind('<Enter>', self.mouseEnter)
            self.entryTypeLabel.bind('<Leave>', self.mouseLeave)

        self.searchEntryVar = StringVar()
        self.searchTextEntry = Entry(self, border=2, relief=GROOVE, width=int(self.dialogWidth/10.5)-50,
                                     textvariable=self.searchEntryVar)
        self.searchTextEntry.__dict__["compName"] = "searchTextEntry"
        self.searchTextEntry.bind('<Button-3>', self.rightClickHandler)
        self.searchTextEntry.bind('<Enter>', self.mouseEnter)
        self.searchTextEntry.bind('<Leave>', self.mouseLeave)
        self.searchTextEntry.bind("<Key>", self.searchEntryKeyHandler)
        self.searchEntryVar.trace("w", self.searchEntryVarTrace)


        self.updateButton = Button(self, text="Update", command=self.updateFind)
        self.updateButton.__dict__["compName"] = "updateButton"
        self.updateButton.bind('<Button-3>', self.rightClickHandler)
        self.updateButton.bind('<Enter>', self.mouseEnter)
        self.updateButton.bind('<Leave>', self.mouseLeave)

        self.toggleAutoUpdateVar = None
        self.toggleUpdateCheckButton = None
        if "Auto-Update" in self.features:
            self.toggleAutoUpdateVar = BooleanVar()
            self.toggleUpdateCheckButton = Checkbutton(self, text="Auto Update",
                                                       variable=self.toggleAutoUpdateVar)
            self.toggleUpdateCheckButton.__dict__["compName"] = "toggleUpdateCheckButton"
            self.toggleUpdateCheckButton.bind('<Button-3>', self.rightClickHandler)
            self.toggleUpdateCheckButton.bind('<Enter>', self.mouseEnter)
            self.toggleUpdateCheckButton.bind('<Leave>', self.mouseLeave)
            self.toggleAutoUpdateVar.set(False)
            self.toggleAutoUpdateVar.trace("w", self.handleAutoUpdateToggle)

        self.toggleRegexVar = None
        self.toggleRegexCheckButton = None
        if "Regex Toggle" in self.features:
            #   If user wants to use regular expressions, then Auto Update needs to be turned off:
            self.toggleRegexVar = BooleanVar()
            self.toggleRegexCheckButton = Checkbutton(self, text="Reg Ex", variable=self.toggleRegexVar)
            self.toggleRegexCheckButton.__dict__["compName"] = "toggleRegexCheckButton"
            self.toggleRegexCheckButton.bind('<Button-3>', self.rightClickHandler)
            self.toggleRegexCheckButton.bind('<Enter>', self.mouseEnter)
            self.toggleRegexCheckButton.bind('<Leave>', self.mouseLeave)
            self.toggleRegexVar.set(False)
            self.toggleRegexVar.trace("w", self.handleRegexVarToggle)

        self.toggleLineFilterVar = None
        self.toggleLineFilterCheckButton = None
        if "Line Filtering" in self.features:
            self.toggleLineFilterVar = BooleanVar()
            self.toggleLineFilterCheckButton = Checkbutton(self, text="Line Filtering", variable=self.toggleLineFilterVar)
            self.toggleLineFilterCheckButton.__dict__["compName"] = "toggleLineFilterCheckButton"
            self.toggleLineFilterCheckButton.bind('<Button-3>', self.rightClickHandler)
            self.toggleLineFilterCheckButton.bind('<Enter>', self.mouseEnter)
            self.toggleLineFilterCheckButton.bind('<Leave>', self.mouseLeave)
            self.toggleLineFilterVar.set(False)
            self.toggleLineFilterVar.trace("w", self.handleLineFilterVarToggle)

        self.optionsButton = Button(self, text="Options", command=self.toggleOptionsMenu)
        self.optionsButton.__dict__["compName"] = "optionsButton"
        self.optionsButton.bind('<Button-3>', self.rightClickHandler)
        self.optionsButton.bind('<Enter>', self.mouseEnter)
        self.optionsButton.bind('<Leave>', self.mouseLeave)

        self.messagesLabel = None
        if "Messages" in self.features:
            self.messagesLabel  = Label(self, text=SearchEntryBar.DEFAULT_MESSAGE,
                                        fg=SearchEntryBar.DEFAULT_MESSAGE_COLOR, width=50, border=2, relief=SUNKEN)
            self.messagesLabel.__dict__["compName"] = "messagesLabel"
            self.messagesLabel.bind('<Enter>', self.mouseEnter)
            self.messagesLabel.bind('<Leave>', self.mouseLeave)

        self.locationVar = None
        self.matchLocationSpinner = None
        if "Location Spinner" in self.features:
            self.locationVar = IntVar()
            self.matchLocationSpinner = Spinbox(self, width=8, state=NORMAL, from_=0, to=1000000,
                                                textvariable=self.locationVar)
            self.matchLocationSpinner.__dict__["compName"] = "matchLocationSpinner"
            self.matchLocationSpinner.bind('<Enter>', self.mouseEnter)
            self.matchLocationSpinner.bind('<Leave>', self.mouseLeave)
            self.locationVar.set(0)
            self.locationVar.trace("w", self.matchLocationChange)

        self.matchCountLabel = None
        self.countLabel = None
        if "Match Count" in self.features:
            self.matchCountLabel = Label(self, text="Match Count: ")
            self.matchCountLabel.__dict__["compName"] = "matchCountLabel"
            self.matchCountLabel.bind('<Enter>', self.mouseEnter)
            self.matchCountLabel.bind('<Leave>', self.mouseLeave)
            self.countLabel = Label(self, width=8, border=2, relief=SUNKEN)
            self.countLabel.__dict__["compName"] = "countLabel"
            self.countLabel.bind('<Enter>', self.mouseEnter)
            self.countLabel.bind('<Leave>', self.mouseLeave)

        self.popupMenu = SearchEntryBar.PopupMenu(self, self.listener)
        self.popupShown = False
        self.bind('<Button-3>', self.rightClickHandler)

        self.searchEntryLabel.grid(row=0, column=0, ipadx=0, pady=3, sticky='w')
        self.searchTextEntry.grid(row=0, column=1, ipadx=0, pady=3, sticky='ew')
        self.updateButton.grid(row=0, column=2, ipadx=3, padx=10, sticky='e')
        if self.toggleUpdateCheckButton is not None:
            self.toggleUpdateCheckButton.grid(row=0, column=3, ipadx=3, padx=3, sticky='e')
        if self.toggleRegexCheckButton is not None:
            self.toggleRegexCheckButton.grid(row=0, column=4, ipadx=3, padx=3, sticky='e')
        if self.toggleLineFilterCheckButton is not None:
            self.toggleLineFilterCheckButton.grid(row=0, column=5, padx=5, pady=5, sticky='e')
        self.optionsButton.grid(row=0, column=6, padx=5, pady=5, sticky='e')

    def handleLineFilterVarToggle(self, *argv):
        print("handleLineFilterVarToggle")

    def matchLocationChange(self, *argv):
        print("matchLocationChange")
        newLocation = self.locationVar.get()
        if newLocation < len(self.textMatchLocations):
            newLocationTag = self.textMatchLocations[newLocation-1][3]
            if self.activeLocaitonTag is not None:
                self.listener({"target": "updateActiveLocation", "tagName": self.activeLocaitonTag, "state": "found"})
            self.listener({"target": "updateActiveLocation", "tagName": newLocationTag, "state": "active"})
            self.activeLocaitonTag = newLocationTag
            #   states: normal, found, active

    def updateFind(self):
        autoUpdate = False
        if self.toggleAutoUpdateVar is not None:
            autoUpdate = self.toggleAutoUpdateVar.get()
        regex = False
        if self.toggleRegexVar is not None:
            regex = self.toggleRegexVar.get()
        caseSensitive = False
        if self.popupMenu.boolVarCaseSens is not None:
            caseSensitive = self.popupMenu.boolVarCaseSens.get()
        wordsOnly = False
        if self.popupMenu.boolVarWordsOnly is not None:
            wordsOnly = self.popupMenu.boolVarWordsOnly.get()

        self.listener({"target": "updateFind", "searchEntry": self.searchEntryVar.get(),
                       "regex": regex, "autoUpdate": autoUpdate,
                       "caseSensitive": caseSensitive,
                       "wordsOnly": wordsOnly,
                       "updateResultsReceiver": self.updateResultsReceiver})

    def updateResultsReceiver(self, message: dict):
        #   print("updateResultsReceiver:\t" + str(message))
        if "results" in message and message["results"] is not None:
            if "count" in message["results"]:
                #   print("message.results.count:\t" + str(message["results"]["count"]))
                if self.countLabel is not None:
                    self.countLabel.configure(text=str(message["results"]["count"]))
            if "textMatchLocations" in message["results"]:
                #if self.textMatchLocations is not None:
                self.textMatchLocations = message["results"]["textMatchLocations"]

    def mouseEnter(self, event):
        if self.popupMenu.boolVarToolTips is not None:
            if self.popupMenu.boolVarToolTips.get():
                self.toolTip.delete(0, 1)
                newToolTip = self.toolTips[event.widget.__dict__["compName"]]
                self.toolTip.add_checkbutton(label=newToolTip, command=self.doNothing)
                self.toolTip.tk_popup(event.x_root, event.y_root, 0)
        if self.messagesLabel is not None:
            self.messagesLabel.configure(text=self.toolTips[event.widget.__dict__["compName"]], foreground="#006666")
        """
        try:
            self.toolTip.tk_popup(event.x_root, event.y_root, 0)
        finally:
            self.toolTip.grab_release()
        """

    def doNothing(self):
        pass

    def mouseLeave(self, event):
        self.messagesLabel.configure(text=SearchEntryBar.DEFAULT_MESSAGE,
                                     foreground=SearchEntryBar.DEFAULT_MESSAGE_COLOR)
        #   self.toolTip.grab_release()

    def handleRegexVarToggle(self, *argv):
        if self.toggleRegexVar.get():
            if self.toggleAutoUpdateVar is not None:
                self.toggleAutoUpdateVar.set(False)
            if self.popupMenu is not None:
                if self.popupMenu.boolVarCaseSens is not None:
                    self.popupMenu.boolVarCaseSens.set(False)
                if self.popupMenu.boolVarWordsOnly is not None:
                    self.popupMenu.boolVarWordsOnly.set(False)
            if self.entryTypeLabel is not None:
                self.entryTypeLabel.configure(text="(Regex)")
        else:
            if self.entryTypeLabel is not None:
                self.entryTypeLabel.configure(text='(' + self.searchType + ')')

    def toggleOptionsMenu(self):
        if not self.popupShown:
            try:
                self.popupMenu.tk_popup(800, 100, 0)
                self.popupShown = True

                #   Need automatic tearoff when Options button is pressed
                self.update()
                self.event_generate("<<TearOff>>", when="tail")

            finally:
                self.popupMenu.grab_release()


        #   force update of search results if there is anything in the search text field
        searchText = self.searchEntryVar.get()
        if searchText is not None and searchText != '':
            self.listener({"target": "searchEntryVarTrace", "searchEntry": searchText,
                                          "autoUpdate": True,
                                          "regex": self.toggleRegexVar.get(),
                                          "updateResultsReceiver": self.updateResultsReceiver,
                                          "caseSensitive": False,
                                          "wordsOnly": False})

    def handleAutoUpdateToggle(self, *argv):
        if self.toggleAutoUpdateVar.get():
            self.toggleRegexVar.set(False)


    def searchEntryKeyHandler(self, event):
        autoUpdate = False
        if self.toggleAutoUpdateVar is not None:
            autoUpdate = self.toggleAutoUpdateVar.get()
        if event.keysym == "Return" or autoUpdate:
            regex = False
            if self.toggleRegexVar is not None:
                regex = self.toggleRegexVar.get()
            caseSensitive = False
            if self.popupMenu.boolVarCaseSens is not None:
                caseSensitive = self.popupMenu.boolVarCaseSens.get()
            wordsOnly = False
            if self.popupMenu.boolVarWordsOnly is not None:
                wordsOnly = self.popupMenu.boolVarWordsOnly.get()
            self.listener({"target": "searchEntryKeyHandler", "event": event, "searchEntry": self.searchEntryVar.get(),
                           "regex": regex, "autoUpdate": autoUpdate, "caseSensitive": caseSensitive,
                           "wordsOnly": wordsOnly, "updateResultsReceiver": self.updateResultsReceiver})

    def searchEntryVarTrace(self, *argv):
        #   print("SearchEntryBar.searchEntryVarTrace:\t" + self.searchEntryVar.get())
        autoUpdate = False
        if self.toggleAutoUpdateVar is not None:
            autoUpdate = self.toggleAutoUpdateVar.get()
        regex = False
        if self.toggleRegexVar is not None:
            regex = self.toggleRegexVar.get()
        caseSensitive = False
        if self.popupMenu.boolVarCaseSens is not None:
            caseSensitive = self.popupMenu.boolVarCaseSens.get()
        wordsOnly = False
        if self.popupMenu.boolVarWordsOnly is not None:
            wordsOnly = self.popupMenu.boolVarWordsOnly.get()

        self.listener({"target": "searchEntryVarTrace", "searchEntry": self.searchEntryVar.get(),
                       "autoUpdate": autoUpdate, "regex": regex, "updateResultsReceiver": self.updateResultsReceiver,
                       "caseSensitive": caseSensitive, "wordsOnly": wordsOnly})

    def rightClickHandler(self, event):
        #   print("rightClickHandler:\t" + str(event))
        if not self.popupShown:
            try:
                self.popupMenu.tk_popup(event.x_root, event.y_root, 0)
                self.popupShown = True
            finally:
                self.popupMenu.grab_release()

    class PopupMenu(Menu):

        def __init__(self, searchEntryBar, listener=None):
            #   Menu.__init__(self, container, text="Sort Controls", tearoff=1)
            if listener is not None and not callable(listener):
                raise Exception("PopupMenu constructor - Invalid listener argument:  " + str(listener))
            self.searchEntryBar = searchEntryBar

            self.menuFloating = False

            features = self.searchEntryBar.features
            Menu.__init__(self, searchEntryBar, tearoff=1, title="Search Options", tearoffcommand=self.menuTearOff)

            self.boolVarCaseSens = None
            self.boolVarWordsOnly = None
            self.boolVarFuzzy = None
            self.boolVarShowCount = None
            self.boolVarLocationSpinner = None
            self.boolVarMessagesBar = None
            self.boolVarShowType = None
            self.boolVarToolTips = None

            self.topLevelPopup = None
            self.filterDetailsPanel = None

            if "Save Filter" in features:
                self.add_command(label="Save Filter", command=self.saveFilter)
            if "Select Filters" in features:
                self.add_command(label="Select Filters", command=self.selectFilters)

            if "Save Filter" in features or "Select Filters" in features:
                self.add_separator()

            if "Case Toggle" in features:
                self.boolVarCaseSens = BooleanVar()
                self.add_checkbutton(label='Case Sensitive', variable=self.boolVarCaseSens,
                                     command=lambda: self.popupMenuItemHandler("Case Sensitive"))
                self.boolVarCaseSens.set(True)
            if "Words Toggle" in features:
                self.boolVarWordsOnly = BooleanVar()
                self.add_checkbutton(label='Words Only', variable=self.boolVarWordsOnly,
                                     command=lambda: self.popupMenuItemHandler("Words Only"))
                self.boolVarWordsOnly.set(True)

            if "Fuzzy Toggle" in features:
                self.boolVarFuzzy = BooleanVar()
                self.add_checkbutton(label='Fuzzy Search', variable=self.boolVarFuzzy,
                                     command=lambda: self.popupMenuItemHandler("Fuzzy Search"))
                self.boolVarWordsOnly.set(True)

            if "Case Toggle" in features or "Words Toggle" in features or "Fuzzy Toggle" in features:
                self.add_separator()

            if "Match Count" in features:
                self.boolVarShowCount = BooleanVar()
                self.add_checkbutton(label='Show Count', variable=self.boolVarShowCount,
                                     command=lambda: self.popupMenuItemHandler("Show Count"))
                self.boolVarShowCount.set(False)
            if "Location Spinner" in features:
                self.boolVarLocationSpinner = BooleanVar()
                self.add_checkbutton(label='Location Spinner', variable=self.boolVarLocationSpinner,
                                     command=lambda: self.popupMenuItemHandler("Location Spinner"))
                self.boolVarLocationSpinner.set(False)
            if "Messages" in features:
                self.boolVarMessagesBar = BooleanVar()
                self.add_checkbutton(label='Messages Bar', variable=self.boolVarMessagesBar,
                                     command=lambda: self.popupMenuItemHandler("Messages Bar"))
                self.boolVarMessagesBar.set(False)
            if "Search Type" in features:
                self.boolVarShowType = BooleanVar()
                self.add_checkbutton(label='Show Search Type', variable=self.boolVarShowType,
                                     command=lambda: self.popupMenuItemHandler("Show Search Type"))
                self.boolVarShowType.set(False)
            if "Tool Tips" in features:
                self.boolVarToolTips = BooleanVar()
                self.add_checkbutton(label='Tool Tips', variable=self.boolVarToolTips,
                                     command=lambda: self.popupMenuItemHandler("Tool Tips"))
                self.boolVarToolTips.set(False)

            self.numericMenu = None
            if "Select Type" in features:
                self.numericMenu    = Menu( self, tearoff=1)

                """ tkinter event bubble thread management bug:  sticks on the first selection.
                
                self.numericMenu.add_radiobutton(label="Text", value="Text", variable=self.numericStringVar)
                if "Number" in features:
                    self.numericMenu.add_radiobutton(label="Number", value="Number", variable=self.numericStringVar)
                if "Integer" in features:
                    self.numericMenu.add_radiobutton(label="Integer", value="Integer", variable=self.numericStringVar)
                if "Real" in features:
                    self.numericMenu.add_radiobutton(label="Real", value="Real", variable=self.numericStringVar)
                if "Date" in features:
                    self.numericMenu.add_radiobutton(label="Date", value="Date", variable=self.numericStringVar)
                if "Time" in features:
                    self.numericMenu.add_radiobutton(label="Time", value="Time", variable=self.numericStringVar)
                if "Date-Time" in features:
                    self.numericMenu.add_radiobutton(label="Date-Time", value="Date-Time", variable=self.numericStringVar)
                """

                self.typeCheckButtonBoolBars = {}
                self.typeCheckButtonBoolBars["Text"] = BooleanVar()
                self.numericMenu.add_checkbutton(label="Text",
                                                 variable=self.typeCheckButtonBoolBars["Text"],
                                                 command=lambda: self.typeSelectHandler("Text"))
                if "Number" in features:
                    self.typeCheckButtonBoolBars["Number"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Number",
                                                     variable=self.typeCheckButtonBoolBars["Number"],
                                                     command=lambda: self.typeSelectHandler("Number"))
                if "Integer" in features:
                    self.typeCheckButtonBoolBars["Integer"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Integer",
                                                     variable=self.typeCheckButtonBoolBars["Integer"],
                                                     command=lambda: self.typeSelectHandler("Integer"))
                if "Real" in features:
                    self.typeCheckButtonBoolBars["Real"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Real",
                                                     variable=self.typeCheckButtonBoolBars["Real"],
                                                     command=lambda: self.typeSelectHandler("Real"))
                if "Date" in features:
                    self.typeCheckButtonBoolBars["Date"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Date",
                                                     variable=self.typeCheckButtonBoolBars["Date"],
                                                     command=lambda: self.typeSelectHandler("Date"))
                if "Time" in features:
                    self.typeCheckButtonBoolBars["Time"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Time",
                                                     variable =self.typeCheckButtonBoolBars["Time"],
                                                     command=lambda: self.typeSelectHandler("Time"))
                if "Date-Time" in features:
                    self.typeCheckButtonBoolBars["Date-Time"] = BooleanVar()
                    self.numericMenu.add_checkbutton(label="Date-Time",
                                                     variable=self.typeCheckButtonBoolBars["Date-Time"],
                                                     command=lambda: self.typeSelectHandler("Date-Time"))
                self.add_cascade(label="Select Type", menu=self.numericMenu)
                self.searchEntryBar.searchType = "Text"
                self.typeCheckButtonBoolBars["Text"].set(True)

            self.savedRegexMenu = None
            if "Data Type Regular Expressions" in features:
                self.savedRegexMenu  = Menu(self, tearoff=0)
                self.savedRegexMenu.add_command(label="Add a Regex", command=lambda: self.savedRegexSet("Add a Regex"))
                self.savedRegexMenu.add_command(label="Email Address", command=lambda: self.savedRegexSet("Email Address"))
                self.savedRegexMenu.add_command(label="Phone Number", command=lambda: self.savedRegexSet("Phone Number"))
                self.savedRegexMenu.add_command(label="URL", command=lambda: self.savedRegexSet("URL"))
                self.savedRegexMenu.add_command(label="Postal Code", command=lambda: self.savedRegexSet("Postal Code"))
                self.savedRegexMenu.add_command(label="Tracking Number", command=lambda: self.savedRegexSet("Tracking Number"))
                self.savedRegexMenu.add_command(label="UPC", command=lambda: self.savedRegexSet("UPC"))
                self.savedRegexMenu.add_command(label="ISBN", command=lambda: self.savedRegexSet("ISBN"))
                self.savedRegexMenu.add_command(label="Internet Domain", command=lambda: self.savedRegexSet("Internet Domain"))
                self.savedRegexMenu.add_command(label="IP Address", command=lambda: self.savedRegexSet("IP Address"))
                self.savedRegexMenu.add_command(label="Port Number", command=lambda: self.savedRegexSet("Port Number"))
                self.add_cascade(label="Regular Expressions", menu=self.savedRegexMenu)

            print("PopupMenu constructor - self.winfo_name():\t" + str(self.winfo_name()))

            self.bind('<Unmap>', self.unmapMenu)
            self.bind('<Destroy>', self.destroyMenu)

        def saveFilter(self):
            print("PopupMenu.saveFilter")

        def selectFilters(self):
            print("PopupMenu.selectFilters")

        def savedRegexSet(self, regexName: str):
            print("savedRegexSet:\t" + str(regexName))
            messagebox.showinfo("Regular Expresion", "Not Implemented Yet:\t" + str(regexName))

        def typeSelectHandler(self, checkBoxLabel: str):
            print("typeSelectHandler:\t" + str(checkBoxLabel))
            for name, checkBoolVar in self.typeCheckButtonBoolBars.items():
                if name != checkBoxLabel and checkBoolVar.get():
                    checkBoolVar.set(False)
            self.searchEntryBar.entryTypeLabel.configure(text='(' + checkBoxLabel + ')')
            self.switchToType(checkBoxLabel)
            self.searchEntryBar.searchType = checkBoxLabel

        def menuTearOff(self, componentPathName, commandName):
            #   print("menuTearOff:\t" + str(componentPathName))
            self.menuFloating = True

        def popupMenuItemHandler(self, menuText: str):
            #   print("popupMenuItemHandler - self.winfo_ismapped():\t" + str(self.winfo_ismapped()))
            #   print("popupMenuItemHandler - self.winfo_name():\t" + str(self.winfo_name()))
            if menuText is None or not isinstance(menuText, str) or menuText not in \
                    ('Case Sensitive', 'Words Only', "Fuzzy Search", 'Show Count', 'Location Spinner', 'Messages Bar',
                     'Show Search Type', 'Tool Tips'):
                raise Exception("popupMenuItemHandler - invalid menuText argument:    " + str(menuText))

            if menuText == 'Case Sensitive':
                if self.boolVarCaseSens.get():
                    if self.searchEntryBar.toggleRegexVar is not None:
                        self.searchEntryBar.toggleRegexVar.set(False)

                #   force update of search results if there is anything in the search text field
                searchText   = self.searchEntryBar.searchEntryVar.get()
                if searchText is not None and searchText != '':
                    if self.searchEntryBar.toggleRegexVar is not None:
                        regex = self.searchEntryBar.toggleRegexVar.get()
                    else:
                        regex = False
                    if self.boolVarCaseSens is not None:
                        caseSensitive = self.boolVarCaseSens.get()
                    else:
                        caseSensitive = False
                    if self.boolVarWordsOnly is not None:
                        wordsOnly = self.boolVarWordsOnly.get()
                    else:
                        wordsOnly = False

                    self.searchEntryBar.listener({"target": "searchEntryVarTrace", "searchEntry": searchText,
                                   "autoUpdate": True, "regex": regex,
                                   "updateResultsReceiver": self.searchEntryBar.updateResultsReceiver,
                                   "caseSensitive": caseSensitive, "wordsOnly": wordsOnly})

            elif menuText == 'Words Only':
                if self.boolVarWordsOnly.get():
                    self.searchEntryBar.toggleRegexVar.set(False)

                #   force update of search results if there is anything in the search text field
                searchText   = self.searchEntryBar.searchEntryVar.get()
                if searchText is not None and searchText != '':
                    self.searchEntryBar.listener({"target": "searchEntryVarTrace", "searchEntry": searchText,
                                   "autoUpdate": True,
                                   "regex": self.searchEntryBar.toggleRegexVar.get(),
                                   "updateResultsReceiver": self.searchEntryBar.updateResultsReceiver,
                                   "caseSensitive": self.boolVarCaseSens.get(),
                                   "wordsOnly": self.boolVarWordsOnly.get()})

            elif menuText == "Fuzzy Search":
                for name, checkBoolVar in self.typeCheckButtonBoolBars.items():
                    if name != "Text" and checkBoolVar.get():
                        checkBoolVar.set(False)
                self.typeCheckButtonBoolBars["Text"].set(True)
                self.switchToType('Fuzzy Match', force=self.boolVarFuzzy.get())

            elif menuText == 'Show Count':
                if self.searchEntryBar.matchCountLabel is not None and self.searchEntryBar.countLabel is not None:
                    if self.boolVarShowCount.get():
                        self.searchEntryBar.matchCountLabel.grid(row=1, column=3)
                        self.searchEntryBar.countLabel.grid(row=1, column=4)
                    else:
                        self.searchEntryBar.matchCountLabel.grid_forget()
                        self.searchEntryBar.countLabel.grid_forget()
            elif menuText == 'Location Spinner':
                if self.searchEntryBar.matchLocationSpinner is not None:
                    if self.boolVarLocationSpinner.get():
                        self.searchEntryBar.matchLocationSpinner.grid(row=1, column=2)
                    else:
                        self.searchEntryBar.matchLocationSpinner.grid_forget()
            elif menuText == 'Messages Bar':
                if self.searchEntryBar.messagesLabel is not None:
                    if self.boolVarMessagesBar.get():
                        self.searchEntryBar.messagesLabel.grid(row=1, column=1)
                    else:
                        self.searchEntryBar.messagesLabel.grid_forget()
            elif menuText == "Show Search Type":
                if self.searchEntryBar.entryTypeLabel is not None:
                    if self.boolVarShowType.get():
                        self.searchEntryBar.entryTypeLabel.grid(row=1, column=0, ipadx=0, pady=3, sticky='w')
                    else:
                        self.searchEntryBar.entryTypeLabel.grid_forget()
            elif menuText == 'Tool Tips':
                if self.boolVarToolTips.get():
                    pass
                else:
                    pass

        def switchToType(self, filterType: str, force: bool = None):

            #   DISABLED FOR PORT TO LinuxTools on 2022-04-03
            return

            if force is not None and not force:
                if self.filterDetailsPanel is not None:
                    self.filterDetailsPanel.grid_forget()
                    self.filterDetailsPanel = None
                if self.topLevelPopup is not None:
                    self.topLevelPopup.destroy()
                    self.topLevelPopup = None
                return
            dataType = "Text"
            if filterType == "Fuzzy Match":
                dataType = "fuzzy match"
            elif filterType == "Number":
                dataType = "real"
            elif filterType == "Integer":
                dataType = "integer"
            elif filterType == "Real":
                dataType = "real"
            elif filterType == "Date":
                dataType = "date"
            elif filterType == "Time":
                dataType = "time"
            elif filterType == "Date-Time":
                dataType = "dateTime"

            title = filterType
            if filterType != "Fuzzy Match":
                filterType = "Equals"

            if self.filterDetailsPanel is not None:
                self.filterDetailsPanel.grid_forget()
                self.filterDetailsPanel.destroy()
                self.filterDetailsPanel = None
            if self.topLevelPopup is not None:
                self.topLevelPopup.destroy()
                self.topLevelPopup = None

            geometryStr = None
            screenWidth = self.winfo_screenwidth()

            if dataType == "fuzzy match":
                geometryStr = "470x180+" + str(screenWidth - 520) + "+100"
            if dataType == "integer":
                geometryStr = "350x110+" + str(screenWidth - 400) + "+100"
            elif dataType == "real":
                geometryStr = "350x110+" + str(screenWidth - 400) + "+100"
            elif dataType == "date":
                geometryStr = "380x270+" + str(screenWidth - 430) + "+100"
            elif dataType == "time":
                geometryStr = "270x230+" + str(screenWidth - 320) + "+100"
            elif dataType == "dateTime":
                geometryStr = "530x250+" + str(screenWidth - 580) + "+100"

            if geometryStr is not None:
                if not force:
                    self.boolVarFuzzy.set(False)
                self.topLevelPopup = Toplevel(self)
                self.topLevelPopup.title(title + " Search")
                self.topLevelPopup.geometry(geometryStr)
                self.topLevelPopup.protocol('WM_DELETE_WINDOW', self.destroyTypeDialog)
                if self.filterDetailsPanel is not None:
                    self.filterDetailsPanel.grid_forget()
                    self.filterDetailsPanel.destroy()
                self.filterDetailsPanel = FilterDetailsPanel(self.topLevelPopup, dataType, filterType,
                                                             listener=self.listener)
                self.filterDetailsPanel.grid(row=0, column=2, padx=5, pady=5, sticky='w')
                self.topLevelPopup.mainloop()

        def destroyTypeDialog(self):
            if self.filterDetailsPanel is not None:
                self.filterDetailsPanel.grid_forget()
                self.filterDetailsPanel.destroy()
                self.filterDetailsPanel = None
            if self.topLevelPopup is not None:
                self.topLevelPopup.destroy()
                self.topLevelPopup = None
            if self.boolVarFuzzy is not None:
                self.boolVarFuzzy.set(False)

        def exitMenu(self, event):
            #   print("PopupMenu.exitMenu")
            self.searchEntryBar.fileNamePopupShown = False

        def unmapMenu(self, event):
            #print("unmapMenu - self.menuFloating:\t" + str(self.menuFloating))
            if not self.winfo_ismapped() and not self.menuFloating:
                self.searchEntryBar.fileNamePopupShown = False

        def destroyMenu(self, event):
            #   print("destroyMenu")
            self.searchEntryBar.fileNamePopupShown = False




def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == '__main__':
    mainView = Tk()
    mainView.geometry("800x500+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    mainView.mainloop()
