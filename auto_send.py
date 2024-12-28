from utils.script import send_faucet, ask_question, read_wallets, get_balance
from utils.banner import BANNER
from utils.logger import get_logger
from config import MAIN_WALLET
import os
from eth_account import Account

logger = get_logger()

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.py")

def check_main_wallet():
    """检查主钱包配置"""
    if MAIN_WALLET['private_key'] and MAIN_WALLET['private_key'].strip():
        # 如果地址为空，从私钥生成地址
        if not MAIN_WALLET['address']:
            try:
                account = Account.from_key(MAIN_WALLET['private_key'])
                MAIN_WALLET['address'] = account.address
            except Exception as e:
                logger.error(f"从私钥生成地址时出错: {str(e)}")
                return False
        return True
    return False

def setup_main_wallet():
    """设置主钱包"""
    # 首先检查配置文件中是否有主钱包私钥
    if check_main_wallet():
        logger.info("\n=== 检测到已配置的主钱包 ===")
        try:
            # 获取钱包余额
            balance = get_balance(MAIN_WALLET['address'])
            logger.info(f"主钱包地址: {MAIN_WALLET['address']}")
            if balance is not None:
                logger.info(f"当前余额: {balance:.8f} BASE ETH")
            else:
                logger.warning("无法获取钱包余额")
        except Exception as e:
            logger.error(f"检查钱包信息时出错: {str(e)}")

        use_config = ask_question("是否使用此主钱包进行发送？(y/n): ")
        if use_config.lower() == 'y':
            logger.info("将使用配置文件中的主钱包")
            return MAIN_WALLET['private_key']
        else:
            logger.info("您选择使用新的钱包")
    else:
        logger.info("\n=== 未检测到主钱包配置 ===")
    
    # 如果没有配置或选择不使用配置的主钱包，则手动输入
    while True:
        pv_key = ask_question('\n请输入在Base主网上拥有BASE ETH的钱包的私钥:\n此钱包将用于初始转账: ')
        if not pv_key:
            logger.error("未提供私钥，请重新输入")
            continue
        if not pv_key.startswith('0x'):
            pv_key = '0x' + pv_key
        
        # 验证私钥并获取地址
        try:
            account = Account.from_key(pv_key)
            address = account.address
            # 获取钱包余额
            balance = get_balance(address)
            logger.info(f"\n钱包地址: {address}")
            if balance is not None:
                logger.info(f"当前余额: {balance:.8f} BASE ETH")
            else:
                logger.warning("无法获取钱包余额")
            break
        except Exception as e:
            logger.error(f"验证私钥时出错: {str(e)}")
            continue

    # 询问是否保存到配置文件
    save_to_config = ask_question("\n是否将此私钥保存为默认主钱包？(y/n): ")
    if save_to_config.lower() == 'y':
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # 更新私钥和地址
            new_content = config_content.replace(
                "    'private_key': '',",
                f"    'private_key': '{pv_key}',")
            new_content = new_content.replace(
                "    'address': ''",
                f"    'address': '{address}'")
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info("钱包信息已保存到配置文件，下次可直接使用")
        except Exception as e:
            logger.error(f"保存配置文件时出错: {str(e)}")
            logger.error(f"配置文件路径: {CONFIG_FILE}")
    
    return pv_key

