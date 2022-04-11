#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         view/RunnableSelection.py
#   Date Started:   March 31, 2022
#   Purpose:        Manage selection, design, and storage of Linux Tools, which are commands for which a particular
#                   set of arguments has been selected and set.
#   Development:
#       Actions:
#           0.  Show paths listed in os.environ['HOME'].
#           1.  Check to see if a particular Linux command line program is installed.
#           2.  Install a CLI command.
#           3.  Run a Linux CLI command with typed in options.
#           4.  Run a Linux CLI command with GUI component selected options, i.e. run a Tool.
#           5.  Save a Tool with a name for selection later.
#           6.  Load a saved Tool
#           7.  Run a saved Tool.
#           8.  Use the output of a saved tool as the input of another.
#           9.  View output in line, table, or tree form.
#           10. Determine which command line tools are installed by locating and listing and filtering all
#                   man pages.
#           11. From man page available list, show options for each command.
#           12. From man page available list, show man page, searchable.
#           13. From man page available list, show man page in navigatable sections.
#           14. Group commands by tags.  Include a default set for major functional groups and let user add their
#                   own.
#
#       Location of command line programs:
#           /bin
#           /usr/bin
#           see: echo $PATH
#           try:    $:  apt-cache policy <name>
#           worse:  $:  apt list --installed | grep <name>
#           worst:  $:  dpkg -l | grep <name>
#
#   2022-04-01: Showing command line options available for program:
#       Downloaded source of doclifter, a pure python script that converts troff to XML.
#       Location of man page files:
#           Ubuntu: /usr/share/man/man1/*.1.gz          71. MB
#                   /usr/share/man/man2/*.2.gz          973 kN
#                       ...
#                   /usr/share/man/man8/*.8.gz          1.5 MB
#       Each of the *.gz man page files extracts to a single troff / nroff file.
#       These appear to all be named 'data' in the man1 folder.
#
#       The "manpath" command's output is:
#           /home/keithcollins/.local/share/man:/usr/local/man:/usr/local/share/man:/usr/share/man
#               /home/keithcollins/.local/share/man         Only has man1 folder which only has 17 files in it.
#                                                           None has the .gz extension.  troff files.
#                                                           This could be a working set cache.
#               /usr/local/man                              Empty.
#               /usr/local/share/man                        Empty.
#               /usr/share/man                              Listed supra.
#
#           Tested: man ati.  ati.4.gz is in /usr/share/man/man4
#                   It is not in man1 or man3.
#           The C standard library appears to be present in man3.
#
#
#       2022-04-03: Popup Menu Action / Toggle Lists:
#           For selected file:
#               Show man page => Toplevel showing man page by section view
#               Show command configurarion  =>  for commands, the config property sheet,
#                                                   for functions / libraries, as appropriate.
#                                                   Can name and save a tool design from here.
#               Show ConfigurationManager   =>  List of configurations / Tools saved for the selected
#                                                   man page / program ..., with the particular
#                                                   configs available on selection from list.
#           For selected Filter Entry:
#               Show saved filters
#               Name and save filter
#               Copy filter to other columns => column select check box list
#               Turn on / off content filtering =>
#                   Modifies view and behavior by opening up another tab in notebook for content filtering,
#                       using general filter design dashboard currently in my SQLite table content view.
#                       Can apply filters to all columns or selected ones.
#                       Can [next], [prev], [first], [last] through results.
#                   New notebook tab can include Console Help with SearchBar and selected column listed
#                       to left.  Man page for selected shows in content Text ahd search bar allows
#                       real-time or triggered regular expression searches.
#               If selected documents a DLL *.so library, show explorer for the data available about
#                   it.  Code for this is in hardInfo.py project.
#
#           For selected Column / Man page Folder:
#               Sort order toggle.
#               Switch to selected content filtering view.
#
#

from subprocess import Popen, PIPE, STDOUT
from datetime import datetime
from os import environ, listdir
from os.path import isfile, isdir
from collections import OrderedDict
from re import search, findall, match, compile
from gzip import open as gzOpen
from getopt import getopt, GetoptError
from sys import argv, stderr
from enum import Enum
from functools import partial
from copy import deepcopy

from tkinter import Tk, LabelFrame, Label, Listbox, OptionMenu, Button, Entry, Text, messagebox, Scrollbar, \
                    Frame, Checkbutton, Menu, Toplevel,  \
                    SUNKEN, RIDGE, RAISED, GROOVE, SINGLE, MULTIPLE, BROWSE, EXTENDED, END, NORMAL, DISABLED, \
                    BOTTOM, TOP, RIGHT, HORIZONTAL, VERTICAL, X, Y, BOTH, \
                    BooleanVar
