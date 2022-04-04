#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   July 12, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/Menus.py
#   Purpose:        Programmable Main menu and programmable menus generally.
#   Development:
#

import os
from tkinter import Tk, Menu, messagebox


class MenuContent:
    """
    Hard code for this application for now.
    Can keep it flexible with one MainMenu
    """

    def __init__(self):
        self.content = {}
        self.messageSource = 'view.Menus.MenuContent.additem'

        self.content = {'items': ['Files', 'Analysis'],
                        'itemDefs': {
                            'Files': {
                                'items': ['Open New', 'Open Archived', 'Save','Exit'],
                                'itemDefs': {
                                    'Open New': {'action': fileOpenStub,
                                             'config': None,
                                             'descriptor': None,
                                             'text': 'Open a new log file for analysis'},
                                    'Open Archived': {'action': fileOpenArchivedStub,
                                             'config': None,
                                             'descriptor': None,
                                             'text': 'Open an archived log file for analysis'},
                                    'Save': {'action': fileSaveStub,
                                             'config': None,
                                             'descriptor': None,
                                             'text': 'Save a log file to the archive'},
                                    'Exit': {'action': fileExitStub,
                                             'config': None,
                                             'descriptor': None,
                                             'text': 'Exit this program'},
                                },
                            },
                            'Analysis': {
                                'items': ['Regular Expression', 'Splitting'],
                                'itemDefs': {
                                    'Regular Expression': {
                                            'action': regularExpressionStub,
                                            'config': {},
                                            'descriptor': {},
                                            'text': 'Design and run regular expressions on log files'},
                                    'Splitting': {
                                            'action': splittingStub,
                                            'config': {},
                                            'descriptor': {},
                                            'text': 'Use character based splitting to create record structure from log text lines'}
                                }
                            }
                        }
                    }

    def pathExists(self, menuPath):
        """

        :param menuPath:
        :return:
        """
        branch = self.content['itemDefs']
        for itemName in menuPath:
            self.logger.addMessage(self.messageSource, 'Looking for item:\t' + itemName + '\t\t' + 'In:\t' + str(branch))
            if branch is not None and itemName in branch:
                #   is it a sub-menu?
                if 'itemDefs' in branch[itemName]:
                    branch = branch[itemName]['itemDefs']
                else:
                    branch = None
            else:
                return False
        return True

    def constructPath(self, menuPath):
        pass

    def addItem(self, menuPath, name, action, config, descriptor, text, force, **keyWordArguments ):
        """
        Items on the same path as existing items are replaced by the new item if force == true.
        :param menuPath:    list of names of menu items which is the path in the menu at which to place the new item.
        :param name:        name that user sees in the menu.
        :param action:      method to invoke when menu item is selected.  invocation does not include passable
                            parameters yet, but this could be added.
        :param confir:      all configuration parameters for the gui component.
        :param descriptor:  all information needed to launch the action, including arguments.
        :param text:        descriptive text for item help.  could be displayed as a tool tip.
        :param force:       if false, do not replace item if one is found at same path location, otherwse replace.
        :return:            message string reporting results of operation
        """

        self.logger.addMessage(self.messageSource, 'Adding a Menu Item at: ' + str(menuPath))
        for itemName in menuPath:
            print(itemName)
        if self.pathExists(menuPath):
            self.logger.addMessage(self.messageSource, 'item path exists:\t' + str(menuPath))
        else:
            self.logger.addMessage(self.messageSource, 'adding item path:\t' + str(menuPath))

        self.logger.listMessages(self.messageSource, 'Debug Messages')

    def constructMenu(self):
        pass


class MenuView(Menu):

    def __init__(self, container, menu, isMenuBar: bool = False):
        self.container = container
        if not isinstance(menu, MenuContent):
            raise Exception('MenuView constructor: content must be instance of MenuContent')
        self.menu = menu

        print('menu content:\t' + str(menu.content))
        self.addMenu(None, menu.content)

        menuBar = Menu(container)
        fileMenu = Menu(menuBar, tearoff=0)
        fileMenu.add_command(label='New', command=fileNewStub)
        fileMenu.add_command(label='Open', command=fileOpenStub)
        fileMenu.add_command(label='Save', command=fileSaveStub)
        fileMenu.add_command(label='Close', command=fileCloseStub)
        fileMenu.add_command(label='Exit', command=fileExitStub)
        menuBar.add_cascade(label='Files', menu=fileMenu)
        if isMenuBar:
            container.config(menu=menuBar)

        #   self.showMessage("showinfo", "MenuView Constructor Ran")

    def addMenu(self, parent, itemDefinitions):
        for item in itemDefinitions['items']:
            newMenu = Menu()
            itemDefinition  = itemDefinitions['itemDefs'][item]
            if 'items' in itemDefinition:       #   this is a sub menu
                self.addMenu(newMenu, itemDefinition)
            else:                               #   this is an action
                pass
            print(str(itemDefinition))


    def showMessage(self, messateType, messageText, **keyWordArguments):
        if messateType is not None and isinstance(messateType, str):
            if messateType == "showinfo":
                messagebox.showinfo("Message", messageText)
            elif messateType == "showwarning":
                messagebox.showinfo("Warning", 'Warning Message')
            elif messateType == "showerror":
                pass
            elif messateType == "askokcancel":
                pass
            elif messateType == "askquestion":
                pass
            elif messateType == "askretrycancel":
                pass
            elif messateType == "askyesno":
                pass
            elif messateType == "askyesnocancel":
                pass


#Testing purposes only:
    def selectFile(self, startFolder, logFilesText) :
        """
        Load contents of any number of text files from a folder
        :param startFolder:     Initial folder to look in for log files.
        :param logFilesText:    Map of file path to list of lines of text in file.
        :return:
        """
        logFileSelected = filedialog.askopenfilenames(initialdir=startFolder)
        #   print(str(type(logFileSelected)))
        #   print(str(logFileSelected))
        for filePath in logFileSelected:
            logFile = open(filePath, 'r')
            logText = logFile.read()
            logFilesText[filePath] = logText.split('\n')
            logFile.close()


from tkinter import filedialog

def fileNewStub():
    messagebox.showinfo('New file feature', "not implemented yet")

def fileOpenStub():
    messagebox.showinfo('Open file feature', "not implemented yet")

def fileOpenArchivedStub():
    messagebox.showinfo('Open archived file feature', "not implemented yet")

def fileSaveStub():
    messagebox.showinfo('Save file feature', "not implemented yet")

def fileCloseStub():
    messagebox.showinfo('Close file feature', "not implemented yet")

def fileExitStub():
    #  messagebox.showinfo('Exit program feature', "not implemented yet")
    answer = messagebox.askyesno('Exit program ', "Exit the menu designer program?")
    if answer == True:
        window.destroy()

def regularExpressionStub():
    messagebox.showinfo('Regular Expression Design', "not implemented yet")

def splittingStub():
    messagebox.showinfo('Generate Records by Splitting', "not implemented yet")


if __name__ == '__main__':

    window  = Tk()
    window.geometry('800x400+50+50')
    window.title('Menu Design View')
    menuContent = MenuContent()

    menuView = MenuView(window, menuContent)
    logEntries = {}

    menuItemPath    = ['Files', 'Open']
    config = None
    descriptor = None
    #   textFile = TextFile()
    #   menuView.selectFile('/var/log', logEntries)

    menuContent.addItem(menuItemPath, 'Open', menuView.selectFile, config, descriptor, 'Import a log file into application', False)

    menubar = MenuView(window, menuContent, True)
    window.mainloop()