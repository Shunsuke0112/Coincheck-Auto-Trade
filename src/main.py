import os
import time
import json
from coincheck.coincheck import CoinCheck

sec = 1
oldCandlestick = None
newCandlestick = None
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
    elif sec == 60:
        newCandlestick.set(last)
        # TODO あとで消す
        flg = oldCandlestick is not None

        # 約定判定
        if oldCandlestick is not None:
            print('判定します')
            print(vars(oldCandlestick))
            print(vars(newCandlestick))

        oldCandlestick = newCandlestick
        sec = 1
        if flg:
            break

    else:
        # 監視状態
        newCandlestick.set(last)
        sec = sec + 1
