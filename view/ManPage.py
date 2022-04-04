#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         view/ManPage.py
#   Date Started:   April 2, 2022
#   Purpose:        Views for Man Pages, including by section and in HTML viewer, pywebview.
#   Development:
#       Primary view should have sections listed vertically on the left with a text windos in the central content
#       area for the text.
#

from tkinter import Tk, messagebox

PROGRAM_TITLE = "Man Page Views"


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":
    mainView = Tk()

    mainView.geometry("800x600+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())

    mainView.mainloop()


