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
# 売り注文済みフラグ
sell_order_flg = False


@retry(exceptions=Exception, delay=1)
def get_last():
    """
    ティッカーのlastを取得する（エラーの場合は1秒後に再実行）

    :rtype: last
    """
    res = coinCheck.ticker.all()
    return json.loads(res)['last']


# 空のデータフレーム作り、データを入れる
df = pd.DataFrame()
df = df.append({'price': get_last(), }, ignore_index=True)

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    price_now = get_last()
    # 1つ前の価格と比較
    difference = price_now - df.iloc[-1]["price"]
    df = df.append({'price': price_now, 'difference': difference, }, ignore_index=True)

    if not buy_order_flg and df.iloc[-2]["difference"] < 0 and df.iloc[-1]["difference"] > 0:
        # 未購入状態で降下から上昇に変化したとき
        print("買い注文実施")
        buy_order_flg = True
        amount = amount - price_now
    elif buy_order_flg and df.iloc[-2]["difference"] > 0 and df.iloc[-1]["difference"] < 0:
        # 購入状態で上昇から降下に変化したとき
        print("売り注文実施")
        buy_order_flg = False
        amount = amount + price_now

    # 現在の金額を表示
    print(amount)

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
    time.sleep(interval_sec)
