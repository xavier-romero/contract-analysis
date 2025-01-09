# CONTRACT ANALYSIS

All steps need to be run in the repo's root folder.

## Step 0: Download transactions

```bash
ENV=cardona ./0_downloader.py
```
This will create the folder ```zkevm_cardona/transactions``` with a bunch of json files containing ALL transaction from the network until the last verified batch.

Each json file will be an array of transactions, with this format:
```
[
    {
        // all tx properties here
        k1: v1,
        k2: v2,
        receipt: {
            // all receipt properties here
            k1: v1,
            k2: v2
        }
    },
    {
        ...
    }
    ...
]
```

Timings:
- Bali: ~12 minutes
- Cardona: ~15 minutes
- Mainnet: ~5 hours

After first run, by just repeating the process it will behave incrementally, so only the last incomplete file will be regenerated until the current batch, which will be much faster.


## Step 1: Identify Contracts, get bytecode
```bash
ENV=cardona ./1_processor.py
```

This will process all previous files, extracting all contracts found. For caching/speed purposes a full list of contracts/no-contracts will be kept in memory until the end.
For Mainnet, this will require much memory so its recommended to close as much applications as possible.

The output is just 1 json file (ex: zkevm_cardona_contracts.json) with all contracts, having this format:
```
{
    "contract_address": {
        "create_tx_hash": "0xHASH",
        "create_block": "0xAA",
        "creator": "0xHASH",
        "input": "0x",
        "runtime": "0x",
        "tx_count": n,
        "txs": [
            "0xHASH1",
            "0xHASH2",
            ...
        ],
        "failed_txs": [
            "0xHASH1",
            ...
        ]
    }
}
```

Timings:
- Bali: ~45 minutes
- Cardona: ~1h 15minutes
- Mainnet: 

The process keeps a file with the contracts and no-contracts, so repeating the process will be much faster as there will be no need to query RPC again.

## Step 2: Process contracts, identify opcodes & potential conflicts
```bash
ENV=cardona ./2_analyzer.py
```
Process runtime for each contract to identify potential conflicts due to unsupported/changed bytecodes.
As output writes a file with info about opcodes (contracts for each opcode, etc), and a "conflicts" file with all contracts that could potentially lead to different result execution.

Opcodes file:
```
{
    "opcode": {
        "contract_address": [<opcode_count_in_contract>, <contract_call_count>],
        ...
    },
    ...
}
```

Conflicts file:
```
{
    "opcode": {
        "contract_address": [
            "0xHASH1",
            "0xHASH2",
            ...
        ],
        ...
    },
    ...
}
```

Timings:
- Bali: ~3 minutes
- Cardona: ~30 seconds
- Mainnet: 


## Step 3: Trace conflicts and confirm potential issues
```bash
ENV=cardona ./3_evaluator.py
```
Process conflicts and trace transactions to confirm if the unsupported/changed opcode is being used or not.
As output, it generated two files:
- ```reverted.json``` with contracts and its transactions that have been reverted due to unsupported opcode
- ```changed.json``` with contracts and its transactions that have been executed using a changed opcode 

These files are meant to be of the whole process that are meant

Timings:
- Bali: ~1 hour
- Cardona: ~3 hours
- Mainnet: 

### Manual trace
For any manual validation, the trace can be done this way:
```bash
TX=0x383009c7043733c039f29ec4568626d42c23ed3e21fa7d3d1348c1a41b52a0d1
RPC=https://rpc-debug.cardona.zkevm-rpc.com

PARAMS='["'$TX'",{"disableStorage":true,"disableStack":true,"disableMemory":true,"disableReturnData":true}]'
curl -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","id":1,"method":"debug_traceTransaction","params":'$PARAMS'}' $RPC
```

## Step 4: Summary
```bash
ENV=cardona ./4_summary.py
```
This steps loads files from previous steps and produces a summary with understandable information.
Timings:
- Bali: ~1 minute
- Cardona: ~1 minute
- Mainnet: 

