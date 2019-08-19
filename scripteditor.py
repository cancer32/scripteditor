#!/usr/bin/env python
import socket
import time
import sys
import os
import syntax

try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.uic import loadUi
except ImportError:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import QIcon
    from PyQt5.uic import loadUi

__all__ = ['ScriptEditor']

# Python compatibility for string and bytes
if sys.version_info < (3,):
    def b(x):
        return unicode(x)
else:
    import codecs

    def b(x):
        return codecs.latin_1_encode(x)[0]


class ScriptEditor(QMainWindow):
    def __init__(self, uiFile='', parent=None):
        super(self.__class__, self).__init__(parent)

        # Load ui file
        loadUi(uiFile, self)
        # Naming
        self.setWindowTitle('Script Editor')

        # Variables
        self._connected = False
        self.host = ''
        self.port = 0

        # Calling class methods
        self.retranslateUi()
        self.pbState()
        self.statusbar.clearMessage()

        # Connecting pyqtSignals
        self.actionConnect.triggered.connect(self.onConnect)
        self.actionRun.triggered.connect(self.onRun)
        self.pte_editor.cursorPositionChanged.connect(self.onTextCursorChange)
        self.actionFont.triggered.connect(self.onFontChange)
        self.actionEcho_All.toggled.connect(self.onEchoAll)

    def retranslateUi(self):
        # Add lables in statusbar
        self.lb_hoststatus = QLabel('Not Connected')
        self.lb_hoststatus.setMinimumWidth(200)
        self.lb_hoststatus.setAlignment(Qt.AlignHCenter)
        self.statusbar.addPermanentWidget(self.lb_hoststatus, 0)

        self.lb_lineno = QLabel('Lin 1 Col 1')
        self.lb_lineno.setMinimumWidth(150)
        self.lb_lineno.setAlignment(Qt.AlignHCenter)
        self.statusbar.addPermanentWidget(self.lb_lineno, 0)

    def pbState(self):
        if self._connected:
            self.actionConnect.setEnabled(False)
            self.actionDisconnect.setEnabled(True)
            self.actionRun.setEnabled(True)
            self.actionEcho_All.setEnabled(True)
            self.statusbar.showMessage('Connected to .... %s' % self.host)
            self.lb_hoststatus.setText('Host : %s@%s' % (self.host, self.port))

        else:
            self.actionConnect.setEnabled(True)
            self.actionDisconnect.setEnabled(False)
            self.actionRun.setEnabled(False)
            self.actionEcho_All.setEnabled(False)
            self.statusbar.showMessage('Disconnected')
            self.lb_hoststatus.setText('Host : Not Connected')

    @pyqtSlot()
    def onConnect(self):
        cntWnd = ConnectWindow(self, self.host, self.port)

        if cntWnd.exec_():
            self.host = cntWnd.le_host.text()
            self.port = cntWnd.le_port.value()

            if self.host and self.port:
                if self.isAlive(self.host, self.port):
                    # Open port on taget host for command output
                    openPortCmd = 'import maya.cmds as cmds\nif not cmds.commandPort(\'%s:%s\',q=True):\n\tcmds.commandPort(n=\'%s:%s\',eo=True,stp=\'python\')' % (
                        self.host, self.port + 1, self.host, self.port + 1)
                    self.sendTo(self.host, self.port, b(openPortCmd))
                    # Thread for command output
                    self.outThrd = OutputThread(self, self.host, self.port + 1)
                    # Connect pyqtSignals
                    self.outThrd.echoOut.connect(self.showOutput)
                    self.outThrd.errorOut.connect(self.statusbar.showMessage)
                    self.actionDisconnect.triggered.connect(self.outThrd.quit)
                    self.outThrd.finished.connect(self.onDisconnect)
                    # Start thread
                    self.outThrd.start()
                    # Button states
                    if self.outThrd.isRunning():
                        self._connected = True
                        self.pbState()
                    else:
                        QMessageBox.warning(self, 'Error', 'Unable to connect the host')
                        self.statusbar.showMessage('Unable to connect the host')
                else:
                    QMessageBox.warning(self, 'Error', 'Unable to find the host')
                    self.statusbar.showMessage('Unable to find the host')
            else:
                QMessageBox.warning(self, 'Error', 'Please provide the host and the port')
                self.statusbar.showMessage('Please provide the host and the port')

    @pyqtSlot()
    def onDisconnect(self):
        if self._connected:
            # Send close port command on disconnect
            closePortCmd = 'import maya.cmds as cmds\nif cmds.commandPort(\'%s:%s\',q=True):\n\tcmds.commandPort(n=\'%s:%s\',cl=True)' % (
                self.host, self.port + 1, self.host, self.port + 1)
            self.sendTo(self.host, self.port, b(closePortCmd))

        self._connected = False
        self.pbState()

    # Slot for showing command output received from the host
    @pyqtSlot('QString')
    def showOutput(self, txt):
        if txt and txt != 'None':
            self.tb_output.append(txt)

    # Slot for changing line and column number on stausbar
    @pyqtSlot()
    def onTextCursorChange(self):
        cursor = self.pte_editor.textCursor()
        x = cursor.blockNumber() + 1
        y = cursor.positionInBlock() + 1
        self.lb_lineno.setText('Lin %s Col %s' % (x, y))

    # Slot for sending commands to the host
    @pyqtSlot()
    def onRun(self):
        cursor = self.pte_editor.textCursor()
        text = ''

        if cursor.hasSelection():
            text = cursor.selectedText()
        else:
            text = self.pte_editor.toPlainText()

        if text:
            try:
                text = unicode(text).replace(u'\u2029', u'\n')
            except:
                text = text.replace('\u2029', '\n')

            # Send command
            ans = self.sendTo(self.host, self.port, b(text))
            self.showOutput(text)
            if ans:
                ans = ans.decode('utf-8')
                ans = ans.replace('\n\x00', '')
                ans = ans.strip()
                self.showOutput(ans)

    # Slot for setting echo all commands
    @pyqtSlot(bool)
    def onEchoAll(self, state):
        ScriptEditor.sendTo(self.host, self.port, b('import maya.cmds as cmds'))
        if state:
            cmdecho = ScriptEditor.sendTo(self.host, self.port, b('cmds.commandEcho(st=True)'))
            if cmdecho:
                self.statusbar.showMessage('Echo all commands on')
        else:
            cmdecho = ScriptEditor.sendTo(self.host, self.port, b('cmds.commandEcho(st=False)'))
            if cmdecho:
                self.statusbar.showMessage('Echo all commands off')

    # Slot for font change
    @pyqtSlot()
    def onFontChange(self):
        currentFont = self.pte_editor.font()
        font, status = QFontDialog().getFont(currentFont)

        if status:
            size = font.pointSize()
            self.pte_editor.setFont(font)
            self.pte_editor.setTabStopWidth((32 * size) / 12)

    def closeEvent(self, event):
        if self._connected:
            # On close disconnect host and stop the thread
            self.onDisconnect()
            if self.outThrd.isRunning():
                self.outThrd.quit()

        event.accept()

    @staticmethod
    def isAlive(host, port, timeout=4):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return

    @staticmethod
    def sendTo(host, port, text, buff=20480, timeout=20):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))

            if result == 0:
                sock.send(text)
                data = sock.recv(buff)
                sock.close()
                if data:
                    return data
                else:
                    return
            else:
                return
        except Exception as e:
            print(e)
            return


