from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from utils.logger import get_logger

logger = get_logger()

# 配置
PROVIDER = Web3(Web3.HTTPProvider('https://base.llamarpc.com'))
MESSAGE = "Sign to prove you own the address"
CONTRACT_ADDRESS = "0x83102E2Dc04CF0d2879C4F5dbD17246Fec2C963a"

# NFT合约ABI
NFT_ABI = [
    {
        "inputs": [
            {
                "internalType": "bytes",
                "name": "signature",
                "type": "bytes"
            }
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

async def sign_message(private_key):
    """签名消息"""
    try:
        account = Account.from_key(private_key)
        message = encode_defunct(text=MESSAGE)
        signed_message = account.sign_message(message)
        return signed_message.signature.hex()
    except Exception as e:
        logger.error(f"签名消息时出错: {str(e)}")
        return None

async def mint_nft(private_key, signature):
    """铸造NFT"""
    try:
        account = Account.from_key(private_key)
        contract = PROVIDER.eth.contract(address=CONTRACT_ADDRESS, abi=NFT_ABI)

        transaction = contract.functions.mint(
            signature
        ).build_transaction({
            'from': account.address,
            'nonce': PROVIDER.eth.get_transaction_count(account.address),
            'gas': 300000,
        })

        signed_txn = PROVIDER.eth.account.sign_transaction(transaction, private_key)
        tx_hash = PROVIDER.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info("Mint NFT交易已发送，等待确认...")
        
        receipt = PROVIDER.eth.wait_for_transaction_receipt(tx_hash)
        tx_hash_hex = receipt.transactionHash.hex()
        logger.info(f"NFT铸造成功，交易哈希: https://basescan.org/tx/{tx_hash_hex}")
        
        return tx_hash_hex
    except Exception as e:
        logger.error(f"与合约交互时出错: {str(e)}")
        return None
