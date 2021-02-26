import os
import time
import json
from coincheck.coincheck import CoinCheck

# 秒数
sec = 1
# 前回のローソク足
oldCandlestick = None
# 今回のローソク足
newCandlestick = None
# 上昇フラグ
riseFlg = False
# 買い注文済みフラグ
buyOderFlg = False
# 売り注文済みフラグ
sellOderFlg = False

coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])


class Candlestick:
    start = 0
    end = 0
    max = 0
    min = 0

    def __init__(self, rate):
        # 初期化
        self.start = rate
        self.end = rate
        self.max = rate
        self.min = rate

    def set(self, rate):
        if sec == 60:
            self.end = rate
        if self.max <= rate:
            self.max = rate
        if self.min >= rate:
            self.min = rate


while True:
    time.sleep(1)
    print(sec, "秒経過")

    res = coinCheck.ticker.all()
    last = json.loads(res)['last']

    if newCandlestick is not None:
        print(vars(newCandlestick))

    if sec == 1:
        # ローソク足更新
        newCandlestick = Candlestick(last)
        sec = sec + 1

    elif sec == 5:
        newCandlestick.set(last)
        # TODO あとで消す
        flg = oldCandlestick is not None

        # 約定判定
        if oldCandlestick is not None:

            # 売り注文がなければ
            if not sellOderFlg:
                varsOldCandlestick = vars(oldCandlestick)
                varsNewCandlestick = vars(newCandlestick)

                print('判定します')
                print('oldCandlestick: ' + str(varsOldCandlestick))
                print('newCandlestick: ' + str(varsNewCandlestick))

                difference = varsNewCandlestick['end'] - varsOldCandlestick['end']

                # 下降→上昇
                if (not riseFlg) and difference > 0:
                    riseFlg = True

                    # 注文されていなかったら（保険）
                    if (not buyOderFlg) and (not sellOderFlg):
                        print("FALL to RISE: ORDER!")
                        print("newCandlestick['max']+1で逆指値の買い注文入れる")
                        buyOderFlg = True

                # 下降→下降
                if (not riseFlg) and difference <= 0:
                    # None
                    print("FALL to FALL: WATCHING...")

                # 上昇→上昇
                elif riseFlg and difference > 0:
                    print("RISE to RISE: WATCHING...")

                # 上昇→下降
                elif riseFlg and difference <= 0:
                    riseFlg = False
                    buyOderFlg = False

                    # TODO 約定済みかチェック
                    contractFlg = True

                    if contractFlg:
                        # TODO 逆指値注文を検討
                        print("RISE to FALL: ORDER!")
                        print("成り行きで売り注文入れる")
                        sellOderFlg = True
                    else:
                        print("RISE to FALL: CANCEL!")
                        print("注文キャンセル")

        oldCandlestick = newCandlestick
        sec = 1
        if flg:
            break

    else:
        # 監視状態
        newCandlestick.set(last)
        sec = sec + 1
