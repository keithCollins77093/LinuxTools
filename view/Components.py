#   Project:        LinuxTools
#   Date Imported:  April 6, 2022
#   Imported from:  Linux Log Reader
#   Date Started:   July 14, 2021
#   Author:         George Keith Watson
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/Components.py
#   Purpose:        Custom and composite GUI components not supplied in tkinter or tkJsonTreeViewFrameinter.ttk.
#   Development:
#       2021-07-15:
#           There will be two different styles of toolbar, one using tkinter controls only and one using tkinter.ttk
#           controls only.  The first obvious reason is the difference in how configuration parameters are handled
#           syntactically.  The difference creates structural differences in the descriptor json for each making a
#           structure handling both possible but irregular.  A factor prohibiting uniform and flexible styling when
#           they are combined is that ttk widgets have the native look and feel of the platform on which the program
#           runs, whereas tkinter widgets have the tkinter look and feel.  Another good reason is that programmatic
#           control of styling by the user while the program is running is very different for each, requiring for
#           clarity of the code as well as consistency of the user interface for all components of a tool bar
#           that they be kept separate.
#
#           Composite tools required:
#               tkinter.Scale with current value displayed to side rather than under title.
#               Drop down date / calendar - frame positioned directly below activation tool.
#               Drop down (pop-up) listbox and radio button set frames.
#               Any other desirable drop down or pop up complex controls.
#               Type specific tkinter Entry controls with interactive parsing, like email addresses, phone numbers,
#                   dates, or any custom DFA driven state-event interactive filtering.  (even a grep grammer could
#                   be filterable with this.)  Grammar driven interactive parser.
#
#           Design of tools / components:
#               A property sheet will be the gui component for setting the configuration of a component.
#               Configurations for components will be savable and can include any subset of settings, including
#                   ones common to multiple or all components.
#               Sets of configurations for component sets will also be savable as styles.
#
#       2021-08-02:
#           FilterPanel, usable for any type of filtering, from unformatted text streams to short message strings
#           to lines of text to columns of a database table.  Data in this application will frequently be
#           initially structured as lines of text, in particular all of the linux command output that I can
#           think of is.  The type determines the layout.  A database table filter will need to have a column
#           selector listing the names of the columns, along with a filter settings structure and a results structure
#           that stores separate filter settings for each column along with the results for each in the form
#           of a sequence of row indexes.  For lines of text, only a single filter settings instance will be
#           needed.  The results object of the text lines filter setting structure will need to record the
#           line number, column number, and length of each segment of text that passes the filter.  For text,
#           only a single filter settings instance will be needed, however the manner in which the filter is
#           implemented in a GUI layout is variable.  For long text streams, it will be necessary to record
#           all of the locations and lengths of each match so that a GUI component displaying the results can
#           find them.
#           In a table, field types become an issue.  If th field is numeric, then range filters and multiple
#           range filters can be used.  Whether to allow functions for filtering is another consideration.
#           The general form would be where f(x) meets particular constraints, such as equals a value, falls
#           into a range, is in an enumerated set, etc.
#
#       2021-08-04:
#           class FilterTypeSelectionPanel(LabelFrame):
#               Numeric Filter radio button options: High Value, Low Value, Value Range, Equals, Equals with Radius
#               Add button will add to numeric filters for the selected column.
#               User can specify as many as they like.
#               User should also be able to save filters for each type and simultaneous filter sets for a table.
#               The various filters for the various columns should be available to assembly into new table filters.
#               Unique naming by the user is required, as well as a txt a syntax for the filter itself.
#
#       2021-08-10:
#           Useful Filter Button Names:   Commit, Run, Filter, OK, Cancel, Save, Select
#               buttons = {"Commit": lambda: buttonHandler("Commit"),
#                          "Run": lambda: buttonHandler("Run"),
#                          "Filter": lambda: buttonHandler("Filter"),
#                          "OK": lambda: buttonHandler("OK"),
#                          "Cancel": lambda: buttonHandler("Cancel"),
#                          "Save": lambda: buttonHandler("Save"),
#                          "Select": lambda: buttonHandler("Select")}
#
#           Binary Data Searching and UTF-16 characters:
#           Need ability to search for text with ANY unicode-8 or unicode-16 characters in it.
#           A hexadecimal string representing a byte sequence would work.
#
#       2021-08-11:
#           Need a popup meny that appears anywhere and shows the help dialog option along with context dependent
#           optiono.
#           The general help dialog will display help in a searchable tkinter.Text component and will have a list
#           of topics which the use can select from, each of which has its own text to display in the Text.
#           This will be in a tkinter.Toplevel so that the user can switch to it at any time, and which will
#           toggle with the same help menu item selection.
#           The help dialog should market the product by showing the user how it is used, what it can be used for,
#           the value of its features, and any caveats respecting where it is going to break depending on platform
#           idiosyncracies.  See the first page of "man ps" for for a good example of this.  The built in tools
#           will not work correctly on some versions of posix.  They should be guaranteed to work on any debian
#           installation, however, since debian is the best choice for security and general usability.
#


from copy import deepcopy
import datetime
from collections import OrderedDict
import logging, sys, re
from functools import partial
from enum import Enum

from tkinter import Tk, Toplevel, Label, Frame, LabelFrame, Button, Checkbutton, Radiobutton, Menubutton, Listbox, \
                    Entry, Scrollbar, Text, \
                    OptionMenu, Scale, Menu, Spinbox, \
                    IntVar, StringVar, BooleanVar, DoubleVar, \
                    messagebox, filedialog, \
                    NORMAL, RAISED, SUNKEN, GROOVE, RIDGE, FLAT, EW, N, LEFT, CENTER, RIGHT, W, E, CENTER, \
                    HORIZONTAL, VERTICAL, END, TOP, BOTTOM, LEFT, RIGHT, X, Y, BOTH, \
                    SINGLE, EXTENDED, MULTIPLE, BROWSE, YES, NO, DISABLED

from tkinter.ttk    import Treeview, Style

from service.Messaging import Message
from model.Util import INSTALLATION_FOLDER, LOGGING_FOLDER, Cursors
import textwrap


PROGRAM_TITLE = "Components Designer Demo"


