import boto3


def dynamo_record_create(simulation, create_at, project_name, algorithm, profit, price, buying, selling):
    """
    DynamoDBへログを送信（本番のみ）
    """
    if simulation:
        return

    try:
        dynamo_db = boto3.resource('dynamodb')

        # DynamoDBのテーブル名
        table_name = 'coincheck-auto-trade'
        table = dynamo_db.Table(table_name)

        table.put_item(
            Item={
                'create_at': create_at,  # 時刻
                'name': project_name,  # プロジェクト名
                'algorithm': algorithm,  # アルゴリズム
                'profit': int(profit),  # 利益
                'price': int(price),  # 終値
                'buying': str(buying),  # 買い注文実施
                'selling': str(selling),  # 売り注文実施
            }
        )
        print('Successful writing to DynamoDB!')
    except Exception as e:
        print(e)
