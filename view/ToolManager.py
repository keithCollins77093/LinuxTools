#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         view/ToolManager.py
#   Date Started:   April 8, 2022
#   Purpose:        GUI components fot Tool Management.
#   Development:
#       Features:
#           In addition to designing a tool using the property sheet of flags and arguments, the user
#               can type a line for the tool, which is easy to parse, after all they had to use C when this
#               stuff was originally designed, amd arg values can have place holders which are fill-able
#               on each run.
#           The ToolManager should be a LabelFrame which therefore can be places in any compatible context,
#               like a Toplevel or other Frame.  It will therefore need methods to:
#                   set its data content,
#                   set its view state,
#                   get its data content,
#                   get its view state.
#               Once instantiated, the parent or context component cannot be changed without making an entirely
#               new copy.
#
#       2022-04-08: Tool Design Workflows Requirements Specification
#           Assumptions:
#               A button, checkbox, or menu option is available at all times to show / hide the ManPage Treeview
#               and a man page list-detail for the sections and their text contents.
#               Possibly a button or menu selection to shell out and see the man page for a command in the terminal.
#           1)  CLI style:
#               a)  Type command with flags and arguments into an Entry control
#               b)  Type tool name into another Entry control
#               c)  Type description into a Text control
#               d)  Press [Save] button
#               e)  Application attempts to save and asks you to type another name if the one provided is taken.
#               f)  Option available to show a list of names of tools.
#                   1)  Option selected => list-detail Toplevel shows with list of tool names on the left and
#                           a property sheet with each one's details on left, updated on selection from list.
#           2)  Property Sheet Style
#               a)  A blank property sheet displays and the user selects the flags they want,
#                       using a Checkbox for each, and enters their arguments if available and desired,
#                       in the order they want them as they appear in the command line text Label.
#               b)  The user can re-arrange the order with a pop-up list.
#               c)  Type tool name into another Entry control
#               d)  Type description into a Text control
#               e)  Click the [Save] button
#               e)  Application attempts to save and asks you to type another name if the one provided is taken.
#               f)  Option available to show a list of names of tools.
#                   1)  Option selected => list - detail Toplevel shows with list of tool names on the left and
#                           a property sheet with each one's details on left, updated on seletion from list.
#           3)  Template Style
#               a)  Option available to show a list of names of tools.
#                   1)  Option selected => list - detail Toplevel shows with list of tool names on the left and
#                           a property sheet with each one's details on left, updated on selection from list.
#                   2)  Select a tool from list and press [Select] button.
#               b)  Property sheet for setting flags and arguments is populated with the command and its arguments.
#               c)  User modifies the selection of flags and the arguments chosen or entered and the changes
#                       appear in the command line text Label.
#               d)  The user can re-arrange the order with a pop-up list.
#               e)  Enter an new name for the new tool.
#               f)  The rest is the same as (e) through (f) in (2), Property Sheet Style
#
from copy import deepcopy
from collections import OrderedDict

from tkinter import Tk, messagebox, LabelFrame, Button, Label, Listbox, OptionMenu, Text, Message, \
                    BOTH, FLAT, RIDGE, GROOVE, SUNKEN, RAISED, NORMAL, SINGLE, END, \
                    DISABLED, WORD
from tkinter.ttk import Notebook

from model.Installation import USER_DATA_FOLDER
from model.ToolDB import ToolManager as ToolManDB, ToolSet, Tool
from view.Components import JsonTreeViewFrame, JsonTreeView

PROGRAM_TITLE = "Tools Manager"

INSTALLING  = False
TESTING     = False


