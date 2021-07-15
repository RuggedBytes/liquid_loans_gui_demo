#!/usr/bin/env python3

# Copyright (c) 2020-2021 Rugged Bytes IT-Services GmbH
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys

import elementstx  # noqa
from bitcointx import select_chain_params
from bitcointx.core import satoshi_to_coins
from bitcointx.core.key import CKey
from bitcointx.rpc import RPCCaller
from bitcointx.wallet import P2WPKHCoinAddress
from elementstx.wallet import CCoinConfidentialAddress


ASSET_NAMES = (
    "USD",
    "EUR",
    "JPY",
    "CAD",
    "GOLD",
    "SILVER",
    "PLATINUM",
)


def get_random_addr():
    blinding_key = CKey.from_secret_bytes(os.urandom(32))
    key = CKey.from_secret_bytes(os.urandom(32))
    addr = CCoinConfidentialAddress.from_unconfidential(
        P2WPKHCoinAddress.from_pubkey(key.pub), blinding_key.pub
    )
    return addr


select_chain_params(sys.argv[1])

rpc1 = RPCCaller(conf_file=sys.argv[2])
rpc2 = RPCCaller(conf_file=sys.argv[3])

for asset_name in ASSET_NAMES:
    issued = rpc1.issueasset(satoshi_to_coins(1_000_000), 0)

    print(f"-assetdir={issued['asset']}:{asset_name} ", end='')

    rpc1.sendtoaddress(
        rpc2.getnewaddress(),
        satoshi_to_coins(500_000),
        "",
        "",
        False,
        False,
        1,
        "CONSERVATIVE",
        issued["asset"],
    )
    rpc1.generatetoaddress(1, str(get_random_addr()))

print()
