# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os

from bitcointx import ChainParams
from bitcointx.core.key import CKey
from bitcointx.wallet import P2WPKHCoinAddress
from elementstx.wallet import CCoinConfidentialAddress
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow

from common import LoaderUI


def _get_random_addr():
    with ChainParams("elements"):
        blinding_key = CKey.from_secret_bytes(os.urandom(32))
        key = CKey.from_secret_bytes(os.urandom(32))
        addr = CCoinConfidentialAddress.from_unconfidential(
            P2WPKHCoinAddress.from_pubkey(key.pub), blinding_key.pub
        )
    return addr


def generate_block(rpc):
    """Generate one block"""
    return rpc.generatetoaddress(1, str(_get_random_addr()))


class BlockGenerator(QTimer):
    def __init__(self, *args):
        super(BlockGenerator, self).__init__(*args)
        self.setInterval(4000)

    def timerEvent(self, event):
        app = QApplication.instance()
        generate_block(app.rpc)


class MainWindow(QMainWindow, LoaderUI):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(__file__)
        self.generator = BlockGenerator(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_block_high)
        self.timer.setInterval(1000)
        self.timer.start()

    def update_block_high(self):
        _translate = QtCore.QCoreApplication.translate
        app = QApplication.instance()
        block_high = app.rpc.getblockcount()
        self.blockhigh.setText(
            _translate("MainWindow", "Current block: ") + f"{block_high}"
        )

    @pyqtSlot(int, name="on_autogen_stateChanged")
    def change_generator(self, status):
        if status:
            self.generator.start()
        else:
            self.generator.stop()

    def closeEvent(self, event):
        self.generator.stop()

    @pyqtSlot(int, name="on_mine_period_valueChanged")
    def update_mining_config(self, value):
        value = int(value) * 1000
        self.generator.setInterval(value)