from tkinter.ttk import Notebook

from model.HelpContent import HelpContent
from view.Help import HelpDialog

PROGRAM_TITLE = "Linux Tool Manager"

USAGE_HELP  = "\nHelp using Linux Tool Manager:\n" \
              "\tDevelopment Plans:\tActions which will be implemented:\n" \
              "\t\t0.  Show paths listed in os.environ['HOME']. \n" \
              "\t\t1.  Check to see if a particular Linux command line program is installed. \n" \
              "\t\t2.  Install a CLI command. \n" \
              "\t\t3.  Run a Linux CLI command with typed in options. \n" \
              "\t\t4.  Run a Linux CLI command with GUI component selected options, i.e. run a Tool. \n" \
              "\t\t5.  Save a Tool with a name for selection later. \n" \
              "\t\t6.  Load a saved Tool. \n" \
              "\t\t7.  Run a saved Tool. \n" \
              "\t\t8.  Ust the output of a saved tool as the input of another. \n" \
              "\t\t9.  View output in line, table, or tree form. \n" \
              "\t\t10. Determine which command line tools are installed by locating and listing and filtering all man pages. \n" \
              "\t\t11. From man page available list, show options for each command. \n" \
              "\t\t12. From man page available list, show man page, searchable. \n" \
              "\t\t13. From man page available list, show man page in navigatable sections. \n" \
              "\t\t14. Group commands by tags.  Include a default set for major functional groups and let user add their own. \n"


class Cursors(Enum):
    Hand_1      = 'hand1'
    Hand_2      = 'hand2'
    Arrow       = 'arrow'
    Circle      = 'circle'
    Clock       = 'clock'
    Cross       = 'cross'
    DotBox      = 'dotbox'
    Exchange    = 'exchange'
    Fluer       = 'fleur'
    Heart       = 'heart'
    Man         = "man"
    Mouse       = 'mouse'
    Pirate      = 'pirate'
    Plus        = 'plus'
    Shuttle     = "shuttle"
    Sizing      = 'sizing'
    Spider      = 'spider'
    Spraycan    = 'spraycan'
    Star        = 'star'
    Target      = 'target'
    Tcross      = 'tcross'
    Trek        = 'trek'
    Watch       = 'watch'

    def __str__(self):
        return self.value


class MenuItemType(Enum):
    Command     = 'Command'
    Check       = "Check Box"
    Radio       = "Radio Button"
    Separator   = "Separator"
    Submenu     = 'Sub-Menu'

    def __str__(self):
        return self.value


class Boolean:
    def __init__(self, init: bool):
        self.value = init
    def set(self, val: bool):
        self.value = val
    def get(self):
        return self.value


class PopupMenuItem(Enum):
    #   Man page file name filters:
    ShowSaved       = ("Show Saved Filters", MenuItemType.Command)
    NameAndSave     = ("Name and Save Filter", MenuItemType.Command)
    CopyTo          = ("Copy Filter to ...", MenuItemType.Command)
    ToggleContent   = ("Toggle Content Filtering", MenuItemType.Check, Boolean(False) )
    ExploreSO       = ("Explore *.so Library", MenuItemType.Command)

    #   Man page item selection in any of the lists:
    ShowManPage         = ("Show this Man Page", MenuItemType.Command)
    ShowManPageList     = ("Show Man Pages in List", MenuItemType.Command)
    ConfigureTool       = ("Configure Tool for this Runnable", MenuItemType.Command)
    ToolManager         = ("Tool Manager", MenuItemType.Command)

    def __str__(self):
        return self.value[0]

    def getType(self):
        return self.value[1]

    @staticmethod
    def listFilterItems():
        return (PopupMenuItem.ShowSaved, PopupMenuItem.NameAndSave,PopupMenuItem.CopyTo, PopupMenuItem.ToggleContent,
                PopupMenuItem.ExploreSO)

    @staticmethod
    def listManpageItems():
        return (PopupMenuItem.ShowManPage, PopupMenuItem.ShowManPageList, PopupMenuItem.ConfigureTool,
                PopupMenuItem.ToolManager)


