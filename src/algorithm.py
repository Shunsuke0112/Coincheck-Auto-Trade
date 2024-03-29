##############################
# 関数（アルゴリズム系）
##############################

import pandas as pd


def create_result(buy_flg, sell_flg):
    """
    アルゴリズム実行後のレスポンス

    :rtype: object
    """
    return {
        'buy_flg': buy_flg,
        'sell_flg': sell_flg
    }


def difference(df):
    """
    上昇下降トレンドによる判定

    :rtype: object
    """
    df['diff'] = df['close'].diff()

    # 下降→上昇
    buy_flg = df.iloc[-2]['diff'] < 0 < df.iloc[-1]['diff']
    # 上昇→下降
    sell_flg = df.iloc[-2]['diff'] > 0 > df.iloc[-1]['diff']

    print(str(df.iloc[-2]['diff']) + ' -> ' + str(df.iloc[-1]['diff']))

    return create_result(buy_flg, sell_flg)


def bollinger_bands(df):
    """
    ボリンジャーバンドによる判定

    :rtype: object
    """
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

    print('-' + str(sigma) + 'σ: ' + str(df.iloc[-1]['-' + str(sigma) + 'σ']))
    print('+' + str(sigma) + 'σ: ' + str(df.iloc[-1]['+' + str(sigma) + 'σ']))

    # 最新の値段が±xσ区間を超えているか判定
    buy_flg = df.iloc[-1]['close'] < df.iloc[-1]['-' + str(sigma) + 'σ']
    sell_flg = df.iloc[-1]['close'] > df.iloc[-1]['+' + str(sigma) + 'σ']
    return create_result(buy_flg, sell_flg)


def macd(df):
    """
    MACDによる判定

    :rtype: object
    """
    # http://www.algo-fx-blog.com/macd-python-technical-indicators/

    macd = pd.DataFrame()
    macd['close'] = df['close']
    macd['ema_12'] = df['close'].ewm(span=12).mean()
    macd['ema_26'] = df['close'].ewm(span=26).mean()

    macd['macd'] = macd['ema_12'] - macd['ema_26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    macd['histogram'] = macd['macd'] - macd['signal']

    print(str(macd.iloc[-2]['histogram']) + ' -> ' + str(macd.iloc[-1]['histogram']))

    # ヒストグラムが負から正になったとき（MACDがシグナルを下から上に抜けるとき）
    buy_flg = macd.iloc[-2]['histogram'] < 0 < macd.iloc[-1]['histogram']
    # ヒストグラムが正の状態で減少したとき
    sell_flg = macd.iloc[-2]['histogram'] > 0 and macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram']
    return create_result(buy_flg, sell_flg)


def hybrid(df):
    """
    ボリンジャーバンドとMACDによる判定

    :rtype: object
    """
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

    print('-' + str(sigma) + 'σ: ' + str(df.iloc[-1]['-' + str(sigma) + 'σ']))
    print('+' + str(sigma) + 'σ: ' + str(df.iloc[-1]['+' + str(sigma) + 'σ']))

    # 最新の値段が±xσ区間を超えているか判定
    buy_flg = df.iloc[-1]['close'] < df.iloc[-1]['-' + str(sigma) + 'σ']

    macd = pd.DataFrame()
    macd['close'] = df['close']
    macd['ema_12'] = df['close'].ewm(span=12).mean()
    macd['ema_26'] = df['close'].ewm(span=26).mean()

    macd['macd'] = macd['ema_12'] - macd['ema_26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    macd['histogram'] = macd['macd'] - macd['signal']

    print(str(macd.iloc[-2]['histogram']) + ' -> ' + str(macd.iloc[-1]['histogram']))

    # ヒストグラムが減少したとき（ヒストグラムがプラス状態であるときのみ）
    sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram'] and macd.iloc[-2]['histogram'] > 0
    return create_result(buy_flg, sell_flg)


def rsi(df):
    """
    RSIによる判定

    :rtype: object
    """
    # http://www.algo-fx-blog.com/rsi-python-ml-features/

    # RSIの期間（基本は14）
    duration = 14

    df['diff'] = df['close'].diff()
    # 最初の欠損レコードを切り落とす
    diff = df['diff'][1:]

    # 値上がり幅、値下がり幅をシリーズへ切り分け
    up, down = diff.copy(), diff.copy()
    up[up < 0] = 0
    down[down > 0] = 0

    # 値上がり幅/値下がり幅の単純移動平均（14)を処理
    up_sma_14 = up.rolling(window=duration, center=False).mean()
    down_sma_14 = down.abs().rolling(window=duration, center=False).mean()

    # RSIの計算
    df['rs'] = up_sma_14 / down_sma_14
    df['rsi'] = 100.0 - (100.0 / (1.0 + df['rs']))
    print('RSI: ' + str(df['rsi'].iloc[-1]))

    # RSIが30を下回ったとき
    buy_flg = float(df['rsi'].iloc[-1]) < 30
    # RSIが70を上回ったとき
    sell_flg = float(df['rsi'].iloc[-1]) > 70
    return create_result(buy_flg, sell_flg)


def mix(df):
    """
    ボリンジャーバンド・MACD・RSIによる判定

    :rtype: object
    """
    # ボリンジャーバンド
    bollinger_bands_result = bollinger_bands(df)
    # MACD
    macd_result = macd(df)
    # RSI
    rsi_result = rsi(df)

    buy_flg_count = 0
    sell_flg_count = 0

    if bollinger_bands_result['buy_flg']:
        buy_flg_count += 1
    if bollinger_bands_result['sell_flg']:
        sell_flg_count += 1
    if macd_result['buy_flg']:
        buy_flg_count += 1
    if macd_result['sell_flg']:
        sell_flg_count += 1
    if rsi_result['buy_flg']:
        buy_flg_count += 1
    if rsi_result['sell_flg']:
        sell_flg_count += 1

    buy_flg = buy_flg_count >= 2
    sell_flg = sell_flg_count >= 2

    return create_result(buy_flg, sell_flg)
