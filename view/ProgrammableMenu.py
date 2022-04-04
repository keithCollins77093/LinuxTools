#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 9, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         ProgrammablePopup
#   Purpose:        View for managing scans of volumes and sub volumes.
#   Development:
#
#       This is a popup menu or any other type of menu in Python which the user / programmer provides a design to
#       construct the menu they require.  The design is a dictionary or map of menu text to actions.  The actions
#       are either method references, or callbacks, or sub menu definitions.
#   2019-02-20:
#       Use:
#       Write a derived class in the python file that imports this module and where the services for each menu option
#       are.  As long as the methods passed are invokable from the context in which the derived class is used,
#       the methods will be invoked when the menu option is chosen.
#       If parameterization of the methods invoked by menu item selection is required, the programmer using this
#       module must provide them separately, since parameter placeholdcers cannot be included in the method
#       binding that tkinter menus provide.  This of course can be done by setting attributes of objects that the
#       item service method has access to before the menu item is chosen.
#
#       The most straight forward implementation strategy is to place all of the methods which are involed by the
#       menu items into the class that derives from ProgrammablePopup, and use ainstance (self) dict declaration to
#       specify the design before the super class' constructor is called, passing it to the super class constructor.
#       All local instance methods (ones which self is the first parameter of) are then available to include in the
#       menu definition as item actions.  The local methods are usable as gateways and context managers for any
#       method invokable from that context.
#

from tkinter import Menu, Tk, Frame, Label


class ProgrammablePopup(Menu):

    def __init__(self, container, name: str, design: dict, **keyWordArguments):
        if 'tearoff' in keyWordArguments:
            self.tearoff   =  keyWordArguments['tearoff']
        else:
            self.tearoff = False
        Menu.__init__(self, container, tearoff=self.tearoff)
        if design == None:
            raise Exception('ProgrammablePopup constructor - design is None')
        else:
            self.design = design
        self.container  = container
        self.name       = name
        if 'sorted' in keyWordArguments and isinstance(keyWordArguments['sorted'], bool):
            self.sorted     = keyWordArguments['sorted']
        else:
            self.sorted = False
        self.buildMenu(self, self.design)
        #self.bind('<Key>', self.keyPressed)

    def buildMenu(self, parent, design):
        names = list(design.keys())
        if self.sorted:
            names.sort()
        for name in names:
            toDo = design[name]
            if 'type' in toDo:
                if toDo['type'] == 'item':
                    item = parent.add_command(label=name, command=toDo['call'])
                elif toDo['type'] == 'checkbutton':
                    parent.add_checkbutton(label=toDo['label'], onvalue=toDo['onvalue'], offvalue=toDo['offvalue'],
                                   variable=toDo['variable'])
                elif toDo['type'] == 'menu':     #   sub menu
                    if 'tearoff' in toDo:
                        tearoff = toDo['tearoff']
                    else:
                        tearoff=False

                    #   for naming submenus, need to keep track of path during recursion
                    subMenu = Menu(parent, name="subMenu_" + name, tearoff=tearoff)

                    #subMenu.bind('<Key>', self.keyPressed)
                    parent.add_cascade(label=name, menu=self.buildMenu(subMenu, toDo['items']))
            else:
                pass
                """
                This does not work:
                if callable(toDo):
                    parent.add_command(label=name, command=toDo)
                else:
                    raise Exception('ProgrammablePopup constructor - passed method is not callable:\t' + str(toDo))
                """
        return parent

    def keyPressed(self, event):
        print('ProgrammablePopup.keyPressed:\t' + str(event.char))



class TestMenu(ProgrammablePopup):
    def __init__(self, context, name: str, design: dict):
        if design == None:
            self.design     = {'Configured Utility': {
                                    'type': "menu",
                                    'items':    {
                                        'Platform': {'type': "item", 'call': self.showPlatformInfo },
                                        'Operating System': { 'type': "item", "call": self.showOpSysInfo },
                                        'Device': { "type": 'item', "call": self.showDeviceInfo },
                                        'Environment': { "type": 'item', "call": self.showEnvironmentInfo }
                                    }
                            },
                            'Services': {
                                "type": "menu",
                                "items": {
                                    'One': {'type': 'item', "call": self.serviceOne },
                                    'Two': { "type": 'item', "call": self.serviceTwo },
                                    'Three': { "type": "item", "call": self.serviceThree }
                                }
                            }
                       }
        ProgrammablePopup.__init__(self, context, name, self.design)


    def getMenu(self, path):
        print('getMenu')
        return self.getItem(path)

    def getItem(self, path):
        "path is a list or tuple of menu names in hierarchical order"
        print('getItem')
        selection = self.design
        for name in path:
            selection = selection[name]
            if selection[type] == 'menu':
                selection = selection['items']
        return selection


    def serviceOne(self):
        print('serviceOne')

    def serviceTwo(self):
        print('serviceTwo')

    def serviceThree(self):
        print('serviceThree')

    def showPlatformInfo(self):
        print('showPlatformInfo')

    def showOpSysInfo(self):
        print('showOpSysInfo')

    def showDeviceInfo(self):
        print('showDeviceInfo')

    def showEnvironmentInfo(self):
        print('showEnvironmentInfo')



class FrameTest(Frame):
    def __init__(self, container):
        Frame.__init__(self, container)

        labelFrame = Label(self, text="Frame Label", relief='ridge', borderwidth=5)
        labelFrame.pack(expand=1)

        self.popupMenu = ProgrammablePopup(labelFrame, 'popupMenu', None)
        labelFrame.bind("<Button-3>", self.popup)

    def popup(self, event):
        print('popupMenu')
        self.popupMenu.post(event.x_root, event.y_root)


if __name__ == "__main__":
    mainView = Tk()
    mainView.geometry("300x200+500+200")

    frameTest   = FrameTest(mainView)
    frameTest.pack(expand=1)

    mainView.mainloop()
