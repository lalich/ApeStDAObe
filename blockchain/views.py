from django.shortcuts import render
import datetime
import hashlib
import json
from uuid import uuid4
import socket
from urllib.parse import urlparse
from django.http import JsonResponse, HttpResponse, HttpRequest, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import requests
from web3 import Web3

## Transaction on the ganache test chain
ganache_url = "HTTP://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))
act1 = web3.eth.account.from_key("0x60e63c2f38e832b18b69e260ca9faeca1523d1fcb77c9f9a672d6a9e0b572812")
test_address = "0xef4f179C78cfC13aA83e0a15e88Ea9b2536F805a"

transaction = {
    'from': act1.address,
    'to': test_address,
    'value': 1000000000,
    'nonce': web3.eth.get_transaction_count(act1.address),
    'gas': 250000,
    'gasPrice': web3.to_wei(8,'gwei'),
}
signed = web3.eth.account.sign_transaction(transaction, "0x60e63c2f38e832b18b69e260ca9faeca1523d1fcb77c9f9a672d6a9e0b572812")

tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
tx = web3.eth.get_transaction(tx_hash)
assert tx['from'] == act1.address


def home(request):
        return render(request, 'blockchain/home.html')

class Blockchain:
    def __init__(self):
        self.chain = []
        self.transactions = []
        self.create_block(nonce = 1, previous_hash = '0')
        self.nodes = set()

    def create_block(self, nonce, previous_hash):
        block = {
                'index': len(self.chain) + 1,
                'timestamp': str(datetime.datetime.now()),
                'nonce': nonce,
                'previous_hash': previous_hash,
                'transactions': self.transactions
                }
        self.transactions = []
        self.chain.append(block)
        return block
    
    def get_last_block(self):
        return self.chain[-1]
    
    def proof_of_work(self, previous_nonce):
        new_nonce = 1
        check_nonce = False
        while check_nonce is False:
            hash_operation = hashlib.sha256(str(new_nonce**2 - previous_nonce**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_nonce = True
            else:
                new_nonce += 1
        return new_nonce
        
    def hash (self, block):
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    def is_chain_valid(self, chain):
        previous_block = chain[0]
        block_index = 1
        while block_index < len(chain):
            block = chain[block_index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            previous_nonce = previous_block['nonce']
            nonce = block['nonce']
            hash_operation = hashlib.sha256(str(nonce**2 - previous_nonce**2).encode()).hexdigest()
            if hash_operation[:4] != '0000':
                return False
            previous_block = block
            block_index += 1
            return True
        
    def add_transaction(self, sender, receiver, amount, time):
        self.transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
            'time': str(datetime.datetime.now())
        })
        previous_block = self.get_last_block()
        return previous_block['index'] + 1
    
    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
    
    def replace_chain(self): #New
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

#CREATE BLOCKCHAIN
blockchain = Blockchain()
node_address = str(uuid4()).replace('-', '')
root_node = 'e33f0158f0aed43b3bc741dc69ed4540d'

def mine_block(request): #mine a block
    if request.method == 'GET':
        previous_block = blockchain.get_last_block()
        previous_nonce = previous_block['nonce']
        nonce = blockchain.proof_of_work(previous_nonce)
        previous_hash = blockchain.hash(previous_block)
        blockchain.add_transaction(sender = root_node, receiver= node_address, amount = 1, time=str(datetime.datetime.now()))
        block = blockchain.create_block(nonce, previous_hash)
        response = {'message': 'Congratulations on mining an ApeSt DAO block homie!',
                    'index': block['index'],
                    'timestamp': block['timestamp'],
                    'nonce': block['nonce'],
                    'previous_hash': block['previous_hash'],
                    'transactions': block['transactions']}
        return JsonResponse(response)
    
def get_chain(request):  #GETTING the full blockchain
        if request.method == 'GET':
            response = {'chain': blockchain.chain,
                        'length': len(blockchain.chain)}
            return JsonResponse(response)
        
def is_valid(request): # validity chexk
        if request.method == 'GET':
            is_valid = blockchain.is_chain_valid(blockchain.chain)
            if is_valid:
                response = {'message': 'Yep, ApeSt DAO is valid on the blockchain'}
            else:
                response = {'message': 'Nahm, not here, ApeSt DAO has relocated'}
            return JsonResponse(response)

@csrf_exempt
def add_transaction(request): #addie of a transaction
    if request.method == 'POST':
        received_json = json.loads(request.body)
        transaction_keys = ['sender', 'receiver', 'amount', 'time']
        if not all(key in received_json for key in transaction_keys):
            return 'Some deets are missing to complete the transaction', HttpResponse(status=400)
        index = blockchain.add_transaction(received_json['sender'], received_json['receiver'], received_json['amount'], received_json['time'])
        response = {'message': f'Welcome to the Block {index}'}
    return JsonResponse(response)

@csrf_exempt
def connect_node(request): #connecting new nodes
    if request.method == 'POST':
        received_json = json.loads(request.body)
        nodes = received_json.get('nodes')
        if nodes is None:
            return "No node", HttpResponse(status=400)
        for node in nodes:
            blockchain.add_node(node)
        response = {'message': 'All the Ape-nodes are now connected. The ApeSt DAO Blockchain now contains the following nodes:',
                    'total_nodes': list(blockchain.nodes)}
    return JsonResponse(response)
    

def replace_chain(request): #replace the chain by longest chain if needed
    if request.method == 'GET':
        is_chain_replaced = blockchain.replace_chain()
        if is_chain_replaced:
            response = {'message': 'The nodes had different chains so the chain was replaced by the longest one!', 'new_chain': blockchain.chain}
        else:
            response = {'message': 'Your ApeSt DAO chains are the longest already, thank you for supporting', 'actual_chain': blockchain.chain}
    return JsonResponse(response)


#Smart contact creation
ganache_url = "HTTP://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

bytecode = '608060405234801561001057600080fd5b50610ac8806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c806331c7aca31461003b5780639e747add14610061575b600080fd5b61004361007d565b60405161005899989796959493929190610816565b60405180910390f35b61007b60048036038101906100769190610681565b6103a8565b005b600080600001805461008e906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546100ba906109c3565b80156101075780601f106100dc57610100808354040283529160200191610107565b820191906000526020600020905b8154815290600101906020018083116100ea57829003601f168201915b50505050509080600101805461011c906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610148906109c3565b80156101955780601f1061016a57610100808354040283529160200191610195565b820191906000526020600020905b81548152906001019060200180831161017857829003601f168201915b5050505050908060020180546101aa906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546101d6906109c3565b80156102235780601f106101f857610100808354040283529160200191610223565b820191906000526020600020905b81548152906001019060200180831161020657829003601f168201915b505050505090806003018054610238906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610264906109c3565b80156102b15780601f10610286576101008083540402835291602001916102b1565b820191906000526020600020905b81548152906001019060200180831161029457829003601f168201915b5050505050908060040180546102c6906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546102f2906109c3565b801561033f5780601f106103145761010080835404028352916020019161033f565b820191906000526020600020905b81548152906001019060200180831161032257829003601f168201915b5050505050908060050160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16908060050160149054906101000a900460ff16908060050160159054906101000a900460ff16908060050160169054906101000a900460ff16905089565b6040518061012001604052808a81526020018981526020018881526020018781526020018681526020018573ffffffffffffffffffffffffffffffffffffffff1681526020018415158152602001831515815260200182151581525060008082015181600001908051906020019061042192919061054c565b50602082015181600101908051906020019061043e92919061054c565b50604082015181600201908051906020019061045b92919061054c565b50606082015181600301908051906020019061047892919061054c565b50608082015181600401908051906020019061049592919061054c565b5060a08201518160050160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060c08201518160050160146101000a81548160ff02191690831515021790555060e08201518160050160156101000a81548160ff0219169083151502179055506101008201518160050160166101000a81548160ff021916908315150217905550905050505050505050505050565b828054610558906109c3565b90600052602060002090601f01602090048101928261057a57600085556105c1565b82601f1061059357805160ff19168380011785556105c1565b828001600101855582156105c1579182015b828111156105c05782518255916020019190600101906105a5565b5b5090506105ce91906105d2565b5090565b5b808211156105eb5760008160009055506001016105d3565b5090565b60006106026105fd846108f7565b6108c6565b90508281526020810184848401111561061a57600080fd5b610625848285610981565b509392505050565b60008135905061063c81610a64565b92915050565b60008135905061065181610a7b565b92915050565b600082601f83011261066857600080fd5b81356106788482602086016105ef565b91505092915050565b60008060008060008060008060006101208a8c0312156106a057600080fd5b60008a013567ffffffffffffffff8111156106ba57600080fd5b6106c68c828d01610657565b99505060208a013567ffffffffffffffff8111156106e357600080fd5b6106ef8c828d01610657565b98505060408a013567ffffffffffffffff81111561070c57600080fd5b6107188c828d01610657565b97505060608a013567ffffffffffffffff81111561073557600080fd5b6107418c828d01610657565b96505060808a013567ffffffffffffffff81111561075e57600080fd5b61076a8c828d01610657565b95505060a061077b8c828d0161062d565b94505060c061078c8c828d01610642565b93505060e061079d8c828d01610642565b9250506101006107af8c828d01610642565b9150509295985092959850929598565b6107c881610943565b82525050565b6107d781610955565b82525050565b60006107e882610927565b6107f28185610932565b9350610802818560208601610990565b61080b81610a53565b840191505092915050565b6000610120820190508181036000830152610831818c6107dd565b90508181036020830152610845818b6107dd565b90508181036040830152610859818a6107dd565b9050818103606083015261086d81896107dd565b9050818103608083015261088181886107dd565b905061089060a08301876107bf565b61089d60c08301866107ce565b6108aa60e08301856107ce565b6108b86101008301846107ce565b9a9950505050505050505050565b6000604051905081810181811067ffffffffffffffff821117156108ed576108ec610a24565b5b8060405250919050565b600067ffffffffffffffff82111561091257610911610a24565b5b601f19601f8301169050602081019050919050565b600081519050919050565b600082825260208201905092915050565b600061094e82610961565b9050919050565b60008115159050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b82818337600083830152505050565b60005b838110156109ae578082015181840152602081019050610993565b838111156109bd576000848401525b50505050565b600060028204905060018216806109db57607f821691505b602082108114156109ef576109ee6109f5565b5b50919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b6000601f19601f8301169050919050565b610a6d81610943565b8114610a7857600080fd5b50565b610a8481610955565b8114610a8f57600080fd5b5056fea2646970667358221220876e7f4418385646aa961dc1deae9237fa8a6bacd1534e72718d2b8304f3fcc164736f6c63430008000033'
abi = '[]'

web3.eth.default_account = web3.eth.accounts[0]

ApeStFF = web3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = ApeStFF.constructor().transact()

tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

@csrf_exempt
def create_apestff(request):
    ganache_url = "HTTP://127.0.0.1:7545"
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    bytecode = '608060405234801561001057600080fd5b50610ac8806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c806331c7aca31461003b5780639e747add14610061575b600080fd5b61004361007d565b60405161005899989796959493929190610816565b60405180910390f35b61007b60048036038101906100769190610681565b6103a8565b005b600080600001805461008e906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546100ba906109c3565b80156101075780601f106100dc57610100808354040283529160200191610107565b820191906000526020600020905b8154815290600101906020018083116100ea57829003601f168201915b50505050509080600101805461011c906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610148906109c3565b80156101955780601f1061016a57610100808354040283529160200191610195565b820191906000526020600020905b81548152906001019060200180831161017857829003601f168201915b5050505050908060020180546101aa906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546101d6906109c3565b80156102235780601f106101f857610100808354040283529160200191610223565b820191906000526020600020905b81548152906001019060200180831161020657829003601f168201915b505050505090806003018054610238906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610264906109c3565b80156102b15780601f10610286576101008083540402835291602001916102b1565b820191906000526020600020905b81548152906001019060200180831161029457829003601f168201915b5050505050908060040180546102c6906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546102f2906109c3565b801561033f5780601f106103145761010080835404028352916020019161033f565b820191906000526020600020905b81548152906001019060200180831161032257829003601f168201915b5050505050908060050160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16908060050160149054906101000a900460ff16908060050160159054906101000a900460ff16908060050160169054906101000a900460ff16905089565b6040518061012001604052808a81526020018981526020018881526020018781526020018681526020018573ffffffffffffffffffffffffffffffffffffffff1681526020018415158152602001831515815260200182151581525060008082015181600001908051906020019061042192919061054c565b50602082015181600101908051906020019061043e92919061054c565b50604082015181600201908051906020019061045b92919061054c565b50606082015181600301908051906020019061047892919061054c565b50608082015181600401908051906020019061049592919061054c565b5060a08201518160050160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060c08201518160050160146101000a81548160ff02191690831515021790555060e08201518160050160156101000a81548160ff0219169083151502179055506101008201518160050160166101000a81548160ff021916908315150217905550905050505050505050505050565b828054610558906109c3565b90600052602060002090601f01602090048101928261057a57600085556105c1565b82601f1061059357805160ff19168380011785556105c1565b828001600101855582156105c1579182015b828111156105c05782518255916020019190600101906105a5565b5b5090506105ce91906105d2565b5090565b5b808211156105eb5760008160009055506001016105d3565b5090565b60006106026105fd846108f7565b6108c6565b90508281526020810184848401111561061a57600080fd5b610625848285610981565b509392505050565b60008135905061063c81610a64565b92915050565b60008135905061065181610a7b565b92915050565b600082601f83011261066857600080fd5b81356106788482602086016105ef565b91505092915050565b60008060008060008060008060006101208a8c0312156106a057600080fd5b60008a013567ffffffffffffffff8111156106ba57600080fd5b6106c68c828d01610657565b99505060208a013567ffffffffffffffff8111156106e357600080fd5b6106ef8c828d01610657565b98505060408a013567ffffffffffffffff81111561070c57600080fd5b6107188c828d01610657565b97505060608a013567ffffffffffffffff81111561073557600080fd5b6107418c828d01610657565b96505060808a013567ffffffffffffffff81111561075e57600080fd5b61076a8c828d01610657565b95505060a061077b8c828d0161062d565b94505060c061078c8c828d01610642565b93505060e061079d8c828d01610642565b9250506101006107af8c828d01610642565b9150509295985092959850929598565b6107c881610943565b82525050565b6107d781610955565b82525050565b60006107e882610927565b6107f28185610932565b9350610802818560208601610990565b61080b81610a53565b840191505092915050565b6000610120820190508181036000830152610831818c6107dd565b90508181036020830152610845818b6107dd565b90508181036040830152610859818a6107dd565b9050818103606083015261086d81896107dd565b9050818103608083015261088181886107dd565b905061089060a08301876107bf565b61089d60c08301866107ce565b6108aa60e08301856107ce565b6108b86101008301846107ce565b9a9950505050505050505050565b6000604051905081810181811067ffffffffffffffff821117156108ed576108ec610a24565b5b8060405250919050565b600067ffffffffffffffff82111561091257610911610a24565b5b601f19601f8301169050602081019050919050565b600081519050919050565b600082825260208201905092915050565b600061094e82610961565b9050919050565b60008115159050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b82818337600083830152505050565b60005b838110156109ae578082015181840152602081019050610993565b838111156109bd576000848401525b50505050565b600060028204905060018216806109db57607f821691505b602082108114156109ef576109ee6109f5565b5b50919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b6000601f19601f8301169050919050565b610a6d81610943565b8114610a7857600080fd5b50565b610a8481610955565b8114610a8f57600080fd5b5056fea2646970667358221220876e7f4418385646aa961dc1deae9237fa8a6bacd1534e72718d2b8304f3fcc164736f6c63430008000033'
    web3.eth.default_account = web3.eth.accounts[0]
    ApeStFF = web3.eth.contract(abi=abi, bytecode=bytecode)
    contract_address = '0x18bc99eE752DF4CF896F8C831518a8c717ab558E'
    ape_st_ff_instance = web3.eth.contract(address='0x18bc99eE752DF4CF896F8C831518a8c717ab558E', abi=[
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"name": "createNFTProject",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "ApeStFFs",
		"outputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getContractDetails",
		"outputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
])
    if request.method == 'POST':
        try:
            received_json = json.loads(request.body.decode('utf-8'))
            tx_hash = ape_st_ff_instance.functions.createNFTProject(
                received_json['name'],
                received_json['ein'],
                received_json['locationZip'],
                received_json['description'],
                received_json['website'],
                received_json['founder'],
                received_json['jungle'],
                received_json['tree'],
                received_json['node']
            ).transact()
            
            tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

            if tx_receipt and tx_receipt['status'] == 1:
                contract_details = ape_st_ff_instance.functions.getContractDetails().call()
                response = {
                    'message': f'Contract created successfully', 
                    'contract_details': {
                        'contract': contract_address,
                        'name': contract_details[0],
                        'ein': contract_details[1],
                        'locationZip': contract_details[2],
                        'description': contract_details[3],
                        'website': contract_details[4],
                        'founder': contract_details[5],
                        'jungle': contract_details[6],
                        'tree': contract_details[7],
                        'node': contract_details[8]
                }}
                return JsonResponse(response)
                
            else:
                return JsonResponse({'error': 'Contract creation failed'})

        except Exception as e:
            return JsonResponse({'error': str(e)})
    
    return JsonResponse({'message': 'GET request received'})


@csrf_exempt
def get_apestd(request):
    ganache_url = "HTTP://127.0.0.1:7545"
    web3 = Web3(Web3.HTTPProvider(ganache_url))
    bytecode = '608060405234801561001057600080fd5b50610ac8806100206000396000f3fe608060405234801561001057600080fd5b50600436106100365760003560e01c806331c7aca31461003b5780639e747add14610061575b600080fd5b61004361007d565b60405161005899989796959493929190610816565b60405180910390f35b61007b60048036038101906100769190610681565b6103a8565b005b600080600001805461008e906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546100ba906109c3565b80156101075780601f106100dc57610100808354040283529160200191610107565b820191906000526020600020905b8154815290600101906020018083116100ea57829003601f168201915b50505050509080600101805461011c906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610148906109c3565b80156101955780601f1061016a57610100808354040283529160200191610195565b820191906000526020600020905b81548152906001019060200180831161017857829003601f168201915b5050505050908060020180546101aa906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546101d6906109c3565b80156102235780601f106101f857610100808354040283529160200191610223565b820191906000526020600020905b81548152906001019060200180831161020657829003601f168201915b505050505090806003018054610238906109c3565b80601f0160208091040260200160405190810160405280929190818152602001828054610264906109c3565b80156102b15780601f10610286576101008083540402835291602001916102b1565b820191906000526020600020905b81548152906001019060200180831161029457829003601f168201915b5050505050908060040180546102c6906109c3565b80601f01602080910402602001604051908101604052809291908181526020018280546102f2906109c3565b801561033f5780601f106103145761010080835404028352916020019161033f565b820191906000526020600020905b81548152906001019060200180831161032257829003601f168201915b5050505050908060050160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16908060050160149054906101000a900460ff16908060050160159054906101000a900460ff16908060050160169054906101000a900460ff16905089565b6040518061012001604052808a81526020018981526020018881526020018781526020018681526020018573ffffffffffffffffffffffffffffffffffffffff1681526020018415158152602001831515815260200182151581525060008082015181600001908051906020019061042192919061054c565b50602082015181600101908051906020019061043e92919061054c565b50604082015181600201908051906020019061045b92919061054c565b50606082015181600301908051906020019061047892919061054c565b50608082015181600401908051906020019061049592919061054c565b5060a08201518160050160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555060c08201518160050160146101000a81548160ff02191690831515021790555060e08201518160050160156101000a81548160ff0219169083151502179055506101008201518160050160166101000a81548160ff021916908315150217905550905050505050505050505050565b828054610558906109c3565b90600052602060002090601f01602090048101928261057a57600085556105c1565b82601f1061059357805160ff19168380011785556105c1565b828001600101855582156105c1579182015b828111156105c05782518255916020019190600101906105a5565b5b5090506105ce91906105d2565b5090565b5b808211156105eb5760008160009055506001016105d3565b5090565b60006106026105fd846108f7565b6108c6565b90508281526020810184848401111561061a57600080fd5b610625848285610981565b509392505050565b60008135905061063c81610a64565b92915050565b60008135905061065181610a7b565b92915050565b600082601f83011261066857600080fd5b81356106788482602086016105ef565b91505092915050565b60008060008060008060008060006101208a8c0312156106a057600080fd5b60008a013567ffffffffffffffff8111156106ba57600080fd5b6106c68c828d01610657565b99505060208a013567ffffffffffffffff8111156106e357600080fd5b6106ef8c828d01610657565b98505060408a013567ffffffffffffffff81111561070c57600080fd5b6107188c828d01610657565b97505060608a013567ffffffffffffffff81111561073557600080fd5b6107418c828d01610657565b96505060808a013567ffffffffffffffff81111561075e57600080fd5b61076a8c828d01610657565b95505060a061077b8c828d0161062d565b94505060c061078c8c828d01610642565b93505060e061079d8c828d01610642565b9250506101006107af8c828d01610642565b9150509295985092959850929598565b6107c881610943565b82525050565b6107d781610955565b82525050565b60006107e882610927565b6107f28185610932565b9350610802818560208601610990565b61080b81610a53565b840191505092915050565b6000610120820190508181036000830152610831818c6107dd565b90508181036020830152610845818b6107dd565b90508181036040830152610859818a6107dd565b9050818103606083015261086d81896107dd565b9050818103608083015261088181886107dd565b905061089060a08301876107bf565b61089d60c08301866107ce565b6108aa60e08301856107ce565b6108b86101008301846107ce565b9a9950505050505050505050565b6000604051905081810181811067ffffffffffffffff821117156108ed576108ec610a24565b5b8060405250919050565b600067ffffffffffffffff82111561091257610911610a24565b5b601f19601f8301169050602081019050919050565b600081519050919050565b600082825260208201905092915050565b600061094e82610961565b9050919050565b60008115159050919050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b82818337600083830152505050565b60005b838110156109ae578082015181840152602081019050610993565b838111156109bd576000848401525b50505050565b600060028204905060018216806109db57607f821691505b602082108114156109ef576109ee6109f5565b5b50919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b6000601f19601f8301169050919050565b610a6d81610943565b8114610a7857600080fd5b50565b610a8481610955565b8114610a8f57600080fd5b5056fea2646970667358221220876e7f4418385646aa961dc1deae9237fa8a6bacd1534e72718d2b8304f3fcc164736f6c63430008000033'
    web3.eth.default_account = web3.eth.accounts[0]
    contract_address = '0x18bc99eE752DF4CF896F8C831518a8c717ab558E'
    ape_st_ff_instance = web3.eth.contract(address='0x18bc99eE752DF4CF896F8C831518a8c717ab558E', abi=[
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"name": "createNFTProject",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "ApeStFFs",
		"outputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getContractDetails",
		"outputs": [
			{
				"internalType": "string",
				"name": "name",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "ein",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "locationZip",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "description",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "website",
				"type": "string"
			},
			{
				"internalType": "address",
				"name": "founder",
				"type": "address"
			},
			{
				"internalType": "bool",
				"name": "jungle",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "tree",
				"type": "bool"
			},
			{
				"internalType": "bool",
				"name": "node",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
])


    if tx_receipt and tx_receipt['status'] == 1:
                contract_details = ape_st_ff_instance.functions.getContractDetails().call()
                response = {
                    'message': f'Contract created successfully', 
                    'contract_details': {
                        'contract': contract_address,
                        'name': contract_details[0],
                        'ein': contract_details[1],
                        'locationZip': contract_details[2],
                        'description': contract_details[3],
                        'website': contract_details[4],
                        'founder': contract_details[5],
                        'jungle': contract_details[6],
                        'tree': contract_details[7],
                        'node': contract_details[8]
                }}
                return JsonResponse(response)
            
    
    return JsonResponse({'message': 'GET request received'})