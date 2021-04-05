import boto3
from boto3.dynamodb.conditions import Key


def set_result(simulation, algorithm, interval, profit):
    """
    DynamoDBへログを送信
    """
    try:
        dynamoDB = boto3.resource('dynamodb')
        table_name = 'coincheck-auto-trade-simulation' if simulation else 'coincheck-auto-trade'
        table = dynamoDB.Table(table_name)  # DynamoDBのテーブル名

        # DynamoDBへのquery処理実行
        queryData = table.query(
            KeyConditionExpression=Key('algorithm').eq(algorithm) & Key('interval').eq(interval),  # 取得するKey情報
            Limit=1  # 取得するデータ件数
        )

        if queryData['Count'] == 0:
            # 初回登録
            table.put_item(
                Item={
                    'algorithm': algorithm,  # アルゴリズム
                    'interval': interval,  # 間隔
                    'profit': int(profit)  # 利益
                }
            )
        else:
            # 2回目以降
            table.update_item(
                Key={'algorithm': algorithm, 'interval': interval},
                UpdateExpression='set profit = :p',
                ExpressionAttributeValues={
                    ':p': int(queryData['Items'][0]['profit']) + int(profit),
                }
            )
    except Exception as e:
        print(e)
