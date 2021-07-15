# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication

from cli.cli_common import load_data_with_checking_hash

from common import CommonMainWindow, LoaderUI, cached_property


class MainWindow(CommonMainWindow, LoaderUI):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(__file__)
        self.plan_changed.connect(self.do_if_plan_changed)
        self.sign_save.connect(self.sign_contract)
        self.stage_found.connect(self.do_if_stage_found)
        self.is_contract_finished.connect(self.do_if_finished)

    @cached_property
    def debtor_cli(self):
        app = QApplication.instance()
        if getattr(sys, "frozen", False):
            return f"{app.path}/cli/debtor_cli"
        return f"{app.path}/cli/debtor_cli.py"

    @pyqtSlot()
    def on_openbutton_clicked(self):
        self.open_plan()

    def do_if_finished(self):
        self.getCollateral.setEnabled(True)

    def do_if_plan_changed(self, _):
        self.acceptbutton.setEnabled(True)
        self.regbutton.setEnabled(False)
        self.earlybutton.setEnabled(False)

    def do_if_stage_found(self):
        self.regbutton.setEnabled(True)
        self.earlybutton.setEnabled(True)

    @property
    def std_args(self):
        return [
            "-r",
            self.rpc_param,
            "--plan",
            self._plan_path,
            "--data",
            self._contract_data,
        ]

    @pyqtSlot(name="on_getCollateral_clicked")
    def return_collateral(self):
        self.call(
            self.debtor_cli,
            ["getcollaterall", *self.std_args, "--force"],
            "collateral was returned",
            lambda: self.getCollateral.setEnabled(False),
        )

    @pyqtSlot(name="on_regbutton_clicked")
    def make_payment(self):
        self.call(
            self.debtor_cli,
            ["paydebt", *self.std_args, "--force"],
            "debt was partially returned",
        )

    @pyqtSlot(name="on_earlybutton_clicked")
    def make_early_payment(self):
        self.call(
            self.debtor_cli,
            ["paydebt", *self.std_args, "--full", "--force"],
            "debt was fully returned",
        )

    @pyqtSlot(name="on_acceptbutton_clicked")
    def accept_plan(self):
        app = QApplication.instance()
        fileinfo = self.get_filename(f"{app.suffix}info")
        self.call(
            self.debtor_cli,
            ["accept", *self.std_args[:-2], "-o", fileinfo],
            "Plan was accepted",
            lambda: self.acceptbutton.setEnabled(False),
        )

    def sign_contract(self, sign_path):
        self.call(
            self.debtor_cli,
            ["sign", *self.std_args, "-o", sign_path],
            "Contract was signed",
            lambda: self.plan.signButton.setEnabled(False),
        )

    def validate_contract_data(self, fileName):
        debtor_data = load_data_with_checking_hash(fileName)
        debtor_fields = (
            "tx",
            "shared-blinding-xkey",
            "creditor-control-asset",
            "start-block-num",
        )
        for field in debtor_fields:
            if field not in debtor_data:
                raise ValueError(f"{field} not exists in contract data")
