# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtWidgets import (
    QDialog, QLayout, QHBoxLayout, QLabel, QDoubleSpinBox
)

from common import LoaderUI, clear_layout
from PyQt5 import QtCore


class CreatePlanDialog(QDialog, LoaderUI):
    def __init__(self):
        super(CreatePlanDialog, self).__init__()
        self.setupUi(__file__)
        self.num_skips.valueChanged.connect(self.update_lates)
        self._value = self.num_skips.value()

    def update_lates(self, value):
        if hasattr(self, '_value'):
            if value > self._value:
                self.add_fields(value - self._value)
            elif value < self._value:
                self.remove_fields(self._value - value)
        self._value = int(value)

    def remove_fields(self, num_to_remove):
        for _ in range(num_to_remove):
            item = self.late_layout.takeAt(
                self.late_layout.count()-1
            )
            if item is None:
                return
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            elif isinstance(item, QLayout):
                clear_layout(item)
            self.late_layout.removeItem(item)

    def add_fields(self, num_to_add):
        for _ in range(num_to_add):
            field_layout = self.late_layout.itemAt(
                self.late_layout.count()-1
            )
            if field_layout is None:
                value = 5.5
            else:
                value = field_layout.itemAt(1).widget().value()

            _translate = QtCore.QCoreApplication.translate
            layout = QHBoxLayout()
            LateRepaymentlabel = QLabel(self)
            LateRepaymentlabel.setText(_translate(
                "CreatePlanDialog",
                f"Late Repayment Rate {self.late_layout.count() + 1}"))
            layout.addWidget(LateRepaymentlabel)
            LateRatedoubleSpinBox = QDoubleSpinBox(self)
            LateRatedoubleSpinBox.setProperty("value", value)
            layout.addWidget(LateRatedoubleSpinBox)
            self.late_layout.addLayout(layout)