class ListAndDetails(LabelFrame):
    """
    List of items on the left with a panel showing the details of each item when it is selected on the
    right.  The details panel is a JsonTreeView showing the dict that holds the item details.
    """

    def __init__(self, container, items: OrderedDict, viewConfig: dict,  **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)
        self.items = deepcopy(items)
        self.viewConfig = deepcopy(viewConfig)
        self.listItemNames = tuple(items.keys())
        self.listBox    = Listbox(self, border=2, relief=GROOVE, selectmode=SINGLE, height=viewConfig['height'])
        self.listBox.insert(END, *self.listItemNames)
        self.listBox.bind('<<ListboxSelect>>', self.listItemSelected)
        self.listBox.bind('<Button-3>', self.listItemRightClick)
        self.listBox.bind('<Double-Button-1>', self.listItemDoubleClick)
        self.listBox.bind('<Key>', self.listItemEvent)
        self.listBox.bind('<Enter>', self.listItemEvent)
        self.listBox.bind('<Leave>', self.listItemEvent)
        self.listBox.bind('<FocusIn>', self.listItemEvent)
        self.listBox.bind('<FocusOut>', self.listItemEvent)
        if len(self.listItemNames) > 0:
            self.listBox.selection_set(0, 0)

        self.detailsTree = JsonTreeView(self, self.items, {"openBranches": True, "mode": JsonTreeView.MODE_STRICT,
                                                            'listener': self.messageReceiver})

        self.listBox.grid(row=0, column=0, padx=10, pady=10, sticky='wn')
        self.detailsTree.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

    def listItemSelected(self, event):
        idx = self.listBox.curselection()
        print("ListAndDetails.listItemSelected:\t" + self.listBox.get(idx))

    def listItemRightClick(self, event):
        print("ListAndDetails.listItemRightClick:\t" + str(event))

    def listItemDoubleClick(self, event):
        print("ListAndDetails.listItemDoubleClick:\t" + str(event))

    def listItemEvent(self, event):
        print("ListAndDetails.listItemEvent:\t" + str(event))

    def messageReceiver(self, message: dict):
        print("ListAndDetails.messageReceiver")
        if isinstance(message, dict):
            print("\tmessage:\t" + str(message))

    def getState(self):
        """
        Get the item name and the content of the particular branch in the tree which is currently selected.
        :return:
            returns the item name along with the particular branch in the tree which is currently selected.
        """
        print("ListAndDetails.getState")

    def setModel(self, items: OrderedDict):
        print("ListAndDetails.setModel:\t" + str(items))


class ToolTip(Menu):

    def __init__(self, container, toolTipText: str):
        Menu.__init__(self, container, tearoff=0)
        self.add_checkbutton(label=toolTipText, command=self.doNothing())

    def replaceTip(self, newTipText: str):
        self.delete(0, 1)
        self.add_checkbutton(label=newTipText, command=self.doNothing())

    def doNothing(self):
        pass


class PopupChecklist(Toplevel):

    def __init__(self, container, checkListDefinitions: OrderedDict, title: str = None, geometryStr: str=None,
                 **keyWordArguments):
        if checkListDefinitions is None or not isinstance(checkListDefinitions, OrderedDict):
            raise Exception("PopupChecklist constructor - Invalid checkListDefinitions argument:  " + str(checkListDefinitions))
        if title is None or not isinstance(title, str):
            raise Exception("PopupChecklist constructor - Invalid title argument:  " + str(title))
        if geometryStr is None or not isinstance(geometryStr, str):
            raise Exception("PopupChecklist constructor - Invalid geometryStr argument:  " + str(geometryStr))
        Toplevel.__init__(self, container, keyWordArguments)

        self.title(title)
        self.geometry(geometryStr)
        self.attributes('-topmost', 'true')
        self.checkBoxes = None
        self.variables = None
        if 'checkBoxes' in checkListDefinitions:
            self.checkBoxes = OrderedDict()
            self.variables = OrderedDict()
            rowIdx = 0
            for identifier, definition in checkListDefinitions['checkBoxes'].items():
                self.variables[identifier]   = definition['variable']
                checkbox    = Checkbutton(self, text=definition['text'], variable=definition['variable'],
                                          **definition['style'])
                definition['variable'].set(definition['value'])
                if 'trace' in definition and callable(definition['trace']):
                    definition['variable'].trace_add('write', definition['trace'])
                checkbox.grid(row=rowIdx, column=0, padx=definition['padx'], pady=definition['pady'],
                              sticky=definition['sticky'])
                checkbox.bind('<Enter>', self.mouseEnter)
                checkbox.bind('<Leave>', self.mouseLeave)
                rowIdx += 1

        if 'buttons' in checkListDefinitions:
            for ideitifier, definition in checkListDefinitions['buttons'].items():
                button      = Button( self, text=definition['text'], command=definition['command'],
                                      **definition['style'])
                button.grid(row=rowIdx, column=0, padx=definition['padx'], pady=definition['pady'],
                              sticky=definition['sticky'])


    def mouseEnter(self, event):
        event.widget.config(fg='blue', relief=RIDGE)

    def mouseLeave(self, event):
        event.widget.config(fg='black', relief=FLAT)

    def getState(self):
        currentState = OrderedDict()
        for key, value in self.variables.items():
            currentState[key] = value.get()
        return currentState


class PopupPanel(Toplevel):
    """
    Toplevel window that can contain any panel, i.e. a Frame or LabelFrame derived class.
    """

    DEFAULT_GEOMETRY    = {'width': 525, 'height': 400, 'left': 800, 'top': 300}

    def __init__(self, container, title: str, geometryDef: dict = None, **keyWordArguments):
        if not isinstance(title, str):
            raise Exception("PopupPanel constructor - Invalid title argument:  " + str(title))
        if geometryDef is None:
            geometryDef = PopupPanel.DEFAULT_GEOMETRY
        elif not isinstance(geometryDef, dict) or isinstance(geometryDef, str):
             raise Exception("PopupPanel constructor - Invalid geometryDef argument:  " + str(geometryDef))

        Toplevel.__init__(self, container, keyWordArguments)
        self.title(title)

        if isinstance(geometryDef, str):
            geometryStr = geometryDef
        else:
            geometryStr = str(geometryDef['width']) + 'x' + str(geometryDef['height']) + '+' + \
                          str(geometryDef['left']) + '+' + str(geometryDef['top'])
        self.geometry(geometryStr)
        self.content = None
        self.protocol('WM_DELETE_WINDOW', self.dispose)

    def setContent(self, content: Frame, **gridConfig):
        #   if content is None or not isinstance(content, Frame):
        #    raise Exception("PopupPanel constructor - Invalid content argument:  " + str(content))
        if gridConfig is None or not isinstance(gridConfig, dict):
            raise Exception("PopupPanel constructor - Invalid gridConfig argument:  " + str(gridConfig))
        self.content = content
        content.grid(**gridConfig)

    def show(self):
        self.mainloop()

    def dispose(self):
        if self.content is not None:
            self.content.grid_forget()
            self.content = None
        self.destroy()