class PopupMenu(Menu):

    DefaultDesign   = {
        'tearoff': 1,
        'title': "",
        'border': 3,
        'relief': RAISED,
        'tearoffcommand': None,
        'activebackground': 'gray',
        'activeforeground': 'blue',
        'activeborderwidth': 3,
        'bg': '#DDDDDD'
    }

    def __init__(self, context, title: str=None, features: tuple=None, design: dict=None, listener=None):
        if not isinstance(title, str):
            raise Exception("PopupMenu constructor - Invalid title argument:  " + str(listener))
        if listener is not None and not callable(listener):
            raise Exception("PopupMenu constructor - Invalid listener argument:  " + str(listener))
        if isinstance(features, tuple):
            for item in features:
                if not isinstance(item, PopupMenuItem):
                    raise Exception("PopupMenu constructor - Invalid PopupMenuItem argument:  " + str(item))
            self.features = features
        else:
            raise Exception("PopupMenu constructor - Invalid features argument:  " + str(features))
        if design is None:
            self.design = PopupMenu.DefaultDesign
            self.design['title'] = self.title = title
            self.design['tearoffcommand'] = self.menuTearOff
        else:
            #   validate then use
            pass

        self.listener = listener
        Menu.__init__(self, context, **self.design )

        self.menuFloating = False
        self.currentWidgetName = None

        for feature in self.features:
            #   need functype partial here
            if feature.value[1] == MenuItemType.Command:
                self.add_command(label=feature.value[0], command=partial(self.handleCommand, feature.value[0]))
            elif feature.value[1] == MenuItemType.Check:
                self.add_checkbutton(label=feature.value[0], variable=feature.value[2],
                                     command=partial(self.handleToggle, feature))
            elif feature.value[1] == MenuItemType.Radio:
                self.add_radiobutton(label=feature.value[0], command=partial(self.handleCommand, feature.value[0]))
            elif feature.value[1] == MenuItemType.Separator:
                self.add_separator()
            elif feature.value[1] == MenuItemType.Submenu:
                pass

        self.bind('<Unmap>', self.unmapMenu)
        self.bind('<Destroy>', self.destroyMenu)

    def messageReceiver(self, message: dict):
        if 'currentWidgetName' in message:
            self.currentWidgetName  = message['currentWidgetName']

    def handleCommand(self, featureName: str):
        self.listener({'source': "PopupMenu.handleCommand",
                       'featureName': featureName,
                       'currentWidgetName': self.currentWidgetName})

    def handleToggle(self, feature: PopupMenuItem):
        feature.value[2].set(not feature.value[2].get())
        self.listener({'source': "PopupMenu.handleCommand",
                       'featureName': feature.value[0],
                       'newValue': feature.value[2].get()})

    def exitMenu(self, event):
        print("PopupMenu.exitMenu")
        self.popupShown = False

    def menuTearOff(self, componentPathName, commandName):
        #   print("menuTearOff:\t" + str(componentPathName))
        self.menuFloating = True

    def unmapMenu(self, event):
        print("unmapMenu - self.menuFloating:\t" + str(self.menuFloating))
        if not self.winfo_ismapped() and not self.menuFloating:
            self.unpost()
            self.popupShown = False

    def destroyMenu(self, event):
        print("destroyMenu")
        #   self.destroy()
        self.unpost()
        self.popupShown = False


class ToolManager(Notebook):
    """
    This will have a ttk.Notebook with pages holding the various option dialogs possible.
    """

    def __init__(self, container, **keyWordArguments):
        Notebook.__init__(self, container)

        self.runnableSelection = RunnableSelection(mainView, text="Runnable File Selection", border=5, relief=SUNKEN)
        self.installationChecker = InstallationChecker(mainView, text="Installation Checker")
        self.toolDesigner = ToolDesigner(mainView, text="Linux Tool Designer")

        self.add(self.runnableSelection, state=NORMAL, sticky='nsew', padding=(5, 5), text='Runnable Selection')
        self.add(self.installationChecker, state=NORMAL, sticky='nsew', padding=(5, 5), text='Installation Checker')
        self.add(self.toolDesigner, state=NORMAL, sticky='nsew', padding=(10, 10), text='Tool Designer')
        self.tabIdRunnableSel = 0
        self.tabIdInstallCheck = 1
        self.tabIdToolDesigner = 2
        self.select(tab_id=self.tabIdToolDesigner)


class Utils:

    @staticmethod
    def collectManPages():
        manFileMap = OrderedDict()
        sub = Popen(('manpath',), stdout=PIPE, stderr=STDOUT)
        output, error_message = sub.communicate()
        pathList = output.decode('utf-8').strip().split(':')
        for pathName in pathList:
            contents = listdir(pathName)
            for itemName in contents:
                if itemName.startswith('man'):
                    if isdir(pathName + '/' + itemName):
                        manFileMap[pathName + '/' + itemName] = tuple(Utils.getFileList(pathName + '/' + itemName))
        return manFileMap

    @staticmethod
    def getFileList(pathName: str):
        fileList = listdir(pathName)
        newFileList = []
        for listItem in fileList:
            if isfile(pathName + '/' + listItem):
                newFileList.append(listItem)
        newFileList.sort()
        return newFileList

    @staticmethod
    def reSearch(stringList: list, regularExpression: str, includeList: list = None):
        checkOnly = False
        if isinstance(includeList, tuple) or isinstance(includeList, list):
            checkOnly = True
        matchList = []
        reProg = compile(regularExpression)
        for string in stringList:
            if isinstance(string, str):
                startIdx = 0
                while startIdx < len(string):
                    match = reProg.search(string, pos=startIdx)
                    if checkOnly:
                        if match is not None:
                            matchList.append(True)
                            break
                        else:
                            matchList.append(False)
                            break;
                    else:
                        if match is not None:
                            matchList.append(match)
                            startIdx = match.span()[0] + 1
                            print("\n" + str(match))
        return tuple(matchList)


