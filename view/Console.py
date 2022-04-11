#   Project:        LinuxTools
#   Imported From:  LinuxLogForensics
#   Date Started:   July 24, 2021
#   Date Imported:  April 8, 2022
#   Author:         George Keith Watson
#   Copyright:      (c) Copyright 2021 George Keith Watson
#   Module:         view/Console.py
#   Purpose:        A Linux command line interface for developing use of Linux commands in this Application.
#                   One class of commands used will be the text filtering utilities which will be used for
#                   log message / line sequence analysis.
#   Development:
#       2021-08-01:
#           Add to quick, pre-configured tools menu:
#               lsblk -f
#               lsblk -f --json
#           Add feature to display the {command} --help page for any linux command next to or click-available
#               from the quick pre-configured tool menu.
#               This plus full man page text needs to be available and viewable simultaneously from
#               the tool configuration property sheet.
#           Add features in Feature Development/2021-08-01/Programming Wonders_ Python Script to Recover Deleted
#               Files And Partitions.pdf.
#
#           dpkg --verity and dpkg --audit strategy:
#               Source: Feature Development/2021-08-01/:
#                   Ask Ubuntu: What is the use of 'sudo dpkg --verify', source: man dpkg:
#               "Currently the only functional check performed is an md5sum [hash] verification of the file contents
#               against the stored value in the files database.  It will only get checked if the database contains
#               the md5sum.  To check for any missing metadata in the database, the --audit command can be used"
#
#               This is the strategy I planned to use for any and all files needing secure storage and preservation
#               as investigation resources or as presentable evidence.
#
#       2021-08-02:
#           When a table is created for a new command + arguments, if the SQLiteDB application is also running
#           and has loaded the console output database's metadata for viewing, it needs to receive a message
#           using the RAM disk that its db meta data needs updating.  It can then initialize a new db meta data
#           object and do a setModel on all of its components that use the new db meta data object.
#
#       2021-08-17:
#           Add fuzzy string matching to token index only in this module, along with any tokenized text.
#           as long as the user selects "Words Only" for searching, fuzzy matches are possible on any text.
#           User will be able to specify a fuzzy ratio or percent match or percent distance, and since
#           most users are unfamiliar with fuzzy matching, a mouse over on the tag created for the match
#           in a tkinter.Text should show the fuzzy distance or closeness in a tool tip or message label.
#
#       2021-08-19
#           When formatting output as json, include a means of pretty-printing it or switching to a Treeview.
#           Treeview will allow the user to add custom syntax coloring, i.e. for particular field names,
#           branch names, or path specifiers.
#           Commands to study (any json output availble?):
#               uname, uptime, hostname, last reboot, date, w, whoami, buffer, cat proc/meminfo,
#               lsusb, dmidecode, sudo dmidecode, hdparm -i /dev/sda, badblocka -s /dev/sda,
#               mpstat 1, vmstat 1, iostat 1,
#               tcpdump -i eth0 'port 80'           Monitor all traffic on port 80 (http)
#               tcpdump -i eth0                     Capture and display all packets on interface eth0
#               lsof                                list all open files on the system
#               free,
#               watch df -h                         Execute "df -h" showing periodic updates
#               id, last, who, w,
#               ps, jobs, bg,
#               ip a, ethtool eth0, ping host, whois domain,
#               dig domain,                         Display DNS information for domain
#               dig -x IP_ADDRESS                   Reverse lookup of ip address
#               host domain                         display DNS ip address for domain
#               hostname -i                         display network address of the host
#               hostname -l                         display all local ip addresses of the host
#               wget http://domain.com/file         download named file
#               netstat -nutlp                      display listening tcp and udp ports and corresponding programs
#               tar,
#               locate name                         find files and directories by name
#               find                                "
#               scp, rsync, df -h, fdisk -l, du -ah, du -sh,
#
#       2021-08-21 (journalctl output)
#
#           Source: www.commandlinux.com/man-page/man1/systemd.1.html
#
#           "systemd is a system and service manager for Linux operating systems. When run as first process on
#           boot (as PID 1), it acts as init system that brings up and maintains userspace services. Separate
#           instances are started for logged-in users to start their services."
#
#           "When run as a system instance, systemd interprets the configuration file system.conf and the files in
#           system.conf.d directories; when run as a user instance, systemd interprets the configuration file
#           user.conf and the files in user.conf.d directories. See systemd-system.conf(5) for more information."
#
#
#           man journalctl:
#
#           "If called without parameters, it will show the full contents of the journal, starting with the oldest
#           entry collected."
#
#           "If one or more match arguments are passed, the output is filtered accordingly. A match is in the
#           format "FIELD=VALUE", e.g. "_SYSTEMD_UNIT=httpd.service", referring to the components of a
#           structured journal entry. See systemd.journal-fields(7) for a list of well-known fields. If
#           multiple matches are specified matching different fields, the log entries are filtered by both,
#           i.e. the resulting output will show only entries matching all the specified matches of this kind.
#           If two matches apply to the same field, then they are automatically matched as alternatives, i.e.
#           the resulting output will show entries matching any of the specified matches for the same field.
#           Finally, the character "+" may appear as a separate word between other terms on the command line.
#           This causes all matches before and after to be combined in a disjunction (i.e. logical OR)."
#
#           "It is also possible to filter the entries by specifying an absolute file path as an argument. The
#           file path may be a file or a symbolic link and the file must exist at the time of the query. If a
#           file path refers to an executable binary, an "_EXE=" match for the canonicalized binary path is
#           added to the query. If a file path refers to an executable script, a "_COMM=" match for the script
#           name is added to the query. If a file path refers to a device node, "_KERNEL_DEVICE=" matches for
#           the kernel name of the device and for each of its ancestor devices is added to the query. Symbolic
#           links are dereferenced, kernel names are synthesized, and parent devices are identified from the
#           environment at the time of the query. In general, a device node is the best proxy for an actual
#           device, as log entries do not usually contain fields that identify an actual device. For the
#           resulting log entries to be correct for the actual device, the relevant parts of the environment
#           at the time the entry was logged, in particular the actual device corresponding to the device node,
#           must have been the same as those at the time of the query. Because device nodes generally change
#           their corresponding devices across reboots, specifying a device node path causes the resulting
#           entries to be restricted to those from the current boot."
#
#           NEED:
#           Workflow comparisons, examples, for various filtering problems.
#
#           man systemd-journald.service:
#
#           systemd-journald is a system service that collects and stores logging data. It creates and maintains
#           structured, indexed journals based on logging information that is received from a variety of sources:
#
#           •   Kernel log messages, via kmsg
#
#           •   Simple system log messages, via the libc syslog(3) call
#
#           •   Structured system log messages via the native Journal API, see sd_journal_print(3)
#
#           •   Standard output and standard error of service units. For further details see below.
#
#           •   Audit records, originating from the kernel audit subsystem
#
#           The daemon will implicitly collect numerous metadata fields for each log messages in a secure and
#           unfakeable way. See systemd.journal-fields(7) for more information about the collected metadata.
#
#           THERE IS NO EXPLANATION REGARDING WHAT "unfakable" MEANS.
#           This word is not in the dictionary.
#           Logs are written using the C programming language, not secure, to re-writable media, not secure.
#           The ease with which a virus can mobilize functions in a C program is ridiculous.  OOP, e.g. Java
#           at least has classes with access control to all of the members.
#           Logs need to be written to non-rewritable media.  DVD's are one example.
#
#           man mkisofs:    (makes an ISO image from a folder so that it can be burned to CD or DVD)
#
#           genisoimage is a pre-mastering program to generate ISO9660/Joliet/HFS hybrid filesystems.
#
#           genisoimage  is  capable  of  generating  the System Use Sharing Protocol records (SUSP) specified
#           by the Rock Ridge Interchange Protocol.  This is used to further describe the files in the ISO9660
#           filesystem  to  a  Unix host,  and  provides information such as long filenames, UID/GID, POSIX
#           permissions, symbolic links, and block and character device files.
#
#           If Joliet or HFS hybrid command line options are specified, genisoimage will create the additional
#           filesystem metadata needed for Joliet or HFS.  Otherwise genisoimage will generate a pure ISO9660
#           filesystem.
#
#       2021-10-23:
#           Carbon Footprint of current intrinsically insecure digital technology foundation:
#               Just looking at the header information required for every email and then at the packet
#               streams produced using wireshark it is easy to see that security on the internet is a major
#               problem that multiplies by an order of magnitude, a factor of 10, the energy
#               use required for internet traffic.  It also slows communications down by as much, and
#               increases direct and immediate costs to the user by the same factor for the bandwidth
#               required, not to mention the downstream costs, according to progressives, of its massive
#               energy inefficiency.
#               Are there estimates published by the Federal Government of the carbon footprint, or just the
#               mega-watt hours consumed by internet traffic yearly?  One must add to this the additional
#               processing power required at each sending and receiving node or server.
#

