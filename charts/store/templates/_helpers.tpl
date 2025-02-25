{{/*
Expand the name of the chart.
*/}}
{{- define "store.name" -}}
{{- include "common.name" (dict "Chart" .Chart "Values" .Values "Component" "store") -}}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "store.fullname" -}}
{{- include "common.fullname" (dict "Chart" .Chart "Release" .Release "Values" .Values "Component" "store") -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "store.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "store.labels" -}}
{{- include "common.labels" (dict "Chart" .Chart "Release" .Release "Component" "store") -}}
{{- end }}

{{/*
Match labels
*/}}
{{- define "store.matchLabels" -}}
{{- include "common.matchLabels" (dict "Chart" .Chart "Release" .Release "Component" "store") -}}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "store.selectorLabels" -}}
app.kubernetes.io/name: {{ include "store.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "store.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "store.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
