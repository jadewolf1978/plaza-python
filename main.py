import asyncio
import requests
import json
from web3 import Web3
from utils.script import read_wallets, read_proxy_file
from utils.banner import BANNER
from utils.logger import get_logger
from utils.transactions import run_transactions
from contract import mint_nft, sign_message

logger = get_logger()

# 常量定义
REFF_CODE = 'bfc7b70e-66ad-4524-9bb6-733716c4da94'
PROXY_PATH = 'proxy.txt'
DECIMAL = 1000000000000000000

HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'ja',
    'Content-Type': 'application/json',
    'Origin': 'https://testnet.plaza.finance',
    'Referer': 'https://testnet.plaza.finance/',
    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'x-plaza-api-key': REFF_CODE,
    'x-plaza-vercel-server': 'undefined'
}

def create_session(proxy_url=None):
    """创建请求会话"""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    if proxy_url:
        try:
            if proxy_url.startswith('http://'):
                proxy_parts = proxy_url.replace('http://', '').split('@')
                if len(proxy_parts) == 2:
                    auth, host_port = proxy_parts
                    user, password = auth.split(':')
                    host, port = host_port.split(':')
                    
                    session.proxies = {
                        'http': f'http://{user}:{password}@{host}:{port}',
                        'https': f'http://{user}:{password}@{host}:{port}'
                    }
                else:
                    raise ValueError('代理URL格式无效')
        except Exception as e:
            logger.error(f'设置代理时出错: {str(e)}')
    
    return session

