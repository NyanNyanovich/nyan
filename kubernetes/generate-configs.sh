#!/bin/bash

configs_dir="../configs"
kconfigs_dir="configs"
secret_names="client_config.json" # filenames to be treated as secrets

config_template=$(cat <<EOF
kind: ConfigMap
apiVersion: v1
metadata:
  name: <CMMAP>
  namespace: nyan
data:
  <FILENAME>: |
EOF
)

secret_template=$(cat <<EOF
kind: Secret
apiVersion: v1
metadata:
  name: <CMMAP>
  namespace: nyan
type: Opaque
data:
  <FILENAME>:
EOF
)

template_sed_f="<FILENAME>"
template_sed_c="<CMMAP>"
padding="    "

log() {
  echo "[LOG] $*"
}

assemble_config_from_file() {
  local source="$1"
  local destination="$2"
  if [[ ! -f "$source" ]]; then
    log "Assembly error: $source does not exist"
    return 1
  fi

  local config_contents
  config_contents=$(cat "$source")

  local padded_contents
  padded_contents=$(echo "$config_contents" | sed "s/^/$padding/")

  local prepared_template
  prepared_template=$(echo "$config_template" | \
    sed "s/$template_sed_f/$(basename "$source")/" | \
    sed "s/$template_sed_c/$(basename "$source" .json | sed 's/_/-/g')/")

  {
    echo "$prepared_template"
    echo "$padded_contents"
  } > "$destination"
}

assemble_secret_from_file() {
  local source="$1"
  local destination="$2"
  if [[ ! -f "$source" ]]; then
    log "Assembly error: $source does not exist"
    return 1
  fi

  local encoded
  encoded=$(base64 -w 0 "$source")

  local prepared_template
  prepared_template=$(echo "$secret_template" | \
    sed "s/$template_sed_f/$(basename "$source")/" | \
    sed "s/$template_sed_c/$(basename "$source" .json | sed 's/_/-/g')/")

  {
    echo "$prepared_template"
    echo "$padding$encoded"
  } > "$destination"
}

mkdir -p "$kconfigs_dir"

for config_json in "$configs_dir"/*.json; do
  [[ -f "$config_json" ]] || continue
  config_basename=$(basename "$config_json")
  config_name=$(basename "$config_json" .json).yaml

  if echo "$secret_names" | grep -qE "(^|\\|)$config_basename(\\||$)"; then
    log "Assembling $config_basename as Secret"
    assemble_secret_from_file "$config_json" "$kconfigs_dir/$config_name"
  else
    log "Assembling $config_basename as ConfigMap"
    assemble_config_from_file "$config_json" "$kconfigs_dir/$config_name"
  fi
done

if echo "$secret_names" | grep -qE "(^|\\|)channels.json(\\||$)"; then
  assemble_secret_from_file "../channels.json" "$kconfigs_dir/channels.yaml"
else
  assemble_config_from_file "../channels.json" "$kconfigs_dir/channels.yaml"
fi
