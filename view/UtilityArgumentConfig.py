#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 18, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         view/UtilityArgumentConfig
#   Purpose:        View for petting a particular flag and argument configuration for a command line utility.
#   Development:
#

import os, sys, string
from pathlib import Path
from collections import OrderedDict
from math import ceil
from functools import partial
from copy import deepcopy

from tkinter import Tk, Label, Entry, Button, Text, Frame, LabelFrame, filedialog, messagebox, Checkbutton, Menu, \
                    Toplevel, Message, Listbox, \
                    StringVar, IntVar, BooleanVar, \
                    INSERT, END, N, S, E, W, LEFT, CENTER, RIGHT, BOTH, \
                    SUNKEN, FLAT, RAISED, GROOVE, RIDGE, DISABLED, NORMAL
from tkinter.ttk import Combobox
#  import idlelib
from tkinter.messagebox import ABORT, RETRY, IGNORE, OK, CANCEL, YES, NO, ERROR, INFO, QUESTION, WARNING

from model.Util import Cursors
from service.linux.Utilities import ManPageScanner
from model.UtilConfig import Configuration
from view.ProgrammableMenu import ProgrammablePopup
from view.ToolOutput import ToolOutput
from view.FrameScroller import FrameScroller
from model.ManPage import ManSection
from view.ToolManager import ToolManagerTabs
from model.ToolDB import ToolManager, Tool


class ConfirmCommandLine(Toplevel):

    def __init__(self, container, progName: str, optionsIncluded: tuple, _title: str=None, synopsis: str=None,
                 listener=None, **keyWordArguments):
        if not isinstance(progName, str):
            raise Exception("ConfirmCommandLine constructor - Invalid progName argument:  " + str(progName))
        if not isinstance(optionsIncluded, tuple):
            raise Exception("ConfirmCommandLine constructor - Invalid optionsIncluded argument:  " + str(optionsIncluded))
        if not isinstance(_title, str):
            raise Exception("ConfirmCommandLine constructor - Invalid title argument:  " + str(_title))
        if not isinstance(synopsis, str):
            raise Exception("ConfirmCommandLine constructor - Invalid synopsis argument:  " + str(synopsis))
        if listener is not None and not callable(listener):
            raise Exception("ConfirmCommandLine constructor - Invalid listener argument:  " + str(listener))

        Toplevel.__init__(self, container, keyWordArguments)
        self._title = _title
        self.title(self._title)
        self.geometry("500x175+100+200")
        self.progName = progName
        self.synopsisText = synopsis
        self.listener = listener
        self.optionsIncluded = None
        self.constructLayout()
        self.setModel(optionsIncluded)

    def constructLayout(self):
        self.labelCommandLine   = Label(self, text=" Command Line that will Run: ", width=55, anchor='w',
                                        border=3, relief=GROOVE)
        self.labelCommandLine.bind("<Enter>", self.mouseEnter)
        self.labelCommandLine.bind("<Leave>", self.mouseLeave)
        self.textCommandLine = Text(self, width=55, height=1, state=NORMAL, border=4, relief=SUNKEN)
        self.textCommandLine.insert(END, "ls -l -run_this_in_one_hour --help -dev=/media/keithcollins/ISOpartition")

        self.labelToolName = Label(self, text=" Tool Name: ", border=3, relief=RIDGE)
        self.toolNameVar = StringVar()
        self.toolNameVisited = False
        self.entryToolName = Entry(self, border=3, relief=SUNKEN, width=25, textvariable=self.toolNameVar)
        self.entryToolName.insert(END, "tool name")
        self.entryToolName.bind('<FocusIn>', self.entryNameFocused)

        #   NEED: Tool Description Label and Entry

        self.buttonSave = Button(self, text="Save", command=self.saveTool)
        self.buttonCancel = Button(self, text="Cancel", command=self.cancelSaveTool)
        self.viewSynopsisVar = BooleanVar()
        self.checkboxViewSynopsis   = Checkbutton(self, text="View Synopsis", border=3, relief=RIDGE,
                                                  variable=self.viewSynopsisVar)
        self.viewSynopsisVar.set(False)

        self.textLineHeight = 4
        if len(self.synopsisText.split('\n')) > 8:
            self.textLineHeight = 6
        self.textSynopsis   = Text(self, width=55, height=self.textLineHeight, border=3, relief=SUNKEN, state=NORMAL)
        self.textSynopsis.insert(END, self.synopsisText)
        self.textSynopsis.configure(state=DISABLED)

        self.viewSynopsisVar.trace_add("write", self.synopsisViewToggle)
        self.buttonSave.bind('<Enter>', self.mouseEnter)
        self.buttonSave.bind('<Leave>', self.mouseLeave)
        self.buttonCancel.bind('<Enter>', self.mouseEnter)
        self.buttonCancel.bind('<Leave>', self.mouseLeave)
        self.checkboxViewSynopsis.bind('<Enter>', self.mouseEnter)
        self.checkboxViewSynopsis.bind('<Leave>', self.mouseLeave)
        self.labelToolName.bind('<Enter>', self.mouseEnter)
        self.labelToolName.bind('<Leave>', self.mouseLeave)
        self.entryToolName.bind('<Enter>', self.mouseEnter)
        self.entryToolName.bind('<Leave>', self.mouseLeave)

        self.labelCommandLine.grid(row=0, column=0, columnspan=4, padx=15, pady=5)
        self.textCommandLine.grid(row=1, column=0, columnspan=4, padx=15, pady=10)

        self.labelToolName.grid(row=2, column=0, columnspan=1, padx=10, pady=5)
        self.entryToolName.grid(row=2, column=1, columnspan=2, padx=10, pady=5)

        self.buttonSave.grid(row=3, column=0, columnspan=1, padx=10, pady=5)
        self.buttonCancel.grid(row=3, column=1, columnspan=1, padx=10, pady=5)
        self.checkboxViewSynopsis.grid(row=3, column=2, columnspan=2, padx=10, pady=10)

    def setModel(self, optionsList: tuple):
        self.optionsIncluded = optionsList
        commandText = self.progName
        for option in self.optionsIncluded:
            #   print(str(option))
            commandText += ' ' + option['text']
        self.textCommandLine.delete('1.0', END)
        self.textCommandLine.insert(END, commandText)

    def getModel(self):
        return self.optionsIncluded

    def mouseEnter(self, event):
        event.widget.configure( fg='blue')

    def mouseLeave(self, event):
        event.widget.configure( fg='black')

    def saveTool(self):
        print("saveTool")
        toolName = self.entryToolName.get()
        if ToolManager.toolExists(toolName):
            messagebox.showwarning("Tool Name Exists", "There is a tool with the same name\n"
                                                       "in the database already:  " + toolName)
        else:
            ToolManager.addTool(Tool(toolName, 'description', self.progName, OrderedDict({})))

    def cancelSaveTool(self):
        if self.listener is not None:
            self.listener({'source': "ConfirmCommandLine", 'action': 'cancelSaveTool'})

    def synopsisViewToggle(self, *args):
        print("synopsisViewToggle:\t" + str(self.viewSynopsisVar.get()))
        if self.viewSynopsisVar.get():
            if self.textLineHeight == 4:
                self.geometry("500x275+100+200")
            else:
                self.geometry("500x325+100+200")
            self.textSynopsis.grid(row=4, column=0, columnspan=4, padx=10, pady=10)
        else:
            self.textSynopsis.grid_forget()
            self.geometry("500x175+100+200")

    def entryNameFocused(self, event):
        print("entryNameFocused")
        if not self.toolNameVisited:
            self.entryToolName.selection_range(0, END)
            self.toolNameVisited = True


