#   Project:        LinuxTools
#   Imported From:  LinuxLogForensics
#   Date Imported:  April 8, 2022
#   Author:         George Keith Watson
#   Date Started:   August 22, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         view/Administration.py
#   Purpose:        Security management
#   Development:
#
import json

from tkinter import Tk, Toplevel, LabelFrame, messagebox, \
                    RAISED, FLAT, GROOVE, RIDGE, SUNKEN, X, Y, BOTH

from view.Components import JsonTreeViewFrame, JsonTreeView

PROGRAM_TITLE = "Administration"

from model.Util import pathFromList, INSTALLATION_FOLDER, APPLICATION_TEST_DATA
from view.Components import JsonTreeViewFrame


class Administration(Toplevel):

    def __init__(self, container, geometryString, listener, **keyWordArguments):
        #   Check arguments
        Toplevel.__init__(self, container, **keyWordArguments)
        self.geometry = geometryString
        self.listener = listener
        #   read in and display security index
        fileName    = pathFromList((INSTALLATION_FOLDER, APPLICATION_TEST_DATA, "sha256sums.txt"))
        file = open(fileName, "r")
        fileContent = file.read()
        file.close()
        jsonContent     = json.loads(fileContent)

        #   Put json into the json Treeview
        syntaxTreeviewConfig = {"mode": JsonTreeView.MODE_NAME_VALUE, "openBranches": False}
        self.jsonTreeView = JsonTreeViewFrame(self, jsonContent, syntaxTreeviewConfig,
                                              text="Encryption and Hashing Admin",
                                              border=4, relief=RAISED)
        self.protocol('WM_DELETE_WINDOW', lambda: self.exit())

        self.jsonTreeView.pack(expand=True, fill=BOTH)

    def exit(self):
        self.destroy()
        if self.listener != None:
            self.listener({"sender": "view.administration", "action": "exited", "status": 'destroyed'})


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == '__main__':
    mainView = Tk()
    mainView.geometry("900x500+50+50")
    mainView.title(PROGRAM_TITLE)
    mainView.layout = "grid"
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    administration  = Administration(mainView, "600x500+500+100", None)
    administration.mainloop()

    #   mainView.mainloop()
