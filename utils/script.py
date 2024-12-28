import json
import os
import requests
from web3 import Web3
from eth_account import Account
from utils.logger import get_logger
import random

logger = get_logger()

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLETS_FILE = os.path.join(ROOT_DIR, "wallets.txt")

def ask_question(question):
    """从用户获取输入"""
    return input(question)

def check_proxy_info(proxy):
    """检查代理IP信息"""
    try:
        # 从代理字符串中提取IP
        if '://' in proxy:
            proxy = proxy.split('://')[-1]
        if '@' in proxy:
            proxy = proxy.split('@')[-1]
        ip = proxy.split(':')[0]
        
        # 如果是本地代理，直接使用实际IP检查
        if ip in ['127.0.0.1', 'localhost']:
            try:
                response = requests.get('https://api.ipify.org?format=json', 
                                     proxies={'http': proxy, 'https': proxy},
                                     timeout=10)
                if response.status_code == 200:
                    ip = response.json()['ip']
            except:
                logger.warning(f"无法获取实际IP地址，使用代理地址: {proxy}")
                return None
        
        # 使用 ip-api.com 获取IP信息
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'ip': ip,
                    'country': data['country'],
                    'region': data['regionName'],
                    'city': data['city'],
                    'isp': data['isp']
                }
    except Exception as e:
        logger.error(f"检查代理信息时出错: {str(e)}")
    return None

def read_proxy_file(file_path):
    """读取代理文件并检查代理信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            proxies = [line.strip() for line in f if line.strip()]
        
        if not proxies:
            logger.warning('文件中未找到代理。')
            return []
            
        logger.info("正在检查代理信息...")
        proxy_info_list = []
        for proxy in proxies:
            info = check_proxy_info(proxy)
            if info:
                logger.info(f"代理: {proxy}")
                logger.info(f"  - IP: {info['ip']}")
                logger.info(f"  - 国家: {info['country']}")
                logger.info(f"  - 地区: {info['region']}")
                logger.info(f"  - 城市: {info['city']}")
                logger.info(f"  - ISP: {info['isp']}")
                proxy_info_list.append((proxy, info))
            else:
                logger.warning(f"无法获取代理信息: {proxy}")
                proxy_info_list.append((proxy, None))
                
        return [p[0] for p in proxy_info_list]  # 返回代理列表
        
    except Exception as e:
        logger.error(f'读取代理文件时出错: {str(e)}')
        return []

def read_wallets():
    """从wallets.txt读取钱包"""
    try:
        with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                return json.loads(content)
            return []
    except FileNotFoundError:
        logger.info(f"在{WALLETS_FILE}中未找到钱包")
        return []
    except Exception as e:
        logger.error(f"读取钱包文件时出错: {str(e)}")
        return []

async def send_faucet(faucet_amount, address_recipient, private_key):
    """发送资金到钱包"""
    logger.info(f"发送水龙头 {faucet_amount} 到地址 {address_recipient}")
    try:
        w3 = Web3(Web3.HTTPProvider('https://base.llamarpc.com'))
        account = Account.from_key(private_key)
        
        # 获取当前gas价格
        gas_price = w3.eth.gas_price
        
        # 构建交易
        transaction = {
            'nonce': w3.eth.get_transaction_count(account.address),
            'to': address_recipient,
            'value': w3.to_wei(faucet_amount, 'ether'),
            'gas': 21000,
            'maxFeePerGas': gas_price,
            'maxPriorityFeePerGas': gas_price,
            'chainId': 8453  # Base链的chainId
        }

        # 签名交易
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        
        # 发送交易
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(f"交易发送到 {address_recipient}: https://basescan.org/tx/{tx_hash.hex()}")
        
        # 等待交易确认
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt['transactionHash'].hex()
    except Exception as e:
        logger.error(f"发送水龙头时出错: {str(e)}")
        return None

def get_balance(address):
    """获取钱包余额"""
    try:
        w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return float(balance_eth)
    except Exception as e:
        logger.error(f"获取余额时出错: {str(e)}")
        return None
