#!/bin/bash

# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

shopt -s expand_aliases
DATADIR1=/root/elementsdir1
DATADIR2=/root/elementsdir2
alias e1-dae="/root/elements/src/elementsd -datadir=$DATADIR1"
alias e1-cli="/root/elements/src/elements-cli -datadir=$DATADIR1"
alias e2-dae="/root/elements/src/elementsd -datadir=$DATADIR2"
alias e2-cli="/root/elements/src/elements-cli -datadir=$DATADIR2"
alias e1-qt="/root/elements/src/qt/elements-qt -datadir=$DATADIR1"
alias e2-qt="/root/elements/src/qt/elements-qt -datadir=$DATADIR2"
# start the first elemetsd daemon
e1-dae
# start the second elemetsd daemon
e2-dae
# wait for starting
sleep 5
# split all money for two parts
ADDRGEN2="AzppBXXLMGg5iNMpLtFxv1xcxj6xEqBBb3j9nCLkYwQwF4wxHCxPUdAZHRknxvtcSgwcnBwECStHuAhB"
ADDRGEN1="AzppBXXLMGg5iNMpLtFxv1xcxj6xEqBBb3j9nCLkYwQwF4wxHCxPUdAZHRknxvtcSgwcnBwECStHuAhB"
e1-cli sendtoaddress $(e1-cli getnewaddress) 21000000 "" "" true
e1-cli generatetoaddress 101 $ADDRGEN1
e1-cli sendtoaddress $(e2-cli getnewaddress) 10500000 "" "" false
e1-cli generatetoaddress 101 $ADDRGEN1

e1-cli getwalletinfo
e2-cli getwalletinfo

/root/split.py

exec /root/issues.py elements "$DATADIR1/elements.conf" "$DATADIR2/elements.conf" > /root/demo_assets.txt
