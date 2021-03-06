# Coincheckオートトレード

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

買い：MACDがシグナルを下から上に抜けるとき

売り：ヒストグラムが減少したとき

### HYBRID

**ボリンジャーバンドとMACDによる判定**

買い：-2σを下回ったとき

売り：ヒストグラムが減少したとき

## 環境

```shell  
% python -V
Python 3.9.1

% docker -v
Docker version 20.10.3, build 48d30b5

% docker-compose -v
docker-compose version 1.28.2, build 67630359
```

## 準備

### APIキーの発行

CoincheckでAPIキーを発行する。

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
# アルゴリズム（DIFFERENCE, BOLLINGER_BANDS, MACD, HYBRID）  
ALGORITHM=HYBRID  
# 1回の取引で購入する金額（円） 500円以上、ビットコインの場合は(0.005*レート)円以上  
AMOUNT=45000
```

## 実行

```shell
% docker-compose up --build
```  
