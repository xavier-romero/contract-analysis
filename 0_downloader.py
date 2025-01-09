#!/usr/bin/python3
import os
import re
from time import time
from utils import chunks
from downloader_helper import (
    batch_fetcher, _dumper, get_last_verified_batch_number)
import config as cfg

output_folder = cfg.TRANSACTIONS_FOLDER

# check if the folder exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
existing_files = sorted(os.listdir(output_folder))
if existing_files:
    last_file = existing_files[-1]
    first_batch = re.search(r"from_batch_(\d+)_to", last_file).group(1)
    first_batch = int(first_batch)
    os.remove(os.path.join(output_folder, last_file))
else:
    first_batch = 0

last_batch = get_last_verified_batch_number()

cfg.linfo(f"Getting batches from {first_batch} to {last_batch}.")
global_start_time = time()
batches_ids = list(range(first_batch, last_batch+1))

for chunk_batches_ids in chunks(
    batches_ids, cfg.DOWNLOAD_BATCHES_PER_ITER
):
    start = chunk_batches_ids[0]
    end = chunk_batches_ids[-1]
    cfg.linfo(f"Downloading batches from {start} to {end}.")
    start_time = time()
    txs = batch_fetcher(chunk_batches_ids)
    _dumper(txs, output_folder, f"from_batch_{start:010}_to_{end:010}.json")
    total_time = time() - start_time
    print(
        f"Downloaded {end-start+1} batches with {len(txs)} txs "
        f"in {total_time:.2f} seconds | txs/s: {len(txs)/total_time:.0f}"
    )

global_total_time = time() - global_start_time
print(f"Total time: {global_total_time:.2f} seconds")

# Files generated on the output folder containing all transactions.
# Each output file is just an array of txs
# [
#     {
#         // all tx properties here
#         k: v
#         receipt: {
#             // all receipt properties here
#             k: v
#         }
#     },
#     {
#         ...
#     }
#     ...
# ]
# 5h to get all txs from zkevm mainnet