class OptionDetail(LabelFrame):

    def __init__(self, container, optionDef: dict, **keyWordArguments):
        if not isinstance(optionDef, dict):
            raise Exception("SynopsisPanel constructor - Invalid optionDef argument:  " + str(optionDef))
        self.optionDef = deepcopy(optionDef)
        LabelFrame.__init__(self, container, keyWordArguments)
        #   Members: text, description, optional argument.

        self.labelText = Label(self, text='Text', border=3, relief=RIDGE, width=12)
        self.labelTextVal = Label(self, text=optionDef['text'], border=3, relief=RIDGE, width=40)
        self.labelDescription = Label(self, text='Description', border=3, relief=RIDGE, width=12)
        #   , border=4, relief=SUNKEN, state=DISABLED, wrap=WORD,
        #                                fg="#000088", padx=10, pady=10
        #   self.textDescriptionVal = Text(self, text=optionDef['description'], border=3, relief=RIDGE, width=400)
        self.textDescriptionVal = Text(self, border=4, relief=SUNKEN, state=DISABLED, wrap=WORD, fg="#000088",
                                       padx=10, pady=10, width=40,
                                       height=min(len(optionDef['description'].split('\n')), 8))
        self.textDescriptionVal.config(state=NORMAL)
        self.textDescriptionVal.delete('1.0', 'end')
        self.textDescriptionVal.insert(END, optionDef['description'])
        self.textDescriptionVal.config(state=DISABLED)

        self.labelText.grid(row=0, column=0, padx=15, pady=5, sticky='w')
        self.labelTextVal.grid(row=0, column=1, padx=15, pady=5, sticky='w')
        self.labelDescription.grid(row=1, column=0, padx=15, pady=5, sticky='w')
        self.textDescriptionVal.grid(row=1, column=1, padx=15, pady=5, sticky='w')

        if 'argument' in optionDef:
            self.labelArgument = Label(self, text='Argument', border=3, relief=RIDGE, width=12)
            self.labelArgumentVal = Label(self, text=optionDef['argument'], border=3, relief=RIDGE, width=40)
            self.labelArgument.grid(row=2, column=0, padx=15, pady=5, sticky='w')
            self.labelArgumentVal.grid(row=2, column=1, padx=15, pady=5, sticky='w')
            self.labelArgument.bind("<Enter>", self.mouseEntered)
            self.labelArgument.bind("<Leave>", self.mouseLeft)

        self.labelText.bind("<Enter>", self.mouseEntered)
        self.labelText.bind("<Leave>", self.mouseLeft)
        self.labelTextVal.bind("<Enter>", self.mouseEntered)
        self.labelTextVal.bind("<Leave>", self.mouseLeft)
        self.labelDescription.bind("<Enter>", self.mouseEntered)
        self.labelDescription.bind("<Leave>", self.mouseLeft)

    def mouseEntered(self, event):
        event.widget.configure(fg='blue', relief=RAISED)

    def mouseLeft(self, event):
        event.widget.configure(fg='black', relief=RIDGE)


class SynopsisPanel(LabelFrame):

    def __init__(self, container, synopsis: tuple, options: dict, **keyWordArguments):
        if not isinstance(synopsis, tuple):
            raise Exception("SynopsisPanel constructor - Invalid synopsis argument:  " + str(synopsis))
        if not isinstance(options, dict):
            raise Exception("SynopsisPanel constructor - Invalid options argument:  " + str(options))
        self.synopsisList = synopsis
        LabelFrame.__init__(self, container, keyWordArguments)

        self.optionsList = []
        self.currentOptionDef = None
        for sectionName, optionSet in options.items():
            self.optionsList.append(sectionName)
            for option in optionSet:
                if self.currentOptionDef is None:
                    self.currentOptionDef = option
                self.optionsList.append("    " + str(option['text']))
        self.optionsList = tuple(self.optionsList)

        self.labelSynopsis      = Label( self, text="Synopsis", width=35, border=3, relief=RAISED)
        self.listBoxSynopsis    = Listbox(self, relief=RAISED, border=3, selectmode=SINGLE, width=35, height=15)
        self.listBoxSynopsis.insert(END, *self.synopsisList)
        self.listBoxSynopsis.bind('<<ListboxSelect>>', self.synopsisItemSelected)

        self.labelOptions      = Label( self, text="Options", width=30, border=3, relief=RAISED)
        self.listBoxOptions = Listbox(self, relief=RAISED, border=3, selectmode=SINGLE, width=30, height=15)
        self.listBoxOptions.insert(END, *self.optionsList)
        self.listBoxSynopsis.bind('<<ListboxSelect>>', self.optionSelected)

        self.optionDetail = OptionDetail(self, self.currentOptionDef, border=4, relief=RAISED)

        self.labelSynopsis.bind('<Enter>', self.mouseEntered)
        self.labelSynopsis.bind('<Leave>', self.mouseLeft)
        self.listBoxSynopsis.bind('<Enter>', self.mouseEntered)
        self.listBoxSynopsis.bind('<Leave>', self.mouseLeft)
        self.labelOptions.bind('<Enter>', self.mouseEntered)
        self.labelOptions.bind('<Leave>', self.mouseLeft)
        self.listBoxOptions.bind('<Enter>', self.mouseEntered)
        self.listBoxOptions.bind('<Leave>', self.mouseLeft)


        self.labelSynopsis.grid(row=0, column=0, columnspan=2, sticky='ew', padx=15, pady=5)
        self.listBoxSynopsis.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=15, pady=5)
        self.labelOptions.grid(row=0, column=2, columnspan=2, sticky='ew', padx=15, pady=5)
        self.listBoxOptions.grid(row=1, column=2, columnspan=2, sticky='nsew', padx=15, pady=5)

        self.optionDetail.grid(row=2, column=0, columnspan=4, sticky='nsew', padx=15, pady=5)

    def synopsisItemSelected(self, event):
        print("synopsisItemSelected:\t" + self.listBoxSynopsis.selection_get())

    def optionSelected(self, event):
        print("optionSelected:\t" + self.listBoxOptions.selection_get())

    def mouseEntered(self, event):
        event.widget.configure(fg='blue')

    def mouseLeft(self, event):
        event.widget.configure(fg='black')