from os import environ, walk, remove
from os.path import isdir, isfile
from sys import stderr, exc_info
from subprocess import Popen, PIPE, STDOUT
from json import loads, dump
from shutil import copytree
from datetime import datetime
from enum import Enum
import logging

from tkinter import Tk, LabelFrame, Listbox, Label, Entry, Button, Text, Frame, filedialog, messagebox, \
                    Checkbutton, Menu, Toplevel, Scrollbar, scrolledtext, \
                    StringVar, IntVar, BooleanVar, \
                    INSERT, END, N, S, E, W, NW, NE, SW, SE, LEFT, CENTER, RIGHT, BOTH, HORIZONTAL, VERTICAL, \
                    SUNKEN, FLAT, RAISED, GROOVE, RIDGE, BROWSE, SINGLE, MULTIPLE, EXTENDED, X, Y, \
                    TOP, BOTTOM, LEFT, RIGHT, NORMAL, DISABLED, WORD
from tkinter import ttk

from model.Util import JsonIndex, pathFromList, INSTALLATION_FOLDER, DOCUMENTATION_FOLDER, SUDO_HELP_FILE, \
                    SUDO_MAN_FILE, USER_CACHE_FOLDER, \
                    USER_DATA_FOLDER, SAVED_CONSOLE_OUT_FOLDER, CONSOLE_OUT_TEXT_FOLDER, CONSOLE_OUT_DB_FOLDER,\
                    USER_LOG_ARCHIVES_FOLDER, APP_DATA_FOLDER, USER_CONSOLE_OUT_DB

from model.DBInterface import saveDpkg_l_OutputToDB, savePs_lf_A_OutputToDB, journalctl_o_json_OutputToDB
from model.HelpContent import HelpContent
from service.tools.dpkg import DEFAULT_DEB_DPKG_LOCATION, DEFAULT_DEB_DPKG_NAME
from view.Components import OptionEntryDialog, JsonTreeViewFrame, JsonTreeView
from view.Help import HelpDialog, HelpAndApproval
from view.Administration import Administration

FEATURE_NAME_IMAGE_LOGS     = "CD / DVD Image of Logs"
FEATURE_NAME_ISO_IMAGE_FOLDER   = "Make ISO Image of Folder"
FEATURE_NAME_EXFOLIATE_FOLDER   = "Exfoliate Folder"

DPKG_HELP_VERIFY    = "Source: man dpkg\n" \
                      "Verifies  the  integrity  of package-name or all packages if omitted, by comparing \n" \
                      "information from the files installed by a package with the files metadata information \n" \
                      "stored in the dpkg database (since dpkg 1.17.2).  The origin of the files  metadata  \n" \
                      "information in  the  database is  the  binary  packages themselves. That metadata gets \n" \
                      "collected at package unpack time during the installation process.\n" \
                      "Currently the only functional check performed is an md5sum verification of the file \n" \
                      "contents against the stored value in  the  files database.  It will only get checked if \n" \
                      "the database contains the file md5sum. To check for any missing metadata in the database, \n" \
                      "the --audit command can be used.\n\n" \
                      "The output format is selectable with the --verify-format option, which by default uses the \n" \
                      "rpm format, but that might change in  the future, and as such, programs parsing this command \n" \
                      "output should be explicit about the format they expect."

DPKG_HELP_AUDIT     = "Source: man dpkg\n" \
                        "Performs database sanity and consistency checks for package-name or all packages if \n" \
                      "omitted (per package checks since dpkg 1.17.10).  For example, searches for packages \n" \
                      "that have been installed only partially on your system or that have missing,  wrong  or \n" \
                      "obsolete control data or files. dpkg will suggest what to do with them to get them fixed."

HELP_LOG_FOLDER_IMAGE = "In the Linux OS, Logs are written to disk in a dedicated folder.  In a Debian Linux OS, \n" \
                        "one example being Ubuntu, they are written to the /var/log/ directory.  You have access \n" \
                        "to this folder so you can examine its contents and their protections / permissions at \n" \
                        "any time.  There is no standard program or method for writing these essential security \n" \
                        "files to media that cannot be re-written.  Anything on a hard drive can be re-written, \n" \
                        "and most of your log files do not require administrator access permissions to view them \n" \
                        "and change their content.  The root account is sufficient, accessed simply with the \n" \
                        "'sudo' command and your user account password.  'Rootkits' (google it) are a common \n" \
                        "hacker method of obtaining root and even administrator access, so re-writable logs are \n" \
                        "simply written in pencil to the typical hacker.  If the intruder can gain access, " \
                        "then they can gain access to the logs and cover their tracks.  The logs are the primary \n" \
                        "means of establishing a timeline showing that an intrusion happened or that damage was \n" \
                        "done.  Log files therefore should be regularly backed up to DVD or CD using a disk type \n" \
                        "and  mode that does not allow overwirting.\n\n" \
                        "See https://en.m.wikipedia.org/wiki/Rootkit using your phone's browser:\n" \
                        "\"Rootkit detection is difficult because a rootkit may be able to subvert the software \n" \
                        "that is intended to find it.  Detection methods include using an alternative and trusted \n" \
                        "operating system, behavioral-based methods, signature scanning, difference scanning, and \n" \
                        "memory dump analysis.  Removal can be complicated or practically impossible, especially \n" \
                        "in cases where the rootkit resides in the kernal;  reinstallation of the operating system \n" \
                        "may be the only available solution to the problem.  When dealing with firmware rootkits, \n" \
                        "removal may require hardware replacement, or specialized equipment.\""

HELP_FOLDER_IMAGE   = "Making an ISO image file of a folder makes the content read-only and preserves the byte-\n" \
                      "by-byte content of the folder, including all folder and file attributes, also known as\n" \
                      "the meta-data.  The image file can then be mounted as a regular folder and its contents\n" \
                      "examined with any appropriate application or forensic tool.  This is one means of performing\n" \
                      "a forensically sound back-up, meaning the content is usable as evidence without examination\n" \
                      "of extensive logs to verify the integrity of the backup.\n\n" \
                      "WARNING: Check destination file name in terminal that pops up before running.\n" \
                      "This feature will over-write a file with the same name."


EXFOLIATE_FOLDER_HELP   = "Exfoliation of a folder is the process of deleting all of the leaves, meaning the files, \n" \
                          "while leaving the hierarchical folder structure in place.\n" \
                          "Once an ISO image of a folder is made, the folder structure can be re-used and filled\n" \
                          "with new content.  This is useful for any established or standard work flow in which \n" \
                          "periodically the current work product needs to be saved in a read-only, secure form, and \n" \
                          "then the same folder structure used for new work.  Each time the ISO image of the folder \n" \
                          "is created the folder can be exfoliated and then re-used for the next phase.  If you have\n" \
                          "a standard folder structure for college work, for instance, each semester can be tidily\n" \
                          "packaged up separately and cleaned, and the folder structure then remains identical from\n" \
                          "semester to semester.  A month-to-month accounting system does the same thing for its\n" \
                          "monthly journals and logs.\n\n" \
                          "There is no consistent way programmatically to place deleted files in the system cache.\n" \
                          "This is done by the file manager dialog installed with your version of Linux.  If you want\n" \
                          "your exfoliated files in a cache folder so that you can recover them if you made a mistake,\n" \
                          "you can select this option in the next dialog.  The exfoliated folder will be copied to\n" \
                          "the application installation folder under the userData/cache/ folder.  The folders and \n" \
                          "files moved will not retain all of their meta-data, unlike the ISO of the folder that \n" \
                          "you hopefully made before exfoliating.  Specifically, they will losw the owner and group\n" \
                          "identifiers."

