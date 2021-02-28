import os
import time
import json
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

amount = 20000000.0

# 約何秒間botを起動させるか
working_time = 300

# 何秒ごとに価格データを確認するか
interval_sec = 60

# 注文済みフラグ
buy_order_flg = False
sell_order_flg = False
buying = False
rise_count = 0
fall_count = 0
no_change_count = 0
fall_limit = 3
no_change_limit = 7


# ティッカーのlastを取得する（エラーの場合は1秒後に再実行）
@retry(exceptions=Exception, delay=1)
def get_last():
    res = coinCheck.ticker.all()
    return json.loads(res)['last']


# 初めの何回か(デフォルトでは25回)は取引をせずに価格データをただ集める
def price_data_collecting(how_many_samples=25):
    print("まずは今から" + str(how_many_samples * interval_sec) + "秒間、価格データを収集します。")
    price_list = []
    for i in range(how_many_samples):
        price_list.append(get_last())
        time.sleep(interval_sec)

    print("収集が完了しました。")
    return price_list


# 初めのサンプル価格データの収集
sample_data = price_data_collecting()

# 空のデータフレーム作ってさっき集めたデータを入れる
df = pd.DataFrame()
df["price"] = sample_data

# ボリンジャーバンドの期間。20とすることが多い
# 今回の場合、要するに過去20個の価格サンプルの内、今の価格の偏差値が30以下の場合に買い注文をいれるということ
duration = 20
sigma = 2

# for i in range(int(working_time / interval_sec)):
while True:
    # 最新の価格を取ってくる
    price_now = get_last()
    df = df.append({'price': price_now, }, ignore_index=True)

    # 移動平均と標準偏差を計算
    df["SMA"] = df["price"].rolling(window=duration).mean()
    df["std"] = df["price"].rolling(window=duration).std()

    # 注目している σ区間の境界線(今回は下にsigma分、つまり偏差値30以下)
    df["-" + str(sigma) + "σ"] = df["SMA"] - sigma * df["std"]
    df["+" + str(sigma) + "σ"] = df["SMA"] + sigma * df["std"]

    # 最新の値段がσ区間を超えているか判定
    # 今回は 「低すぎる値なら下がり過ぎなので、その時の価格で買うべき」という考え方を想定
    buy_flg = df.iloc[-1]["price"] < df.iloc[-1]["-" + str(sigma) + "σ"]
    sell_flg = df.iloc[-1]["price"] > df.iloc[-1]["+" + str(sigma) + "σ"]

    if not buy_order_flg and not buying and buy_flg:
        print("買い注文準備中")
        buy_order_flg = True
    # if not sell_order_flg and buying and sell_flg:
    #     print("売り注文準備中")
    #     sell_order_flg = True

    if buy_order_flg:
        if fall_count == fall_limit:
            print(str(fall_count) + "回連続降下")
            print("買い注文を実行します。")
            amount = amount - price_now
            buy_order_flg = False
            buying = True
            fall_count = 0
            no_change_count = 0
        elif no_change_count >= no_change_limit and fall_count != 0:
            print(str(no_change_count) + "回連続変化なし")
            print("買い注文を実行します。")
            amount = amount - price_now
            buy_order_flg = False
            buying = True
            fall_count = 0
            no_change_count = 0
        elif df.iloc[-2]["price"] > df.iloc[-1]["price"]:
            print("-" + str(sigma) + "σから降下")
            fall_count += 1
            no_change_count = 0
        elif df.iloc[-2]["price"] == df.iloc[-1]["price"]:
            print("-" + str(sigma) + "σから変化なし")
            no_change_count += 1
        elif df.iloc[-2]["price"] < df.iloc[-1]["price"]:
            print("-" + str(sigma) + "σから上昇")
            print("買い注文を実行します。")
            amount = amount - price_now
            buy_order_flg = False
            buying = True
            fall_count = 0
            no_change_count = 0

    # if sell_order_flg:
    #     if rise_count == 3:
    #         print(str(rise_count) + "回連続上昇")
    #         print("売り注文を実行します。")
    #         amount = amount + price_now
    #         sell_order_flg = False
    #         buying = False
    #         rise_count = 0
    #     elif df.iloc[-2]["price"] > df.iloc[-1]["price"]:
    #         print("+" + str(sigma) + "σから降下")
    #         print("売り注文を実行します。")
    #         amount = amount + price_now
    #         sell_order_flg = False
    #         buying = False
    #         rise_count = 0
    #     elif df.iloc[-2]["price"] == df.iloc[-1]["price"]:
    #         print("+" + str(sigma) + "σから変化なし")
    #     elif df.iloc[-2]["price"] < df.iloc[-1]["price"]:
    #         print("+" + str(sigma) + "σから上昇")
    #         rise_count += 1

    # if (not buy_order_flg) and buy_flg:
    #     print("買い注文を実行します。")
    #     amount = amount - price_now
    #     buy_order_flg = True
    #
    if buying:
        if no_change_count == no_change_limit:
            print(str(no_change_count) + "回連続変化なし")
            print("売り注文を実行します。")
            amount = amount + price_now
            buy_order_flg = False
            buying = False
            no_change_count = 0
        elif df.iloc[-2]["price"] > df.iloc[-1]["price"]:
            print("降下")
            print("売り注文を実行します。")
            amount = amount + price_now
            buy_order_flg = False
            buying = False
            no_change_count = 0
        elif df.iloc[-2]["price"] == df.iloc[-1]["price"]:
            print("変化なし")
            no_change_count += 1
        elif df.iloc[-2]["price"] < df.iloc[-1]["price"]:
            print("上昇")
            no_change_count = 0

    print(amount)

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
    time.sleep(interval_sec)