class ToolsTree(LabelFrame):

    def __init__(self, container, toolMap, toolSetIndex, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)
        toolMap, toolSetIndex = ToolManDB.readDB()

        self.jsonTreeViewFrame = JsonTreeViewFrame(self, toolMap, {"listener": self.messageReceiver,
                                                                   "mode": JsonTreeView.MODE_STRICT}, width=700)

        self.labelMessages = Label(self, text="messages", width=80, border=3, relief=SUNKEN)

        self.jsonTreeViewFrame.grid(row=2, column=1, columnspan=5, padx=10, pady=5)
        self.labelMessages.grid(row=10, column=0, columnspan=5, padx=10, pady=5)

    def messageReceiver(self, message: dict):
        print("ToolsTree.messageReceiver:\t" + str(message))


class ToolConfigDetail(LabelFrame):

    def __init__(self, container, toolConfig: Tool, **keyWordArguments):
        LabelFrame.__init__(self, container, width=300, **keyWordArguments)
        print(toolConfig)

        self.labelName   = Label(self, text='Name', width=12, relief=SUNKEN)
        self.labelName.bind('<Enter>', self.mouseEnter)
        self.labelName.bind('<Leave>', self.mouseLeave)
        self.labelNameVal   = Label(self, text=toolConfig.getName(), width=25, relief=SUNKEN)
        self.labelNameVal.bind('<Enter>', self.mouseEnter)
        self.labelNameVal.bind('<Leave>', self.mouseLeave)

        self.labelDescription   = Label(self, text="Description", width=12, relief=SUNKEN)
        self.labelDescription.bind('<Enter>', self.mouseEnter)
        self.labelDescription.bind('<Leave>', self.mouseLeave)
        self.messageDescription = Message( self, text=toolConfig.getDescription(), width=200, relief=SUNKEN)
        self.messageDescription.bind('<Enter>', self.mouseEnter)
        self.messageDescription.bind('<Leave>', self.mouseLeave)

        self.labelCommand = Label(self, text='Command', width=12, relief=SUNKEN)
        self.labelCommand.bind('<Enter>', self.mouseEnter)
        self.labelCommand.bind('<Leave>', self.mouseLeave)
        self.labelCommandVal = Label(self, text=toolConfig.getCommand(), width=25, relief=SUNKEN)
        self.labelCommandVal.bind('<Enter>', self.mouseEnter)
        self.labelCommandVal.bind('<Leave>', self.mouseLeave)

        self.labelArguments   = Label(self, text="Arguments", width=12, relief=SUNKEN)
        self.labelArguments.bind('<Enter>', self.mouseEnter)
        self.labelArguments.bind('<Leave>', self.mouseLeave)
        argumentsStr = ""
        argIdx = 0
        for argument in toolConfig.getArgList():
            if argIdx > 0:
                argumentsStr += argument + '\n'
            argIdx += 1
        self.messageArguments = Message( self, text=argumentsStr, width=200, relief=SUNKEN)
        self.messageArguments.bind('<Enter>', self.mouseEnter)
        self.messageArguments.bind('<Leave>', self.mouseLeave)

        self.labelName.grid(row=0, column=0, sticky='w', padx=15, pady=5)
        self.labelNameVal.grid(row=0, column=1, sticky='w', padx=15, pady=5)
        self.labelDescription.grid(row=1, column=0, sticky='w', padx=15, pady=5)
        self.messageDescription.grid(row=1, column=1, sticky='w', padx=15, pady=5)
        self.labelCommand.grid(row=2, column=0, sticky='w', padx=15, pady=5)
        self.labelCommandVal.grid(row=2, column=1, sticky='w', padx=15, pady=5)
        self.labelArguments.grid(row=3, column=0, sticky='w', padx=15, pady=5)
        self.messageArguments.grid(row=3, column=1, sticky='w', padx=15, pady=5)

    def mouseEnter(self, event):
        event.widget.configure(fg="blue", relief=RAISED)

    def mouseLeave(self, event):
        event.widget.configure(fg="black", relief=SUNKEN)