class ConnectWindow(QDialog):
    def __init__(self, parent=None, host=None, port=None):
        super(self.__class__, self).__init__(parent)
        # Naming window
        self.setWindowTitle('Connect')
        # Adding root layout
        self.lyt = QGridLayout(self)
        self.setLayout(self.lyt)
        # Calling class methods
        self.retranslateUi(host, port)
        # Connecting signals
        self.bb_connect.accepted.connect(self.accept)
        self.bb_connect.rejected.connect(self.reject)

    def retranslateUi(self, host, port):
        # Adding lineEdits and labels
        lb_host = QLabel('Host  : ')

        self.le_host = QLineEdit()
        if host:
            self.le_host.setText(host)
        else:
            self.le_host.setText('127.0.0.1')

        lb_port = QLabel('Port  : ')

        self.le_port = QSpinBox()
        self.le_port.setRange(0,99999)
        if port:
            self.le_port.setValue(port)
        else:
            self.le_port.setValue(5050)

        # Adding connect button
        self.bb_connect = QDialogButtonBox()
        self.bb_connect.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        # Adding widgets to layout
        self.lyt.addWidget(lb_host,0,0)
        self.lyt.addWidget(self.le_host,0,1)
        self.lyt.addWidget(lb_port,1,0)
        self.lyt.addWidget(self.le_port,1,1)
        self.lyt.addWidget(self.bb_connect,2,0,2,0)


class OutputThread(QThread):
    echoOut = pyqtSignal(str)
    errorOut = pyqtSignal(str)

    def __init__(self, parent=None, host='', port=0000, buff=4096):
        super(self.__class__, self).__init__(parent)
        self.parent = parent
        self.host = host
        self.port = port
        self.buffer = buff
        self._running = False

    def __del__(self):
        try:
            self.wait()
        except Exception as e:
            print('[Error] %s' % e)

    def run(self, *args, **kwargs):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            status = self.sock.connect_ex((self.host, self.port))

            if status == 0:
                self._running = True

                while True:
                    if self._running:
                        data = self.sock.recv(self.buffer)
                        if data:
                            data = data.decode('utf-8')
                            data = data.replace('\n\x00', '')
                            data = data.strip()
                        self.echoOut.emit(data)
                        time.sleep(0.1)
                    else:
                        break
            else:
                print('[Error] Unable to connect output port from host.')
                self.errorOut.emit('Unable to connect output port from host.')
                self.quit()
        except Exception as e:
            print('[Error] %s' % e)
            self.errorOut.emit('%s' %e)

    def quit(self, *args, **kwargs):
        if self._running:
            self._running = False
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        super(self.__class__, self).quit()


if __name__ == '__main__':
    path = os.path.dirname(__file__)
    os.chdir(path)
    app = QApplication(sys.argv)
    wnd = ScriptEditor('scripteditor_ui.ui')
    highlight = syntax.PythonHighlighter(wnd.pte_editor.document())
    wnd.show()
    sys.exit(app.exec_())
