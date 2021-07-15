#!/usr/bin/env python3

# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from sys import exit

from common import LoanApp
from debtor import MainWindow, conf_file


class DebtorApp(LoanApp):
    suffix = "d"
    config_name = "Debtor"

    def __init__(self):
        super(DebtorApp, self).__init__(conf_file=conf_file)
        self.main = MainWindow()
        self.main.show()


if __name__ == "__main__":
    exit(DebtorApp().exec_())