TOOL_MANAGER_HELP      = "This is the linux tool manager.\n" \
                          "With this feature you can check to see if a command you specify is installed on the " \
                          "booted linux operating system.  If it isn't, you then have the option of installing it.\n" \
                          "You will need to have an active internet connection for the installation process to " \
                          "work.\n\n" \
                          "You are also able to configure particular commands to perform particular tasks that you\n" \
                          "do or want to do frequently without having to remember every flag and argument required\n" \
                          "for each.\n" \
                          "These are called \"Tools\" in the fileHero application.\n" \
                          "To build a tool, you first select the Linux command you want to configure. \n" \
                          "you then select the command line arguments you want to include and the values for those\n" \
                          "that require them.  To save your design, you give it a name and then choose the\n" \
                          "\"Save Tool\" option.  Each tool you save will be available in future fileHero sessions\n" \
                          "and each can be used as a template for solving similar problems.\n\n"  \
                          "The next dialog will handle the details."


class OutputFrame(LabelFrame):

    VIEW_MODES  = ('text', 'list', 'tree')

    def __init__(self, container, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)
        self.configure(border=5, relief=SUNKEN)
        self.container = container
        self.outputText         = Text(self, border=3, relief=SUNKEN, state=DISABLED)
        self.outputListBox      = Listbox(self, border=3, relief=GROOVE, selectmode=EXTENDED)
        self.outputTreview      = JsonTreeView(self, None, {})
        self.vertScrollBar = None
        self.horzScrollBar = None
        self.currentViewMode = None
        self.setViewMode('text')

        """
        #   Load some sample text from the help files
        sudoManFile = open(INSTALLATION_FOLDER + '/' + DOCUMENTATION_FOLDER + '/' + SUDO_MAN_FILE, 'r')
        sudoManText = sudoManFile.read()
        sudoManFile.close()
        """
        self.content = None
        try:
            commandList = ['dpkg', '-l']
            sub     = Popen(commandList, stdout=PIPE, stderr=STDOUT )
            self.container.lastCommandRunTime = datetime.now()
            output, error_message = sub.communicate()
            content  = output.decode('utf-8')
            self.setContent(content, commandList)
        except Exception:
            self.content = ''
            for line in exc_info():
                self.content += str(line) + '\n'

    def setContent(self, content: str, commandList: list):
        self.outputText.config(state=NORMAL)
        self.outputText.delete('1.0', 'end')
        self.outputText.insert(END, content)
        self.outputText.config(state=DISABLED)

        lines = content.split('\n')
        maxLineLen = 0
        lineIdx = 0
        for line in lines:
            length = len(line)
            if length > maxLineLen:
                maxLineLen = length
            lineIdx += 1
        self.outputListBox.delete(0, END)
        self.outputListBox.insert(END, *lines)
        self.outputListBox.configure(height=50, width=maxLineLen + 4)

        jsonContent = None
        try:
            jsonContent = loads(content)
        except:
            #   Possibly a list of json formatted lines
            commandString = ''
            for arg in commandList:
                commandString += arg + ' '
            commandString = commandString.strip()
            jsonContent = {}
            jsonContent[commandString] = []
            lines = content.split('\n')
            for line in lines:
                #   print("json:\t" + line)
                if line.strip() != '':
                    jsonContent[commandString].append(loads(line))

        if jsonContent is not None:
            self.outputTreview.setModel(jsonContent)
            self.currentViewType = 'tree'

        self.content = content

    def setViewMode(self, mode: str):
        if mode is None or not mode in OutputFrame.VIEW_MODES:
            raise Exception("OutputFrame.setViewMode - invalid mode argument:   " + str(mode))
        if mode != self.currentViewMode:
            if self.vertScrollBar is not None:
                self.vertScrollBar.pack_forget()
                self.vertScrollBar = None
            if self.horzScrollBar is not None:
                self.horzScrollBar.pack_forget()
                self.horzScrollBar = None

            if self.currentViewMode == 'text':
                self.outputText.pack_forget()
            elif self.currentViewMode == 'list':
                self.outputListBox.pack_forget()
            elif self.currentViewMode == 'tree':
                self.outputTreview.pack_forget()

            if mode == 'text':
                self.vertScrollBar = Scrollbar(self.container, command=self.outputText.yview, orient=VERTICAL)
                self.horzScrollBar = Scrollbar(self.container, command=self.outputText.xview, orient=HORIZONTAL)
                self.outputText.config(yscrollcommand=self.vertScrollBar.set,
                                       xscrollcommand=self.horzScrollBar.set)
                self.outputText.pack(fill=BOTH, expand=True, padx=2, pady=2)
                self.vertScrollBar.pack(side=RIGHT, fill=Y)
                self.horzScrollBar.pack(side=BOTTOM, fill=X)
                self.currentViewMode = 'text'
            elif mode == 'list':
                self.vertScrollBar = Scrollbar(self.container, command=self.outputListBox.yview, orient=VERTICAL)
                self.horzScrollBar = Scrollbar(self.container, command=self.outputListBox.xview, orient=HORIZONTAL)
                self.outputListBox.config(yscrollcommand=self.vertScrollBar.set,
                                       xscrollcommand=self.horzScrollBar.set)
                self.outputListBox.pack(fill=BOTH, expand=True, padx=2, pady=2)
                self.vertScrollBar.pack(side=RIGHT, fill=Y)
                self.horzScrollBar.pack(side=BOTTOM, fill=X)
                self.currentViewMode = 'list'
            elif mode == 'tree':
                self.vertScrollBar = Scrollbar(self.container, command=self.outputTreview.yview, orient=VERTICAL)
                self.horzScrollBar = Scrollbar(self.container, command=self.outputTreview.xview, orient=HORIZONTAL)
                self.outputTreview.config(yscrollcommand=self.vertScrollBar.set,
                                       xscrollcommand=self.horzScrollBar.set)
                self.outputTreview.pack(fill=BOTH, expand=True, padx=2, pady=2)
                self.vertScrollBar.pack(side=RIGHT, fill=Y)
                self.horzScrollBar.pack(side=BOTTOM, fill=X)
                self.currentViewMode = 'tree'


class DataSourceType(Enum):
    IsoFile             = "ISO file"
    Partition           = "Partition"
    Folder              = "Folder"
    SQLiteDatabase      = "SQLite Database"
    SQLiteTable         = "SQLite Table"
    Ethernet            = "Ethernet"
    WiFi                = "WiFi"
    Internet            = "Internet (TCP/IP)"

    def __str__(self):
        return self.value


