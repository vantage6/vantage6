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

{{/*
Kubernetes env-var suffix for a file-based database label (underscores only).
*/}}
{{- define "node.databaseEnvLabel" -}}
{{- .databaseName | replace "-" "_" | upper -}}
{{- end }}

{{/*
Kubernetes resource name for a file-based database volume.
*/}}
{{- define "node.databasePvName" -}}
{{- $name := printf "%s-db-pv-%s" .releaseName .databaseName -}}
{{- $name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Kubernetes resource name for a file-based database volume claim.
*/}}
{{- define "node.databasePvcName" -}}
{{- $name := printf "%s-db-pvc-%s" .releaseName .databaseName -}}
{{- $name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Returns "true" if .Values.node.taskNamespace already exists in the cluster and is Helm-owned
by a release other than this one (per its meta.helm.sh/release-name and
meta.helm.sh/release-namespace annotations), "false" otherwise.

A namespace that exists but carries no Helm ownership annotations at all (e.g. provisioned
by a platform team outside Helm, specifically for this node) is NOT treated as a collision —
only a namespace already claimed by a genuinely different release is. Multiple node releases
intentionally sharing one task namespace (e.g. for local development) is a supported,
non-default setup; see task-namespace.yml and NOTES.txt for how this is surfaced.

Requires the root context (.) as input. Relies on the `lookup` function, which only has
cluster access during `helm install`/`upgrade` — it returns nothing during offline
`helm template`, so this check is inert there.
*/}}
{{- define "node.taskNamespaceOwnedByOtherRelease" -}}
{{- $existingNs := lookup "v1" "Namespace" "" .Values.node.taskNamespace -}}
{{- $owned := false -}}
{{- if $existingNs -}}
  {{- $releaseName := "" -}}
  {{- $releaseNamespace := "" -}}
  {{- if $existingNs.metadata.annotations -}}
    {{- $releaseName = index $existingNs.metadata.annotations "meta.helm.sh/release-name" | default "" -}}
    {{- $releaseNamespace = index $existingNs.metadata.annotations "meta.helm.sh/release-namespace" | default "" -}}
  {{- end -}}
  {{- if and (ne $releaseName "") (or (ne $releaseName .Release.Name) (ne $releaseNamespace .Release.Namespace)) -}}
    {{- $owned = true -}}
  {{- end -}}
{{- end -}}
{{- if $owned }}true{{- else }}false{{- end -}}
{{- end }}

{{/*
Returns "true" if .Values.node.taskNamespace already exists in the cluster (regardless of
who owns it), "false" otherwise. Used to skip declaring the Namespace resource when it's
already there, rather than asking Helm to manage/adopt a resource that may not carry this
release's ownership metadata - Helm refuses to do that by default. See task-namespace.yml.
*/}}
{{- define "node.taskNamespaceExists" -}}
{{- if lookup "v1" "Namespace" "" .Values.node.taskNamespace }}true{{- else }}false{{- end -}}
{{- end }}