class ParameterSettings(LabelFrame):

    FONT_FAMILY     = "Arial"
    FONT_SIZE       = 10
    DEFAULT_FONT    = (FONT_FAMILY, FONT_SIZE)

    def __init__(self, container, name: str, utilDescriptor: dict, enums: dict, **keyWordArguments):
        if 'frameConfig' in keyWordArguments and isinstance(keyWordArguments['frameConfig'], dict):
            LabelFrame.__init__(self, container, name=name, **keyWordArguments['frameConfig'])
        else:
            LabelFrame.__init__(self, container, name=name)
        self.container = container
        if utilDescriptor == None:
            raise Exception('FlagSettings constructor - utilDescriptor argument = None')
        if enums == None:
            self.enums  = {}
        else:
            self.enums  = enums
        self.utilDescriptor = utilDescriptor
        self.config(text="Parameter Settings")

        self.constructParametterCheckBoxes()
        #self.constructValueControls()

        rowIndex = 0
        for name, definition in self.utilDescriptor.items():
            self.parameterCheckbuttons[name].grid(row=rowIndex, column=0, sticky=W)
            rowIndex += 1
        """
        rowIndex = 0
        for name, definition in self.utilDescriptor.items():
            self.valueControls[name].grid(row=rowIndex, column=2, padx=5, sticky=E)
            rowIndex += 1
        """
        # self.constructValueControls()
        self.currentParametterName  = None

        self.messageDescription = Message(self, name="messageDescription", text="Messages", font=ConfigSettings.DEFAULT_FONT, width=350)
        self.messageDescription.grid(row=100, column=0, padx=15, pady=15, sticky=W)

        self.constructValueControls()

    def constructParametterCheckBoxes(self):
        self.parameterCheckbuttons  = {}
        self.parameterIntVars       = {}
        rowIndex = 0
        maxWidth = 1
        for name, definition in self.utilDescriptor.items():
            if len(name) > maxWidth:
                maxWidth    = len(name)
            self.parameterIntVars[name]  = IntVar()
            self.detailsVar = IntVar()
            self.parameterCheckbuttons[name] = Checkbutton(self, name=name, text=name, font=ParameterSettings.DEFAULT_FONT,
                                                           variable=self.parameterIntVars[name], bg='darkgray', relief=FLAT,
                                                           anchor=W)
            self.parameterIntVars[name].trace_variable('w', self.parameterCheckbuttonChanged)
            self.parameterCheckbuttons[name].bind('<Enter>', self.mouseEnteredParameter)
            self.parameterCheckbuttons[name].bind('<Leave>', self.mouseLeftParameter)

            self.detailsVar.set(0)
            rowIndex += 1

        for name, checkbutton in self.parameterCheckbuttons.items():
            checkbutton.config(width=maxWidth + 3)

    def constructValueControls(self):
        self.frameValueEntry    = Frame(self, name="frameValueEntry", relief=RIDGE, borderwidth=3)
        self.frameValueEntry.grid(row=len(self.utilDescriptor.items())+2, column=0, sticky=W)

        self.entryShowCount     = 0
        self.valueControls      = {}
        self.valueStringVars    = {}
        maxWidth = 1
        rowIndex = 0
        for name, definition in self.utilDescriptor.items():
            if len(name) > maxWidth:
                maxWidth    = len(name)
            if definition['value'] in self.enums:      #   this will be a combo box dropdown showing the enumerated possibilities
                self.valueStringVars[name]  = StringVar()
                values = []
                for value in self.enums[definition['value']]['values']:
                    values.append( value['name'] )

                self.valueControls[name]    = Frame(self.frameValueEntry, name='frame_' + name )
                labelValue                  = Label(self.valueControls[name], name='label_' + name, text=name )
                #   need to compute width based on actual content
                comboboxValue               = Combobox(self.valueControls[name], name='combobox_' + name, justify=LEFT,
                                                       width=6, height=10, values=values, state='readonly',
                                                       font=ParameterSettings.DEFAULT_FONT,
                                                       textvariable=self.valueStringVars[name])
                self.valueStringVars[name].set(values[0])
                self.valueStringVars[name].trace('w', self.comboBoxValueChanged)
                labelValue.grid(row=0, column=0, pady=2, padx=2)
                comboboxValue.grid(row=0, column=2, pady=2, padx=2)

            elif definition['value'] == 'FILE':
                self.valueControls[name]    = Frame(self.frameValueEntry, name='frame_' + name )
                labelFilePath      = Label(self.valueControls[name], name='label_value_' + name, justify=LEFT, text=name, width=len(name) + 2,
                                           relief=RIDGE)
                entryName          = Entry(self.valueControls[name], name='entry_' + name, justify=LEFT, width=30)
                buttonFileSelect   = Button(self.valueControls[name], name='button_' + name, text='FILE', width=4, command=self.buttonFileSelect)
                buttonFileSelect.bind('<Button-1>', self.buttonFileSelectClicked)
                labelFilePath.grid(row=0, column=0, pady=2, padx=2)
                entryName.grid(row=0, column=1, pady=2, padx=2)
                buttonFileSelect.grid(row=0, column=2, pady=2, padx=2)
            else:
                self.valueControls[name]    = Frame(self.frameValueEntry, name='frame_' + name)
                labelValue = Label(self.valueControls[name], name='label_' + name, text=name)
                entryValue = Entry(self.valueControls[name], name='entry_' + name, justify=LEFT, width=15)
                entryValue.insert(END, 'enter value')
                labelValue.grid(row=0, column=0)
                entryValue.grid(row=0, column=1)
            rowIndex += 1

    def buttonFileSelect(self):
        response = filedialog.askopenfilename(initialdir=os.curdir)
        if response != () and response != '':
            entry = self.valueControls[self.selectedParameterName].__dict__['children']['entry_' + self.selectedParameterName]
            entry.delete(0, END)
            entry.insert(END,response)

    def buttonFileSelectClicked(self, event):
        self.selectedParameterName = event.widget._name.split('_')[1]
        #print('self.selectedParameterName:\t' + self.selectedParameterName)

    def comboBoxValueChanged(self, arg1, arg2, arg3):
        print('comboBoxValueChanged')

    def parameterCheckbuttonChanged(self, arg1, arg2, arg3):
        #print('parameterCheckbuttonChanged:\t' + str(self.currentParametterName) + ":\t" +
        #      str(bool(self.parameterIntVars[self.currentParametterName].get())))
        if self.parameterIntVars[self.currentParametterName].get():
            self.entryShowCount += 1
            self.valueControls[self.currentParametterName].grid(row=self.entryShowCount+2, column=0, columnspan=3)
            self.selectedParameterName  = self.currentParametterName
        else:
            self.entryShowCount -= 1
            self.valueControls[self.currentParametterName].grid_forget()


    def getParameterIntVars(self):
        return self.parameterIntVars

    def getValueControls(self):
        return self.valueControls


    def mouseEnteredParameter(self, event):
        name = event.widget._name
        self.currentParametterName  = name
        message = ''
        if name != None and name in self.utilDescriptor and 'description' in self.utilDescriptor[name] and \
                ( isinstance(self.utilDescriptor[name]['description'], list) or isinstance(self.utilDescriptor[name]['description'], tuple)):
            for line in self.utilDescriptor[name]['description']:
                message += line + ' '
            self.messageDescription.config(text=message)

    def mouseLeftParameter(self, event):
        pass


