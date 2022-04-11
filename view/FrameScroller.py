#   Project:        LinuxTools
#                   Imported from:  File Volume Indexer
#                       on April 3, 2022.
#   Author:         George Keith Watson
#   Date Started:   February 28, 2019
#   Copyright:      (c) Copyright 2019, 2022 George Keith Watson
#   Module:         FrameScroller
#   Purpose:        View for managing scans of volumes and sub volumes.
#   Development:
#       Instructions for use:
#           Since the content of a scrollableFrame must have the scrollable Frame as its parent, the scrollable
#           Frame must be obtained from the scroller Frame and the pacing or gridding of the content Frame
#           makes it visible in the scroller Frame.  This is categorically outside of the control of this module,
#           unless the user passes a json frame definition in and it is created here.  If so, then the user must
#           still retrieve the constructed frame to make it the parent of the components it contains.  They could
#           also pass in an entire json framem definition including all components, in which case this module
#           will have a method to obtain reverences to any of the components constructed by passing their names in.
#           The standard name path can be used for the name to make this entirely general for complex nesting structures
#           with repeated component names at different levels.
#

from tkinter import Frame, LabelFrame, Tk, Text, Scrollbar, Label, \
                    BOTTOM, W, RIGHT, X, Y, VERTICAL, HORIZONTAL, BOTH, INSERT


class FrameScroller(LabelFrame):
    def __init__(self, container, name: str, **keyWordArguments):
        LabelFrame.__init__(self, container, name=name)
        if "minimize" in keyWordArguments and isinstance( keyWordArguments["minimize"], bool ) and keyWordArguments["minimize"]:
            self.minimize   = keyWordArguments["minimize"]
            self.stretch    = False
        else:
            self.stretch    = True
            self.minimize   = False

        self.textScroller       = Text(self, name="textScroller")
        self.scrollerFrame      = Frame(self.textScroller, name="scrollerFrame")

        self.textScroller.window_create(INSERT, window=self.scrollerFrame, stretch=self.stretch, align=BOTTOM)

        self.scrollbarVert = Scrollbar(self, name="scrollbarVert", orient=VERTICAL)
        self.scrollbarHorz = Scrollbar(self, name="scrollbarHorz", orient=HORIZONTAL)
        #self.scrollbarHorz.pack(side=BOTTOM, fil=X, anchor=W)
        self.scrollbarHorz.pack(side=BOTTOM, anchor=W, fill=X)
        self.scrollbarVert.pack(side=RIGHT, fill=Y)
        self.textScroller.config(yscrollcommand=self.scrollbarVert.set)
        self.textScroller.config(xscrollcommand=self.scrollbarHorz.set)
        self.scrollbarVert.config(command=self.textScroller.yview)
        self.scrollbarHorz.config(command=self.textScroller.xview)

        if self.minimize:
            self.textScroller.pack()
        else:
            self.textScroller.pack(fill=BOTH, expand=True)

    def getScrollerFrame(self):
        return self.scrollerFrame


if __name__ == "__main__":
    print("FrameScroller running")
    mainView = Tk()
    mainView.geometry("300x400+300+100")
    frameScroller   = FrameScroller(mainView, "frameScroller")

    label = Label(frameScroller.getScrollerFrame(), name="label", width=100, text='Since the content of a scrollableFrame must have the scrollable Frame as its parent, the scrollable Frame must be obtained from the scroller Frame and the pacing or gridding of the content Frame makes it visible in the scroller Frame.  This is categorically outside of the control of this module,')
    label.pack()

    frameScroller.pack()
    mainView.mainloop()