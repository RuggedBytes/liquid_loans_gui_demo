#!/usr/bin/env python3

# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from sys import exit

from common import LoanApp
from facilitator import MainWindow, conf_file


class FacilitatorApp(LoanApp):
    suffix = ""
    config_name = "Facilitator"

    def __init__(self):
        super(FacilitatorApp, self).__init__(conf_file=conf_file)
        self.main = MainWindow()
        self.main.show()


if __name__ == "__main__":
    exit(FacilitatorApp().exec_())