class FlagSettings(LabelFrame):
    def __init__(self, container, name: str, utilDescriptor: dict, **keyWordArguments):
        if 'frameConfig' in keyWordArguments and isinstance(keyWordArguments['frameConfig'], dict):
            LabelFrame.__init__(self, container, name=name, **keyWordArguments['frameConfig'])
        else:
            LabelFrame.__init__(self, container, name=name)
        if utilDescriptor == None:
            raise Exception('FlagSettings constructor - utilDescriptor argument = None')
        self.utilDescriptor = utilDescriptor
        self.config(text="Flag Settings")
        self.flagCheckbuttons   = {}
        self.flagIntVars        = {}
        rowIndex = 0
        maxWidth = 1
        for name, definition in self.utilDescriptor.items():

            if 'verboseName' in definition:
                name = definition['verboseName']

            #print("FlagSettings name:\t" + name)
            if len(name) > maxWidth:
                maxWidth    = len(name)
            self.flagIntVars[name]  = IntVar()
            self.flagCheckbuttons[name] = Checkbutton(self, name=name, text=name, font=ParameterSettings.DEFAULT_FONT,
                                                    variable=self.flagIntVars[name], bg='darkgray', relief=FLAT,
                                                    anchor=W)
            self.flagIntVars[name].trace_variable('w', self.flagCheckbuttonChanged)
            self.flagCheckbuttons[name].bind('<Enter>', self.mouseEnteredFlag)
            self.flagCheckbuttons[name].bind('<Leave>', self.mouseLeftFlag)

            #   If a saved configuration is the subject of this dialog, it will be used here:
            self.flagIntVars[name].set(0)      #   default setting forr new configuration of utility.

            self.flagCheckbuttons[name].grid(row=rowIndex, column = 0, sticky=W)
            rowIndex += 1

        for name, checkbutton in self.flagCheckbuttons.items():
            checkbutton.config(width=maxWidth+3)

        self.messageDescription = Message(self, name="messageDescription", text="Messages", font=ConfigSettings.DEFAULT_FONT, width=350)
        self.messageDescription.grid(row=rowIndex+2, column=0, rowspan=12, padx=5, pady=5, sticky=W)

    def getflagIntVars(self):
        return self.flagIntVars

    def flagCheckbuttonChanged(self, arg1, arg2, arg3):
        #print('flagCheckbuttonChanged')
        pass

    def mouseEnteredFlag(self, event):
        #print('mouseEnteredFlag:\t' + event.widget._name)
        name = event.widget._name
        message = ''
        if name != None and name in self.utilDescriptor and 'description' in self.utilDescriptor[name] and \
                ( isinstance(self.utilDescriptor[name]['description'], list) or isinstance(self.utilDescriptor[name]['description'], tuple)):
            for line in self.utilDescriptor[name]['description']:
                message += line + ' '
            self.messageDescription.config(text=message)

    def mouseLeftFlag(self, event):
        #print('mouseLeftFlag:\t' + event.widget._name)
        self.messageDescription.config(text="Messages")