async def faucet():
    """主函数"""
    logger.warning(BANNER)
    logger.warning("=== 本脚本用于Base主网自动发送 ===")
    logger.warning("此脚本将从您的主钱包向wallets.txt文件中的多个钱包分发资金(BASE ETH)。")
    logger.warning("请确保您的主钱包中有足够的BASE ETH来支付交易费用和分发的总金额。")

    # 读取钱包
    wallets = read_wallets()
    if not wallets:
        logger.error("在wallets.txt中未找到钱包。请添加钱包以继续。")
        return
    
    # 显示所有钱包地址
    logger.info(f"\n=== 从文件中加载了{len(wallets)}个钱包 ===")
    for i, wallet in enumerate(wallets, 1):
        balance = get_balance(wallet['address'])
        if balance is not None:
            logger.info(f"钱包 {i}: {wallet['address']} (当前余额: {balance:.8f} BASE ETH)")
        else:
            logger.info(f"钱包 {i}: {wallet['address']} (无法获取余额)")
    
    # 输入水龙头金额
    while True:
        try:
            faucet_amount = ask_question('\n请输入要发送到每个钱包的BASE ETH金额（例如，0.0003）：')
            amount = float(faucet_amount)
            if amount <= 0:
                logger.error("请输入大于0的数字")
                continue
            break
        except ValueError:
            logger.error("请输入有效的数字")
    
    # 计算总金额
    total_amount = amount * len(wallets)
    logger.info(f"\n=== 转账详情 ===")
    logger.info(f"每个钱包将收到: {amount:.8f} BASE ETH")
    logger.info(f"钱包总数: {len(wallets)}")
    logger.info(f"需要发送总额: {total_amount:.8f} BASE ETH")

    # 设置主钱包
    pv_key = setup_main_wallet()
    if not pv_key:
        return
    
    # 最后确认
    logger.warning(f"\n=== 请确认转账信息 ===")
    logger.warning(f"您即将向{len(wallets)}个钱包发送总共{total_amount:.8f} BASE ETH")
    logger.warning(f"每个钱包将收到 {amount:.8f} BASE ETH")
    is_confirmed = ask_question("\n您确定要继续此操作吗？ (y/n): ")

    if is_confirmed.lower() != 'y':
        logger.warning("用户取消操作。")
        return

    # 开始发送资金
    logger.info("\n=== 开始资金分发 ===")
    try:
        # 使用主私钥向第一个钱包发送资金
        first_wallet_balance = get_balance(wallets[0]['address'])
        if first_wallet_balance is not None and first_wallet_balance >= total_amount:
            logger.info(f"第一个钱包({wallets[0]['address']})余额充足({first_wallet_balance:.8f} BASE ETH)，跳过转账")
            first_wallet_has_funds = True
        else:
            logger.info(f"第1步: 从主钱包向第一个钱包({wallets[0]['address']})发送{total_amount:.8f} BASE ETH")
            send_to_wallet = await send_faucet(str(total_amount), wallets[0]['address'], pv_key)

            if not send_to_wallet:
                logger.error("发送资金到第一个钱包失败")
                return
            else:
                logger.info(f"成功发送{total_amount:.8f} BASE ETH到{wallets[0]['address']}")
                first_wallet_has_funds = True

        if first_wallet_has_funds:
            # 从钱包到钱包进行其他转账
            for i in range(len(wallets) - 1):
                sender_wallet = wallets[i]
                receipt_wallet = wallets[i + 1]
                amount_to_send = amount * (len(wallets) - (i + 1))

                # 检查接收钱包的余额
                receipt_balance = get_balance(receipt_wallet['address'])
                if receipt_balance is not None and receipt_balance >= amount:
                    logger.info(f"\n第{i+2}步: 钱包{receipt_wallet['address']}余额充足({receipt_balance:.8f} BASE ETH)，跳过转账")
                    continue

                logger.info(f"\n第{i+2}步: 从钱包{sender_wallet['address']}向钱包{receipt_wallet['address']}转账{amount_to_send:.8f} BASE ETH")
                send_to_wallets = await send_faucet(
                    str(amount_to_send),
                    receipt_wallet['address'],
                    sender_wallet['privateKey']
                )
                
                if not send_to_wallets:
                    logger.error(f"向{receipt_wallet['address']}发送资金失败")
                    return
                else:
                    logger.info(f"成功从{sender_wallet['address']}向{receipt_wallet['address']}转账{amount_to_send:.8f} BASE ETH")

            logger.info("\n=== 资金分发完成 ===")
            logger.info("所有钱包已成功充资！")
            
            # 显示最终结果和当前余额
            logger.info("\n=== 转账结果汇总 ===")
            logger.info(f"成功处理 {len(wallets)} 个钱包")
            logger.info("\n当前钱包余额:")
            for i, wallet in enumerate(wallets, 1):
                balance = get_balance(wallet['address'])
                if balance is not None:
                    logger.info(f"钱包 {i}: {wallet['address']} - {balance:.8f} BASE ETH")
                else:
                    logger.info(f"钱包 {i}: {wallet['address']} - 无法获取余额")
        
    except Exception as e:
        logger.error(f"操作过程中发生错误: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(faucet())
