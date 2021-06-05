# Coincheck Auto Trade

## アルゴリズム

### DIFFERENCE

**上昇下降トレンドによる判定**

買い：下降トレンドから上昇トレンドに切り替わったとき

売り：上昇トレンドから下降トレンドに切り替わったとき

### BOLLINGER_BANDS

**ボリンジャーバンドによる判定**

買い：-2σを下回ったとき

売り：+2σを上回ったとき

### MACD

**MACDによる判定**

買い：ヒストグラムが負から正になったとき（MACDがシグナルを下から上に抜けるとき）

売り：ヒストグラムが正の状態で減少したとき

### HYBRID

**ボリンジャーバンドとMACDによる判定**

買い：-2σを下回ったとき

売り：ヒストグラムが減少したとき

### RSI

**RSIによる判定**

買い：RSIが30を下回ったとき

売り：RSIが70を上回ったとき

### MIX

**ボリンジャーバンド・MACD・RSIによる判定**

ボリンジャーバンド・MACD・RSIのいずれか2つが条件を満たしたとき

## 環境

```shell  
$ python -V
Python 3.9.1

$ docker -v
Docker version 20.10.3, build 48d30b5

$ docker-compose -v
docker-compose version 1.28.2, build 67630359
```

## 準備

### APIキーの発行

[Coincheck]( https://h.accesstrade.net/sp/cc?rk=0100nerr00l6g9 )でAPIキーを発行する。

パーミッションは以下を選択。

- 新規注文
- 取引履歴
- 残高

※本人確認が必要です。

### .envの配置

このリポジトリのルートディレクトリに.envを作成します。

以下のように環境変数を設定して.envというファイル名で配置します。

```
# 発行したアクセスキー
ACCESS_KEY=XXXXXXXXXXXX

# 発行したシークレットキー
API_SECRET=YYYYYYYYYYYYYYYYYYYY

# 売買を行う通貨（btc, etc, fct, mona）  
COIN=btc  

# アルゴリズム（DIFFERENCE, BOLLINGER_BANDS, MACD, HYBRID, RSI, MIX）  
ALGORITHM=HYBRID  

# 1回の取引で購入する金額（円）500円以上、ビットコインの場合は(0.005*レート)円以上 
# 未設定の場合は満額 
AMOUNT=45000

# シミュレーションモード
SIMULATION=true

# ローソク足の期間
INTERVAL=60

# DynamoDBアクセスキー
AWS_ACCESS_KEY_ID=XXXXXXXXXXXX

# DynamoDBシークレットキー
AWS_SECRET_ACCESS_KEY=YYYYYYYYYYYYYYYYYYYY

# DynamoDBリージョン
AWS_DEFAULT_REGION=ap-northeast-1

# 利益
PROFIT=0
```

## 実行

```shell
% docker-compose up --build
```  