Example output for Bali:
```bash
Processed env bali until batch 83379 with a total of 1944936 txs.
- Addresses identified as contracts: 288369
- Addresses identified as NO contracts: 32196

Many have unsupported opcodes:
	- 48 contracts with unsupported opcode BLOBHASH having a total of 269 transactions.
	- 5 contracts with unsupported opcode BLOBBASEFEE having a total of 152 transactions.
	- 25 contracts with unsupported opcode TLOAD having a total of 177 transactions.
	- 61 contracts with unsupported opcode TSTORE having a total of 315 transactions.
	- 28 contracts with unsupported opcode MCOPY having a total of 368 transactions.

Many have changed opcodes:
	- 465 contracts with changed opcode SELFDESTRUCT having a total of 1014 transactions.
	- 101 contracts with changed opcode EXTCODEHASH having a total of 687 transactions.
	- 445 contracts with changed opcode BLOCKHASH having a total of 36368 transactions.
	- 1518 contracts with changed opcode DIFFICULTY having a total of 773707 transactions.

Tracing txs, we confirm how much have been failed due to unsupported opcodes:
	- 40 contracts with reverted txs due to unsupported opcode BLOBHASH having a total of 46 transactions
	Top contracts with more txs reverted for BLOBHASH:
		- Contract 0xc06d771d63246d241f7f4755e5d2863bfeb7543c with 4 reverted txs using this opcode.
		- Contract 0x1f86fdd143b8005cef8aa73fac6d7cdcbc6f6808 with 2 reverted txs using this opcode.
		- Contract 0x1810d41f061e6334786d7e04607d94e969734cd4 with 2 reverted txs using this opcode.
		- Contract 0x1b45d3a190b1fb5094d10b09db10dcf22bf4df5b with 2 reverted txs using this opcode.
		- Contract 0xcf6f26784c9c0c0b15bc96d0d0057d6de9d56a07 with 1 reverted txs using this opcode.
	- 1 contracts with reverted txs due to unsupported opcode BLOBBASEFEE having a total of 4 transactions
	Top contracts with more txs reverted for BLOBBASEFEE:
		- Contract 0x031d47e0a3303c00ff0b5f2a7016053534e35ab9 with 4 reverted txs using this opcode.
	- 8 contracts with reverted txs due to unsupported opcode TLOAD having a total of 15 transactions
	Top contracts with more txs reverted for TLOAD:
		- Contract 0x7808710c268d126772ea1924bdb8cd454e5e6e04 with 5 reverted txs using this opcode.
		- Contract 0x6ac5d8e53c93f151697a49a2757e06b196a1a5a3 with 4 reverted txs using this opcode.
		- Contract 0xff9efb70565bd8895857fab0b67fd3c7fec0340b with 1 reverted txs using this opcode.
		- Contract 0x60b2fec641c08021e8823fabb9732e85e1548a8a with 1 reverted txs using this opcode.
		- Contract 0x6a400e97792cb7f0e0bf4a3cdc851e6618ef94af with 1 reverted txs using this opcode.
	- 29 contracts with reverted txs due to unsupported opcode TSTORE having a total of 70 transactions
	Top contracts with more txs reverted for TSTORE:
		- Contract 0x17c331d0c2634415d4e2f1f7d7273bd5db9392f9 with 4 reverted txs using this opcode.
		- Contract 0x6385a55b0c8ac6a26e6d7dd5cd0b82ec7a169671 with 4 reverted txs using this opcode.
		- Contract 0xe2f874d485c395c1f6ebef4e44afed67e940bc51 with 4 reverted txs using this opcode.
		- Contract 0xd10df2cfa98e631114036734814eba032754f4d0 with 4 reverted txs using this opcode.
		- Contract 0xf578a8b04e8a8426ef56a22dd7120374ba96a8a3 with 4 reverted txs using this opcode.
	- 20 contracts with reverted txs due to unsupported opcode MCOPY having a total of 141 transactions
	Top contracts with more txs reverted for MCOPY:
		- Contract 0x01eba71a9922a9da86a2e66bfc9c99206c1d3746 with 64 reverted txs using this opcode.
		- Contract 0x75a74dff88287994d201e5d2479b9b11d663ff1e with 22 reverted txs using this opcode.
		- Contract 0x31921234771b67030a5f2f1f4933b23d5893b01a with 20 reverted txs using this opcode.
		- Contract 0xcf249cfbb1443a54ad8628d578ec3def20c1080b with 6 reverted txs using this opcode.
		- Contract 0x6700117554b856ffce4fc1680395a52e9479cdb1 with 5 reverted txs using this opcode.

Tracing txs, we confirm how much have executed using changed opcodes:
	- 335 contracts with txs using changed opcode SELFDESTRUCT having a total of 33860 transactions
	Top 5 contracts with more txs using opcode SELFDESTRUCT:
		- Contract 0x1e8422b74ead154312b96785602675442755b373 with 32556 txs using this opcode.
		- Contract 0xa1ae8aa5edd487602b98b3e076e5f19443337519 with 352 txs using this opcode.
		- Contract 0x2c3fca7be75b76ebb20840ab6127e674bc19be74 with 326 txs using this opcode.
		- Contract 0x410c0f87c55c294404fade5c1adff7db8e64f0b8 with 54 txs using this opcode.
		- Contract 0x88e88be075f0b48c51b1d4be7d7dfc55530fafd0 with 52 txs using this opcode.
	- 88 contracts with txs using changed opcode EXTCODEHASH having a total of 2848 transactions
	Top 5 contracts with more txs using opcode EXTCODEHASH:
		- Contract 0xfbe07a394847c26b1d998b6e44ee78a9c8191f13 with 1344 txs using this opcode.
		- Contract 0x1e8422b74ead154312b96785602675442755b373 with 1220 txs using this opcode.
		- Contract 0xc29bd29dacd9561c43e9bc8e457e358d23520ced with 11 txs using this opcode.
		- Contract 0xac4fa6039b9922f89194eac0ad15298cd9e7eec0 with 11 txs using this opcode.
		- Contract 0xe9fd0810e5704acdd036719af3712d20c1d20379 with 11 txs using this opcode.
	- 399 contracts with txs using changed opcode BLOCKHASH having a total of 36771 transactions
	Top 5 contracts with more txs using opcode BLOCKHASH:
		- Contract 0xb331801a46cb90827758329ef099abbc33fb1d48 with 2193 txs using this opcode.
		- Contract 0x71af3ec27cb29ebb3e41f66bfef2b196501569f7 with 2161 txs using this opcode.
		- Contract 0x1e8422b74ead154312b96785602675442755b373 with 2052 txs using this opcode.
		- Contract 0x3c17b7af34a9c783fd57fe058dbc20edbaf92af6 with 777 txs using this opcode.
		- Contract 0xfa35b8431cbf6fd31f4e9b44783d0fdce57afe4b with 769 txs using this opcode.
	- 228 contracts with txs using changed opcode DIFFICULTY having a total of 19421 transactions
	Top 5 contracts with more txs using opcode DIFFICULTY:
		- Contract 0x1e8422b74ead154312b96785602675442755b373 with 13056 txs using this opcode.
		- Contract 0xa1ae8aa5edd487602b98b3e076e5f19443337519 with 2571 txs using this opcode.
		- Contract 0x2c3fca7be75b76ebb20840ab6127e674bc19be74 with 2391 txs using this opcode.
		- Contract 0x410c0f87c55c294404fade5c1adff7db8e64f0b8 with 396 txs using this opcode.
		- Contract 0x88e88be075f0b48c51b1d4be7d7dfc55530fafd0 with 380 txs using this opcode.

```