class JsonTreeView(Treeview):

    MODE_STRICT = "strict-tree"
    MODE_NAME_VALUE = "name-value"
    MODES = (MODE_NAME_VALUE, MODE_STRICT)
    DEFAULT_MODE = MODE_NAME_VALUE

    DEFAULT_NAME_COL_WIDTH  = 200
    DEFAULT_VALUE_COL_WIDTH = 800

    def __init__(self, container, jsonContent: dict, jsonTreeviewConfig: dict):
        if jsonContent is not None and not isinstance(jsonContent, dict):
            raise Exception("JsonTreeView constructor - invalid json argument:   " + str(jsonContent))
        self.jsonTreeviewConfig = jsonTreeviewConfig        #   deepcopy would be more secure but this has Tk content.
        self.listener = None
        if 'listener' in self.jsonTreeviewConfig:
            if callable(self.jsonTreeviewConfig['listener']):
                self.listener = self.jsonTreeviewConfig['listener']

        openBranches = None
        if "openBranches" in self.jsonTreeviewConfig:
            openBranches = self.jsonTreeviewConfig["openBranches"]
            if openBranches is not None and not isinstance(openBranches, bool):
                raise Exception("JsonTreeView constructor - invalid openBranches argument:   " + str(openBranches))

        mode = None
        if "mode" in self.jsonTreeviewConfig:
            mode = self.jsonTreeviewConfig["mode"]
            if mode is not None and not isinstance(mode, str):
                raise Exception("JsonTreeView constructor - invalid mode argument:   " + str(mode))
        if not mode in JsonTreeView.MODES:
            self.mode = JsonTreeView.DEFAULT_MODE
        else:
            self.mode = mode
        if openBranches is None:
            self.openBranches = False
        else:
            self.openBranches = openBranches
        self.nameColWidth   = JsonTreeView.DEFAULT_NAME_COL_WIDTH
        self.valueColWidth  = JsonTreeView.DEFAULT_VALUE_COL_WIDTH

        if 'columnWidths' in self.jsonTreeviewConfig:
            if isinstance(self.jsonTreeviewConfig['columnWidths'], dict):
                if 'name' in self.jsonTreeviewConfig['columnWidths']:
                    if isinstance(self.jsonTreeviewConfig['columnWidths']['name'], int):
                        self.nameColWidth = self.jsonTreeviewConfig['columnWidths']['name']
                if 'value' in self.jsonTreeviewConfig['columnWidths']:
                    if isinstance(self.jsonTreeviewConfig['columnWidths']['value'], int):
                        self.valueColWidth = self.jsonTreeviewConfig['columnWidths']['value']
            else:
                raise Exception("JsonTreeView constructor - invalid columnWidth argument:   " + str(self.jsonTreeviewConfig['columnWidths']))

        self.style = Style()
        self.style.configure("Treeview", font=('Calibri', 11))

        #   ttk.Treeview.__init__(self, container, style="app.jsonTreeStyle", selectmode=EXTENDED, height=15)
        Treeview.__init__(self, container, selectmode=BROWSE, height=15)

        if self.mode == JsonTreeView.MODE_NAME_VALUE:
            self['columns'] = ["Name", "Value"]
            self.column('#0')
            self.column('#1', width=self.nameColWidth, minwidth=150, stretch=YES)
            self.column('#2', width=self.valueColWidth, minwidth=500, stretch=YES)
            self['show'] = 'tree headings'
            self.heading('#1', text="Name", anchor=W)
            self.heading('#2', text="Value", anchor=W)
            #    self.treeView.column(columnId, minwidth=100, width=columnDefs[columnId]['guiMinColWidth'],
            #           stretch=YES)
        else:
            self['show'] = 'tree headings'

        self.jsonContent = None
        if jsonContent is not None:
            self.setModel(jsonContent)

        self.bind("<<TreeviewSelect>>", self.selectHandler)
        self.bind("<<TreeviewOpen>>", self.openHandler)
        self.bind("<<TreeviewClose>>", self.closeHandler)
        self.bind("<Button-1>", self.leftMouseClick)
        self.bind("<Button-3>", self.rightMouseClick)
        self.bind("<Double-Button-1>", self.doubleMouseClick)

        self.bind('<Key>', self.localEvent)
        self.bind('<Enter>', self.localEvent)
        self.bind('<Leave>', self.localEvent)
        self.bind('<FocusIn>', self.localEvent)
        self.bind('<FocusOut>', self.localEvent)

    def localEvent(self, event):
        print("JsonTreeView.localEvent:\t" + str(event))
        if str(event.type) == "Enter":
            if event.focus:
                self.style.configure("Treeview", foreground='blue')
        elif str(event.type) == "Leave":
            self.style.configure("Treeview", foreground='black')

    def leftMouseClick(self, event):
        print("JsonTreeView.leftMouseClick:\t" + str(event))
        if self.listener is not None:
            itemText = []
            selection = self.selection()
            for item in selection:
                itemText += self.item(item, 'text')
            self.listener({'source': "JsonTreeView.leftMouseClick", 'event': event,
                           "selection": selection, "itemText": itemText})

    def rightMouseClick(self, event):
        print("JsonTreeView.rightMouseClick:\t" + str(event))
        if self.listener is not None:
            itemText = []
            selection = self.selection()
            for item in selection:
                itemText += self.item(item, 'text')
            self.listener({'source': "JsonTreeView.rightMouseClick", 'event': event,
                           "selection": selection, "itemText": itemText})

    def doubleMouseClick(self, event):
        print("JsonTreeView.doubleMouseClick:\t" + str(event))
        if self.listener is not None:
            itemText = []
            selection = self.selection()
            for item in selection:
                itemText += self.item(item, 'text')
            self.listener({'source': "JsonTreeView.doubleMouseClick", 'event': event,
                           "selection": selection, "itemText": itemText})

    def addBranch(self, parentId, name, branches):
        if isinstance(name, str) and name.startswith('__'):         #   meta-data
            return
        if isinstance(branches, str) and branches.startswith('__'): #   meta-data
            return

        if isinstance(branches, dict):
            if self.mode == JsonTreeView.MODE_STRICT:
                branchId = self.insert(parentId, END, text=str(name), tags=str(name), open=self.openBranches)
            elif self.mode == JsonTreeView.MODE_NAME_VALUE:
                branchId = self.insert(parentId, END, values=(str(name), ""), tags=str(name), open=self.openBranches)
            for key, value in branches.items():
                self.addBranch(branchId, key, value)
            branches['__changed']   = False
        elif isinstance(branches, list) or isinstance(branches, tuple):
            if self.mode == JsonTreeView.MODE_STRICT:
                branchId = self.insert(parentId, END, text=str(name), tags=str(name), open=self.openBranches)
            elif self.mode == JsonTreeView.MODE_NAME_VALUE:
                branchId = self.insert(parentId, END, values=(str(name), ""), tags=str(name), open=self.openBranches)
            listIdx = 0
            for element in branches:
                self.addBranch(branchId, "Idx: " + str(listIdx), element)
                listIdx += 1
        else:
            if name == None:
                if self.mode == JsonTreeView.MODE_STRICT:
                    self.insert(parentId, END, text=str(branches), tags=str(name), open=self.openBranches)
                elif self.mode == JsonTreeView.MODE_NAME_VALUE:
                    self.insert(parentId, END, values=(str(branches), ""), tags=str(name), open=self.openBranches)
            else:
                if self.mode == JsonTreeView.MODE_STRICT:
                    branchId = self.insert(parentId, END, text=str(name), tags=str(name), open=self.openBranches)
                    self.insert(branchId, END, text=str(branches), open=self.openBranches)
                elif self.mode == JsonTreeView.MODE_NAME_VALUE:
                    branchId = self.insert(parentId, END, values=("\t"+str(name), str(branches)), tags=str(name),
                                                        open=self.openBranches)

    def setModel(self, jsonContent: dict):
        items = self.get_children()
        self.delete(*items)
        for name, value in jsonContent.items():
            self.addBranch('', name, value)
        self.jsonContent = jsonContent

    def getState(self):
        return self.jsonContent

    def getTreeviewConfig(self):
        return self.jsonTreeviewConfig

    def refresh(self):
        """
        Since only a reference to the jsonContent is recorded as an attribute of this object, changes can
        be made externally which will be visible inside this object.  If so, the '__changes] attribute,
        which is never displayed, should be set to true so that the tree can be refreshed using this
        method potentially without redrawing the entire structure.
        :return:
        """
        pass

    def selectHandler(self, *argv):
        #   print("treeViewSelectHandler")
        if self.listener is not None:
            itemText = []
            selection = self.selection()
            for item in selection:
                itemText += self.item(item, 'text')
            self.listener({'source': "selectHandler", 'args': argv, 'selection':selection,
                           'itemText': itemText})

    def openHandler(self, *argv):
        #   print("treeViewOpenHandler")
        if self.listener is not None:
            self.listener({'source': "openHandler", 'args': argv})

    def closeHandler(self, *argv):
        #   print("treeViewCloseHandler")
        if self.listener is not None:
            self.listener({'source': "closeHandler", 'args': argv})


