# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
from pathlib import Path
from typing import List

from PyQt5 import QtCore
from PyQt5.QtCore import QProcess, Qt, QTimer, qInfo
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from common import LoaderUI

from .get_contract_start_delay import GetContractStartDelay


class MainWindow(QMainWindow, LoaderUI):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(__file__)
        self.CreateCotractButton.clicked.connect(self.create_contract)

        self.SignButton.clicked.connect(self.sign_contract)
        self.SendButton.clicked.connect(self.send_contract)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_block_high)
        self.timer.setInterval(1000)
        self.timer.start()

        app = QApplication.instance()

        self.blockchain_network = app.common_settings.value(
            "blockchain_network")

        if self.blockchain_network is None:
            self.blockchain_network = "elements"
            app.common_settings.setValue("blockchain_network",
                                         self.blockchain_network)

    def update_block_high(self):
        _translate = QtCore.QCoreApplication.translate
        app = QApplication.instance()
        block_high = app.rpc.getblockcount()
        self.blockhigh.setText(
            _translate("MainWindow", "Current block: ") + f"{block_high}"
        )
        self.timer.start()

    def create_contract(self):
        app = QApplication.instance()
        plan_file, _ = QFileDialog.getOpenFileName(
            self, "Open Plan", str(app.path), filter="*.plan",
        )
        if not plan_file:
            return

        blockchain_network = app.common_settings.value("blockchain_network")

        dlg = GetContractStartDelay()
        dlg.exec()
        if dlg.result():
            contract_start_delay = dlg.ContractStartDelay.value()

            creditor_file = self.get_filename(plan_file, "cinfo")
            debtor_file = self.get_filename(plan_file, "dinfo")
            filecreditor = self.get_filename(plan_file, "cdata")
            filedebtor = self.get_filename(plan_file, "ddata")
            filetxdata = self.get_filename(plan_file, "tx")
            args: List = [
                "make",
                "-r",
                app.rpc_param,
                "--plan",
                plan_file,
                "-l",
                creditor_file,
                "-c",
                debtor_file,
                "--output-creditor",
                filecreditor,
                "--output-debtor",
                filedebtor,
                "--output-tx",
                filetxdata,
                "--contract-start-delay",
                contract_start_delay,
                "--network",
                blockchain_network
            ]
            process = QProcess(self)
            QApplication.setOverrideCursor(Qt.WaitCursor)

            def contract_created(status_int, status):
                QApplication.restoreOverrideCursor()
                if status_int:
                    result = \
                        process.readAllStandardError().data().decode("utf-8")
                    QMessageBox.critical(self, "Error", result)
                else:
                    output = \
                        process.readAllStandardOutput().data().decode("utf-8")
                    self.statusbar.showMessage(
                        f"Contract transaction was created", 5000)
                    QMessageBox.information(
                        self,
                        "Info",
                        f"{output}\n",
                    )

            args = [str(arg) for arg in args]
            process.finished.connect(contract_created)
            if getattr(sys, "frozen", False):
                facilitator_cli = f"{app.path}/cli/facilitator_cli"
            else:
                facilitator_cli = f"{app.path}/cli/facilitator_cli.py"

            qInfo(f"CLI: {facilitator_cli} {' '.join(args)}\n")
            process.start(facilitator_cli, args)

    def sign_contract(self):
        app = QApplication.instance()
        contract_tx_file, _ = QFileDialog.getOpenFileName(
            self, "Open Contract Tx", str(app.path), filter="*.tx",
        )
        if not contract_tx_file:
            return

        blockchain_network = app.common_settings.value("blockchain_network")

        creditor_sign_file = self.get_filename(contract_tx_file, "csignature")
        debtor_sign_file = self.get_filename(contract_tx_file, "dsignature")
        filetx = self.get_filename(contract_tx_file, "stx")
        args: List = [
            "sign",
            "-r",
            app.rpc_param,
            "--tx",
            contract_tx_file,
            "-c",
            creditor_sign_file,
            "-d",
            debtor_sign_file,
            "-o",
            filetx,
            "--network",
            blockchain_network
        ]
        process = QProcess(self)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        def contract_signed(status_int, status):
            QApplication.restoreOverrideCursor()
            if status_int:
                result = process.readAllStandardError().data().decode("utf-8")
                QMessageBox.critical(self, "Error", result)
            else:
                output = \
                    process.readAllStandardOutput().data().decode("utf-8")
                self.statusbar.showMessage(
                    f"Contract transaction was signed", 5000)
                QMessageBox.information(
                    self,
                    "Info",
                    f"{output}\n",
                )

        args = [str(arg) for arg in args]
        process.finished.connect(contract_signed)
        if getattr(sys, "frozen", False):
            facilitator_cli = f"{app.path}/cli/facilitator_cli"
        else:
            facilitator_cli = f"{app.path}/cli/facilitator_cli.py"

        qInfo(f"CLI: {facilitator_cli} {' '.join(args)}\n")
        process.start(facilitator_cli, args)

    def send_contract(self):
        app = QApplication.instance()
        signed_tx_file, _ = QFileDialog.getOpenFileName(
            self, "Open Signed Tx", str(app.path), filter="*.stx",
        )
        if not signed_tx_file:
            return
        with open(signed_tx_file) as file:
            tx_str = file.read()

        try:
            app.rpc.sendrawtransaction(tx_str)
        except Exception as e:
            QMessageBox.critical(
                self, "Send Error", f"Transaction was not sent: {e}"
            )
            return
        # wait_confirm(txid, app.rpc)
        app.main.statusbar.showMessage("contract transaction was sent", 5000)
        QMessageBox.information(
            self, "Info", "contract transaction was sent",
        )

    def get_filename(self, plan_file, suffix):
        plan = Path(plan_file)
        file_name = plan.stem
        file_path = plan.parent.absolute()
        file = f"{file_path}/{file_name}.{suffix}"
        return file