class SwitchSectionSettings(LabelFrame):

    def __init__(self, container, sectionName: ManSection, optionDefList: tuple, commandSettings: OrderedDict,
                 **keyWordArguments):
        LabelFrame.__init__(self, container, text=str(sectionName), **keyWordArguments)
        self.config(bg='darkgray')
        self.flagDescriptionMap     = {}
        maxDescrLen = 0
        for optionDef in optionDefList:
            if 'description' in optionDef and len(optionDef['description']) > maxDescrLen:
                maxDescrLen = len(optionDef['description'])
        lineCount = ceil( maxDescrLen / 33 )
        if lineCount > 5:
            lineCount = 5
        self.textDescription  = Text(self, name=str(sectionName).lower(), height=lineCount, width=35, state=DISABLED,
                                     wrap='word')
        row = 0
        self.textDescription.grid(row=row, column=0, columnspan=4, padx=15, pady=5, sticky='we')

        self.optionCheckBoxMap  = OrderedDict()
        self.optionSelectionMap  = OrderedDict()
        self.commandSettings = OrderedDict()
        row = 1
        for optionDef in optionDefList:
            optName = optionDef['text']
            self.optionSelectionMap[optName] = BooleanVar()
            self.commandSettings[optName] = {}
            self.commandSettings[optName]['includeVar'] = self.optionSelectionMap[optName]
            self.commandSettings[optName]['argument'] = None
            self.optionCheckBoxMap[optName] = Checkbutton(self, text=optName, anchor=W, bg='darkgray',
                                                          variable=self.optionSelectionMap[optName])
            if 'description' in optionDef:
                self.flagDescriptionMap[self.optionCheckBoxMap[optName]] = optionDef['description']
            else:
                self.flagDescriptionMap[self.optionCheckBoxMap[optName]] = "[None in Man Page]"
            self.optionCheckBoxMap[optName].bind('<Button-1>', self.optionClick)
            self.optionCheckBoxMap[optName].bind('<Enter>', self.checkBoxEnter)
            self.optionCheckBoxMap[optName].bind('<Leave>', self.checkBoxLeave)
            self.optionCheckBoxMap[optName].grid(row=row, column=0, columnspan=4, sticky=W)
            row += 1

    def optionClick(self, event):
        print("optionClick:\t" + str(event.widget))

    def checkBoxEnter(self, event):
        self.textDescription.config(state=NORMAL)
        self.textDescription.delete('1.0', END)
        self.textDescription.insert('1.0', self.flagDescriptionMap[event.widget])
        self.textDescription.config(state=DISABLED)
        event.widget.config(fg='blue')

    def checkBoxLeave(self, event):
        event.widget.config(fg='black')

    def getCommandSettings(self):
        return self.commandSettings


