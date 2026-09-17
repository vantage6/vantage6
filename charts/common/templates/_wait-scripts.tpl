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
  - one line per failed attempt saying what went wrong;
  - one line per retry with the remaining countdown;
  - a closing line with the status and elapsed time;
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
{{- /*
The closing summary, in two halves. Everything up to %{onerror} is printed
whether or not the wait succeeded; the tail only when curl gives up.

%{num_retries} is deliberately not used here: it needs curl >= 8.9 and older
images print "unknown --write-out variable" in the middle of the line instead.
The per-retry countdown below already reports the attempt number.

%{time_total} covers the last attempt only, not the whole wait, hence the
wording: after 12 retries it still reports a fraction of a second.
*/ -}}
{{- $summary := printf "%%{stderr}%s at %%{url}: HTTP %%{http_code} (last attempt took %%{time_total}s)\\n" $label -}}
{{- $gaveUp := printf "%%{onerror}%s did not become ready, giving up (curl exit %%{exitcode}).\\n" $label -}}
# Treat HTTP errors as failures. --no-progress-meter rather than --silent: it
# drops the progress bar but keeps the per-retry countdown, which --silent hides.
- --fail
- --no-progress-meter
- --show-error
# Bound a single attempt, so attempts stay roughly on the configured interval.
- --connect-timeout
- {{ $interval | quote }}
- --max-time
- {{ add $interval 1 | quote }}
# Retry up to maxAttempts times. On a fresh install the target Service may not
# resolve at all yet, so retry DNS and connection errors too, not just the
# transient ones curl retries by default.
- --retry
- {{ $retries | quote }}
- --retry-delay
- {{ $interval | quote }}
- --retry-connrefused
- --retry-all-errors
# Discard the body; only reachability matters.
- --output
- /dev/null
- --write-out
- {{ printf "%s%s" $summary $gaveUp | squote }}
- {{ $url | quote }}
{{- end -}}
