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