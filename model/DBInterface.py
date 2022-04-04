#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   July 12, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         model/DBInterface.py
#   Purpose:        Provide interface to SQLite database which can be used for various analytics on log
#                   message sequences.
#   Development:
#

import os
import sqlite3
import datetime
import json
from copy import deepcopy
import re
from os.path import isfile
from collections import OrderedDict
from enum import Enum

from tkinter import Tk, Menu, messagebox

from view import Menus
from model.Installation import INSTALLATION_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB, pathFromList

#   Circular dependency created by:
#   from model.Util import pathFromList, INSTALLATION_FOLDER, APP_DATA_FOLDER, DATABASE_INDEX_FILE
DATABASE_INDEX_FILE     = '/home/keith/PycharmProjects/LinuxLogReader' + '/' + 'data' + '/' + 'db_index.txt'


def isValidIdentifier(name: str, quoted: bool=True):
    legalFieldNameChars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
    digits = "0123456789"
    print("isValidIdentifier?:\t" + name)
    if quoted:
        return name is not None and isinstance(name, str) and not name.lower().startswith("sqlite_")
    elif name is not None:
        if name[0: 1] not in legalFieldNameChars:
            return False
        charIdx = 1
        passing = True
        while passing and charIdx < len(name):
            passing = name[charIdx: charIdx+1] in legalFieldNameChars or \
                      name[charIdx: charIdx+1] in digits
            charIdx += 1
        return passing
    else:
        return False


class DBTable:
    pass


class TableAttrib(Enum):
    NAME        = 'Name'
    TABLE_TYPE  = 'Table Type'
    TABLE_NAME  = 'Table Name'
    CREATE_SQL  = 'Create SQL'
    ROOT_PAGE   = 'Root Page'

    def __str__(self):
        return self.value


class ColumnAttrib(Enum):
    TYPE            = 'Type'
    INDEX           = 'Index'
    NAME            = 'Name'
    NO_NULLS        = 'Nulls not Allowed'
    DEFAULT_VALUE   = 'Default Value'
    PRIMARY_KEY_IDX = 'Primary Key Index'

    def __str__(self):
        return self.value


