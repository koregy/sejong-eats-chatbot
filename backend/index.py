import json
import boto3
import os
import random
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# --- 설정 ---
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Sejong_Restaurants')
table = dynamodb.Table(TABLE_NAME)

# AI 클라이언트
try:
    bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
    AI_AVAILABLE = True
except Exception as e:
    print(f"Bedrock 설정 실패: {e}")
    AI_AVAILABLE = False

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    print("[DEBUG] 요청 들어옴:", json.dumps(event))

    # 1. CORS 처리
    method = event.get('requestContext', {}).get('http', {}).get('method')
    if method == 'OPTIONS':
        return create_response(200, "CORS OK")

    # 2. 데이터 파싱
    body = {}
    try:
        if event.get('body'):
            body = json.loads(event['body'])
        elif event.get('queryStringParameters'):
            body = event.get('queryStringParameters')
    except:
        pass

    # 3. 상세 정보 요청 처리
    if body.get('restaurant_id'):
        return get_restaurant_details(body['restaurant_id'])

    # 4. 채팅/검색 요청 처리
    user_msg = body.get('message', '')
    if user_msg:
        return handle_chat(user_msg)

    return create_response(200, {"message": "서버는 살아있는데, 메시지가 비어있어요."})

# --- 핵심 로직 ---

def handle_chat(user_msg):
    # 1단계: AI에게 키워드 추출 요청 (식당 이름 우선)
    keyword = extract_keyword_with_ai(user_msg)
    print(f"AI가 추출한 키워드: {keyword}")

    # 2단계: 추출한 키워드로 DB 검색
    restaurants = search_db(keyword)
    
    # 3단계: 결과가 0개라면? 사용자 문장으로 직접 재검색
    if not restaurants:
        print("AI 키워드 검색 실패 -> 직접 검색 시도")
        # '추천', '맛집' 같은 불필요한 단어 제거 후 검색
        cleaned_msg = clean_message(user_msg)
        if cleaned_msg:
            restaurants = search_db(cleaned_msg)

    # 4단계: 결과 반환
    if restaurants:
        # 랜덤 섞기
        random.shuffle(restaurants)
        return create_response(200, {
            "message": f"'{keyword}' 관련 맛집을 찾아봤어요! 😋",
            "restaurants": restaurants[:5]
        })
    else:
        fallback_msg = get_ai_fallback_message(user_msg)
        return create_response(200, {"message": fallback_msg})

def extract_keyword_with_ai(text):
    if not AI_AVAILABLE:
        return text 

    try:
        # 프롬프트: 식당 이름을 최우선으로 하도록 지시
        prompt = f"""
        Human: 사용자가 맛집을 찾고 있어. 다음 문장에서 검색에 사용할 핵심 단어 하나만 추출해줘.
        
        [우선순위]
        1. '식당 이름'이 있다면 무조건 식당 이름을 추출해. (예: "신안골분식 가고싶어" -> "신안골분식")
        2. 식당 이름이 없다면 '메뉴'나 '음식 종류'를 추출해. (예: "매운거 추천해줘" -> "매운")
        
        설명 없이 단어만 딱 출력해.
        
        문장: "{text}"
        
        Assistant:"""

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": prompt}]
        })

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0", 
            body=body
        )
        
        result = json.loads(response['body'].read())
        extracted_word = result['content'][0]['text'].strip()
        
        return extracted_word.replace('"', '').replace("'", "")

    except Exception as e:
        print(f"AI 키워드 추출 실패: {e}")
        return text

def clean_message(text):
    """직접 검색을 위해 불필요한 조사/단어 제거"""
    remove_words = ["추천", "해줘", "맛집", "어디", "알려줘", "있어?", "가고싶어", "검색", "좀"]
    cleaned = text
    for word in remove_words:
        cleaned = cleaned.replace(word, "")
    return cleaned.strip()

def search_db(keyword):
    """DB에서 키워드로 검색"""
    print(f"DB 검색 시작: {keyword}")
    if len(keyword) < 1: return [] # 키워드가 너무 짧으면 검색 안함

    try:
        response = table.scan()
        items = response.get('Items', [])
        
        results = []
        target_keyword = keyword.replace(" ", "") 
        
        for item in items:
            name = item.get('place_name', item.get('name', ''))
            cat = item.get('main_category', item.get('category', ''))
            desc = item.get('description', '')
            
            # 검색 로직: 이름, 카테고리, 설명에서 찾기
            if (target_keyword in name.replace(" ", "") or 
                target_keyword in cat.replace(" ", "") or 
                target_keyword in desc.replace(" ", "")):
                
                results.append({
                    "id": item.get('id'),
                    "place_name": name,
                    "main_category": cat,
                    "road_address_name": item.get('road_address_name', ''),
                    "scraped_rating": item.get('scraped_rating', '0.0'),
                    "description": desc,
                    "operating_hours_summary": "상세보기",
                    "place_url": item.get('place_url', '')
                })
        
        return results
    except Exception as e:
        print(f"DB 에러: {e}")
        return []

def get_ai_fallback_message(user_msg):
    if not AI_AVAILABLE:
        return f"'{user_msg}'에 대한 정보를 못 찾겠어요 ㅠㅠ"
        
    try:
        prompt = f"""
        Human: 사용자가 "{user_msg}"라고 물었는데 검색 결과가 없어. 
        데이터베이스에 없는 식당이거나 메뉴인 것 같아.
        친절하게 위로해주고, "한식, 중식, 양식, 치킨" 중에서 골라달라고 짧게 한 문장으로 말해줘.
        Assistant:"""
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        })
        
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
    except:
        return "검색 결과가 없어요. 다른 메뉴를 추천해드릴까요?"

def get_restaurant_details(r_id):
    try:
        response = table.get_item(Key={'id': str(r_id)})
        item = response.get('Item')
        if not item: return create_response(404, {"message": "정보 없음"})
        if 'operating_hours' not in item: item['operating_hours'] = []
        return create_response(200, item)
    except:
        return create_response(500, {"message": "조회 실패"})

def create_response(status, body):
    return {
        'statusCode': status,
        'headers': {
            'Content-Type': 'application/json',
        },
        'body': json.dumps(body, cls=DecimalEncoder, ensure_ascii=False)
    }