#!/usr/bin/python3
import os
import config as cfg
from time import time
from utils import chunks
from downloader_helper import (
    objects_retriever, trace_fetcher, _dumper)

output_folder = cfg.OUTPUT_FOLDER
conflicts_file = cfg.CONFLICTS_FILE
conflicts = objects_retriever(os.path.join(output_folder, conflicts_file))
reverted_file = cfg.REVERTED_FILE
changed_file = cfg.CHANGED_FILE
trace_cache_file = cfg.TRACE_CACHE_FILE

global_start_time = time()

DEBUGS_PER_CHUNK = 500


def find_issues_for_opcodes(opcodes_names, opcodes):
    try:
        trace_cache = \
            objects_retriever(os.path.join(output_folder, trace_cache_file))
    except FileNotFoundError:
        trace_cache = {}
    finally:
        something_to_save = False

    issues_found = {
        _opcode: {} for _opcode in opcodes_names
    }
    for _opcode in opcodes:
        for _addr, _txs in conflicts.get(_opcode, {}).items():
            _n_txs = len(_txs)
            is_ok = True
            _txs_to_trace = [x for x in _txs if x not in trace_cache]
            print(
                f"Contract {_addr} | opcode {_opcode} | txs: {_n_txs} "
                f"(to trace: {len(_txs_to_trace)})...", end=' '
            )

            _i = 0
            # Get traces for not cached txs
            for _chunk_traces in chunks(_txs_to_trace, DEBUGS_PER_CHUNK):
                _i += len(_chunk_traces)
                if _n_txs > DEBUGS_PER_CHUNK:
                    print(f"{_i} ...", end=' ', flush=True)
                _traces = trace_fetcher(_chunk_traces)
                if _traces:
                    for _trace in _traces:
                        _steps = _trace.get('structLogs', [])
                        _opcodes = list(set([x.get('op') for x in _steps]))
                        _tx_hash = _trace.get('tx_hash')
                        trace_cache[_tx_hash] = _opcodes
                    something_to_save = True
                    del _traces

            for _tx in _txs:
                _opcodes = trace_cache.get(_tx)
                _opcodes_found = \
                    [x for x in _opcodes if x in opcodes_names]
                del _opcodes
                if _opcodes_found:
                    if is_ok:
                        print("KO")
                        is_ok = False
                    for _opcode_found in _opcodes_found:
                        if _addr in issues_found[_opcode_found]:
                            issues_found[_opcode_found][_addr].append(_tx)
                        else:
                            issues_found[_opcode_found][_addr] = [_tx]
                    print(
                        f"\tFound issues on opcode for contract {_addr}, "
                        f"tx {_tx} | opcodes: {_opcodes_found}"
                    )
                del _opcodes_found
            if is_ok:
                print("OK")

        # Saving after each opcode, just in case we get killed in between
        if something_to_save:
            _dumper(trace_cache, output_folder, trace_cache_file)
            something_to_save = False

    del trace_cache
    return issues_found


# ADD TX COUNT FOR EACH CONTRACT
# ADD DATES OF TXS?

reverted_that_would_work_with_op = \
    find_issues_for_opcodes(
        cfg.UNSUPPORTED_OPCODES_NAMES, cfg.UNSUPPORTED_OPCODES)
_dumper(reverted_that_would_work_with_op, output_folder, reverted_file)

success_that_would_behave_different = \
    find_issues_for_opcodes(cfg.CHANGED_OPCODES_NAMES, cfg.CHANGED_OPCODES)
_dumper(success_that_would_behave_different, output_folder, changed_file)

global_total_time = time() - global_start_time
print(f"Total time: {global_total_time:.2f} seconds")
