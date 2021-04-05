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
if environment.COIN == 'btc':
    min_amount = float(res_json['price'])

# 購入金額の判定
amount = get_amount()
if amount < min_amount:
    print('Please specify more than ' + str(min_amount) + ' Yen')
    sys.exit()

print('ALGORITHM: ' + environment.ALGORITHM)
print('Buy ' + environment.COIN + ' for ' + str(amount) + ' Yen')

# シミュレーションの場合
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

    coin_amount = get_status()[environment.COIN]
    now_amount = df.iloc[-1]['close'] * coin_amount

    # 買い注文実施判定
    buying = environment.order_id is None and buy_flg
    # 売り注文実施判定
    selling = environment.order_id is not None and sell_flg

    if buying:
        # 買い注文実施
        print('Execute a buy order!')
        order_json = simulation_buy(get_amount()) if environment.simulation else buy(get_amount())

        # 買い注文成功の場合
        if order_json is not None:
            # オーダーIDをセット
            environment.order_id = order_json['id']
            # 購入金額をセット
            environment.market_buy_amount = float(order_json['market_buy_amount'])
            # シミュレーションの場合
            if environment.simulation:
                environment.simulation_jpy -= get_amount()
                environment.simulation_coin += float(order_json['amount'])
    elif selling:
        # 売り注文実施
        print('Execute a sell order!')
        order_json = simulation_sell() if environment.simulation else sell(environment.order_id)

        # 売り注文成功の場合
        if order_json is not None:
            # オーダーIDを初期化
            environment.order_id = None

            # 利益を計算するためにレートを取得
            order_rate_json = get_rate('sell', order_json['amount'], None)
            # 今回の取引の利益
            profit = float(order_rate_json['price']) - environment.market_buy_amount
            environment.profit += profit
            environment.df_profit = environment.df_profit.append({'profit': profit, }, ignore_index=True)

            # DynamoDBに連携
            set_result(environment.simulation, environment.ALGORITHM, environment.INTERVAL, profit)

            # シミュレーションの場合
            if environment.simulation:
                environment.simulation_jpy += float(order_rate_json['price'])
                environment.simulation_coin = 0

            #  df_profitのlength調整
            if len(environment.df_profit.index) > 4:
                environment.df_profit = environment.df_profit.drop(environment.df_profit.index[0])

            # 1%以上の損失を出しているか
            loss = environment.market_buy_amount * 0.01 + profit
            loss_flg = loss < 0
            # 3連続の損失か
            environment.df_profit['diff'] = environment.df_profit.diff()
            down_flg = (environment.df_profit.iloc[-3]['diff'] < 0 and
                        environment.df_profit.iloc[-2]['diff'] < 0 and
                        environment.df_profit.iloc[-1]['diff'] < 0)

            # 購入金額初期化
            environment.market_buy_amount = 0

            # 1%以上の損失を出している、もしくは2連続で損失が出たら暴落の可能性があるので一時停止する
            if loss_flg or down_flg:
                print('loss_flg: ' + str(loss_flg))
                print(loss)
                print('down_flg: ' + str(down_flg))
                print(environment.df_profit)

                if not environment.simulation:
                    # 5時間停止
                    sleep(5)
                    # 一時停止した後なので初期化
                    environment.df_profit = pd.DataFrame() \
                        .append({'profit': profit, }, ignore_index=True) \
                        .append({'profit': profit, }, ignore_index=True) \
                        .append({'profit': profit, }, ignore_index=True)
                    # サンプルデータ作り直し（この後、先頭行を削除されるので+1）
                    df = data_collecting(2 + 1 if environment.ALGORITHM == 'DIFFERENCE' else 25 + 1)

    # 現在の時刻・金額を表示
    dt_now = datetime.datetime.now()
    time = dt_now.strftime('%Y/%m/%d %H:%M:%S')
    status = get_status()
    print(time + ' ' + str(status))

    # 先頭行を削除してdfの長さを一定に保つ（長時間の運用時のメモリ対策）
    df = df.drop(df.index[0])