class ConsoleMenuBar(Menu):

    def __init__(self, consoleView):
        Menu.__init__(self, consoleView)

        #   This assumes that dialog is an instance of ConsoleView which has at self.outputFrame an instance of
        #   OutputFrame which has an attribute named self.outputText which is the ttk.Text containing the output.
        self.consoleView = consoleView

        self.currentViewType = 'text'
        fileMenu = Menu(self, tearoff=0)
        redirctSubMenu  = Menu(self, tearoff=0)
        redirctSubMenu.add_command(label='to File',
                                   command=lambda: self.redirectOutput(
                                       text=self.consoleView.outputFrame.content,
                                       target='file', commandText=self.consoleView.commandText.get()))
        redirctSubMenu.add_command(label='to Database Table', command=lambda: self.redirectOutput(
            text=self.consoleView.outputFrame.content,
            target='dbTable', commandText=self.consoleView.commandText.get()))
        fileMenu.add_cascade(menu=redirctSubMenu, label='Redirect Output')

        selectSourceSubMenu = Menu(self, tearoff=0)
        selectSourceSubMenu.add_command(label=str(DataSourceType.IsoFile),
                                        command=lambda: self.selectInfoSource(DataSourceType.IsoFile))
        selectSourceSubMenu.add_command(label=str(DataSourceType.Partition),
                                        command=lambda: self.selectInfoSource(DataSourceType.Partition))
        selectSourceSubMenu.add_command(label=str(DataSourceType.Folder),
                                        command=lambda: self.selectInfoSource(DataSourceType.Folder))
        selectSourceSubMenu.add_command(label=str(DataSourceType.SQLiteDatabase),
                                        command=lambda: self.selectInfoSource(DataSourceType.SQLiteDatabase))
        selectSourceSubMenu.add_command(label=str(DataSourceType.SQLiteTable),
                                        command=lambda: self.selectInfoSource(DataSourceType.SQLiteTable))
        selectSourceSubMenu.add_command(label=str(DataSourceType.Ethernet),
                                        command=lambda: self.selectInfoSource(DataSourceType.Ethernet))
        selectSourceSubMenu.add_command(label=str(DataSourceType.WiFi),
                                        command=lambda: self.selectInfoSource(DataSourceType.WiFi))
        selectSourceSubMenu.add_command(label=str(DataSourceType.Internet),
                                        command=lambda: self.selectInfoSource(DataSourceType.Internet))
        fileMenu.add_cascade(menu=selectSourceSubMenu, label='Select Information Source')

        fileMenu.add_command(label=FEATURE_NAME_IMAGE_LOGS, command=self.consoleView.makeLogFolderImage)
        fileMenu.add_command(label='Mount Log Folder Image as Folder', command=self.consoleView.mountLogFolderImage)
        fileMenu.add_command(label=FEATURE_NAME_ISO_IMAGE_FOLDER, command=self.consoleView.makeFolderImage)
        fileMenu.add_command(label='Mount ISO Image as Folder', command=self.consoleView.mountFolderImage)
        fileMenu.add_command(label=FEATURE_NAME_EXFOLIATE_FOLDER, command=self.consoleView.exfoliateFolder)
        #   fileMenu.add_command(label='Exit', command=self.consoleView.ExitProgram)
        self.add_cascade(label='Files', menu=fileMenu)

        viewsMenu = Menu(self, tearoff=0)
        viewsMenu.add_command(label='Text',
                              command=self.showTextView)
        viewsMenu.add_command(label='List',
                              command=self.showListView)
        viewsMenu.add_command(label='Tree',
                              command=self.showTreeview)
        self.add_cascade(label='Views', menu=viewsMenu)

        configurationMenu = Menu(self, tearoff=0)
        configurationMenu.add_command(label='Administration',
                                      command=self.launchAdminDialog)
        configurationMenu.add_command(label='Application Logging',
                                      command=lambda: self.showMessage(title='Application Logging', message="Not implemented yet"))
        configurationMenu.add_command(label='Default Workflows',
                                      command=lambda: self.showMessage(title='Default Workflows', message="Not implemented yet"))
        configurationMenu.add_command(label='GUI Styles',
                                      command=lambda: self.showMessage(title='GUI Styles', message="Not implemented yet"))
        self.add_cascade(label='Configuration', menu=configurationMenu)

        toolsMenu = Menu(self, tearoff=0)

        journalctlMenu = Menu(toolsMenu, tearoff=0)
        journalctlMenu.add_command(label='journalctl --system --lines=1000 -o json',
                                      command=lambda: self.genericJournalctlTool('--system', '--lines=1000', '-o json' ))
        journalctlMenu.add_command(label='journalctl --user --lines=1000 -o json',
                                      command=lambda: self.genericJournalctlTool('--user', '--lines=1000', '-o json' ))
        journalctlMenu.add_command(label='journalctl --dmesg --lines=1000 -o json',
                                      command=lambda: self.genericJournalctlTool('--dmesg', '--lines=1000', '-o json' ))
        toolsMenu.add_cascade(label='System Journal', menu=journalctlMenu)


        dpkgMenu    = Menu(toolsMenu, tearoff=0)
        dpkgMenu.add_command(label='dpkg --help     dpkg help page',
                                      command=lambda: self.genericDpkgTool('--help'))
        dpkgMenu.add_command(label='dpkg -l     Tabular list of all installed packages',
                                      command=lambda: self.genericDpkgTool('-l'))
        dpkgMenu.add_command(label='sudo dpkg --verify [<package>...]    Verify the integrity of package(s)',
                                      command=lambda: self.genericDpkgTool('--verify'))

        #   -C|--audit [<package>...]        Check for broken package(s).
        dpkgMenu.add_command(label='sudo dpkg --audit [<package>...]     Check for broken package(s)',
                                      command=lambda: self.genericDpkgTool('--audit'))
        #   DEFAULT_DEB_DPKG_LOCATION, DEFAULT_DEB_DPKG_NAME
        dpkgMenu.add_command(label= DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME +  '    Display content of dpkg database',
                                      command=lambda: self.listFileContent(DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME))


        toolsMenu.add_cascade(label='Installed Software', menu=dpkgMenu)

        processMenu = Menu(toolsMenu, tearoff=0)
        processMenu.add_command(label='ps --help all',
                                command=lambda: self.genericProcessesTool('--help all'))
        processMenu.add_command(label='ps -lf -u    Running processes of a specified user',
                                command=lambda: self.genericProcessesTool('-u'))
        processMenu.add_command(label='ps -lf -A    Active processes in generic Unix format',
                                command=lambda: self.genericProcessesTool('-A'))
        processMenu.add_command(label='ps -lf -T    Active processes launched from a terminal',
                                command=lambda: self.genericProcessesTool('-T'))
        processMenu.add_command(label='ps -lf -C    Filter by process name and show children',
                                command=lambda: self.genericProcessesTool('-C'))
        toolsMenu.add_cascade(label='Processes', menu=processMenu)

        processMenu.bind('<Enter>', lambda menuName: self.mouseEnteredMenu(menuName='process'))
        processMenu.bind('<Leave>', lambda menuName: self.mouseExitedMenu(menuName='process'))

        listBLockDevicesMenu = Menu(toolsMenu, tearoff=0)
        listBLockDevicesMenu.add_command(label='lsblk --help',
                                command=lambda: self.genericBlockDevicesTool('--help'))
        listBLockDevicesMenu.add_command(label='lsblk   List information about block devices',
                                command=lambda: self.genericBlockDevicesTool())
        listBLockDevicesMenu.add_command(label='lsblk -f   Include file system type in list',
                                command=lambda: self.genericBlockDevicesTool('-f'))
        listBLockDevicesMenu.add_command(label='lsblk -f --json    Write output in json format',
                                command=lambda: self.genericBlockDevicesTool('-f', '--json'))
        listBLockDevicesMenu.add_command(label='lsblk --output-all    Output all columns',
                                command=lambda: self.genericBlockDevicesTool('--output-all'))
        listBLockDevicesMenu.add_command(label='lsblk --output-all --json    Output all columns in json format',
                                command=lambda: self.genericBlockDevicesTool('--output-all', '--json'))
        toolsMenu.add_cascade(label='Block Devices', menu=listBLockDevicesMenu)

        hashMenu = Menu(toolsMenu, tearoff=0)
        hashMenu.add_command(label='blake2b512', command=lambda: self.hashAndSave('blake2b512'))
        hashMenu.add_command(label='blake2s256', command=lambda: self.hashAndSave('blake2s256'))
        hashMenu.add_command(label='md2', command=lambda: self.hashAndSave('md2'))
        hashMenu.add_command(label='md4', command=lambda: self.hashAndSave('md4'))
        hashMenu.add_command(label='md5', command=lambda: self.hashAndSave('md5'))
        hashMenu.add_command(label='mdc2', command=lambda: self.hashAndSave('mdc2'))
        hashMenu.add_command(label='rmd160', command=lambda: self.hashAndSave('rmd160'))
        hashMenu.add_command(label='sha1', command=lambda: self.hashAndSave('sha1'))
        hashMenu.add_command(label='sha224', command=lambda: self.hashAndSave('sha224'))
        hashMenu.add_command(label='sha256', command=lambda: self.hashAndSave('sha256'))
        hashMenu.add_command(label='sha384', command=lambda: self.hashAndSave('sha384'))
        hashMenu.add_command(label='sha512', command=lambda: self.hashAndSave('sha512'))
        hashMenu.add_command(label='sha3-224', command=lambda: self.hashAndSave('sha3-224'))
        hashMenu.add_command(label='sha3-256', command=lambda: self.hashAndSave('sha3-256'))
        hashMenu.add_command(label='sha3-384', command=lambda: self.hashAndSave('sha3-384'))
        hashMenu.add_command(label='sha3-512', command=lambda: self.hashAndSave('sha3-512'))
        hashMenu.add_command(label='shake128', command=lambda: self.hashAndSave('shake128'))
        hashMenu.add_command(label='sm3', command=lambda: self.hashAndSave('sm3'))

        toolsMenu.add_cascade(label='Hash and Save Output', menu=hashMenu)

        encryptionMenu = Menu(toolsMenu, tearoff=0)
        encryptionMenu.add_command(label='aes128', command=lambda: self.encryptAndSave('aes128'))
        encryptionMenu.add_command(label='aes192', command=lambda: self.encryptAndSave('aes192'))
        encryptionMenu.add_command(label='aes256', command=lambda: self.encryptAndSave('aes256'))
        encryptionMenu.add_command(label='aria128', command=lambda: self.encryptAndSave('aria128'))
        encryptionMenu.add_command(label='aria192', command=lambda: self.encryptAndSave('aria192'))
        encryptionMenu.add_command(label='aria256', command=lambda: self.encryptAndSave('aria256'))
        encryptionMenu.add_command(label='base64', command=lambda: self.encryptAndSave('base64'))
        encryptionMenu.add_command(label='bf', command=lambda: self.encryptAndSave('bf'))
        encryptionMenu.add_command(label='camellia128', command=lambda: self.encryptAndSave('camellia128'))
        encryptionMenu.add_command(label='camellia192', command=lambda: self.encryptAndSave('camellia192'))
        encryptionMenu.add_command(label='camellia256', command=lambda: self.encryptAndSave('camellia256'))
        encryptionMenu.add_command(label='cast', command=lambda: self.encryptAndSave('cast'))
        encryptionMenu.add_command(label='cast5-cbc', command=lambda: self.encryptAndSave('cast5-cbc'))
        encryptionMenu.add_command(label='chacha20', command=lambda: self.encryptAndSave('chacha20'))
        encryptionMenu.add_command(label='des', command=lambda: self.encryptAndSave('des'))
        encryptionMenu.add_command(label='des3', command=lambda: self.encryptAndSave('des3'))
        encryptionMenu.add_command(label='idea', command=lambda: self.encryptAndSave('idea'))
        encryptionMenu.add_command(label='rc2', command=lambda: self.encryptAndSave('rc2'))
        encryptionMenu.add_command(label='rc4', command=lambda: self.encryptAndSave('rc4'))
        encryptionMenu.add_command(label='rc5', command=lambda: self.encryptAndSave('rc5'))
        encryptionMenu.add_command(label='seed', command=lambda: self.encryptAndSave('seed'))
        encryptionMenu.add_command(label='sm4', command=lambda: self.encryptAndSave('sm4'))

        toolsMenu.add_cascade(label='Encrypt and Save Output', menu=encryptionMenu)


        listBLockDevicesMenu.bind('<Enter>', lambda menuName: self.mouseEnteredMenu(menuName='listBLockDevices'))
        listBLockDevicesMenu.bind('<Leave>', lambda menuName: self.mouseExitedMenu(menuName='listBLockDevices'))

        toolsMenu.add_command(label='Select Tool',
                             command=lambda: self.showMessage(title='Select Tool', message="Not implemented yet"))
        toolsMenu.add_command(label='Configure Tool',
                             command=lambda: self.showMessage(title='Configure Tool', message="Not implemented yet"))
        toolsMenu.add_command(label='Pipe Tools',
                             command=lambda: self.showMessage(title='Pipe Tools', message="Not implemented yet"))
        toolsMenu.add_command(label='Tool Manager', command=self.launchToolManager)
        toolsMenu.add_command(label='diff',
                                      command=lambda: self.genericDiffTool('-y'))
        self.add_cascade(label='Tools', menu=toolsMenu)

        self.add_separator()
        volumeIdxMenu = Menu(self, tearoff=0)
        volumeIdxMenu.add_command(label="Scan Folder", command=self.scanFolder)
        volumeIdxMenu.add_command(label="Store Current", command=self.storeCurrentScan)
        volumeIdxMenu.add_command(label="Select Stored", command=self.selectStoredScan)
        volumeIdxMenu.add_command(label="Volume Manager", command=self.manageScannedVolumes)
        self.add_cascade(label="Volume Indexer", menu = volumeIdxMenu)
        self.add_separator()

        helpMenu = Menu(self, tearoff=1)
        self.helpDialogBoolVar = BooleanVar()
        helpMenu.add_checkbutton(label="Help Dialog", variable=self.helpDialogBoolVar, command=self.toggleHelpDialog)
        helpMenu.add_command(label="Current Tasks", command=self.launchTasksHelp)
        self.statusBarBoolVar = BooleanVar()
        helpMenu.add_checkbutton(label="Detail Status Bar", variable=self.statusBarBoolVar,
                                 command=self.toggleDetailStatusBar)
        self.add_cascade(label='Help', menu=helpMenu)

        self.consoleView.config(menu=self)

    def launchToolManager(self):
        print("launchToolManager")

    def selectInfoSource(self, type: DataSourceType):
        print("selectInfoSource:\t" + str(type))

    def scanFolder(self):
        print("scanFolder")

    def storeCurrentScan(self):
        print("storeCurrentScan")

    def selectStoredScan(self):
        print("selectStoredScan")

    def manageScannedVolumes(self):
        print("manageScannedVolumes")

    def messageReceiver(self, message: dict):
        print("messageReceiver:\t" + str(message))
        #               self.listener({"sender": "view.administration", "action": "exited", "status": 'destroyed'})
        if message is not None and isinstance(message, dict):
            if "sender" in message:
                if  message["sender"] == "view.administration":
                    if "status" in message and message["status"] == "destroyed":
                        self.consoleView.adminDialog = None

    def launchAdminDialog(self):
        print("launchAdminDialog")
        if self.consoleView.adminDialog == None:
            self.consoleView.adminDialog = Administration(self.consoleView, "600x500+500+100", self.messageReceiver)
            self.consoleView.adminDialog.mainloop()


    def launchToolManager(self):
        print("launchToolManager")


    def hashAndSave(self, hashType: str):
        print("hashAndSave:\t" + hashType)

    def encryptAndSave(self, encryptionType: str):
        print("encryptAndSave:\t" + encryptionType)

    def toggleHelpDialog(self):
        print("launchHelpDialog:\t" + str(self.helpDialogBoolVar.get()))

        #   Trim the search features available in the general HalpDialog

        if self.helpDialogBoolVar.get():
            if self.consoleView.helpDialog is None:
                self.consoleView.helpDialog = HelpDialog(self.consoleView, HelpContent("General Help", None),
                                                         'helpdialog', "750x500+400+50")
                self.consoleView.helpDialog.mainloop()
        else:
            if self.consoleView.helpDialog is not None:
                self.consoleView.helpDialog.destroy()
                self.consoleView.helpDialog = None

    def launchTasksHelp(self):
        print("launchTasksHelp")

    def toggleDetailStatusBar(self):
        print("toggleDetailStatusBar:\t" + str(self.statusBarBoolVar.get()))

    def showTextView(self):
        print("showTextView")
        self.consoleView.outputFrame.setViewMode('text')

    def showListView(self):
        print("showListView")
        self.consoleView.outputFrame.setViewMode('list')

    def showTreeview(self):
        print("showTreeview")
        self.consoleView.outputFrame.setViewMode('tree')

    def mouseEnteredMenu(self, menuName):
        #   print('mouseEnteredMenu:\t' + str(menuName))
        if menuName=='process':
            self.consoleView.messageLabel.config(text='Processes: Run the ps command with the argument shown')

    def mouseExitedMenu(self, menuName):
        self.consoleView.messageLabel.config(text='Messages')

    def genericJournalctlTool(self, *args):
        print('genericJournalctlTool:\t' + str(args))
        command = 'journalctl'
        for arg in args:
            command += " " + arg
        self.consoleView.commandText.set(command)
        self.consoleView.runLinuxTool()

    def listFileContent(self, filePath: str):
        """
        This currently displays in a list of Packages with each one's fields listed below it.
        This output needs a table to display it.  This can be done in text or it can be done using a Treeview.
        A list of column formatted lines would also work.
        There are 36 different field names and only some are used for each package.  A treeview is most appropriate
        for this purpose.
        A master-slave display would work nicely as well.  List of package names on the left with a property
        sheet showing field values present on the left.
        Use: view.PropertySheetScrollable.py.
        The ability to show all packages for which particular fields are present would also be nice.
        :param filePath:
        :return:
        """
        print("listFileContent:\t" + str(filePath))
        if filePath is None or not isinstance(filePath, str) or not isfile(filePath):
            raise Exception("listFileContent.listFileContent - invalid filePath argument:   " + str(filePath))
        listFile = open(filePath, "r")
        print("Opened:\t" + str(filePath))
        fileContent     = listFile.read()
        print("Read:\t" + str(filePath))
        print("\n" + fileContent)
        listFile.close()
        self.consoleView.outputFrame.outputText.config(state=NORMAL)
        self.consoleView.outputFrame.outputText.delete('1.0', 'end')
        self.consoleView.outputFrame.outputText.insert('end', fileContent)
        self.consoleView.outputFrame.outputText.config(state=DISABLED)

    def genericDpkgTool(self, *args):
        print('genericDpkgTool:\t' + str(args))
        if len(args) == 1 and (args[0] == '--verify' or args[0] == '--audit'):
            #   Must be run under sudo for complete access to all required files when doing comprehensive check.
            #       Is this true for any packages?
            #   Pop up a Toplevel informing the user that the process is running in the background.
            #   Start the command as a process using subprocess.Popen().
            #   When this completes, report status and ask if user would like results displayed in the console
            #   Default is to display the results in the console.

            #   gnome-terminal -- packageVerify.sh
            scriptName = None
            if args[0] == '--verify':
                scriptName = 'packageVerify.sh'
            elif args[0] == '--audit':
                scriptName = 'packageAudit.sh'
            if scriptName is not None:
                shellScriptCommand = pathFromList((INSTALLATION_FOLDER, scriptName))
                argv = []
                argv.append('gnome-terminal')
                argv.append('--')
                argv.append(shellScriptCommand)
                sub = Popen(argv, stdout=PIPE, stderr=STDOUT)
                lastCommandRunTime = str(datetime.now())
                output, error_message = sub.communicate()
                print('output:\t' + output.decode('utf-8'))
            
        else:
            command = 'dpkg'
            for arg in args:
                command += " " + arg
            self.consoleView.commandText.set(command)
            self.consoleView.runLinuxTool()

    def genericBlockDevicesTool(self, *args):
        print('genericBlockDevicesTool:\t' + str(args))
        command = 'lsblk'
        for arg in args:
            command += " " + arg
        self.consoleView.commandText.set(command)
        self.consoleView.runLinuxTool()

    def genericProcessesTool(self, *args):
        #   print('genericProcTool:\t' + str(args))
        #   messagebox.showinfo('Generic proc Tools', 'Not Implemented Yet')
        if len(args) == 1:
            if args[0] == '-u':
                #   enter user name first
                optionEntryDialog = OptionEntryDialog(self.consoleView, optionName='User Name', type='text',
                                                        callback=self.processOptionCallback,
                                                        validator=self.userNameValidator)
                optionEntryDialog.titleString('Enter: User Name')
                optionEntryDialog.geometryString("275x100+250+100")
                optionEntryDialog.mainloop()
            elif args[0] == '-C':
                #   enter process name filter first
                #   this can actually be a list of process names
                optionEntryDialog = OptionEntryDialog(self.consoleView, optionName='Process Name', type='text',
                                                        callback=self.processOptionCallback,
                                                        validator=self.processNameValidator)
                optionEntryDialog.titleString('Enter: Process Name')
                optionEntryDialog.geometryString("275x100+250+100")
                optionEntryDialog.mainloop()
            else:
                self.consoleView.commandText.set('ps -lf ' + args[0])
                self.consoleView.runLinuxTool()

    def processOptionCallback(self, **keyWordArguments):
        print('processOptionCallback:\t' + str(keyWordArguments))
        if "optionName" in keyWordArguments and 'entry' in keyWordArguments:
            if keyWordArguments["optionName"] == 'User Name':
                self.consoleView.commandText.set('ps -u ' + keyWordArguments['entry'])
                self.consoleView.runLinuxTool()
            elif keyWordArguments["optionName"] == 'Process Name':
                self.consoleView.commandText.set('ps -C ' + keyWordArguments['entry'])
                self.consoleView.runLinuxTool()

    def processNameValidator(self, processName: str):
        return None

    def userNameValidator(self, userName: str):
        print('userNameValidator:\t' + str(userName))
        issues = False
        if userName is None or not isinstance(userName, str):
            issues = True
        for char in userName:
            if not char.isalnum() and char not in ('_', '.', '-', '@', '$'):
                issues = True
        if not issues:
            if '$' in userName and not userName.endswith('$'):
                issues = True
            elif '-' in userName and userName.startswith('-'):
                issues = True
        if not issues:
            return None
        return 'User name is invalid.\nOnly letters, digits, underscores, \nperiods, dashes, @, and $ are allowed.\n' + \
               'The name may not start with a dash, \nand lower case letters are recommended.\n' + \
               '$ is optional and may only appear at the end.'

    def genericDiffTool(self, *args):
        """
        Select two files to compare using th built in file selection dialog.
        Display their names in order so that diff is visibly done to show changed in first required to produce second.
        Run the diff -y generic tool on them.
        display the human readable results in the console.
        Provide means for user to switch between the diff -y outout and the DiffParseResult.
        Provide means of switching on and off detail on diff and stats of files compared.
        :param args:
        :return:
        """
        print('genericDiffTool:\t' + str(args))
        messagebox.showinfo('Generic diff Tools', 'Not Implemented Yet')

    def showMessage(self, **keyWordArguments):
        messagebox.showinfo(keyWordArguments['title'], keyWordArguments['message'])

    def redirectOutput(self, **keyWordArguments):
        if 'text' not in keyWordArguments:
            raise Exception('redirectOutput - text argument missing')
        if not isinstance(keyWordArguments['text'], str):
            raise Exception('redirectOutput - invalid text argument:    ' + str(keyWordArguments['text']))
        if 'target' not in keyWordArguments:
            raise Exception('redirectOutput - target argument missing')
        if not isinstance(keyWordArguments['target'], str) or keyWordArguments['target'] not in ('file', 'dbTable'):
            raise Exception('redirectOutput - invalid target argument:    ' + str(keyWordArguments['target']))
        if 'commandText' not in keyWordArguments:
            raise Exception('redirectOutput - commandText argument missing')
        if not isinstance(keyWordArguments['commandText'], str):
            raise Exception('redirectOutput - invalid commandText argument:    ' + str(keyWordArguments['commandText']))

        #   print('ConsoleMenuBar.redirectOutput:\t' + str(keyWordArguments))

        #   File Option:
        if keyWordArguments['target'] == 'file':
            """
            USER_DATA_FOLDER = 'userData'
            SAVED_CONSOLE_OUT_FOLDER = 'consoleOutput'
            CONSOLE_OUT_TEXT_FOLDER = 'consoleOutput/text'
            CONSOLE_OUT_DB_FOLDER = 'consoleOutput/database'
            USER_LOG_ARCHIVES_FOLDER = 'logArchives'
        
            USER_CONSOLE_OUT_DB = 'ConsoleOutput.db'
            """
            filePath = INSTALLATION_FOLDER + '/' + USER_DATA_FOLDER + '/' + CONSOLE_OUT_TEXT_FOLDER
            if isdir(filePath):
                print("Found:\t" + filePath)
                print('\tCreating file for text output of command:\t' + keyWordArguments['commandText'])
                print('\tRun at:\t' + str(self.consoleView.lastCommandRunTime))
                if self.consoleView.lastCommandRunTime is None:
                    messagebox.showinfo('Save Console Output to File', 'You must run a command before saving it output' )
                else:
                    """
                    The file name will be in an index table with the time stamp and the command text as the 
                    key field of the table.  This can be done using both a json file and an SQLite table
                    dedicated to this purpose, and probably should be done in both for visibility, with a
                    warning to the user not to change the json file.
                    An integrity check can be done on start-up and at various other times for application
                    security.
                    """
                    commandLine = keyWordArguments['commandText'].split(' ')
                    command = commandLine[0]
                    fileName = str(self.consoleView.lastCommandRunTime) + ' ' + command
                    del (commandLine[0])
                    if len(commandLine) >= 1:
                        commandLine = tuple(commandLine)
                        fileName += ' ' + str(commandLine)
                    fileName += '.cmd_out'
                    messagebox.showinfo('File Name for Output', fileName )
                    jsonIndex   = JsonIndex(indexFileName='consoleOutArchive.index', archiveType='console output archive')
                    jsonIndex.addEntry('console output archive', 'consoleOutArchive.index',
                                       {"command": command, 'args': commandLine,
                                        'timeStamp': str(self.consoleView.lastCommandRunTime),
                                     'project': None, 'analysis': None, 'workflow': None, 'notes': '',
                                     'fileName': fileName, 'contentName': None})
                    contentFilePath = INSTALLATION_FOLDER + '/' + USER_DATA_FOLDER + '/' + CONSOLE_OUT_TEXT_FOLDER + '/' + \
                                    fileName
                    contentFile     = open(contentFilePath, 'w')
                    contentFile.write(keyWordArguments['text'])
                    contentFile.close()

            else:
                messagebox.showerror('Save Console Output to File',
                                     'Folder for console output files does not exist:\n' + filePath)

        #   DB Table Option:
        elif keyWordArguments['target'] == 'dbTable':
            argv = keyWordArguments['commandText'].split()
            if argv[0] == 'dpkg' and '-lf' in argv:      #   CHECK: always same tabular format with '-l' option?
                #   Assumption: -l in the argv means:
                #   The four fields in each line, in order, are: Name, Version, Architecture, and Description
                saveDpkg_l_OutputToDB(argv, keyWordArguments['text'])
            elif argv[0] == 'ps' and len(argv) == 3 and '-lf' in argv and '-A' in argv:
                #   ps -l -A
                savePs_lf_A_OutputToDB(argv, keyWordArguments['text'])
            #   journalctl --system --lines=1000 -o json
            elif argv[0] == "journalctl" and len(argv) == 5 and "-o" in argv and "json" in argv:
                print("journalctl --system --lines=1000 -o json ==>> SQLite DB Table")
                journalctl_o_json_OutputToDB(argv, keyWordArguments['text'])


