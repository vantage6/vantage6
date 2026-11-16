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
Labels of the node pod. Algorithm pods use these for pod affinity and network policies.
*/}}
{{- define "node.podLabels" -}}
{{ include "node.matchLabels" . }}
component: node
{{- end }}

{{/*
Labels that the node puts on every pod it starts for algorithm runs. Must match
ContainerManager.algorithm_pod_labels.
*/}}
{{- define "node.algorithmPodLabels" -}}
v6-pod-type: algorithm
v6-node-release: {{ .Release.Name }}
{{- end }}

{{- define "node.namespace" -}}
{{- .Values.namespace | default .Release.Namespace -}}
{{- end }}

{{- define "node.serviceAccountName" -}}
{{- if .Values.node.serviceAccount.create -}}
{{- printf "%s-sa" .Release.Name -}}
{{- else -}}
{{- required "node.serviceAccount.name is required when node.serviceAccount.create is false" .Values.node.serviceAccount.name -}}
{{- end -}}
{{- end }}

{{/*
Static (host path) storage is only meant for single-machine development clusters.
*/}}
{{- define "node.tasksStatic" -}}
{{- if .Values.node.persistence.tasks.hostPath }}true{{ end -}}
{{- end }}

{{- define "node.logsStatic" -}}
{{- if .Values.node.logging.volumeHostPath }}true{{ end -}}
{{- end }}

{{- define "node.databasesStatic" -}}
{{- range .Values.node.databases.fileBased }}{{ if and .volumePath (not .existingClaim) }}true{{ end }}{{ end -}}
{{- end }}

{{- define "node.taskClaimName" -}}
{{- .Values.node.persistence.tasks.existingClaim | default (printf "%s-task-pvc" .Release.Name) -}}
{{- end }}

{{- define "node.logsClaimName" -}}
{{- .Values.node.logging.existingClaim | default (printf "%s-logs-pvc" .Release.Name) -}}
{{- end }}

{{/*
Kubernetes env-var suffix for a file-based database label (underscores only).
*/}}
{{- define "node.databaseEnvLabel" -}}
{{- .databaseName | replace "-" "_" | upper -}}
{{- end }}

{{/*
Kubernetes resource name for a dev-only host path database volume.
*/}}
{{- define "node.databasePvName" -}}
{{- $name := printf "%s-db-pv-%s" .releaseName .databaseName -}}
{{- $name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Kubernetes resource name for a dev-only host path database volume claim.
*/}}
{{- define "node.databasePvcName" -}}
{{- $name := printf "%s-db-pvc-%s" .releaseName .databaseName -}}
{{- $name | trunc 63 | trimSuffix "-" -}}
{{- end }}

{{/*
Claim that holds a file-based database: the user's existing claim, or in dev mode the
claim on top of the host path volume.
Usage: include "node.databaseClaimName" (dict "releaseName" .Release.Name "db" $db)
*/}}
{{- define "node.databaseClaimName" -}}
{{- if .db.existingClaim -}}
{{- .db.existingClaim -}}
{{- else if .db.volumePath -}}
{{- include "node.databasePvcName" (dict "releaseName" .releaseName "databaseName" .db.name) -}}
{{- else -}}
{{- fail (printf "File-based database '%s' needs 'existingClaim' (or 'volumePath' in development)" .db.name) -}}
{{- end -}}
{{- end }}

{{/*
Path of a file-based database inside its claim.
*/}}
{{- define "node.databaseSubPath" -}}
{{- .db.subPath | default .db.originalName | default "" -}}
{{- end }}
