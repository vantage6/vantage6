#!/bin/sh

# This script is used to start the UI dev server. It's main function is to ensure that
# the contents of the env.js file are updated when the environment variables change.
# This is not trivial because the upload sync from devspace does otherwise not trigger
# a restart of the container.
# If the env.js file is updated, the UI is restarted.

echo "=== Starting UI dev server (dev_startup.sh) ==="

# Function to generate env.js
generate_env_js() {
    envsubst < /app/src/assets/env.template.js > /app/src/assets/env.js
}

# Function to get environment variables hash
get_env_hash() {
    env_keycloak_realm=$(printenv | grep "KEYCLOAK_REALM" | cut -d'=' -f2)
    env_keycloak_client=$(printenv | grep "KEYCLOAK_CLIENT" | cut -d'=' -f2)
    env_auth_url=$(printenv | grep "AUTH_URL" | cut -d'=' -f2)
    echo "$env_keycloak_realm$env_keycloak_client$env_auth_url" | md5sum | cut -d' ' -f1
}

# Function to get environment variables hash from env.js
get_env_hash_from_env_js() {
    envjs_keycloak_realm=$(grep "keycloak_realm" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    envjs_keycloak_client=$(grep "keycloak_client" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    envjs_auth_url=$(grep "auth_url" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    # envjs_api_url=$(grep "api_url" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    # envjs_server_url=$(grep "server_url" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    # envjs_api_path=$(grep "api_path" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    # envjs_allowed_algorithm_stores=$(grep "allowed_algorithm_stores" /app/src/assets/env.js | cut -d'=' -f2 | cut -d'"' -f2)
    echo "$envjs_keycloak_realm$envjs_keycloak_client$envjs_auth_url" | md5sum | cut -d' ' -f1
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