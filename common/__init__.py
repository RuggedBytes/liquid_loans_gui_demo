# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import hashlib
import json
import math
import pathlib
import sys

from colour import Color
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import (
    QMutex,
    QProcess,
    QSettings,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
    qInfo,
)
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.uic import loadUiType

from bitcointx.wallet import CCoinExtKey
from bitcointx.core import CTransaction, b2lx, x, lx
from bitcointx.rpc import JSONRPCError
from bitcointx import ChainParams
from cli.lib.constants import (
    LOCKED_COLLATERAL_PATH,
    CONTRACT_COLLATERAL_INP_INDEX, CONTRACT_PRINCIPAL_INP_INDEX,
    CONTRACT_COLLATERAL_OUT_INDEX,
)
from cli.lib.types import Amount, PlanData, ElementsRPCCaller, DataLookupError
from cli.cli_common import load_data_with_checking_hash
from elementstx.core import (
    Uint256, calculate_asset, generate_asset_entropy, CAsset
)
from cli.lib.rpc_utils import (
    find_all_payments, track_tx_by_prevouts, track_contract_txs
)
from cli.lib.generator import generate_abl_contract_for_lateral_stage
from cli.lib.utils import SafeDerivation

from .demo_config import link_to_esplora

RED_STYLE_PROGRESS_BAR = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}
QProgressBar::chunk {
    background-color: red;
}
"""


def clear_layout(lo):
    for _ in range(lo.count()):
        item = lo.takeAt(0)

        if isinstance(item, QLayout):
            clear_layout(item)
        else:
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        lo.removeItem(item)


class LoaderUI:
    def setupUi(self, file):
        path = pathlib.Path(file).parent.absolute()
        ui_name = self.__class__.__name__.lower() + ".ui"
        ui_file = path / "ui" / ui_name
        ui, _ = loadUiType(ui_file)
        ui = ui()
        ui.setupUi(self)
        self.__dict__.update(ui.__dict__)


class PlanMonitor(QTimer):
    block_high_updated = pyqtSignal(int)
    contract_tx_changed = pyqtSignal()

    def __init__(self, rpc):
        super(PlanMonitor, self).__init__()
        self._rpc = rpc
        self._current_block = None
        self.setInterval(2000)
        self.start()

    def timerEvent(self, event):
        try:
            block_high = self._rpc.getblockcount()
        except JSONRPCError:
            return

        if block_high != self._current_block:
            self._current_block = block_high
            self.block_high_updated.emit(block_high)


class GuiRPCCaller:
    def __init__(self, **kwargs):
        self.mutex = QMutex()
        self._coin_api = ElementsRPCCaller(**kwargs)

    def __getattr__(self, name):
        self.mutex.lock()
        try:
            return self._coin_api.__getattr__(name)
        finally:
            self.mutex.unlock()


def get_dict_from_settings(settings, group_key, default):
    if group_key in settings.childGroups():
        settings.beginGroup(group_key)
        param = {}
        for key in settings.childKeys():
            param[key] = settings.value(key)
        settings.endGroup()
    else:
        settings.beginGroup(group_key)
        for key, value in default.items():
            settings.setValue(key, value)
        settings.endGroup()
        param = default
    return param


class LoanApp(QApplication):
    suffix = ""
    config_name = "Loan"
    grab_msg = ""
    revoke_msg = ""

    def __init__(self, **kwargs):
        super(LoanApp, self).__init__(sys.argv)
        if getattr(sys, "frozen", False):
            application_path = pathlib.Path(sys.executable).parent.absolute()
        else:
            application_path = pathlib.Path(__file__).parent.parent.absolute()
        self.path = application_path
        QSettings.setPath(
            QSettings.IniFormat, QSettings.UserScope, str(self.path)
        )
        self.settings = QSettings(
            QSettings.IniFormat,
            QSettings.UserScope,
            "config",
            self.config_name,
        )
        self.common_settings = QSettings(
            QSettings.IniFormat, QSettings.UserScope, "config", "common",
        )
        rpc_param = get_dict_from_settings(self.settings, "rpc", kwargs)
        self.rpc = GuiRPCCaller(**rpc_param)
        self.rpc_param = list(rpc_param.values()).pop()
        self.assetlabels = self.rpc.dumpassetlabels()

    def get_asset_name(self, asset_hex_in):
        for name, asset_hex in self.assetlabels.items():
            if asset_hex == asset_hex_in:
                return name
        return asset_hex_in

    def get_asset_by_name(self, asset_name):
        return self.assetlabels.get(asset_name, asset_name)


class StageLayout(QWidget):
    def __init__(self, *arg):
        super(StageLayout, self).__init__(*arg)
        self.gbox = QGridLayout(self)
        self.gbox.setSpacing(0)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        # Make gradient
        powderblue = Color("#B0E0E6")
        blue = Color("#4040FF")
        row_colors = powderblue.range_to(blue, self.gbox.rowCount())
        width = self.width()
        for idx in range(self.gbox.rowCount()):
            new_color = next(row_colors)
            color = QtGui.QColor.fromRgb(
                new_color.red * 255,
                new_color.green * 255,
                new_color.blue * 255,
            )
            painter.setPen(color)
            painter.setBrush(color)
            cell_rect = self.gbox.cellRect(idx, 0)
            x = cell_rect.topLeft().x()
            y = cell_rect.topLeft().y()
            height = cell_rect.height()
            painter.drawRect(x, y, width, height)
        # Draw lines
        painter.setPen(QtGui.QPen(QtCore.Qt.black))
        for _y in range(self.gbox.rowCount()):
            for _x in range(self.gbox.columnCount()):
                itm = self.gbox.itemAtPosition(_y, _x)
                if itm is not None and isinstance(itm.widget(), StageWidget):
                    stage_w = itm.widget()
                    if stage_w._prev is not None:
                        start = stage_w._prev.tw.mapToGlobal(
                            stage_w._prev.tw.rect().topRight()
                        )
                        stop = stage_w.tw.mapToGlobal(
                            stage_w.tw.rect().topLeft()
                        )
                        sourcePoint = self.mapFromGlobal(start)
                        destPoint = self.mapFromGlobal(stop)
                        arrowSize = 10.0
                        line = QtCore.QLineF(sourcePoint, destPoint)

                        if line.length() == 0.0:
                            continue

                        painter.drawLine(line)
                        # drawing the arrow is from here
                        # https://gist.github.com/reusee/2406975
                        # Draw the arrows if there's enough room.
                        angle = math.acos(line.dx() / line.length())
                        if line.dy() >= 0:
                            angle = math.pi * 2.0 - angle

                        destArrowP1 = destPoint + QtCore.QPointF(
                            math.sin(angle - math.pi * 2 / 5) * arrowSize,
                            math.cos(angle - math.pi * 2 / 5) * arrowSize,
                        )
                        destArrowP2 = destPoint + QtCore.QPointF(
                            math.sin(angle - math.pi + 2 * math.pi / 5)
                            * arrowSize,
                            math.cos(angle - math.pi + 2 * math.pi / 5)
                            * arrowSize,
                        )

                        painter.setBrush(QtCore.Qt.black)
                        painter.drawPolygon(
                            QtGui.QPolygonF(
                                [line.p2(), destArrowP1, destArrowP2]
                            )
                        )

        super(StageLayout, self).paintEvent(event)


class EarlyButton(QPushButton):
    def paintEvent(self, event):
        super(EarlyButton, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        image_path = pathlib.Path(__file__).parent.absolute() / "green.png"
        image = QtGui.QPixmap(f"{image_path}")
        size = self.height() * 5 // 7
        painter.drawPixmap(
            QtCore.QRect(
                self.width() - size, (self.height() - size) / 2, size, size
            ),
            image,
        )


class GrabButton(QPushButton):
    def paintEvent(self, event):
        super(GrabButton, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtCore.Qt.black))
        painter.drawLine(0, self.height() / 2, self.width(), self.height() / 2)
        image_path = pathlib.Path(__file__).parent.absolute() / "red.png"
        image = QtGui.QPixmap(f"{image_path}")
        size = self.height() * 6 // 14
        painter.drawPixmap(
            QtCore.QRect(
                self.width() - size, (self.height() - size) / 2, size, size
            ),
            image,
        )


class StageWidget(QWidget):
    def __init__(self, stage, prev_widget, highlight, color):
        super(StageWidget, self).__init__()
        hbox = QVBoxLayout(self)
        hbox.setSpacing(0)
        if stage.next_lateral_stage is not None:
            br_btn = QPushButton(text=f"{stage.regular_repayment_amount}")
            hbox.addWidget(br_btn)
            br_btn.clicked.connect(self.show_info)
        self._stage = stage
        early_btn = EarlyButton(text=f"{stage.early_repayment_amount}")
        hbox.addWidget(early_btn)
        early_btn.clicked.connect(self.show_info)
        self._prev = prev_widget
        self.tw = early_btn if stage.next_lateral_stage is None else br_btn
        if highlight:
            if stage.next_lateral_stage is not None:
                br_btn.setStyleSheet("QPushButton {background-color: green}")
            early_btn.setStyleSheet("EarlyButton {background-color: green}")
        else:
            if stage.next_lateral_stage is not None:
                br_btn.setStyleSheet(
                    f"QPushButton {{background-color: {color}}}"
                )
            early_btn.setStyleSheet(
                f"EarlyButton {{background-color: {color}}}"
            )

    def show_info(self):
        info = "\n".join(
            (
                f"body of the debt: {self._stage.B}",
                f"regular payment: {self._stage.regular_repayment_amount}",
                f"early full payment: {self._stage.early_repayment_amount}",
                f"lstage level: {self._stage.parent_lateral_stage.level_n}",
                f"vstage index: {self._stage.index_m}",
            )
        )
        QMessageBox.information(self, "Plan", info)


class GrabWidget(QWidget):
    def __init__(self, stage, color):
        super(GrabWidget, self).__init__()
        hbox = QVBoxLayout(self)
        hbox.setSpacing(0)

        self._stage = stage
        to_creditor_amount = stage.amount_C_forfeited
        to_debtor_amount = stage.plan.C - stage.amount_C_forfeited
        common_btn = GrabButton(
            parent=self, text=f"{to_creditor_amount}\n{to_debtor_amount}"
        )
        hbox.addWidget(common_btn)
        common_btn.clicked.connect(self.show_info)

        self._prev = None
        self.tw = common_btn
        common_btn.setStyleSheet(f"GrabButton {{background-color: {color}}}")

    def show_info(self):
        to_creditor_amount = self._stage.amount_C_forfeited
        to_debtor_amount = self._stage.plan.C - self._stage.amount_C_forfeited
        info = "\n".join(
            (f"to creditor: {to_creditor_amount}",
             f"to debtor: {to_debtor_amount}",)
        )
        QMessageBox.information(self, "Plan", info)


def get_short_name(name):
    app = QApplication.instance()
    alias_name = app.get_asset_name(name)
    if len(alias_name) > 32:
        alias_name = f"{alias_name[:7]}...{alias_name[-7:]}"
    return alias_name


class BalanceWidget(QWidget, LoaderUI):
    def __init__(self, *arg):
        super(BalanceWidget, self).__init__(*arg)
        self.setupUi(__file__)
        app = QApplication.instance()
        self._rpc = app.rpc
        self.list_asset = list(app.assetlabels.keys())
        app.main.add_asset.connect(self.add_asset)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.start()
        self._timer.timeout.connect(self.update_balance)
        self._timer.timeout.emit()

    def add_asset(self, asset_hex):
        if not asset_hex:
            self.list_asset = []
        else:
            self.list_asset.append(asset_hex)
        self.update_balance()

    def add_assets(self):
        for asset_hex in self.list_asset:
            idx = self.balance_list.count()
            asset_label = QLabel(f"{get_short_name(asset_hex)}: ")
            asset_label.setToolTip(asset_hex)
            self.balance_list.setWidget(
                idx, QFormLayout.LabelRole, asset_label
            )
            try:
                balance = self._rpc.getbalance("*", 0, False, asset_hex,)
            except JSONRPCError:
                return
            self.balance_list.setWidget(
                idx, QFormLayout.FieldRole, QLabel(f"{Amount(balance)}")
            )

    def update_balance(self):
        self.clear()
        self.add_assets()

    def clear(self):
        clear_layout(self.balance_list)


class PlanSummary(QWidget, LoaderUI):
    contract_data_changed = pyqtSignal(str)
    create_sign = pyqtSignal()

    def __init__(self, plan_path, *arg):
        super(PlanSummary, self).__init__(*arg)
        self.setupUi(__file__)
        _translate = QtCore.QCoreApplication.translate
        with open(plan_path) as f:
            plandata = PlanData(**json.loads(f.read()))

        self._plan_name = pathlib.Path(plan_path).stem

        self.base.setText(f"{plandata.rates.rate_due} %")
        self.early.setText(f"{plandata.rates.rate_early} %")
        self.penalty.setText(f"{plandata.rates.rate_collateral_penalty} %")
        for n, late_rate in enumerate(plandata.rates.rates_late):
            label = QLabel(self.groupBox)
            label.setText(_translate("Form", f"Late repayment rate {n+1}:"))
            idx = self.formLayout.count()
            self.formLayout.setWidget(idx, QFormLayout.LabelRole, label)
            late = QLabel(self.groupBox)
            late.setText(f"{late_rate} %")
            self.formLayout.setWidget(idx, QFormLayout.FieldRole, late)
        self.periods.setText(f"{plandata.N}")
        principal_asset = plandata.principal_asset.to_hex()
        collateral_asset = plandata.collateral_asset.to_hex()
        self.collateral_asset.setText(get_short_name(collateral_asset))
        self.collateral_asset.setToolTip(collateral_asset)
        self.collateral_amount.setText(f"{plandata.collateral_amount} sat")
        self.principal_asset.setText(get_short_name(principal_asset))
        self.principal_asset.setToolTip(principal_asset)
        self.principal_amount.setText(f"{plandata.principal_amount} sat")

        self.repayment_plan = plandata.to_repayment_plan()
        self.contractButton.clicked.connect(self.add_contract_data)
        self.contract_data = None
        self.signButton.clicked.connect(lambda: self.create_sign.emit())
        app = QApplication.instance()
        app.main.add_asset.emit("")
        app.main.add_asset.emit(principal_asset)
        app.main.add_asset.emit(collateral_asset)

    def add_contract_data(self):
        app = QApplication.instance()
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "Open Contract Data",
            str(app.path),
            filter=f"{self._plan_name}.{app.suffix}data",
        )

        if not fileName:
            return

        main_window = self.parent().parent()

        if hasattr(main_window, "validate_contract_data"):
            try:
                main_window.validate_contract_data(fileName)
            except Exception as e:
                QMessageBox.critical(
                    self, "Contract Data Error", f"Error: {e}"
                )
                return

        self.signButton.setEnabled(True)
        self.contract_data = fileName
        self.contract_data_changed.emit(fileName)
        self.contractButton.setEnabled(False)


class PlanStatus(QWidget):
    can_revoke = pyqtSignal(bool)
    can_grab = pyqtSignal(bool)
    have_payment = pyqtSignal(bool)

    def __init__(self, plan_widget, *arg):
        super(PlanStatus, self).__init__(*arg)
        app = QApplication.instance()
        self._rpc = app.rpc
        self._bitcoin_asset = CAsset(lx(app.assetlabels["bitcoin"]))
        self._plan_widget = plan_widget
        self._repayment_plan = plan_widget.repayment_plan
        self._current_block_label = None

        self.link_to_esplora = app.common_settings.value("link")

        if self.link_to_esplora is None:
            self.link_to_esplora = link_to_esplora
            app.common_settings.setValue("link", self.link_to_esplora)

        self.blockchain_network = app.common_settings.value(
            "blockchain_network")

        if self.blockchain_network is None:
            self.blockchain_network = "elements"
            app.common_settings.setValue("blockchain_network",
                                         self.blockchain_network)

        self._current_block = None
        self.horizontalLayout = QVBoxLayout(self)

        if self._plan_widget.contract_data is None:
            self.add_stage_info(None)
            return

        with ChainParams(self.blockchain_network):
            self.read_contract_data()
            self.track_contract(None)
            self.check_contract_finished()

        self.add_contract_start_info()
        self.add_not_found()
        self.add_current_block_info()
        self.add_stage_info(None)
        self.last_stage = False

    def read_contract_data(self):
        data = load_data_with_checking_hash(self._plan_widget.contract_data)
        self._start_block = data["start-block-num"]
        self._shared_blinding_xkey = CCoinExtKey(data["shared-blinding-xkey"])
        self._tx = data["tx"]

    def add_timeout_info(self, vstage):
        if self._current_block is None:
            return
        if vstage is None:
            return
        widget = QWidget()
        hbox = QHBoxLayout(widget)
        hbox.addWidget(QLabel("Window Time: "))
        bar = QProgressBar()

        timeout_blocks = (
            vstage.parent_lateral_stage.level_n + vstage.index_m + 1
        ) * vstage.plan.num_blocks_in_period
        timeout_blocks = self._start_block + timeout_blocks

        bar.setMinimum(timeout_blocks - vstage.plan.num_blocks_in_period)
        bar.setMaximum(timeout_blocks)

        if int(self._current_block) > bar.maximum():
            msg = self._msg if hasattr(self, "_msg") else ""
            bar.setFormat(f"current block: {self._current_block}" f"{msg}")
            bar.setValue(bar.maximum())
            bar.setStyleSheet(RED_STYLE_PROGRESS_BAR)
            if self.last_stage:
                self.can_grab.emit(True)
                self.can_revoke.emit(False)
            else:
                self.can_grab.emit(False)
                self.can_revoke.emit(True)
        else:
            bar.setFormat(f"current block: %v")
            self.can_grab.emit(False)
            self.can_revoke.emit(False)

        bar.setValue(int(self._current_block))
        self._bar = bar
        hbox.addWidget(bar)
        hbox.addWidget(QLabel(f"<- Timeout"))
        self.horizontalLayout.addWidget(widget)

    def add_not_found(self):
        label = QLabel()
        label.setText(f"Contract TX not found in blockchain")
        self.horizontalLayout.addWidget(label)

    @pyqtSlot()
    def change_status(self):
        self._change_status()

    def _change_status(self):
        if not hasattr(self, "_start_block"):
            self.add_stage_info(None)
            return

        if not hasattr(self, "_contract_tx_list"):
            return

        self.clear()

        self.add_current_block_info()
        self.add_contract_start_info()

        if hasattr(self, "_finished_txid"):
            self.add_contract_tx_info(self._finished_txid)
            self.add_finish_info()
            self.can_grab.emit(False)
            self.can_revoke.emit(False)
            return

        last_contract_txid = b2lx(self._contract_tx_list[-1].GetTxid())
        self.add_last_contract_tx_info(last_contract_txid)

        contract_txid = b2lx(self._contract_tx_list[0].GetTxid())
        self.add_contract_tx_info(contract_txid)

        vstage = self._vstage_list[-1]
        lstage = vstage.parent_lateral_stage

        app = QApplication.instance()

        if vstage.index_m == len(lstage.vertical_stages) - 1:
            self._msg = app.grab_msg
            self.last_stage = True
        else:
            self._msg = app.revoke_msg
            self.last_stage = False

        self.add_stage_info(vstage)
        self.add_timeout_info(vstage)
        app.main.stage_found.emit()

    def add_stage_info(self, current_vstage):
        mywidget = StageLayout()
        gbox = mywidget.gbox
        gray = Color("#848484")
        white = Color("#FAFAFA")
        first_lstage = self._repayment_plan.first_lateral_stage
        num_vstages = sum(vs.num_vstages_recursive(only_branched=False)
                          for vs in first_lstage.vertical_stages)

        colors = white.range_to(gray, num_vstages)

        def show_stages(layout, lstage, plan_color,
                        row=0, column=0, prev=None):
            current_plan_colors = [
                next(colors, "light gray") for _ in lstage.vertical_stages[1:]
            ]
            current_plan_colors.append(plan_color)
            num_branched = 0
            for vstage, color in zip(
                reversed(lstage.vertical_stages), current_plan_colors
            ):
                stage_widget = StageWidget(
                    vstage,
                    prev if vstage.index_m == 0 else None,
                    current_vstage == vstage,
                    color,
                )
                gbox.addWidget(
                    stage_widget,
                    # row
                    vstage.index_m + row,
                    # column
                    column + vstage.parent_lateral_stage.level_n + 1,
                )
                if vstage.next_lateral_stage is not None:
                    show_stages(
                        layout,
                        vstage.next_lateral_stage,
                        color,
                        vstage.index_m + row + 1,
                        column + num_branched,
                        stage_widget,
                    )

                num_branched += vstage.num_vstages_recursive(
                    only_branched=True)

            grab_widget = GrabWidget(lstage.vertical_stages[-1], "red",)
            gbox.addWidget(
                grab_widget,
                # row
                lstage.vertical_stages[-1].index_m + row + 1,
                # column
                column + lstage.level_n + 1,
            )

        show_stages(gbox, self._repayment_plan.first_lateral_stage,
                    next(colors, "light gray"))
        for idx in range(gbox.rowCount()):
            label = QLabel()
            label.setText(f"period {idx +1}")
            gbox.addWidget(label, idx, 0)
        scroll = QScrollArea()
        # scroll.setFixedHeight(250)
        scroll.setWidget(mywidget)
        self.horizontalLayout.addWidget(scroll)

    def add_finish_info(self):
        hbox = QHBoxLayout()
        cap_label = QLabel()
        cap_label.setText("The contract was finished.")
        hbox.addWidget(cap_label)
        label = QLabel()
        label.setText("Last TX:")
        hbox.addWidget(label)
        label = QLabel()
        linked_txid = (
            f'<a href="{self.link_to_esplora}'
            f'/tx/{self._finished_txid}">{self._finished_txid}</a>'
        )
        label.setText(f"{linked_txid}")
        label.setOpenExternalLinks(True)
        hbox.addWidget(label)
        spacerItem = QSpacerItem(
            40, 20, QSizePolicy.Minimum, QSizePolicy.Expanding
        )
        hbox.addStretch()
        self.horizontalLayout.addLayout(hbox)
        self.horizontalLayout.addItem(spacerItem)
        self.horizontalLayout.addWidget(QWidget())

    def add_contract_start_info(self):
        label = QLabel()
        label.setText(f"Contract start block: {self._start_block}")
        self.horizontalLayout.addWidget(label)

    def add_contract_tx_info(self, txid):
        label = QLabel()
        linked_txid = (
            f'<a href="{self.link_to_esplora}' f'/tx/{txid}">{txid}</a>'
        )
        label.setText(f"Contract Txid: {linked_txid}")
        label.setOpenExternalLinks(True)
        self.horizontalLayout.addWidget(label)

    def add_last_contract_tx_info(self, txid):
        label = QLabel()
        linked_txid = (
            f'<a href="{self.link_to_esplora}' f'/tx/{txid}">{txid}</a>'
        )
        label.setText(f"Last Contract Txid: {linked_txid}")
        label.setOpenExternalLinks(True)
        self.horizontalLayout.addWidget(label)

    def add_current_block_info(self):
        hbox = QHBoxLayout()
        label = QLabel()
        label.setText(f"{self._current_block}")
        cap_label = QLabel(label)
        cap_label.setText("Current block:")
        hbox.addWidget(cap_label)
        hbox.addWidget(label)
        hbox.addStretch()
        if self._current_block_label is not None:
            self._current_block_label.setParent(None)
        self._current_block_label = label
        self.horizontalLayout.addLayout(hbox)

    @pyqtSlot(int)
    def change_block(self, block):
        self._current_block_label.setText(f"{block}")
        self._current_block = block

        with ChainParams("elements"):
            self.track_contract(block)
            self.check_contract_finished()
            self.check_payment_exists()

        if hasattr(self, "_bar"):
            self._bar.setValue(int(block))
            if int(self._current_block) > self._bar.maximum():
                msg = self._msg if hasattr(self, "_msg") else ""
                self._bar.setFormat(
                    f"current block: {self._current_block}" f"{msg}"
                )
                self._bar.setValue(self._bar.maximum())
                self._bar.setStyleSheet(RED_STYLE_PROGRESS_BAR)
                if self.last_stage:
                    self.can_grab.emit(True)
                    self.can_revoke.emit(False)
                else:
                    self.can_grab.emit(False)
                    self.can_revoke.emit(True)

    def check_contract_finished(self):
        if hasattr(self, "_contract_tx_list"):
            if len(self._contract_tx_list) > len(self._vstage_list):
                assert (
                    len(self._contract_tx_list) == len(self._vstage_list) + 1
                )
                finished_txid = b2lx(self._contract_tx_list[-1].GetTxid())
                self._finished_txid = finished_txid
                self._change_status()
                parent = self.parent()
                if parent:
                    parent = parent.parent()
                    if parent:
                        parent.is_contract_finished.emit()

    def track_contract(self, current_block):  # noqa
        if current_block is None:
            try:
                current_block = self._rpc.getblockcount()
                self._current_block = current_block
            except JSONRPCError:
                return

        if current_block <= self._start_block:
            return

        if not hasattr(self, "_contract_tx_list"):
            incomplete_contract_tx = CTransaction.deserialize(x(self._tx))
            collateral_inp = incomplete_contract_tx.vin[
                CONTRACT_COLLATERAL_INP_INDEX
            ]
            principal_inp = incomplete_contract_tx.vin[
                CONTRACT_PRINCIPAL_INP_INDEX
            ]

            # Facilitator blanks out the input of the other party,
            # check that one of these inputs is blanked out,
            # and use other input for finding the contract tx in blockchain
            if collateral_inp.prevout.hash == b'\x00'*32:
                idx = CONTRACT_PRINCIPAL_INP_INDEX
            elif principal_inp.prevout.hash == b'\x00'*32:
                idx = CONTRACT_COLLATERAL_INP_INDEX
            else:
                raise RuntimeError("Uknown contract tx data")

            try:
                contract_tx = track_tx_by_prevouts(
                    b2lx(incomplete_contract_tx.vin[idx].prevout.hash),
                    self._rpc,
                    prev_txout_index=incomplete_contract_tx.vin[idx].prevout.n,
                    from_block=self._start_block,
                    to_block=current_block
                )
            except (JSONRPCError, DataLookupError):
                return

            if not contract_tx:
                return

            contract_hash_preimage = self._shared_blinding_xkey.pub + str(
                self._repayment_plan.deterministic_representation()
            ).encode("utf-8")
            contract_hash = Uint256(
                hashlib.sha256(contract_hash_preimage).digest()
            )
            creditor_control_asset = calculate_asset(
                generate_asset_entropy(
                    contract_tx.vin[CONTRACT_PRINCIPAL_INP_INDEX].prevout,
                    contract_hash
                )
            )
            self._creditor_control_asset = creditor_control_asset

            debtor_control_asset = calculate_asset(
                generate_asset_entropy(
                    contract_tx.vin[CONTRACT_COLLATERAL_INP_INDEX].prevout,
                    contract_hash
                )
            )
            self._debtor_control_asset = debtor_control_asset

            unblind_result = contract_tx.vout[
                CONTRACT_COLLATERAL_OUT_INDEX
            ].unblind_confidential_pair(
                self._shared_blinding_xkey.derive_path(
                    LOCKED_COLLATERAL_PATH
                ).priv,
                contract_tx.wit.vtxoutwit[
                    CONTRACT_COLLATERAL_OUT_INDEX
                ].rangeproof,
            )
            if unblind_result.error:
                raise RuntimeError(
                    f"Unblindable contract tx data: {unblind_result.error}")

            with SafeDerivation():
                generate_abl_contract_for_lateral_stage(
                    self._repayment_plan.first_lateral_stage,
                    self._shared_blinding_xkey,
                    self._start_block,
                    creditor_control_asset,
                    debtor_control_asset,
                    self._bitcoin_asset,
                    unblind_result.get_descriptor()
                )

            try:
                contract_tx_list, vstage_list = track_contract_txs(
                    b2lx(contract_tx.vin[idx].prevout.hash),
                    self._rpc,
                    prev_txout_index=contract_tx.vin[idx].prevout.n,
                    from_block=self._start_block,
                    to_block=current_block,
                    plan=self._repayment_plan
                )
            except (JSONRPCError, DataLookupError):
                return

            self._contract_tx_list = contract_tx_list
            self._vstage_list = vstage_list
            self._change_status()
        else:
            contract_tx = self._contract_tx_list[-1]
            idx = CONTRACT_COLLATERAL_INP_INDEX
            try:
                contract_tx_list, vstage_list = track_contract_txs(
                    b2lx(contract_tx.vin[idx].prevout.hash),
                    self._rpc,
                    prev_txout_index=contract_tx.vin[idx].prevout.n,
                    from_block=contract_tx.block_num,
                    to_block=current_block,
                    plan=self._repayment_plan
                )
            except (JSONRPCError, DataLookupError):
                return

            assert (
                self._contract_tx_list[-1].GetTxid() ==
                contract_tx_list[0].GetTxid()
            )

            self._contract_tx_list.extend(contract_tx_list[1:])
            self._vstage_list.extend(vstage_list[1:])

            if len(contract_tx_list) > 1:
                self._change_status()

    def check_payment_exists(self):
        if hasattr(self, "_contract_tx_list") and \
                hasattr(self, "_creditor_control_asset"):
            payments_list = find_all_payments(
                self._contract_tx_list, self._creditor_control_asset,
                self._rpc
            )
        else:
            payments_list = []

        self.have_payment.emit(bool(payments_list))

    def clear(self):
        if hasattr(self, "_bar"):
            del self._bar

        clear_layout(self.horizontalLayout)


class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """  # noqa

    def __init__(self, func):
        self.__doc__ = getattr(func, "__doc__")
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self

        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class CommonMainWindow(QMainWindow):
    plan_changed = pyqtSignal(str)
    contract_data_changed = pyqtSignal(str)
    sign_save = pyqtSignal(str)
    add_asset = pyqtSignal(str)
    stage_found = pyqtSignal()
    is_contract_finished = pyqtSignal()

    def __init__(self):
        super(CommonMainWindow, self).__init__()
        self._plan_path = None
        self._contract_data = None
        self._monitor = None
        app = QApplication.instance()
        self.rpc_param = app.rpc_param

        self.blockchain_network = app.common_settings.value(
            "blockchain_network")

        if self.blockchain_network is None:
            self.blockchain_network = "elements"
            app.common_settings.setValue("blockchain_network",
                                         self.blockchain_network)

    def showEvent(self, event):
        if hasattr(self, "balance"):
            return
        if not hasattr(self, "balance_place"):
            return
        self.balance = BalanceWidget(self)
        self.balance_place.addWidget(self.balance)

    def call(self, app, args, message, done_func=None, box_message=None):
        args.extend(["--network", self.blockchain_network])

        process = QProcess(self)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        def process_finished(status_int, status):
            QApplication.restoreOverrideCursor()
            if status_int:
                result = process.readAllStandardError().data().decode("utf-8")
                QMessageBox.critical(self, "Error", result)
            else:
                output = process.readAllStandardOutput().data().decode("utf-8")
                self.statusbar.showMessage(f"{message}", 5000)
                QMessageBox.information(
                    self,
                    "Info",
                    f"{box_message if box_message is not None else ''}\n"
                    f"{output}\n",
                )
                if done_func is not None:
                    done_func()

        args = [str(arg) for arg in args]
        qInfo(f"CLI: {app} {' '.join(args)}\n")
        process.finished.connect(process_finished)
        process.start(app, args)

    @pyqtSlot()
    def open_plan(self):
        app = QApplication.instance()
        fileName, _ = QFileDialog.getOpenFileName(
            self, "Open Plan", str(app.path), filter="*.plan"
        )
        if fileName:
            try:
                with open(fileName) as f:
                    PlanData(**json.loads(f.read()))
            except (json.decoder.JSONDecodeError, TypeError):
                QMessageBox.critical(self, "Error", "It is not Plan file")
            else:
                self.update_plan_info(fileName)

    def update_plan_info(self, plan_file):
        self._plan_path = plan_file
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None
        self.plan_changed.emit(plan_file)
        if not hasattr(self, "plan_place"):
            return
        self.plan = PlanSummary(plan_file, self)
        for idx in range(self.plan_place.count()):
            item = self.plan_place.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
            self.plan_place.removeItem(item)
        self.plan_place.addWidget(self.plan)
        self.plan.contract_data_changed.connect(self.contract_data_change)
        self.plan.create_sign.connect(self.click_sign_button)
        if not hasattr(self, "plan_status_place"):
            return
        for idx in range(self.plan_status_place.count()):
            item = self.plan_status_place.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
        self.plan_status = PlanStatus(self.plan, self)
        self.plan_status_place.addWidget(self.plan_status)

    def contract_data_change(self, data_file):
        app = QApplication.instance()
        self._contract_data = data_file
        if self._monitor is not None:
            self._monitor.stop()
        self._monitor = PlanMonitor(app.rpc)
        if not hasattr(self, "plan_status_place"):
            return
        for idx in range(self.plan_status_place.count()):
            item = self.plan_status_place.takeAt(0)
            widget = item.widget()
            widget.setParent(None)
            self.plan_status_place.removeItem(item)
        self.plan_status = PlanStatus(self.plan, self)
        self.plan_status_place.addWidget(self.plan_status)
        self._monitor.block_high_updated.connect(self.plan_status.change_block)
        self._monitor.contract_tx_changed.connect(
            self.plan_status.change_status
        )
        self.contract_data_changed.emit(data_file)
        self._monitor.contract_tx_changed.emit()

    def click_sign_button(self):
        app = QApplication.instance()
        fileName = self.get_filename(f"{app.suffix}signature")
        self._sign_path = fileName
        self.sign_save.emit(fileName)

    def get_filename(self, suffix):
        plan = pathlib.Path(self._plan_path)
        file_name = plan.stem
        file_path = plan.parent.absolute()
        return f"{file_path}/{file_name}.{suffix}"
