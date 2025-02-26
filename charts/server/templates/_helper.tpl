{{/*
Expand the name of the chart.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
*/}}
{{- define "vantage6.name" -}}
{{- default "vantage6" .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vantage6.labels" -}}
app: {{ template "vantage6.name" . }}
release: {{ .Release.Name }}
heritage: {{ .Release.Service }}
chart: {{ .Chart.Name }}
version: {{ .Chart.Version }}
{{- end -}}


{{- define "vantage6.matchLabels" -}}
release: {{ .Release.Name }}
app: {{ template "vantage6.name" . }}
{{- end -}}
