from PyQt5.QtCore import QIODevice, QFile
from PyQt5.QtWidgets import QDialog, QGridLayout, QSizePolicy, QLabel, QTextEdit
from PyQt5.QtGui import QFont
import sys
from utils import *

class QKOSAbout(QDialog):
    def __init__(self, parent):
        super(QKOSAbout, self).__init__(parent)
        gridlayout = QGridLayout(self);
        titlefont = QFont()
        titlefont.setPointSize(24)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        label = QLabel("About QKeysOnScreen", self)
        label.setFont(titlefont)
        label.setSizePolicy(policy)
        gridlayout.addWidget(label, 0,0)
        labelcopyright = QLabel("\u00a9 2015 Fredrick Brennan <admin@8chan.co>")
        labelcopyright.setSizePolicy(policy)
        gridlayout.addWidget(labelcopyright, 1,0)
        labeldesc = "<p>QKeysOnScreen is a simple application intended for "+\
                    "presentations, video tutorials, and any other case where"+\
                    " you'd want to display the current state of the keyboard"+\
                    " on the screen. For more information see our <a href=\""+\
                    "https://github.com/ctrlcctrlv/QKeysOnScreen\">Github</a>"+\
                    " project."
        qlabeldesc = QLabel(labeldesc)
        qlabeldesc.setWordWrap(True)
        gridlayout.addWidget(qlabeldesc, 2,0)

        from PyQt5.QtCore import QT_VERSION_STR
        from PyQt5.Qt import PYQT_VERSION_STR
        import platform
        pyversion = '.'.join([str(o) for o in sys.version_info])
        uname_result = platform.uname()
        uname = '{} {}'.format(uname_result.system, uname_result.release)
        labelversions = ("<strong>Versions:</strong><br>Qt: {0}<br>PyQt: {1}"+\
                        "<br>Python: {2}<br>OS: {3}<br>QKeysOnScreen: 1.0.0")\
                        .format(QT_VERSION_STR, PYQT_VERSION_STR,
                                platform.python_version(),
                                uname, platform.machine())
        qlabelversions = QLabel(labelversions)
        qlabelversions.setStyleSheet('border: 1px solid green')
        gridlayout.addWidget(qlabelversions, 0,1)

        self.kb = get_keyboard_path()
        self.mouse = get_mouse_path()
        self.infoqlabel = QLabel('<strong>Devices:</strong><br>'+
                                 'Our mouse is {0}<br/>Our keyboard is {1}'
                                 .format(self.mouse, self.kb) , self)
        self.infoqlabel.setStyleSheet('border: 1px solid green')
        gridlayout.addWidget(self.infoqlabel, 2,1)

        qte = QTextEdit(self)
        qte.setReadOnly(True)
        qfile = QFile(':/LICENSE')
        qfile.open(QIODevice.ReadOnly)
        qte.setPlainText(bytes(qfile.readAll()).decode('utf-8'))
        qfile.close()

        gridlayout.addWidget(qte, 3,0, 1,2)

        self.setLayout(gridlayout)
