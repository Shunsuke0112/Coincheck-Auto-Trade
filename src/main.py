import os
import time
from src.coincheck.coincheck import CoinCheck

i = 1
coinCheck = CoinCheck(os.environ['ACCESS_KEY'], os.environ['API_SECRET'])

while True:
    time.sleep(1)
    print(i, "秒経過")
    i = i + 1

    res = coinCheck.ticker.all()
    print(res)
