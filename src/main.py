import datetime
import sys

from api import *
from algorithm import *
from dynamodb import *

##############################
# 環境変数チェック
##############################

# 暗号通貨の判定
if not (environment.COIN == 'btc' or
        environment.COIN == 'etc' or
        environment.COIN == 'fct' or
        environment.COIN == 'mona'):
    print('Invalid coin.')
    sys.exit()

# アルゴリズムの判定
if not (environment.ALGORITHM == 'DIFFERENCE' or
        environment.ALGORITHM == 'BOLLINGER_BANDS' or
        environment.ALGORITHM == 'MACD' or
        environment.ALGORITHM == 'HYBRID' or
        environment.ALGORITHM == 'RSI' or
        environment.ALGORITHM == 'MIX'):
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
if environment.COIN == 'btc':
    min_amount = float(res_json['price'])

# 購入金額の判定
amount = get_amount()
if amount < min_amount:
    print('Please specify more than ' + str(min_amount) + ' Yen')
    sys.exit()

print('ALGORITHM: ' + environment.ALGORITHM)
print('Buy ' + environment.COIN + ' for ' + str(amount) + ' Yen')

if not environment.simulation:
    print('##############################')
    print('####                      ####')
    print('####   Production Mode!   ####')
    print('####                      ####')
    print('##############################')

##############################
# メイン処理
##############################

# 空のデータフレーム作り、サンプルデータを入れる
df = data_collecting(2 if environment.ALGORITHM == 'DIFFERENCE' else 25)

# 以下無限ループ
while True:
    # 最新の価格を取ってくる
    candle_stick = get_candle_stick()
    df = df.append({'open': candle_stick['open'], 'high': candle_stick['high'], 'low': candle_stick['low'], 'close': candle_stick['close'], }, ignore_index=True)

    buy_flg = False
    sell_flg = False

    if environment.ALGORITHM == 'DIFFERENCE':
        result = difference(df)
        buy_flg = result['buy_flg']
        sell_flg = result['sell_flg']
    elif environment.ALGORITHM == 'BOLLINGER_BANDS':
        result = bollinger_bands(df)
        buy_flg = result['buy_flg']
        sell_flg = result['sell_flg']
    elif environment.ALGORITHM == 'MACD':
        result = macd(df)
        buy_flg = result['buy_flg']
        sell_flg = result['sell_flg']
    elif environment.ALGORITHM == 'HYBRID':
        result = hybrid(df)
        buy_flg = result['buy_flg']
        sell_flg = result['sell_flg']
    elif environment.ALGORITHM == 'RSI':
        result = rsi(df)
        buy_flg = result['buy_flg']
        sell_flg = result['sell_flg']
    elif environment.ALGORITHM == 'MIX':
        bollinger_bands_result = bollinger_bands(df)
        rsi_result = rsi(df)
        buy_flg = bollinger_bands_result['buy_flg'] or rsi_result['buy_flg']
        sell_flg = bollinger_bands_result['sell_flg'] or rsi_result['sell_flg']
    else:
        print('Invalid algorithm.')
        sys.exit()

    # 買い注文実施判定
    buying = environment.order_id is None and buy_flg
    # 売り注文実施判定
    selling = environment.order_id is not None and sell_flg

    if buying:
        # 買い注文実施
        print('Execute a buy order!')
        try:
            order_json = simulation_buy(get_amount()) if environment.simulation else buy(get_amount())
            if order_json is not None:
                environment.order_id = order_json['id']
                environment.market_buy_amount = float(order_json['market_buy_amount'])
                if environment.simulation:
                    environment.simulation_jpy -= get_amount()
                    environment.simulation_coin += float(order_json['amount'])
        except Exception as e:
            print(e)
    elif selling:
        # 売り注文実施
        print('Execute a sell order!')
        try:
            order_json = simulation_sell(environment.order_id) if environment.simulation else sell(environment.order_id)
            if order_json is not None:
                environment.order_id = None
                order_rate_json = get_rate('sell', order_json['amount'])
                # 今回の取引の利益
                profit = float(order_rate_json['price']) - environment.market_buy_amount
                # 1%以上の損失を出しているか
                loss_flg = environment.market_buy_amount * 0.01 + profit < 0
                environment.profit += profit
                environment.market_buy_amount = 0
                if environment.simulation:
                    environment.simulation_jpy += float(order_rate_json['price'])
                    environment.simulation_coin = 0

                now_down_flg = profit < 0
                # 1%以上の損失を出している、もしくは2連続で損失が出たら暴落の可能性があるので一時停止する
                if loss_flg or (environment.down_flg and now_down_flg):
                    sleep()
                    # 一時停止した後なのでリセット
                    environment.down_flg = False
                else:
                    # 継続中なので今回の判定をセット
                    environment.down_flg = now_down_flg
        except Exception as e:
            print(e)

    # 現在の時刻・金額を表示
    dt_now = datetime.datetime.now()
    time = dt_now.strftime('%Y/%m/%d %H:%M:%S')
    status = get_status()
    print(time + ' ' + str(status))

    # データログ送信
    dynamo_record_create(environment.simulation, time, environment.PROJECT_NAME,
                         environment.ALGORITHM, environment.profit, candle_stick['close'], buying, selling)

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