class ConfigSettings(LabelFrame):
    FONT_FAMILY     = "Arial"
    FONT_SIZE       = 10
    DEFAULT_FONT    = (FONT_FAMILY, FONT_SIZE)

    #   keyWordArguments can only be valid config settings for a LabelFrame
    def __init__(self, container, utilityName, definition: dict, configuration=None,  **keyWordArguments):
        #   print('ConfigSetings - constructor')
        if definition == None:
            raise Exception('ConfigSettings constructor - definition is None')
        elif not isinstance(definition, dict):
            raise Exception('ConfigSettings constructor - definition invdlid:  ' + str(definition))
        else:
            self.definition = definition
        self.utilityName = utilityName
        if 'frameConfig' in keyWordArguments and isinstance(keyWordArguments['frameConfig'], dict):
            LabelFrame.__init__(self, container, name=self.utilityName, **keyWordArguments['frameConfig'])
        else:
            LabelFrame.__init__(self, container, name=self.utilityName)
        if "topLevel" in keyWordArguments:
            self.container  = keyWordArguments["topLevel"]
        else:
            self.container  = container

        self.toolManagerToplevel = None
        self.toolManager = None
        self.confirmCommandLine = None

        self.commandSettings = OrderedDict()

        self.configUtilMenu = {"type": "menu",
                                        'tearoff': True,
                                        "items": {
                                            'Edit Selections': {
                                                "type": 'checkbutton',
                                                "label": 'Edit Selections',
                                                "onvalue": True,
                                                "offvalue": False,
                                                "variable": BooleanVar(),
                                                "call": lambda: self.menuItemHandler(featureName="Edit Selections")
                                            },
                                            'Show Selection Details': {
                                                "type": 'checkbutton',
                                                "label": 'Show Selection Details',
                                                "onvalue": True,
                                                "offvalue": False,
                                                "variable": BooleanVar(),
                                                "call": lambda: self.menuItemHandler(featureName="Show Selection Details")
                                            }
                                        }
                               }
        toolManagerVar = BooleanVar()
        commandLineViewVar = BooleanVar()

        self.toolsMenu  = {     "type": "menu",
                                'tearoff': True,
                                'items': {
                                    'Save Tool': {'type': 'item', "call": lambda: self.menuItemHandler(
                                        featureName="Save Tool")
                                    },
                                    'Select Tool': {'type': 'item', "call": lambda: self.menuItemHandler(
                                        featureName="Select Tool")
                                    },
                                    'Run in Console': {'type': 'item', "call": lambda: self.menuItemHandler(
                                        featureName="Run in Console")
                                    },
                                    'Run in Terminal': {'type': 'item', "call": lambda: self.menuItemHandler(
                                        featureName="Run in Terminal")
                                    },
                                    'Tool Manager': {
                                        "type": 'item',
                                        "call": lambda: self.menuItemHandler(featureName="Tool Manager")
                                    },

                                    #   'Pipe': {'type': 'item', "call": lambda: self.menuItemHandler(featureName="Pipe",
                                    #                                                              variable=None) },
                                    #   'Batch': {"type": 'item', "call": lambda: self.menuItemHandler(featureName="Batch") },
                                    #   'Edit': {"type": 'item', "call": lambda: self.menuItemHandler(featureName="Edit") },
                                    #   'Run': {"type": "item", "call": self.runCurrentConfiguration}
                                }
                            }
        showDescriptionVar = BooleanVar()
        self.utilitiesMenu  = { "type": "menu",
                                'tearoff': True,
                                "items": {
                                    'Configure': {'type': 'item', "call": lambda: self.menuItemHandler(featureName="Configure")
                                                  },
                                    'Import': {"type": 'item', "call": lambda: self.menuItemHandler(featureName="Import")
                                               },
                                    'Script': {"type": 'item', "call": lambda: self.menuItemHandler(featureName="Script")
                                               },
                                    'Show Description': {
                                        "type": 'checkbutton',
                                        "label": 'Show Selection Description',
                                        "onvalue": True,
                                        "offvalue": False,
                                        "variable": showDescriptionVar,
                                        "call": lambda: self.menuItemHandler(
                                            featureName="Show Description",
                                            variable=showDescriptionVar
                                        )
                                    }
                                }
                            }
        self.logsMenu   = { 'type': "menu",
                            'tearoff': True,
                            'items': {
                                'View Activities': {'type': 'item', "call": lambda: self.menuItemHandler(
                                        featureName="View Activities")
                                    },
                                'View Tool Use': {"type": 'item', "call": lambda: self.menuItemHandler(
                                        featureName="View Tool Use")
                                    },
                            }
                        }
        self.fileMenu   = { 'type': "menu",
                            'tearoff': True,
                            'items':    {
                                'Read Configuration': {'type': "item", 'call': lambda: self.menuItemHandler(
                                        featureName="Read Configuration")},
                                'Write Configuration': { 'type': "item", "call": lambda: self.menuItemHandler(
                                        featureName="Write Configuration")}
                                }
                            }
        #   self.menuBarDesign   = {'File': self.fileMenu, 'Utilities': self.utilitiesMenu, 'Tools':    self.toolsMenu, 'Logs': self.logsMenu,
        self.menuBarDesign   = {'Tools':    self.toolsMenu,
                                'Logs': self.logsMenu,

                           }
        self.configure(cursor=Cursors.Arrow)

        self.intVarOne          = IntVar()
        self.intVarTwo          = IntVar()
        self.intVarThree        = IntVar()
        self.configUtilMenu['items']['Edit Selections']['variable']             = self.intVarOne
        self.configUtilMenu['items']['Show Selection Details']['variable']      = self.intVarTwo
        self.utilitiesMenu["items"]['Show Description']['variable']             = self.intVarThree
        self.intVarThree.trace('w', self.intVarThreeChanged)


        #   Menu bar
        menuBar = ProgrammablePopup(container, 'ParameterSettings.menubar', self.menuBarDesign, tearoff=0)
        #   menuBar = ProgrammablePopup(container, 'menubar', self.menuBarDesign, tearoff=0)

        self.container.config(menu=menuBar)
        self.parameterDefs  = None
        #   print(self.definition)

        self.optionsList = None
        self.switchesList = None
        self.commandsList = None
        self.diagnosticsList = None
        self.descriptionsList = None
        self.isRoffParsed = False
        self.roffOptionMap = OrderedDict()
        if ManSection.Synopsis in self.definition and isinstance(self.definition[ManSection.Synopsis], tuple):
            self.roffOptionMap[ManSection.Synopsis] = self.definition[ManSection.Synopsis]
            self.synopsisText = '\n'.join(self.roffOptionMap[ManSection.Synopsis])
        if ManSection.Options in self.definition and isinstance(self.definition[ManSection.Options], tuple):
            self.roffOptionMap[ManSection.Options]    = self.optionsList = self.definition[ManSection.Options]
            self.isRoffParsed = True
        if ManSection.Switches in self.definition and isinstance(self.definition[ManSection.Switches], tuple):
            self.roffOptionMap[ManSection.Switches]    = self.switchesList   = self.definition[ManSection.Switches]
            self.isRoffParsed = True
        if ManSection.Commands in self.definition and isinstance(self.definition[ManSection.Commands], tuple):
            self.roffOptionMap[ManSection.Commands]    = self.commandsList   = self.definition[ManSection.Commands]
            self.isRoffParsed = True
        if ManSection.Diagnostics in self.definition and isinstance(self.definition[ManSection.Diagnostics], tuple):
            self.roffOptionMap[ManSection.Diagnostics]    = self.diagnosticsList   = self.definition[ManSection.Diagnostics]
            self.isRoffParsed = True
        if ManSection.Description in self.definition and isinstance(self.definition[ManSection.Description], tuple):
            self.roffOptionMap[ManSection.Description]    = self.descriptionsList   = self.definition[ManSection.Description]
            self.isRoffParsed = True

        if "DESCRIPTION" in definition:
            if isinstance( self.definition["DESCRIPTION"], list) or isinstance( self.definition["DESCRIPTION"], tuple):
                if isinstance(self.definition["OPTIONS"], dict):
                    self.parameterDefs = self.definition["OPTIONS"]
                else:
                    raise Exception("ConfigSetings constructor - no parameter definitions in utility definition")
            elif isinstance( self.definition["DESCRIPTION"], dict):
                self.parameterDefs = self.definition["DESCRIPTION"]
            else:
                raise Exception("ConfigSetings constructor - no parameter definitions in utility definition")
            #   Separate flags from settable parameters:
            #   whether an option is a flag depends on whether it has a value setting in addition to presence or absence
            #   in the command line.

        if self.isRoffParsed:
            self.layoutRoffParse(self.roffOptionMap)
        else:
            self.layoutPageParse(self.parameterDefs)
        self.setConfiguration(configuration)

    def layoutPageParse(self, parameterDefs):
        #   The fields in a parameter definition are: primaryName, verboseName, description, value, valueOptional,
        #       if value is not present, the parameter is a flag.
        #       All will have primaryName, verboseName and description.
        #       if verboseName and primaryName are the same, only one needs to be shown as primaryName
        #       value can be the identifier of an enum.  enums will be listed in a parameter definition slot named
        #       Configuration.ENUM_VALUES_NAME, which is a dict keyed on the value string.
        #
        self.flagParameters     = {}
        self.valueParameters    = {}
        self.enums              = {}
        for name, descriptor in parameterDefs.items():
            if name != Configuration.ENUM_VALUES_NAME:
                if 'value' in descriptor:
                    self.valueParameters[name]  = descriptor
                else:
                    self.flagParameters[name]  = descriptor
            else:       #   this is the secion that defines all of the enums listed as value possibilities for the various parameters
                self.enums = descriptor
                for name, enumDescriptor in self.enums.items():
                    maxWidth = 1
                    for value in enumDescriptor['values']:
                        if len(value['name']) > maxWidth:
                            maxWidth    = len(value['name'])
                    enumDescriptor['maxWidth']  = maxWidth

        self.frameFlagSettings       = FlagSettings(self, "frameFlagSettings", self.flagParameters,
                                                    frameConfig={'relief': GROOVE, 'borderwidth': 2,
                                                                 'fg': 'blue', 'bg': 'darkgray'})
        self.frameParameterSettings   = ParameterSettings(self, "frameParameterSettings", self.valueParameters,
                                                          self.enums, frameConfig={'relief': GROOVE, 'borderwidth': 2,
                                                                                  'fg': 'blue', 'bg': 'darkgray'})


        frameHeader     = Frame(self, name="frameHeader", relief=RAISED)

        labelUtilityLabel = Label(frameHeader, name="labelUtilityLabel", text='Utility Name: ',
                                  font=(ConfigSettings.FONT_FAMILY, ConfigSettings.FONT_SIZE), relief=FLAT)
        labelUtilityName = Label(frameHeader, name="labelUtilityName", text=self.utilityName,
                                 font=(ConfigSettings.FONT_FAMILY, ConfigSettings.FONT_SIZE), relief=FLAT)

        if "SYNOPSIS" in self.definition:
            self.synopsisText = self.definition['SYNOPSIS']
        else:
            self.synopsisText = "Not Available"
        #   Remove leading, trailing, and embedded blank lines
        inText = False
        synopsisLines = []
        sLines = self.synopsisText.split('\n')
        synopsisWidth = 40
        for line in sLines:
            if len(line.strip()) > 0:
                if not inText:
                    inText = True
                    synopsisLines.append(line)
                else:
                    if len(line.strip()) > 0:
                        synopsisLines.append(line)
                    else:
                        inText = False
                if inText:
                    if len(line) + 2 > synopsisWidth:
                        synopsisWidth = len(line) + 2
        self.synopsisText = '\n'.join(synopsisLines)
        self.synopsisShown = BooleanVar()
        self.synopsisShown.set(True)
        checkboxShowSynopsis    = Checkbutton(frameHeader, text="Show Synopsis", variable=self.synopsisShown,
                                              border=3, relief=RIDGE)
        self.synopsisShown.trace_add("write", self.synopsisToggle)

        self.frameSynopsis = LabelFrame(self, text="Synopsis", name="frameSynopsis", relief=RAISED, width=400)
        self.labelSynopsis = Label(self.frameSynopsis, text=self.synopsisText, relief=SUNKEN, width=synopsisWidth,
                                   height=len(synopsisLines))
        self.labelSynopsis.pack(expand=True, fill=BOTH, padx=10, pady=5)

        self.frameSynopsis.grid(row=2, column=0, columnspan=2, padx=15, pady=5)

        labelUtilityLabel.grid(row=0, column=0, sticky=W, padx=15, pady=5)
        labelUtilityName.grid(row=0, column=1, sticky=E, padx=15, pady=5)
        checkboxShowSynopsis.grid(row=0, column=2, sticky=E, padx=15, pady=5)
        frameHeader.grid(row=0, column=0, columnspan=2, sticky=E+W)

        self.frameFlagSettings.grid(row=3, column=0, columnspan=2, sticky=W, padx=15, pady=5)
        self.frameFlagSettings.grid_columnconfigure(0, weight=1)
        self.frameParameterSettings.grid(row=4, column=0, columnspan=2, sticky=W, padx=15, pady=5)

        self.frameSave  = ConfigSettings.SaveFrame(self, "frameSave")
        self.frameSave.grid(row=1, column=0, columnspan=1)

    def messageReceiver(self, message):
        #   {'source': "ConfirmCommandLine", 'action': 'cancelSaveTool'}
        if 'source' in message:
            if message['source'] == "ConfirmCommandLine":
                if 'action' in message:
                    if message['action'] == 'cancelSaveTool':
                        self.exitCommandConfirm()

    def layoutRoffParse(self, roffOptionMap: OrderedDict):
        self.switchSectionFrames = OrderedDict()
        row = 0
        for sectionId, optionDefs in roffOptionMap.items():
            if sectionId == ManSection.Synopsis:
                continue
            self.switchSectionFrames[sectionId] = SwitchSectionSettings(self, sectionId, optionDefs, self.commandSettings,
                                                                        border=4, relief=GROOVE)
            self.switchSectionFrames[sectionId].grid(row=row, column=0, padx=15, pady=5)
            row += 1

    def synopsisToggle(self, *args):
        print("synopsisToggle:\t" + str(self.synopsisShown.get()))
        if self.synopsisShown.get():
            self.frameSynopsis.grid(row=2, column=0, columnspan=2, padx=15, pady=5)
        else:
            self.frameSynopsis.grid_forget()


    def menuItemHandler(self, featureName=None, variable=None):
        if featureName == 'Tool Manager':
            if self.toolManagerToplevel == None:
                self.toolManagerToplevel = Toplevel(self)
                self.toolManagerToplevel.title("Tool Manager")
                self.toolManagerToplevel.geometry("700x500+600+200")
                self.toolManagerToplevel.protocol('WM_DELETE_WINDOW', self.exitToolManager)
            self.toolManager = ToolManagerTabs(self.toolManagerToplevel, border=5, relief=RAISED)
            self.toolManager.pack(expand=True, fill=BOTH)
            self.toolManagerToplevel.mainloop()
        elif featureName == "Save Tool":
            optionsSelected = []
            for sectionId, optionDefs in self.roffOptionMap.items():
                if sectionId == ManSection.Synopsis:
                    continue
                commandSettings = self.switchSectionFrames[sectionId].getCommandSettings()
                for optionName, optionSetting in commandSettings.items():
                    if optionSetting['includeVar'].get():
                        optionSetting['text'] = optionName
                        optionsSelected.append(optionSetting)
            optionsSelected = tuple(optionsSelected)

            if self.confirmCommandLine is None:
                self.confirmCommandLine = ConfirmCommandLine(self, self.utilityName, optionsSelected,
                                                             _title="Command Settings", synopsis=self.synopsisText,
                                                             listener=self.messageReceiver)
                self.confirmCommandLine.protocol('WM_DELETE_WINDOW', self.exitCommandConfirm)
            else:
                self.confirmCommandLine.setModel(optionsSelected)
            self.confirmCommandLine.mainloop()
        else:
            messagebox.showinfo(str(featureName), "Not Implemented Yet")

    def exitCommandConfirm(self):
        self.confirmCommandLine.destroy()
        self.confirmCommandLine = None

    def exitToolManager(self):
        self.toolManagerToplevel.destroy()
        self.toolManagerToplevel = None
        self.toolManager = None

    def intVarThreeChanged(self, arg1, arg2, arg3):
        print('intVarThreeChanged')

    def runCurrentConfiguration(self):
        "Starting with flags only.  Initial population of parameters not done yet."
        print("runCurrentConfiguration")

        toolName   = self.utilityName
        flagIntVarMap = self.frameFlagSettings.getflagIntVars()
        for name, definition in self.flagParameters.items():
            #print('flagParameter: ' + name + ":\t" + str(definition) )
            if flagIntVarMap[name].get():
                #print("Flag Selected:\t" + name)
                toolName += ' ' + name

        parameterIntVars    = self.frameParameterSettings.getParameterIntVars()
        valueControls       = self.frameParameterSettings.getValueControls()
        for name, included in parameterIntVars.items():
            if included.get():
                #print( 'valueControls[name]:\t' + str(valueControls[name].__dict__['_name']))
                frameNameParts = valueControls[name].__dict__['_name'].split('_')
                #   Frames will be recorded, and there will be either an entry or a combobox in the frame
                #print("children:\t" + str( valueControls[name].__dict__['children'] ))
                if 'entry_' + frameNameParts[1] in valueControls[name].__dict__['children']:    #   input widget is an Entry
                    #print('Input Control:\t' + 'entry_' + frameNameParts[1])
                    entry = valueControls[name].__dict__['children']['entry_' + frameNameParts[1]]
                    #print("Value:\t" + entry.get() )
                    toolName += ' ' + name + ' ' + entry.get()
                elif 'combobox_' + frameNameParts[1] in valueControls[name].__dict__['children']:    #   input widget is a Combobox
                    print('Input Control:\t' + 'combobox_' + frameNameParts[1])
