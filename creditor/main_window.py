# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import pathlib
import sys
from typing import List

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QApplication, QFileDialog

from cli.cli_common import load_data_with_checking_hash
from common import (
    CommonMainWindow,
    LoaderUI,
    cached_property,
)

from .create_plan_dialog import CreatePlanDialog


class MainWindow(CommonMainWindow, LoaderUI):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(__file__)
        self.sign_save.connect(self.sign_contract)
        self.contract_data_changed.connect(self.change_data)

    @pyqtSlot()
    def on_openplanButton_clicked(self):
        self.open_plan()

    @cached_property
    def creditor_cli(self):
        app = QApplication.instance()
        if getattr(sys, "frozen", False):
            return f"{app.path}/cli/creditor_cli"
        return f"{app.path}/cli/creditor_cli.py"

    @pyqtSlot(name="on_MakePlanButton_clicked")
    def show_create_plan_dialog(self):
        app = QApplication.instance()
        assets_creditor = set(app.assetlabels.keys())
        assets_debtor = set(app.assetlabels.keys())
        dlg = CreatePlanDialog()
        dlg.LoanAssetcomboBox.addItems(assets_creditor)
        dlg.CollateralAssetcomboBox.addItems(assets_debtor)
        dlg.exec()
        if dlg.result():
            filePlan, _ = QFileDialog.getSaveFileName(
                self, "Save Plan", str(app.path), filter="*.plan",
            )
            if not filePlan:
                return
            if not filePlan.endswith(".plan"):
                filePlan += ".plan"

            plan = pathlib.Path(filePlan)
            file_name = plan.stem
            file_path = plan.parent.absolute()
            suffix = f"{app.suffix}info"
            fileInfo = f"{file_path}/{file_name}.{suffix}"

            loan_amount = dlg.LoanAmountspinBox.value()
            loan_asset = dlg.LoanAssetcomboBox.currentText().split(":")[0]
            loan_asset = app.get_asset_by_name(loan_asset)
            collateral_amount = dlg.CollateralAmountspinBox.value()
            collateral_asset = dlg.CollateralAssetcomboBox.currentText().split(
                ":"
            )[0]
            collateral_asset = app.get_asset_by_name(collateral_asset)
            total_steps = dlg.TotalStepsspinBox.value()
            total_periods = dlg.TotalPeriodsspinBox.value()
            rate_due = f"{dlg.BaseRatedoubleSpinBox.value()}"
            rate_early = f"{dlg.EarlyRatedoubleSpinBox.value()}"

            rates_late = []
            for idx in range(dlg.late_layout.count()):
                wgt = dlg.late_layout.itemAt(idx).itemAt(1).widget()
                rates_late.append(f"{wgt.value()}")

            rate_collateral_penalty = f"{dlg.PenaltyRatedoubleSpinBox.value()}"
            num_blocks = dlg.NumBlocksspinBox.value()
            args: List = [
                "make",
                "-r",
                self.rpc_param,
            ]
            args.extend(
                (
                    "--principal-asset",
                    loan_asset,
                    "--principal-amount",
                    loan_amount,
                    "--collateral-asset",
                    collateral_asset,
                    "--collateral-amount",
                    collateral_amount,
                    "--collateral-amount-unconditionally-forfeited",
                    "1",
                    "--total-steps",
                    total_steps,
                    "--total-periods",
                    total_periods,
                    "--rate-due",
                    rate_due,
                    "--rate-early",
                    rate_early,
                    "--num-blocks-in-period",
                    num_blocks,
                )
            )
            args.append("--rates-late")
            args.append(",".join(str(rl) for rl in rates_late))
            args.extend(
                (
                    "--rate-collateral-penalty",
                    rate_collateral_penalty,
                    "--output-plan",
                    filePlan,
                    "--output-info",
                    fileInfo,
                )
            )
            self.call(
                self.creditor_cli, args, "Plan was created",
                lambda: self.update_plan_info(f"{filePlan}")
            )

    def sign_contract(self, sign_path):
        args: List = [
            "sign",
            "-r",
            self.rpc_param,
        ]
        args.extend(
            (
                "--plan",
                self._plan_path,
                "--data",
                self._contract_data,
                "-o",
                sign_path,
            )
        )
        self.call(
            self.creditor_cli,
            args,
            "Contract was signed",
            lambda: self.plan.signButton.setEnabled(False),
        )

    @pyqtSlot(name="on_RevokeButton_clicked")
    def revoke_window(self):
        args: List = [
            "revokewindow",
            "-r",
            self.rpc_param,
        ]
        args.extend(
            ("--plan", self._plan_path, "--data", self._contract_data,
                "--force",)
        )
        self.call(self.creditor_cli, args, "The window was revoked")

    @pyqtSlot(name="on_GrabButton_clicked")
    def grab_collateral(self):
        args: List = [
            "revokewindow",
            "-r",
            self.rpc_param,
        ]
        args.extend(
            ("--plan", self._plan_path, "--data", self._contract_data,
                "--force",)
        )
        self.call(self.creditor_cli, args, "The collateral was grabbed")

    @pyqtSlot(name="on_SpendButton_clicked")
    def spend_coins(self):
        args: List = [
            "getpayment",
            "-r",
            self.rpc_param,
        ]
        args.extend(
            ("--plan", self._plan_path, "--data", self._contract_data,
                "--force",)
        )
        self.call(self.creditor_cli, args, "The payment was spent")

    def validate_contract_data(self, fileName):
        creditor_data = load_data_with_checking_hash(fileName)
        creditor_fields = (
            "tx",
            "shared-blinding-xkey",
            "debtor-control-asset",
            "start-block-num",
        )
        for field in creditor_fields:
            if field not in creditor_data:
                raise ValueError(f"{field} not exists in contract data")

    def change_data(self, data_file):
        self.plan_status.can_revoke.connect(self.RevokeButton.setEnabled)
        self.plan_status.can_grab.connect(self.GrabButton.setEnabled)

        def change_spend_button(value):
            self.SpendButton.setEnabled(value)
            if value:
                self.SpendButton.setStyleSheet("background-color: green")
            else:
                self.SpendButton.setStyleSheet("background-color: light gray")

        self.plan_status.have_payment.connect(change_spend_button)
