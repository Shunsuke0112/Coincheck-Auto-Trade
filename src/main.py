import os
import time
import json
import datetime
import sys
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

###############
# 共通
###############

# 注文ID
order_id = None
# 利益
profit = 0

# 通貨
COIN = os.environ['COIN']
PAIR = COIN + '_jpy'
# アルゴリズム
ALGORITHM = os.environ['ALGORITHM']
# 購入金額
AMOUNT = int(os.environ['AMOUNT'])

# 暗号通貨の判定
if not (COIN == 'btc' or
        COIN == 'etc' or
        COIN == 'fct' or
        COIN == 'mona'):
    print('invalid coin.')
    sys.exit()

# アルゴリズムの判定
if not (ALGORITHM == 'DIFFERENCE' or
        ALGORITHM == 'BOLLINGER_BANDS' or
        ALGORITHM == 'MACD' or
        ALGORITHM == 'HYBRID'):
    print('invalid algorithm.')
    sys.exit()

# 最小注文数量（円）
min_amount = 500
if COIN == 'btc':
    params = {
        'order_type': 'buy',
        'pair': PAIR,
        'amount': 0.005
    }
    res = coinCheck.order.rate(params)
    min_amount = json.loads(res)['price']

# 購入金額の判定
if AMOUNT < min_amount:
    print('Please specify more than ' + min_amount + ' Yen')
    sys.exit()

print('ALGORITHM: ' + ALGORITHM)
print('Buy ' + COIN + ' for ' + str(AMOUNT) + ' Yen')


@retry(exceptions=Exception, delay=1)
def get_last():
    """
    ティッカーのlastを取得する（エラーの場合は1秒後に再実行）

    :rtype: last
    """
    ticker = coinCheck.ticker.all()
    return json.loads(ticker)['last']


def get_candle_stick():
    """
    1分前のローソク足を算出

    :rtype: candle
    """
    candle = {}
    for j in range(60):
        price = get_last()

        if j == 0:
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
        elif j == 59:
            candle['close'] = price

        if j != 0:
            candle['high'] = price if price > candle['high'] else candle['high']
            candle['low'] = price if price < candle['low'] else candle['low']

        time.sleep(1)
    return candle