async def get_faucet(address, proxy_url=None):
    """获取水龙头"""
    session = create_session(proxy_url)
    try:
        logger.info(f"正在为地址 {address} 请求水龙头...")
        
        # 确保地址是checksum格式
        checksum_address = Web3.to_checksum_address(address)
        
        # 设置请求头的Content-Length
        data = {'address': checksum_address}
        json_data = json.dumps(data)
        headers = session.headers.copy()
        headers['Content-Length'] = str(len(json_data))
        
        response = session.post(
            'https://api.plaza.finance/faucet/queue',
            json=data,
            headers=headers,
            verify=True
        )
        
        logger.info(f"水龙头请求状态码: {response.status_code}")
        try:
            result = response.json()
            logger.info(f"水龙头响应内容: {result}")
            if response.status_code == 403 and "You must have $1 worth of ETH" in result.get('message', ''):
                logger.error("需要在主网持有价值1美元的ETH才能领取水龙头")
                return None
        except:
            logger.info(f"水龙头响应文本: {response.text}")
        
        response.raise_for_status()
        if response.status_code in [200, 201]:
            logger.info("水龙头响应：成功")
            return 'success'
        return None
    except Exception as e:
        logger.error(f"获取水龙头时出错: {str(e)}")
        if hasattr(e, 'response') and e.response:
            logger.error(f"错误状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                logger.error(f"错误详情: {error_detail}")
            except:
                logger.error(f"错误响应: {e.response.text}")
        return None

async def fetch_user(address, proxy_url=None):
    """获取用户信息"""
    session = create_session(proxy_url)
    try:
        response = session.get(f'https://api.plaza.finance/user?user={address}')
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取用户信息时出错: {str(e)}")
        return None

async def claim_request(address, proxy_url=None):
    """申请奖励"""
    session = create_session(proxy_url)
    try:
        response = session.post(
            'https://api.plaza.finance/referrals/claim',
            json={'address': address, 'code': 'QoH1pwf6C0qJ'}
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

async def fetch_user_balance(address, proxy_url=None):
    """获取用户余额"""
    session = create_session(proxy_url)
    try:
        response = session.get(
            'https://api.plaza.finance/user/balances',
            params={'networkId': 84532, 'user': address}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"获取余额时出错: {str(e)}")
        return None

async def get_sign(level, user, signature, proxy_url=None):
    """获取签名"""
    session = create_session(proxy_url)
    try:
        response = session.post(
            'https://api.plaza.finance/gamification/claim-level-rewards',
            json={'level': level, 'user': user, 'signature': signature}
        )
        response.raise_for_status()
        return response.json()['signature']
    except Exception as e:
        logger.error(f"获取签名时出错: {str(e)}")
        if getattr(e, 'response', None) and e.response.json().get('message') == '用户已领取奖励':
            return 'claimed'
        return None

async def claim_nft_reward(points, nft_type, required_points, wallet, proxy, claimed_state):
    """领取NFT奖励"""
    wallet_key = wallet['address'].lower()
    if claimed_state[wallet_key][f'nft{nft_type}']:
        return

    if points < required_points:
        return

    logger.info(f"=== 领取 NFT {nft_type} 奖励 地址: {wallet['address']} ===")
    sign_wallet = await sign_message(wallet['privateKey'])
    signature = await get_sign(nft_type, wallet['address'], sign_wallet, proxy)

    if signature and signature != 'claimed':
        mint_result = await mint_nft(wallet['privateKey'], signature)
        if mint_result:
            logger.info(f"=== NFT {nft_type} 成功领取 ===")
            claimed_state[wallet_key][f'nft{nft_type}'] = True
        else:
            logger.error(f"=== 领取 NFT {nft_type} 失败 ===")
    elif signature == 'claimed':
        claimed_state[wallet_key][f'nft{nft_type}'] = True

async def approve_wsteth(web3, wallet_address, private_key):
    """批准 wstETH"""
    try:
        # 确保地址是checksum格式
        wallet_address = Web3.to_checksum_address(wallet_address)
        wsteth_address = Web3.to_checksum_address('0x13e5fb0b6534bb22cbc59fae339dbbe0dc906871')
        bond_eth_address = Web3.to_checksum_address('0x47129e886b44b5b8815e6471fcd7b31515d83242')
        
        # 创建合约实例
        contract = web3.eth.contract(
            address=wsteth_address,
            abi=WSTETH_ABI
        )
        
        # 批准 bondETH
        nonce = web3.eth.get_transaction_count(wallet_address)
        max_amount = 2**256 - 1
        
        approve_txn = contract.functions.approve(
            bond_eth_address,
            max_amount
        ).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price
        })
        
        signed_txn = web3.eth.account.sign_transaction(approve_txn, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt.status != 1:
            logger.error("bondETH批准交易失败")
            return False
        logger.info("bondETH 的批准交易已确认", extra={"url": f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"})
        
        # 批准 levETH (使用相同地址)
        nonce = web3.eth.get_transaction_count(wallet_address)
        approve_txn = contract.functions.approve(
            bond_eth_address,
            max_amount
        ).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': web3.eth.gas_price
        })
        
        signed_txn = web3.eth.account.sign_transaction(approve_txn, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt.status != 1:
            logger.error("levETH批准交易失败")
            return False
        logger.info("levETH 的批准交易已确认", extra={"url": f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"})
        
        return True
    except Exception as e:
        logger.error(f"批准 wstETH 时出错: {str(e)}")
        return False

async def deposit(web3, wallet_address, private_key):
    """存款"""
    try:
        # 确保地址是checksum格式
        wallet_address = Web3.to_checksum_address(wallet_address)
        bond_eth_address = Web3.to_checksum_address('0x47129e886b44b5b8815e6471fcd7b31515d83242')
        
        # 创建合约实例
        contract = web3.eth.contract(
            address=bond_eth_address,
            abi=BOND_ABI
        )
        
        # 获取用户wstETH余额
        wsteth_contract = web3.eth.contract(
            address=Web3.to_checksum_address('0x13e5fb0b6534bb22cbc59fae339dbbe0dc906871'),
            abi=WSTETH_ABI
        )
        balance = wsteth_contract.functions.balanceOf(wallet_address).call()
        
        # 构建存款交易
        nonce = web3.eth.get_transaction_count(wallet_address)
        deposit_txn = contract.functions.deposit(
            balance,
            0  # minSharesOut
        ).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': web3.eth.gas_price
        })
        
        signed_txn = web3.eth.account.sign_transaction(deposit_txn, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        logger.info(f"存款交易已发送: {tx_hash.hex()}")
        
        # 等待交易确认
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt.status != 1:
            logger.error("存款交易失败")
            return False
            
        logger.info("存款交易已确认", extra={"url": f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"})
        return True
    except Exception as e:
        logger.error(f"存款过程中出错: {str(e)}")
        return False

async def main():
    """主函数"""
    logger.warning(BANNER)
    wallets = read_wallets()
    proxy_list = read_proxy_file(PROXY_PATH)
    index = 0
    claimed_state = {}

    while True:
        for wallet in wallets:
            wallet_key = wallet['address'].lower()
            claimed_state[wallet_key] = claimed_state.get(wallet_key, {'nft1': False, 'nft3': False})
            proxy = proxy_list[index % len(proxy_list)] if proxy_list else None
            logger.warning(f"使用代理运行: {proxy or '无代理'}")

            try:
                await claim_request(wallet['address'], proxy)

                profile = await fetch_user(wallet['address'], proxy)
                level = profile.get('level', 0) if profile else 0
                points = profile.get('points', 0) if profile else 0
                logger.info(f"=== 地址: {wallet['address']} | 等级: {level} | 积分: {points} ===")

                logger.info("=== 检查 NFT 奖励 ===")
                await claim_nft_reward(points, 1, 50, wallet, proxy, claimed_state)
                await claim_nft_reward(points, 3, 200, wallet, proxy, claimed_state)

                if not claimed_state[wallet_key]['nft1'] and not claimed_state[wallet_key]['nft3']:
                    logger.info("=== 此地址没有可领取的 NFT 奖励 ===")
                else:
                    logger.info("=== 此地址的 NFT 奖励已领取 ===")

                balances = await fetch_user_balance(wallet['address'], proxy)
                balance = int(balances[0].get('balanceRaw', '0'), 10) / DECIMAL if balances else 0
                logger.info(f"=== 地址: {wallet['address']} | wstETH 余额: {balance} ===\n")

                if balance > 0.02:
                    logger.info(f"开始进行交易，地址: {wallet['address']}")
                    await run_transactions(wallet['privateKey'])
                else:
                    logger.info("=== wstETH 余额不足，尝试领取水龙头 ===")
                    faucet_result = await get_faucet(wallet['address'], proxy)
                    if faucet_result == 'success':
                        logger.info("水龙头领取成功，等待15秒后继续...")
                        await asyncio.sleep(15)  # 等待余额到账
                        await run_transactions(wallet['privateKey'])
                    else:
                        logger.error("水龙头领取失败")

            except Exception as e:
                logger.error(f"处理钱包时出错: {str(e)}")

            index += 1
            await asyncio.sleep(1)  # 避免请求过快

        logger.info("=== 完成一轮操作，等待下一轮... ===")
        await asyncio.sleep(60)  # 等待1分钟后开始下一轮

if __name__ == "__main__":
    asyncio.run(main())
