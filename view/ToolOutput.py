#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 21, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         ToolOutput
#   Purpose:        View for managing the output of configured command line utilities.  Initially its purpose
#                   is simply to display any amount of output in a scrollable Text, but formatting for
#                   structured storage and search and analysis tools will be implemented.  Filtering using
#                   regular expressions, with a GUI regular expretion designer will be included.
#   Development:
#       The output of bash commands could be piped together using the bash commands grep, sed, and awk to
#       extract formatted, structured data which can then be stored in a database table or placed into
#       a json, which my json viewer can be used to structure further, and stored in a noSQL like tiny db.
#       This will allow collection of large amounts of data usable for analysis, and workflows for standard
#       forensic analysis can be designed in as templates.
#       sed, awk, and grep based tools and user custom designing need to be included and supported in this
#       dialog for this purpose, so that the user had the data in front of them rather than needeing to be an
#       expert in the use of these extraction and structuring tools using the pipe feature (which will be)
#       in the tool designer (utility configurator) of this application.
#

import os
from tkinter import Tk, Toplevel, LabelFrame, Text, Button, Label, Scrollbar, \
                        SUNKEN, GROOVE, END, VERTICAL, HORIZONTAL, BOTH, BOTTOM, X, RIGHT, Y, E, W, N, S
from tkinter.scrolledtext import ScrolledText

from view import ProgrammableMenu

class ToolOutput(LabelFrame):
    def __init__(self, container, name, **keyWordArguments):
        LabelFrame.__init__(self, container, name=name)
        if "frameConfig" in keyWordArguments and isinstance(keyWordArguments["frameConfig"], dict):
            self.config(keyWordArguments["frameConfig"])
        outputChars = ''
        if 'commandText' in keyWordArguments and isinstance(keyWordArguments['commandText'], str):
            self.commandText    = keyWordArguments['commandText']
            outputStream    = os.popen(keyWordArguments['commandText'])
            outputChars     = outputStream.read().strip()
            outputStream.close()

        """
        Pack layout:
        
        if 'limitScroll' in keyWordArguments and keyWordArguments['limitScroll']:
            outputText  = ScrolledText(self, font=('consolas', 10))
            outputText.pack(expand=True, fill=BOTH)
        else:       # scroll for both horizontal and vertical
            horizontalScroller  = Scrollbar(self, orient=HORIZONTAL)
            horizontalScroller.pack(side=BOTTOM, fill=X)
            verticalScroller    = Scrollbar(self, orient=VERTICAL)
            verticalScroller.pack(side=RIGHT, fill=Y)
            outputText          = Text(self, font=('consolas', 10), wrap=None, yscrollcommand=verticalScroller.set,
                                       xscrollcommand=horizontalScroller.set)
            #outputText.pack(expand=True, fill=BOTH)
            outputText.pack()
            horizontalScroller.config(command=outputText.xview)
            verticalScroller.config(command=outputText.yview)
        """
        #   Grid Layout:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        horizontalScroller = Scrollbar(self, orient=HORIZONTAL, name="horizontalScroller")
        horizontalScroller.grid(row=1, column=0, sticky=E+W)
        verticalScroller = Scrollbar(self, orient=VERTICAL, name="verticalScroller")
        verticalScroller.grid(row=0, column=1, sticky=N+S)
        outputText = Text(self, font=('consolas', 10), wrap=None, bd=0, name="outputText",
                          yscrollcommand=verticalScroller.set,
                          xscrollcommand=horizontalScroller.set)
        # outputText.pack(expand=True, fill=BOTH)
        outputText.grid(row=0, column=0, sticky=N+S+E+W)
        horizontalScroller.config(command=outputText.xview)
        verticalScroller.config(command=outputText.yview)

        outputText.insert(END, outputChars)
        outputText.config(state = 'disabled')


if __name__ == "__main__":
    mainView    = Tk()
    mainView.geometry("500x600+100+100")
    toolName    = 'ls -l'
    toolOutput = ToolOutput(mainView, toolName, frameConfig={'text': ' Tool Output: ' + toolName + " ",
                                                             'padx': 10, 'pady': 10, 'relief': SUNKEN, 'borderwidth': 4})
    toolOutput.pack(expand=True)
    mainView.mainloop()