class JsonTreeViewFrame(LabelFrame):

    def __init__(self, container, jsonContent: dict, jsonTreeviewConfig: dict, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)

        horizontalScroller = Scrollbar(self, orient=HORIZONTAL, border=3, relief=GROOVE, width=15,
                                       cursor=Cursors.Hand_1.value)
        verticalScroller = Scrollbar(self, orient=VERTICAL, border=3, relief=GROOVE, width=15,
                                     cursor=Cursors.Hand_1.value)
        self.jsonTreeview = JsonTreeView(self, jsonContent, jsonTreeviewConfig)
        self.jsonTreeview.configure(yscroll=verticalScroller.set, xscroll=horizontalScroller.set)

        horizontalScroller.config(command=self.jsonTreeview.xview)
        verticalScroller.config(command=self.jsonTreeview.yview)

        self.jsonTreeview.pack(expand=True, side=LEFT, fill=BOTH, anchor="n")
        horizontalScroller.pack(side=BOTTOM, fill=X, after=self.jsonTreeview, anchor='s')
        verticalScroller.pack(side=RIGHT, fill=Y, anchor='e')

        #   self.contentText.config(state=NORMAL)
        #   self.contentText.window_create('1.0', window=self.contentFrame, stretch=True, align=BOTTOM)
        #   self.contentText.config(state=DISABLED)

        #   self.messageLabel = Label(self, text='messages', border=3, relief=SUNKEN, cursor=Cursors.DotBox.value)
        #   self.messageLabel.bind("<Enter>", self.mouseEnter)
        #   self.messageLabel.bind("<Leave>", self.mouseLeave)

        #   self.contentText.pack(expand=True, fill=BOTH)
        #   horizontalScroller.pack(side=BOTTOM, anchor='w', fill=X)
        #   verticalScroller.pack(side=RIGHT, fill=Y)
        #   self.messageLabel.pack(side=BOTTOM, anchor='w', fill=X)

    def mouseEnter(self, event):
        event.widget.configure(foreground='blue')

    def mouseLeave(self, event):
        event.widget.configure(foreground='black')


class ToggleButton(Label):

    def __init__(self, container, onText, offText, **keyWordArguments):
        if onText is None or not isinstance(onText, str):
            raise Exception('ToggleButton constructor: invalid onText argument: ' + str(onText))
        if offText is None or not isinstance(offText, str):
            raise Exception('ToggleButton constructor: invalid offText argument:    ' + str(offText))
        super().__init__(container, keyWordArguments)
        self.onText     = onText
        self.offText    = offText
        self.config(border=3, relief=RAISED, text=self.offText)
        self.state = False
        self.bind('<Button-1>', self.clicked)

    def clicked(self, event):
        if self.state:
            self.config(relief=RAISED, text=self.offText)
            self.state = False
        else:
            self.config(relief=SUNKEN, text=self.onText)
            self.state = True


class TtkTogleButton(Label):

    def __init__(self, container, onText, offText, **keyWordArguments):
        if onText is None or not isinstance(onText, str):
            raise Exception('TtkTogleButton constructor: invalid onText argument: ' + str(onText))
        if offText is None or not isinstance(offText, str):
            raise Exception('TtkTogleButton constructor: invalid offText argument:    ' + str(offText))
        super().__init__(container, **keyWordArguments)
        self.onText     = onText
        self.offText    = offText
        #   self.config(border=3, relief=RAISED, text=self.offText)
        self.state = False
        self.bind('<Button-1>', self.clicked)

    def clicked(self, event):
        if self.state:
            self.config(relief=RAISED, text=self.offText)
            self.state = False
        else:
            self.config(relief=SUNKEN, text=self.onText)
            self.state = True


