{{- define "moogla.name" -}}
moogla
{{- end -}}

{{- define "moogla.fullname" -}}
{{ include "moogla.name" . }}
{{- end -}}
