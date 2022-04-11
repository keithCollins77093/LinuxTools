#   Project:        LinuxLogForensics
#   Author:         George Keith Watson
#   Date Started:   July 14, 2021
#   Copyright:      (c) Copyright 2021 George Keith Watson
#   Module:         service/Messaging.py
#   Purpose:        Central messaging service which provides for communication between independent components so that
#                   no component needs to have a reference to another to communicate with it.
#   Development:
#

from tkinter import Tk
from datetime import datetime

class Messaging:

    def __init__(self, component: str):
        if component is None or not isinstance(component, str):
            raise Exception('Messaging constructor - invalid component argument:    ' + str(component))
        self.component = component
        self.recipients = {}

    def registerRecipient(self, name, listener):
        if name is not None and isinstance(name, str):
            #   print('Messaging.registerRecipient - type(listener):\t' + str(type(listener)))
            if listener is not None and callable(listener):
                #   print('Messaging.registerRecipient - registering listener for:\t' + name)
                self.recipients[name] = listener

class Message:

    def __init__(self, attributes: dict):
        self.timeStamp  = datetime.now()
        if attributes is None or not isinstance(attributes, dict):
            self.aborted = True
            raise Exception('Messaging.Message constructor: attributes argument is not valid:\t' + str(attributes))
        self.attributes = {}
        for key, value in attributes.items():
            self.attributes[key] = value
        self.aborted = False

    def __setattr__(self, key, value):
        if key in self.__dict__:
            return False
        self.__dict__[key] = value
        return True


class ComponentNames:
    """
    Immutable object with all of the declared, messegable component's names.
    """
    def __init__(self):
        self.MV_MenuBar    = 'MV.MainMenuBar'
        self.FileMetaData           = 'FileMetaData'
        self.LogFiles               = 'LogFiles'
        self.FMDV_PropertySheet     = 'FMDV.PropertySheet'
        self.FileMetaDataView       = 'FileMetaDataView'
        self.MasterTreeView         = 'MasterTreeView'
        self.MTV_PrototypeMenuBar   = 'MTV.PrototypeMenuBar'
        self.DBTable                = 'DBTable'
        self.DBManager              = 'DBManager'
        self.DBI_PrototypeMenuBar   = 'DBI.PrototypeMenuBar'
        self.Configuration          = 'Configuration'
        self.MenuContent            = 'MenuContent'
        self.MenuView               = 'MenuView'
        self.L_Message              = 'L.Message'
        self.Logger                 = 'Logger'

    def __setattr__(self, key, value):
        if key in self.__dict__:
            return False
        self.__dict__[key]  = value
        return True



if __name__ == '__main__':
    window  = Tk()
    window.geometryString('800x400+50+50')
    window.titleString('Messaging Manager')

    print('Files view constructed')

    window.mainloop()
