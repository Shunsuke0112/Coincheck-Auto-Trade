import datetime
import json
import os
import sys
import time
import pandas as pd

from coincheck.coincheck import CoinCheck
from retry import retry

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

###############
# 共通変数
###############

# 注文ID
order_id = None
# 購入金額
market_buy_amount = 0
# 利益
profit = 0

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
# シミュレーション用通貨
simulation_jpy = 100000.0
simulation_coin = 0.0


###############
# 関数
###############

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
    1分間のローソク足を算出

    :rtype: candle
    """
    candle = {}
    interval = 60
    for sec in range(1, interval + 1):
        price = get_last()

        if sec == 1:
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
        elif sec == interval:
            candle['close'] = price

        if sec != 1:
            candle['high'] = price if price > candle['high'] else candle['high']
            candle['low'] = price if price < candle['low'] else candle['low']

        var = {
            'profit': profit,
            'market_buy_amount': market_buy_amount,
            'order_id': order_id,
            'COIN': COIN,
            'PAIR': PAIR,
            'ALGORITHM': ALGORITHM,
            'AMOUNT': AMOUNT
        }
        print(str(sec).zfill(2) + 'sec... var: ' + str(var) + ' candle: ' + str(candle))
        time.sleep(1)
    return candle


def data_collecting(how_many_samples=25):
    """
    初めの数回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print('Collecting data... (' + str(how_many_samples) + ' minutes)')
    sample_data = pd.DataFrame()
    for i in range(1, how_many_samples + 1):
        candle_data = get_candle_stick()
        sample_data = sample_data.append({'open': candle_data['open'], 'high': candle_data['high'], 'low': candle_data['low'], 'close': candle_data['close'], }, ignore_index=True)
        print(str(i) + '/' + str(how_many_samples) + ' finish.')
    print('Collection is complete!')
    return sample_data


def buy(market_buy_amount):
    """
    指定した金額で買い注文を入れる（成行）

    :rtype: order_create_json
    """
    params = {
        'pair': PAIR,
        'order_type': 'market_buy',
        'market_buy_amount': market_buy_amount,  # 量ではなく金額
    }
    order = coinCheck.order.create(params)
    order_create_json = json.loads(order)

    if order_create_json['success']:
        return order_create_json
    else:
        print(order)
        return None


def simulation_buy(market_buy_amount):
    """
    シミュレーション：指定した金額で買い注文を入れる（成行）

    :rtype: order_create_json
    """
    params = {
        'order_type': 'buy',
        'pair': PAIR,
        'price': market_buy_amount
    }
    order_rate = coinCheck.order.rate(params)
    return {
        'id': 'simulation',
        'market_buy_amount': market_buy_amount,
        'amount': json.loads(order_rate)['amount'],
    }


def sell(order_id):
    """
    購入した量で売り注文を入れる（成行）

    :rtype: order_create_json
    """
    transactions = coinCheck.order.transactions()
    for transaction in json.loads(transactions)['transactions']:
        if order_id == transaction['order_id']:
            # TODO 買い注文が2つに分かれてるときがあるので一旦、全額売却にしておく
            # coin_amount = transaction['funds'][COIN]
            coin_amount = get_status()[COIN]
            params = {
                'pair': PAIR,
                'order_type': 'market_sell',
                'amount': coin_amount,
            }
            order = coinCheck.order.create(params)
            order_create_json = json.loads(order)

            if order_create_json['success']:
                return order_create_json
            else:
                print(order)
                return None


def simulation_sell(order_id):
    """
    シミュレーション：購入した量で売り注文を入れる（成行）

    :rtype: order_create_json
    """
    return {
        'amount': simulation_coin
    }


def get_rate(order_type, coin_amount):
    """
    レートを取得する

    :rtype: order_rate_json
    """
    params = {
        'order_type': order_type,
        'pair': PAIR,
        'amount': coin_amount
    }
    order_rate = coinCheck.order.rate(params)
    return json.loads(order_rate)


