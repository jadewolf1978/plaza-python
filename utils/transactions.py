import asyncio
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
import requests
from .logger import logger
import random

# 配置
PROVIDER = Web3(Web3.HTTPProvider('https://sepolia.base.org'))
CONTRACT_ADDRESS = Web3.to_checksum_address('0x47129e886b44b5b8815e6471fcd7b31515d83242')
EXPLORER = 'https://sepolia.basescan.org/tx/'
APPROVE_AMOUNT = Web3.to_wei(10000, 'ether')

# Token 配置
TOKENS = [
    {'address': '0x13e5fb0b6534bb22cbc59fae339dbbe0dc906871', 'name': 'wstETH'},
    {'address': '0x1aC493C87a483518642f320Ba5b342c7b78154ED', 'name': 'bondETH'},
    {'address': '0x975f67319f9DA83B403309108d4a8f84031538A6', 'name': 'levETH'},
]

# Token 类型常量
TOKEN_TYPE = {
    'WSTETH_TO_BOND': 0,   # wstETH -> bondETH
    'WSTETH_TO_LEV': 1,    # wstETH -> levETH
    'BOND_TO_WSTETH': 2,   # bondETH -> wstETH
    'LEV_TO_WSTETH': 3     # levETH -> wstETH
}

# ERC20 ABI
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
        "stateMutability": "nonpayable"
    },
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
        "stateMutability": "view"
    }
]