class ToolsListDetail(LabelFrame):

    def __init__(self, container, toolMap: OrderedDict, toolSetIndex: OrderedDict, **keyWordArguments ):
        LabelFrame.__init__(self, container, keyWordArguments)

        self.toolMap = deepcopy(toolMap)
        self.toolSetIndex = deepcopy(toolSetIndex)
        self.detailFrameMap = {}
        for toolName, toolConfig in self.toolMap.items():
            self.detailFrameMap[toolName] = ToolConfigDetail(self, toolConfig, text=toolName)
        self.currentToolDetailView = None

        self.toolNameListbox    = Listbox(self, relief=SUNKEN, border=3, selectmode=SINGLE, width=30)
        self.toolNameListbox.insert(END, *toolMap.keys())
        self.toolNameListbox.bind('<<ListboxSelect>>', self.toolSelection)
        self.toolNameListbox.bind('<Enter>', self.mouseEntered)
        self.toolNameListbox.bind('<Leave>', self.mouseLeft)
        self.toolNameListbox.selection_set(0)

        self.toolNameListbox.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.detailFrameMap[tuple(self.toolMap.keys())[0]].grid(row=0, column=3, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.currentToolDetailView = self.detailFrameMap[tuple(self.toolMap.keys())[0]]

    def mouseEntered(self, event):
        event.widget.configure(foreground='blue')

    def mouseLeft(self, event):
        event.widget.configure(foreground='black')

    def toolSelection(self, *args):
        selection =  str(self.toolNameListbox.selection_get())
        print("toolSelection:\t" + selection)
        if self.currentToolDetailView is not None:
            self.currentToolDetailView.grid_forget()
        self.detailFrameMap[selection].grid(row=0, column=3, columnspan=2, padx=10, pady=5, sticky="nsew")
        self.currentToolDetailView = self.detailFrameMap[selection]

    def messageReceiver(self, message: dict):
        print("ToolsListDetail.messageReceiver:\t" + str(message))


class ToolManagerTabs(Notebook):

    def __init__(self, container, **keyWordArguments):
        Notebook.__init__(self, container)
        toolMap, toolSetIndex = ToolManDB.readDB()
        self.toolsTree = ToolsTree( self, toolMap, toolSetIndex, **keyWordArguments)
        self.toolsListDetail = ToolsListDetail(self, toolMap, toolSetIndex, **keyWordArguments )
        self.add(self.toolsListDetail, state=NORMAL, sticky='nsew', padding=(5, 5), text='Tools List')
        self.add(self.toolsTree, state=NORMAL, sticky='nsew', padding=(5, 5), text='Tools Tree')

    def messageReceiver(self, message: dict):
        print("ToolManager.messageReceiver:\t" + str(message))


class ToolManager(LabelFrame):
    """
    This is the master frame with the controls whic are applied to the various pages of the notebook which
    is the content view of this dialog.
    """
    def __init__(self, container, **keyWordArguments):
        pass


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":

    toolSet = None
    if INSTALLING:
        exit(0)

    if TESTING:
        exit(0)

    print(__doc__)

    mainView = Tk()
    mainView.geometry("700x400+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    #   toolManager = ToolsTree(mainView, border=5, relief=RAISED)
    toolManager = ToolManagerTabs(mainView, border=5, relief=RAISED)
    toolManager.pack(expand=True, fill=BOTH)

    mainView.mainloop()
