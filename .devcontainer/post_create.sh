#!/usr/bin/env bash

# Install uv
wget -qO- https://astral.sh/uv/install.sh | sh

# Install nvm
curl https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

\. "$NVM_DIR/nvm.sh"

nvm install 22

# Install client dependencies
cd client
uv venv
source .venv/bin/activate
uv pip install -e .