class TtkToolBarDefinition:

    def __init__(self, **keyWordArguments):
        self.defaultConfig  = {
            'padding': (3, 3, 3, 3),
            'relief': GROOVE
        }
        self.componentOrder = ['Button', 'Checkbutton', 'Entry', 'Label', 'Combobox', 'Menubutton', 'Scale',
                               'Spinbox', 'Progressbar', 'Separator', 'Sizegrip', 'ToggleButton' ]
        self.components = {
            'ToggleButton': {
                'type': 'ToggleButton',
                'options': {
                    'text': 'OFF',
                    'anchor': CENTER,
                    'borderwidth': 2,
                    'image': None,
                    'compound': LEFT,
                    'justify': CENTER,
                    'padding': self.defaultConfig['padding'],
                    'relief': RAISED,
                    'style': None,
                    'takefocus': True
                }
            }
        }


class ToolBarDefinition:

    def menuResponse(self, message):
        messagebox.showinfo('Menu Response', message)

    def __init__(self, **keyWordArguments):
        #   Without listbox or radiobutton sets since these make the horizontal bar too wide.  A Menubutton, included
        #   does everything these would contribute.
        self.defaultConfig  = {
            'padx': 3,
            'pady': 3,
            'border': 3,
            'relief': RAISED
        }
        self.componentOrder = ['Button', 'Checkbutton', 'ToggleButton', 'Entry', 'Label', 'Menubutton', 'Scale']
        self.components = {}
        self.button = {
                'type': 'Button',
                'config': {
                    'text': 'Button',
                    'command': buttonClicked,
                    'justify': CENTER,
                    'padx': self.defaultConfig['padx'],
                    'pady': self.defaultConfig['pady'],
                    'border': self.defaultConfig['border'],
                    'relief': self.defaultConfig['relief']
                }
        }
        self.checkbutton    = {
            'type': 'Checkbutton',
            'onCommand': None,
            'offCommand': None,
            'config': {
                'text': 'Checkbutton',
                'bd': 3,
                'command': checkButtonClicked,
                'justify': LEFT,
                'padx': self.defaultConfig['padx'],
                'pady': self.defaultConfig['pady'],
                'border': self.defaultConfig['border'],
                'relief': self.defaultConfig['relief'],
                'variable': self.checkButtonIntvar
            }
        }
        self.togglebutton   = {
            'type': 'ToggleButton',
            'config': {
                'text': 'ToggleButton',
                'padx': self.defaultConfig['padx'],
                'pady': self.defaultConfig['pady'],
                'border': self.defaultConfig['border'],
                'relief': self.defaultConfig['relief']
            }
        }
        self.entry  = {
            'type': 'Entry',
            'text': 'Entry',
            'config': {
                'border': self.defaultConfig['border'],
                'relief': self.defaultConfig['relief']
            }
        }
        self.label = {
            'type': 'Label',
            'config': {
                'text': 'Label',
                'border': self.defaultConfig['border'],
                'padx': self.defaultConfig['padx'],
                'pady': self.defaultConfig['pady'],
                'relief': self.defaultConfig['relief']
            },
            'eventHandlers': {
                '<Button-1>': labelEventHandler,
                '<Button-2>': labelEventHandler,
                '<Button-3>': labelEventHandler,
                '<Button-4>': labelEventHandler,
                '<Button-5>': labelEventHandler,
                '<Motion>': labelEventHandler,
                '<ButtonRelease>': labelEventHandler,
                '<Double-Button-1>': labelEventHandler,
                '<Double-Button-2>': labelEventHandler,
                '<Double-Button-3>': labelEventHandler,
                '<Enter>': labelEventHandler,
                '<Leave>': labelEventHandler,
                '<FocusIn>': labelEventHandler,
                '<FocusOut>': labelEventHandler,
                '<Return>': labelEventHandler,
                '<Key>': labelEventHandler
            }
        }
        self.menubutton = {
            'type': 'Menubutton',
            'itemNames': ('one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven'),
            'items': {'one': {'label': 'One', 'command': lambda: self.menuResponse('One')},
                      'two': {'label': 'Two', 'command': lambda: self.menuResponse('Two')},
                      'three': {'label': 'Three', 'command': lambda: self.menuResponse('Three')},
                      'four': {'label': 'Four', 'command': lambda: self.menuResponse('Four')},
                      'five': {'label': 'Five', 'command': lambda: self.menuResponse('Five')},
                      'six': {'label': 'Six', 'command': lambda: self.menuResponse('Six')},
                      'seven': {'label': 'Seven', 'command': lambda: self.menuResponse('Seven')},
                      'eight': {'label': 'Eight', 'command': lambda: self.menuResponse('Eight')},
                      'nine': {'label': 'Nine', 'command': lambda: self.menuResponse('Nine')},
                      'ten': {'label': 'Ten', 'command': lambda: self.menuResponse('Ten')},
                      'eleven': {'label': 'Eleven', 'command': lambda: self.menuResponse('Eleven')}
                      },
            'config': {
                'text': 'Menubutton',
                'anchor': W,
                'border': self.defaultConfig['border'],
                'padx': self.defaultConfig['padx'],
                'pady': self.defaultConfig['pady'],
                'relief': self.defaultConfig['relief']
            }
        }
        self.scale     = {
            'type': 'Scale',
            'text': 'Scale',
            'config': {
                'border': self.defaultConfig['border'],
                'relief': self.defaultConfig['relief'],
                'orient': HORIZONTAL,
                'command': scaleMoved,
                'variable': self.scaleVariable,
                'from_': 32.00,
                'to': 212.00,
                'resolution': 0.1,
                'label': 'Temp (F)',
                'length': 180,
                'showvalue': 0,
                'sliderlength': 20,
                #   'tickinterval': 32
            }
        }
        self.addComponent('Button', self.button, True)
        self.addComponent('Checkbutton', self.checkbutton, True)
        self.addComponent('ToggleButton', self.togglebutton, True)
        self.addComponent("Entry", self.entry, True)
        self.addComponent("Label", self.label, True)
        self.addComponent("Menubutton", self.menubutton, True)
        self.addComponent("Scale", self.scale, True)

    def addComponent(self, name: str, descriptor: dict, force: bool = False):
        """
        Adds a component to the toolbar definition.
        Will raise an Exception if invalid arguments are padded in.
        :param name:    user's name for the component.
        :param descriptor:  map containing tkinter configuration parameter map.
        :param force:   if true and a component with the same name already exists, the new one will replace it.
                        if false, the existing component with the same name will not be replaced.
        :return:        True if component added, False otherwise.
        """
        if name is None or not isinstance(name, str):
            raise Exception("ToolBarDefinition.addComponent:    name argument is invalid:   " + str(name))
        if descriptor is None or not isinstance(descriptor, dict):
            raise Exception("ToolBarDefinition.addComponent:    tdescriptor argument is invalid:    " + str(descriptor))
        if force is None or not isinstance(force, bool):
            raise Exception("ToolBarDefinition.addComponent:    force argument is invalid:  " + str(force))
        if 'components' not in self.__dict__:
            self.components = {}
        if name in self.components:
            if not force:
                return False
            else:
                print('Replacing conponent:\t' + name)
        self.components[name]   = descriptor

    def removeComponent(self, name: str):
        if name is not None and isinstance(name, str) and name in self.components:
            del self.components[name]

    def configComponent(self, name: str, config: dict):
        if config is None or not isinstance(config, dict):
            raise Exception("ToolBarDefinition.configComponent: config argument is invalid:    " + str(config))
        if name in self.components:
            self.components[name]   = config
            return True
        else:
            return False

    def setAttribute(self, componentName: str, attributeName: str, value):
        if attributeName is None or not isinstance(attributeName, str):
            raise Exception("ToolBarDefinition.setAttribute:    attributeName argument is invalid:  " + str(attributeName))
        if componentName in self.components:
            self.components[componentName][attributeName]   = value
            return True
        else:
            return False


