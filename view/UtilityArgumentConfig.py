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

from tkinter import Tk, Label, Entry, Button, Text, Frame, LabelFrame, filedialog, messagebox, Checkbutton, Menu, \
                    Toplevel, Message, Listbox, \
                    StringVar, IntVar, \
                    INSERT, END, N, S, E, W, LEFT, CENTER, RIGHT, BOTH, \
                    SUNKEN, FLAT, RAISED, GROOVE, RIDGE         #   values for relief parameter
from tkinter.ttk import Combobox
#  import idlelib
from tkinter.messagebox import ABORT, RETRY, IGNORE, OK, CANCEL, YES, NO, ERROR, INFO, QUESTION, WARNING
import os, sys, string
from pathlib import Path

from service.linux.Utilities import ManPageScanner
from model.UtilConfig import Configuration
from view.ProgrammableMenu import ProgrammablePopup
from view.ToolOutput import ToolOutput
from view.FrameScroller import FrameScroller


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
        self.config(text="Parametter Settings")

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


class ConfigSettings(LabelFrame):
    FONT_FAMILY     = "Arial"
    FONT_SIZE       = 10
    DEFAULT_FONT    = (FONT_FAMILY, FONT_SIZE)

    #   keyWordArguments can only be valid config settings for a LabelFrame
    def __init__(self, container, utilityName, definition: dict, configuration,  **keyWordArguments):
        #   print('ConfigSetings - constructor')
        if definition == None:
            raise Exception('ConfigSettings constructor - definition is None')
        else:
            self.definition = definition
        if 'frameConfig' in keyWordArguments and isinstance(keyWordArguments['frameConfig'], dict):
            LabelFrame.__init__(self, container, name=utilityName, **keyWordArguments['frameConfig'])
        else:
            LabelFrame.__init__(self, container, name=utilityName)
        if "topLevel" in keyWordArguments:
            self.container  = keyWordArguments["topLevel"]
        else:
            self.container  = container

        self.configUtilMenu = {"type": "menu",
                                        'tearoff': True,
                                        "items": {
                                            'Edit Selections': {
                                                "type": 'checkbutton',
                                                "label": 'Edit Selections',
                                                "onvalue": True,
                                                "offvalue": False
                                            },
                                            'Show Selection Details': {
                                                "type": 'checkbutton',
                                                "label": 'Show Selection Details',
                                                "onvalue": True,
                                                "offvalue": False
                                            }
                                        }
                               }
        self.toolsMenu  = {     "type": "menu",
                                'tearoff': True,
                                'items': {
                                    'Pipe': {'type': 'item', "call": self.menuItemHandler},
                                    'Batch': {"type": 'item', "call": self.menuItemHandler},
                                    'Edit': {"type": 'item', "call": self.menuItemHandler},
                                    'Run': {"type": "item", "call": self.runCurrentConfiguration}
                                }
                            }
        self.utilitiesMenu  = { "type": "menu",
                                'tearoff': True,
                                "items": {
                                    'Configure': {'type': 'item', "call": self.menuItemHandler},
                                    'Import': {"type": 'item', "call": self.menuItemHandler},
                                    'Script': {"type": 'item', "call": self.menuItemHandler},
                                    'Show Description': {
                                        "type": 'checkbutton',
                                        "label": 'Show Selection Description',
                                        "onvalue": True,
                                        "offvalue": False
                                    }
                                }
                            }
        self.logsMenu   = { 'type': "menu",
                            'tearoff': True,
                            'items': {
                                'View Activities': {'type': 'item', "call": self.menuItemHandler},
                                'View Tool Use': {"type": 'item', "call": self.menuItemHandler},
                            }
                        }
        self.fileMenu   = { 'type': "menu",
                            'tearoff': True,
                            'items':    {
                                'Read Configuration': {'type': "item", 'call': self.menuItemHandler},
                                'Write Configuration': { 'type': "item", "call": self.menuItemHandler}
                                }
                            }
        self.menuBarDesign   = {'File': self.fileMenu,
                                'Utilities': self.utilitiesMenu,
                                'Tools':    self.toolsMenu,
                                'Logs': self.logsMenu
                           }

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

        #   if  definition["DESCRIPTION"] is a list of strings, then it is text, each string being a line,
        #       and definition["OPTIONS"] has the parameter definitions
        #   if definition["DESCRIPTION"] is a dict, then its keys are the parameter names and its values are a formatted
        #       dict with particular fields defining the parameter
        #   The fields in a parameter definition are: primaryName, verboseName, description, value, valueOptional,
        #       if value is not present, the parameter is a flag.
        #       All will have primaryName, verboseName and description.
        #       if verboseName and primaryName are the same, olny one needs to be shown as primaryName
        #       value can be the identifier of an enum.  enums will be listed in a parameter definition slot named
        #       Configuration.ENUM_VALUES_NAME, which is a dict keyed on the value string.
        #

        self.parameterDefs  = None
        #   print(self.definition)
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
        self.commandName        = self.definition['NAME']['name']
        self.flagParameters     = {}
        self.valueParameters    = {}
        self.enums              = {}
        for name, descriptor in self.parameterDefs.items():
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

        labelUtilityLabel = Label(frameHeader, name="labelUtilityLabel", text='Utility Name: ', font=(ConfigSettings.FONT_FAMILY, ConfigSettings.FONT_SIZE),
                                  relief=FLAT)
        labelUtilityName = Label(frameHeader, name="labelUtilityName", text=utilityName, font=(ConfigSettings.FONT_FAMILY, ConfigSettings.FONT_SIZE),
                                 relief=FLAT)

        labelUtilityLabel.grid(row=0, column=0, sticky=W, padx=15, pady=5)
        labelUtilityName.grid(row=0, column=1, sticky=E, padx=15, pady=5)
        frameHeader.grid(row=0, column=0, columnspan=2, sticky=E+W)

        self.frameFlagSettings.grid(row=2, column=0, columnspan=2, sticky=W, padx=15, pady=5)
        self.frameFlagSettings.grid_columnconfigure(0, weight=1)
        self.frameParameterSettings.grid(row=3, column=0, columnspan=2, sticky=W, padx=15, pady=5)

        self.frameSave  = ConfigSettings.SaveFrame(self, "frameSave")
        self.frameSave.grid(row=1, column=0, columnspan=1)

        self.setConfiguration(configuration)


    def menuItemHandler(self):
        print("menuItemHandler")

    def intVarThreeChanged(self, arg1, arg2, arg3):
        print('intVarThreeChanged')

    def runCurrentConfiguration(self):
        "Starting with flags only.  Initial population of parameters not done yet."
        print("runCurrentConfiguration")

        toolName   = self.commandName
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
        toolOutput = ToolOutput(outputView, self.commandName, frameConfig={'text': ' Tool Output: ' + self.commandName + " ",
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
    mainView.geometry("400x600+400+50")
    #   2021-08-21: new installation for different user:
    #   utilityDefinitions  = ManPageScanner(str(Path('/home/keith/PycharmProjects/VolumeIndexer/service/linux/manPages/').absolute())).getUtilityDefinitions()
    utilityDefinitions  = ManPageScanner(str(Path('/home/keithcollins/PycharmProjects/VolumeIndexer/service/linux/manPages/').absolute())).getUtilityDefinitions()

    #   working with hand supplemented dd json for initial development and testing
    dd_suplDocs     = utilityDefinitions['dd_supl']
    lsDocs          = utilityDefinitions['ls']

    #for key, value in dd_suplDocs.items():
    #    print( "Section:\t" + key + "\tcontent:\t" + str(value) )

    frameScroller   = FrameScroller(mainView, "frameScroller")
    configSetings   = ConfigSettings(frameScroller.getScrollerFrame(), 'ls', lsDocs, None, frameConfig={'relief': RIDGE,
                                     'borderwidth': 3, 'fg': 'blue', 'bg': 'darkgray'}, topLevel=mainView)
    frameScroller.pack(fill=BOTH, expand=True)
    configSetings.pack(expand=True, anchor=N+W)

    mainView.mainloop()

