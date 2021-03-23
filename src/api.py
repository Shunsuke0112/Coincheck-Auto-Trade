##############################
# 関数（API系）
##############################

import json
import time
import pandas as pd
import os

import environment

from retry import retry
from coincheck.coincheck import CoinCheck

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])


@retry(exceptions=Exception, delay=1)
def get_latest_trading_rate():
    """
    最新の取引レートを取得する

    :rtype: float
    """
    if environment.COIN == 'btc':
        ticker = coinCheck.ticker.all()
        return json.loads(ticker)['last']

    params = {
        'pair': environment.PAIR
    }
    trade_all = coinCheck.trade.all(params)
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
            'pair': environment.PAIR,
            'amount': coin_amount
        }
    else:
        params = {
            'order_type': order_type,
            'pair': environment.PAIR,
            'price': price
        }
    order_rate = coinCheck.order.rate(params)
    return json.loads(order_rate)


def get_candle_stick():
    """
    1分間のローソク足を算出する

    :rtype: object
    """
    candle = {}
    for sec in range(1, environment.INTERVAL + 1):
        price = get_latest_trading_rate()

        if sec == 1:
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
        elif sec == environment.INTERVAL:
            candle['close'] = price

        if sec != 1:
            candle['high'] = price if price > candle['high'] else candle['high']
            candle['low'] = price if price < candle['low'] else candle['low']

        var = {
            'profit': environment.profit,
            'market_buy_amount': environment.market_buy_amount,
            'order_id': environment.order_id,
            'COIN': environment.COIN,
            'PAIR': environment.PAIR,
            'ALGORITHM': environment.ALGORITHM,
            'AMOUNT': environment.AMOUNT
        }
        print(str(sec).zfill(2) + 'sec... var: ' + str(var) + ' candle: ' + str(candle))
        time.sleep(1)
    return candle


def data_collecting(how_many_samples=25):
    """
    初めの数回は取引をせずに価格データを集める

    :rtype: price_list
    """
    print('Collecting data... (' + str(how_many_samples * environment.INTERVAL) + ' sec)')
    df = pd.DataFrame()
    for i in range(1, how_many_samples + 1):
        candle = get_candle_stick()
        df = df.append({'open': candle['open'], 'high': candle['high'], 'low': candle['low'], 'close': candle['close'], }, ignore_index=True)
        print(str(i) + '/' + str(how_many_samples) + ' finish.')
    print('Collection is complete!')
    return df


def buy(market_buy_amount):
    """
    指定した金額で買い注文を入れる（成行）

    :rtype: object
    """
    params = {
        'pair': environment.PAIR,
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

    :rtype: object
    """
    order_rate = get_rate('buy', None, market_buy_amount)
    return {
        'id': 'simulation',
        'market_buy_amount': market_buy_amount,
        'amount': order_rate['amount']
    }


def sell(order_id):
    """
    購入した量で売り注文を入れる（成行）

    :rtype: object
    """
    transactions = coinCheck.order.transactions()
    for transaction in json.loads(transactions)['transactions']:
        if order_id == transaction['order_id']:
            # TODO 買い注文が2つに分かれてるときがあるので一旦、全額売却にしておく
            # coin_amount = transaction['funds'][COIN]
            coin_amount = get_status()[environment.COIN]
            params = {
                'pair': environment.PAIR,
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


def simulation_sell():
    """
    シミュレーション：購入した量で売り注文を入れる（成行）

    :rtype: object
    """
    return {
        'amount': environment.simulation_coin
    }


def get_status():
    """
    現在の状態を取得する

    :rtype: object
    """
    if environment.simulation:
        return {
            'profit': environment.profit,  # 利益
            'jpy': environment.simulation_jpy,  # 円
            environment.COIN: environment.simulation_coin,  # COIN
        }

    account_balance = coinCheck.account.balance()
    account_balance_json = json.loads(account_balance)
    if account_balance_json['success']:
        return {
            'profit': environment.profit,  # 利益
            'jpy': account_balance_json['jpy'],  # 円
            environment.COIN: float(account_balance_json[environment.COIN]),  # COIN
        }
    else:
        return account_balance_json


def get_amount():
    """
    購入金額を取得する

    :rtype: float
    """
    if environment.AMOUNT is None or environment.AMOUNT == '':
        # 未指定の場合は満額設定
        return float(get_status()['jpy'])
    else:
        return float(environment.AMOUNT)


def sleep(hour):
    """
    指定した時間停止する
    """
    interval = environment.INTERVAL * hour
    for minute in range(0, interval):
        print(str(minute) + '/' + str(interval) + ' minutes passed...')
        for sec in range(1, environment.INTERVAL + 1):
            print(str(sec).zfill(2) + 'sec...')
            time.sleep(1)
