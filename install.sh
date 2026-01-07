#!/usr/bin/env bash
# Weft CLI Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/weftlabs/weft-cli/main/install.sh | sh
# Or: wget -qO- https://raw.githubusercontent.com/weftlabs/weft-cli/main/install.sh | sh
# Local test: WEFT_LOCAL_INSTALL=1 bash install.sh

set -e

# Configuration
REPO="weftlabs/weft-cli"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
PYTHON_MIN_VERSION="3.11"
LOCAL_INSTALL="${WEFT_LOCAL_INSTALL:-0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
error() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

info() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS and architecture
detect_platform() {
    local os arch

    case "$(uname -s)" in
        Linux*)     os="linux" ;;
        Darwin*)    os="darwin" ;;
        *)          error "Unsupported operating system: $(uname -s)" ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)   arch="amd64" ;;
        aarch64|arm64)  arch="arm64" ;;
        *)              error "Unsupported architecture: $(uname -m)" ;;
    esac

    echo "${os}_${arch}"
}

# Check Python version
check_python() {
    if ! command_exists python3; then
        error "Python 3 is required but not found. Please install Python ${PYTHON_MIN_VERSION} or higher."
    fi

    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
        error "Python ${PYTHON_MIN_VERSION}+ is required (found: ${python_version})"
    fi

    info "✓ Python ${python_version} detected"
}

# Check Docker
check_docker() {
    if ! command_exists docker; then
        warn "Warning: Docker not found. Weft requires Docker to run agents."
        warn "Install Docker from: https://docs.docker.com/get-docker/"
    else
        info "✓ Docker detected"
    fi
}

# Get latest release version
get_latest_version() {
    if command_exists curl; then
        curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" | \
            grep '"tag_name":' | \
            sed -E 's/.*"v?([^"]+)".*/\1/'
    elif command_exists wget; then
        wget -qO- "https://api.github.com/repos/${REPO}/releases/latest" | \
            grep '"tag_name":' | \
            sed -E 's/.*"v?([^"]+)".*/\1/'
    else
        error "curl or wget is required"
    fi
}

# Install using pip
install_with_pip() {
    local version="$1"
    local install_cmd="python3"
    local install_target

    info "Installing Weft ${version} using pip..."

    # Check if pip is available via python -m pip
    if ! ${install_cmd} -m pip --version >/dev/null 2>&1; then
        error "pip is not available. Please install pip first."
    fi

    # Determine install target
    if [ "$LOCAL_INSTALL" = "1" ]; then
        # Local development mode - install from current directory
        if [ ! -f "pyproject.toml" ]; then
            error "LOCAL_INSTALL=1 but pyproject.toml not found. Run from repository root."
        fi
        install_target="."
        info "Installing from local directory (development mode)"
    else
        # Normal mode - install from GitHub
        install_target="git+https://github.com/${REPO}.git@v${version}"
    fi

    # Install to user directory with explicit flags for PEP 668 compliance
    # Try --user first, then --break-system-packages if needed (macOS Homebrew Python)
    if ${install_cmd} -m pip install --user --no-warn-script-location "${install_target}" >/tmp/weft-install.log 2>&1; then
        info "✓ Weft installed successfully"
    elif grep -q "externally-managed-environment" /tmp/weft-install.log; then
        # Homebrew Python requires --break-system-packages even with --user
        warn "Detected externally-managed Python, using --break-system-packages..."
        if ${install_cmd} -m pip install --user --break-system-packages --no-warn-script-location "${install_target}" >/tmp/weft-install.log 2>&1; then
            info "✓ Weft installed successfully"
        else
            cat /tmp/weft-install.log
            error "Failed to install Weft. See output above for details."
        fi
    else
        cat /tmp/weft-install.log
        error "Failed to install Weft. See output above for details."
    fi
}

# Verify installation
verify_installation() {
    # Check common locations for the weft binary
    local paths=(
        "$HOME/.local/bin"
        "$HOME/Library/Python/*/bin"
        "/usr/local/bin"
    )

    local weft_path=""
    for path in "${paths[@]}"; do
        # Expand glob patterns
        for expanded_path in $path; do
            if [ -f "$expanded_path/weft" ]; then
                weft_path="$expanded_path"
                break 2
            fi
        done
    done

    if [ -z "$weft_path" ]; then
        warn "Warning: weft binary not found in expected locations"
        warn "You may need to add Python's bin directory to your PATH"
        return 1
    fi

    # Test the installation
    if "$weft_path/weft" --version >/dev/null 2>&1; then
        info "✓ Installation verified: $weft_path/weft"

        # Check if directory is in PATH
        if ! echo "$PATH" | grep -q "$weft_path"; then
            warn ""
            warn "Add to PATH by adding this to your shell profile (~/.bashrc or ~/.zshrc):"
            echo "  export PATH=\"$weft_path:\$PATH\""
            warn ""
        fi
        return 0
    else
        warn "Warning: weft binary found but not working correctly"
        return 1
    fi
}

# Main installation
main() {
    info "====================================="
    info "  Weft CLI Installation Script"
    info "====================================="
    echo ""

    # Pre-flight checks
    info "Checking prerequisites..."
    check_python
    check_docker
    echo ""

    # Get version
    if [ "$LOCAL_INSTALL" = "1" ]; then
        info "Local install mode enabled"
        VERSION="dev"
    else
        info "Fetching latest version..."
        VERSION=$(get_latest_version)
        if [ -z "$VERSION" ]; then
            VERSION="0.1.0"
            warn "Could not fetch latest version, using v${VERSION}"
        else
            info "Latest version: v${VERSION}"
        fi
    fi
    echo ""

    # Install
    install_with_pip "$VERSION"
    echo ""

    # Verify
    info "Verifying installation..."
    if verify_installation; then
        info ""
        info "====================================="
        info "  Installation Complete!"
        info "====================================="
        info ""
        info "Next steps:"
        info "  1. Set your Claude API key:"
        info "     export ANTHROPIC_API_KEY=sk-ant-api03-..."
        info ""
        info "  2. Initialize a project:"
        info "     cd your-project && weft init"
        info ""
        info "  3. Read the documentation:"
        info "     https://github.com/${REPO}/tree/main/docs"
        info ""
    else
        warn ""
        warn "Installation completed but verification failed."
        warn "Please check your PATH configuration or install using:"
        warn "  pip3 install --user git+https://github.com/${REPO}.git"
        warn ""
    fi
}

# Run main installation
main "$@"
