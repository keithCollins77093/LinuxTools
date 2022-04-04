#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   August 24, 2021
#   Copyright:      (c) Copyright 2021, 2022 George Keith Watson
#   Module:         model/Installation.py
#   Purpose:        Record and manage installation details for installation on particular partition.
#   Development:
#

import os
import platform



if platform.system() == 'Windows':
    USER_HOME   = 'C:\\Users\\user'
elif 'HOME' in os.environ:
    USER_HOME =  os.environ['HOME']
else:
    USER_HOME = '~'

if platform.system() == 'Windows':
    INSTALLATION_FOLDER     = 'C:\\Users\\user\\PycharmProjects\\LinuxLogForensics'
    PYCHARM_PROJECTS_FOLDER         = USER_HOME + '\\PycharmProjects'
    IMAGE_TEST_FILES_FOLDER         = PYCHARM_PROJECTS_FOLDER + '\\ImageTestFiles'
    JPEG_HOME_SCAN_RESULT_LIST      = IMAGE_TEST_FILES_FOLDER + '\\imageFiles_MIME_image_jpeg.list'
    DISK_LAYOUT_EXAMPLES        = INSTALLATION_FOLDER + '\\Documentation\\Examples\\DiskLayout\\2021-08-23'
    EXTERNAL_SOURCE_LIBRARIES   = USER_HOME + '\\PycharmProjects\\ExternalSourceLibraries'
    EXIF_SOURCE_LIBRARY         = EXTERNAL_SOURCE_LIBRARIES + '\\exif-1.3.1\\src\\exif'
    PILLOW_SOURCE_LIBRARY       = EXTERNAL_SOURCE_LIBRARIES + '\\pillow'
else:
    INSTALLATION_FOLDER             = USER_HOME + '/PycharmProjects/LinuxLogForensics'
    PYCHARM_PROJECTS_FOLDER         = USER_HOME + '/PycharmProjects'
    IMAGE_TEST_FILES_FOLDER         = PYCHARM_PROJECTS_FOLDER + '/ImageTestFiles'
    #   linux command:
    #   find . -type f -exec file --mime-type {} \; | awk '{if ($NF == "image/jpeg") print $0 }' > imageFiles.list
    #   produced:
    JPEG_HOME_SCAN_RESULT_LIST      = IMAGE_TEST_FILES_FOLDER + '/imageFiles_MIME_image_jpeg.list'
    DISK_LAYOUT_EXAMPLES        = INSTALLATION_FOLDER + '/Documentation/Examples/DiskLayout/2021-08-23'
    EXTERNAL_SOURCE_LIBRARIES   = USER_HOME + '/PycharmProjects/ExternalSourceLibraries'
    EXIF_SOURCE_LIBRARY         = EXTERNAL_SOURCE_LIBRARIES + '/exif-1.3.1/src/exif'
    PILLOW_SOURCE_LIBRARY       = EXTERNAL_SOURCE_LIBRARIES + '/pillow'


#   Image MIME types:
IMAGE_MIME_TYPES = ('', '', '', '', '', '', '', '', '', '',
                    '', '', '', '', '', '', '', '', '', '',
                    '', '', '', '', '', '', '', '', '', '',
                    '', '', '', '', '', '', '', '', '', '', )
#   image/x-jg, bmp, x-windows-bmp, vnd.dwg, x-dwg, fif, florian, vnd.fpx, vnd.net-fpx, g3fax, gif, x-icon, ief, jpeg,
#   pjpeg, x-jps, jutvision, vasa, naplps, x-niff, x-portable-bitmap, x-pict, x-pcx, x-portable-greymap, pict,
#   x-xpixmap, png, x-portable-anymap, x-portable-pixmap, x-quicktime, cmu-raster, x-cmu-raster, vnd.rn-realflash,
#   x-rgb, vnd.rn-realpix, vnd.dwg, x-dwg, tiff, x-tiff, florian, vnd.wap.wbmp, x-xbitmap, x-xbm, xbm, vnd.xiff,
#   x-xpixmap, xpm, png, x-xwindowdump,

APP_DATA_FOLDER                 = 'data'
USER_CONSOLE_OUT_DB             = 'ConsoleOutput.db'


def pathFromList(fileNameList: tuple):
    if fileNameList is None or not isinstance(fileNameList, tuple) or len(fileNameList) < 1:
        raise Exception('Util.pathFromList - invalid fileNameList argument:    ' + str(fileNameList))
    fileNameList = list(fileNameList)
    pathName = fileNameList[0]
    if platform.system() == 'Windows':
        pathParts = []
        for pathPart in fileNameList:
            pathParts += list(listFromPathString(pathPart))
        pathName = pathParts[0]
        pathParts.pop(0)
        return os.path.join(pathName, *pathParts)
    idx = 1
    while idx < len(fileNameList):
        pathName += '/' + fileNameList[idx]
        idx += 1
    return pathName


def listFromPathString(pathName: str):
    """
    Assumes Linux formatted path name, i.e. no 'file::' or other protocol prepended and with '/' for separation.
    This will be modified as needed to handle MS Windows format and URI/URL strings.
    :param pathName:
    :return:
    """
    list = pathName.split('/')
    if len( list[0] ) == 0:
        del(list[0])
    return tuple(list)

