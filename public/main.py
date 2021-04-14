import datetime
import hashlib
import hmac
import http.client
import json
import sys
import time
import urllib

import pandas as pd
from retry import retry

##############################
# パラメータ
##############################

ACCESS_KEY = '発行したアクセスキー'
SECRET_KEY = '発行したシークレットアクセスキー'

# 計測間隔(int型)
INTERVAL = 60

# 通貨(btc, etc, fct, mona)
COIN = 'btc'

# シミュレーションモード(True, False)
SIMULATION = True

# 購入金額(int型, 指定しない場合は全額)
AMOUNT = None

##############################
# 変数
##############################

# 注文ID
order_id = None
# 購入金額
market_buy_amount = 0
# 利益
profit = 0

# シミュレーション用通貨
simulation_jpy = 100000.0
simulation_coin = 0.0

PAIR = COIN + '_jpy'


##############################
# Coincheck認証用クラス
# https://github.com/coincheckjp/coincheck-python
##############################

class CoinCheck:
    apiBase = 'coincheck.jp'

    def __init__(self, accessKey, secretKey):
        self.accessKey = accessKey
        self.secretKey = secretKey

    def __getattr__(self, attr):
        attrs = ['ticker', 'trade', 'order_book', 'order', 'leverage', 'account'
            , 'send', 'deposit', 'bank_account', 'withdraw', 'borrow', 'transfer']

        if attr in attrs:
            # dynamic import module
            moduleName = attr.replace('_', '')
            module = __import__('coincheck.' + moduleName)
            # uppercase first letter
            className = attr.title().replace('_', '')
            module = getattr(module, moduleName)
            class_ = getattr(module, className)
            # dynamic create instance of class
            func = class_(self)
            setattr(self, attr, func)
            return func
        else:
            raise AttributeError('Unknown accessor ' + attr)

    def setSignature(self, path):
        nonce = str(round(time.time() * 1000000))
        url = 'https://' + self.apiBase + path
        message = nonce + url
        signature = hmac.new(self.secretKey.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()
        self.request_headers.update({
            'ACCESS-NONCE': nonce,
            'ACCESS-KEY': self.accessKey,
            'ACCESS-SIGNATURE': signature
        })

    def request(self, method, path, params=None):
        if params is None:
            params = {}
        if method == 'GET' and len(params) > 0:
            path = path + '?' + urllib.parse.urlencode(params)
        data = ''
        self.request_headers = {}
        if method == 'POST' or method == 'DELETE':
            self.request_headers = {
                'content-type': "application/json"
            }
            path = path + '?' + urllib.parse.urlencode(params)
        self.setSignature(path)

        self.client = http.client.HTTPSConnection(self.apiBase)
        self.client.request(method, path, data, self.request_headers)
        res = self.client.getresponse()
        data = res.read()
        return data.decode("utf-8")


coincheck = CoinCheck(ACCESS_KEY, SECRET_KEY)


##############################
# 関数（API系）
##############################

@retry(exceptions=Exception, delay=1)
def get_latest_trading_rate():
    """
    最新の取引レートを取得する

    :rtype: float
    """
    if COIN == 'btc':
        ticker = coincheck.request('GET', '/api/ticker')
        return json.loads(ticker)['last']

    params = {
        'pair': PAIR
    }
    trade_all = coincheck.request('GET', '/api/trades', params)
    data = json.loads(trade_all)['data']
    return float(data[0]['rate'])


@retry(exceptions=Exception, delay=1)
def get_rate(order_type, coin_amount, price):
    """
    レートを取得する

    :rtype: object
    """
    if coin_amount is not None:
        params = {
            'order_type': order_type,
            'pair': PAIR,
            'amount': coin_amount
        }
    else:
        params = {
            'order_type': order_type,
            'pair': PAIR,
            'price': price
        }
    order_rate = coincheck.request('GET', '/api/exchange/orders/rate', params)
    return json.loads(order_rate)


def get_candle_stick():
    """
    1分間のローソク足を算出する

    :rtype: object
    """
    candle = {}
    for sec in range(1, INTERVAL + 1):
        price = get_latest_trading_rate()

        if sec == 1:
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
        elif sec == INTERVAL:
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
            'AMOUNT': AMOUNT
        }
        print(str(sec).zfill(2) + 'sec... var: ' + str(var) + ' candle: ' + str(candle))
        time.sleep(1)
    return candle


def buy(market_buy_amount):
    """
    指定した金額で買い注文を入れる（成行）

    :rtype: object
    """
    params = {
        'pair': PAIR,
        'order_type': 'market_buy',
        'market_buy_amount': market_buy_amount,  # 量ではなく金額
    }
    order = coincheck.request('POST', '/api/exchange/orders', params)
    order_create_json = json.loads(order)

    if order_create_json['success']:
        return order_create_json
    else:
        print(order)
        return None


