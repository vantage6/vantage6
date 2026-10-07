#!/usr/bin/env bash
#
# Copy the third-party support images listed in docker/mirror-images.txt into the
# vantage6 registry, tagged with the vantage6 version. With FLOATING_TAGS=true a
# release also moves the major.minor and latest tags, in the same way that
# release.yml does for the alpine support image.
#
# Invoked through `make mirror-images`; see docker/mirror-images.txt for why we
# re-publish these images and why regctl is used instead of `docker dhi mirror`.
#
# Environment:
#   REGISTRY       target registry prefix (default ghcr.io/vantage6/infrastructure)
#   TAG            tag to publish under, i.e. the vantage6 version (required)
#   PUSH_REG       when not "true", resolve and report only; nothing is pushed
#   FLOATING_TAGS  when "true", also move major.minor and latest where the version
#                  allows it (see below). Off by default, so that a shared tag is
#                  never moved unless the caller asked for it.
#
# regctl copies the whole multi-arch index plus the attached SBOM and provenance
# referrers, so the hardened-image guarantees survive the copy. `docker pull` +
# `docker push` would flatten the index to a single platform and drop them.
set -euo pipefail

REGISTRY="${REGISTRY:-ghcr.io/vantage6/infrastructure}"
TAG="${TAG:-}"
PUSH_REG="${PUSH_REG:-false}"
FLOATING_TAGS="${FLOATING_TAGS:-false}"

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

# Alongside the exact version, a release also moves the floating tags, matching
# what release.yml does for the alpine support image: major.minor for a final
# release or for a pre-release of a .0 (no stable release claims that tag yet),
# and latest for final releases only. A '.postN' rebuild counts as final, as it
# does in release.yml. Codenames such as 'uluru' and local builds match nothing
# here and are published under their own tag alone.
extra_tags=()
if [ "${FLOATING_TAGS}" = "true" ] &&
   [[ "${TAG}" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)((a|b|rc)[0-9]+)?(\.post[0-9]+)?$ ]]; then
  major_minor="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
  patch="${BASH_REMATCH[3]}"
  prerelease="${BASH_REMATCH[4]}"

  if [ -z "${prerelease}" ]; then
    extra_tags+=("${major_minor}" "latest")
  elif [ "${patch}" -eq 0 ]; then
    extra_tags+=("${major_minor}")
  fi
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

  # The floating tags are copied from the image we just published rather than
  # from dhi.io again: the blobs are already in place, so this is a manifest
  # write instead of a second pull. regctl preserves the manifest digest across
  # a copy, so the digest we resolved above also identifies the mirrored copy.
  for extra in ${extra_tags[@]+"${extra_tags[@]}"}; do
    if [ "${PUSH_REG}" = "true" ]; then
      echo "  -> ${REGISTRY}/${name}:${extra}"
      regctl image copy --referrers --digest-tags \
        "${REGISTRY}/${name}@${digest}" "${REGISTRY}/${name}:${extra}"
    else
      echo "  -> ${REGISTRY}/${name}:${extra} (skipped, PUSH_REG != true)"
    fi
  done
done < <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "${image_list}")
