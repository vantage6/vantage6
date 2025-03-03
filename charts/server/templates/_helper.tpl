{{/*
Expand the name of the chart.
*/}}
{{- define "vantage6.name" -}}
{{- include "common.name" (dict "Chart" .Chart "Values" .Values "Component" "server") -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "vantage6.fullname" -}}
{{- include "common.fullname" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "server") -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "vantage6.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "vantage6.labels" -}}
{{- include "common.labels" (dict "Chart" .Chart "Release" .Release "Component" "server") -}}
{{- end }}

{{/*
Match labels
*/}}
{{- define "vantage6.matchLabels" -}}
{{- include "common.matchLabels" (dict "Chart" .Chart "Release" .Release "Component" "server") -}}
{{- end }}
