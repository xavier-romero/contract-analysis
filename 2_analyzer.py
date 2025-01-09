#!/usr/bin/python3
import os
import config as cfg
from time import time
from downloader_helper import objects_retriever, _dumper
from config import UNSUPPORTED_OPCODES, CHANGED_OPCODES
import matplotlib.pyplot as plt


output_folder = cfg.OUTPUT_FOLDER
contracts_file = cfg.CONTRACTS_FILE
opcodes_file = cfg.OPCODES_FILE
conflicts_file = cfg.CONFLICTS_FILE

global_start_time = time()


def check_runtime(address, runtime):
    assert runtime, f"Contract {address} has no runtime!"
    assert runtime.startswith('0x'), \
        f"Contract for {address} has invalid runtime!"
    assert (len(runtime) % 2 == 0), \
        f"Contract for {address} has invalid length!"

    runtime = runtime[2:]
    bytes_left = len(runtime) // 2
    pc = 0
    opcodes = {}

    while bytes_left > 0:
        opcode = runtime[pc*2:pc*2+2]
        opcodes[opcode] = opcodes.get(opcode, 0) + 1
        pc += 1
        bytes_left -= 1

        is_push = int(opcode, 16) >= 0x60 and int(opcode, 16) <= 0x7f
        if is_push:
            push_bytes = int(opcode, 16) - 0x5f
            if push_bytes > bytes_left:
                # print(f"Push opcode {opcode} has not enough bytes left!")
                break
            pc += push_bytes
            bytes_left -= push_bytes

    return opcodes


contracts = objects_retriever(os.path.join(output_folder, contracts_file))
contract_call_distr = {}
opcodes_map = {}
opcodes_totals = {}

_modified = False


print(
    f"Contract count: {len(contracts)}",
    "Total transaction count: ",
    sum(len(v.get('txs', [])) for v in contracts.values()),
    "Total failed transaction count: ",
    sum(len(v.get('failed_txs', [])) for v in contracts.values())
)

for address, info in contracts.items():
    _call_count = info.get('tx_count', 0)
    contract_call_distr[_call_count] = \
        contract_call_distr.get(_call_count, 0) + 1

    if info.get('opcodes') is None:
        opcode_map = check_runtime(address, info.get('runtime'))
        contracts[address]['opcodes'] = opcode_map
        _modified = True

    # update global opcodes counters
    for opcode, count in contracts[address]['opcodes'].items():
        if opcode in opcodes_map:
            opcodes_totals[opcode] = opcodes_totals.get(opcode, 0) + count
            opcodes_map[opcode][address] = [count, _call_count]
        else:
            opcodes_totals[opcode] = count
            opcodes_map[opcode] = {address: [count, _call_count]}

if _modified:
    print("Saving modified contracts (added opcodes).")
    _dumper(contracts, output_folder, contracts_file)

# print(
#     "Call distribution:",
#     json.dumps(
#         dict(sorted(contract_call_distr.items(), reverse=True)),
#         indent=4
#     )
# )
opcodes_map['totals'] = opcodes_totals
_dumper(opcodes_map, output_folder, opcodes_file)

conflicts = {}
# Failed txs on contracts with unsupported opcodes,
# as they could have failed because the unsupported opcode
for _opcode in UNSUPPORTED_OPCODES:
    conflicts[_opcode] = {}
    for _addr in opcodes_map[_opcode]:
        if opcodes_map[_opcode][_addr][0] > 0:
            _failed_txs = contracts[_addr].get('failed_txs', [])
            if _failed_txs:
                conflicts[_opcode][_addr] = _failed_txs

# Successful txs on contracts with changed opcodes,
# as they could behave differently now
for _opcode in CHANGED_OPCODES:
    conflicts[_opcode] = {}
    for _addr in opcodes_map[_opcode]:
        if opcodes_map[_opcode][_addr][0] > 0:
            _successful_txs = contracts[_addr].get('txs', [])
            if _successful_txs:
                conflicts[_opcode][_addr] = _successful_txs

del contracts
del opcodes_map

# Print conflicts summary
for _opcode in conflicts:
    print(f"Opcode {_opcode} conflicts:")
    # total number of txs and addresses
    print(f"\tTotal txs: {sum(len(v) for v in conflicts[_opcode].values())}")
    print(f"\tTotal contracts: {len(conflicts[_opcode])}")
    print()

_dumper(conflicts, output_folder, conflicts_file)
del conflicts

if False:
    # Convert string keys to numbers (integers or floats)
    x = [int(k) for k in contract_call_distr.keys()]
    y = list(contract_call_distr.values())

    # Create the plot
    plt.figure(figsize=(8, 6))
    # plt.plot(x, y, marker='o', linestyle='-', color='b', label='Line')
    plt.scatter(x, y, color='b', label='Points')
    plt.title('Contract call distribution')
    plt.xlabel('tx count')
    plt.ylabel('number of contracts')
    plt.legend()
    plt.grid()

    # Show the plot
    plt.show()

del contract_call_distr

global_total_time = time() - global_start_time
print(f"Total time: {global_total_time:.2f} seconds")


# Opcodes json file format:
# {
#     "opcode": {
#         "total": n,
#         "contract_address": [opcode_count, tx_count],
#         ...
#     },
# }
# Conflicts json file format:
# {
#     "opcode": {
#         "contract_address": ["0xHASH1", "0xHASH2", ...],
#         ...
#     },
#     ...
# }
