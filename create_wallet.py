import json
import os
from eth_account import Account
import secrets
from utils.logger import get_logger
from utils.banner import BANNER
from utils.script import ask_question

logger = get_logger()

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WALLETS_FILE = os.path.join(SCRIPT_DIR, "wallets.txt")

def get_existing_wallets():
    """获取现有钱包列表"""
    try:
        with open(WALLETS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                return json.loads(content)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.error(f"读取现有钱包时出错: {str(e)}")
    return []

def create_new_wallet():
    """创建新钱包"""
    # 生成随机私钥
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    
    wallet_details = {
        'address': account.address,
        'privateKey': private_key,
        'mnemonic': None  # Python版本不使用助记词
    }

    logger.info("创建了新的以太坊钱包:")
    logger.info(f"地址: {wallet_details['address']}")
    logger.info(f"私钥: {wallet_details['privateKey']}")

    return wallet_details

def save_wallet_to_file(wallet_details):
    """保存钱包到文件"""
    try:
        wallets = get_existing_wallets()
        wallets.append(wallet_details)

        with open(WALLETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(wallets, f, indent=2, ensure_ascii=False)

        logger.warning(f"钱包已保存到 {WALLETS_FILE}")
        return True
    except Exception as e:
        logger.error(f"保存钱包时出错: {str(e)}")
        return False

async def asking_how_many_wallets():
    """询问要创建多少个钱包"""
    while True:
        try:
            answer = ask_question('您想创建多少个钱包？ ')
            num = int(answer)
            if num > 0:
                return num
            logger.error("请输入大于0的数字")
        except ValueError:
            logger.error("请输入有效的数字")

async def main():
    """主函数"""
    logger.warning(BANNER)
    
    # 读取现有钱包数量
    existing_wallets = get_existing_wallets()
    existing_count = len(existing_wallets)
    logger.info(f"当前钱包文件中已有 {existing_count} 个钱包地址")
    
    # 询问要创建的钱包数量
    num_wallets = await asking_how_many_wallets()
    logger.info(f"即将创建 {num_wallets} 个新钱包...")
    
    # 创建新钱包
    success_count = 0
    for i in range(num_wallets):
        logger.info(f"正在创建第{i + 1}/{num_wallets}个钱包...")
        new_wallet = create_new_wallet()
        if save_wallet_to_file(new_wallet):
            success_count += 1

    # 显示最终结果
    total_wallets = len(get_existing_wallets())
    logger.info(f"\n=== 创建完成 ===")
    logger.info(f"本次成功创建: {success_count}/{num_wallets} 个钱包")
    logger.info(f"钱包文件现共有: {total_wallets} 个钱包地址")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
