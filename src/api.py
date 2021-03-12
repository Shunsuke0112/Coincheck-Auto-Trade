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
    for sec in range(1, environment.INTERVAL + 1):
        price = get_last()

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

    :rtype: order_create_json
    """
    params = {
        'order_type': 'buy',
        'pair': environment.PAIR,
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


def simulation_sell(order_id):
    """
    シミュレーション：購入した量で売り注文を入れる（成行）

    :rtype: order_create_json
    """
    return {
        'amount': environment.simulation_coin
    }


def get_rate(order_type, coin_amount):
    """
    レートを取得する

    :rtype: order_rate_json
    """
    params = {
        'order_type': order_type,
        'pair': environment.PAIR,
        'amount': coin_amount
    }
    order_rate = coinCheck.order.rate(params)
    return json.loads(order_rate)


@retry(exceptions=Exception, delay=1)
def get_status():
    """
    現在の状態を取得する

    :rtype: {}
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
            environment.COIN: account_balance_json[environment.COIN],  # COIN
        }
    else:
        return account_balance_json


def get_amount():
    if environment.AMOUNT is None or environment.AMOUNT == '':
        # 未指定の場合は満額設定
        amo = float(get_status()['jpy'])
    else:
        amo = float(environment.AMOUNT)
    return amo
