# Worker Lambda container (Python 3.11)
# Uses AWS Lambda base image with Runtime Interface Emulator for local invoke

# Stage 1: Builder with newer GCC for compiling numpy
# Use python:3.11-slim as builder (has GCC 12+ by default)
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Upgrade pip and install packages
# Install numpy explicitly first (crewai depends on it, and it needs proper compilation)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install \
        numpy \
        boto3 \
        crewai \
        crewai-tools \
        flask \
        google-api-python-client \
        google-auth \
        google-auth-httplib2 \
        google-auth-oauthlib \
        gspread \
        httpx \
        pymongo \
        dnspython \
        python-dotenv \
        python-json-logger \
        requests \
        requests-oauthlib \
        slack-sdk

# Stage 2: Runtime - copy packages from builder
FROM public.ecr.aws/lambda/python:3.11

# Copy installed packages from builder
COPY --from=builder /install/lib/python3.11/site-packages /var/lang/lib/python3.11/site-packages
COPY --from=builder /install/bin /var/lang/bin

# Copy application code so modules like 'services' resolve at package root
# Remove package metadata directories that can cause import conflicts
COPY src/ /var/task/
RUN rm -rf /var/task/ai_automation_with_slack.egg-info && \
    find /var/task -type d -name "__pycache__" | xargs rm -rf 2>/dev/null || true

# Optional: copy credentials and env (or mount them at runtime)
COPY google_credentials.json /var/task/google_credentials.json
COPY .env /var/task/.env

# Set the Lambda handler: module.function
# Our handler is defined in /var/task/lambda_handler.py as lambda_function
CMD ["lambda_handler.lambda_function"]
