#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         model/ToolsDB.py
#   Date Started:   April 8, 2022
#   Purpose:        Interface to LinuxTools.db, the exclusive repository of user defined configurations of Linux
#                   commands.
#   Development:
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
#       Commands to possibly include in initial Tool set:
#               1)  mmls - Display the partition layout of a volume system  (partition tables)
#                           (Requlres an image file - dd)
#                       SYNOPSIS:
#                       mmls [-t mmtype ] [-o offset ] [ -i imgtype ] [-b dev_sector_size] [-BrvV] [-aAmM] image [images]
#               2)  fsstat - Display general details of a file system
#                       SYNOPSIS:
#                       fsstat [-f fstype ] [-i imgtype] [-o imgoffset] [-b dev_sector_size] [-tvV] image [images]
#
#               3)  "Plaso (https://github.com/log2timeline/plaso) is a Python-based rewrite
#                           of the Perl-based log2timeline tool initially created by Kristinn
#                           Gudjonsson and enhanced by others. It's easy to make a super
#                           timeline with log2timeline, but interpretation is difficult. The latest
#                           version of the plaso engine can parse the ext4 as well as different
#                           type of artifacts, such as syslog messages, audit, utmp, and others."
#                           (Breach detection with Linux filesystem forensics)
#                           (23 Apr 2018 | Gary Smith (/users/greptile))
#


from sqlite3 import connect, Binary
from os import environ
from collections import OrderedDict
from datetime import datetime
from copy import deepcopy
from subprocess import Popen, PIPE, STDOUT
from pickle import loads, dumps
from enum import Enum

from tkinter import Tk, messagebox

from model.Installation import USER_DATA_FOLDER

PROGRAM_TITLE = "Tools Database"

INSTALLING  = False
TESTING     = True


class ExportFormat(Enum):
    CSV         = "CSV"
    TEXT        = 'Text'
    OO_WRITE    = 'OpenOffice Write'
    OO_CALC     = "OpenOffice Calc"

    def __str__(self):
        return self.value


class Tool:

    def __init__(self, name: str, description: str, command: str, arguments: OrderedDict):
        self.timeStamp = datetime.now()
        Tool.__checkArgs(name, description, command, arguments)
        self.name = name
        self.description = description
        self.command = command
        self.arguments = deepcopy(arguments)

    @staticmethod
    def makeTool( name: str, description: str, command: str, arguments: OrderedDict):
        Tool.__checkArgs(name, description, command, arguments)
        return Tool(name, description, command, arguments)

    @staticmethod
    def __checkArgs( name: str, description: str, command: str, arguments: OrderedDict):
        if not isinstance(name, str):
            raise Exception("Tool constructor - Invalid name argument:  " + str(name))
        if not isinstance(description, str):
            raise Exception("Tool constructor - Invalid description argument:  " + str(description))
        if not isinstance(command, str):
            raise Exception("Tool constructor - Invalid command argument:  " + str(command))
        if not isinstance(arguments, OrderedDict):
            raise Exception("Tool constructor - Invalid arguments argument:  " + str(arguments))

    def getName(self):
        return self.name

    def getDescription(self):
        return self.description

    def getCommand(self):
        return self.command

    def getArgList(self):
        #   Uses flag=value format for parameters, flags with arguments
        argList = [self.command, ]
        for name, value in self.arguments.items():
            argString = name
            if value is not None:
                argString += "=" + value
            argList.append(argString)
        return tuple(argList)

    def run(self, background: bool=False):
        sub = Popen(self.getArgList(), stdout=PIPE, stderr=STDOUT)
        output, error_message = sub.communicate()
        return output.decode('utf-8')

    def __str__(self):
        return str(self.__dict__)

    def list(self):
        print("\nTool:\t" + self.name)
        print("\tDescription:\t" + self.description)
        print("\tCommand:\t\t" + self.command)
        print("\tArguments:")
        for name, value in self.arguments.items():
            if value is None:           #   This is a flag.  It has no argument
                print("\t\t" + name + ":\t\t[flag]")
            else:                       #   This is a parameter.
                                        #   It has an argument which will always be stored as a string
                print("\t\t" + name + ":\t" + value)


