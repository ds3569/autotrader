import operator
import time
import pyupbit
import datetime
import requests
import numpy as np

access = "access-key"
secret = "secret-key"
myToken = "token"

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

def choose_coin():
    #거래량을 기준으로 투자 코인 선택
    coin_dic = {}
    for i in pyupbit.get_tickers(fiat="KRW"):
        df = pyupbit.get_ohlcv(i, 15)
        try:
            coin_dic[i] = float(df['volume'].mean())
        except Exception as e:
            coin_dic[i] = 0.0

    coin_dic_sorted = sorted(coin_dic.items(), key=operator.itemgetter(1), reverse=True)
    return coin_dic_sorted[0][0]

def get_ror(k, coin):
    #K별 예상 수익률 백테스팅
    df = pyupbit.get_ohlcv(coin, 15)
    try:
        df['range'] = (df['high'] - df['low']) * k
        df['target'] = df['open'] + df['range'].shift(1)

        fee = 0.001
        df['ror'] = np.where(df['high'] > df['target'],
                             df['close'] / df['target'] - fee,
                             1)

        ror = df['ror'].cumprod()[-2]
        return ror
    except Exception as e:
        return 0

def bestK(coin):
    #가장 백테스팅 결과가 좋은 K 값 선택
    k_dic = {}
    for k in np.arange(0.1, 1.0, 0.1):
        ror = get_ror(k, coin)
        k_dic[k] = float(ror)

    k_dic_sorted = sorted(k_dic.items(), key=operator.itemgetter(1), reverse=True)
    return k_dic_sorted[0][0]

def get_target_price(ticker, k):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker.strip("KRW-"):
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken,"#check", "autotrade start")
coin = choose_coin()

while True:
    try:
        k = bestK(coin)
        now = datetime.datetime.now()
        start_time = get_start_time(coin)
        end_time = start_time + datetime.timedelta(days=1)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price(coin, k)
            ma15 = get_ma15(coin)
            current_price = get_current_price(coin)
            if target_price < current_price and ma15 < current_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order(coin, krw*0.9995)
                    post_message(myToken,"#check", coin + "buy : " +str(buy_result))
        else:
            btc = get_balance(coin)
            mine = get_current_price(coin)
            if (btc * mine) > 5000:
                sell_result = upbit.sell_market_order(coin, btc)
                post_message(myToken, "#check", coin + "sell : " + str(sell_result))
                coin = choose_coin()
                time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken,"#check", e)
        time.sleep(1)