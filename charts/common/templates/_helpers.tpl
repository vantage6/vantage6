{{/*
Expand the name of the chart.
Usage: {{ include "common.name" (dict "Chart" .Chart "Values" .Values "Component" "node") }}
*/}}
{{- define "common.name" -}}
{{- $ctx := . -}}
{{- default $ctx.Chart.Name $ctx.Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
Usage: {{ include "common.fullname" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "node") }}
*/}}
{{- define "common.fullname" -}}
{{- $ctx := . -}}
{{- if $ctx.Values.fullnameOverride }}
{{- $ctx.Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default $ctx.Chart.Name $ctx.Values.nameOverride }}
{{- if contains $name $ctx.Release.Name }}
{{- $ctx.Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" $ctx.Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Common labels
Usage: {{ include "common.labels" (dict "Chart" .Chart "Release" .Release "Component" "node") }}
*/}}
{{- define "common.labels" -}}
{{- $ctx := . -}}
app: {{ include "common.name" $ctx }}
release: {{ $ctx.Release.Name }}
heritage: {{ $ctx.Release.Service }}
chart: {{ $ctx.Chart.Name }}
version: {{ $ctx.Chart.Version }}
{{- end }}

{{/*
Match labels
Usage: {{ include "common.matchLabels" (dict "Chart" .Chart "Release" .Release "Component" "node") }}
*/}}
{{- define "common.matchLabels" -}}
{{- $ctx := . -}}
app: {{ include "common.name" $ctx }}
release: {{ $ctx.Release.Name }}
{{- end }}

{{/*
Reference to a third-party support image (curl, kubectl, ...). These are
re-published from their upstream registry into the vantage6 registry on every
release and tagged with the vantage6 version, so a chart always pulls the copy
it was tested against. See docker/mirror-images.txt.

Pass 'override' to use a different image, e.g. one from an internal registry.

Usage: {{ include "common.supportImage" (dict "Chart" .Chart "name" "curl" "override" $cfg.image) }}
*/}}
{{- define "common.supportImage" -}}
{{- if .override -}}
{{ .override }}
{{- else -}}
{{ printf "ghcr.io/vantage6/infrastructure/%s:%s" .name .Chart.AppVersion }}
{{- end -}}
{{- end }}

{{/*
Image pull secrets from global.imagePullSecrets, if any. Only needed when images
are pulled from a registry that requires authentication, e.g. when the support
images have been overridden to point at an internal mirror.

The helper indents itself and renders nothing at all when no secrets are set, so
it leaves no stray blank line behind.

Usage (as the first entry of a pod spec):
    {{- include "common.imagePullSecrets" (dict "Values" .Values "indent" 6) }}
*/}}
{{- define "common.imagePullSecrets" -}}
{{- $secrets := (.Values.global | default dict).imagePullSecrets -}}
{{- if $secrets -}}
{{- printf "imagePullSecrets:\n%s" (toYaml $secrets | trimSuffix "\n") | nindent (int .indent) -}}
{{- end -}}
{{- end }}