def data_collecting(how_many_samples=25):
    """
    初めの25回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print('Collecting data... (' + str(how_many_samples) + ' minutes)')
    sample_data = pd.DataFrame()
    for i in range(how_many_samples):
        candle_stick = get_candle_stick()
        sample_data = sample_data.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)
    print('Collection is complete!')
    return sample_data


def buy(market_buy_amount):
    """
    指定した金額で買い注文を入れる（成行）

    :rtype: order_json
    """
    params = {
        'pair': PAIR,
        'order_type': 'market_buy',
        'market_buy_amount': market_buy_amount,  # 量ではなく金額
    }
    order = coinCheck.order.create(params)
    order_json = json.loads(order)

    if order_json['success']:
        return order_json
    else:
        print(order)
        return None


def sell(order_id):
    """
    購入した量で売り注文を入れる（成行）

    :rtype: order_json
    """
    transactions = coinCheck.order.transactions()
    for transaction in json.loads(transactions)['transactions']:
        if order_id == transaction['order_id']:
            coin_amount = transaction['funds'][COIN]
            params = {
                'pair': PAIR,
                'order_type': 'market_sell',
                'amount': coin_amount,
            }
            order = coinCheck.order.create(params)
            order_json = json.loads(order)

            if order_json['success']:
                return order_json
            else:
                print(order)
                return None


def get_rate(order_type, amount):
    """
    レートを取得する

    :rtype: order_rate_json
    """
    params = {
        'order_type': order_type,
        'pair': PAIR,
        'amount': amount
    }
    order_rate = coinCheck.order.rate(params)
    return json.loads(order_rate)


def get_status():
    """
    現在の状態を取得する

    :rtype: {}
    """
    account_balance = coinCheck.account.balance()
    account_balance_json = json.loads(account_balance)
    return {
        'profit': profit,  # 利益
        'jpy': account_balance_json['jpy'],  # 円
        COIN: account_balance_json[COIN],  # COIN
    }


# 空のデータフレーム作り、サンプルデータを入れる
df = data_collecting()

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    candle_stick = get_candle_stick()
    df = df.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)

    buy_flg = False
    sell_flg = False

    if ALGORITHM == 'DIFFERENCE':
        # 降下から上昇に変化したとき
        buy_flg = df.iloc[-3]['close'] > df.iloc[-2]['close'] and df.iloc[-2]['close'] < df.iloc[-1]['close']
        # 上昇から降下に変化したとき
        sell_flg = df.iloc[-3]['close'] < df.iloc[-2]['close'] and df.iloc[-2]['close'] > df.iloc[-1]['close']
    elif ALGORITHM == 'BOLLINGER_BANDS':
        # ボリンジャーバンドの期間（基本は20）
        duration = 20
        # σの値
        sigma = 2

        # 移動平均
        df['SMA'] = df['close'].rolling(window=duration).mean()
        # 標準偏差
        df['std'] = df['close'].rolling(window=duration).std()

        # σ区間の境界線
        df['-' + str(sigma) + 'σ'] = df['SMA'] - sigma * df['std']
        df['+' + str(sigma) + 'σ'] = df['SMA'] + sigma * df['std']

        # 最新の値段が±xσ区間を超えているか判定
        buy_flg = df.iloc[-1]['close'] < df.iloc[-1]['-' + str(sigma) + 'σ']
        sell_flg = df.iloc[-1]['close'] > df.iloc[-1]['+' + str(sigma) + 'σ']
    elif ALGORITHM == 'MACD':
        macd = pd.DataFrame()
        macd['close'] = df['close']
        macd['ema_12'] = df['close'].ewm(span=12).mean()
        macd['ema_26'] = df['close'].ewm(span=26).mean()

        macd['macd'] = macd['ema_12'] - macd['ema_26']
        macd['signal'] = macd['macd'].ewm(span=9).mean()
        macd['histogram'] = macd['macd'] - macd['signal']

        # MACDがシグナルを下から上に抜けるとき
        buy_flg = macd.iloc[-2]['histogram'] < 0 and macd.iloc[-1]['histogram'] > 0
        # ヒストグラムが減少したとき
        sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram']
    elif ALGORITHM == 'HYBRID':
        # ボリンジャーバンドの期間（基本は20）
        duration = 20
        # σの値
        sigma = 2

        # 移動平均
        df['SMA'] = df['close'].rolling(window=duration).mean()
        # 標準偏差
        df['std'] = df['close'].rolling(window=duration).std()

        # σ区間の境界線
        df['-' + str(sigma) + 'σ'] = df['SMA'] - sigma * df['std']
        df['+' + str(sigma) + 'σ'] = df['SMA'] + sigma * df['std']

        # 最新の値段が±xσ区間を超えているか判定
        buy_flg = df.iloc[-1]['close'] < df.iloc[-1]['-' + str(sigma) + 'σ']

        macd = pd.DataFrame()
        macd['close'] = df['close']
        macd['ema_12'] = df['close'].ewm(span=12).mean()
        macd['ema_26'] = df['close'].ewm(span=26).mean()

        macd['macd'] = macd['ema_12'] - macd['ema_26']
        macd['signal'] = macd['macd'].ewm(span=9).mean()
        macd['histogram'] = macd['macd'] - macd['signal']

        # ヒストグラムが減少したとき
        sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram']

    if order_id is None and buy_flg:
        # 未購入状態で-xσを下回っていたら買い注文実施
        print('Execute a buy order!')
        try:
            order_json = buy(AMOUNT)
            if order_json is not None:
                order_id = order_json['id']
                profit -= float(order_json['market_buy_amount'])
        except Exception as e:
            print(e)
    elif order_id is not None and sell_flg:
        # 購入状態で+xσを上回っていたら売り注文実施
        print('Execute a sell order!')
        try:
            order_json = sell(order_id)
            if order_json is not None:
                order_id = None
                order_rate_json = get_rate('sell', order_json['amount'])
                profit += float(order_rate_json['price'])
        except Exception as e:
            print(e)

    # 現在の時刻・金額を表示
    dt_now = datetime.datetime.now()
    status = get_status()
    print(dt_now.strftime('%Y/%m/%d %H:%M:%S') + ' ' + str(status))

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