def simulation_buy(market_buy_amount):
    """
    シミュレーション：指定した金額で買い注文を入れる（成行）

    :rtype: object
    """
    order_rate = get_rate('buy', None, market_buy_amount)
    return {
        'id': 'simulation',
        'market_buy_amount': market_buy_amount,
        'amount': order_rate['amount']
    }


def sell():
    """
    全量で売り注文を入れる（成行）

    :rtype: object
    """
    coin_amount = get_status()[COIN]
    params = {
        'pair': PAIR,
        'order_type': 'market_sell',
        'amount': coin_amount,
    }
    order = coincheck.request('POST', '/api/exchange/orders', params)
    order_create_json = json.loads(order)

    if order_create_json['success']:
        return order_create_json
    else:
        print(order)
        return None


def simulation_sell():
    """
    シミュレーション：購入した量で売り注文を入れる（成行）

    :rtype: object
    """
    return {
        'amount': simulation_coin
    }


def get_status():
    """
    現在の状態を取得する

    :rtype: object
    """
    if SIMULATION:
        return {
            'profit': profit,  # 利益
            'jpy': simulation_jpy,  # 円
            COIN: simulation_coin,  # COIN
        }

    account_balance = coincheck.request('GET', '/api/accounts/balance')
    account_balance_json = json.loads(account_balance)
    if account_balance_json['success']:
        return {
            'profit': profit,  # 利益
            'jpy': account_balance_json['jpy'],  # 円
            COIN: float(account_balance_json[COIN]),  # COIN
        }
    else:
        return account_balance_json


def get_amount():
    """
    購入金額を取得する

    :rtype: float
    """
    if AMOUNT is None or AMOUNT == '':
        # 未指定の場合は満額設定
        return float(get_status()['jpy'])
    else:
        return float(AMOUNT)


def sleep(hour):
    """
    指定した時間停止する
    """
    interval = INTERVAL * hour
    for minute in range(0, interval):
        print(str(minute) + '/' + str(interval) + ' minutes passed...')
        for sec in range(1, INTERVAL + 1):
            print(str(sec).zfill(2) + 'sec...')
            time.sleep(1)


##############################
# 変数チェック
##############################

# 暗号通貨の判定
if not (COIN == 'btc' or COIN == 'etc' or COIN == 'fct' or COIN == 'mona'):
    print('Invalid coin.')
    sys.exit()

# レートを取得してみる
res_json = get_rate('sell', 0.005, None)

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

print('Buy ' + COIN + ' for ' + str(amount) + ' Yen')

# シミュレーションの場合
if not SIMULATION:
    print('##############################')
    print('####                      ####')
    print('####   Production Mode!   ####')
    print('####                      ####')
    print('##############################')

##############################
# メイン処理
##############################

# 空のデータフレーム作り、サンプルデータを入れる
df = pd.DataFrame()
loop = 2
print('Collecting data... (' + str(loop * INTERVAL) + ' sec)')
for i in range(1, loop + 1):
    candle = get_candle_stick()
    df = df.append({'open': candle['open'], 'high': candle['high'], 'low': candle['low'], 'close': candle['close'], }, ignore_index=True)
    print(str(i) + '/' + str(loop) + ' finish.')
print('Collection is complete!')

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    candle_stick = get_candle_stick()
    df = df.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)

    # アルゴリズム
    df['diff'] = df['close'].diff()
    # 下降→上昇
    buy_flg = df.iloc[-2]['diff'] < 0 < df.iloc[-1]['diff']
    # 上昇→下降
    sell_flg = df.iloc[-2]['diff'] > 0 > df.iloc[-1]['diff']

    # 買い注文実施判定
    buying = order_id is None and buy_flg
    # 売り注文実施判定
    selling = order_id is not None and sell_flg

    if buying:
        # 買い注文実施
        print('Execute a buy order!')
        order_json = simulation_buy(get_amount()) if SIMULATION else buy(get_amount())

        # 買い注文成功の場合
        if order_json is not None:
            # オーダーIDをセット
            order_id = order_json['id']
            # 購入金額をセット
            market_buy_amount = float(order_json['market_buy_amount'])
            # シミュレーションの場合
            if SIMULATION:
                simulation_jpy -= get_amount()
                simulation_coin += float(order_json['amount'])
    elif selling:
        # 売り注文実施
        print('Execute a sell order!')
        order_json = simulation_sell() if SIMULATION else sell()

        # 売り注文成功の場合
        if order_json is not None:
            # オーダーIDを初期化
            order_id = None

            # 利益を計算するためにレートを取得
            order_rate_json = get_rate('sell', order_json['amount'], None)
            # 今回の取引の利益
            profit += float(order_rate_json['price']) - market_buy_amount

            # シミュレーションの場合
            if SIMULATION:
                simulation_jpy += float(order_rate_json['price'])
                simulation_coin = 0

            # 購入金額初期化
            market_buy_amount = 0

    # 現在の時刻・金額を表示
    dt_now = datetime.datetime.now()
    status = get_status()
    print(dt_now.strftime('%Y/%m/%d %H:%M:%S') + ' ' + str(status))

    df = df.drop(df.index[0])