class RunnableSelection(LabelFrame):

    def __init__(self, container, **keyWordArguments):

        LabelFrame.__init__(self, container, keyWordArguments)

        self.folderLabel    = Label(self, text=" Paths with Command Executable Files ", border=3, relief=RIDGE)

        self.runnableFolderListBox = Listbox(self, relief=RAISED, border=3, selectmode=SINGLE, width=30)
        self.pathList, self.timeStamp = tuple(environ['PATH'].split(':')), datetime.now()
        self.runnableFolderListBox.insert(END, *self.pathList)
        self.runnableFolderListBox.bind('<<ListboxSelect>>', self.folderSelection)

        self.runnableListBox = Listbox(self, relief=RAISED, border=3, selectmode=SINGLE, width=20)
        self.runnableFileList = Utils.getFileList(self.pathList[0])
        self.runnableListBox.insert(END, *self.runnableFileList)
        self.runnableListBox.bind('<<ListboxSelect>>', self.fileSelection)

        self.messageLabel = Label(self, text="Messages", width=50, border=3, relief=SUNKEN)

        self.folderLabel.grid(row=0, column=0, sticky="ne", padx=10, pady=10)
        self.runnableFolderListBox.grid(row=1, column=0, sticky="ne", padx=10, pady=10)
        self.runnableListBox.grid(row=1, column=1, sticky="nw", padx=10, pady=10)
        self.messageLabel.grid(row=2, column=0, columnspan=2, sticky="swe", padx=10, pady=10)

    def folderSelection(self, event):
        selection = self.runnableFolderListBox.selection_get()
        #   print("folderSelection:\t" + str(self.pathList[selection]))
        print("folderSelection:\t" + str(event))
        pathName = selection
        if isinstance(selection, int):
            pathName    = self.pathList[selection]
        if not isdir(pathName):
            return
        self.runnableFileList = Utils.getFileList(pathName)
        self.runnableListBox.delete(0, END)
        self.runnableListBox.insert(END, *self.runnableFileList)

    def fileSelection(self, event):
        #   selection = self.runnableListBox.selection_get()
        #   print("fileSelection:\t" + str(self.runnableFileList[selection]))
        print("fileSelection:\t" + str(event))

    def showManPage(self, commandName):
        print("showManPage:\t" + commandName)


class InstallationChecker(LabelFrame):

    def __init__(self, container, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)

        self.labelProgramName = Label(self, text=" Program name: ")
        self.entryProgramName = Entry(self, text="Ehter Name")

        self.labelProgramName.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.entryProgramName.grid(row=0, column=1, padx=5, pady=5, sticky='e')


class ToolConfig(LabelFrame):

    def __init__(self, container, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)


