# -*- coding: utf-8 -*-

"""
In this example, we position two push
buttons in the bottom-right corner
of the window.
"""

import sys
from PyQt4 import QtGui

class Example(QtGui.QWidget):

    def __init__(self):
        super(Example, self).__init__()

        self.initUI()

    def initUI(self):

        okButton = QtGui.QPushButton("OK")
        cancelButton = QtGui.QPushButton("Cancel")
        test1Button = QtGui.QPushButton('test1')
        test2Button = QtGui.QPushButton('test2')
        test3Button = QtGui.QPushButton('test3')

        # hbox = QtGui.QHBoxLayout()
        # hbox.addStretch()
        # hbox.addWidget(okButton)
        # hbox.addWidget(cancelButton)

        vbox1 = QtGui.QVBoxLayout()


        vbox2 = QtGui.QVBoxLayout()
        vbox1.addWidget(okButton)
        vbox1.addStretch(9)
        vbox2.addWidget(cancelButton)
        vbox2.addWidget(test1Button)
        vbox2.addWidget(test2Button)
        vbox2.addStretch(1)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)






        self.setLayout(hbox)

        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle('Buttons')
        self.show()

def main():

    app = QtGui.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()