class FieldDefSQLite:
    """
    Immutable and extendable field definition.

    SQLite3 Documentation at www.sqlite.org/datatype3.html:

    Type Conversions:
    "Any column in an SQLite version 3 database, except an INTEGER PRIMARY KEY column, may be used to store
    a value of any storage class."

    Date and Time SQLite3 native formats:
        * TEXT as ISO8601 strings ("YYYY-MM-DD HH:NN:SS.SSS")  [resolution in mine is micro-seconds)
        * REAL as Julian day numbers, the number of days since noon in Greenwich on November 24, 4714 B.C.
            according to the (epi)proleptic Gregorian calendar.
        * INTEGER as Unix time, the number of seconds since 1970-01-01 00:00:oo UTC.
    None of these is adequate for log entry time stamps since even when measured in microseconds key collisions
    can occur.  They are usable for other purposes and can be relied on for efficiency in coding the application
    level.
    """

    STORAGE_CLASSES = ("NULL", "NUMERIC", "INTEGER", "REAL", "TEXT", "BLOB")
    STORAGE_TYPES    = ("DATETIME", "DATE", "BOOLEAN", "NUMERIC", "NATIVE",
                        "INTEGER", "INT", "TINYINT", "SMALLINT",  "MEDIUMINT", "BIGINT", "UNSIGNED BIG",
                        "INT2",  "INT8",
                        "REAL", "FLOAT", "DOUBLE", "DECIMAL", "PRECISION",
                        "TEXT", "CHAR", "CLOB", "BLOB",
                        "VARCHAR", "CHARACTER", "NCHAR", "NVARCHAR" )   #   (length) specifiers allowed
    SORT_ORDERS     = ("ASC", "DESC")
    GENERATE_TYPES  = ("STORED", "VIRTUAL")

    def __init__(self, fieldName: str, storageType: str, size: int, isKey: bool, isUnique: bool, nullsNotAllowed: bool,
                 isPrimary: bool, autoincrement: bool, sortOrder: str, defaultValue: str, collateName: str,
                 foreignKeyClause: str, isGenerated: bool, generateExpression: str, generateType: str,
                 **keyWordArguments):
        #   ALL FIELDS SHOULD BE VALIDATED
        print("FieldDefSQLite - storageType:\t" + storageType)
        if fieldName is None or not isinstance(fieldName, str) or not isValidIdentifier(fieldName):
            raise Exception('FieldDefSQLite constructor - invalid fieldName argument:  ' + str(fieldName))
        if storageType is None or not isinstance(storageType, str) or storageType not in FieldDefSQLite.STORAGE_TYPES:
            raise Exception('FieldDefSQLite constructor - invalid storageType argument:  ' + str(storageType))
        if size is not None and not isinstance(size, int):
            raise Exception('FieldDefSQLite constructor - invalid size argument:  ' + str(size))
        if isKey is not None and not isinstance(isKey, bool):
            raise Exception('FieldDefSQLite constructor - invalid isKey argument:  ' + str(isKey))
        if isUnique is not None and not isinstance(isUnique, bool):
            raise Exception('FieldDefSQLite constructor - invalid isUnique argument:  ' + str(isUnique))
        if nullsNotAllowed is not None and not isinstance(nullsNotAllowed, bool):
            raise Exception('FieldDefSQLite constructor - invalid nullsNotAllowed argument:  ' + str(nullsNotAllowed))
        if isPrimary is not None and not isinstance(isPrimary, bool):
            raise Exception('FieldDefSQLite constructor - invalid isPrimary argument:  ' + str(isPrimary))
        if autoincrement is not None and not isinstance(autoincrement, bool):
            raise Exception('FieldDefSQLite constructor - invalid autoincrement argument:  ' + str(autoincrement))
        if sortOrder is not None and not isinstance(sortOrder, str) or sortOrder not in FieldDefSQLite.SORT_ORDERS:
            raise Exception('FieldDefSQLite constructor - invalid sortOrder argument:  ' + str(sortOrder))
        if collateName is not None and not isinstance(collateName, str):
            raise Exception('FieldDefSQLite constructor - invalid collateName argument:  ' + str(collateName))
        if foreignKeyClause is not None and not isinstance(foreignKeyClause, str):
            raise Exception('FieldDefSQLite constructor - invalid foreignKeyClause argument:  ' + str(foreignKeyClause))
        if isGenerated is not None and not isinstance(isGenerated, bool):
            raise Exception('FieldDefSQLite constructor - invalid isGenerated argument:  ' + str(isGenerated))
        if generateExpression is not None and not isinstance(generateExpression, int):
            raise Exception('FieldDefSQLite constructor - invalid generateExpression argument:  ' + str(generateExpression))
        if generateType is not None and not isinstance(generateType, int):
            raise Exception('FieldDefSQLite constructor - invalid generateType argument:  ' + str(generateType))

        self.fieldName = fieldName
        self.storageType  = storageType
        self.size = size
        self.isKey = isKey
        self.isUnique = isUnique
        self.nullsNotAllowed = nullsNotAllowed
        self.isPrimary = isPrimary
        self.autoincrement  = autoincrement
        self.sortOrder = sortOrder
        self.defaultValue = defaultValue
        self.collateName = collateName
        self.foreignKeyClause = foreignKeyClause
        self.isGenerated = isGenerated
        self.generateExpression = generateExpression
        self.generateType = generateType

        for name, value in keyWordArguments.items():
            self.__dict__[name] = value

    def __setattr__(self, key, value):
        #   print("__setattr__:  assiging, " + str(value) + " to " + key)
        if key not in self.__dict__:
            self.__dict__[key] = value

    def __str__(self):
        text = ""

        return text

    def list(self):
        print("\nFieldDefSQLite:\t" + self.fieldName)
        print("\tstorageType:\t" + str(self.storageType))
        print("\tsize:\t" + str(self.size))
        print("\tisKey:\t" + str(self.isKey))
        print("\tisUnique:\t" + str(self.isUnique))
        print("\tnullsNotAllowed:\t" + str(self.nullsNotAllowed))
        print("\tisPrimary:\t" + str(self.isPrimary))
        print("\tautoincrement:\t" + str(self.autoincrement))
        print("\tsortOrder:\t" + str(self.sortOrder))
        print("\tdefaultValue:\t" + str(self.defaultValue))
        print("\tcollateName:\t" + str(self.collateName))
        print("\tforeignKeyClause:\t" + str(self.foreignKeyClause))
        print("\tisGenerated:\t" + str(self.isGenerated))
        print("\tgenerateExpression:\t" + str(self.generateExpression))
        print("\tgenerateType:\t" + str(self.generateType))


