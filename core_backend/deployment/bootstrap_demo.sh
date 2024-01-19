#!/bin/bash
set -e

# Function to add any cleanup actions
function cleanup() {
	echo "Cleanup."
}
trap cleanup EXIT

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

# This is the name of the secret in aws secrets manager
SECRET_JWT="aaq-demo-jwt-secret"
SECRET_CONTENT="aaq-demo-content-access"
SECRET_WHATSAPP_VERIFY="aaq-demo-whatsapp-verify-token"
SECRET_WEB_DB_CONNECTION="aaq-demo-web-db-connection-details"
SECRET_WHATSAPP="aaq-demo-whatsapp-token"
SECRET_OPENAI="aaq-demo-open-ai-key"
SECRET_QUESTION_ANSWER="aaq-demo-question-answer"

export NEXT_PUBLIC_BACKEND_URL="${NEXT_PUBLIC_API_URL}"
export JWT_SECRET=$(get_secret_value ${SECRET_JWT} "" "text")

# Set password for user for `fullaccess` and `readonly` account to access content
export CONTENT_FULLACCESS_PASSWORD=$(get_secret_value ${SECRET_CONTENT} "full_access_password" "json")
export CONTENT_READONLY_PASSWORD=$(get_secret_value ${SECRET_CONTENT} "read_only_password" "json")

export WHATSAPP_TOKEN=$(get_secret_value ${SECRET_WHATSAPP} "" "text")
export WHATSAPP_VERIFY_TOKEN=$(get_secret_value ${SECRET_WHATSAPP_VERIFY} "" "text")
export OPENAI_API_KEY=$(get_secret_value ${SECRET_OPENAI} "" "text")
export QUESTION_ANSWER_SECRET=$(get_secret_value ${SECRET_QUESTION_ANSWER} "" "text")

# if using a nginx reverse proxy, set path here
BACKEND_ROOT_PATH="/api"

# Postgres instance endpoint
export POSTGRES_HOST=$(get_secret_value ${SECRET_WEB_DB_CONNECTION} "host" "json")
export POSTGRES_PORT=$(get_secret_value ${SECRET_WEB_DB_CONNECTION} "port" "json")
export POSTGRES_USER=$(get_secret_value ${SECRET_WEB_DB_CONNECTION} "username" "json")
export POSTGRES_PASSWORD=$(get_secret_value ${SECRET_WEB_DB_CONNECTION} "password" "json")
export POSTGRES_DB=$(get_secret_value ${SECRET_WEB_DB_CONNECTION} "dbname" "json")




export PROMETHEUS_MULTIPROC_DIR="/tmp"

DOMAIN="${DOMAIN}"

# Resolve Qdrant host
SERVICE_RECORD=$(dig +short SRV ${QDRANT_HOST})

read -r PRIORITY WEIGHT PORT HOST <<< "$(echo $SERVICE_RECORD | cut -d' ' -f 1-4)"

# Strip the trailing dot of the host if necessary
HOST=${HOST%.}

# Get the IP address of the host (assuming the hostname resolves to an IP address)
IP=$(dig +short A $HOST)
export QDRANT_HOST="${IP}"

exec "$@"