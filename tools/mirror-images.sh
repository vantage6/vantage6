#!/usr/bin/env bash
#
# Copy the third-party support images listed in docker/mirror-images.txt into the
# vantage6 registry, tagged with the vantage6 version.
#
# Invoked through `make mirror-images`; see docker/mirror-images.txt for why we
# re-publish these images and why regctl is used instead of `docker dhi mirror`.
#
# Environment:
#   REGISTRY  target registry prefix (default ghcr.io/vantage6/infrastructure)
#   TAG       tag to publish under, i.e. the vantage6 version (required)
#   PUSH_REG  when not "true", resolve and report only; nothing is pushed
#
# regctl copies the whole multi-arch index plus the attached SBOM and provenance
# referrers, so the hardened-image guarantees survive the copy. `docker pull` +
# `docker push` would flatten the index to a single platform and drop them.
set -euo pipefail

REGISTRY="${REGISTRY:-ghcr.io/vantage6/infrastructure}"
TAG="${TAG:-}"
PUSH_REG="${PUSH_REG:-false}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
image_list="${script_dir}/../docker/mirror-images.txt"

if [ -z "${TAG}" ]; then
  echo "error: TAG is required, e.g. 'make mirror-images TAG=5.1.0'" >&2
  exit 1
fi

if ! command -v regctl >/dev/null 2>&1; then
  echo "error: regctl not found. See https://regclient.org/install/ to install it." >&2
  exit 1
fi

if [ ! -f "${image_list}" ]; then
  echo "error: image list not found at ${image_list}" >&2
  exit 1
fi

if [ "${PUSH_REG}" != "true" ]; then
  echo "PUSH_REG is not 'true': resolving sources only, nothing will be pushed."
fi

# Strip comments and blank lines, then read 'name upstream-reference' pairs.
while read -r name source _rest; do
  if [ -z "${name}" ] || [ -z "${source}" ]; then
    echo "error: malformed entry in ${image_list}: '${name} ${source}'" >&2
    exit 1
  fi

  # Copy by digest rather than by tag, so the image we publish is the one we
  # resolved even if the upstream tag moves mid-run.
  digest="$(regctl image digest "${source}")"
  target="${REGISTRY}/${name}:${TAG}"
  echo "${source} (${digest})"

  if [ "${PUSH_REG}" = "true" ]; then
    echo "  -> ${target}"
    regctl image copy --referrers --digest-tags "${source}@${digest}" "${target}"
  else
    echo "  -> ${target} (skipped, PUSH_REG != true)"
  fi
done < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "${image_list}")