class TableDefSQLite:

    TEMP_KEY_WORDS = ("TEMP", "TEMPORARY")

    def __init__(self, databaseName: str, tableName: str, fieldDefinitions: tuple, temp: str, ifNotExists: bool,
                 schemaName: str, asSelectStmt: str, withoutRowId: bool, **keyWordArguments):
        """

        :param databaseName:        File specification with full path of database file.
                                    Must already exist and be an SQLite database.
        :param tableName:           Does not need to exist yet.
        :param fieldDefinitions:    list of field definition json/map/dict objects.
        :param temp:
        :param ifNotExists:
        :param schemaName:
        :param asSelectStmt:
        :param withoutRowId:
        """
        if databaseName is None or not isinstance(databaseName, str) or not self.isValidDatabaseName(databaseName):
            raise Exception('TableDefSQLite constructor - invalid databaseName argument:   ' + str(databaseName))
        if tableName is None or not isinstance(tableName, str) or not isValidIdentifier(tableName):
            raise Exception('TableDefSQLite constructor - invalid databaseName argument:   ' + str(tableName))
        if fieldDefinitions is None or (not isinstance(fieldDefinitions, list) and not isinstance(fieldDefinitions, tuple)):
            raise Exception('TableDefSQLite constructor - invalid fieldDefinitions argument:   ' + str(fieldDefinitions))
        for fieldDefinition in fieldDefinitions:
            if fieldDefinition is None or not isinstance(fieldDefinition, FieldDefSQLite):
                raise Exception('TableDefSQLite constructor - invalid fieldDefinitions argument:   ' + str(fieldDefinitions))
        if temp is not None and (not isinstance(temp, str) or temp not in TableDefSQLite.TEMP_KEY_WORDS):
            raise Exception('TableDefSQLite constructor - invalid temp argument:   ' + str(temp))
        if ifNotExists is not None and not isinstance(ifNotExists, bool):
            raise Exception('TableDefSQLite constructor - invalid ifNotExists argument:   ' + str(ifNotExists))
        if schemaName is not None and not isinstance(schemaName, str):
            raise Exception('TableDefSQLite constructor - invalid schemaName argument:   ' + str(schemaName))
        if asSelectStmt is not None and not isinstance(asSelectStmt, str):
            raise Exception('TableDefSQLite constructor - invalid asSelectStmt argument:   ' + str(asSelectStmt))
        if withoutRowId is not None and not isinstance(withoutRowId, bool):
            raise Exception('TableDefSQLite constructor - invalid withoutRowId argument:   ' + str(withoutRowId))

        self.databaseName = databaseName
        self.tableName = tableName
        self.fieldDefinitions = deepcopy(fieldDefinitions)
        self.temp           = temp
        self.ifNotExists    = ifNotExists
        self.schemaName     = schemaName
        self.asSelectStmt   = asSelectStmt
        self.withoutRowId   = withoutRowId
        for name, value in keyWordArguments.items():
            self.__dict__[name] = value

    def addFieldDefinition(self, fieldDefinition: dict):
        pass

    def isValidDatabaseName(self, databaseName: str):
        return True

    def __setattr__(self, key, value):
        if key not in self.__dict__:
            self.__dict__[key] = value


class TableData:

    def __init__(self, tableDefinition: TableDefSQLite, data: list):
        """

        :param tableDefinition:
        :param data:                a list of table rows, each of which is a json with non null fields present
        """
        pass


class ConsoleImport:

    def __init__(self):
        pass


