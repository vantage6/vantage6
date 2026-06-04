{{/*
Reusable initContainer helper script(s).

Library-chart templates can be consumed from dependent charts via `include`.
*/}}

{{- define "common.waitForComponentReadyScript" -}}
#!/bin/sh
# Wait for a component to become reachable at a URL.
# Env:
#   TARGET_URL         - URL to poll (required)
#   MAX_ATTEMPTS       - number of attempts before failing (default set by caller)
#   INTERVAL_SECONDS   - sleep between attempts (default set by caller)
#   WAIT_LABEL         - human-readable component label (required)
set -e

i=0
echo "Waiting for ${WAIT_LABEL} at ${TARGET_URL}..."

until curl -fsS --connect-timeout "${INTERVAL_SECONDS}" --max-time "$((INTERVAL_SECONDS+1))" "${TARGET_URL}" >/dev/null 2>&1; do
  i=$((i+1))
  if [ "$i" -ge "${MAX_ATTEMPTS}" ]; then
    echo "${WAIT_LABEL} not ready after ${i} attempts, giving up."
    exit 1
  fi
  echo "${WAIT_LABEL} not ready yet, attempt ${i}/${MAX_ATTEMPTS}..."
  sleep "${INTERVAL_SECONDS}"
done

echo "${WAIT_LABEL} is ready."
{{- end -}}

