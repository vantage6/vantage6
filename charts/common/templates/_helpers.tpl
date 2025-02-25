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