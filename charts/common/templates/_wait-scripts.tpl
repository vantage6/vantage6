{{/*
Reusable initContainer helper(s).

Library-chart templates can be consumed from dependent charts via `include`.
*/}}

{{/*
Arguments for an initContainer that waits for a component to become reachable
at a URL. Emitted as `args` for a container whose command is `curl`.

Deliberately shell-free: the hardened curl image ships no /bin/sh, so the wait
is expressed with curl's own retry flags instead of a polling loop.

Feedback in `kubectl logs`, since there is no shell to echo progress:
  - one line per failed attempt, from --show-error;
  - a closing line with the status, retry count and elapsed time;
  - an extra line naming the component when it never came up.

Input (dict):
  url               - URL to poll (required)
  label             - human-readable component label (default "Component")
  maxAttempts       - total attempts before failing (default 60)
  intervalSeconds   - delay between attempts (default 5)
*/}}
{{- define "common.waitForComponentReadyArgs" -}}
{{- $url := required "waitForComponentReadyArgs: 'url' is required" .url -}}
{{- $label := .label | default "Component" -}}
{{- $attempts := int (.maxAttempts | default 60) -}}
{{- $interval := int (.intervalSeconds | default 5) -}}
{{- /* --retry counts the retries *after* the first attempt, so drop that one. */ -}}
{{- $retries := max 0 (sub $attempts 1) -}}
{{- /* Text before %{onerror} is printed either way; only the tail is error-only. */ -}}
{{- $writeOut := printf "%%{stderr}Waited for %s at %%{url}: HTTP %%{http_code} after %%{num_retries} retries (%%{time_total}s)\\n%%{onerror}%s did not become ready, giving up (curl exit %%{exitcode}).\\n" $label $label -}}
- --fail
- --silent
- --show-error
- --connect-timeout
- {{ $interval | quote }}
- --max-time
- {{ add $interval 1 | quote }}
- --retry
- {{ $retries | quote }}
- --retry-delay
- {{ $interval | quote }}
{{- /* The target Service may not resolve at all yet on a fresh install, so
       retry DNS and HTTP errors too, not just the transient ones. */}}
- --retry-connrefused
- --retry-all-errors
- --output
- /dev/null
- --write-out
- {{ $writeOut | squote }}
- {{ $url | quote }}
{{- end -}}
