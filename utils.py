import evdev
from PyQt5.QtCore import QObject, QSettings, Qt
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtX11Extras import QX11Info

_devices = [evdev.InputDevice(d) for d in evdev.list_devices()]

def _get_devices_with_key(key):
    devcaps = {d.fn: d.capabilities(verbose=True) for d in _devices}

    keyboards = list()

    for k, caps in devcaps.items():
        for typetuple, buttonlist in caps.items():
            for buttontuple in buttonlist:
                name, code = buttontuple
                if not isinstance(name, list):
                    name = [name] # Some devices names can be lists...
                for n in name:
                    if n == key:
                        keyboards.append(k)

    return keyboards

# FIXME: I didn't see a way to check the type of device, and capabilities() only
# refers to the individual keys available. It would be better to check the dev
# type, but for now this function just returns the device with the "Q" key.
def get_keyboard_path():
    return _get_devices_with_key("KEY_Q")

# Same as above but with BTN_LEFT.
def get_mouse_path():
    return _get_devices_with_key("BTN_LEFT")

def get_qfont_from_qsettings():
    qs = QSettings()
    fontstr = qs.value("font", "")
    if not fontstr:
        return QFont('monospace', qs.value("fontsize", 48))
    else:
        retqfont = QFont()
        retqfont.fromString(fontstr)
        return retqfont

def make_qkos_window(qwidget):
    qwidget.setWindowIcon(QIcon(':/images/qkos.png'))
    # QtWayland does not yet support WA_TranslucentBackground (10/2/2015)
    if not QX11Info.isPlatformX11():
        qwidget.setStyleSheet('background-color: white')
    else:
        qwidget.setAttribute(Qt.WA_TranslucentBackground)
    qwidget.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

def normalize_evdev_event(ev):
    event = evdev.categorize(ev)

    if not (isinstance(event, evdev.KeyEvent) or \
            isinstance(event, evdev.RelEvent) or \
            isinstance(event, FakeScrollWheelUpEvent)):
        return False

    # Hackery for scroll wheels...
    if isinstance(event, evdev.RelEvent):
        if event.event.code == 0x0B:
            keycode = evdev.ecodes.REL[0x06]
        else:
            keycode = evdev.ecodes.REL[event.event.code]
        if keycode != 'REL_WHEEL': return
        keystate = 0x4 # custom key state because scroll wheel never goes "UP"
    else:
        keycode = event.keycode
        keystate = event.keystate

    if isinstance(keycode, list):
        keycode = keycode[0]

    return (keycode, keystate)

class FakeScrollWheelUpEvent(evdev.events.InputEvent):
    def __init__(self):
        import time

        self.value = self.keystate = value = 0x0
        self.keycode = "REL_WHEEL"

        t = time.time();
        self.sec = int(t)
        self.usec = int((t%1)*1000000)
        self.type = 'REL'
        self.code = 'REL_WHEEL'

class KeyInfo(QObject):
    def __init__(self):
        super(KeyInfo, self).__init__()
        self.qs = QSettings()

    def key_name(self, kn):
        # Mouse buttons
        if kn == 'BTN_LEFT': return ('Left Click', False)
        if kn == 'BTN_RIGHT': return ('Right Click', False)
        if kn == 'BTN_MIDDLE': return ('Middle Click', False)
        if kn == 'REL_WHEEL': return ('Scroll Wheel', False)

        # Arrow keys
        if kn == 'KEY_LEFT': return ('Left', False)
        if kn == 'KEY_RIGHT': return ('Right', False)

        # Braces
        if kn == 'KEY_LEFTBRACE': return ('[', False)
        if kn == 'KEY_RIGHTBRACE': return (']', False)

        kn = kn.replace('KEY_','')
        mf = self.meta_info(kn)
        if not mf:
            return (kn.capitalize(), False)
        else:
            print(self.qs.value("differentiate", True))
            return ('{}{}'.format(('Left ' if mf['left'] else 'Right ') \
                                if self.qs.value("differentiate", True) else '',
                                mf['type'].strip().capitalize()), mf)

    def meta_info(self, kn):
        if (kn.lower().find('left') == -1 and kn.lower().find('right') == -1):
            return False

        return {'left' : (kn.lower().find('left') != -1),
                'right': (kn.lower().find('right') != -1),
                'type' : kn.lower().replace('left','').replace('right','')}

class QSettingsHandler(QObject):
    def __init__(self, qo):
        super(QSettingsHandler, self).__init__()
        self.qo = qo
        self.qs = QSettings()

    def init_parent(self, parent):
        parent.qs = self.qs
        parent.set_qsettings_setting = lambda k, v: \
                                       self.set_qsettings_setting(k, v)
        return parent

    def set_qsettings_setting(self, key, value):
        self.qs.setValue(key, value)
        self.qo.settings.emit(key, value)

class Draggable(QObject):
    def mousePressEvent(self, event):
        self.offset = event.pos()

    def mouseMoveEvent(self, event):
        x=event.globalX()
        y=event.globalY()
        x_w = self.offset.x()
        y_w = self.offset.y()
        self.move(x-x_w, y-y_w)