def savePs_lf_A_OutputToDB(self, argv, consoleOutput):
    #   Field Names:    F S   UID     PID    PPID  C PRI  NI ADDR SZ WCHAN  TTY          TIME CMD
    outputLines = consoleOutput.split('\n')
    fieldNameList   = tuple(outputLines[0].split())
    print('fieldNameList:\t' + str(fieldNameList))
    del(outputLines[0])
    #   PID is the key since process id is always unique.  Its index in the row token list is 3
    index = []
    tableRows = {}
    for line in outputLines:
        #   print('line:\t' + line)
        tokens = line.split()
        if len(tokens) == 0:
            break
        #   everything from column index 14 on ia part of the command field the first token of which is at
        #       tokens[14]
        command = ''
        colIdx = 14
        while colIdx < len(tokens):
            command += tokens[colIdx]
            if colIdx < len(tokens) - 1:
                command += ' '
            colIdx += 1
        tokens[14] = command
        colIdx = len(tokens) - 1
        while colIdx > 14:
            del( tokens[colIdx])
            colIdx -= 1
        tokens = tuple(tokens)

        print('row:\t' + str(tokens))
        if len(tokens) != len(fieldNameList):
            raise Exception("ConsoleMenuBar.savePs_l_A_OutputToDB - record length does not match heading count:\t" + str(tokens))
        index.append(tokens[3])
        tableRows[tokens[3]] = {}
        fieldIdx = 0
        while fieldIdx < len(fieldNameList):
            tableRows[tokens[3]][fieldNameList[fieldIdx]] = tokens[fieldIdx]
            fieldIdx += 1

    tableName = ''
    commandLine = ''
    for arg in argv:
        tableName += arg.replace('-', '_')
        commandLine += arg + ' '
    userName = os.environ["USER"]
    accessRights = userName

    dbMetaData = DBMetaData_SQLite(pathFromList((INSTALLATION_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB)))
    connection = sqlite3.connect(pathFromList((INSTALLATION_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB)))
    cursor = connection.cursor()

    #   Check to see if a table with the same name already exists in USER_CONSOLE_OUT_DB
    if not tableName in dbMetaData.tableNames:
        #   F  S  UID  PID  PPID  C  PRI  NI  ADDR  SZ  WCHAN  TTY  TIME  CMD
        cursor.execute("CREATE TABLE " + tableName + " (rowId INTEGER PRIMARY KEY AUTOINCREMENT, "
                                                     "runTimeStamp TEXT KEY NOT NULL, "
                                                     "F TEXT NOT NULL, S TEXT NOT NULL, UID TEXT NOT NULL,"
                                                     "PID TEXT KEY NOT NULL, PPID TEXT NOT NULL,"
                                                     "C TEXT NOT NULL, PRI TEXT NOT NULL, NI TEXT NOT NULL,"
                                                     "ADDR TEXT NOT NULL, SZ TEXT NOT NULL, WCHAN TEXT NOT NULL,"
                                                     "TTY TEXT NOT NULL, TIME TEXT NOT NULL, CMD TEXT NOT NULL)")

        #   Second, add an entry in the DB's table index for the new table.
        tableCreateTimeStamp    = str(datetime.datetime.now())
        cursor.execute('''INSERT INTO DBSchema (tableName, commandLine, creationTimeStamp, owner, 
                            creatorAppName, accessRights) VALUES(?,?,?,?,?,?)''',
                       (tableName, commandLine, tableCreateTimeStamp, userName,
                        "LinuxLogReader.view.Console", accessRights))

    for processId, processRecord in tableRows.items():
        cursor.execute(
            "INSERT INTO " + tableName + " (runTimeStamp, F, S, UID, PID, PPID, C, PRI, NI, ADDR, SZ, WCHAN, TTY, TIME, CMD) "
                                         "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (str(self.consoleView.lastCommandRunTime), processRecord['F'], processRecord['S'], processRecord['UID'],
             processRecord['PID'], processRecord['PPID'],
             processRecord['C'], processRecord['PRI'], processRecord['NI'], processRecord['ADDR'], processRecord['SZ'],
             processRecord['WCHAN'], processRecord['TTY'], processRecord['TIME'], processRecord['CMD'], ))

    connection.commit()
    connection.close()
    connection = None


def inferJournalAttrType(name: str, value: str):
    match = re.search('\d+', value)  # test for integer type string
    if match is not None and match.span()[1] == len(value):
        if 'TIMESTAMP' in name.upper():
            #   ISSUE:
            #   Need to check for different time formats, not just an integer
            #   e.g. 'SYSLOG_TIMESTAMP': 'Aug 20 20:21:36 '
            #   See:    www.programiz.com/python-programming/datetime/strptime
            #           www.docs.python.org/3/library/datetime.html
            #   Also need to check for scale if it is an integer.  Does it make sense as a microsecond, milisecond,
            #       or second measure since 1970-01-01 00:00:00???
            #
            #   ISSUE:
            #   There are 113 different field names in this omni-log which aggregates, according to the documentation
            #   for journalctl, from all of the various log entry producers.
            #   Can these be distinguished using:
            #   *   the count of field names?
            #   *   then comparing the set of field names of entries with the same count?
            #
            return 'microEpochTimeStamp'  # i.e. microseconds since 1970-01-01 00:00:00
        else:
            return 'Integer'
    else:
        match = re.search('[0-9A-Fa-f]+', value)  # test for hexadecimal type string
        if match is not None and match.span()[1] == len(value):
            return "Hexadecimal"
        else:
            attributeList = value.split(';')
            for attribute in attributeList:
                expression = attribute.split('=')
                if len(expression) == 2:
                    match = re.search('[0-9A-Fa-f]+', expression[1])  # test for hexadecimal type string
                    if match is not None and match.span()[1] == len(expression[1]):
                        return "HexAttrList"
    return "String"


