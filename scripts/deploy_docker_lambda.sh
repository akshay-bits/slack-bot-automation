#!/bin/bash

# Two-Lambda Docker Deployment Script
# Deploys Gateway Lambda (webhooks) + Worker Lambda (business logic)
# Works on Intel Mac, M1/M2/M3 Mac, Linux, Windows WSL

set -e

# Configuration (customize for each project)
PROJECT_NAME="${PROJECT_NAME:-qa-slack-bot}"
GATEWAY_FUNCTION="${GATEWAY_FUNCTION:-${PROJECT_NAME}-gateway}"
WORKER_FUNCTION="${WORKER_FUNCTION:-${PROJECT_NAME}-worker}"
ECR_REPO_NAME="${ECR_REPO_NAME:-${PROJECT_NAME}}"
REGION="${AWS_REGION:-ap-south-1}"
MEMORY_SIZE="${MEMORY_SIZE:-512}"
TIMEOUT="${TIMEOUT:-300}"
WORKER_TIMEOUT="${WORKER_TIMEOUT:-900}"  # Worker needs more time for AI/DB operations

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "🚀 Starting Two-Lambda deployment for: ${PROJECT_NAME}"
echo "📍 Region: ${REGION}"
echo "🗃️ ECR URI: ${ECR_URI}"
echo "⚡ Gateway Function: ${GATEWAY_FUNCTION}"
echo "🔧 Worker Function: ${WORKER_FUNCTION}"

# Step 1: Setup Docker Buildx (for cross-platform builds)
echo "🔧 Setting up Docker buildx for cross-platform builds..."
docker buildx create --name lambda-builder --use --bootstrap 2>/dev/null || \
docker buildx use lambda-builder 2>/dev/null || \
echo "Buildx already configured"

# Step 2: Create ECR repository if it doesn't exist
echo "📦 Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${REGION} --output text > /dev/null 2>&1 || \
aws ecr create-repository --repository-name ${ECR_REPO_NAME} --region ${REGION} --output text

# Step 3: Login to ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Step 4: Build and push with proper platform targeting
echo "🔨 Building Docker image for AWS Lambda (linux/amd64)..."
echo "⚠️  This may take longer on M1/M2/M3 Macs due to platform emulation"

# Force linux/amd64 platform for Lambda compatibility
docker buildx build \
  --platform linux/amd64 \
  -t ${ECR_URI}:latest \
  --output type=image,push=true \
  . \
  --provenance=false \
  --sbom=false

echo "✅ Image successfully built and pushed to ECR"

# Step 5: Create or update IAM roles
echo "👤 Setting up IAM roles..."

# Gateway Lambda Role
GATEWAY_ROLE_NAME="${PROJECT_NAME}-gateway-role"
GATEWAY_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${GATEWAY_ROLE_NAME}"

# Worker Lambda Role
WORKER_ROLE_NAME="${PROJECT_NAME}-worker-role"
WORKER_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${WORKER_ROLE_NAME}"

# Create trust policy (same for both)
cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create Gateway Role (needs to invoke worker)
if ! aws iam get-role --role-name ${GATEWAY_ROLE_NAME} 2>/dev/null; then
    echo "Creating Gateway IAM role: ${GATEWAY_ROLE_NAME}"

    aws iam create-role \
        --role-name ${GATEWAY_ROLE_NAME} \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Basic Lambda execution
    aws iam attach-role-policy \
        --role-name ${GATEWAY_ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Create policy to invoke worker lambda
    cat > /tmp/gateway-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${WORKER_FUNCTION}"
        }
    ]
}
EOF

    aws iam put-role-policy \
        --role-name ${GATEWAY_ROLE_NAME} \
        --policy-name InvokeWorkerPolicy \
        --policy-document file:///tmp/gateway-policy.json

    echo "⏳ Waiting for gateway role to propagate..."
    sleep 10
else
    echo "Gateway IAM role already exists: ${GATEWAY_ROLE_NAME}"
fi

# Create Worker Role (needs full permissions for business logic)
if ! aws iam get-role --role-name ${WORKER_ROLE_NAME} 2>/dev/null; then
    echo "Creating Worker IAM role: ${WORKER_ROLE_NAME}"

    aws iam create-role \
        --role-name ${WORKER_ROLE_NAME} \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Basic Lambda execution
    aws iam attach-role-policy \
        --role-name ${WORKER_ROLE_NAME} \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    # Add any additional policies your worker needs (MongoDB, external APIs, etc.)
    # Example: AWS Secrets Manager for API keys
    # aws iam attach-role-policy \
    #     --role-name ${WORKER_ROLE_NAME} \
    #     --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

    echo "⏳ Waiting for worker role to propagate..."
    sleep 10
