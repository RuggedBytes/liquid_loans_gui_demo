#!/usr/bin/env python3

# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from sys import exit

from common import LoanApp
from creditor import MainWindow, conf_file


class CreditorApp(LoanApp):
    suffix = "c"
    config_name = "Creditor"
    grab_msg = ", you can grab collateral"
    revoke_msg = ", you can revoke window"

    def __init__(self):
        super(CreditorApp, self).__init__(conf_file=conf_file)
        self.main = MainWindow()
        self.main.show()


if __name__ == "__main__":
    exit(CreditorApp().exec_())