class ToolDesigner(LabelFrame):
    """
    ToolDesigner Plans: (2022-04-01)
    Include:
        A Text with the lists of each man page folder displayed horizontally, scrollable in both directions.
        A filter for all lists and a filter for each list.
            Filter: an Entry and a live toggle and a go button.
        A popup menu specific to each entry with selections to show the man page:
            All and searchable,
            In sections, navigatable,
        Same popup menu with selection to show options Frame with ability to select options and set the values
            of those which have them.  This Frame also saves named Tools / command configurations.
        Popup for this LabelFrame generally which has selections to:
            Regroup commands by top level functional tag,
            Select a Tool,
            Run a selected tool,
            Compose a stream of tools, i.e. output of one is input of next,
            ...
        ...
    """

    def __init__(self, container, **keyWordArguments):
        """
        Entire content needs to be grid'd into a frame and the frame placed into the Text as its sole window.
        Filter Entry's can be at bottom or top as long as the fact that they're regular expression filters is clear.
        "Go" button must fit next to filter or below it, along with toggle for keystroke update.
        Message label will span bottom of this Frame below the Text.
        Popup Toplevel's can handle details available in popup menus.
        :param container:
        :param keyWordArguments:
        """
        LabelFrame.__init__(self, container, keyWordArguments)

        self.filterPopupMenu = PopupMenu(self, title="Filter Options", features=PopupMenuItem.listFilterItems(),
                                         design=None, listener=self.messageReceiver)
        self.manPagePopupMenu   = PopupMenu(self, title="Runnable Options", features=PopupMenuItem.listManpageItems(),
                                            design=None, listener=self.messageReceiver)
        self.filterPopupShown = False
        self.manPagePopupShown = False

        self.bind('<Button-3>', self.rightClickHandler)
        self.configure(cursor=Cursors.Hand_1.value)

        self.manFileMap = Utils.collectManPages()   #   Security: make these lists into tuples
        #   Parallel structure determining which files get included in the Listbox of the path:
        self.manFileViewMapFiltered = OrderedDict()
        for filePath, fileList in self.manFileMap.items():
            self.manFileViewMapFiltered[filePath] = []
            for fileName in fileList:
                self.manFileViewMapFiltered[filePath].append(True)

        horizontalScroller = Scrollbar(self, orient=HORIZONTAL)
        verticalScroller = Scrollbar(self, orient=VERTICAL)
        self.contentText        = Text(self, state=DISABLED, border=5, relief=SUNKEN, padx=5, pady=5,
                                       yscrollcommand=verticalScroller.set, xscrollcommand=horizontalScroller.set)

        self.contentFrame               = None
        self.manFileListMap             = None
        self.manFilterEntryMap          = None
        self.manFilterGoButtonMap       = None
        self.manFilterAutoUpdateCheckMap     = None
        self.filePathMap                = None
        self.manFilterEntryStateMap     = None
        self.manAutoUpdateCheckVarMap   = None
        self.listboxNameMap             = None
        self.listboxPathMap             = None

        self.constructLayout(self.manFileMap)
        self.setModel(self.manFileMap)

        self.listViewState()

    def constructLayout(self, manFileMap: OrderedDict):
        print("constructLayout")
        self.contentFrame   = LabelFrame(self.contentText, text="Runnable File Search & Config", border=5, relief=RAISED )
        self.manFileListMap     = OrderedDict()
        self.manFilterEntryMap     = OrderedDict()
        self.manFilterGoButtonMap     = OrderedDict()
        self.manFilterAutoUpdateCheckMap     = OrderedDict()
        self.filePathMap    = OrderedDict()
        self.manFilterEntryStateMap     = OrderedDict()
        self.manAutoUpdateCheckVarMap = OrderedDict()
        self.listboxNameMap = OrderedDict()
        self.listboxPathMap = OrderedDict()

        horizontalScroller = Scrollbar(self, orient=HORIZONTAL, border=3, relief=GROOVE, width=15,
                                       cursor=Cursors.Hand_1.value)
        verticalScroller = Scrollbar(self, orient=VERTICAL, border=3, relief=GROOVE, width=15,
                                     cursor=Cursors.Hand_1.value)
        self.contentText        = Text(self, state=DISABLED, border=5, relief=SUNKEN, padx=5, pady=5,
                                       yscrollcommand=verticalScroller.set, xscrollcommand=horizontalScroller.set)
        horizontalScroller.config(command=self.contentText.xview)
        verticalScroller.config(command=self.contentText.yview)

        self.contentFrame   = LabelFrame(self.contentText, text="Runnable File Search & Config", border=5, relief=RAISED )
        col = 0
        for pathName, manFileList in manFileMap.items():
            filePath = pathName
            pathName = pathName.replace('/', '-').replace('.', '_')
            self.listboxNameMap[filePath]   = pathName
            self.listboxPathMap[pathName]   = filePath

            #   This is resulting in folder name not being updated in message bar at bottom until second click on new list.
            self.filePathMap[pathName] = filePath

            self.manFileListMap[pathName]  = Listbox(self.contentFrame, relief=RAISED, border=3, selectmode=SINGLE,
                                                     width=20, height=20, name=pathName, cursor=Cursors.Arrow.value)
            self.manFileListMap[pathName].bind('<<ListboxSelect>>', self.manFileSelected)
            self.manFileListMap[pathName].bind("<Enter>", self.mouseEnter)
            self.manFileListMap[pathName].bind("<Leave>", self.mouseLeave)
            self.manFileListMap[pathName].bind('<Button-3>', self.rightClickHandler)

            self.manFilterEntryMap['filter:' + pathName]  = Entry(self.contentFrame, border=3, relief=SUNKEN, width=20,
                                                                    name='filter:' + pathName)
            self.manFilterEntryMap['filter:' + pathName].insert(0, "regex filter")
            self.manFilterEntryMap['filter:' + pathName].bind("<Key>", self.entryKeyPress)
            self.manFilterEntryMap['filter:' + pathName].bind("<FocusIn>", self.entryFocusIn)
            self.manFilterEntryMap['filter:' + pathName].bind("<FocusOut>", self.entryFocusOut)
            self.manFilterEntryMap['filter:' + pathName].bind("<Enter>", self.mouseEnter)
            self.manFilterEntryMap['filter:' + pathName].bind("<Leave>", self.mouseLeave)
            self.manFilterEntryMap['filter:' + pathName].bind('<Button-3>', self.rightClickHandler)

            self.manFilterEntryStateMap['filter:' + pathName] = False

            updateFrame = Frame(self.contentFrame, border=2, relief=RIDGE)
            self.manFilterGoButtonMap['go:' + pathName] = Button(updateFrame, text='Go', width=2,
                                                                 name='go:' + pathName, cursor=Cursors.Arrow.value)
            self.manFilterGoButtonMap['go:' + pathName].bind('<ButtonRelease-1>', self.goButtonPress)
            self.manFilterGoButtonMap['go:' + pathName].bind("<Enter>", self.mouseEnter)
            self.manFilterGoButtonMap['go:' + pathName].bind("<Leave>", self.mouseLeave)
            self.manFilterGoButtonMap['go:' + pathName].bind('<Button-3>', self.rightClickHandler)


            self.manAutoUpdateCheckVarMap['check:' + pathName] = BooleanVar()
            self.manFilterAutoUpdateCheckMap['check:' + pathName]   = \
                Checkbutton(updateFrame, text="Auto Update", name='check:' + pathName, cursor=Cursors.Fluer.value,
                            variable=self.manAutoUpdateCheckVarMap['check:' + pathName])
            self.manFilterAutoUpdateCheckMap['check:' + pathName].bind("<Enter>", self.mouseEnter)
            self.manFilterAutoUpdateCheckMap['check:' + pathName].bind("<Leave>", self.mouseLeave)
            self.manFilterAutoUpdateCheckMap['check:' + pathName].bind('<ButtonRelease-1>', self.autoUpdateCheckClick)
            self.manFilterAutoUpdateCheckMap['check:' + pathName].bind('<Button-3>', self.rightClickHandler)

            self.manFilterGoButtonMap['go:' + pathName].grid(row=0, column=0)
            self.manFilterAutoUpdateCheckMap['check:' + pathName].grid(row=0, column=1)

            self.manFileListMap[pathName].grid(row=0, column=col, padx=5, pady=5, sticky="wns")
            self.manFilterEntryMap['filter:' + pathName].grid(row=1, column=col, padx=5, pady=5, sticky="wn")
            updateFrame.grid(row=2, column=col, padx=5, pady=5, sticky="n")
            col += 1

        self.contentText.config(state=NORMAL)
        self.contentText.window_create('1.0', window=self.contentFrame, stretch=True, align=BOTTOM)
        self.contentText.config(state=DISABLED)

        self.messageLabel = Label(self, text='messages', border=3, relief=SUNKEN, cursor=Cursors.DotBox.value)
        self.messageLabel.bind("<Enter>", self.mouseEnter)
        self.messageLabel.bind("<Leave>", self.mouseLeave)

        horizontalScroller.pack(side=BOTTOM, anchor='w', fill=X)
        verticalScroller.pack(side=RIGHT, fill=Y)
        self.contentText.pack(expand=True, fill=BOTH)
        self.messageLabel.pack(side=BOTTOM, anchor='w', fill=X)

    def setModel(self, manFileMap: OrderedDict):
        print("setModel")
        self.manFileMap = OrderedDict()
        for filePath, pathName in self.listboxNameMap.items():
            self.manFileListMap[pathName].delete(0, END)
            self.manFileMap[filePath]   = deepcopy(manFileMap[filePath])

            fileIdx = 0
            for fileName in self.manFileMap[filePath]:
                if self.manFileViewMapFiltered[filePath][fileIdx]:
                    self.manFileListMap[pathName].insert(END, fileName)
                fileIdx += 1

            self.manFileListMap[pathName].selection_set(0)

    def setViewState(self, viewState: dict):
        print("setViewState")
        if 'autoUpdates' in viewState:
            for controlName, boolVar in self.manAutoUpdateCheckVarMap.items():
                boolVar.set(viewState['autoUpdates'][controlName])
        if 'filters' in viewState:
            for controlName, entry in self.manFilterEntryMap.items():
                entry.delete(0, END)
                entry.insert(END, viewState['filters'][controlName])

        #   The Listbox's also need to be updated by applying the filters to the map of file name lists
        #       to build the filtered file name lists buffer.

    def getState(self):
        """
        Get the content, which is the manFileMap obtained initially from Utils.collectManPages().
        Since the view state, i.e the filter entry, the auto-update checkbox, and the particular selection
            in each list can be used to reconstruct the filtered buffer and view, the filter list
            burrer(s) do not need to be rerutned.
        :return:
        """
        print("getState")
        return self.manFileMap

    def getViewState(self):
        print("getViewState")
        viewState = {}
        viewState['autoUpdates'] = {}
        # auto-update check box settings:
        for controlName, checkVar in self.manAutoUpdateCheckVarMap.items():
            viewState['autoUpdates'][controlName] = checkVar.get()
        #   Filter regular expression settings:
        viewState['filters'] = {}
        for controlName, entry in self.manFilterEntryMap.items():
            viewState['filters'][controlName] = entry.get()
        #   Man page file list selections
        viewState['lists'] = {}
        for controlName, listBox in self.manFileListMap.items():
            selection = listBox.selection_get()
            viewState['lists'][controlName] = selection
        return viewState

    def messageReceiver(self, message: dict):
        print("messageReceiver:\t" + str(message))
        if 'source' in message:
            if message['source'] == "PopupMenu.handleCommand":
                if 'featureName' in message:
                    #   Filter features:
                    if message['featureName'] == "Show Saved Filters":
                        messagebox.showinfo('Show Saved Filters', "Not Implemented Yet")
                    elif message['featureName'] == "Name and Save Filter":
                        messagebox.showinfo('Name and Save Filter', "Not Implemented Yet")
                    elif message['featureName'] == "Copy Filter to ...":
                        messagebox.showinfo('Copy Filter to ...', "Not Implemented Yet")
                    elif message['featureName'] == "Toggle Content Filtering":
                        messagebox.showinfo('Toggle Content Filtering', "Not Implemented Yet")
                    elif message['featureName'] == "Explore *.so Library":
                        messagebox.showinfo('Explore *.so Library', "Not Implemented Yet")
                    #   Man page features
                    elif message['featureName'] == "Show this Man Page":
                        messagebox.showinfo('Show this Man Page', "Not Implemented Yet")

                    elif message['featureName'] == "Show Man Pages in List":
                        if 'currentWidgetName' in message:
                            self.showManPageListView(message['currentWidgetName'])
                        messagebox.showinfo('Show Man Pages in List', "Not Implemented Yet")

                    elif message['featureName'] == "Configure Tool for this Runnable":
                        messagebox.showinfo('Configure Tool for this Runnable', "Not Implemented Yet")
                    elif message['featureName'] == "Tool Manager":
                        messagebox.showinfo('Tool Manager', "Not Implemented Yet")


    def showManPageListView(self, currentWidgetName: str):
        print("showManPageListView:\t" + currentWidgetName)
        print("Listbox widget names:\t" + str(list(self.listboxPathMap.keys())))
        manPageContent = OrderedDict()
        folderPath = self.listboxPathMap[currentWidgetName]
        fileNameList = self.manFileMap[folderPath]
        for fileName in fileNameList:
            filePath = folderPath + '/' + fileName
            #   must run man on the file having isolated the name, all before first dot, instead, to get
            #   the correctly formatted output text.
            runnableName = fileName.split('.')[0]
            sub = Popen(['man', runnableName], stdout=PIPE, stderr=STDOUT)
            output, error_message = sub.communicate()
            text = output.decode('utf-8')
            manPageContent[fileName] = text

        geometryString = "900x500+350+50"
        self.manPageListToplevel = Toplevel(self)
        self.manPageListToplevel.geometry(geometryString)
        self.manPageListToplevel.title("Man Pages in: " + folderPath)
        helpContent = HelpContent("Man Pages in: " + folderPath, manPageContent)
        helpDialog = HelpDialog(self.manPageListToplevel, helpContent, 'all', geometryString)
        helpDialog.pack(expand=True, fill=BOTH)
        self.manPageListToplevel.mainloop()

    def manFileSelected(self, event):
        widgetName  = event.widget._name
        print("manFileSelected in list:\t" + widgetName)
        selection = self.manFileListMap[widgetName].selection_get()
        self.messageLabel.config(text="Folder: " + self.filePathMap[widgetName] + "\t\tFile: " + str(selection))

    def entryKeyPress(self, event):
        print("entryKeyPress in filter:\t" + event.widget._name)

    def entryFocusIn(self, event):
        print("entryFocusIn in filter:\t" + event.widget._name)
        if not self.manFilterEntryStateMap[event.widget._name]:
            event.widget.delete(0, END)
            self.manFilterEntryStateMap[event.widget._name] = True

    def entryFocusOut(self, event):
        print("entryFocusOut in filter:\t" + event.widget._name)

    def mouseEnter(self, event):
        event.widget.configure(foreground='blue')

    def mouseLeave(self, event):
        event.widget.configure(foreground='black')


    def goButtonPress(self, event):
        print("goButtonPress:\t" + event.widget._name)
        goButtonName = event.widget._name
        pathName    = goButtonName.split(':')[1].strip()
        filterText = self.manFilterEntryMap['filter:' + pathName].get()
        print("\tFilter Text:\t" + filterText)
        self.applyFilter(self.listboxPathMap[pathName], filterText)

    def autoUpdateCheckClick(self, event):
        print("autoUpdateCheckClick:\t" + event.widget._name)

    def rightClickHandler(self, event):
        print("rightClickHandler widget-_name:\t" + event.widget._name)
        self.manPagePopupMenu.messageReceiver({'currentWidgetName': event.widget._name})
        if "filter:" in event.widget._name or 'go:' in event.widget._name or "check" in event.widget._name:
            try:
                self.filterPopupMenu.tk_popup(event.x_root, event.y_root, 0)
                self.filterPopupShown = True
                #   print("self.popupShown = True:\t" + str(self.filterPopupShown))
            finally:
                self.filterPopupMenu.grab_release()
        else:   #   Listbox names do not have any prefix:
            try:
                self.manPagePopupMenu.tk_popup(event.x_root, event.y_root, 0)
                self.manPagePopupShown = True
            finally:
                self.manPagePopupMenu.grab_release()


    def applyFilter(self, folderPath: str, filterText: str):
        print("applyFilter:\t" + "pathName:\t" + folderPath + "\t\tfilterText:\t" + filterText)
        # Update list of bool saying which is to be included in display
        self.manFileViewMapFiltered[folderPath] = \
            Utils.reSearch(self.manFileMap[folderPath], filterText, self.manFileViewMapFiltered[folderPath])
        #   Update the Listbox in the current view:
        self.manFileListMap[self.listboxNameMap[folderPath]].delete(0, END)
        fileIdx = 0
        for fileName in self.manFileMap[folderPath]:
            if self.manFileViewMapFiltered[folderPath][fileIdx]:
                self.manFileListMap[self.listboxNameMap[folderPath]].insert(END, fileName)
            fileIdx += 1

    def listViewState(self):
        print("\nlistState:")
        viewState = self.getViewState()
        print("\tList Selections:")
        for controlName, value in viewState['lists'].items():
            print("\t\t" + controlName + ":\t" + str(value))
        print("\tFilter Entries:")
        for controlName, value in viewState['filters'].items():
            print("\t\t" + controlName + ":\t" + str(value))
        print("\tAuto Update Toggles:")
        for controlName, value in viewState['autoUpdates'].items():
            print("\t\t" + controlName + ":\t" + str(value))


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":
    print("argv:\t" + str(argv))
    options = (('-h',''), ('-d', 'td'))
    #   See if user wants the default options
    if argv[1] not in ['-d', '--default']:
        try:
            options, arguments = getopt(argv[1:], 'hd:', ['help', 'doc:'])
        except GetoptError as optErr:
            print("Unrecognized option in command line arguments:\t" + str(argv[1:]), file=stderr)
            print(USAGE_HELP)
            exit(1)

    for opt, arg in options:
        if opt in ['-h', '--help']:
            print(USAGE_HELP)
        elif opt in ['-d', '--doc']:
            if arg == 'td':
                print(ToolDesigner.__doc__)

    mainView = Tk()

    """
    #   Filtering the man page files using regular expressions:
    userInput = '^ls\.'
    manFileMap = Utils.collectManPages()
    filteredManFileMap = OrderedDict()
    for manFolder, fileList in manFileMap.items():
        filteredManFileMap[manFolder] = Utils.reSearch( fileList, userInput)
        print(manFolder)
    for manFolder in filteredManFileMap:
        filteredManFileMap[manFolder]   = tuple(filteredManFileMap[manFolder])

    #   Loading a man page file from its *.gz file:
    nroffPageFile = gzOpen('/usr/share/man/man1/acpi.1.gz', 'rb')
    acpiManBytes = nroffPageFile.read()
    acpiManNroff    = acpiManBytes.decode('utf-8')
    print(acpiManNroff)
    """

    mainView.geometry("800x600+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    """
    runnableSelection     = RunnableSelection(mainView, text="Runnable File Selection", border=5, relief=SUNKEN)
    runnableSelection.pack( expand=True, fill=BOTH)
    installationChecker     = InstallationChecker(mainView, text="Installation Checker")
    installationChecker.pack(expand=True, fill=BOTH)
    """
    toolManager = ToolManager(mainView, border=5, relief=RAISED)
    toolManager.pack(expand=True, fill=BOTH, padx=5, pady=5)

    mainView.mainloop()
