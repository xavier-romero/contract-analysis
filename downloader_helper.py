import requests
import json
import math
import time
from threading import Thread
from pathlib import Path
from utils import chunks
import config as cfg


def get_last_batch_number(ep):
    last_batch_hex = geth_request(ep=ep, method='zkevm_batchNumber')
    return int(last_batch_hex, base=16)


def get_last_verified_batch_number():
    last_batch_hex = geth_request(
        ep=cfg.EP, method='zkevm_verifiedBatchNumber')
    return int(last_batch_hex, base=16)


def trace_transaction(tx_hash):
    params = [
        tx_hash,
        {
            "disableStorage": True,
            "disableStack": True,
            "disableMemory": True,
            "disableReturnData": True,
        }
    ]
    return geth_request(
        ep=cfg.EP_DEBUG, method='debug_traceTransaction', params=params
    )


def trace_fetcher(tx_hashes):
    class Fetcher(Thread):
        def __init__(self, ep, tx_hashes):
            Thread.__init__(self)
            self.ep = ep
            self.tx_hashes = tx_hashes
            self.traces = []
            self.params = {
                "disableStorage": True,
                "disableStack": True,
                "disableMemory": True,
                "disableReturnData": True,
            }

        def run(self):
            for chunk_tx_hashes in chunks(
                self.tx_hashes, cfg.TRACES_QUERIES_PER_REQUEST
            ):
                _traces = geth_request_multi(
                    ep=self.ep,
                    requests=[
                        {
                            'method': 'debug_traceTransaction',
                            'params': [tx_hash, self.params],
                            'id': tx_hash
                        }
                        for tx_hash in chunk_tx_hashes
                    ],
                    map_from_id='tx_hash'
                )
                if _traces and isinstance(_traces, list):
                    if len(_traces) != len(chunk_tx_hashes):
                        cfg.lerror(
                            f"Fetcher.run ep={self.ep}, "
                            f"sent {len(chunk_tx_hashes)}, "
                            f"got {len(_traces)} traces"
                        )
                    self.traces.extend(_traces)
                else:
                    cfg.lerror(
                        f"Fetcher.run ep={self.ep} "
                        f"tx_hashes={chunk_tx_hashes} traces={_traces}"
                    )

    ep = cfg.EP_DEBUG
    threads = []
    chunk_size = int(
        math.ceil(len(tx_hashes)/cfg.THREAD_COUNT)
    )

    for chunk_tx_hashes in chunks(tx_hashes, chunk_size):
        t = Fetcher(ep, chunk_tx_hashes)
        t.start()
        threads.append(t)

    traces = []
    for t in threads:
        t.join()
        traces.extend(t.traces)

    return traces


def get_last_block_number(ep):
    last_block_hex = geth_request(ep=ep, method='eth_blockNumber')
    return int(last_block_hex, base=16)


def endpoint_request(
    method='GET', endpoint=None, path='/', url=None, params=None, body=None,
    data=None, headers=None, auth=None, max_attempts=10, trhottle_cooldown=10,
    error_handler={}, debug=False
):
    if not path.startswith('/'):
        path = f'/{path}'

    # IF URL is provided (it must be full URL) it's used disregarding
    #  whatever is the value for endpoint and path
    if url:
        kwargs = {'method': method, 'url': url}
    else:
        kwargs = {'method': method, 'url': f'{endpoint}{path}'}

    if params:
        kwargs['params'] = params
    if body:
        kwargs['data'] = json.dumps(body)
    elif data:
        kwargs['data'] = data
    if headers:
        kwargs['headers'] = headers
    if auth:
        kwargs['auth'] = auth

    if debug:
        cfg.ldebug(f'kwargs:{kwargs}')

    for attempt in range(1, max_attempts+1):
        try:
            req = requests.request(**kwargs)
            try:
                content = req.json()
            except ValueError:
                content = req.reason
            rcode = req.status_code

            if rcode in error_handler:
                function = error_handler.get(rcode)
                function()
                raise requests.exceptions.HTTPError(
                    f'Handle attempt: {rcode}: {content} for url {req.url}')

            if rcode == 429:
                time.sleep(trhottle_cooldown)
                raise requests.exceptions.HTTPError(
                    f'Throttled!! {rcode}: {content} for url {req.url}')
            if rcode >= 500:
                raise requests.exceptions.HTTPError(
                    f'{rcode} Error: {content} for url {req.url}')

            return rcode, content

        except requests.exceptions.RequestException as e:
            if attempt < max_attempts:
                cfg.linfo(e)
                time.sleep(attempt*attempt)
            else:
                cfg.lerror(e)
                raise


def geth_request(ep, method, params=[], retries=3, debug=False):
    (rcode, content) = endpoint_request(
        method='POST', endpoint='Unused', url=ep,
        body={'method': method, 'params': params, 'id': 1},
        headers={'Content-Type': 'application/json'},
        debug=debug
    )
    if rcode == 200:
        if r := content.get('result'):
            return r
        elif content.get('error') and retries:
            return geth_request(ep, method, params, retries-1)
        else:
            cfg.lerror(
                f"geth_request ep={ep} method={method} params={params} "
                f"retries={retries} answer={content}")
            return None
    else:
        cfg.lerror(
            f"utils.geth_request rcode=={rcode} content={content}")
        return None


