from web3 import Web3
from eth_account import Account
from eth_utils import to_wei

class EthereumWallet:
    def __init__(self, ethereum_node_url, private_key=None):
        if private_key:
            self.private_key = private_key
            self.account = Account.from_key(private_key)
        else:
            self.account = Account.create()
            self.private_key = self.account._private_key

        self.address = self.account.address
        self.web3 = Web3(Web3.HTTPProvider(ethereum_node_url)) 
        self.nonce= self.web3.eth.get_transaction_count(self.address)

    def transfer(self, amount, to_address, gas_price=None, gas_limit=None):
        if not self.web3.isAddress(to_address):
            raise ValueError("Invalid recipient address")

        if gas_price is None:
            gas_price = self.web3.toWei('10', 'gwei')  # Default gas price: 10 Gwei
        if gas_limit is None:
            gas_limit = 21000  # Default gas limit for a simple transfer

        amount_wei = to_wei(amount, 'ether')
        self.nonce += 1 
        transaction = {
            'to': to_address,
            'value': amount_wei,
            'gasPrice': gas_price,
            'gas': gas_limit,
            'nonce': self.nonce,
        }

        signed_transaction = self.web3.eth.account.signTransaction(transaction, self.private_key)
        tx_hash = self.web3.eth.sendRawTransaction(signed_transaction.rawTransaction)
        return tx_hash.hex()

'''
# Example usage:
if __name__ == "__main__":
    # Create a wallet from scratch
    wallet1 = EthereumWallet()
    print(f"Address: {wallet1.address}")
    print(f"Private Key: {wallet1.private_key}")

    # Transfer Ether from wallet1 to wallet2
    wallet2 = EthereumWallet()  # Create another wallet for testing
    tx_hash = wallet1.transfer(1.0, wallet2.address)  # Transfer 1 Ether
    print(f"Transaction Hash: {tx_hash}")

    '''