class ToolSet:

    registry = OrderedDict()

    def __init__(self, name: str):
        self.timeStamp = datetime.now()
        ToolSet.checkName(name)
        self.name = name
        self.toolMap = OrderedDict()
        ToolSet.registry[name] = self

    def addTool(self, name: str, tool: Tool):
        if name not in self.toolMap:
            self.toolMap[name] = deepcopy(tool)
            return tool
        return None

    def removeTool(self, name: str):
        if name in self.toolMap:
            tool = self.toolMap[name]
            del(self.toolMap[name])
            return tool
        return None

    def getToolMap(self):
        return self.toolMap

    @staticmethod
    def checkName(name: str):
        if not isinstance(name, str) or name in ToolSet.registry:
            raise Exception("ToolSet constructor - Invalid name argument:  " + str(name))


class ToolManager:

    __record  = OrderedDict()
    __DBFile    = "LinuxTools.db"
    ToolMap = OrderedDict()
    __ChangeMap = OrderedDict()

    def __init__(self):
        pass

    @staticmethod
    def addTool(tool: Tool):
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+ToolManager.__DBFile)
        cursor = connection.cursor()
        info = dumps(tool.arguments)
        cursor.execute('''INSERT INTO Tools( timeStamp, Name, Description, LinuxCommand, Arguments ) 
                        VALUES( ?, ?, ?, ?, ? )''',
                       (tool.timeStamp, tool.name, tool.description, tool.command, Binary(info)))
        connection.commit()
        cursor.close()
        connection.close()

    @staticmethod
    def toolExists(toolName: str):
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+ToolManager.__DBFile)
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM [Tools] WHERE Name='{toolName}'""".format(toolName=toolName))
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return len(rows) > 0

    @staticmethod
    def removeTool(name: str):
        pass

    @staticmethod
    def getTool(name: str):
        pass

    @staticmethod
    def readDB():
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+ToolManager.__DBFile)
        cursor = connection.cursor()

        toolMap = OrderedDict()
        cursor.execute("""SELECT * FROM Tools""")
        rows = cursor.fetchall()
        for row in rows:
            arguments = loads(row[5])
            toolMap[row[2]] = Tool(row[2], row[3], row[4], arguments)

        toolSetIndex = OrderedDict()
        cursor.execute("""SELECT * FROM ToolSetIndex""")
        rows = cursor.fetchall()
        for row in rows:
            if row[1] not in toolSetIndex:
                toolSetIndex[row[1]] = []
            toolSetIndex[row[1]].append(row[2])
        for toolSetName in toolSetIndex:
            toolSetIndex[toolSetName] = tuple(toolSetIndex[toolSetName])

        cursor.close()
        connection.close()
        return toolMap, toolSetIndex


    @staticmethod
    def writeDB():
        pass

    @staticmethod
    def mergeFromDB():
        pass

    @staticmethod
    def updateDB():
        pass

    @staticmethod
    def createLinuxToolsDB():
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+ToolManager.__DBFile)
        cursor = connection.cursor()
        cursor.execute("""CREATE TABLE `Events` ( 
                            `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                            `timeStamp` TEXT NOT NULL, 
                            `info` BLOB NOT NULL )""")
        cursor.execute("""CREATE TABLE "Tools" ( 
                            `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                            `timeStamp` TEXT NOT NULL, 
                            `Name` TEXT NOT NULL, 
                            `Description` TEXT NOT NULL, 
                            `LinuxCommand` TEXT NOT NULL, 
                            `Arguments` BLOB NOT NULL )""")
        cursor.execute("""CREATE TABLE "ToolSetIndex" ( 
                            `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                            `ToolSetName` TEXT NOT NULL, 
                            `ToolName` TEXT NOT NULL )""")
        connection.commit()

        #   Initial tool set (Same as those in Tool menu in Console)

        #   'journalctl --system --lines=1000 -o json'
        #   Rule: if the instructions indlude an '=' for an argument, it may or may not be required.
        #   Always include it and test for the '=' at the end of the flag name to determine whether to separate
        #   the flag from the argument with and '=' or with a space.

        tools = []

        #   JOURNALS
        tools.append(Tool("System Journal - 1000 Lines", "Show the first 1000 lines of the system activity "
                                                                "journal, meaning most recent 1000 "
                                                              "events recorded in the system journal in JSON format",
                               "journalctl", OrderedDict({"--system": None, "--lines=": "1000", "-o": "json"})))
        tools.append( Tool("User Journal - 1000 Lines", "Show the first 1000 lines of the user's activity"
                                                              "journal, meaning most recent 1000 "
                                                              "events recorded in the user's journal in JSON format",
                               "journalctl", OrderedDict({"--user": None, "--lines=": "1000", "-o": "json"})))
        tools.append( Tool("dmesg Journal - 1000 Lines", "Show the first 1000 lines of the dmesg activity"
                                                              "journal, meaning most recent 1000 "
                                                              "events recorded in the dmesg journal in JSON format",
                               "journalctl", OrderedDict({"--dmesg": None, "--lines=": "1000", "-o": "json"})))

        #   PACKAGES
        tools.append( Tool('dpkg Help', 'Show the simple help output of the dpkg program', 'dpkg',
                        OrderedDict({'--help': None})))
        tools.append( Tool('dpkg Package Table', 'Tabular list of all installed packages', 'dpkg',
                        OrderedDict({'-l': None})))
        #   The argument syntax of the following two commands will cause a filterable list of selections to be
        #   displayed with multiple selection styles.
        tools.append( Tool('dpkg Integrity Check', 'Verify the integrity of package(s)', 'sudo dpkg',
                        OrderedDict({'--verify': "[<package>, ...]"})))
        tools.append( Tool('dpkg Broken Package Check', 'Check for broken package(s)', 'sudo dpkg',
                        OrderedDict({'--audit': "[<package>, ...]"})))

        #   PROCESSES
        tools.append( Tool('Process Help - Verbose', 'Display verbose help for the ps command', 'ps',
                        OrderedDict({'--help': "all"})))
        tools.append( Tool('User\'s Processes', 'Running processes of a specified user', 'ps',
                        OrderedDict({'-lf': None, '-u': "<user name>"})))
        tools.append( Tool('Active Processes', 'List active processes in generic Unix format', 'ps',
                        OrderedDict({'-lf': None, '-A': None})))
        tools.append( Tool('Terminal Processes', 'List active processes launched from a terminal', 'ps',
                        OrderedDict({'-lf': None, '-T': None})))
        tools.append( Tool('Processes + Their Children', 'Filter by process name and show children', 'ps',
                        OrderedDict({'-lf': None, '-C': None})))

        toolSet = ToolSet("Tools in Initial Installation")
        for tool in tools:
            arguments = dumps(tool.arguments)
            timeStamp = tool.timeStamp
            timeStampStr    = "{year:4d}/{month:2d}/{day:2d}" \
                    .format(year=timeStamp.year, month=timeStamp.month, day=timeStamp.day).replace(' ', '0') + ' ' + \
                       "{hour:2d}:{minute:2d}:{second:2d}.{micro:6d}" \
                           .format(hour=timeStamp.hour, minute=timeStamp.minute, second=timeStamp.second,
                                   micro=timeStamp.microsecond).replace(' ', '0')
            cursor.execute('''INSERT INTO Tools( timeStamp, Name, Description, LinuxCommand, Arguments ) 
                                VALUES( ?, ?, ?, ?, ?)''', (timeStampStr, tool.name, tool.description,
                                                            tool.command, Binary(arguments)))
            toolSet.addTool(tool.name, tool)
        for toolName in toolSet.toolMap:
            toolSet.name, toolName
            cursor.execute('''INSERT INTO ToolSetIndex( ToolSetName, ToolName ) VALUES( ?, ?)''',
                           (toolSet.name, toolName))
        connection.commit()
        cursor.close()
        connection.close()

    @staticmethod
    def exportTools(format: ExportFormat, filePath: str, verbose: bool=False):
        """
        Write the tool set to a file which is independent of this program.
        One reason to do this is to do networking without the program running, so that it remains isolated from
        potential network invasion.
        Text format simply lists the commands as they would be typed into the Linux terminal.
        A simple copy and paste is required to run the command.
        :param format: The export file format
        :param filePath: The full absolute path of the file to write to
        :param verbose: Whether to include the complete set of tool definition information in the output.
        :return:
        """
        pass


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":

    toolSet = None
    if INSTALLING:
        toolSet = ToolManager.createLinuxToolsDB()
        exit(0)

    if TESTING:
        dpkgTool = Tool('dpkgHelp', 'Show the simple help output of the dpkg program', 'dpkg',
                        OrderedDict({'--help': None}))
        dpkgTool.list()
        print("\nTool - " + dpkgTool.getName() + ":\t" + str(dpkgTool.getArgList()))
        print("\t" + dpkgTool.getDescription())
        print("\nOutput:\n" + dpkgTool.run())
        print()

        toolMap, toolSetIndex = ToolManager.readDB()
        print("Tools read from DB:")
        for name, tool in toolMap.items():
            print("\t" + name + ":\t" + str(tool))
        exit(0)

    print(__doc__)

    mainView = Tk()
    mainView.geometry("700x400+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())
    mainView.mainloop()
