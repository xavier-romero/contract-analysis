#!/usr/bin/python3
import os
import config as cfg
from time import time
from downloader_helper import (
    objects_retriever, _dumper, contract_fetcher, get_contract_code)


transactions_folder = cfg.TRANSACTIONS_FOLDER
output_folder = cfg.OUTPUT_FOLDER
contracts_file = cfg.CONTRACTS_FILE
no_contracts_file = cfg.NO_CONTRACTS_CACHE

try:
    contracts = objects_retriever(os.path.join(output_folder, contracts_file))
    no_contracts = \
        objects_retriever(os.path.join(output_folder, no_contracts_file))
except FileNotFoundError:
    contracts = {}
    no_contracts = {}

#
#
# TODO: GET CODE FOR CONTRACTS IN BATCHES !!!
#
#

global_start_time = time()

# get file list from folder
for _file in sorted(os.listdir(transactions_folder)):
    start_time = time()
    full_path = os.path.join(transactions_folder, _file)
    print(f"Processing file: {full_path}")
    _txs = objects_retriever(full_path)

    contracts_hits = 0
    no_contracts_hits = 0
    contract_count = 0
    no_contract_count = 0
    rpc_calls = 0

    for _tx in _txs:
        _from = _tx.get('from').lower()
        # The from of a external tx can never be a contract, so we cache taht
        no_contracts[_from] = True
        no_contract_count += 1

        # tx failed
        # if _tx.get('status') == '0x0':
        #     continue

        # We catch direct contract creation here
        _contract = _tx.get('receipt').get('contractAddress')
        if _contract:
            _contract = _contract.lower()
            contracts[_contract] = {
                'create_tx_hash': _tx.get('hash'),
                'create_block': _tx.get('blockNumber'),
                'creator': _tx.get('from'),
                'input': _tx.get('input'),
                'tx_count': 0,
                'txs': [],
                'failed_txs': [],
            }
            contract_count += 1

        else:
            _to = _tx.get('to').lower()
            _input = _tx.get('input')
            _success = _tx.get('receipt').get('status') == '0x1'

            # Regular execution on contract
            if contracts.get(_to):
                contracts[_to]['tx_count'] = contracts[_to]['tx_count'] + 1
                if _success:
                    contracts[_to]['txs'].append(_tx.get('hash'))
                else:
                    contracts[_to]['failed_txs'].append(_tx.get('hash'))
                contracts_hits += 1
                continue

            # Already checked and not a contract
            if no_contracts.get(_to):
                no_contracts_hits += 1
                continue

            # Complex cases, lets retrieve code to be sure
            _code = get_contract_code(_to)
            rpc_calls += 1
            if not _code or _code == '0x':
                no_contracts[_to] = True
                no_contract_count += 1
            else:
                contracts[_to] = {
                    'create_block': 'UNKNOWN',
                    'tx_count': 1,
                    'runtime': _code,
                }
                if _success:
                    contracts[_to]['txs'] = [_tx.get('hash')]
                    contracts[_to]['failed_txs'] = []
                else:
                    contracts[_to]['txs'] = []
                    contracts[_to]['failed_txs'] = [_tx.get('hash')]
                contract_count += 1
            continue

    total_time = time() - start_time
    print(
        f"Processed file: {full_path}, "
        f"new_contracts: {contract_count}, "
        f"new_no_contracts: {no_contract_count}, "
        f"contracts_hits: {contracts_hits}, "
        f"no_contracts_hits: {no_contracts_hits}, "
        f"total_contract_count: {len(contracts)}, "
        f"| RPC calls: {rpc_calls} "
        f"| Time: {total_time:.2f} seconds"
    )
    # Saving after each file, just in case we get killed in between
    _dumper(contracts, output_folder, contracts_file)
    _dumper(no_contracts, output_folder, no_contracts_file)


# Add runtime to these addresses than doesnt have it
_addresses = [k for k, v in contracts.items() if not v.get('runtime')]
_contracts2 = contract_fetcher(_addresses)
for _contract2 in _contracts2:
    contracts[_contract2.get('address')]['runtime'] = \
        _contract2.get('result')

# Saving contracts after runtime update
_dumper(contracts, output_folder, contracts_file)

global_total_time = time() - global_start_time
print(f"Total time: {global_total_time:.2f} seconds")

# Output is just 1 json file with all contracts detected with this format
# {
#     "contract_address": {
#         "create_tx_hash": "0xHASH",
#         "create_block": "0xAA",
#         "creator": "0xHASH",
#         "input": "0x",
#         "runtime": "0x",
#         "tx_count": n,
#         "txs": [
#             "0xHASH1",
#             "0xHASH2",
#             ...
#         ],
#         "failed_txs": [
#             "0xHASH1",
#             ...
#         ]
#     }
# }
# 50m to process all txs from zkevm mainnet