else
    echo "Worker IAM role already exists: ${WORKER_ROLE_NAME}"
fi

# Step 6: Deploy Gateway Lambda Function
echo "⚡ Creating/updating Gateway Lambda function..."

if aws lambda get-function --function-name ${GATEWAY_FUNCTION} 2>/dev/null; then
    echo "Updating existing Gateway Lambda function..."
    aws lambda update-function-code \
        --function-name ${GATEWAY_FUNCTION} \
        --image-uri ${ECR_URI}:latest

    echo "⏳ Waiting for gateway update to complete..."
    while true; do
        STATUS=$(aws lambda get-function-configuration --function-name ${GATEWAY_FUNCTION} --query 'LastUpdateStatus' --output text)
        if [[ "$STATUS" == "InProgress" ]]; then
            echo "⏳ Gateway update in progress..."
            sleep 5
        elif [[ "$STATUS" == "Successful" ]]; then
            echo "✅ Gateway Lambda update completed!"
            break
        else
            echo "❌ Gateway Lambda update failed with status: $STATUS"
            exit 1
        fi
    done

    # Update configuration
    aws lambda update-function-configuration \
        --function-name ${GATEWAY_FUNCTION} \
        --timeout ${TIMEOUT} \
        --memory-size ${MEMORY_SIZE}

else
    echo "Creating new Gateway Lambda function..."
    aws lambda create-function \
        --function-name ${GATEWAY_FUNCTION} \
        --package-type Image \
        --code ImageUri=${ECR_URI}:latest \
        --role ${GATEWAY_ROLE_ARN} \
        --timeout ${TIMEOUT} \
        --memory-size ${MEMORY_SIZE} \
        --image-config '{"Command": ["trigger_lambda.lambda_function"]}'
    
    # ADD THIS: Wait for creation to complete
    echo "⏳ Waiting for gateway creation to complete..."
    aws lambda wait function-active-v2 --function-name ${GATEWAY_FUNCTION}
    echo "✅ Gateway Lambda created!"
fi

# Step 7: Deploy Worker Lambda Function
echo "🔧 Creating/updating Worker Lambda function..."

if aws lambda get-function --function-name ${WORKER_FUNCTION} 2>/dev/null; then
    echo "Updating existing Worker Lambda function..."
    aws lambda update-function-code \
        --function-name ${WORKER_FUNCTION} \
        --image-uri ${ECR_URI}:latest

    echo "⏳ Waiting for worker update to complete..."
    while true; do
        STATUS=$(aws lambda get-function-configuration --function-name ${WORKER_FUNCTION} --query 'LastUpdateStatus' --output text)
        if [[ "$STATUS" == "InProgress" ]]; then
            echo "⏳ Worker update in progress..."
            sleep 5
        elif [[ "$STATUS" == "Successful" ]]; then
            echo "✅ Worker Lambda update completed!"
            break
        else
            echo "❌ Worker Lambda update failed with status: $STATUS"
            exit 1
        fi
    done

    # Update configuration
    aws lambda update-function-configuration \
        --function-name ${WORKER_FUNCTION} \
        --timeout ${WORKER_TIMEOUT} \
        --memory-size ${MEMORY_SIZE}

else
    echo "Creating new Worker Lambda function..."
    aws lambda create-function \
        --function-name ${WORKER_FUNCTION} \
        --package-type Image \
        --code ImageUri=${ECR_URI}:latest \
        --role ${WORKER_ROLE_ARN} \
        --timeout ${WORKER_TIMEOUT} \
        --memory-size ${MEMORY_SIZE} \
        --image-config '{"Command": ["lambda_handler.lambda_function"]}'
    
    echo "⏳ Waiting for worker creation to complete..."
    aws lambda wait function-active-v2 --function-name ${WORKER_FUNCTION}
    echo "✅ Worker Lambda created!"
fi

