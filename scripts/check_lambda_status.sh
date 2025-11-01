#!/bin/bash
# Check the Lambda update status
function check_lambda_status() {
local FUNCTION_NAME=$1
while true; do
STATUS=$(aws lambda get-function-configuration --function-name "$FUNCTION_NAME" --query 'LastUpdateStatus' --output text)
if [[ "$STATUS" == "InProgress" ]]; then
echo "Waiting for Lambda code update to finish... (current status: $STATUS)"
sleep 5
elif [[ "$STATUS" == "Successful" ]]; then
echo "Lambda code update completed successfully!"
break
else
echo "Lambda code update failed with status: $STATUS"
exit 1 # Fail the pipeline if the update isn't in progress or successful
fi
done
}
# Call the function with the provided function name argument
check_lambda_status "$1"
