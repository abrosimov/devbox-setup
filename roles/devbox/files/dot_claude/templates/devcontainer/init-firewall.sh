#!/usr/bin/env bash
# init-firewall.sh — iptables + ipset default-deny egress firewall for devcontainer.
# Reads allowed domains from /usr/local/etc/devcontainer/domains.conf.
# Must run as root (via sudo).
set -euo pipefail

CONF="/usr/local/etc/devcontainer/domains.conf"
IPSET_NAME="allowed_hosts"

if [[ ! -f "$CONF" ]]; then
    echo "ERROR: $CONF not found" >&2
    exit 1
fi

# --- Resolve domains to IPs ---

resolve_domain() {
    local domain="$1"
    # Strip wildcard prefix for resolution
    domain="${domain#\*.}"
    dig +short A "$domain" 2>/dev/null | grep -E '^[0-9]+\.' || true
}

echo "==> Creating ipset: $IPSET_NAME"
ipset destroy "$IPSET_NAME" 2>/dev/null || true
ipset create "$IPSET_NAME" hash:ip hashsize 4096

echo "==> Resolving domains from $CONF"
while IFS= read -r line; do
    # Strip comments and whitespace
    line="${line%%#*}"
    line="$(echo "$line" | xargs)"
    [[ -z "$line" ]] && continue

    ips=$(resolve_domain "$line")
    for ip in $ips; do
        ipset add "$IPSET_NAME" "$ip" 2>/dev/null || true
    done
done < "$CONF"

# --- GitHub Meta API IPs (actions, git, api, etc.) ---

echo "==> Fetching GitHub Meta API IPs"
gh_meta=$(curl -sf https://api.github.com/meta 2>/dev/null || echo '{}')
for key in git api web; do
    echo "$gh_meta" | jq -r ".${key}[]? // empty" 2>/dev/null | while IFS= read -r cidr; do
        # ipset hash:ip doesn't accept CIDRs — expand /32 only, skip others
        if [[ "$cidr" =~ /32$ ]]; then
            ipset add "$IPSET_NAME" "${cidr%/32}" 2>/dev/null || true
        elif [[ "$cidr" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            ipset add "$IPSET_NAME" "$cidr" 2>/dev/null || true
        fi
        # For larger CIDRs, the individual domain resolution above covers most cases
    done
done

# --- Detect Docker host gateway ---

echo "==> Detecting Docker host gateway"
host_gateway=$(ip route | awk '/default/ {print $3}' | head -1)
if [[ -n "$host_gateway" ]]; then
    # Allow the whole /24 subnet for host communication
    host_subnet="${host_gateway%.*}.0/24"
    echo "    Host gateway: $host_gateway (allowing $host_subnet)"
else
    host_subnet=""
    echo "    WARNING: Could not detect host gateway"
fi

# --- Apply iptables rules ---

echo "==> Flushing existing OUTPUT rules"
iptables -F OUTPUT

echo "==> Setting up iptables OUTPUT chain"

# Allow loopback
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established/related connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow DNS (UDP+TCP port 53)
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Allow SSH (port 22) — for git over SSH
iptables -A OUTPUT -p tcp --dport 22 -m set --match-set "$IPSET_NAME" dst -j ACCEPT

# Allow HTTPS (port 443) and HTTP (port 80) to allowed IPs
iptables -A OUTPUT -p tcp --dport 443 -m set --match-set "$IPSET_NAME" dst -j ACCEPT
iptables -A OUTPUT -p tcp --dport 80 -m set --match-set "$IPSET_NAME" dst -j ACCEPT

# Allow host gateway subnet (Docker host communication, bind mounts, etc.)
if [[ -n "$host_subnet" ]]; then
    iptables -A OUTPUT -d "$host_subnet" -j ACCEPT
fi

# Default deny everything else
iptables -P OUTPUT DROP

echo "==> Firewall configured. Rules:"
iptables -L OUTPUT -n --line-numbers

# --- Validation tests ---

echo ""
echo "==> Running validation tests..."

# Positive: should succeed (api.anthropic.com resolves to an allowed IP)
if curl -sf --max-time 5 -o /dev/null https://api.anthropic.com 2>/dev/null; then
    echo "    PASS: api.anthropic.com reachable"
else
    echo "    WARN: api.anthropic.com unreachable (may need DNS propagation)"
fi

# Negative: should fail (example.com is not in the allowlist)
if curl -sf --max-time 3 -o /dev/null https://example.com 2>/dev/null; then
    echo "    FAIL: example.com should be blocked but is reachable"
    exit 1
else
    echo "    PASS: example.com correctly blocked"
fi

echo "==> Firewall initialisation complete."
