#!/bin/bash
set -e

# Function to get value from secrets manager using secret name, key name and output type
function get_secret_value() {
	local secret_name="$1" key="$2" form="$3"
  	: "${json_secret:=$(aws secretsmanager get-secret-value --secret-id ${secret_name} --region ${AWS_REGION} --output ${form} --query "SecretString")}"
  	# If key name is provided, parse json output for the key or return text output
  	if [ -z "$key" ];
  	then
  		echo $json_secret
  	else
  		: "${value:=$(echo ${json_secret} | jq -r 'fromjson | ."'${key}'"')}"
 		echo $value
 	fi
}

echo "Fetching variables from aws store.."
SECRET_OPENAI="${PROJECT_NAME}-${ENV}-openai-key"
SECRET_GEMINI="${PROJECT_NAME}-${ENV}-gemini-key"

echo $SECRET_OPENAI
echo $SECRET_GEMINI

export OPENAI_API_KEY=$(get_secret_value ${SECRET_OPENAI} "" "text")
export GEMINI_API_KEY=$(get_secret_value ${SECRET_GEMINI} "" "text")
exec litellm "$@"
