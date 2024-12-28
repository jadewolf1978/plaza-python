import logging
import os

# 配置日志
def setup_logger():
    logger = logging.getLogger('clash_proxy')
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

def save_clash_proxies_to_file(output_file='proxy.txt'):
    """
    保存Clash默认代理到文件
    """
    # Clash 默认代理端口
    proxies = [
        "socks5://127.0.0.1:7890",  # Clash默认SOCKS5代理
        "http://127.0.0.1:7890"     # Clash默认HTTP代理
    ]
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")
        logger.info(f"已将Clash默认代理保存到 {output_file}")
        logger.info("代理配置：")
        for proxy in proxies:
            logger.info(f"  - {proxy}")
        return True
    except Exception as e:
        logger.error(f"保存代理到文件时出错: {str(e)}")
        return False

if __name__ == "__main__":
    save_clash_proxies_to_file()