def get_status():
    """
    現在の状態を取得する

    :rtype: {}
    """
    if simulation:
        return {
            'profit': profit,  # 利益
            'jpy': simulation_jpy,  # 円
            COIN: simulation_coin,  # COIN
        }

    account_balance = coinCheck.account.balance()
    account_balance_json = json.loads(account_balance)
    if account_balance_json['success']:
        return {
            'profit': profit,  # 利益
            'jpy': account_balance_json['jpy'],  # 円
            COIN: account_balance_json[COIN],  # COIN
        }
    else:
        return account_balance_json


def get_amount():
    if AMOUNT is None or AMOUNT == '':
        # 未指定の場合は満額設定
        amo = float(get_status()['jpy'])
    else:
        amo = float(AMOUNT)
    return amo


###############
# 環境変数チェック
###############

# 暗号通貨の判定
if not (COIN == 'btc' or
        COIN == 'etc' or
        COIN == 'fct' or
        COIN == 'mona'):
    print('Invalid coin.')
    sys.exit()

# アルゴリズムの判定
if not (ALGORITHM == 'DIFFERENCE' or
        ALGORITHM == 'BOLLINGER_BANDS' or
        ALGORITHM == 'MACD' or
        ALGORITHM == 'HYBRID' or
        ALGORITHM == 'RSI'):
    print('Invalid algorithm.')
    sys.exit()

# レートを取得してみる
res_json = get_rate('sell', 0.005)

# キーが有効であるか
is_valid_key = res_json['success']

# APIキーの判定
if not is_valid_key:
    print('Invalid API key.')
    sys.exit()

# 最小注文数量（円）
min_amount = 500
# BTCの場合は0.005以上からしか購入できない
if COIN == 'btc':
    min_amount = float(res_json['price'])

# 購入金額の判定
amount = get_amount()
if amount < min_amount:
    print('Please specify more than ' + str(min_amount) + ' Yen')
    sys.exit()

print('ALGORITHM: ' + ALGORITHM)
print('Buy ' + COIN + ' for ' + str(amount) + ' Yen')

if not simulation:
    print('##############################')
    print('####                      ####')
    print('####   Production Mode!   ####')
    print('####                      ####')
    print('##############################')

###############
# メイン処理
###############

# 空のデータフレーム作り、サンプルデータを入れる
df = data_collecting(2 if ALGORITHM == 'DIFFERENCE' else 25)

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

        # ヒストグラムが減少したとき（ヒストグラムがプラス状態であるときのみ）
        sell_flg = macd.iloc[-2]['histogram'] > macd.iloc[-1]['histogram'] and macd.iloc[-2]['histogram'] > 0
    elif ALGORITHM == 'RSI':
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
        RS = up_sma_14 / down_sma_14
        RSI = 100.0 - (100.0 / (1.0 + RS))
        print('RSI: ' + str(RSI.iloc[-1]))

        buy_flg = float(RSI.iloc[-1]) <= 30
        sell_flg = float(RSI.iloc[-1]) >= 70
    else:
        print('Invalid algorithm.')
        sys.exit()

    if order_id is None and buy_flg:
        # 未購入状態で-xσを下回っていたら買い注文実施
        print('Execute a buy order!')
        try:
            order_json = simulation_buy(get_amount()) if simulation else buy(get_amount())
            if order_json is not None:
                order_id = order_json['id']
                market_buy_amount = float(order_json['market_buy_amount'])
                if simulation:
                    simulation_jpy -= get_amount()
                    simulation_coin += float(order_json['amount'])
        except Exception as e:
            print(e)
    elif order_id is not None and sell_flg:
        # 購入状態で+xσを上回っていたら売り注文実施
        print('Execute a sell order!')
        try:
            order_json = simulation_sell(order_id) if simulation else sell(order_id)
            if order_json is not None:
                order_id = None
                order_rate_json = get_rate('sell', order_json['amount'])
                profit += float(order_rate_json['price']) - market_buy_amount
                market_buy_amount = 0
                if simulation:
                    simulation_jpy += float(order_rate_json['price'])
                    simulation_coin = 0
        except Exception as e:
            print(e)

    # 現在の時刻・金額を表示
    dt_now = datetime.datetime.now()
    status = get_status()
    print(dt_now.strftime('%Y/%m/%d %H:%M:%S') + ' ' + str(status))

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
