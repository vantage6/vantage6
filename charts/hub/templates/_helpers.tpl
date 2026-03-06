{{/*
Helpers for the hub parent chart.
*/}}

{{- define "hub.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "hub.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "hub.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Resolve the TLS secret name for a component Ingress/Certificate.
Usage: {{ include "hub.tlsSecretName" (dict "ctx" . "component" "auth") }}
*/}}
{{- define "hub.tlsSecretName" -}}
{{- $ctx := .ctx -}}
{{- $component := .component -}}
{{- $hi := $ctx.Values.hubIngress | default (dict) -}}
{{- $tls := $hi.tls | default (dict) -}}
{{- $existing := $tls.existingSecrets | default (dict) -}}
{{- $override := (get $existing $component) | default "" -}}
{{- if ne (trim $override) "" -}}
{{- $override -}}
{{- else -}}
{{- printf "%s-%s-tls" $ctx.Release.Name $component -}}
{{- end -}}
{{- end }}
