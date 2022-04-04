#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   January 30, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         Configuration
#   Purpose:        Gateway to the application's SQLite database.
#   Development:
#       Scan entire volume or sub volume (folder, directory) and create a database table the name of which is the
#       folder / directory name containing all or the information obtainable on each file and directory contained
#       in it each in one record in the table.  The tables created can then be used for various searches of the
#       subject volume or volume set which include keywords in the file names or paths as well as the various file
#       meta-data.
#   Location:
#       /home/keithcollins/PycharmProjects/VolumeIndexer/model/Configuration.py

import os
import os.path as path
import datetime
import sqlite3

class Configuration:
    USER_HOME                   = "/home/keithcollins/"
    #   USER_HOME                   = "/home/keith/"

    USER_ROOT                   = "/root/"

    APPLICATION_DB_NAME         = "VolumeIndexer.db"
    DEFAULT_START_DIRECTORY     = "/"

    APPLICATION_FOLDER          =  USER_HOME + "VolumeIndexer/"
    #APPLICATION_FOLDER          =  USER_ROOT + "VolumeIndexer/"

    LOG_FOLDER                  = ".Logging/"
    LOG_FOLDER_                 = "Logging/"
    LOG_FILE                    = "GeneralApplicationLog.vi"
    DATABASE_FILE_NAME          = "VolumeScanner.db"
    GUI_DB_NAME                 = "VolumeIndexerGUI"


    LINUX_STAT_FIELD_NAMES          = ( 'name', 'path', 'inode', 'is_dir', 'is_file', 'is_symlink',
                                        'st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid',
                                        'st_gid', 'st_size', 'st_atime', 'st_mtime', 'st_ctime')

    LINUX_FIELD_NAME_DEFAULT_ORDER  = ( 'name', 'path', 'st_size', 'st_ctime', 'st_mtime', 'st_atime',
                                        'is_file', 'is_dir', 'is_symlink', 'st_uid', 'st_gid', 'st_mode',
                                        'inode', 'st_ino', 'st_dev', 'st_nlink')

    LINUX_FIELD_COMMON_NAMES        = { 'name': 'File name',
                                        'path': 'Directory path',
                                        'st_size': 'Size in byte',
                                        'st_ctime': 'Time created',
                                        'st_mtime': 'Time last modified',
                                        'st_atime': 'Time last accessed',
                                        'is_file': 'Is a file',
                                        'is_dir': 'Is a directory',
                                        'is_symlink': 'Is a symbolic link',
                                        'st_uid': 'User / Owner identifier',
                                        'st_gid': 'Group identifier',
                                        'st_mode': 'Access permissions',
                                        'inode': 'File system node index',
                                        'st_ino': 'Dont know this one',
                                        'st_dev': 'OS device identifier',
                                        'st_nlink': 'Numbers of symbolic lints to this'}

    LINUX_STAT_FIELD_IDS        = {'name': 0,       'path': 1,          'inode': 2,         'is_dir': 3,
                                   'is_file': 4,    'is_symlink': 5,    'st_mode': 6,       'st_ino': 7,
                                   'st_dev': 8,     'st_nlink': 9,      'st_uid': 10,       'st_gid': 11,
                                   'st_size': 12,   'st_atime': 13,     'st_mtime': 14,     'st_ctime': 15}


    #   The type the user sees
    LINUX_STAT_FIELD_TYPE_MAP   = { 'name': 'Text', 'path': 'Text', 'inode': 'Integer', 'is_dir': 'Boolean',
                                    'is_file': 'Boolean', 'is_symlink': 'Boolean', 'st_mode': 'Integer',
                                    'st_ino': 'Integer', 'st_dev': 'Integer', 'st_nlink': 'Integer',
                                    'st_uid': 'Integer', 'st_gid': 'Integer', 'st_size': 'Integer',
                                    'st_atime': 'DateTime', 'st_mtime': 'DateTime', 'st_ctime': 'DateTime'}

    DATA_TYPES                  = ('Any', 'Text', 'Real', 'Integer', 'Date', 'Time', 'Boolean', 'eMail Address', 'URL',
                                   'File Path', 'File Name')

    #   Help text for types
    LINUX_STAT_FIELD_HELP =  {'name': 'The file\'s name',
                              'path': 'The directory path to the file on the drive partition',
                              'inode': 'The inode, or internal index number of the file',
                              'is_dir': 'Is the entry a directory?',
                              'is_file': 'Is the entry a file?',
                              'is_symlink': 'Is the entry a symbolic link to another file or directory?',
                              'st_mode': 'Integer',
                              'st_ino': 'Integer',
                              'st_dev': 'Integer',
                              'st_nlink': 'Integer',
                              'st_uid': 'The identifier of the user who owns the the entry',
                              'st_gid': 'The identifier of the group the owning user belongs to',
                              'st_size': 'The size of the file / folder in bytes.  For a folder, this is the size of the record describing the folder, not its contents.',
                              'st_atime': 'The date-time the file was last accessed',
                              'st_mtime': 'The date-time the file was last modified',
                              'st_ctime': 'The date-time the file was created'
                              }

    #   type user sees ==> type SQLite uses.
    SQLITE_TYPE_MAP             = { 'Text': 'text', 'Integer': 'integer', 'Boolean': 'tinyint', 'Real': 'real',
                                    'DateTime': 'real', 'Date': 'real', 'Time': 'real', 'eMail Addr': 'text',
                                    'URL': 'text', 'File Path': 'text', 'File Name': 'text' }

    def __init__(self):
        #print( "Configuration running")
        #print( "Verifying application folders")
        pass

    def verifyConfiguration(self):
        if path.isdir(Configuration.APPLICATION_FOLDER):
            if path.isdir(Configuration.APPLICATION_FOLDER+Configuration.LOG_FOLDER):
                if path.isfile(Configuration.APPLICATION_FOLDER+Configuration.LOG_FOLDER+Configuration.LOG_FILE):
                    logFile     = open(Configuration.APPLICATION_FOLDER+Configuration.LOG_FOLDER+Configuration.LOG_FILE,"a")
                    logFile.write("ApplicationStarted:\t" + str(datetime.datetime.now()) + "\n")
                    logFile.close()

    try:
        logFile = open(APPLICATION_FOLDER + LOG_FOLDER + LOG_FILE, "a")
        logFile.write("LogFileStarted:\t" + str(datetime.datetime.now()) + "\n")
        logFile.close()
    except:
        try:
            os.mkdir(APPLICATION_FOLDER + LOG_FOLDER)
            os.mkdir(APPLICATION_FOLDER + LOG_FOLDER_)
            logFile = open(APPLICATION_FOLDER + LOG_FOLDER + LOG_FILE, "a")
            logFile.write("LogFileStarted:\t" + str(datetime.datetime.now()) + "\n")
            logFile.close()
        except:
            try:
                if not os.path.isdir(APPLICATION_FOLDER):
                    os.mkdir(APPLICATION_FOLDER)
                if not os.path.isdir(APPLICATION_FOLDER + LOG_FOLDER):
                    os.mkdir(APPLICATION_FOLDER + LOG_FOLDER)
                if not os.path.isdir(APPLICATION_FOLDER + LOG_FOLDER_):
                    os.mkdir(APPLICATION_FOLDER + LOG_FOLDER_)
                logFile = open(APPLICATION_FOLDER + LOG_FOLDER + LOG_FILE, "a")
                logFile.write("LogFileStarted:\t" + str(datetime.datetime.now()) + "\n")
                logFile.close()
            except Exception:
                print("ERROR: unable to create application log file:\t" + APPLICATION_FOLDER + LOG_FOLDER + LOG_FILE)
                exit(1)

    #   Now configure the db file
    #   If it already exists, get the information needed to start working with volume indexes already created
    #   If not, make the database.
    #   Should all information possible be gathered or should user be allowed to include and exclude particular
    #   fields from a table.  If not, the table display needs to be able to show/hide selected fields.

    try:    #   make a db table for the scanner feature
        #   print("sqlite3.version_info:\t" + str(sqlite3.sqlite_version))

        #   for temporary work spaces:
        #   dbConnection = sqlite3.connect(":memory:")
        dbConnection = sqlite3.connect(APPLICATION_FOLDER + "VolumeScanner.db")
        dbConnection.close()
    except:
        print("ERROR: database connection failed")


    #   If the attribute name already exists when attempt is mad to set an attribute's value,
    #   do not allow it.  All declared attributes of a Config object are constants.
    #   The user can, however add attributes that do not already exist.
    def __setattr__(self, key, value):
        print( "Setting " + str(key) + " to:\t" + str(value) )
        print(Configuration.__dict__.items())
        #if not self.__dict__.has_key(key):
        #    self.__dict__[key]  = value
        #print ( str(key) + ":\t" + str(self.__dict__[key]) )


if __name__ == "__main__":
    config = Configuration()
    print( "Configuration.APPLICATION_DB_NAME:\t" + Configuration.APPLICATION_DB_NAME)
    if config.verifyConfiguration():
        pass
