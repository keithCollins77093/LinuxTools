#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 18, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         UtilConfig
#   Purpose:        View for managing scans of volumes and sub volumes.
#   Development:
#       Each Linux command is a potential usable utility for digital forensics work.
#       Each has a set of flags and parameters that the user can set when he invokes the command using a shell.
#       The shell on my MX 18 Linux work partition is bash.
#       Any particular configuration of flags and parameters is potentially re-usable, and in fact users generally
#       develop templates for command parameterizations which they only create minor variations on, and develop
#       small repeated sets of commands with particular parameterizations or parameterization templates
#       for particular types of work.
#       It is therefore counter-productive to make them memorize every possibility when GUI dialogs with help are
#       possible for all of the commands and all of their parameters as a learning tool while using the utilities.
#       This will have the usual effect of eliminating many types of errors as well.
#       Further, it is ridiculous to force the user to type the same commands with parameters, with only subtle
#       variations frequently, over and over.
#       This module defines types for remembering user shell command parameterizations, for templating them and
#       entering only the variations required for particular uses, as well as for generating piped macros or
#       just sequences of such commands for execution.
#       A parameterization is called a Configuration, which has a use assigned name, a particular shell command
#       and a list of all of the parameters which are not defaulted, meaning left off the command line.
#       If a flag parameter is included, it is True and its absence is False for that parameter.
#       If a parameter requiring a value is included, it is set to that value, and its absence sets it to its default.
#       Parameters can also have optional values, meaning their inclusion acts as a flag and specifying their optional
#       value overrides any default if it is included.
#
#

import json

from pathlib import Path

from model.Configuration import Configuration as AppConfig


class Configuration:

    TYPE_FLAG       = 'flag'
    TYPE_PARAMETER  = 'parameter'

    DD_CONFIG_01  =  { "name": "dd_config_01",
                       "shellCommand": "dd",
                       "shell": "bash",
                        "parameters": [
                            {"name": "bs",
                             "value": "b" },
                            {"name": "conv",
                             "value": ["ascii", "ebcdic", "block"]}
                             ]
                        }

    CAT_CONFIG_01   = { "name": "cat_config_01",
                        "shellCommand": "cat",
                        "shell": "bash",
                        "flags": ["--show-all", "--show-nonprinting", "--number"]
                        }

    CHMOD_CONFIG_01 = {"name": "chmod_config_01",
                        "shellCommand": "chmod",
                        "shell": "bash",
                        "flags": ["--changes", "--verbose", "--recursive"]
                        }

    EXAMPLES        = {}

    ENUM_VALUES_NAME    = "__@ENUMERATED_VALUES"
    EXAMPLES_FILENAME   = "example_util_configs.json"


    registry           = {}

    def __init__(self, configuration: dict, **keyWordArguments):
        self.name           = None
        self.shellCommand   = None
        self.shell          = None
        self.flags          = []
        self.parameters     = []
        if configuration == None:
            raise Exception('Configuration constructor - configuration cannot be None')
        else:
            if "name" in configuration and isinstance(configuration["name"], str):
                self.name           = configuration["name"]
            if "shellCommand" in configuration and isinstance(configuration["shellCommand"], str):
                self.shellCommand   = configuration["shellCommand"]
            if "shell" in configuration and isinstance(configuration["shell"], str):
                self.shell          = configuration["shell"]
            if "flags" in configuration and ( isinstance(configuration["flags"], list) or isinstance(configuration["flags"], tuple) ):
                self.setFlags(list(configuration["flags"]))
            if "parameters" in configuration and ( isinstance(configuration["parameters"], list) or isinstance(configuration["parameters"], tuple) ):
                self.setParameters(list(configuration["parameters"]))
        Configuration.registry[self.name]   = self


    def setName(self, name: str):
        if name == None:
            return False
        self.name   = name
        return self.name

    def getName(self):
        return self.name

    def setFlags(self, flags: list):
        self.flags  = []
        for flag in flags:
            if isinstance(flag, str):
                self.flags.append(flag)

    def getFlags(self):
        return self.flags

    def setParameters(self, parameters: list):
        self.parameters     = []
        for parameter in parameters:
            if isinstance(parameter, dict):
                self.parameters.append({})
                if "name" in parameter and isinstance(parameter["name"], str):
                    self.parameters[len(self.parameters) - 1]["name"] = parameter["name"]
                if "value" in parameter:
                    self.parameters[len(self.parameters) - 1]["value"] = parameter["value"]

    def getParameters(self):
        return self.parameters

    def addFlag(self, flag: str):
        if not flag in self.flags:
            self.flags.append(flag)

    def removeFlag(self, flag: str):
        if flag in self.flags:
            self.flags.remove(flag)

    def setParameter(self, parameter: dict):
        if "name" in parameter:
            if not "value" in parameter:
                return False
            self.removeParameter(parameter["name"])
            self.parameters.append(parameter)
        else:
             return False

    def removeParameter(self, parameterName: str):
        found = False
        index = 0
        while not found and index < len(self.parameters):
            if parameterName == self.parameters[index]["name"]:
                found == self.parameters[index]
            else:
                index += 1
        if found:
            self.parameters.remove(found)
            return True
        else:
            return False

    def list(self):
        print("Util Config:\t" + self.name)
        print('shell command:\t' + self.shellCommand)
        print('shell:\t' + self.shell)
        print('flags:')
        for flag in self.flags:
            print("\t" + flag)
        print('parameters:')
        for parameter in self.parameters:
            print("\t" + parameter['name'] + ':\t' + str(parameter['value']) )

    @staticmethod
    def writeExamples():
        file = open(str(Path(AppConfig.APPLICATION_FOLDER + Configuration.EXAMPLES_FILENAME).absolute()), 'w')
        file.write(json.dumps(Configuration.EXAMPLES, indent=4, sort_keys=True))
        file.close()

    @staticmethod
    def readExamples():
        file = open(str(Path(AppConfig.APPLICATION_FOLDER + Configuration.EXAMPLES_FILENAME).absolute()), 'r')
        Configuration.EXAMPLES    = json.load(file)
        file.close()


if __name__ == "__main__":
    ddUtil01_Configuration      = Configuration(Configuration.DD_CONFIG_01)
    catUtil01_Configuration     = Configuration(Configuration.CAT_CONFIG_01)
    #   2021-08-26:  This is missing:
    #   grepUtil01_Configuration    = Configuration(Configuration.GREP_CONFIG_01)
    chmodUtil01_Configuration   = Configuration(Configuration.CHMOD_CONFIG_01)

    Configuration.readExamples()
    print(Configuration.EXAMPLES)