class ExfoliateCopyOptions(LabelFrame):

    def __init__(self, container, listener, **keyWordArguments):
        LabelFrame.__init__(self, container, keyWordArguments)
        self.listener = None
        if listener is not None:
            if callable(listener):
                self.listener = listener
        self.exfoliateVar = BooleanVar()
        self.moveToCacheVar = BooleanVar()
        self.checkBoxExfoliate = Checkbutton(self, text="Exfoliate", variable=self.exfoliateVar,
                                             border=2, relief=RIDGE)
        self.checkBoxMoveToCache = Checkbutton(self, text="Move to Cache", variable=self.moveToCacheVar,
                                               border=2, relief=RIDGE)
        self.exfoliateVar.set(True)
        self.moveToCacheVar.set(True)
        self.buttonProceed = Button(self, text="Proceed", border=4, command=self.proceedClicked )
        self.buttonCancel = Button(self, text="Cancel", border=4, command=self.cancelClicked )

        self.checkBoxExfoliate.grid(row=0, column=0, padx=5, pady=5, sticky='nw')
        self.checkBoxMoveToCache.grid(row=1, column=0, padx=5, pady=5, sticky='nw')
        self.buttonProceed.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.buttonCancel.grid(row=2, column=1, padx=5, pady=5, sticky='e')

    def proceedClicked(self):
        self.destroy()
        if self.listener is not None:
            self.listener({'sender': "ExfoliateCopyOptions", "action": "proceed",
                           "options": {"exfoliate": self.exfoliateVar.get(), "move2cache": self.moveToCacheVar.get()}})

    def cancelClicked(self):
        self.destroy()
        if self.listener is not None:
            self.listener({'sender': "ExfoliateCopyOptions", "action": "cancel"})


