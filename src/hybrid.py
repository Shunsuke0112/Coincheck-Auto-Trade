import os
import time
import json
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

# シミュレーション用金額
amount = 20000000.0
# 何秒ごとに価格データを確認するか
interval_sec = 60
# 買い注文済みフラグ
buy_order_flg = False
# ボリンジャーバンドの期間（基本は20）
duration = 20
# σの値
sigma = 2


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
    print("まずは今から" + str(how_many_samples * interval_sec) + "秒間、価格データを収集します。")
    price_list = []
    for i in range(how_many_samples):
        price_list.append(get_last())
        time.sleep(interval_sec)
    print("収集が完了しました。")
    return price_list


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

    # 最新の値段が±xσ区間を超えているか判定
    # 「低すぎる値なら下がり過ぎなので、その時の価格で買うべき」という考え方を想定
    buy_flg = df.iloc[-1]["price"] < df.iloc[-1]["-" + str(sigma) + "σ"]

    macd = pd.DataFrame()
    macd['close'] = df['price']
    macd['ema_12'] = df['price'].ewm(span=12).mean()
    macd['ema_26'] = df['price'].ewm(span=26).mean()

    macd['macd'] = macd['ema_12'] - macd['ema_26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    macd['histogram'] = macd['macd'] - macd['signal']

    sell_flg = macd.iloc[-2]["histogram"] > macd.iloc[-1]["histogram"] > 0

    if not buy_order_flg and buy_flg:
        # 未購入状態で-xσを下回っていたら買い注文実施
        print("買い注文実施")
        buy_order_flg = True
        amount = amount - price_now
    elif buy_order_flg and sell_flg:
        # 購入状態で+xσを上回っていたら売り注文実施
        print("売り注文実施")
        buy_order_flg = False
        amount = amount + price_now

    # 現在の金額を表示
    print(amount)

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
    time.sleep(interval_sec)