def journalctl_o_json_OutputToDB(argv, consoleOutput):

    VALID_HEX_DIGITS = '01234567890abcdefABCDEF'

    print("journalctl_o_json_OutputToDB:\t" + str(argv))
    #   consoleOutput is a list of log entry json texts
    jsonLines = consoleOutput.split("\n")
    print("first log entry JSON:\t" + str(jsonLines[0]))
    jsonList = []
    #   Scan json/map/dict lines for field names and build a complete list with type inference
    fieldList = {}
    fieldCount = 0
    typedFieldCOunt = 0
    for line in jsonLines:
        if len(line.strip()) > 1:
            logRecord = json.loads(line)
            fieldCount += len(logRecord)
            print(str(logRecord))
            jsonList.append(logRecord)
            #   print("Log Entry Field Count:\t" + str(len(logRecord.keys())))
            for name, value in logRecord.items():
                if name not in fieldList:
                    #   Assuming all fields with the same name are the same type, a single sample might be sufficient
                    #   for type inference.
                    fieldList[name] = inferJournalAttrType(name, value)
                else:
                    attrType = inferJournalAttrType(name, value)
                    if attrType != fieldList[name]:
                        fieldList[name] = 'String'

    print("\njournalctl field list (count=" + str(len(fieldList)) + ") :\t" + str(fieldList))
    print("Field Count:\t" + str(fieldCount))
    """
    Types Present:  Hexadecimal Number (as string)
                    String
                    Lists of Hexadecimal Number assignments separate by semicolons (as a single string)
                        e.g.: '__CURSOR': 's=ccca7175801544a49c99669b8209416b;i=b887;b=555fccea76ea4b1e98b0a49cb51fbd72;m=1aff636;t=5ca079a85f26d;x=8c61b5c16ba5e63a'
                    Integer (as string)
                    "TIMESTAMP" in name with Integer (as string) which is microseconds since new epoch, January 1, 1970
                            at 00:00:00
                    
    """


def saveDpkg_l_OutputToDB(self, argv, consoleOutput):

    #   This assumes that there is a header which ends with a line of '======'
    #   If the termination line is not found, it trims at most 10 lines from the top.
    #   The first three lines appear to be the internal default settings of th dpkg command.
    #   This needs research.
    outputLines = consoleOutput.split('\n')
    lineIdx = 0
    while not outputLines[0].endswith("==============================") and lineIdx < 10:
        del (outputLines[0])
        lineIdx += 1
    if lineIdx < 10:
        del (outputLines[0])

    index = []
    tableRows = {}
    for line in outputLines:
        #   print('line:\t' + line)
        tokens = line.split()
        #   print('\ttokens:\t' + str(tokens))
        if len(tokens) > 0:
            del (tokens[0])
            description = ''
            tokenIdx = 3
            while tokenIdx < len(tokens):
                description += tokens[tokenIdx] + ' '
                tokenIdx += 1
            index.append(tokens[0])
            #   This needs to be updated each time with the current list of allowed architectures since
            #   dpkg can be used to change this.
            #   if tokens[2] not in ['all', 'amd64', 'i386']:
            #       raise Exception('Parse of dpkg -l output: invalid Architecture field:\t' + tokens[2])
            tableRows[tokens[0]] = {'Name': tokens[0],
                                    'Version': tokens[1],
                                    'Architecture': tokens[2],
                                    'Description': description}

    #   First, create a table for the command (argv) if one does not yet exist.

    #   PROBLEM: Ordering of arguments can be different for commands with exactly tne same arguments.
    #   Encourage user to be consistent.
    #   Also develop a class which recognized the arguments of each command and has a __str__() override
    #   that places them i a canonical order.
    tableName = ''
    commandLine = ''
    for arg in argv:
        tableName += arg.replace('-', '_')
        commandLine += arg + ' '
    userName = os.environ["USER"]
    accessRights = userName

    dbMetaData = DBMetaData_SQLite(pathFromList((INSTALLATION_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB)))
    connection = sqlite3.connect(pathFromList((INSTALLATION_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB)))
    cursor = connection.cursor()

    #   Check to see if a table with the same name already exists in USER_CONSOLE_OUT_DB
    if not tableName in dbMetaData.tableNames:
        cursor.execute("CREATE TABLE " + tableName + " (rowId INTEGER PRIMARY KEY AUTOINCREMENT, "
                                                     "runTimeStamp TEXT KEY NOT NULL, packageName TEXT KEY NOT NULL, version TEXT NOT NULL,"
                                                     "architecture TEXT KEY, description TEXT)")

        #   Second, add an entry in the DB's table index for the new table.
        tableCreateTimeStamp    = str(datetime.now())
        cursor.execute('''INSERT INTO DBSchema (tableName, commandLine, creationTimeStamp, owner, 
                            creatorAppName, accessRights) VALUES(?,?,?,?,?,?)''',
                       (tableName, commandLine, tableCreateTimeStamp, userName,
                        "LinuxLogReader.view.Console", accessRights))

    #   Third, add the command output rows to the new table.
    for packageName, packageRecord in tableRows.items():
        cursor.execute(
            "INSERT INTO " + tableName + " (runTimeStamp, packageName, version, architecture, description) VALUES(?,?,?,?,?)",
            (str(self.consoleView.lastCommandRunTime), packageRecord["Name"], packageRecord["Version"],
             packageRecord["Architecture"], packageRecord["Description"]))

    connection.commit()
    connection.close()
    connection = None