# Step 8: Set environment variables for both functions
if [ -f .env ]; then
    echo "🔧 Setting Lambda environment variables from .env..."
    
    # Wait to ensure both functions are ready for configuration updates
    echo "⏳ Ensuring functions are active..."
    aws lambda wait function-active-v2 --function-name ${GATEWAY_FUNCTION}
    aws lambda wait function-active-v2 --function-name ${WORKER_FUNCTION}

    # Read .env file and filter out reserved AWS variables
    BASE_ENV_JSON=$(python3 -c "
import json
env_vars = {}
reserved_keys = ['AWS_REGION', 'AWS_DEFAULT_REGION', 'AWS_EXECUTION_ENV', 
                 'AWS_LAMBDA_FUNCTION_NAME', 'AWS_LAMBDA_FUNCTION_MEMORY_SIZE',
                 'AWS_LAMBDA_FUNCTION_VERSION', 'LAMBDA_TASK_ROOT', 
                 'LAMBDA_RUNTIME_DIR', '_HANDLER', '_X_AMZN_TRACE_ID']

with open('.env', 'r') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            if key not in reserved_keys:
                env_vars[key] = value.strip()
print(json.dumps(env_vars))
    ")

    # Create Gateway environment JSON (add LAMBDA_HANDLER to base vars)
    ENV_JSON=$(echo "$BASE_ENV_JSON" | python3 -c "
import json
import sys
env_vars = json.loads(input())
env_vars['LAMBDA_HANDLER'] = '${WORKER_FUNCTION}'
print(json.dumps({'Variables': env_vars}))
    ")

    # Create Worker environment JSON (use base vars as-is)
    WORKER_ENV_JSON=$(echo "$BASE_ENV_JSON" | python3 -c "
import json
import sys
env_vars = json.loads(input())
print(json.dumps({'Variables': env_vars}))
    ")

    # Set environment for Gateway (includes LAMBDA_HANDLER)
    aws lambda update-function-configuration \
        --function-name ${GATEWAY_FUNCTION} \
        --environment "$ENV_JSON"

    # Set environment for Worker (without LAMBDA_HANDLER)
    aws lambda update-function-configuration \
        --function-name ${WORKER_FUNCTION} \
        --environment "$WORKER_ENV_JSON"
    
    echo "✅ Environment variables configured (reserved AWS vars filtered)"
fi

# Step 9: Create API Gateway ONLY for Gateway Lambda
echo "🌐 Setting up API Gateway for Gateway Lambda..."

API_NAME="${PROJECT_NAME}-api"

# Check if API already exists
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='${API_NAME}'].id" --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
    echo "Creating new API Gateway..."
    API_ID=$(aws apigateway create-rest-api --name ${API_NAME} --query 'id' --output text)

    # Get root resource
    ROOT_ID=$(aws apigateway get-resources --rest-api-id ${API_ID} --query 'items[0].id' --output text)

    # Create webhook resource
    RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id ${API_ID} \
        --parent-id ${ROOT_ID} \
        --path-part webhook \
        --query 'id' --output text)

    # Create POST method
    aws apigateway put-method \
        --rest-api-id ${API_ID} \
        --resource-id ${RESOURCE_ID} \
        --http-method POST \
        --authorization-type NONE

    # Set up Lambda integration (ONLY with Gateway Lambda)
    aws apigateway put-integration \
        --rest-api-id ${API_ID} \
        --resource-id ${RESOURCE_ID} \
        --http-method POST \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${GATEWAY_FUNCTION}/invocations"

    # Deploy API
    aws apigateway create-deployment \
        --rest-api-id ${API_ID} \
        --stage-name prod

    # Add Lambda permission (ONLY for Gateway Lambda)
    aws lambda add-permission \
        --function-name ${GATEWAY_FUNCTION} \
        --statement-id api-gateway-invoke \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/*" 2>/dev/null || echo "Permission already exists"
else
    echo "API Gateway already exists: ${API_ID}"
fi

API_URL="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/webhook"

# Step 10: Cleanup
rm -f /tmp/trust-policy.json /tmp/gateway-policy.json

# Step 11: Success summary
echo ""
echo "🎉 Two-Lambda Deployment completed successfully!"
echo ""
echo "📋 Architecture Details:"
echo "   🌐 Gateway Lambda: ${GATEWAY_FUNCTION} (handles webhooks)"
echo "   🔧 Worker Lambda: ${WORKER_FUNCTION} (business logic)"
echo "   📦 ECR Repository: ${ECR_REPO_NAME}"
echo "   🌍 Region: ${REGION}"
echo ""
echo "🔗 API Gateway URL: ${API_URL}"
echo ""
echo "🔄 Data Flow:"
echo "   1. Slack → API Gateway → Gateway Lambda"
echo "   2. Gateway Lambda → Validates & Deduplicates"
echo "   3. Gateway Lambda → Invokes Worker Lambda (async)"
echo "   4. Worker Lambda → AI/MongoDB/Business Logic"
echo ""
echo "📋 Next Steps:"
echo "   1. Use this URL in your Slack webhook configuration"
echo "   2. Test with Slack app mentions"
echo "   3. Monitor both functions in CloudWatch"
echo "   4. Scale worker memory/timeout as needed"
echo ""
echo "🔧 Function Handlers:"
echo "   Gateway: lambda_handler.lambda_function"
echo "   Worker: lambda_handler.lambda_function"
echo ""
