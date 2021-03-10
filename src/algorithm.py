##############################
# 関数（アルゴリズム系）
##############################

import pandas as pd


def create_result(buy_flg, sell_flg):
    """


    :rtype: {}
    """
    return {
        'buy_flg': buy_flg,
        'sell_flg': sell_flg
    }


def difference(df):
    # TODO 基準値と終値をログ出力
    # 下降→上昇
    buy_flg = df.iloc[-3]['close'] > df.iloc[-2]['close'] < df.iloc[-1]['close']
    # 移動平均線が降下トレンドになったら
    sell_flg = df.iloc[-3]['close'] < df.iloc[-2]['close'] > df.iloc[-1]['close']
    return create_result(buy_flg, sell_flg)


def bollinger_bands(df):
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
    return create_result(buy_flg, sell_flg)


def macd(df):
    # http://www.algo-fx-blog.com/macd-python-technical-indicators/

    macd = pd.DataFrame()
    macd['close'] = df['close']
    macd['ema_12'] = df['close'].ewm(span=12).mean()
    macd['ema_26'] = df['close'].ewm(span=26).mean()

    macd['macd'] = macd['ema_12'] - macd['ema_26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    macd['histogram'] = macd['macd'] - macd['signal']

    # MACDがシグナルを下から上に抜けるとき
    buy_flg = macd.iloc[-2]['histogram'] < 0 and macd.iloc[-1]['histogram'] > 0
    # ヒストグラムが減少したとき（ヒストグラムがプラス状態であるときのみ）
    sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram'] and macd.iloc[-2]['histogram'] > 0
    return create_result(buy_flg, sell_flg)


def hybrid(df):
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

    # ヒストグラムが減少したとき（ヒストグラムがプラス状態であるときのみ）
    sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram'] and macd.iloc[-2]['histogram'] > 0
    return create_result(buy_flg, sell_flg)


def rsi(df):
    # http://www.algo-fx-blog.com/rsi-python-ml-features/

    # RSIの期間（基本は14）
    duration = 14

    close = df['close']
    diff = close.diff()
    # 最初の欠損レコードを切り落とす
    diff = diff[1:]

    # 値上がり幅、値下がり幅をシリーズへ切り分け
    up, down = diff.copy(), diff.copy()
    up[up < 0] = 0
    down[down > 0] = 0

    # 値上がり幅/値下がり幅の単純移動平均（14)を処理
    up_sma_14 = up.rolling(window=duration, center=False).mean()
    down_sma_14 = down.abs().rolling(window=duration, center=False).mean()

    # RSIの計算
    rs = up_sma_14 / down_sma_14
    rsi = 100.0 - (100.0 / (1.0 + rs))
    print('RSI: ' + str(rsi.iloc[-1]))

    buy_flg = float(rsi.iloc[-1]) <= 30
    sell_flg = float(rsi.iloc[-1]) >= 70
    return create_result(buy_flg, sell_flg)
