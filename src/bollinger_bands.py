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
# 何秒ごとに価格データを確認するか
interval_sec = 60
# 注文ID
order_id = None
# ボリンジャーバンドの期間（基本は20）
duration = 20
# σの値
sigma = 2

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


def price_data_collecting(how_many_samples=25):
    """
    初めの25回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print("Collecting data... (" + str(how_many_samples * interval_sec) + "sec)")
    price_list = []
    for i in range(how_many_samples):
        price_list.append(get_last())
        time.sleep(interval_sec)
    print("Collection is complete!")
    return price_list


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


# 初めのサンプル価格データの収集
sample_data = price_data_collecting()

# 空のデータフレーム作り、サンプルデータを入れる
df = pd.DataFrame()
df["price"] = sample_data

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    price_now = get_last()
    df = df.append({'price': price_now, }, ignore_index=True)

    # 移動平均と標準偏差を計算
    df["SMA"] = df["price"].rolling(window=duration).mean()
    df["std"] = df["price"].rolling(window=duration).std()

    # σ区間の境界線
    df["-" + str(sigma) + "σ"] = df["SMA"] - sigma * df["std"]
    df["+" + str(sigma) + "σ"] = df["SMA"] + sigma * df["std"]

    # 最新の値段が±xσ区間を超えているか判定
    # 「低すぎる値なら下がり過ぎなので、その時の価格で買うべき」という考え方を想定
    buy_flg = df.iloc[-1]["price"] < df.iloc[-1]["-" + str(sigma) + "σ"]
    sell_flg = df.iloc[-1]["price"] > df.iloc[-1]["+" + str(sigma) + "σ"]

    if order_id is None and buy_flg:
        # 未購入状態で-xσを下回っていたら買い注文実施
        print("Execute a buy order!")
        try:
            order_json = buy(1000)
            if order_json is not None:
                order_id = order_json['id']
                profit -= float(order_json['market_buy_amount'])
        except Exception as e:
            print(e)
    elif order_id is not None and sell_flg:
        # 購入状態で+xσを上回っていたら売り注文実施
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

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
    time.sleep(interval_sec)
