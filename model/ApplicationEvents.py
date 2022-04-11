#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   April 6, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         model/ApplicationEvents.py
#   Date Started:   April 6, 2022
#   Purpose:        Record use of the application and recoed into an SQLite database for easy access and review by
#                   the user.  The value is the record of the user's activities with the application available to
#                   the user so that they can remember what they did and when, what tools they designed and when,
#                   what tools they ran producing what output for use as operational business or legal evidence
#                   and when, etc.
#                   The user will be able to configure secure, red only mirroring and hashing, with passwords that
#                   are stored as hash signatures only.
#   Development:
#

from datetime import datetime
from enum import Enum
from copy import deepcopy
from collections import OrderedDict
from os import environ
from sqlite3 import connect, Binary
from pickle import dumps, loads

from tkinter import Tk, messagebox

from model.Installation import USER_DATA_FOLDER

PROGRAM_TITLE = "Application Events - Transparent"
INSTALLING  = True


class EventType(Enum):
    GUI         = 'GUI'
    DB          = 'DB'
    FILE        = "File"
    FOLDER      = "Folder"
    OS          = 'OS'
    ETHERNET    = 'Ethernet'
    WIFI        = 'WiFi'
    MODULE      = "Module"
    CLASS       = "Class"
    METHOD      = "Method"

    def __str__(self):
        return self.value


class ExportFormat(Enum):
    CSV         = "CSV"
    SQLite      = "SQLite"
    JSON        = "JSON"
    XML         = "XML"
    XHTML       = "XHTML"


class ApplicationEvent:

    TypeNameMap     = {
        "GUI":      EventType.GUI,
        "DB":       EventType.DB,
        "File":     EventType.FILE,
        "Folder":   EventType.FOLDER,
        "OS":       EventType.OS,
        "Ethernet": EventType.ETHERNET,
        "WiFi":     EventType.WIFI,
        "Module":   EventType.MODULE,
        "Class":    EventType.CLASS,
        "Method":   EventType.METHOD
    }

    def __init__(self, source: str, timeStamp: datetime, eventType: EventType, eventName: str, eventAttributes: dict):
        ApplicationEvent.checkEventArgs( source, timeStamp, eventType, eventName, eventAttributes )
        self.source     = source
        self.timeStamp  = timeStamp
        self.eventType  = eventType
        self.eventName  = eventName
        self.eventAttributes = deepcopy(eventAttributes)


    def getAttribute(self, name: str):
        if name in self.eventAttributes:
            return self.eventAttributes[name]
        return None

    @staticmethod
    def checkEventArgs( source: str, timeStamp: datetime, eventType: EventType, eventName: str, eventAttributes: dict):
        if not isinstance(source, str) or not isinstance(timeStamp, datetime) or not isinstance(eventType, EventType) \
                or not isinstance(eventName, str) or not isinstance(eventAttributes, dict):
            raise Exception("ApplicationEvent.checkEventArgs - attempt to record invalid application event")

    def list(self):
        print("ApplicationEvent:\t" + str(self.eventName))
        print("\tsource:\t" + str(self.source))
        print("\ttimeStamp:\t" + self.timeStamp.ctime())
        print("\teventType:\t" + str(self.eventType))
        print("\tattributes:")
        for name, value in self.eventAttributes.items():
            print("\t\t" + str(name) + ":\t" + str(value))

    def __str__(self):
        return str({
            "Name": str(self.eventName), "Source": str(self.source), "Time Stamp": self.timeStamp.ctime(),
            "Type": str(self.eventType), "Attributes": str(self.eventAttributes)
        })


class EventManager:

    record  = OrderedDict()
    __DBFile    = "ApplicationActivity.db"

    def __init__(self):
        pass

    @staticmethod
    def addEvent(event: ApplicationEvent):
        EventManager.record[event.timeStamp] = deepcopy(event)

    @staticmethod
    def list():
        print("\nApplication Event Records (chronological):")
        for name, value in EventManager.record.items():
            print("\t" + str(name) + ":\t" + str(value))

    @staticmethod
    def export(format: ExportFormat, filePath: str):
        """
        Write the current content of the event record sequence to the specified file in the requested format.
        :param format:
        :param filePath:
        :return:
        """
        pass

    @staticmethod
    def createAppActivityDB():
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+EventManager.__DBFile)
        cursor = connection.cursor()
        #   cursor.execute("CREATE TABLE `Events` ( `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, `timeStamp` TEXT NOT NULL, `info` BLOB NOT NULL )")
        #   cursor.execute("CREATE TABLE `Debug` ( `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, `timeStamp` TEXT NOT NULL, `info` BLOB NOT NULL )")
        cursor.execute("""CREATE TABLE `Events` ( `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                            `timeStamp` TEXT NOT NULL, `info` BLOB NOT NULL )""")
        cursor.execute("""CREATE TABLE `Debug` ( `RowId` INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
                            `timeStamp` TEXT NOT NULL, `info` BLOB NOT NULL )""")
        connection.commit()
        cursor.close()
        connection.close()

    @staticmethod
    def commit():
        """
        Write current record sequence to the database and empty the list.
        :param self:
        :return:
        """
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+EventManager.__DBFile)
        cursor = connection.cursor()
        for timeStamp, event in EventManager.record.items():
            info = dumps(event)
            timeStampString = "{year:4d}/{month:2d}/{day:2d}" \
                .format(year=timeStamp.year, month=timeStamp.month, day=timeStamp.day).replace(' ', '0') + ' ' + \
                   "{hour:2d}:{minute:2d}:{second:2d}.{micro:6d}" \
                       .format(hour=timeStamp.hour, minute=timeStamp.minute, second=timeStamp.second,
                               micro=timeStamp.microsecond).replace(' ', '0')
            cursor.execute('''INSERT INTO Events( timeStamp, info ) VALUES( ?, ?)''', (timeStampString, Binary(info)))
        connection.commit()
        cursor.close()
        connection.close()
        EventManager.record     = OrderedDict()

    @staticmethod
    def getDBrecords():
        records = OrderedDict()
        connection = connect(environ['HOME']+'/'+USER_DATA_FOLDER+'/'+EventManager.__DBFile)
        cursor = connection.cursor()
        cursor.execute('''SELECT * FROM Events''')
        rows = cursor.fetchall()
        for row in rows:
            records[row[1]] = loads(row[2])
            #   print(str(row[1]) + ":\t" + str(records[row[1]]))
        return records

    @staticmethod
    def getDbFileName():
        return EventManager.__DBFile


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        #   EventManager.commit()
        mainView.destroy()


if __name__ == "__main__":
    if INSTALLING:
        print("HOME:\t" + environ['HOME'])
        print("Data Folder:\t" + USER_DATA_FOLDER)
        print("Application Activity DB Name:\t" + EventManager.getDbFileName())
        EventManager.createAppActivityDB()

    #   print(datetime.now().microsecond)
    applicationEvent    = ApplicationEvent( "ApplicationEvents module", datetime.now(), EventType.MODULE, "Start",
                                            {"Developer": "Keith Michael Collins"})
    applicationEvent.list()
    EventManager.addEvent(applicationEvent)
    EventManager.list()
    #   EventManager.commit()
    records     = EventManager.getDBrecords()
    print("\nApplication Event Records:")
    for timeStamp, info in records.items():
        print("\t" + str(timeStamp) + ":\t" + str(info))

    exit(0)

    mainView = Tk()
    mainView.geometry("700x400+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())
    mainView.mainloop()
