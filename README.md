## Sejong Eats Chatbot
AWS Serverless 아키텍처와 생성형 AI(Amazon Bedrock)를 활용하여 구축한 고려대학교 세종캠퍼스 주변 맛집 추천 챗봇 서비스입니다.
Terraform을 이용한 IaC(Infrastructure as Code)를 구현하여 인프라의 자동 배포 및 관리가 가능하며, 자연어 처리(NLP)를 통해 사용자의 의도를 파악하고 맞춤형 식당 정보를 제공합니다.

## 실행 화면 (Demo)
demo1.png
demo2.png

## 시스템 아키텍처
사용자의 요청은 웹 프론트엔드에서 AWS Lambda로 전달되며, Lambda 내부에서 AI 모델(Claude 3)과 데이터베이스(DynamoDB)를 참조하여 최적의 응답을 생성합니다.

```mermaid
graph LR
    User[사용자] -->|Web Chat| Frontend[Frontend (HTML/JS)]
    Frontend -->|REST API| LambdaURL[AWS Lambda Function URL]
    LambdaURL --> Lambda[Backend Lambda (Python)]
    Lambda -->|Intent Analysis| Bedrock[Amazon Bedrock (Claude 3)]
    Lambda -->|Query Data| DynamoDB[(Amazon DynamoDB)]

기술 스택 (Tech Stack)
Infrastructure
- Terraform: AWS 리소스(Lambda, DynamoDB, IAM, Function URL)의 프로비저닝 및 상태 관리
- AWS Serverless: 서버 관리 부담이 없는 Lambda 기반 컴퓨팅 환경 구축

Backend & AI
- Python 3.12: 비즈니스 로직 및 데이터 처리
- Amazon Bedrock (Claude 3): 자연어 기반 사용자 의도 분석 및 키워드 추출
- Amazon DynamoDB: NoSQL 기반의 식당 데이터 및 리뷰 저장소

Frontend
- HTML5 / JavaScript (Vanilla): 외부 라이브러리 의존성을 최소화한 경량 웹 클라이언트
- Tailwind CSS: 유틸리티 퍼스트 기반의 반응형 UI 디자인

주요 기능
1. AI 기반 자연어 검색
- 단순 키워드 매칭이 아닌, 문맥을 이해하는 검색을 지원합니다.
- 예: "매운 국물 요리 추천해줘" -> "매운", "국물" 키워드 추출 및 검색
2. 실시간 데이터 조회
- DynamoDB를 통해 빠르고 확장성 있는 데이터 읽기/쓰기를 지원합니다.
3. 위치 기반 서비스 연동
- 추천된 식당의 카카오맵 URL을 제공하여 즉각적인 길 찾기 및 위치 확인이 가능합니다.
4. 랜덤 추천 알고리즘
- 검색 결과 내에서 무작위 셔플링을 통해 사용자에게 다양한 선택지를 제안합니다.

프로젝트 구조
sejong_eats_v2/
├── backend/
│   └── index.py            # AWS Lambda 메인 핸들러 (비즈니스 로직)
├── frontend/
│   └── index.html          # 웹 클라이언트 UI
├── infra/
│   ├── main.tf             # Terraform 메인 설정 파일
│   ├── variables.tf        # 변수 정의
│   └── outputs.tf          # 출력 값 정의
├── restaurants.json        # 초기 데이터셋 (식당 정보)
├── operating_hours.json    # 초기 데이터셋 (영업 시간)
└── upload_real_data.py     # 데이터 마이그레이션 스크립트

설치 및 배포 (Deployment)
이 프로젝트는 Terraform을 사용하여 AWS 환경에 자동으로 배포됩니다.

1. 사전 요구 사항
- AWS CLI 설정 (Access Key, Secret Key)
- Terraform 설치
- Python 3.12 설치

2. 인프라 배포
Terraform을 초기화하고 AWS 리소스를 생성합니다.
cd infra
terraform init
terraform plan
terraform apply
- 배포 완료 후 출력되는 function_url을 복사하여 프론트엔드 설정에 사용합니다.

3. 데이터 마이그레이션
로컬의 JSON 데이터를 DynamoDB 테이블로 업로드합니다.
# 프로젝트 루트 디렉토리에서 실행
python upload_real_data.py

4. 프론트엔드 설정
frontend/index.html 파일을 열고, 코드 상단 API_URL 상수에 Terraform 배포 결과로 얻은 URL을 입력합니다.

## 추후 개선 계획 (Future Roadmap)
현재 버전은 초기 모델(MVP)로서 핵심 기능 구현에 집중하였으며, 향후 다음과 같은 고도화 작업을 진행할 예정입니다.

1.  **검색 알고리즘 최적화**
    * 현재의 키워드 매칭 방식을 넘어, RAG (Retrieval-Augmented Generation) 기법을 도입하여 문맥 기반의 검색 정확도를 향상
    * 사용자 피드백(검색 결과 클릭률 등)을 반영한 추천 랭킹 알고리즘 개발

2.  **데이터 확장 및 자동화**
    * 교내 학생 식당(학식) 메뉴 데이터 크롤링 및 연동
    * 사용자가 직접 식당 정보 수정 요청을 보낼 수 있는 제보 기능 추가

3.  **사용자 경험(UX) 개선**
    * 검색 결과가 없을 경우, AI가 대체 메뉴를 제안하는 시나리오 고도화
    * 메뉴 결정이 어려운 사용자를 위한 '랜덤 룰렛' 기능 추가