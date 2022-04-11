#   Project:        LinuxTools
#   Imported From:  File Volume Indexer
#   Date Imported:  April 8, 2022
#   Author:         George Keith Watson
#   Module:         service/tools/dpkg.py
#   Date Started:   August 20, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Purpose:        For debian linux os's, dpkg-query command line application retrieves information from the installed
#                   application database.  This module provides an API for working with that information.
#   Development:
#       Possible uses include ability custom map file types to applications that can use them.
#
#       MOVED TO:   LinuxLogForensics on 2021-08-21
#   Project:        LinuxLogForensics
#   Author:         George Keith Watson
#   Module:         service/tools/dpkg.py
#   Date Started:   August 21, 2021
#   Copyright:      (c) Copyright 2019, 2021 George Keith Watson
#   Purpose:        For debian linux os's, dpkg-query command line application retrieves information from the installed
#                   application database.  This module provides an API for working with that information.
#   Development:
#       Reviewing the information in the file that this module collects information from and comparing it to that
#       available with the dpkg command, there are many fields in the dpkg database file that are not present
#       in the dpkg listing (dpkg -l), which the --help page admits is a 'concise' table of information.
#       This information needs to be available to the user and can easily be imported into a database table,
#       timestamped for tracking and updating.
#       Feature:    on each update to a table tracking installations, only include entries that have changed
#       since the previous entry for the package.  Also, need a field for 'deleted' packages, i.e. a boolean or
#       a text fields for the package's current status, or both for integrity checking.
#

from os import path
from sys import exc_info
from traceback import format_tb

DEFAULT_DEB_DPKG_LOCATION = "/var/lib/dpkg/"  # a large plain text file with a parse-able format
DEFAULT_DEB_DPKG_NAME = "status"


class DpkgDB:

    """
    Format of this file is a single field per line with the name at the left edge, followed by a colon then the value.
        If the value is more than one line long, as happens frequently in the description field, then the extra lines
        start with a whitespace character.
    """
    FLAG_NAME_DATA_FOLDER_EXISTS    = "DataFolderExists"
    FLAG_NAME_DATA_FILE_EXISTS      = "DataFileExists"
    FLAG_NAME_DATA_FILE_CAN_READ    = "DataFileCanRead"
    FLAG_NAME_DATA_FILE_READ        = "DataFileRead"


    def __init__(self):
        self.getPackageInfo()
        print("\n" + str( self.dpkgDBFileStatus ))
        self.exceptionInfo  = None


    def getPackageInfo(self):
        self.dpkgDBFileStatus   = {}
        if path.isdir( DEFAULT_DEB_DPKG_LOCATION ):
            self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FOLDER_EXISTS ]     = True
            if path.isfile( DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME ):
                self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FILE_EXISTS ] = True

                #   record of packages installed according to this file / database.
                #   level 1 key is the package name, and its value is another map.
                #   level 2 key is the field name, and its value is the field value.
                self.DPKG_DB        = {}
                self.packageNames   = []
                self.fieldNames     = []


                #   if the database file cannot be read or doesn't exist, need to use dpkg-query command line tool
                #   instead and parse its output format.
                try:
                    dpkgFile    = open( DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME, "r" )
                    self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FILE_CAN_READ ] = True

                    currentPackageName  = None
                    currentFieldName    = None
                    recordCount = 0
                    #    minimize buffering by using real-time line stream reading method
                    for line in dpkgFile:
                        #print( "LINE READ:\t" + line )
                        if currentPackageName is None:      #   beginning of a package record
                            if len( line.strip() ) != 0:
                                if line.startswith("Package"):
                                    nameValue   = line.split(':')
                                    currentPackageName = nameValue[1].strip()
                                    if not currentPackageName in self.packageNames:
                                        self.packageNames.append(currentPackageName)
                                    print("New package:\t" + currentPackageName)
                                    self.DPKG_DB[currentPackageName]  = {}
                                    recordCount += 1
                                    self.DPKG_DB[currentPackageName]["recordNumber"] = recordCount
                            else:   #   blank line between package records
                                pass
                        else:           #   next field in a package record
                            if len( line.strip() ) == 0:    #   end of current package record found
                                currentPackageName = None
                            else:
                                if line[0].isspace():   #   new line of field value text
                                    self.DPKG_DB[currentPackageName][currentFieldName] += " " + line.strip()
                                else:                   #   new field
                                    nameValue = line.split(':')
                                    #print ( nameValue )
                                    if len(nameValue) == 2:         #   correct format for a field
                                        currentFieldName    = nameValue[0].strip()
                                        if not currentFieldName in self.fieldNames:
                                            self.fieldNames.append(currentFieldName)
                                        self.DPKG_DB[ currentPackageName ][ currentFieldName ]  = nameValue[1].strip()
                                        #print("\t" + nameValue[0].strip() + ":\t" + nameValue[1].strip())

                    self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FILE_READ ] = True
                    dpkgFile.close()

                    if "galculator" in self.DPKG_DB:
                        print( str( self.DPKG_DB["galculator"] ) )

                except IOError:
                    self.exceptionInfo = self.formatExceptionInfo()
                    print( self.exceptionInfo )
                    self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FILE_CAN_READ ] = False
                    raise Exception("IOError reading:\t" + DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME)
                except Exception:
                    self.exceptionInfo = self.formatExceptionInfo()
                    print( self.exceptionInfo )
                    self.dpkgDBFileStatus[ DpkgDB.FLAG_NAME_DATA_FILE_CAN_READ ] = False
                    raise Exception("Exception reading:\t" + DEFAULT_DEB_DPKG_LOCATION + DEFAULT_DEB_DPKG_NAME)
            else:
                self.dpkgDataFileExists = False
        else:
            self.dpkgDataFolderExists = False


    def formatExceptionInfo(self, maxTBlevel=5):
        #   Copied from: https://www.linuxjournal.com/article/5821
        cla, exc, trbk = exc_info()
        excName = cla.__name__
        try:
            excArgs = exc.__dict__["args"]
        except KeyError:
            excArgs = "<no args>"
        excTb = format_tb(trbk, maxTBlevel)
        return (excName, excArgs, excTb)

    def getPackageList(self):
        return self.packageNames

    def getPackageData(self, packageName):
        if packageName in self.DPKG_DB:
            return self.DPKG_DB[packageName]
        return None

    def getPackageField(self, packageName, fieldName):
        packageData = self.getPackageData(packageName)
        if packageData is not None:
            return packageData[fieldName]
        return None

    def getFieldNameList(self):
        return self.fieldNames

    #   this requires an index which could be built for each field at start.
    #   with an index the opportunity exists to sort also, which should be used to make searching more efficient.
    #   examples:
    #       get all packages which have a particular field.
    #       get all packages with a particular field with a particular value, or which meets relational constraints.
    #           this one would benefit from the SQLite engine, so an in memory database would be needed.
    #   this should be developed to be fully general since there is no Python module at PyPI for working with the dpkg database (Debian).
    #
    def getPackagesWithfield(self, fieldName):
        pass


if __name__ == "__main__":
    print( "Running dpkg")
    dpkgDB  = DpkgDB()
    print( "\nField Names:\t" + str(dpkgDB.getFieldNameList() ))
    print("\tField Count:\t" + str(len(dpkgDB.getFieldNameList())))

    #   print( dpkgDB.getPackageList() )

    #   print( dpkgDB.getPackageData( "galculator" ) )
    #   print( "\ngalculator section:\t" + str(dpkgDB.getPackageField( "galculator", "Section" ) ))

