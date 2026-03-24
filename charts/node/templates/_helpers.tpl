{{/*
Expand the name of the chart.
*/}}
{{- define "node.name" -}}
{{- include "common.name" (dict "Chart" .Chart "Values" .Values "Component" "node") -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "node.fullname" -}}
{{- include "common.fullname" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "node") -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "node.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "node.labels" -}}
{{- include "common.labels" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "node") -}}
{{- end }}

{{/*
Match labels
*/}}
{{- define "node.matchLabels" -}}
{{- include "common.matchLabels" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "node") -}}
{{- end }}

