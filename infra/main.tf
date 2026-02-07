# 1. AWS 공급자 설정
provider "aws" {
  region = "ap-northeast-2"
}

# 2. 맛집 데이터 저장소 (DynamoDB)
resource "aws_dynamodb_table" "restaurants" {
  name           = "Sejong_Restaurants"
  billing_mode   = "PAY_PER_REQUEST" # 무료 티어 친화적
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# 3. 챗봇 백엔드 (Lambda)
# 주의: backend 폴더에 코드가 없으면 에러나므로 아래 단계에서 코드 생성 필요
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../backend"
  output_path = "lambda_function.zip"
}

resource "aws_lambda_function" "chatbot" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "sejong-chatbot-api"
  role             = aws_iam_role.iam_for_lambda.arn
  handler          = "index.lambda_handler" # 파일명.함수명
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Lambda가 DB 이름을 알 수 있게 환경변수로 주입
  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.restaurants.name
    }
  }
}

# 4. Lambda 권한 설정 (IAM Role)
resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Lambda가 DynamoDB와 로그에 접근할 수 있게 정책 연결
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.iam_for_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dynamodb_access" {
  name = "dynamodb_access"
  role = aws_iam_role.iam_for_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ]
      Effect   = "Allow"
      Resource = aws_dynamodb_table.restaurants.arn
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_access" {
  name = "bedrock_access"
  role = aws_iam_role.iam_for_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "bedrock:InvokeModel",
        "bedrock:ListFoundationModels"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

# 5. 외부 접속용 주소 생성 (Function URL - API Gateway 대체)
resource "aws_lambda_function_url" "chatbot_url" {
  function_name      = aws_lambda_function.chatbot.function_name
  authorization_type = "NONE" # 누구나 접속 가능 (CORS 설정 필요)
  
  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    expose_headers    = ["keep-alive", "date"]
    max_age           = 86400
  }
}

# 6. 결과 출력 (배포 후 URL 보여줌)
output "api_endpoint" {
  value = aws_lambda_function_url.chatbot_url.function_url
}