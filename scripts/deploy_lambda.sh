#!/bin/bash

# Deploy Q&A Slack Bot to AWS Lambda
set -e

# Configuration
FUNCTION_NAME="qa-slack-bot"
REGION="us-east-1"
ROLE_NAME="qa-slack-bot-role"
IMAGE_NAME="qa-slack-bot"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${IMAGE_NAME}"

echo "🚀 Starting deployment of Q&A Slack Bot..."
echo "Function Name: $FUNCTION_NAME"
echo "Region: $REGION"
echo "ECR URI: $ECR_URI"

# Step 1: Create ECR repository if it doesn't exist
echo "📦 Creating ECR repository..."
aws ecr describe-repositories --repository-names $IMAGE_NAME --region $REGION 2>/dev/null || \
aws ecr create-repository --repository-name $IMAGE_NAME --region $REGION

# Step 2: Get ECR login token
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Step 3: Build Docker image
echo "🔨 Building Docker image..."
docker build --platform linux/amd64 -t $IMAGE_NAME .

# Step 4: Tag and push image
echo "📤 Pushing image to ECR..."
docker tag $IMAGE_NAME:latest $ECR_URI:latest
docker push $ECR_URI:latest

# Step 5: Create IAM role if it doesn't exist
echo "👤 Setting up IAM role..."
if ! aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Creating IAM role..."
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
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
        }'

    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    echo "Waiting for role to be ready..."
    sleep 10
fi

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "Role ARN: $ROLE_ARN"

# Step 6: Create or update Lambda function
echo "⚡ Creating/updating Lambda function..."
if aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null; then
    echo "Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --image-uri $ECR_URI:latest

    # Wait for update to complete
    ./scripts/check_lambda_status.sh $FUNCTION_NAME

    # Update configuration
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 300 \
        --memory-size 512
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --package-type Image \
        --code ImageUri=$ECR_URI:latest \
        --role $ROLE_ARN \
        --timeout 300 \
        --memory-size 512
fi

# Step 7: Create API Gateway if it doesn't exist
echo "🌐 Setting up API Gateway..."
API_NAME="qa-slack-bot-api"

# Check if API exists
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text)

if [ -z "$API_ID" ] || [ "$API_ID" == "None" ]; then
    echo "Creating new API Gateway..."
    API_ID=$(aws apigateway create-rest-api --name $API_NAME --query 'id' --output text)

    # Get root resource ID
    ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query 'items[0].id' --output text)

    # Create resource
    RESOURCE_ID=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_ID \
        --path-part webhook \
        --query 'id' --output text)

    # Create POST method
    aws apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method POST \
        --authorization-type NONE

    # Set up integration
    aws apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $RESOURCE_ID \
        --http-method POST \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME/invocations"

    # Deploy API
    aws apigateway create-deployment \
        --rest-api-id $API_ID \
        --stage-name prod

    # Add Lambda permission for API Gateway
    aws lambda add-permission \
        --function-name $FUNCTION_NAME \
        --statement-id api-gateway-invoke \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*"

else
    echo "API Gateway already exists with ID: $API_ID"
fi

# Step 8: Get API Gateway URL
API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod/webhook"

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "1. Go to Slack API Event Subscriptions"
echo "2. Set Request URL to: $API_URL"
echo "3. Test your bot with: @BotName /ask What is Python?"
echo ""
echo "🔗 Useful URLs:"
echo "API Gateway URL: $API_URL"
echo "Lambda Function: https://console.aws.amazon.com/lambda/home?region=$REGION#/functions/$FUNCTION_NAME"
echo "API Gateway: https://console.aws.amazon.com/apigateway/home?region=$REGION#/apis/$API_ID"
