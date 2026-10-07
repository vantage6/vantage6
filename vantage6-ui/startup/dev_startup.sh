#!/bin/sh

# This script is used to start the UI development environment. It's main function is to ensure that
# the contents of the env.js file are updated when the environment variables change.
# This is not trivial because the upload sync from devspace does otherwise not trigger
# a restart of the container.
# If the env.js file is updated, the UI is restarted.

echo "=== Starting UI development environment (dev_startup.sh) ==="

# Function to generate env.js
generate_env_js() {
    envsubst < /app/src/assets/env.template.js > /app/src/assets/env.js
}

get_env_var_value() {
    env_var_name=$1
    printenv | grep "^$env_var_name=" | cut -d'=' -f2
}

get_env_var_value_from_env_js() {
    env_var_name=$1
    grep "\[\"$env_var_name\"\]" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2
}

# Function to get environment variables hash
get_env_hash() {
    env_api_path=$(get_env_var_value "API_PATH")
    env_hq_url=$(get_env_var_value "HQ_URL")
    env_keycloak_realm=$(get_env_var_value "KEYCLOAK_REALM")
    env_keycloak_client=$(get_env_var_value "KEYCLOAK_CLIENT")
    env_auth_url=$(get_env_var_value "AUTH_URL")
    echo "$env_api_path$env_hq_url$env_keycloak_realm$env_keycloak_client$env_auth_url" | md5sum | cut -d' ' -f1
}

# Function to get environment variables hash from env.js
get_env_hash_from_env_js() {
    envjs_api_path=$(get_env_var_value_from_env_js "api_path")
    envjs_hq_url=$(get_env_var_value_from_env_js "hq_url")
    envjs_keycloak_realm=$(get_env_var_value_from_env_js "keycloak_realm")
    envjs_keycloak_client=$(get_env_var_value_from_env_js "keycloak_client")
    envjs_auth_url=$(get_env_var_value_from_env_js "auth_url")
    echo "$envjs_api_path$envjs_hq_url$envjs_keycloak_realm$envjs_keycloak_client$envjs_auth_url" | md5sum | cut -d' ' -f1
}

# Generate env.js initially
generate_env_js

# Start ng serve in the background
echo "Starting UI..."
cd /app
ng serve --host 0.0.0.0 --port 80 &
UI_PROCESS_ID=$!

# infinite loop to keep updating the environment variables when necessary
echo "Starting environment variable monitor..."
ENV_HASH=$(get_env_hash)
while true; do
    sleep 10
    ENVJS_HASH=$(get_env_hash_from_env_js)
    if [ "$ENVJS_HASH" != "$ENV_HASH" ]; then
        echo "Env.js outdated, regenerating env.js and restarting ng serve..."

        # Kill existing ng serve process
        if kill -0 $UI_PROCESS_ID 2>/dev/null; then
            kill $UI_PROCESS_ID
            wait $UI_PROCESS_ID 2>/dev/null
        fi

        # Regenerate env.js
        generate_env_js

        # Start new ng serve process
        echo "Restarting UI..."
        ng serve --host 0.0.0.0 --port 80 &
        UI_PROCESS_ID=$!
    fi

    # Check if ng serve is still running
    if ! kill -0 $UI_PROCESS_ID 2>/dev/null; then
        echo "UI's main process died, exiting..."
        break
    fi
done