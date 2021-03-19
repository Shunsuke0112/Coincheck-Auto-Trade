import os
import pandas as pd

##############################
# 共通変数
##############################

# 注文ID
order_id = None
# 購入金額
market_buy_amount = 0
# 利益
PROFIT = os.getenv('PROFIT')
profit = float(PROFIT if type(PROFIT) is str and PROFIT != '' else 0.0)
df_profit = pd.DataFrame() \
    .append({'profit': profit, }, ignore_index=True) \
    .append({'profit': profit, }, ignore_index=True) \
    .append({'profit': profit, }, ignore_index=True)

# シミュレーション用通貨
simulation_jpy = 100000.0
simulation_coin = 0.0

# 計測間隔
INTERVAL = int(os.environ['INTERVAL'])

# 通貨
COIN = os.environ['COIN']
PAIR = COIN + '_jpy'
# アルゴリズム
ALGORITHM = os.environ['ALGORITHM']
# 購入金額
AMOUNT = os.getenv('AMOUNT')

# シミュレーションモード
SIMULATION = os.getenv('SIMULATION')
simulation = False if SIMULATION is None or SIMULATION == '' or SIMULATION == 'false' else True

# プロジェクト名
PROJECT_NAME = os.environ['COMPOSE_PROJECT_NAME']