class DBManager_SQLite:

    def __init__(self):
        self.dbsSelected = {}
        self.tablesSelected = {}

        #   Linux Only Path Used Here: Could use os.path
        self.dbIndexFileName   = DATABASE_INDEX_FILE
        if not os.path.isfile(self.dbIndexFileName):
            fd  = open(self.dbIndexFileName, 'w')
            fd.close()

    def importConsoleOutput(self, tableDefinition: TableDefSQLite):
        pass

    def selectDB(self):
        messagebox.showinfo('selectDB', "not implemented yet")

    def closeDB(self):
        messagebox.showinfo('closeDB', "not implemented yet")

    def selectTable(self):
        messagebox.showinfo('selectTable', "not implemented yet")

    def showTable(self):
        messagebox.showinfo('showTable', "not implemented yet")

    def showSelectedTables(self):
        messagebox.showinfo('showSelectedTables', "not implemented yet")

    def showSelectedDatabases(self):
        messagebox.showinfo('showSelectedDatabases', "not implemented yet")

    def showDBMetaData(self):
        messagebox.showinfo('showDBMetaData', "not implemented yet")

    def showTableMetaData(self):
        messagebox.showinfo('showTableMetaData', "not implemented yet")


class TableDescriptor:

    registry = OrderedDict()

    def __init__(self, databaseName: str, databasePath: str, tableName: str):
        """
        Perform security and integrity checks on a table requested before using and collect its meta data.
        :param databaseName:
        :param databasePath:
        :param tableName:
        """
        print("\nTableDescriptor constructor is running")
        if databaseName is None or not isinstance(databaseName, str):
            raise Exception('TableDescriptor constructor - invalid databaseName argument:    ' + str(databaseName))
        if databasePath is None or not isinstance(databasePath, str) or not isfile(databasePath):
            raise Exception('TableDescriptor constructor - invalid databasePath argument:    ' + str(databasePath))
        if tableName is None or not isinstance(tableName, str):
            raise Exception('TableDescriptor constructor - invalid tableName argument:    ' + str(tableName))
        #   Open database and check to see table exists, then record its column data:

        self.databaseName   = databaseName
        self.databasePath   = databasePath
        self.tableName      = tableName

        database = sqlite3.connect(self.databasePath)
        cursor = database.cursor()
        cursor.execute('''SELECT * FROM sqlite_master WHERE type=\'table\' AND name=? ORDER BY name''', (self.tableName,))

        self.tableInfo = OrderedDict()
        for row in cursor:
            print("\t" + str(row))
            if self.tableName == row[2]:
                self.tableInfo[TableAttrib.NAME]          = row[1]
                self.tableInfo[TableAttrib.TABLE_TYPE]     = row[0]
                self.tableInfo[TableAttrib.TABLE_NAME]     = row[2]
                self.tableInfo[TableAttrib.CREATE_SQL]     = row[4]
                self.tableInfo[TableAttrib.ROOT_PAGE]      = row[3]
                break

        self.tableInfo['columns']   = OrderedDict()

        self.columnIndex    = OrderedDict()

        cursor.execute('''PRAGMA table_info("{table}")'''.format(table=tableName))
        for definition in cursor:
            self.tableInfo['columns'][definition[1]] = {
                ColumnAttrib.INDEX: definition[0],
                ColumnAttrib.NAME: definition[1],
                ColumnAttrib.TYPE: definition[2],
                ColumnAttrib.NO_NULLS: definition[3],
                ColumnAttrib.DEFAULT_VALUE: definition[4],
                ColumnAttrib.PRIMARY_KEY_IDX: definition[5],
            }
        cursor.close()
        database.close()
        self.db_id  = self.databasePath + "::" + self.tableName
        TableDescriptor.registry[self.db_id]    = self

    def getDatabaseName(self):
        return self.databaseName

    def getDatabasePath(self):
        return self.databasePath

    def getTtableName(self):
        return self.tableName

    def getTableInfo(self):
        return self.tableInfo

    def getColumnInfo(self):
        return None


