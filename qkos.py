import signal
from PyQt5.QtWidgets import QApplication

class QKOSApplication(QApplication):
    def __init__(self, *args, **kwargs):
        super(QKOSApplication, self).__init__(*args, **kwargs)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
