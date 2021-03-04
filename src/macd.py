import os
import time
import json
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

# シミュレーション用金額
amount = 20000000.0

# 買い注文済みフラグ
buy_order_flg = False


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
    初めの30回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print("まずは今から" + str(how_many_samples) + "分間、価格データを収集します。")
    sample_data = pd.DataFrame()
    for i in range(how_many_samples):
        candle_stick = get_candle_stick()
        sample_data = sample_data.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)
    print("収集が完了しました。")
    return sample_data


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

    if not buy_order_flg and buy_flg:
        print("買い注文実施")
        buy_order_flg = True
        amount = amount - df.iloc[-1]['close']
    elif buy_order_flg and sell_flg:
        print("売り注文実施")
        buy_order_flg = False
        amount = amount + df.iloc[-1]['close']

    print(amount)