def geth_request_multi(ep, requests, retries=5, map_from_id='number'):
    (rcode, content) = endpoint_request(
        method='POST', endpoint='Unused', url=ep, body=requests,
        headers={'Content-Type': 'application/json'},
    )
    if rcode == 200:
        result = []
        for c in content:
            if r := c.get('result'):
                if isinstance(r, str):
                    r = {'result': r}
                # The id has been set to batch number when querying
                if map_from_id:
                    r[map_from_id] = c.get('id')
                result.append(r)
            elif c.get('error') and retries:
                # this error is thrown when there are no txs in the batch
                if c.get('error').get('message', '') == \
                        'method handler crashed':
                    continue
                retry_in = (10-retries)*2
                cfg.linfo(
                    f"RETRY for geth_request ep={ep} "
                    f"retries={retries} answer={c} sleep={retry_in} "
                    f"body={requests}")
                time.sleep(retry_in)
                return geth_request_multi(
                    ep, requests, retries-1, map_from_id=map_from_id)
            else:
                cfg.lerror(
                    f"geth_request ep={ep} request={requests} "
                    f"retries={retries} answer={c}")
                return None
        return result
    else:
        cfg.lerror(
            f"utils.geth_request rcode=={rcode} content={content}")
        return None


def get_contracts_filename(batches_filename):
    folder = cfg.DOWNLOAD_PATH
    Path(folder).mkdir(parents=True, exist_ok=True)

    base_name = batches_filename.split('.')[0]
    filename = \
        f"{folder}/" \
        f"direct_contracts_{base_name}.json"

    return filename


def batch_fetcher(batch_ids):
    class Fetcher(Thread):
        def __init__(self, ep, batch_ids):
            Thread.__init__(self)
            self.ep = ep
            self.batch_ids = batch_ids
            self.batches = []

        def run(self):
            for chunk_batch_ids in chunks(
                self.batch_ids, cfg.DOWNLOAD_QUERIES_PER_REQUEST
            ):
                self.batches.extend(
                    geth_request_multi(
                        ep=ep,
                        requests=[
                            {
                                'method': 'zkevm_getBatchByNumber',
                                'params': [hex(batch_number), True],
                                'id': batch_number
                            }
                            for batch_number in chunk_batch_ids
                        ]
                    )
                )
            for batch in self.batches:
                if not batch.get('transactions'):
                    batch['transactions'] = []

    ep = cfg.EP
    threads = []
    chunk_size = int(
        math.ceil(len(batch_ids)/cfg.THREAD_COUNT)
    )

    for chunk_batch_ids in chunks(batch_ids, chunk_size):
        t = Fetcher(ep, chunk_batch_ids)
        t.start()
        threads.append(t)

    transactions = []
    for t in threads:
        t.join()
        for _batch in t.batches:
            transactions.extend(_batch.get('transactions', []))

    return transactions


def get_contract_code(contract_address):
    return geth_request(
        ep=cfg.EP, method='eth_getCode', params=[contract_address, "latest"]
    )


def contract_fetcher(contract_addresses):
    class Fetcher(Thread):
        def __init__(self, ep, contract_addresses):
            Thread.__init__(self)
            self.ep = ep
            self.contract_addresses = contract_addresses
            self.codes = []

        def run(self):
            for chunk_contract_addresses in chunks(
                self.contract_addresses, cfg.DOWNLOAD_QUERIES_PER_REQUEST
            ):
                self.codes.extend(
                    geth_request_multi(
                        ep=ep,
                        requests=[
                            {
                                'method': 'eth_getCode',
                                'params': [addr, "latest"],
                                'id': addr
                            }
                            for addr in chunk_contract_addresses
                        ],
                        map_from_id='address'
                    )
                )

    ep = cfg.EP
    threads = []
    chunk_size = int(
        math.ceil(len(contract_addresses)/cfg.THREAD_COUNT)
    )

    for chunk_contract_addresses in chunks(contract_addresses, chunk_size):
        t = Fetcher(ep, chunk_contract_addresses)
        t.start()
        threads.append(t)

    codes = []
    for t in threads:
        t.join()
        codes.extend(t.codes)

    return codes


def _dumper(objects, output_folder, filename):
    class BEncoder(json.JSONEncoder):
        def default(self, o):
            return o.__dict__

    Path(output_folder).mkdir(parents=True, exist_ok=True)
    filename = f"{output_folder}/{filename}"

    cfg.linfo(f"Saving objects to {filename}")

    with open(filename, 'w') as outfile:
        json.dump(objects, outfile, indent=2, cls=BEncoder)
        cfg.ldebug(
            f"Dumped {len(objects)} to file {filename}")
        outfile.close()

    return True


def contract_dumper(contracts, from_batch_filename):
    cfg.ldebug(
        f"Saving {len(contracts)} contracts from file {from_batch_filename}")

    filename = get_contracts_filename(from_batch_filename)
    cfg.linfo(f"Saving contracts to {filename}")

    if _dumper(contracts, filename):
        return filename


def objects_retriever(filename):
    f = open(filename, 'r')

    cfg.ldebug(f"Loading file {filename}")
    objects = json.load(f)
    f.close()
    cfg.linfo(
        f"File {filename} with {len(objects)} items loaded to memory.")
    return objects
