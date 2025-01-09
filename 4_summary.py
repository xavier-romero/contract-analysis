#!/usr/bin/python3
import sys
import os
import re
import config as cfg
from time import time
from downloader_helper import objects_retriever


transactions_folder = cfg.TRANSACTIONS_FOLDER
output_folder = cfg.OUTPUT_FOLDER
contracts_file = cfg.CONTRACTS_FILE
no_contracts_file = cfg.NO_CONTRACTS_CACHE
conflicts_file = cfg.CONFLICTS_FILE
reverted_file = cfg.REVERTED_FILE
changed_file = cfg.CHANGED_FILE

env = os.getenv('ENV')
summary = ""

global_start_time = time()

# get file list from folder
existing_files = sorted(os.listdir(transactions_folder))
if not existing_files:
    print("No files to process.")
    sys.exit(1)

last_file = existing_files[-1]
last_batch = re.search(r"from_batch_\d+_to_(\d+)\.json", last_file).group(1)
last_batch = int(last_batch)

total_txs = 0
for _file in existing_files:
    full_path = os.path.join(transactions_folder, _file)
    _txs = objects_retriever(full_path)
    total_txs += len(_txs)
    del _txs

summary += \
    f"Processed env {env} until batch {last_batch} " \
    f"with a total of {total_txs} txs."


contracts = objects_retriever(os.path.join(output_folder, contracts_file))
no_contracts = \
    objects_retriever(os.path.join(output_folder, no_contracts_file))

total_contracts = len(contracts)
total_no_contracts = len(no_contracts)
del contracts
del no_contracts

summary += \
    f"\n- Addresses identified as contracts: {total_contracts}" \
    f"\n- Addresses identified as NO contracts: {total_no_contracts}"

conflicts = objects_retriever(os.path.join(output_folder, conflicts_file))

summary += "\n\nMany have unsupported opcodes:"
for _i, _opcode in enumerate(cfg.UNSUPPORTED_OPCODES):
    _n_contracts = len(conflicts.get(_opcode, {}))
    _n_txs = sum(len(_txs) for _txs in conflicts.get(_opcode, {}).values())
    _opcode = cfg.UNSUPPORTED_OPCODES_NAMES[_i]
    summary += \
        f"\n\t- {_n_contracts} contracts with unsupported opcode {_opcode} " \
        f"having a total of {_n_txs} transactions."

summary += "\n\nMany have changed opcodes:"
for _i, _opcode in enumerate(cfg.CHANGED_OPCODES):
    _n_contracts = len(conflicts.get(_opcode, {}))
    _n_txs = sum(len(_txs) for _txs in conflicts.get(_opcode, {}).values())
    _opcode = cfg.CHANGED_OPCODES_NAMES[_i]
    summary += \
        f"\n\t- {_n_contracts} contracts with changed opcode {_opcode} " \
        f"having a total of {_n_txs} transactions."

summary += "\n\nTracing txs, we confirm how much have been failed due to unsupported opcodes:"  # noqa
reverted = objects_retriever(os.path.join(output_folder, reverted_file))
for _opcode, _content in reverted.items():
    _n_contracts = len(_content)
    _n_txs = sum(len(_txs) for _txs in _content.values())
    summary += \
        f"\n\t- {_n_contracts} contracts with reverted txs due to unsupported opcode {_opcode} having a total of {_n_txs} transactions"  # noqa
    # We will show the top 5 contracts with more txs reverted
    summary += f"\n\tTop contracts with more txs reverted for {_opcode}:"
    _top = sorted(
        _content.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:5]
    for _addr, _txs in _top:
        summary += \
            f"\n\t\t- Contract {_addr} with {len(_txs)} reverted txs using this opcode."  # noqa
    del _top
del reverted
summary += "\n"

summary += "\nTracing txs, we confirm how much have executed using changed opcodes:"  # noqa
changed = objects_retriever(os.path.join(output_folder, changed_file))
for _opcode, _content in changed.items():
    _n_contracts = len(_content)
    _n_txs = sum(len(_txs) for _txs in _content.values())
    summary += \
        f"\n\t- {_n_contracts} contracts with txs using changed opcode {_opcode} having a total of {_n_txs} transactions"  # noqa
    # We will show the top 5 contracts with more txs using changed opcodes
    summary += f"\n\tTop 5 contracts with more txs using opcode {_opcode}:"
    _top = sorted(
        _content.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:5]
    for _addr, _txs in _top:
        summary += \
            f"\n\t\t- Contract {_addr} with {len(_txs)} txs using this opcode."  # noqa
    del _top
del changed
summary += "\n"

print()
print("*** SUMMARY ***")
print(summary)

global_total_time = time() - global_start_time
print()
print(f"Total report time: {global_total_time:.2f} seconds")
