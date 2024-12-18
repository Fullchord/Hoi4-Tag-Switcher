import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QCheckBox,
    QPushButton,
    QSpinBox,
    QLabel
)
from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
import pymem
import pymem.process
import qdarktheme

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MemoryUtils:
    @staticmethod
    def OffsetCalculator(pm, base_address, offsets):
        address = base_address
        for offset in offsets:
            address = pm.read_ulonglong(address) + offset
        return address

class HoI4Window(QMainWindow):
    def __init__(self):
        super(HoI4Window, self).__init__()

        # Load UI File
        ui_file_path = resource_path("main.ui")
        uic.loadUi(ui_file_path, self)

        # Define Widgets
        self.ConnectedLable = self.findChild(QLabel, "ConnectedLable")
        self.ConnectButton = self.findChild(QPushButton, "ConnectButton")
        self.TagBox = self.findChild(QSpinBox, "TagBox")
        self.TagButton = self.findChild(QPushButton, "TagButton")
        self.OpenTutorialButton = self.findChild(QPushButton, "OpenTutorialButton")
        self.AllowTraitsBox = self.findChild(QCheckBox, "AllowTraitsBox")
        self.FOWBox = self.findChild(QCheckBox, "FOWBox")
        self.DebugBox = self.findChild(QCheckBox, "DebugBox")

        # Center Label
        self.ConnectedLable.setAlignment(QtCore.Qt.AlignCenter)

        # Connect the ConnectButton signal to the attemptConnection method
        self.ConnectButton.clicked.connect(self.attemptConnection)

        # Connect the OpenTutorialButton signal to the openTutorial method
        self.OpenTutorialButton.clicked.connect(self.openTutorial)

        # Initial connection attempt
        self.attemptConnection()

    def attemptConnection(self):
        try:
            self.pm = pymem.Pymem("hoi4.exe")
            self.client = pymem.process.module_from_name(self.pm.process_handle, "hoi4.exe").lpBaseOfDll
            self.ConnectedLable.setText("Hoi4 - Connected")
            self.connected = True
            self.setBaseAddresses()
            self.TagButton.clicked.connect(self.writeTagBox)  # Connect the TagButton click signal to the writeTagBox method
            self.FOWBox.stateChanged.connect(self.handleFOWBoxChange)  # Connect the FOWBox stateChanged signal
            self.AllowTraitsBox.stateChanged.connect(self.handleAllowTraitsBoxChange)  # Connect the AllowTraitsBox stateChanged signal
            self.DebugBox.stateChanged.connect(self.handleDebugBoxChange)  # Connect the DebugBox stateChanged signal
            self.updateFOWBox()  # Update the FOWBox with the current value from memory
            self.updateAllowTraitsBox()  # Update the AllowTraitsBox with the current value from memory
            self.updateDebugBox()  # Update the DebugBox with the current value from memory
            self.updateTagBox()  # Update the TagBox with the current value from memory
        except Exception as e:
            self.ConnectedLable.setText("Hoi4 - Not Connected")
            self.connected = False

        self.setButtonsStatus()

    def setBaseAddresses(self):
        # Initialize Memory Addresses
        self.baseAddrFOW = self.pm.base_address + 0x2C29099 #FOW
        self.baseAddrAT = self.pm.base_address + 0x2C29078 #AllowTraits
        self.baseAddrTS = self.pm.base_address + 0x2E4FEF8 #Tag Switch Base
        self.baseAddrDbg = self.pm.base_address + 0x2E4F96C #Debug
        self.TSOffset = [0x4D8] #Tag Switch Offset

    def setButtonsStatus(self):
        if self.connected:
            self.ConnectButton.setEnabled(False)
            self.AllowTraitsBox.setEnabled(True)
            self.FOWBox.setEnabled(True)
            self.DebugBox.setEnabled(True)
            self.TagButton.setEnabled(True)
            self.TagBox.setEnabled(True)
        else:
            self.ConnectButton.setEnabled(True)
            self.AllowTraitsBox.setEnabled(False)
            self.FOWBox.setEnabled(False)
            self.DebugBox.setEnabled(False)
            self.TagButton.setEnabled(False)
            self.TagBox.setEnabled(False)

    def updateTagBox(self):
        if self.connected:
            targetAddrTS = MemoryUtils.OffsetCalculator(self.pm, self.baseAddrTS, self.TSOffset)
            tag_value_bytes = self.pm.read_bytes(targetAddrTS, 4)  # Read 4 bytes
            tag_value = int.from_bytes(tag_value_bytes, byteorder='little')
            self.TagBox.setValue(tag_value)

    def writeTagBox(self):
        if self.connected:
            targetAddrTS = MemoryUtils.OffsetCalculator(self.pm, self.baseAddrTS, self.TSOffset)
            new_tag_value = self.TagBox.value()
            self.pm.write_bytes(targetAddrTS, new_tag_value.to_bytes(4, byteorder='little'), 4)
            self.updateTagBox()  # Update the TagBox to reflect the new value

    def updateFOWBox(self):
        if self.connected:
            fow_value_bytes = self.pm.read_bytes(self.baseAddrFOW, 1)  # Read 1 byte
            fow_value = int.from_bytes(fow_value_bytes, byteorder='little')
            self.FOWBox.setChecked(fow_value == 1)

    def updateAllowTraitsBox(self):
        if self.connected:
            at_value_bytes = self.pm.read_bytes(self.baseAddrAT, 1)  # Read 1 byte
            at_value = int.from_bytes(at_value_bytes, byteorder='little')
            self.AllowTraitsBox.setChecked(at_value == 1)

    def updateDebugBox(self):
        if self.connected:
            dbg_value_bytes = self.pm.read_bytes(self.baseAddrDbg, 1)  # Read 1 byte
            dbg_value = int.from_bytes(dbg_value_bytes, byteorder='little')
            self.DebugBox.setChecked(dbg_value == 1)

    def handleFOWBoxChange(self, state):
        if self.connected:
            fow_value = 1 if state == QtCore.Qt.Checked else 0
            self.pm.write_bytes(self.baseAddrFOW, fow_value.to_bytes(1, byteorder='little'), 1)

    def handleAllowTraitsBoxChange(self, state):
        if self.connected:
            at_value = 1 if state == QtCore.Qt.Checked else 0
            self.pm.write_bytes(self.baseAddrAT, at_value.to_bytes(1, byteorder='little'), 1)

    def handleDebugBoxChange(self, state):
        if self.connected:
            dbg_value = 1 if state == QtCore.Qt.Checked else 0
            self.pm.write_bytes(self.baseAddrDbg, dbg_value.to_bytes(1, byteorder='little'), 1)

    def openTutorial(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(resource_path('tutorial.txt')))

if __name__ == "__main__":
    # Enable HiDPI.
    qdarktheme.enable_hi_dpi()

    app = QApplication(sys.argv)

    # Apply dark theme.
    qdarktheme.setup_theme()

    window = HoI4Window()
    window.show()
    sys.exit(app.exec_())