#                controlNameParts =

        #   print("tool name:\t" + toolName)
        outputView    = Toplevel(self)
        outputView.geometry("500x600+100+100")
        toolOutput = ToolOutput(outputView, self.utilityName, frameConfig={'text': ' Tool Output: ' + self.utilityName + " ",
                                 'padx': 10, 'pady': 10, 'relief': SUNKEN, 'borderwidth': 4}, commandText=toolName)
        toolOutput.pack(expand=True)
        outputView.deiconify()



    def setConfiguration(self, configuration):
        #   print('setConfiguration:\t' + str(configuration))
        self.configuration  = configuration
        if self.configuration != None:
            if 'name' in self.configuration:
                #print('Confiiguration Name:\t' +  self.configuration['name'])
                self.frameSave.entryName.delete(0, END)
                self.frameSave.entryName.insert(END, self.configuration['name'])

            if  'flags' in self.configuration:
                for name in self.configuration['flags']:
                    if name in self.frameFlagSettings.flagIntVars:
                        self.frameFlagSettings.flagIntVars[name].set(True)
                    else:
                        print('ERROR:')
                        print( '\tflag name not in intvar map:\t' + name)
                        print("\tself.configuration['flags']" + str(self.configuration['flags']))
                        print("\tself.frameFlagSettings.flagIntVars" + str(self.frameFlagSettings.flagIntVars))

            if 'parameters' in self.configuration:
                for parameter in self.configuration['parameters']:
                    print('Setting view for parameter:\t' + str(parameter))
        else:
            pass    #   clear all settings


    class SaveFrame(LabelFrame):
        def __init__(self, container, name, **keyWordArguments):
            if 'frameConfig' in keyWordArguments and isinstance(keyWordArguments['frameConfig'], dict):
                LabelFrame.__init__(self, container, name=name, **keyWordArguments['frameConfig'])
            else:
                LabelFrame.__init__(self, container, name=name)
            self.labelName       = Label(self, name='label_save', text="Name: ", width=8, anchor=W)
            self.entryName       = Entry(self, name='entry_save', width=15 )
            self.buttonSave      = Button(self, name='button_save', text="Save", anchor=E, command=self.saveNamedConfig)
            self.labelName.grid(row=0, column=0, padx=2)
            self.entryName.grid(row=0, column=1, padx=2)
            self.buttonSave.grid(row=0, column=2, padx=2)

        def saveNamedConfig(self):
            print('saveNamedConfig:\t' + self.entryName.get())
            self.validateName(99)
            if self.validateName(self.entryName.get()):
                print('Name Validated')
            else:
                print('Name ERROR')


        def validateName(self, name: str):
            if name == None or not isinstance(name, str) or name == "":
                return False
            otherChars  = ' _-:;,.[]{}()?'
            valid = True
            if name[0] in string.ascii_letters:
                index = 1
                while valid and index < len(name):
                    if name[index] in string.ascii_letters or name[index] in string.digits or name[index] in otherChars:
                        index += 1
                    else:
                        valid = False
            else:
                valid = False
            return valid


