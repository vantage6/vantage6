# Build environment for Anthropic OSS Scanner audits of vantage6. Not used for
# deployment: it installs all components so an offline agent can build and test them.
FROM python:3.13-bookworm

# Node.js for the Angular UI (Angular 22 needs a recent Node)
COPY --from=node:24-bookworm /usr/local/bin/node /usr/local/bin/
COPY --from=node:24-bookworm /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

RUN pip install --no-cache-dir uv

COPY . /src
WORKDIR /src

# All Python components (CLI, client, common, node, HQ, algorithm store, algorithm tools)
RUN uv sync --frozen
ENV PATH=/src/.venv/bin:$PATH

# UI dependencies, so the agent can build the frontend offline. Use
# `npx ng build --configuration development`: the production build inlines Google
# Fonts and fails without network.
RUN cd vantage6-ui && npm install

# Smoke test: failures warn but do not fail the build
RUN python utest.py || echo "WARNING: some unit tests failed"