class DBMetaData_SQLite:
    """
    This is designed currently exclusively for SQLite databases only.
    SQWLite is the native Python database engine.
    Naming of other database meta data classes will include the particular database engine they are intended for
    importation of databases from.
    Viewers and other modules can include testing of the type of the DBMetaData structure to determine its internal
    structure.
    """

    #   WORKING HERE
    #   Question:  Where to insert column length / size data in the meta-data structure after DB table is read in.
    #               This could perhaps be done generically based on the column type and the values stored.
    #               The maximum numeric value can be found along with the maximum text or varchar value length.

    def __init__(self, dbFileName: str):
        """

        :param dbFileName:
        """
        if dbFileName is None or not isinstance(dbFileName, str) or not isfile(dbFileName):
            raise Exception('DBMetaData constructor - invalid dbFileName argument:    ' + str(dbFileName))
        #   print('Reading Database:\t' + dbFileName)
        self.dbFileName = dbFileName
        database = sqlite3.connect(self.dbFileName)
        cursor = database.cursor()
        self.tables = {}
        self.tableNames = []

        #   print('Looking at the meta data:\t' + self.dbFileName)
        cursor.execute('SELECT * FROM sqlite_master WHERE type=\'table\' ORDER BY name')
        #   This can return index definition rows as well
        for row in cursor:
            tableName   = row[2]
            self.tables[tableName]  = {}
            self.tables[tableName][TableAttrib.TABLE_TYPE]     = row[0]
            self.tables[tableName][TableAttrib.NAME]          = row[1]
            self.tables[tableName][TableAttrib.TABLE_NAME]     = row[2]
            self.tables[tableName][TableAttrib.ROOT_PAGE]      = row[3]
            self.tables[tableName][TableAttrib.CREATE_SQL]     = row[4]
            self.tableNames.append(tableName)
        self.tableNames     = tuple(self.tableNames)

        #   now a table's metadata
        if len(self.tables) > 0:
            for tableName, definition in self.tables.items():
                cursor.execute('''PRAGMA table_info("{table}")'''.format(table=tableName))

                self.tables[tableName]['columns']   = {}
                columnNameIndex = []
                for definition in cursor:
                    #   print(definition)
                    columnNameIndex.append(definition[1])
                    self.tables[tableName]['columns'][definition[1]] = {
                        ColumnAttrib.INDEX: definition[0],
                        ColumnAttrib.NAME: definition[1],
                        ColumnAttrib.TYPE: definition[2],
                        ColumnAttrib.NO_NULLS: definition[3],
                        ColumnAttrib.DEFAULT_VALUE: definition[4],
                        ColumnAttrib.PRIMARY_KEY_IDX: definition[5],
                    }
                self.tables[tableName]['columnNameIndex'] = columnNameIndex
        database.close()

    def getDbFileName(self):
        return self.dbFileName

    def getTables(self):
        return self.tables

    def getTableNames(self):
        return self.tableNames

    @staticmethod
    def tableExists(dbFilePath: str, tableName: str):
        if not isinstance(dbFilePath, str):
            return False
        if not isfile(dbFilePath):
            return False
        if not isinstance(tableName, str):
            return False
        try:
            connection = sqlite3.connect(dbFilePath)
            cursor = connection.cursor()
            cursor.execute('''SELECT name FROM sqlite_master WHERE type='table' and name='{table}' '''.format(table=tableName))
            rows = cursor.fetchall()
            exists = len(rows) > 0
            cursor.close()
            connection.close()
            return exists
        except:
            return False