class ToolBar(LabelFrame):

    def __init__(self, container, toolBarDefinition: ToolBarDefinition, layoutConfig: dict,  **keyWordArguments):
        if toolBarDefinition is None or not isinstance(toolBarDefinition, ToolBarDefinition):
            raise Exception("ToolBar constructor:   toolBarDefinition argument is invalid:  " + str(toolBarDefinition))
        if layoutConfig is None or not isinstance(layoutConfig, dict):
            raise Exception("ToolBar constructor:   layoutConfig argument is invalid:    " + str(layoutConfig))
        super().__init__(container, keyWordArguments)

        #   put the toolbar at the top
        #   self.toolBar = LabelFrame(self, text='Toolbar', bd=3, relief=RAISED)
        #   self.toolBar.grid(row=0, column=0, columnspan=2, sticky=EW+N, padx=10, pady=2)
        #   self.detailToggle   = Checkbutton(self.toolBar, text='Deep', )
        #   self.detailToggle.grid(row=0, column=0, sticky=W, padx=5, pady=5)

        #   for componentName, componentDefinition in toolBarDefinition.components.items():
        #       print( componentName + ':\t' + str(componentDefinition) )
        if not 'componentOrder' in toolBarDefinition.__dict__:
            toolBarDefinition.componentOrder = list(toolBarDefinition.components.keys())
        print('\ncomponentOrder:\t' + str(toolBarDefinition.componentOrder))
        self.components = {}
        for componentName in toolBarDefinition.componentOrder:
            if toolBarDefinition.components[componentName]['type'] == 'Button':
                self.components[componentName] = Button(self, toolBarDefinition.components[componentName]['config'])
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'Checkbutton':
                self.components[componentName] = Checkbutton(self, toolBarDefinition.components[componentName]['config'])
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'ToggleButton':
                self.components[componentName] = ToggleButton(self, 'ON', 'OFF',
                                                              **toolBarDefinition.components[componentName]['config'])
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'Entry':
                self.components[componentName] = Entry(self, toolBarDefinition.components[componentName]['config'])
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'Label':
                self.components[componentName] = Label(self, toolBarDefinition.components[componentName]['config'])
                #   'eventHandlers'
                if 'eventHandlers' in toolBarDefinition.components[componentName]:
                    for eventName, eventHandler in toolBarDefinition.components[componentName]['eventHandlers'].items():
                        self.components[componentName].bind(eventName, eventHandler)
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'Menubutton':
                print('Menubutton:\t' + str(toolBarDefinition.components[componentName]))
                self.components[componentName] = Menubutton(self, toolBarDefinition.components[componentName]['config'])
                itemMenu    = Menu( self.components[componentName], tearoff=0)
                for itemName in toolBarDefinition.components[componentName]['itemNames']:
                    menuItem = toolBarDefinition.components[componentName]['items'][itemName]
                    itemMenu.add_command(label=menuItem['label'], command=menuItem['command'])
                self.components[componentName].config(menu=itemMenu)
                self.components[componentName].pack(side=LEFT)
            elif toolBarDefinition.components[componentName]['type'] == 'Scale':
                self.components[componentName] = Scale(self, toolBarDefinition.components[componentName]['config'])
                self.components[componentName].pack(side=LEFT)


