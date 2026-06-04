{{/*
Expand the name of the chart.
*/}}
{{- define "auth.name" -}}
{{- include "common.name" (dict "Chart" .Chart "Values" .Values "Component" "auth") -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "auth.fullname" -}}
{{- include "common.fullname" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "auth") -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "auth.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "auth.labels" -}}
{{- include "common.labels" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "auth") -}}
{{- end }}

{{/*
Match labels
*/}}
{{- define "auth.matchLabels" -}}
{{- include "common.matchLabels" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "auth") -}}
{{- end }}
