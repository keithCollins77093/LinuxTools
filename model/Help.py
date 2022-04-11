#   Project:        LinuxTools
#   Author:         George Keith Watson
#   Date Started:   March 31, 2022
#   Copyright:      (c) Copyright 2022 George Keith Watson
#   Module:         model/Help.py
#   Date Started:   April 8, 2022
#   Purpose:        Help text database manager and subsystem.
#   Development:
#

from tkinter import Tk, messagebox

from model.Installation import USER_DATA_FOLDER

PROGRAM_TITLE = "Help Database"

INSTALLING  = False
TESTING     = False

HELP_MAP    = {
    "Forensics Intro": {
        "Author":   ["Gustavo Amarchand", "Keanu Munn", "Samantha Renicker"],
        "Title":    "A Study on Linux Forensics",
        "Publication Date": "11/1/2018",
        "Text": "In general, the main objective for a computer forensics expert is to uncover the truth in "
                "the form of evidence from suspect devices. The issue one could argue is that in using closed "
                "source programs there is often no way to verify bugfixes or issues with the current tools version "
                "as this type of information is not disclosed to the users of the tools. This could lead to skewed "
                "results or distortion in the process of evidence gathering [1]. Using an open source tool such as "
                "Sleuth Kit for example an investigator could verify the legitimacy of the program and how it "
                "operates in many different ways, one of which would be the public record of bug fixes another "
                "option would be being able to compare the older versions of the source code to the newer "
                "releases, and the third option would be verifying the actual function of the code therefor being "
                "able to present how it is the tool was able to legitimately produce the evidence [1]. In using a "
                "closed source tool, the investigator is placing layers of abstraction between themselves and the "
                "evidence and with each of these layers the potential that the evidence could be distorted or have"
                "errors could increase."
    },
    "Forensic Imaging": {
        "Author": ["Gustavo Amarchand", "Keanu Munn", "Samantha Renicker"],
        "Title": "A Study on Linux Forensics",
        "Publication Date": "11/1/2018",
        "Text": "Dcfldd was a forensics-oriented version of the Unix dd utility that was developed by the "
        "Department of Defense computer forensics lab in 2002 [9]. The standard dd utility has the "
                "primary purpose of converting and copying files and is often used for backing up the boot sectors "
                "of hard drives. When talking about dcfldd the main differences that are provided by the tool vs "
                "the standard dd are hashing, hash comparisons of the source image and the created copy image, "
                "flexible naming conventions for the split image files, and the ability to direct output to multiple "
                "locations simultaneously [9]. Dcfldd is an important tool in the case of Linux system-based "
                "forensics as being able to make valid images of suspect drives is essential to conducting any "
                "form of proper forensics investigation."
    },
    "The Sleuth Kit": {
        "Author": ["Gustavo Amarchand", "Keanu Munn", "Samantha Renicker"],
        "Title": "A Study on Linux Forensics",
        "Publication Date": "11/1/2018",
        "Text": "Another great tool for forensics use on the Linux platform Sleuth Kit and Autopsy. Sleuth "
                "kit is a toolset used for finding evidence through analysis of file systems, comprised of tools for"
                "examining DOS, BSD, Mac partitions, Sun slices, and GPT disks [2]. Because all these tools are"
                "command line tools Autopsy was created as a graphical suit to allow for easier use of the tools."
                "During analysis. Because a full analysis will often require more than just file and volume system"
                "analysis the modularity of the Sleuth Kit will allow for the inclusion of other tools to further"
                "search for more data. In searching through Sleuth kit tools the ability to look up file hashes"
                "through a hash database is provided [7]. As well as being able to display the details and contents"
                "of all NTFS attributes including Alternate Data Streams."
    }
}


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit the " + PROGRAM_TITLE + " program?")
    if answer:
        mainView.destroy()


if __name__ == "__main__":

    if INSTALLING:
        exit(0)

    if TESTING:
        exit(0)

    print(__doc__)

    #   Quick demo display of a list-detail help layout - IN PROGRESS

    mainView = Tk()
    mainView.geometry("700x400+300+50")
    mainView.title(PROGRAM_TITLE)
    mainView.protocol('WM_DELETE_WINDOW', lambda: ExitProgram())
    mainView.mainloop()