class ConsoleView(Toplevel):

    HELP_TEXT   = 'Please only use actual characters you find on your keyboard.\n' \
                  'Alt-Key and Ctrl-Key combinations, for example, are not allowed and are ignored.\n' \
                  'Allowed characters include upper and lower case letters, numbers, and any of:\n' \
                  '~ ` ! @ # $ % ^ & * ( ) _ - + = [ ] { } | ; : , < . > ?' \
                  'This list includes any printable character except single and double quotes,' \
                  'backslash and forward slash'

    NON_ALPHANUMS = ('~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '-', '+', '=', '[', ']',
                    '{', '}', '|', ';', ':', ',', '<', '.', '>', '?')

    def __init__(self, container, geometry, title, **keyWordArguments):
        if geometry is None or not isinstance(geometry, str):
            raise Exception('MainView constructor: geometry argument is invalid:    ' + str(geometry) )
        if title is None or not isinstance(title, str):
            raise Exception('MainView constructor: title argument is invalid:    ' + str(title) )

        super().__init__(container)
        self.geometry(geometry)
        self.title(title)
        #   self.configuration = Configuration()        #   LinuxLogForensics/model/Configuration.LLF.Configuration
        self.adminDialog = None
        self.menuBar = ConsoleMenuBar(self)
        self.helpDialog = None
        self.helpAndApproval = None
        self.exfoliateOptionsToplevel = None
        self.exfoliateOptions = None

        self.lastCommandRunTime     = None
        self.commandText = StringVar()
        self.commandText.set('dpkg -l')
        self.keyCount = 0
        #   The command label can also display a prompt from the Linux OS
        self.commandLineLabel   = Label(self, text='Command', border=2, relief=RIDGE, padx=10)
        self.commandLineEntry   = Entry(self, border=3, relief=RIDGE, textvariable=self.commandText)
        self.commandLineEntry.bind('<Key>', self.keyPressed)

        self.outputFrame    = OutputFrame(self, border=3, relief=SUNKEN, padx=5, pady=5)

        self.messageLabel   = Label(self, text='messages', border=3, relief=RIDGE)

        self.commandLineLabel.pack(padx=2, pady=2, anchor=W)
        self.commandLineEntry.pack(fill=X, expand=True, padx=10)
        self.outputFrame.pack(fill=BOTH, expand=True, padx=2, pady=2)
        self.messageLabel.pack(fill=X, expand=True, padx=3, pady=3)

    def messageReceiver(self, message: dict):
        print("messageReceiver:\t" + str(message))
        if isinstance(message, dict):
            if "sender" in message:
                if message["sender"] == "HelpAndApproval.sendGoMessage":
                    if "title" in message:
                        if message['title'] == FEATURE_NAME_IMAGE_LOGS:
                            self.launchCD_DVD_logISO()


                        elif message['title'] == FEATURE_NAME_ISO_IMAGE_FOLDER:
                            self.launchFolderToISO()


                        elif message['title'] == FEATURE_NAME_EXFOLIATE_FOLDER:
                            self.exfoliateOptionsToplevel = Toplevel(self, border=5, relief=RAISED)
                            self.exfoliateOptionsToplevel.geometry("300x150+600+300")
                            self.exfoliateOptionsToplevel.title("Exfoliate and Move Options")
                            exfoliateCopyOptions = ExfoliateCopyOptions(self.exfoliateOptionsToplevel, self.messageReceiver,
                                                                        border=3, relief=GROOVE)
                            exfoliateCopyOptions.pack(expand=True, fill=BOTH)
                            self.exfoliateOptionsToplevel.mainloop()

                        elif message['title'] == "Exfoliate: Final Approval":
                            self.helpAndApproval.destroy()
                            self.helpAndApproval = None
                            if self.exfoliateOptions is not None:

                                if self.exfoliateOptions["move2cache"]:
                                    print("Copying Folder:\t" + self.exfoliateOptions['folderPath'])
                                    print("\tTo:\t" + USER_CACHE_FOLDER )
                                    if not isdir(USER_CACHE_FOLDER):
                                        raise Exception("Making Cache Copy of Folder - User Cache Folder, Destination, "
                                                        "Does Not Exist:\t" + USER_CACHE_FOLDER)
                                    #   Construct entire path to the source folder in the user cache folder:
                                    pathParts = self.exfoliateOptions['folderPath'].split('/')[1:]
                                    destinationFolder = USER_CACHE_FOLDER + '/' + pathParts[len(pathParts)-1]
                                    print("Source:\t" + self.exfoliateOptions['folderPath'])
                                    print("Destination:\t" + destinationFolder)
                                    copytree(self.exfoliateOptions['folderPath'], destinationFolder)

                                if self.exfoliateOptions["exfoliate"]:
                                    print("EXFOLIATING:\t" + self.exfoliateOptions['folderPath'])
                                    for (dirpath, dirs, files) in walk(self.exfoliateOptions['folderPath'],
                                                                          topdown=True, onerror=None, followlinks=False):
                                        if len(files) > 0:
                                            for file in files:
                                                filePath = pathFromList((dirpath, file))
                                                print("Deleting:\t" + filePath)
                                                remove(filePath)


                elif message["sender"] == "HelpAndApproval.sendCancelMessage":
                    if "title" in message:
                        if message['title'] in ( FEATURE_NAME_IMAGE_LOGS, FEATURE_NAME_ISO_IMAGE_FOLDER,
                                                 FEATURE_NAME_EXFOLIATE_FOLDER,"Exfoliate: Final Approval"):
                            if self.helpAndApproval is not None:
                                self.helpAndApproval.destroy()
                                self.helpAndApproval = None


                #   {'sender': "ExfoliateCopyOptions", "action": "proceed",
                #               "options": {"exfoliate": self.exfoliateVar.get(), "move2cache": self.moveToCacheVar.get()}}
                elif message['sender'] == "ExfoliateCopyOptions":
                    if "action" in message:
                        if message['action'] == 'proceed':
                            self.exfoliateOptionsToplevel.destroy()
                            if "options" in message and isinstance(message['options'], dict):
                                exfoliate = False
                                if 'exfoliate' in message['options'] and isinstance(message['options']['exfoliate'], bool):
                                    exfoliate = message['options']['exfoliate']
                                move2cache  = False
                                if 'move2cache' in message['options'] and isinstance(message['options']['move2cache'], bool):
                                    move2cache = message['options']['move2cache']

                                if move2cache:
                                    pass

                                if exfoliate:
                                    folderPath = filedialog.askdirectory(title=FEATURE_NAME_EXFOLIATE_FOLDER,
                                                                       initialdir=environ["HOME"], parent=self)
                                    print("Exfoliating:\t" + str(folderPath))
                                    if not isinstance(folderPath, str):     #   user made no selection or multiple selections
                                        return
                                    finalApprovalHelp = "Do you want to proceed with the following operations on:\n\n\t" \
                                                        + folderPath + "?\n\n"
                                    if 'options' in message:
                                        self.exfoliateOptions = message['options']
                                        print("\toptions:\t" + str(self.exfoliateOptions))
                                        if self.exfoliateOptions["exfoliate"]:
                                            finalApprovalHelp   += "\tExfoliate the folder\n"
                                        if self.exfoliateOptions["move2cache"]:
                                            finalApprovalHelp   += "\tMove the folder to cache before exfoliating\n"
                                    if self.exfoliateOptions['exfoliate'] or self.exfoliateOptions['move2cache']:
                                        self.exfoliateOptions['folderPath']     = folderPath
                                    self.helpAndApproval.destroy()
                                    self.helpAndApproval = HelpAndApproval(self, "Exfoliate: Final Approval", finalApprovalHelp,
                                                    "500x325+400+250", self.messageReceiver, border=4, relief=RAISED)

                        elif message['action'] == 'cancel':
                            self.exfoliateOptionsToplevel.destroy()

    def makeLogFolderImage(self):
        self.helpAndApproval  = HelpAndApproval( self, FEATURE_NAME_IMAGE_LOGS, HELP_LOG_FOLDER_IMAGE, "800x450+200+150",
                                            self.messageReceiver, border=5, relief=RAISED)
        self.helpAndApproval.mainloop()



    def mountLogFolderImage(self):
        print("mountLogFolderImage")
        shellScriptCommand = pathFromList((INSTALLATION_FOLDER, 'mountISO.sh'))
        print('RUNNING IN TERMINAL shellScriptCommand:\t' + shellScriptCommand)
        #   gnome-terminal -- ./mountISO.sh
        argv = []
        argv.append('gnome-terminal')
        argv.append('--')
        argv.append(shellScriptCommand)
        argv.append(INSTALLATION_FOLDER)
        sub = Popen(argv, stdout=PIPE, stderr=STDOUT)
        lastCommandRunTime = str(datetime.now())
        output, error_message = sub.communicate()

    def makeFolderImage(self):
        print("ConsoleView.makeFolderImage")
        self.helpAndApproval  = HelpAndApproval( self, FEATURE_NAME_ISO_IMAGE_FOLDER, HELP_FOLDER_IMAGE, "800x325+200+150",
                                            self.messageReceiver, border=5, relief=RAISED)
        self.helpAndApproval.mainloop()

    def mountFolderImage(self):
        print("ConsoleView.mountFolderImage")

    def exfoliateFolder(self):
        print("ConsoleView.exfoliateFolder")
        self.helpAndApproval  = HelpAndApproval( self, FEATURE_NAME_EXFOLIATE_FOLDER, EXFOLIATE_FOLDER_HELP, "800x400+200+150",
                                            self.messageReceiver, border=5, relief=RAISED)
        self.helpAndApproval.mainloop()


    def launchFolderToISO(self):
        print("launchFolderToISO")
        #   get user's selection of folder to copy to ISO
        folderPath = filedialog.askdirectory(initialdir=environ["HOME"])
        if isinstance(folderPath, tuple):
            folderPath = folderPath[0]
        if isinstance(folderPath, str) and isdir(folderPath):
            shellScriptCommand = pathFromList((INSTALLATION_FOLDER, 'foldertoISO.sh'))
            print('RUNNING IN TERMINAL shellScriptCommand:\t' + shellScriptCommand)

            isoFileName = folderPath.replace('/', '_') + ".iso"
            #   Check and warn: Does target *.iso file name already exist.
            #   If so, pick a path or rename.

            argv = ['gnome-terminal', '--', shellScriptCommand, INSTALLATION_FOLDER, folderPath, isoFileName]
            sub = Popen(argv, stdout=PIPE, stderr=STDOUT)
            lastCommandRunTime = str(datetime.now())
            output, error_message = sub.communicate()
            if self.helpAndApproval is not None:
                self.helpAndApproval.destroy()
                self.helpAndApproval = None

            return True
        print("Could not make ISO of selected folder:\t" + folderPath, file=stderr)

    def launchCD_DVD_logISO(self):
        print("launchCD_DVD_logISO")
        shellScriptCommand = pathFromList((INSTALLATION_FOLDER, 'logFoldertoISO.sh'))
        print('RUNNING IN TERMINAL shellScriptCommand:\t' + shellScriptCommand)
        #   gnome-terminal -- ./logFoldertoISO.sh
        argv = []
        argv.append('gnome-terminal')
        argv.append('--')
        argv.append(shellScriptCommand)
        argv.append(INSTALLATION_FOLDER)
        sub = Popen(argv, stdout=PIPE, stderr=STDOUT)
        lastCommandRunTime = str(datetime.now())
        output, error_message = sub.communicate()

        #   print('output:\t' + output.decode('utf-8'))

        #   Notify any other processes listening to the ram disk that this application has started and therefore
        #   can send and receive files using the ramdisk.
        timeStamp = '"' + str(datetime.now()) + '"'
        """
        startNoticeFile = open(ramDiskMountPoint + "/service.Cache.py.start.json", 'w')
        print("File opened on RAM disk:\t" + ramDiskMountPoint + "/service.Cache.py.start.json")
        programName = '"service.Cache.py"'
        programState = '"started"'
        report = loads('{"appName": ' + programName +
                            ', "appState": ' + programState +
                            ', "timeStamp": ' + timeStamp + '}')
        print(report)
        dump(report, startNoticeFile)
        """

    def keyPressed(self, event):
        #   print('keyPressed event:\t' + str(event))
        #   print('keyPressed event.state:\t' + str(event.state))
        #   keysym in ('Control_L', 'Control_R', 'Alt_L', 'Alt_R' )
        #   state in ('Control'=4,'Control|Mod1'=12, 'Mod1'=8 )
        valid = False
        if event.state == 0:        #   not Ctrl or Alt combination
            if self.isCommandChar(event.char):
                #   disable for now:
                #   if self.keyCount == 0:
                #       self.commandText.set('')
                self.keyCount += 1
                valid = True
            elif event.char == '\r':
                self.runLinuxTool()
                valid = True
        """
        if not valid:
            if self.helpLabel == None:
                self.container.geometry('350x275+150+100')
                self.helpLabel  = Label(self, height=10, width=40, border=3, relief=SUNKEN, fg="#002277",
                                        text=ConsoleView.HELP_TEXT, justify=LEFT, wraplength=320)
                self.helpLabel.grid(row=2, column=0, columnspan=3, pady=10)
        """

    def isCommandChar(self, ch: str):
        if ch is None or not isinstance(ch, str) or len(ch) != 1:
            return False
        return ch in ConsoleView.NON_ALPHANUMS or ch.isalpha() or ch.isdigit()


    def runLinuxTool(self):
        commandList     = self.commandText.get().split(' ')
        print('commandList:\t' + str(commandList))
        try:
            sub     = Popen(commandList, stdout=PIPE, stderr=STDOUT )
            self.lastCommandRunTime = datetime.now()
            output, error_message = sub.communicate()
            outputText  = output.decode('utf-8')
        except Exception:
            outputText = ''
            for line in exc_info():
                outputText += str(line) + '\n'

        self.outputFrame.setContent(outputText, commandList)


def ExitProgram():
    answer = messagebox.askyesno('Exit program ', "Exit Linux Console Application?")
    if answer:
        mainView.destroy()


if __name__ == '__main__':
    mainView = Tk()
    consoleView = ConsoleView( mainView, '1000x550+50+50', 'Linux Console')
    mainView.protocol('WM_DELETE_WINDOW',  ExitProgram)
    consoleView.mainloop()