class TableContent:
    """
    This holds a list of table rows.
    Type compatibility of the various parallel fields in the various rows is not verified.
    If the table is editable, types are checked at run time when the field data is displayed to select the
    appropriate GUI component for editing.
    Encapsulating the data set in an object allows the analytical methods to be standardized and for non-standard
    ones to be plugged in, allowing clean management of plug-ins.
    There will be a separate index list for sorting the data and an 'included' field for each row to indicate
    if the row is included after a particular analysis has been done.  The 'included' field needs to be a map
    which is keyed on an analysis identifier and which has a list of boolean values which is parallel to the
    physical sort of rows in the data list.  It is therefore an index set each value member of which  can be
    sorted.
    """

    def __init__(self, dbMetaData: DBMetaData_SQLite, tableName, str, editable=False, **keyWordArguments):
        print('TableContent constructor')


class PrototypeMenuBar(Menu):

    def __init__(self, dialog, dbManager: DBManager_SQLite):
        if dbManager is None or not isinstance(dbManager, DBManager_SQLite):
            raise Exception('PrototypeMenuBar:\tdbManager argument must be an instance of DBManager class')
        print('MainView.PrototypeMenuBar constructor')
        super().__init__(dialog)
        menuBar = Menu(dialog)
        dataBasesMenu = Menu(self, tearoff=0)
        dataBasesMenu.add_command(label='Select Database', command=dbManager.selectDB)
        dataBasesMenu.add_command(label='Close Database', command=dbManager.closeDB)
        dataBasesMenu.add_command(label='Select Table', command=dbManager.selectTable)
        dataBasesMenu.add_command(label='Show Table', command=dbManager.showTable)
        dataBasesMenu.add_command(label='Show Selected Tables', command=dbManager.showSelectedTables)
        dataBasesMenu.add_command(label='Show Selected Databases', command=dbManager.showSelectedDatabases)
        dataBasesMenu.add_command(label='Show DB Metdata', command=dbManager.showDBMetaData)
        dataBasesMenu.add_command(label='Show Table Metadata', command=dbManager.showTableMetaData)

        dataBasesMenu.add_command(label='Exit', command=ExitProgram)
        self.add_cascade(label='Databases', menu=dataBasesMenu)
        dialog.config(menu=self)


def ExitProgram():
    #  messagebox.showinfo('Exit program feature', "not implemented yet")
    answer = messagebox.askyesno('Exit program ', "Exit the database manager program?")
    if answer == True:
        window.destroy()


if __name__ == '__main__':

    tableDescriptor = TableDescriptor("fileHero Search.db",
                                      '/home/keithcollins/PycharmProjects/CommonData/search.db',
                                      "_home_keithcollins_Bitcoin.com Account")
    exit(0)

    fieldAttributes = {
        "fieldName": "Log_Entry",
        "storageType": "VARCHAR",
        "size": 256,
        "isKey": True,
        "isUnique": True,
        "nullsNotAllowed": True,
        "isPrimary": False,
        "autoincrement": False,
        "sortOrder": "ASC",
        "defaultValue": datetime.datetime.now().ctime(),
        "collateName": None,
        "foreignKeyClause": None,
        "isGenerated": False,
        "generateExpression": None,
        "generateType": None
    }
    fieldDefinitionSQLite = FieldDefSQLite(**fieldAttributes, noSQL=False, jsonSourced=True,
                                           linuxCOmmand="journalctl")
    fieldDefinitionSQLite.list()

    fieldDefinitions = (fieldDefinitionSQLite,)
    tableDefinitionSQLite = TableDefSQLite("databaseName.db", "tableName", fieldDefinitions)


    showGUI = False

    if showGUI:

        window  = Tk()
        window.geometry('800x400+50+50')
        window.title('Database Interface View')

        dbManager = DBManager_SQLite()
        menuBar = PrototypeMenuBar(window, dbManager)

        menuContent = Menus.MenuContent()
        menubar = Menus.MenuView(window, menuContent)
        print('DB Interface view constructed')

        window.mainloop()