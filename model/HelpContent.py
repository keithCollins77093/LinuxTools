#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   August 11, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/Help.py
#   Purpose:        Help sub-system dialog.
#   Development:
#       2021-08-11:
#           This is the source module for all help content provided by this application.  It included the quick
#           content sensitive pop-up help content along with management of and access to the general help database.
#

from copy import deepcopy
import os


from model.Util import pathFromList, INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER


class HelpContent:

    def __init__(self, name: str, initialContent: dict, **keyWordArguments):
        """

        :param initial:             initial help content for an instance of HelpContent.
        :param keyWordArguments:    meta data for this help content.
        """
        if name is None or not isinstance(name, str):
            raise Exception("HelpDialog constructor - invalid name argument:\t" + str(name))
        if initialContent is None:
            initialContent = self.generateDefaultContent()
        self.validDescriptor = True
        if not isinstance(initialContent, dict):
            self.validDescriptor = False
        for key, value in initialContent.items():
            if not isinstance(key, str) or not isinstance(value, str):
                self.validDescriptor = False
                break
        if not self.validDescriptor:
            raise Exception("HelpDialog constructor - invalid descriptor argument:\t" + str(initialContent))
        self.name = name
        self.contentMap = deepcopy(initialContent)      #   thread safe

    def removeContent(self, topic):
        if topic is None or not isinstance(topic, str):
            raise Exception("HelpContent.removeContent - invalid topic argument:\t" + str(topic))
        if topic in self.contentMap:
            del(self.contentMap[topic])
            return topic
        return False

    def addContent(self, topic, helpText):
        if topic is None or not isinstance(topic, str):
            raise Exception("HelpContent.removeContent - invalid topic argument:\t" + str(topic))
        if helpText is None or not isinstance(helpText, str):
            raise Exception("HelpContent.removeContent - invalid helpText argument:\t" + str(helpText))
        if topic not in self.contentMap:
            self.contentMap[topic] = helpText
            return topic
        return False

    def addReplace(self, topic, helpText):
        if topic is None or not isinstance(topic, str):
            raise Exception("HelpContent.removeContent - invalid topic argument:\t" + str(topic))
        if helpText is None or not isinstance(helpText, str):
            raise Exception("HelpContent.removeContent - invalid helpText argument:\t" + str(helpText))
        self.contentMap[topic] = helpText

    def __setattr__(self, key, value):
        if key in self.__dict__:
            return False
        self.__dict__[key] = deepcopy(value)

    def list(self):
        print("\nHelpContent:\t" + self.name)
        for topic, helpText in self.contentMap.items():
            print("\t" + topic + ":\t" + helpText)

    def generateDefaultContent(self):
        manPythonFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                          "2021-08-11 12:15:11.618555 man ('python',).cmd_out"))
        if os.path.isfile(manPythonFileName):
            manPythonFile = open(manPythonFileName, 'r')
            manPythonText = manPythonFile.read()
            manPythonFile.close()
        else:
            manPythonText = "ERROR READING FILE:\t" + manPythonFileName

        manJournalCtlFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                              "journalctl.man.txt"))
        if os.path.isfile(manJournalCtlFileName):
            manJournalCtlFile = open(manJournalCtlFileName, 'r')
            manJournalCtlText = manJournalCtlFile.read()
            manJournalCtlFile.close()
        else:
            manJournalCtlText = "ERROR READING FILE:\t" + manJournalCtlFileName

        manAppArmorFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                            "apparmor.man.txt"))
        if os.path.isfile(manAppArmorFileName):
            manAppArmorFile = open(manAppArmorFileName, 'r')
            manAppArmorText = manAppArmorFile.read()
            manAppArmorFile.close()
        else:
            manAppArmorText = "ERROR READING FILE:\t" + manAppArmorFileName

        manDmesgFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                         "dmesg.man.txt"))
        if os.path.isfile(manDmesgFileName):
            manDmesgFile = open(manDmesgFileName, 'r')
            manDmesgText = manDmesgFile.read()
            manDmesgFile.close()
        else:
            manDmesgText = "ERROR READING FILE:\t" + manDmesgFileName

        manFindFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                        "find.man.txt"))
        if os.path.isfile(manFindFileName):
            manFindFile = open(manFindFileName, 'r')
            manFindText = manFindFile.read()
            manFindFile.close()
        else:
            manFindText = "ERROR READING FILE:\t" + manFindFileName

        manSudoFileName = pathFromList((INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, MAN_PAGES_FOLDER,
                                        "sudo.man.txt"))
        if os.path.isfile(manSudoFileName):
            manSudoFile = open(manSudoFileName, 'r')
            manSudoText = manSudoFile.read()
            manSudoFile.close()
        else:
            manSudoText = "ERROR READING FILE:\t" + manSudoFileName

        helpMap = {
            "LinuxLogForensics": "\n\tThis application gives you the ability to easily and conveniently access and search"
                              "the logs maintained by a debian Linux operating system installation.  The \"debian\" Linux"
                              "classification includes all varieties of Ubuntu, among others\n \tIt also interfaces"
                              "with the SQLite database engine to provide SQL capabilities on logging and other"
                              "system information that you elect, using this applicaiton suite, to save into a"
                              "database table or set of tables.  For example, many console or terminal commands"
                              "are available for expoloinr your Linux installation.  If these produce tabular"
                              "output in a know and standard format, then the table can be recorded in an SQLite"
                              "database table and then viewed, searched, filtered, and otherwise worked with as such,"
                              "including use fo the free DB Browser for SQLite on it.",
            "Modular": "\n\tThis application is a set of applications that can interoperate with each other.  You can "
                       "install one at a time, or the entire suite all at once, just depending on your own needs and"
                       "interests in exploring particular information stored by your computer.",
            "Author": "\n\tGeorge Keith Watson\n\teMail:\tkeith.michael.collins@gmx.com",
            "License": "\n\tThe license provided to you for use of this soaftwre product and its various component applicaiotns"
                       "and data sets is a free, open-source license for non-commercial use only.  You may not use it"
                       "for work or business which produces income. You may use it in a non-profit or governmental"
                       "organization for the legally allowed purposes of that organization.",
            "man python": manPythonText,
            "man journalctl": manJournalCtlText,
            "man apparmor": manAppArmorText,
            "man dmesg": manDmesgText,
            "manFindText": manFindText,
            "manSudoText": manSudoText
        }
        return helpMap
