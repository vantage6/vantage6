# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 5.x.y   | :white_check_mark: |
| 4.x.y   | :white_check_mark: |
| < 4.0.0 | :x:                |

## Container Images

The container images we maintain in `ghcr.io/vantage6/infrastructure` are listed in
[docker/maintained-images.txt](docker/maintained-images.txt).

- **Scanning:** all final releases of these images are scanned for known vulnerabilities,
  including the named tags (such as `uluru` for 5.x and `cotopaxi` for 4.x) that point at
  the latest release of a major version.
- **Rebuilding:** releases built on a [Docker Hardened Image](https://docs.docker.com/dhi/)
  (DHI) base are rebuilt periodically to pick up fixes in that base image. Only the base
  image changes; the vantage6 code and its Python dependencies stay the same. Releases on
  other base images are not rebuilt, as a rebuild would not resolve their vulnerabilities.
- **Digests:** a rebuild publishes a new image under the existing tag, so its digest
  changes. If you pin images by digest, update the digest to receive the fixes.

Vulnerabilities in the vantage6 code or its Python dependencies are fixed in a new patch
release.

## Reporting a Vulnerability

Please report (suspected) security vulnerabilities to vantage6@iknl.nl. You will receive a response from us within 72 hours.
If the issue is confirmed, we will release a patch as soon as possible. When the patch is released you will be informed.