if __name__ == "__main__":

    mainView    = Tk()
    mainView.geometry("400x600+800+50")
    #   2021-08-21: new installation for different user:
    #   utilityDefinitions  = ManPageScanner(str(Path('/home/keith/PycharmProjects/VolumeIndexer/service/linux/manPages/').absolute())).getUtilityDefinitions()
    utilityDefinitions  = ManPageScanner(str(Path('/home/keithcollins/PycharmProjects/VolumeIndexer/service/linux/manPages/').absolute())).getUtilityDefinitions()

    #   working with hand supplemented dd json for initial development and testing
    dd_suplDocs     = utilityDefinitions['dd_supl']
    lsDocs          = utilityDefinitions['ls']

    for key, value in dd_suplDocs.items():
        print( "Section:\t" + key + "\tcontent:\t" + str(value) )

    frameScroller   = FrameScroller(mainView, "frameScroller")
    configSetings   = ConfigSettings(frameScroller.getScrollerFrame(), 'ls', lsDocs, None, frameConfig={'relief': RIDGE,
                                     'borderwidth': 3, 'fg': 'blue', 'bg': 'darkgray'}, topLevel=mainView)
    frameScroller.pack(fill=BOTH, expand=True)
    configSetings.pack(expand=True, anchor=N+W)

    mainView.mainloop()

