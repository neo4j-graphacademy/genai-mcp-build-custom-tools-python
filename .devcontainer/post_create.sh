#!/usr/bin/env bash

# install uv
wget -qO- https://astral.sh/uv/install.sh | sh

# install Node v22
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

\. "$HOME/.nvm/nvm.sh"

nvm install 22