class OptionEntryDialog(Toplevel):
    """
    This dialog will be used for entry of strings for use in Linux console commands.
    It should therefore be as secure as possible.
    It therefore should be immutable, but since it is a TopLevel, the parent class is not immutable.
    It therefore uses an immutable contained class to store its attributes.
    """

    OPTION_TYPES    = ('text', 'textList', 'singleSelectList', 'multiSelectList', 'number')

    class Attributes:

        def __init__(self, **keyWordArguments):
            for key, value in keyWordArguments.items():
                self.__dict__[key] = value

        def __setattr__(self, key, value):
            if not key in self.__dict__:
                self.__dict__[key] = value
            else:
                raise Exception('OptionEntryDialog:    Attempt to set immutable attribute:    ' + str(key))

    def __init__(self, container, **keyWordArguments):
        print('OptionEntryDialog constructor:\t' + str(keyWordArguments))
        if 'optionName' not in keyWordArguments:
            raise Exception('OptionEntryDialog constructor - required key word argument, optionName, is missing')
        if keyWordArguments['optionName'] is None or not isinstance(keyWordArguments['optionName'], str):
            raise Exception('OptionEntryDialog constructor - invalid optionName argument:    ' +
                            str(keyWordArguments['optionName']))
        if 'type' not in keyWordArguments:
            raise Exception('OptionEntryDialog constructor - required key word argument, type, is missing')
        if keyWordArguments['type'] is None or not isinstance(keyWordArguments['type'], str) or \
                keyWordArguments['type'] not in OptionEntryDialog.OPTION_TYPES:
            raise Exception('OptionEntryDialog constructor - invalid type argument:    ' +
                            str(keyWordArguments['type']))
        if keyWordArguments['type'] == 'singleSelectList' or keyWordArguments['type'] == 'multiSelectList':
            if 'listItems' not in keyWordArguments:
                self.listItems = None
                raise Exception('OptionEntryDialog constructor - required key word argument, listItems, is missing')
            if keyWordArguments['listItems'] is None or not isinstance(keyWordArguments['listItems'], tuple):
                self.listItems = None
                raise Exception('OptionEntryDialog constructor - invalid listItems argument:    ' +
                                str(keyWordArguments['listItems']))
            for item in keyWordArguments['listItems']:
                if item is None or not isinstance(item, str):
                    self.listItems = None
                    raise Exception('OptionEntryDialog constructor - invalid List Item:    ' + str(item))
            self.listItems = deepcopy(keyWordArguments['listItems'])
        else:
            self.listItems = None
        if keyWordArguments['validator'] is None or not callable(keyWordArguments['validator']):
            self.validator = None
        else:
            self.validator = keyWordArguments['validator']
        if keyWordArguments['callback'] is None or not callable(keyWordArguments['callback']):
            self.callback = None
        else:
            self.callback = keyWordArguments['callback']
        super().__init__(container)
        self.optionName     = keyWordArguments['optionName']
        self.type           = keyWordArguments['type']
        self.attributes = OptionEntryDialog.Attributes(optionName=self.optionName, type=self.type,
                                                       listItems = self.listItems, callback=self.callback,
                                                       validator=self.validator)

        self.entryLabel = Label(self, text=self.attributes.optionName)
        self.optionText     = StringVar()
        self.optionEntry    = Entry(self, border=3, relief=SUNKEN, textvariable=self.optionText)
        self.optionText.set('')
        self.commitButton   = Button(self, text='Commit', command=self.commit)
        self.cancelButton   = Button(self, text='Cancel', command=self.cancel)
        self.validatingVar    = BooleanVar()
        self.validatingCheckbutton  = Checkbutton(self, text='Validate', variable=self.validatingVar)
        self.validatingVar.set(True)
        self.optionEntry.bind('<Key>', self.keyEventHandler)
        self.validatingVar.trace("w", self.validateToggle)

        self.messageLabel = None

        self.entryLabel.grid(row=0, column=0,padx=5, pady=5)
        self.optionEntry.grid(row=0, column=1,padx=5, pady=5)
        self.commitButton.grid(row=1, column=0,padx=2, pady=2)
        self.cancelButton.grid(row=1, column=1,padx=2, pady=2)
        self.validatingCheckbutton.grid(row=2, column=0, columnspan=2,padx=2, pady=2)
        self.optionEntry.focus_set()
        print('OptionEntryDialog constructor finished')

    def keyEventHandler(self, event):
        print('keyEventHandler:\t' + str(event))
        if event.keysym == 'Return':
            self.commit()

    def commit(self):
        canExit = False
        if self.validatingVar.get():
            issues = self.attributes.validator(self.optionText.get())
            if issues == None:
                canExit = True
            else:
                #   validation message should display
                print( issues, file=sys.stderr)
                if self.messageLabel == None:
                    self.geometryString("320x250+250+100")
                    self.messageLabel = Label(self, text=issues, border=4, relief=SUNKEN, fg="#002255" )
                    self.messageLabel.grid(row=3, column=0, columnspan=2, padx=3, pady=3)

        else:
            canExit = True
        if canExit:
            self.attributes.callback(entry=self.optionText.get(), optionName=self.attributes.optionName)
            self.destroy()

    def cancel(self):
        self.destroy()

    def validateToggle(self, *args):
        if not self.validatingVar.get() and self.messageLabel != None:
                self.messageLabel.grid_forget()
                self.geometryString("275x100+250+100")
                self.messageLabel = None


class PasswordInputDialog(Toplevel):

    def __init__(self, container, callback, **keyWordArguments):
        print('PasswordInputDialog constructor:\t' + str(keyWordArguments))
        if callback is None or not callable(callback):
            self.callback = None
        else:
            self.callback = callback
        super().__init__(container, keyWordArguments)

        self.passwordLabel  = Label(self, text='Password', border=2, relief=RIDGE)
        self.entry  = StringVar()
        self.entry.set('')
        self.text   = self.entry.get()
        self.passwordEntry  = Entry(self, show='*', border=2, relief=RIDGE, textvariable=self.entry)

        self.commitButton   = Button(self, text='Commit', command=self.commit)
        self.cancelButton   = Button(self, text='Cancel', command=self.cancel)
        self.ShowButton     = Button(self, text='Show', command=self.showSwitch)
        self.showing = False

        self.passwordEntry.bind('<Button-1>', self.mouseEvent)
        self.passwordEntry.bind('<Button-3>', self.mouseEvent)
        self.passwordEntry.bind('Double-Button-1', self.mouseEvent)
        self.passwordEntry.bind('Double-Button-3', self.mouseEvent)
        self.passwordEntry.bind('<Enter>', self.mouseEvent)
        self.passwordEntry.bind('<Leave>', self.mouseEvent)

        self.passwordLabel.grid(row=0, column=0)
        self.passwordEntry.grid(row=0, column=1)
        self.ShowButton.grid(row=0, column=2)
        self.commitButton.grid(row=1, column=0)
        self.cancelButton.grid(row=1, column=2)
        self.passwordEntry.focus_set()

    def mouseEvent(self, event):
        print('PasswordInputDialog.mouseEvent:\t' + str(event))

    def showSwitch(self):
        if self.showing:
            self.passwordEntry.config(show='*')
            self.ShowButton.config(text='Show')
            self.showing = False
        else:
            self.passwordEntry.config(show='')
            self.ShowButton.config(text='Hide')
            self.showing = True


    def commit(self):
        #   print('PasswordInputDialog.commit()')
        self.callback(Message({'type': 'password', 'value': self.entry.get()}))
        self.destroy()

    def cancel(self):
        print('PasswordInputDialog.cancel()')
        self.callback(Message({'type': 'password', 'value': 'cancelled'}))
        self.destroy()


def buttonClicked():
    print('buttonClicked')


def checkButtonClicked():
    print('checkButtonClicked')


def scaleMoved(scaleValue):
    print('Scale Moved:\t' + str(scaleValue) + '\t\tscaleVariable:\t' + str(scaleVariable.get()))


def labelEventHandler(event):
    print("labelEventHandler event:\t" + str(event))


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        window.destroy()


def messageListner(message: dict):
    print("messageListner:\t" + str(message))


