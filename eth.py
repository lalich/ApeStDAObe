from web3 import Web3, AsyncWeb3
from moralis import evm_api
import json

## test connection to Eth and get last block data
infura_url = "https://mainnet.infura.io/v3/6701ea4f70654045aab51734e07e1caa"
web3 = Web3(Web3.HTTPProvider(infura_url))

print(web3.is_connected())


api_key = "QercoCAZywTkeKevoZC08gBJjPLRd7xN6aV88RZ5asiMv9r3tk762Hrj7pMEw6zE"
block_num = str(web3.eth.block_number)
params = {
    "block_number_or_hash": block_num,
    "chain": "eth", 
    "include": "internal_transactions", 
}

result = evm_api.block.get_block(
    api_key=api_key,
    params=params,
)

print(json.dumps(result, indent=4), block_num)