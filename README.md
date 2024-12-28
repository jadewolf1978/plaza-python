# PLAZA FINANCE BOT (Python版本) 使用默认认为知晓女巫风险 女巫风险自负！

## 作者信息
- 原作者: [zlkcyber](https://github.com/zlkcyber)
- Python版本: [jadewolf1978uk](https://github.com/jadewolf1978uk)
- 推特: [@jadewolf1978uk](https://twitter.com/jadewolf1978uk)

Plaza是一个在Base上提供链上债券和杠杆的平台。

Plaza是一个在Base上构建的智能合约集，用于创建可编程衍生品。它提供两种核心产品：bondETH和levETH，这些是基于ETH流动性质押衍生品（LSTs）和流动性再质押衍生品（LRTs）如wstETH的可编程衍生品。用户可以存入基础池资产如wstETH，并接收levETH或bondETH，这些以ERC20代币形式体现。这些代币可以与DEX、借贷市场、再质押平台等协议进行组合。

- 网站 [https://testnet.plaza.finance/](https://testnet.plaza.finance/rewards/0WkJP1uDWPis)
- 推特 [@plaza_finance](https://x.com/plaza_finance)

## 特性

- **每日自动交易**
  - 自动执行 wstETH -> bondETH -> wstETH 交易
  - 自动执行 wstETH -> levETH -> wstETH 交易
  - 随机交易金额（0.01-0.1 ETH）
  - 智能滑点保护（最小接收数量为交易金额的0.1%）
- **自动获取水龙头**
- **自动生成新钱包**
- **发送资金到现有地址**
- **所有钱包信息保存在 wallets.txt 中**
- **支持使用代理**

## 交易流程

每个钱包会自动执行以下交易循环：
1. wstETH -> bondETH：将随机数量（0.01-0.1）的 wstETH 转换为 bondETH
2. wstETH -> levETH：将随机数量（0.01-0.1）的 wstETH 转换为 levETH
3. bondETH -> wstETH：将获得的 bondETH 转换回 wstETH
4. levETH -> wstETH：将获得的 levETH 转换回 wstETH

每笔交易都会：
- 使用随机交易金额（0.01-0.1 ETH之间）
- 自动设置最小接收数量（交易金额的0.1%）
- 在执行前检查代币余额
- 在交易后显示新的余额

## 要求

- **Python**: 3.8或更高版本
- **pip**: 用于安装依赖
- **钱包必须在eth/base/arb主网上有$1以获取水龙头**
- **使用自动发送功能向现有钱包发送资金**：每个地址发送 `0.00031` eth(大于1u)

## 设置

1. 克隆此仓库：
   ```bash
   git clone https://github.com/jadewolf1978uk/plaza-python.git
   cd plaza-python
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 设置：创建新钱包
   ```bash
   python create_wallet.py
   ```

4. 额外功能：

   - 发送资金到现有地址
     ```bash
     python auto_send.py
     ```
   
   - 使用代理：支持多种代理配置方式

     1. Clash代理（推荐）：
     ```bash
     # 如果你使用Clash，直接运行以下命令生成代理配置：
     python -m utils.clash_proxy
     
     # 这会自动从你的Clash获取代理并保存到proxy.txt
     # 默认使用Clash的本地代理端口：
     # - SOCKS5: 127.0.0.1:7890
     # - HTTP: 127.0.0.1:7890
     ```

     2. 手动配置代理：
     ```bash
     # 编辑 proxy.txt 文件，每行一个代理
     # 支持以下格式：
     # http代理：  http://user:password@ip:port
     # https代理： https://user:password@ip:port
     # socks5代理：socks5://user:password@ip:port
     
     # 示例：
     http://username:pass123@192.168.1.1:8080
     socks5://user:pass@192.168.1.2:1080
     https://192.168.1.3:8080  # 无需认证的代理
     ```

5. 运行脚本：
   ```bash
   python main.py
   ```

## 代码结构

```
plaza-python/
├── main.py              # 主程序
├── contract.py          # 合约交互
├── create_wallet.py     # 钱包创建
├── auto_send.py         # 自动发送
├── requirements.txt     # 依赖文件
├── utils/
│   ├── __init__.py
│   ├── banner.py       # 横幅显示
│   ├── logger.py       # 日志工具
│   ├── script.py       # 通用工具函数
│   └── transactions.py # 交易相关功能（包含随机交易逻辑）
└── README.md
```

## 安全提示

- 交易金额随机化有助于避免交易模式被识别
- 每笔交易都有滑点保护（最小接收数量设置）
- 在每笔交易前都会检查代币余额
- 交易之间有适当的延迟以避免网络拥堵

## License

此项目采用 MIT License 许可。

# Plaza Finance Python Scripts

这是 Plaza Finance 项目的 Python 脚本集合，用于自动化各种区块链操作。

## 自动分发脚本 (auto_send.py)

这个脚本用于在 Base 主网上自动向多个钱包分发 BASE ETH。它具有智能余额检测和高效的资金分发功能。

### 主要功能

1. **主钱包管理**
   - 自动检测配置文件中的主钱包设置
   - 显示主钱包地址和当前 BASE ETH 余额
   - 支持使用已配置的主钱包或输入新的私钥
   - 可选择是否将私钥保存到配置文件中

2. **智能余额检查**
   - 显示所有目标钱包的当前 BASE ETH 余额
   - 自动跳过余额充足的钱包
   - 只向需要的钱包进行转账
   - 转账完成后显示所有钱包的最终余额

3. **详细的状态显示**
   - 转账前显示每个钱包的初始余额
   - 实时显示转账进度和状态
   - 显示每笔转账的详细信息
   - 完成后提供完整的转账汇总

4. **安全特性**
   - 私钥格式验证
   - 余额充足性检查
   - 完整的错误处理机制
   - 转账确认机制

### 使用方法

1. **准备工作**
   ```
   # 确保已安装所需依赖
   pip install -r requirements.txt
   ```

2. **配置文件**
   - 在 `config.py` 中可以配置主钱包信息：
     ```python
     MAIN_WALLET = {
         'private_key': '',  # 主钱包私钥
         'address': ''       # 主钱包地址（可选，会自动从私钥生成）
     }
     ```

3. **准备钱包列表**
   - 在 `wallets.txt` 中添加目标钱包信息，每行一个钱包：
     ```
     地址,私钥
     ```

4. **运行脚本**
   ```
   python auto_send.py
   ```

### 注意事项

1. **资金安全**
   - 确保主钱包中有足够的 BASE ETH 用于转账和支付 Gas 费用
   - 私钥信息请妥善保管，不要泄露给他人

2. **网络要求**
   - 确保网络连接稳定
   - 脚本运行过程中请勿中断

3. **余额检查**
   - 脚本会自动检查每个钱包的余额
   - 如果目标钱包已有足够的 BASE ETH，将自动跳过该钱包

### 错误处理

- 如果转账过程中出现错误，脚本会显示详细的错误信息
- 对于网络错误或余额不足等常见问题，脚本会给出明确的提示

### 开发信息

- 语言：Python 3.8+
- 网络：Base 主网
- 依赖：Web3.py, eth-account

如需帮助或报告问题，请提交 Issue 或联系开发团队。
