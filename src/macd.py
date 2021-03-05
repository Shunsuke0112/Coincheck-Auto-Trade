import os
import time
import json
import datetime
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

# シミュレーション用金額
amount = 20000000.0

# 注文ID
order_id = None

COIN = os.environ['COIN']
pair = COIN + '_jpy'

# 利益
profit = 0


@retry(exceptions=Exception, delay=1)
def get_last():
    """
    ティッカーのlastを取得する（エラーの場合は1秒後に再実行）

    :rtype: last
    """
    res = coinCheck.ticker.all()
    return json.loads(res)['last']


def get_candle_stick():
    candle_stick = {}
    for j in range(60):
        price = get_last()

        if j == 0:
            candle_stick['open'] = price
            candle_stick['high'] = price
            candle_stick['low'] = price
        elif j == 59:
            candle_stick['close'] = price

        if j != 0:
            candle_stick['high'] = price if price > candle_stick['high'] else candle_stick['high']
            candle_stick['low'] = price if price < candle_stick['low'] else candle_stick['low']

        time.sleep(1)
    return candle_stick


def data_collecting(how_many_samples=25):
    """
    初めの25回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print("Collecting data... (" + str(how_many_samples) + "minutes)")
    sample_data = pd.DataFrame()
    for i in range(how_many_samples):
        candle_stick = get_candle_stick()
        sample_data = sample_data.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)
    print("Collection is complete!")
    return sample_data


def buy(market_buy_amount):
    """
    指定した金額で買い注文を入れる（成行）

    :rtype: order_json
    """
    params = {
        "pair": pair,
        "order_type": "market_buy",
        "market_buy_amount": market_buy_amount,  # 量ではなく金額
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
                "pair": pair,
                "order_type": "market_sell",
                "amount": coin_amount,
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
        'pair': pair,
        'amount': amount
    }
    order_rate = coinCheck.order.rate(params)
    return json.loads(order_rate)


# 空のデータフレーム作り、サンプルデータを入れる
df = data_collecting()

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    candle_stick = get_candle_stick()
    df = df.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)

    macd = pd.DataFrame()
    macd['close'] = df['close']
    macd['ema_12'] = df['close'].ewm(span=12).mean()
    macd['ema_26'] = df['close'].ewm(span=26).mean()

    macd['macd'] = macd['ema_12'] - macd['ema_26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    macd['histogram'] = macd['macd'] - macd['signal']

    # MACDがシグナルを下から上に抜けるとき
    buy_flg = macd.iloc[-2]["histogram"] < 0 and macd.iloc[-1]["histogram"] > 0
    # ヒストグラムが減少したとき
    sell_flg = macd.iloc[-2]["histogram"] > macd.iloc[-1]["histogram"]

    if order_id is None and buy_flg:
        print("Execute a buy order!")
        try:
            order_json = buy(1000)
            if order_json is not None:
                order_id = order_json['id']
                profit -= float(order_json['market_buy_amount'])
        except Exception as e:
            print(e)
    elif order_id is not None and sell_flg:
        print("Execute a sell order!")
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
    account_balance = coinCheck.account.balance()
    account_balance_json = json.loads(account_balance)
    res = {
        'profit': profit,  # 利益
        'jpy': account_balance_json['jpy'],  # 円
        COIN: account_balance_json[COIN],  # COIN
    }
    print(dt_now.strftime('%Y/%m/%d %H:%M:%S') + ' ' + str(res))
