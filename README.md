# Coincheck Auto Trade

## 環境

```shell  
$ python -V
Python 3.9.1

$ docker -v
Docker version 20.10.3, build 48d30b5

$ docker-compose -v
docker-compose version 1.28.2, build 67630359
```

## アルゴリズム

### DIFFERENCE

**上昇下降トレンドによる判定**

買い：下降トレンドから上昇トレンドに切り替わったとき

売り：上昇トレンドから下降トレンドに切り替わったとき

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
ACCESS_KEY=XXXXXXXXXXXXXXXX
API_SECRET=YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY
COIN=btc
INTERVAL=60
AMOUNT=
ALGORITHM=DIFFERENCE
SIMULATION=true
```

## 実行

```shell
% docker-compose up --build
```  
