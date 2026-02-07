import boto3
import json
from decimal import Decimal

# 1. DynamoDB 연결
dynamodb = boto3.resource(
    'dynamodb', 
    region_name='ap-northeast-2',
)
table = dynamodb.Table('Sejong_Restaurants')

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        # float(소수점)를 Decimal로 변환 (DynamoDB 필수 요구사항)
        return json.load(f, parse_float=Decimal)

def upload_data():
    print("파일을 읽는 중...")
    try:
        restaurants = load_json('restaurants.json')
        hours_data = load_json('operating_hours.json')
    except FileNotFoundError:
        print("Error: json 파일이 같은 폴더에 있는지 확인해주세요!")
        return

    # 2. 영업시간 데이터를 식당 ID 기준으로 정리 (Dictionary)
    # 예: { "10047142": [ {월요일...}, {화요일...} ] }
    hours_map = {}
    for hour in hours_data:
        r_id = str(hour['restaurant_id']) # ID를 문자열로 통일
        if r_id not in hours_map:
            hours_map[r_id] = []
        
        # 불필요한 필드 제거 (선택사항)
        del hour['restaurant_id'] 
        hours_map[r_id].append(hour)

    # 3. 식당 데이터에 영업시간 합치기 & 업로드
    print("데이터 업로드 시작 (시간이 좀 걸릴 수 있어요)...")
    
    with table.batch_writer() as batch:
        count = 0
        for r in restaurants:
            # ID 타입 통일 (문자열)
            r_id = str(r['id'])
            r['id'] = r_id 
            
            # 영업시간이 있으면 추가, 없으면 빈 리스트
            if r_id in hours_map:
                r['operating_hours'] = hours_map[r_id]
            else:
                r['operating_hours'] = []

            # DynamoDB에 저장 (빈 문자열 "" 처리)
            # DynamoDB는 빈 문자열을 허용하지 않는 경우가 있어 None으로 변환하거나 제거
            clean_item = {k: v for k, v in r.items() if v != ""}
            
            batch.put_item(Item=clean_item)
            count += 1
            if count % 100 == 0:
                print(f"{count}개 업로드 완료...")

    print(f"총 {count}개의 맛집 데이터 업로드 완료! 🎉")

if __name__ == '__main__':
    upload_data()