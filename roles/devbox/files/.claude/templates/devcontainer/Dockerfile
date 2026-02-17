# Devcontainer for Claude Code sandboxed development.
# Language toolchains are conditionally installed via build args.

FROM node:20-bookworm

# --- Language toggle flags ---
ARG INSTALL_GO=false
ARG INSTALL_PYTHON=false
ARG INSTALL_RUST=false
ARG INSTALL_OCAML=false

ARG GO_VERSION=1.23.6
ARG DELTA_VERSION=0.18.2

# --- System packages ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    iptables \
    ipset \
    iproute2 \
    dnsutils \
    fzf \
    ripgrep \
    jq \
    curl \
    sudo \
    build-essential \
    zsh \
    locales \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# --- Locale ---
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# --- gh CLI ---
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*

# --- git-delta ---
RUN curl -fsSL "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/git-delta_${DELTA_VERSION}_$(dpkg --print-architecture).deb" \
    -o /tmp/delta.deb \
    && dpkg -i /tmp/delta.deb && rm /tmp/delta.deb

# --- Go (conditional) ---
RUN if [ "$INSTALL_GO" = "true" ]; then \
    curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-$(dpkg --print-architecture | sed 's/amd64/amd64/;s/arm64/arm64/').tar.gz" \
    | tar -C /usr/local -xz; \
    fi
ENV GOPATH=/home/node/go
ENV PATH="/usr/local/go/bin:${GOPATH}/bin:${PATH}"

# --- Python + uv (conditional) ---
RUN if [ "$INSTALL_PYTHON" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh; \
    fi

# --- Rust (conditional) ---
ENV CARGO_HOME=/home/node/.cargo
ENV RUSTUP_HOME=/home/node/.rustup
RUN if [ "$INSTALL_RUST" = "true" ]; then \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | su node -c "sh -s -- -y --default-toolchain stable --no-modify-path"; \
    fi
ENV PATH="${CARGO_HOME}/bin:${PATH}"

# --- OCaml (conditional) ---
RUN if [ "$INSTALL_OCAML" = "true" ]; then \
    apt-get update && apt-get install -y --no-install-recommends opam \
    && rm -rf /var/lib/apt/lists/* \
    && su node -c "opam init --disable-sandboxing --auto-setup --bare" \
    && su node -c "opam switch create default ocaml-system || true"; \
    fi

# --- Zsh + Powerlevel10k ---
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git /usr/local/share/powerlevel10k
RUN echo 'source /usr/local/share/powerlevel10k/powerlevel10k.zsh-theme' >> /etc/zsh/zshrc

# --- Claude Code ---
RUN npm install -g @anthropic-ai/claude-code

# --- Firewall setup ---
COPY init-firewall.sh /usr/local/bin/init-firewall.sh
COPY domains.conf /usr/local/etc/devcontainer/domains.conf
RUN chmod +x /usr/local/bin/init-firewall.sh

# --- Non-root user setup ---
RUN echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" >> /etc/sudoers.d/firewall \
    && chmod 0440 /etc/sudoers.d/firewall

# Ensure home directory ownership
RUN mkdir -p /home/node/go /home/node/.cargo /home/node/.local \
    && chown -R node:node /home/node

USER node
WORKDIR /home/node/workspace

# Default shell
ENV SHELL=/usr/bin/zsh
CMD ["zsh"]