if __name__ == '__main__':
    logging.basicConfig(filename=INSTALLATION_FOLDER + '/' + LOGGING_FOLDER + '/' + 'view.Components.log',
                        level=logging.DEBUG, format='%(message)s')
    window  = Tk()
    window.geometry('800x400+50+50')
    window.title(PROGRAM_TITLE)
    window.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    checkButtonIntvar   = IntVar()
    scaleVariable       = DoubleVar()

    """
    toggleButton = ToggleButton(window, onText='Switched ON', offText='Switched OFF')

    #   toggleButton.pack(ipadx=3, ipady=3)
    #   toggleButton.pack( {'ipadx': 3, 'ipady': 3 } )


    toolBarDefinition   = ToolBarDefinition()

    toolBar = ToolBar(window, toolBarDefinition, {'type': 'grid', 'config':
                                    {'row': 0, 'column': 0, 'columnspan': 2, 'sticky': EW+N,
                                     'padx': 10, 'pady': 2}}, text='Toolbar', bd=3, relief=RAISED)
    toolBar.pack( {'ipadx': 3, 'ipady': 3, 'pady': 15 } )

    #   ttkToolBarDefinitions   = TtkToolBarDefinition()
    #   ttkTogleButton = TtkTogleButton(window, 'ON', 'OFF', **ttkToolBarDefinitions.components['ToggleButton']['options'])
    #   ttkTogleButton.pack({'ipadx': 3, 'ipady': 3 })
    
    #   validator=None, buttons: dict = None, length: int = DEFAULT_LENGTH,
    #                    history: tuple = None, fuzzyType: str = None, **keyWordArguments

    def validator(textVar: str, event):
        print("validator:\t" + textVar.get())
        if textVar.get() == "error":
            return "ERROR, ERROR, ERROR!!!"
        else:
            return None

    def buttonHandler(buttonText: str):
        print("buttonHandler:\t" + buttonText)

    #   Filter Button Names:   Commit, Run, Filter, OK, Cancel, Save, Select
    buttons = {"Commit": lambda: buttonHandler("Commit"),
               "Run": lambda: buttonHandler("Run"),
               "Filter": lambda: buttonHandler("Filter"),
               "OK": lambda: buttonHandler("OK"),
               "Cancel": lambda: buttonHandler("Cancel"),
               "Save": lambda: buttonHandler("Save"),
               "Select": lambda: buttonHandler("Select")  }

    buttons = {"Filter": lambda: buttonHandler("Filter"),
               "Cancel": lambda: buttonHandler("Cancel"),
               "Save": lambda: buttonHandler("Save"),
               "Select": lambda: buttonHandler("Select")  }

    searchHistory = ("linux", "debian", "kali", "caine", "xwindows", "spynet")

    stringEntryDescriptor = StringEntryDescriptor(validator=validator, buttons=buttons,
                                                  length=StringEntryPane.DEFAULT_LENGTH,
                                                  history=searchHistory, fuzzyType=None,
                                                  messageListener=messageListner)

    #   stringEntryPane = StringEntryPane(window, **stringEntryDescriptor.__dict__, text="Filter String",
    #                                                 border=4, relief=RAISED)
    stringEntryPane = StringEntryPane(window, **stringEntryDescriptor.__dict__, text="Filter String",
                                                  border=4, relief=RAISED)
    stringEntryPane.pack(ipadx=3, ipady=3, padx=5, pady=10)
    """

    """
    includeYear     = BooleanVar()
    includeMonth    = BooleanVar()
    includeDay      = BooleanVar()
    includeHour     = BooleanVar()
    includeMinute   = BooleanVar()
    includeSecond   = BooleanVar()

    def applyButtonClicked():
        print("applyButtonClicked")

    def yearIncludeChange(*args):
        print("yearIncludeChange:\t" + str(includeYear.get()))

    def monthIncludeChange(*args):
        print("monthIncludeChange:\t" + str(includeMonth.get()))

    def dayIncludeChange(*args):
        print("dayIncludeChange:\t" + str(includeDay.get()))

    def hourIncludeChange(*args):
        print("hourIncludeChange:\t" + str(includeHour.get()))

    def minuteIncludeChange(*args):
        print("minuteIncludeChange:\t" + str(includeMinute.get()))

    def secondIncludeChange(*args):
        print("secondIncludeChange:\t" + str(includeSecond.get()))

    includeCheckboConfig    = {
        'onvalue': True,
        'offvalue': False,
        'justify': LEFT,
        'border': 2,
        'relief': FLAT
    }

    includeButtonConfig = {

    }

    from view.SearchComponents import DateTimeField

    checkListDefinitions = OrderedDict( {
        'checkBoxes': {
            DateTimeField.YEAR: {
                'text': 'Year',
                'variable': includeYear,
                    # method receiving change notifications
                'value': True,
                "trace": yearIncludeChange,
                    # configuration options for the checkbox
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            },
            DateTimeField.MONTH: {
                'text': 'Month',
                'variable': includeMonth,
                'value': True,
                "trace": monthIncludeChange,
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            },
            DateTimeField.DAY: {
                'text': 'Day',
                'variable': includeDay,
                'value': True,
                "trace": dayIncludeChange,
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            },
            DateTimeField.HOUR: {
                'text': 'Hour',
                'variable': includeHour,
                'value': True,
                "trace": hourIncludeChange,
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            },
            DateTimeField.MINUTE: {
                'text': 'Minute',
                'variable': includeMinute,
                'value': True,
                "trace": minuteIncludeChange,
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            },
            DateTimeField.SECOND: {
                'text': 'Second',
                'variable': includeSecond,
                'value': True,
                "trace": secondIncludeChange,
                'style': includeCheckboConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            }
        },
        #   Optional button bar at the bottom
        'buttons': {
            'Apply': {
                'text': 'Apply',
                "command": applyButtonClicked,
                'style': includeButtonConfig,
                'padx': 5,
                'pady': 3,
                'sticky': 'w'
            }
        }
    })

    def launchPopupChecklist(checkListDefinitions):
        print("\nlaunchPopupChecklist")
        popupChecklist = PopupChecklist(window, checkListDefinitions, title="Include in Filter",
                                        geometryStr="150x250+800+300", border=5, relief=RAISED )
        popupChecklist.mainloop()

    buttonPopupChecklist = Button(window, text='Popup Check List',
                                  command=lambda: launchPopupChecklist(checkListDefinitions))
    buttonPopupChecklist.pack(ipadx=3, ipady=3, padx=5, pady=15)

    popupPanel  = PopupPanel(window, "Test of PopupPanel", border=5, relief=RAISED)
    popupPanel.show()
        #   container, title: str, geometryDef: dict = None, **keyWordArguments

    """

    listItems = OrderedDict()
    listItems['One']        = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Two']        = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Three']      = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Four']       = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Five']       = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Six']        = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Seven']      = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Eight']      = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }
    listItems['Nine']       = {
        'fieldOne': 'valueOne',
        'fieldTwo': 'valueTwo',
        'fieldThree': 'valueThree'
    }

    viewConfig = {
        'height': 10
    }

    listAndDetails  = ListAndDetails(window, listItems, viewConfig, text='Counting', border=3, relief=RAISED)
    listAndDetails.pack(expand=True, fill=BOTH)

    window.mainloop()

