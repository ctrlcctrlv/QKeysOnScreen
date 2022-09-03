#!/usr/bin/env python3
################################################################################
# QKeysOnScreen - Shows the current keys you're pressing on the screen         #
#                                                                              #
# Requires Evdev and QT5.                                                      #
#                                                                              #
# This software must be run as root, or you must give permission to access the #
# keyboard using something like udev. This makes sense since this program is   #
# basically a keylogger, except it doesn't save the keystrokes or send them    #
# anywhere.                                                                    #
################################################################################
#    This program is free software: you can redistribute it and/or modify      #
#    it under the terms of the GNU General Public License as published by      #
#    the Free Software Foundation, either version 3 of the License, or         #
#    (at your option) any later version.                                       #
#                                                                              #
#    This program is distributed in the hope that it will be useful,           #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#    GNU General Public License for more details.                              #
#                                                                              #
#    You should have received a copy of the GNU General Public License         #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
################################################################################

import sys
import time
import evdev
import operator
import pickle
from functools import reduce
from threading import Thread
from select import select
from math import floor

## QT IMPORTS ##
# Even though it might take up some space, I explicitly import because I don't
# want to run into collisions. `from x import *` is quite dangerous in Python,
# despite how frequently it is used.
from PyQt5.QtCore import Qt, QTimer, QFile, QIODevice
from PyQt5.QtWidgets import (QWidget, QToolTip, QPushButton, QMessageBox,
                             QLabel, QMainWindow, QFrame, QSizePolicy,
                             QGridLayout, QAction, QColorDialog, QFontDialog,
                             QInputDialog, QStyle, QGraphicsOpacityEffect,
                             QDialog, QScrollArea, QTextEdit, QListWidget,
                             QListWidgetItem)
from PyQt5.QtCore import pyqtSignal, QObject, QCoreApplication, QSettings
from PyQt5.QtGui import QFont, QFontMetrics, QIcon, QPixmap, QPalette
# Qt resource system, re-build with       `pyrcc5 resources.qrc -o resources.py`
import resources

# SUBMODULES #
from about import QKOSAbout
from qkos import QKOSApplication
from utils import *

# These need to be set for QSettings to work properly.
QCoreApplication.setOrganizationName("QKeysOnScreen")
QCoreApplication.setApplicationName("QKeysOnScreen")

