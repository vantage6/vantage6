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
Return the single public hostname when the gateway routes all components on one host
(hubGateway.host), or an empty string when each component has its own hostname.
Usage: {{ include "hub.singleHost" . }}
*/}}
{{- define "hub.singleHost" -}}
{{- $hg := .Values.hubGateway | default (dict) -}}
{{- trim ($hg.host | default "") -}}
{{- end }}

{{/*
Resolve the path prefix under which the algorithm store API is served.
Usage: {{ include "hub.storeApiPath" . }}
*/}}
{{- define "hub.storeApiPath" -}}
{{- $storeValues := .Values.store | default (dict) -}}
{{- $storeCfg := $storeValues.store | default (dict) -}}
{{- trimSuffix "/" ($storeCfg.api_path | default "/store") -}}
{{- end }}

{{/*
Resolve the path prefix under which the HQ API is served.
Usage: {{ include "hub.hqApiPath" . }}
*/}}
{{- define "hub.hqApiPath" -}}
{{- $hqValues := .Values.hq | default (dict) -}}
{{- $hqCfg := $hqValues.hq | default (dict) -}}
{{- trimSuffix "/" ($hqCfg.apiPath | default "/hq") -}}
{{- end }}

{{/*
Resolve the TLS secret name for a component Ingress/Certificate.
Usage: {{ include "hub.tlsSecretName" (dict "ctx" . "component" "auth") }}
*/}}
{{- define "hub.tlsSecretName" -}}
{{- $ctx := .ctx -}}
{{- $component := .component -}}
{{- $hg := $ctx.Values.hubGateway | default (dict) -}}
{{- $tls := $hg.tls | default (dict) -}}
{{- $existing := $tls.existingSecrets | default (dict) -}}
{{- $override := (get $existing $component) | default "" -}}
{{- if ne (trim $override) "" -}}
{{- $override -}}
{{- else -}}
{{- printf "%s-%s-tls" $ctx.Release.Name $component -}}
{{- end -}}
{{- end }}
