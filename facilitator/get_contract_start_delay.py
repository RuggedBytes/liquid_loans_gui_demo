# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from PyQt5.QtWidgets import QDialog

from common import LoaderUI


class GetContractStartDelay(QDialog, LoaderUI):
    def __init__(self):
        super(GetContractStartDelay, self).__init__()
        self.setupUi(__file__)