class QKeysOnScreen(QFrame):
    def __init__(self, qo):
        super(QKeysOnScreen, self).__init__()
        self.qo = qo
        self.qsh = QSettingsHandler(self.qo)
        self.qsh.init_parent(self)
        self.ek = EvdevKeymon()
        self.ek.divider = self.qs.value('divider', ' + ')
        self.ek.ignored_keys = self.qs.value('ignored_keys', [])
        self.ki = KeyInfo()
        self.qo = qo

        self.displaystate = []
        self.history = []

        self.initUI()

    def initUI(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        self.gridlayout = QGridLayout();

        self.setLayout(self.gridlayout);

        # Fading out effect
        self.qfade = QGraphicsOpacityEffect()
        self.qfade.setOpacity(1)
        self.qtimer = QTimer(self)
        self.qtimer.timeout.connect(self.timerEvent)
        if (self.qs.value('fade/enabled', True)): self.qtimer.start(50)

        self.qkey = QLabel('', self)
        self.qkey.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.qkey.setMaximumWidth(int(self.qs.value("window/width", 650)))
        self.qkey.setScaledContents(True)
        self.qkey.setStyleSheet('color:{}'.format(self.qs.value("color",
                                                                "white")))
        self.qkey.setGraphicsEffect(self.qfade)
        self.gridlayout.addWidget(self.qkey, 0,0)

        qfont = get_qfont_from_qsettings()
        self._recalculate_font_metrics(qfont)
        self.qkey.setFont(qfont)
        self.smallerQFont = False

    def _recalculate_font_metrics(self, qfont):
        self.monospace_width = QFontMetrics(qfont).averageCharWidth()
        self.monospace_ratio = self.monospace_width / \
                               self.qs.value("fontsize", 48)

    def timerEvent(self):
        # Every n ms, fade out our QGraphicsEffect
        current_opacity = self.qfade.opacity()
        self.qfade.setOpacity(current_opacity - 0.0125)

    def processSettingsChange(self, key, value):
        if key == "color":
            self.qkey.setStyleSheet('color:{}'.format(value))
        elif key == "font":
            newqfont = QFont()
            newqfont.fromString(value)
            self._recalculate_font_metrics(newqfont)
            self.qkey.setFont(newqfont)
        elif key == "window/width":
            self.qkey.setMaximumWidth(int(value))
        elif key == "fade/enabled":
            if value:
                self.qtimer.start(50)
            else:
                self.qtimer.stop()
                self.qfade.setOpacity(1)


    def processIncoming(self, ev):
        newtext = self.ek.processIncoming(ev)
        if not newtext: return
        # Assure that our text will always fit.
        newtextwidth = len(newtext) * self.monospace_width
        targetwidth = int(self.qs.value("window/width", 650)) - 50

        if newtextwidth > targetwidth:
            # New font size...
            x = targetwidth / newtextwidth
            qfont = get_qfont_from_qsettings()
            qfont.setPointSizeF(x*qfont.pointSizeF())
            self.qkey.setFont(qfont)
            self.smallerQFont = True
        elif self.smallerQFont:
            qfont = get_qfont_from_qsettings()
            self.qkey.setFont(qfont)
            self.smallerQFont = False

        self.displaystate = self.ek.down
        self.qfade.setOpacity(1)
        self.qkey.setText(newtext)
        self.qo.history.emit(self.ek.emit)

        if self.ek.event is not None:
            self.qo.message.emit(self.ek.event)
            self.ek.event = None

class QKOSHistoryWindow(QFrame, Draggable):
    def __init__(self, qo):
        super(QKOSHistoryWindow, self).__init__()
        self.qo = qo
        self.qsh = QSettingsHandler(self.qo)
        self.qsh.init_parent(self)
        self.ki = KeyInfo()
        self.qo = qo
        self.paused = False
        self.displaystate = []
        self.down = []
        self.setWindowTitle('QKOS History')
        self.initUI()

    def show(self):
        # Work around a bug in Qt. If we turn on the transparency before
        # the dialog is shown, the background will become black, and
        # pressing any keys will result in background corruption.
        super(QKOSHistoryWindow, self).show()
        self._set_transparency(self.background.isChecked())

    def initUI(self):
        make_qkos_window(self)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.gridlayout = QGridLayout(self)

        self.title = QLabel("Last {0} key combinations pressed...".format(100))
        self.gridlayout.addWidget(self.title, 0, 0)

        self.scrollarea = QScrollArea()
        self.historylabel = QLabel()
        self.scrollarea.setWidget(self.historylabel)
        self.gridlayout.addWidget(self.scrollarea, 1, 0, 1, 2)

        self.pause = QPushButton()
        self.pause.setCheckable(True)
        self.pause.setIcon(QIcon(':/images/pause.png'))
        self.pause.toggled.connect(self._set_paused)
        self.gridlayout.addWidget(self.pause, 0,1)

        # History window context menu
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.background = QAction('Toggle &background', self)
        self.background.setCheckable(True)
        self.background.triggered.connect(self._set_background)
        if self.qs.value("history/background", True):
            self.background.setChecked(True)
        self.addAction(self.background)

        self.setLayout(self.gridlayout)

        self.setMaximumHeight(250)
        self.setMinimumHeight(250)

    def _set_transparency(self, enabled):
        if enabled:
            self.scrollarea.setStyleSheet("")
        else:
            self.scrollarea.setStyleSheet("background-color:transparent;")
            self.setAttribute(Qt.WA_TranslucentBackground, enabled)

        self.setAttribute(Qt.WA_NoSystemBackground, not enabled)
        self.scrollarea.repaint()
        self.repaint()

    def _set_background(self):
        self._set_transparency(self.background.isChecked())
        if self.background.isChecked():
            self.set_qsettings_setting('history/background', 'true')
        else:
            self.set_qsettings_setting('history/background', '')


    def _set_paused(self):
        checked = self.pause.isChecked()
        self.paused = checked
        if checked:
            self.pause.setIcon(QIcon(':/images/play.png'))
        else:
            self.pause.setIcon(QIcon(':/images/pause.png'))

    def processIncoming(self, down):
        if self.paused: return
        # Don't insert meta keys, wait for combination
        if all(i[1] for i in down): return

        self.displaystate.insert(0, down[:])

        if len(self.displaystate) > 100:
            del self.displaystate[100:]

        displaytext = ''

        for downkeys in self.displaystate:
            displaytext += (self.qs.value('divider', ' + ')\
                            .join(i[0] for i in downkeys) + '<br>')

        self.historylabel.setText(displaytext)
        self.historylabel.adjustSize()

class QKOSArrayDialog(QDialog):
    def __init__(self, parent, title, helptext, qo):
        super(QKOSArrayDialog, self).__init__(parent)
        self.qo = qo
        self.qsh = QSettingsHandler(self.qo)
        self.qsh.init_parent(self)
        self.ki = KeyInfo()
        self.itemflags = Qt.ItemIsEditable | Qt.ItemIsSelectable \
                       | Qt.ItemIsEnabled
        self.initUI(title, helptext)

    def initUI(self, title, helptext):
        gridlayout = QGridLayout(self)
        self.listwidget = QListWidget(self)
        self.listwidget.setSelectionMode(QListWidget.MultiSelection)
        self.allkeys = QListWidget(self)
        self.allkeys.setSelectionMode(QListWidget.MultiSelection)
        self.setWindowTitle(title)
        label = QLabel(helptext)
        label.setWordWrap(True)
        gridlayout.addWidget(label, 0,0,1,4)
        gridlayout.addWidget(self.listwidget, 1,0,1,2)
        gridlayout.addWidget(self.allkeys, 1,2,1,2)

        self.addbutton = QPushButton("Add key", self)
        self.delbutton = QPushButton("Delete key", self)
        self.quitbutton = QPushButton("Save && close", self)
        self.cancelbutton = QPushButton("Cancel", self)

        gridlayout.addWidget(self.addbutton, 2, 0)
        gridlayout.addWidget(self.delbutton, 2, 1)
        gridlayout.addWidget(self.quitbutton, 2, 2)
        gridlayout.addWidget(self.cancelbutton, 2, 3)

        items = self.qs.value('ignored_keys', [])
        if items:
            for i, item in enumerate(items):
                qlwi = QListWidgetItem(item, self.listwidget)
                qlwi.setFlags(self.itemflags)

        ecodesqfile = QFile(':/ecodes.p')
        ecodesqfile.open(QIODevice.ReadOnly)
        forpickle = bytes(ecodesqfile.readAll())
        ecodes = pickle.loads(forpickle)
        for ecode in ecodes:
            (keyname, metainfo) = self.ki.key_name(ecode)
            if ecode.split('_')[0] in ['KEY', 'BTN']:
                qlwi = QListWidgetItem(keyname, self.allkeys)
        self.allkeys.sortItems()

        self.addbutton.clicked.connect(self.add_item)
        self.delbutton.clicked.connect(self.del_item)
        self.quitbutton.clicked.connect(self.save_and_quit)
        self.cancelbutton.clicked.connect(self.close)
        self.setLayout(gridlayout)

    def del_item(self):
        for item in self.listwidget.selectedItems():
            row = self.listwidget.row(item)
            self.listwidget.takeItem(row)
        self.allkeys.clearSelection()

    def add_item(self):
        selectedkeys = self.allkeys.selectedItems()

        if selectedkeys:
            for item in selectedkeys:
                row = self.allkeys.row(item)
                item = QListWidgetItem(item.text(), self.listwidget)
        else:
            item = QListWidgetItem('Edit me!', self.listwidget)
            item.setFlags(self.itemflags)

        self.allkeys.clearSelection()

    def save_and_quit(self):
        items = self.list_items()
        self.qs.setValue('ignored_keys', items)
        self.close()

    def list_items(self):
        retval = []
        for i in range(0, self.listwidget.count()):
            retval.append(self.listwidget.item(i).text())
        return retval

class MainWindow(QMainWindow, Draggable):
    def __init__(self, qo):
        super(MainWindow, self).__init__()

        self.qo = qo
        self.qsh = QSettingsHandler(self.qo)
        self.qsh.init_parent(self)

        make_qkos_window(self)

        _devices = [evdev.InputDevice(d) for d in evdev.list_devices()]
        if not _devices:
            QMessageBox.critical(self, 'No devices', '<p>QKeysOnScreen could '+
                'not find any suitable keyboard device. QKeysOnScreen requires'+
                ' access to /dev/input/event* to function. The easiest way to '+
                'give it this is to give it root (run this program with sudo),'+
                ' but you may also add yourself to the input group, like so:'+
                '</p><p><tt>sudo gpasswd -a your_username input</tt></p><p>'+
                '<p>Of course, replace your username with fredrick, and the'+
                ' group of the /dev/input/event* devices with input. Note that'+
                ' after adding yourself to a group you usually have to log out'+
                ' and then log back in for the change to take effect.</p>'+
                'If neither of these options is attractive to you, you may '+
                ' also edit udev, but I couldn\'t figure it out. Maybe <a href'+
                '="https://wiki.archlinux.org/index.php/udev">this page</a> '+
                'will help. Let me know if you figure it out.</p>')
            sys.exit(1)

        self._get_geometry()
        self.setGeometry(*(int(c) for c in self._get_geometry()))
        self.setWindowTitle('QKeysOnScreen')

        self.setToolTip('Try right clicking me for settings.')

        # Context Menu
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.quit = QAction("&Quit", self)
        self.quit.triggered.connect(sys.exit)
        self.addAction(self.quit)

        self.leftright = QAction("Differentiate between &left && right meta "+
                                 "keys", self)
        self.leftright.triggered.connect(self._set_leftright)
        self.leftright.setCheckable(True)
        if self.qs.value("differentiate", True): self.leftright.setChecked(True)
        self.addAction(self.leftright)

        self.fade = QAction("&Fade out last keys", self)
        self.fade.setCheckable(True)
        if self.qs.value("fade/enabled", True): self.fade.setChecked(True)
        self.fade.triggered.connect(self._set_fade)
        self.addAction(self.fade)

        self.history = QAction("Show &history window", self)
        self.history.setCheckable(True)
        if self.qs.value("history/enabled", True): self.history.setChecked(True)
        self.history.triggered.connect(self._toggle_history_window)
        self.addAction(self.history)

        self.color = QAction("Set &color...", self)
        self.color.triggered.connect(self._select_color)
        self.addAction(self.color)

        self.font = QAction("Set &font...", self)
        self.font.triggered.connect(self._select_font)
        self.addAction(self.font)

        self.size = QAction("Set window &size...", self)
        self.size.triggered.connect(self._select_size)
        self.addAction(self.size)

        self.ignored = QAction("Set &ignored keys...", self)
        self.ignored.triggered.connect(self._set_ignored_keys)
        self.addAction(self.ignored)

        self.divider = QAction("Set &divider...", self)
        self.divider.triggered.connect(self._set_divider)
        self.addAction(self.divider)

        self.about = QAction("About", self)
        self.about.triggered.connect(self._about)
        self.addAction(self.about)

        self.historywindow = QKOSHistoryWindow(self.qo)
        self.qo.history.connect(self.historywindow.processIncoming)
        if self.qs.value("history/enabled", True):
            self.historywindow.show()

    def _about(self):
        about = QKOSAbout(self)
        about.show()

    def _toggle_history_window(self):
        if self.history.isChecked():
            self.historywindow.show()
            self.set_qsettings_setting('history/enabled', 'true')
        else:
            self.historywindow.hide()
            self.set_qsettings_setting('history/enabled', '')

    def _set_divider(self):
        divdialog = QInputDialog()
        nowdiv = self.qs.value('divider', ' + ')
        divlabel = 'New divider (currently {0})'.format(nowdiv)
        (div, ok) = divdialog.getText(self, divlabel, divlabel, text=nowdiv)

        if ok:
            self.set_qsettings_setting('divider', div)

    def _set_ignored_keys(self):
        helptext = """
        Type the names of the keys that you wish to ignore here.<br> The box to
        the right lists all keys and buttons that are recognized by the system.
        If you select one and click add, it will be automatically added to the
        ignore list to the left. If you want to add a key combination to ignore
        instead of a single key, simply add it to the left, then double click
        the entry and type the meta key before it. For example, to ignore all
        instances of the combination "Shift + Enter", find "Enter" in the box,
        click "Add key", then double click the newly added key and edit it to be
        "Shift + Enter". Please note that if you have QKeysOnScreen set to
        differentiate between Left and Right meta keys, you'd have to add "Left
        Shift + Enter" and "Right Shift + Enter" to get the same effect.
        """

        qd = QKOSArrayDialog(self, "Set ignored keys", helptext, self.qo)
        qd.show()

    def _set_leftright(self):
        if self.leftright.isChecked():
            self.set_qsettings_setting('differentiate', 'true')
        else:
            self.set_qsettings_setting('differentiate', '')

    def _set_fade(self):
        if self.fade.isChecked():
            self.set_qsettings_setting('fade/enabled', 'true')
        else:
            self.set_qsettings_setting('fade/enabled', '')

    def _select_color(self):
        qcd = QColorDialog(self)
        color = qcd.getColor()
        if color.isValid():
            self.set_qsettings_setting('color', color.name())

    def _select_font(self):
        current_qfont = get_qfont_from_qsettings()
        qfd = QFontDialog(self)
        (font, ok) = qfd.getFont(current_qfont, self, None,
                                 QFontDialog.MonospacedFonts)
        if ok:
            self.set_qsettings_setting('font', font.toString())

    def _select_size(self):
        (desktop_width, desktop_height) = self._get_screen_maxes()
        current_font = get_qfont_from_qsettings()
        font_metrics = QFontMetrics(current_font)
        min_height = font_metrics.height() + 10
        min_width = font_metrics.boundingRect('Shift').width() + 10
        heightlbl = 'Height (minimum {0}, maximum {1})'.format(min_height,
                                                               desktop_height)
        widthlbl = 'Width (minimum {0}, maximum {1})'.format(min_width,
                                                             desktop_width)

        # First height...
        heightdialog = QInputDialog()
        heightdialog.setToolTip('Note: the minimum height of the window is the'+
                                'height of your current font + 10.')
        (height, ok) = heightdialog.getInt(self, 'New window height', heightlbl,
                                       int(self.qs.value('window/height', 200)),
                                       min_height, desktop_height)

        if ok:
            # QKOSCommunicationObject requires str...
            self.set_qsettings_setting('window/height', str(height))

        # First height...
        widthdialog = QInputDialog()
        (width, ok) = widthdialog.getInt(self, 'New window width', widthlbl,
                                        int(self.qs.value('window/width', 200)),
                                        min_width, desktop_width)

        if ok:
            # QKOSCommunicationObject requires str...
            self.set_qsettings_setting('window/width', str(width))

        self.setGeometry(*self._get_geometry())

    def _get_screen_maxes(self):
        qrect = QKOSApplication.desktop().screenGeometry()
        desktop_width = qrect.width()
        desktop_height = qrect.height()

        return (desktop_width, desktop_height)

    def _get_geometry(self):
        # We position our application in the middle of the screen, 60px from
        # the bottom, and we set its width to be 400 pixels constant. First we
        # have to get the screen's geometry, then work with it from there.

        app_width = int(self.qs.value("window/width", 650))
        app_height = int(self.qs.value("window/height", 200))
        (desktop_width, desktop_height) = self._get_screen_maxes()

        return ( (desktop_width-app_width)/2, (desktop_height-app_height-60),
                 app_width, app_height )


class QKOSThread(Thread):
    def __init__(self, qo):
        Thread.__init__(self)
        # QKOSCommunicationObject
        self.qo = qo

    def run(self):
        self.kb = get_keyboard_path()
        self.mouse = get_mouse_path()

        self.devices = filter(None, reduce(operator.concat, [self.kb, self.mouse]))
        if not self.devices: return
        self.devices = map(evdev.InputDevice, self.devices)

        self.devicesdict = {dev.fd: dev for dev in self.devices}

        # I have found the evdev library to be somewhat buggy, and sometimes
        # InputDevices go missing and becoming None, and can't be closed. Let's
        # just ignore all errors in anything dealing with evdev's wonky I/O.

        while True:
            try:
                r, w, x = select(self.devicesdict, [], [])
                for fd in r:
                    for event in self.devicesdict[fd].read():
                        self.qo.message.emit(event)
            except AttributeError: pass # Avoid None.close()


class QKOSCommunicationObject(QObject):
    """
    message: Facilitates communication between the window and evdev with
    pyqtSignal().

    settings: Facilitates communication between MainWindow and QKeysOnScreen
    classes, useful because the context menu is a member of MainWindow but most
    settings are handled by the QKeysOnScreen QWidget.
    """

    # C++ has strict typing, but Python only has duck typing. This makes for
    # some interesting interactions: pyqtSignals are strictly typed. Therefore
    # I have a few different settings types, because for some I need `str`,
    # others `QFont`...
    message = pyqtSignal(evdev.InputEvent) # evdev -> QKOS
    history = pyqtSignal(list)             # QKOS -> QKOSHistory
    settings = pyqtSignal(str, str)        # QSettings

if __name__ == '__main__':
    app = QKOSApplication(sys.argv)
    f = QKOSCommunicationObject()
    mw = MainWindow(f)
    #mw2 = MainWindow(f)
    qk = QKeysOnScreen(f)
    mw.setCentralWidget(qk)
    mw.show()
    #mw2.setCentralWidget(qk)
    #mw2.show()
    f.message.connect(qk.processIncoming)
    f.settings.connect(qk.processSettingsChange)
    client = QKOSThread(f)
    client.daemon = True
    client.start()
    sys.exit(app.exec_())