# 赎回和存款 ABI
REDEEM_ABI = [
    {
        "inputs": [
            {"internalType": "uint8", "name": "tokenType", "type": "uint8"},
            {"internalType": "uint256", "name": "depositAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "minAmount", "type": "uint256"},
        ],
        "name": "redeem",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

CREATE_ABI = [
    {
        "inputs": [
            {"internalType": "uint8", "name": "tokenType", "type": "uint8"},
            {"internalType": "uint256", "name": "depositAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "minAmount", "type": "uint256"},
        ],
        "name": "create",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

def get_random_amount():
    """生成0.01-0.1之间的随机ETH数量"""
    amount = random.uniform(0.01, 0.1)
    # 保留6位小数
    amount = round(amount, 6)
    return Web3.to_wei(amount, 'ether')

def get_min_amount(amount):
    """计算最小接收数量（设为主要数量的0.1%）"""
    return int(amount * 0.001)  # 0.1% of the input amount

async def approve_token_if_needed(private_key: str, token_address: str, token_name: str) -> bool:
    """检查并批准代币"""
    try:
        account = Account.from_key(private_key)
        token_contract = PROVIDER.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        allowance = token_contract.functions.allowance(
            account.address,
            CONTRACT_ADDRESS
        ).call()
        
        if allowance > APPROVE_AMOUNT:
            logger.info(f"{token_name} 已有足够的授权额度")
            return True
            
        # 构建授权交易
        nonce = PROVIDER.eth.get_transaction_count(account.address)
        gas_price = PROVIDER.eth.gas_price
        
        transaction = token_contract.functions.approve(
            CONTRACT_ADDRESS,
            APPROVE_AMOUNT
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': 84532  # Base Sepolia
        })
        
        # 签名并发送交易
        signed_txn = PROVIDER.eth.account.sign_transaction(transaction, private_key)
        tx_hash = PROVIDER.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # 等待交易确认
        receipt = PROVIDER.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            logger.info(f"{token_name} 的授权交易已确认 {EXPLORER}{tx_hash.hex()}")
            return True
        else:
            logger.error(f"{token_name} 授权交易失败")
            return False
            
    except Exception as e:
        logger.error(f"授权 {token_name} 时出错: {str(e)}")
        return False

async def approve_all_tokens(private_key: str) -> bool:
    """批准所有代币"""
    try:
        for token in TOKENS:
            success = await approve_token_if_needed(private_key, token['address'], token['name'])
            if not success:
                logger.error(f"授权 {token['name']} 失败")
                return False
        return True
    except Exception as e:
        logger.error(f"批准所有代币时出错: {str(e)}")
        return False

async def deposit(private_key: str, token_type: int) -> bool:
    """存款函数"""
    try:
        account = Account.from_key(private_key)
        contract = PROVIDER.eth.contract(address=CONTRACT_ADDRESS, abi=CREATE_ABI)
        
        # 生成随机交易金额
        deposit_amount = get_random_amount()
        min_amount = get_min_amount(deposit_amount)
        
        # 检查 wstETH 余额
        wsteth_contract = PROVIDER.eth.contract(
            address=Web3.to_checksum_address(TOKENS[0]['address']),  # wstETH
            abi=ERC20_ABI + [
                {
                    "constant": True,
                    "inputs": [{"name": "owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function",
                    "stateMutability": "view"
                }
            ]
        )
        
        # 获取 wstETH 余额
        balance = wsteth_contract.functions.balanceOf(account.address).call()
        balance_eth = Web3.from_wei(balance, 'ether')
        logger.info(f"当前 wstETH 余额: {balance_eth:.6f} wstETH")
        
        # 检查余额是否足够
        if balance < deposit_amount:
            logger.error(f"wstETH 余额不足: 需要 {Web3.from_wei(deposit_amount, 'ether'):.6f} wstETH，当前余额 {balance_eth:.6f} wstETH")
            return False
            
        # 构建交易
        nonce = PROVIDER.eth.get_transaction_count(account.address)
        gas_price = PROVIDER.eth.gas_price
        
        # 根据代币类型显示不同的信息
        target_token = 'bondETH' if token_type == TOKEN_TYPE['WSTETH_TO_BOND'] else 'levETH'
        logger.info(f"准备将 {Web3.from_wei(deposit_amount, 'ether'):.6f} wstETH 转换为 {target_token}")
        logger.info(f"最小接收数量: {Web3.from_wei(min_amount, 'ether'):.6f}")
        
        transaction = contract.functions.create(
            token_type,
            deposit_amount,
            min_amount
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': 84532  # Base Sepolia
        })
        
        # 签名并发送交易
        signed_txn = PROVIDER.eth.account.sign_transaction(transaction, private_key)
        tx_hash = PROVIDER.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"交易已发送: {EXPLORER}{tx_hash.hex()}")
        
        # 等待交易确认
        receipt = PROVIDER.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            logger.info(f"存款交易已确认 {EXPLORER}{tx_hash.hex()}")
            
            # 检查交易后余额
            new_balance = wsteth_contract.functions.balanceOf(account.address).call()
            new_balance_eth = Web3.from_wei(new_balance, 'ether')
            logger.info(f"交易后 wstETH 余额: {new_balance_eth:.6f} wstETH")
            
            # 检查目标代币余额
            target_contract = PROVIDER.eth.contract(
                address=Web3.to_checksum_address(TOKENS[1 if token_type == TOKEN_TYPE['WSTETH_TO_BOND'] else 2]['address']),
                abi=ERC20_ABI + [
                    {
                        "constant": True,
                        "inputs": [{"name": "owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "", "type": "uint256"}],
                        "type": "function",
                        "stateMutability": "view"
                    }
                ]
            )
            target_balance = target_contract.functions.balanceOf(account.address).call()
            target_balance_eth = Web3.from_wei(target_balance, 'ether')
            logger.info(f"交易后 {target_token} 余额: {target_balance_eth:.6f}")
            
            return True
        else:
            logger.error("存款交易失败")
            return False
            
    except Exception as e:
        logger.error(f"存款过程中出错: {str(e)}")
        return False

async def redeem(private_key: str, token_type: int) -> bool:
    """赎回函数"""
    try:
        account = Account.from_key(private_key)
        contract = PROVIDER.eth.contract(address=CONTRACT_ADDRESS, abi=REDEEM_ABI)
        
        # 生成随机交易金额
        redeem_amount = get_random_amount()
        min_amount = get_min_amount(redeem_amount)
        
        # 确定源代币类型
        source_token_index = 1 if token_type == TOKEN_TYPE['BOND_TO_WSTETH'] else 2
        source_token_name = TOKENS[source_token_index]['name']
        
        # 检查源代币余额
        token_contract = PROVIDER.eth.contract(
            address=Web3.to_checksum_address(TOKENS[source_token_index]['address']),
            abi=ERC20_ABI + [
                {
                    "constant": True,
                    "inputs": [{"name": "owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "type": "function",
                    "stateMutability": "view"
                }
            ]
        )
        
        # 获取代币余额
        balance = token_contract.functions.balanceOf(account.address).call()
        balance_eth = Web3.from_wei(balance, 'ether')
        logger.info(f"当前 {source_token_name} 余额: {balance_eth:.6f}")
        
        # 检查余额是否足够
        if balance < redeem_amount:
            logger.error(f"{source_token_name} 余额不足: 需要 {Web3.from_wei(redeem_amount, 'ether'):.6f}，当前余额 {balance_eth:.6f}")
            return False
        
        # 构建交易
        nonce = PROVIDER.eth.get_transaction_count(account.address)
        gas_price = PROVIDER.eth.gas_price
        
        logger.info(f"准备将 {Web3.from_wei(redeem_amount, 'ether'):.6f} {source_token_name} 转换为 wstETH")
        logger.info(f"最小接收数量: {Web3.from_wei(min_amount, 'ether'):.6f}")
        
        # 获取正确的 token_type 参数
        actual_token_type = 0 if token_type == TOKEN_TYPE['BOND_TO_WSTETH'] else 1
        
        transaction = contract.functions.redeem(
            actual_token_type,
            redeem_amount,
            min_amount
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gasPrice': gas_price,
            'chainId': 84532  # Base Sepolia
        })
        
        # 签名并发送交易
        signed_txn = PROVIDER.eth.account.sign_transaction(transaction, private_key)
        tx_hash = PROVIDER.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        logger.info(f"交易已发送: {EXPLORER}{tx_hash.hex()}")
        
        # 等待交易确认
        receipt = PROVIDER.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            logger.info(f"赎回交易已确认 {EXPLORER}{tx_hash.hex()}")
            
            # 检查交易后源代币余额
            new_balance = token_contract.functions.balanceOf(account.address).call()
            new_balance_eth = Web3.from_wei(new_balance, 'ether')
            logger.info(f"交易后 {source_token_name} 余额: {new_balance_eth:.6f}")
            
            # 检查 wstETH 余额
            wsteth_contract = PROVIDER.eth.contract(
                address=Web3.to_checksum_address(TOKENS[0]['address']),
                abi=ERC20_ABI + [
                    {
                        "constant": True,
                        "inputs": [{"name": "owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "", "type": "uint256"}],
                        "type": "function",
                        "stateMutability": "view"
                    }
                ]
            )
            wsteth_balance = wsteth_contract.functions.balanceOf(account.address).call()
            wsteth_balance_eth = Web3.from_wei(wsteth_balance, 'ether')
            logger.info(f"交易后 wstETH 余额: {wsteth_balance_eth:.6f}")
            
            return True
        else:
            logger.error("赎回交易失败")
            return False
            
    except Exception as e:
        logger.error(f"赎回过程中出错: {str(e)}")
        return False

async def run_transactions(private_key: str) -> bool:
    """运行所有交易"""
    try:
        # 检查网络连接
        if not PROVIDER.is_connected():
            logger.error("无法连接到 Base Sepolia 网络")
            return False
            
        # 获取当前链 ID
        chain_id = PROVIDER.eth.chain_id
        if chain_id != 84532:
            logger.error(f"错误的链 ID: {chain_id}，应该是 84532 (Base Sepolia)")
            return False
            
        # 批准所有代币
        if not await approve_all_tokens(private_key):
            return False
            
        # 1. wstETH -> bondETH
        logger.info("=== 开始 wstETH -> bondETH 交易 ===")
        if await deposit(private_key, TOKEN_TYPE['WSTETH_TO_BOND']):
            logger.info("wstETH -> bondETH 交易成功")
        else:
            logger.error("wstETH -> bondETH 交易失败")
            
        # 等待一段时间
        await asyncio.sleep(10)
            
        # 2. wstETH -> levETH
        logger.info("=== 开始 wstETH -> levETH 交易 ===")
        if await deposit(private_key, TOKEN_TYPE['WSTETH_TO_LEV']):
            logger.info("wstETH -> levETH 交易成功")
        else:
            logger.error("wstETH -> levETH 交易失败")
            
        # 等待一段时间
        await asyncio.sleep(10)
            
        # 3. bondETH -> wstETH
        logger.info("=== 开始 bondETH -> wstETH 交易 ===")
        if await redeem(private_key, TOKEN_TYPE['BOND_TO_WSTETH']):
            logger.info("bondETH -> wstETH 交易成功")
        else:
            logger.error("bondETH -> wstETH 交易失败")
            
        # 等待一段时间
        await asyncio.sleep(10)
            
        # 4. levETH -> wstETH
        logger.info("=== 开始 levETH -> wstETH 交易 ===")
        if await redeem(private_key, TOKEN_TYPE['LEV_TO_WSTETH']):
            logger.info("levETH -> wstETH 交易成功")
        else:
            logger.error("levETH -> wstETH 交易失败")
            
        return True
            
    except Exception as e:
        logger.error(f"运行交易时出错: {str(e)}")
        return False
