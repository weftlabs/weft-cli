# Install Weft CLI

This guide shows how to install **Weft CLI** and get it running in a real project.  
Most users can be up and running in a few minutes.

## Prerequisites

Before installing Weft, make sure you have:
- **Python 3.11 or higher**
- **Docker and Docker Compose** (for running agents)
- **Claude API key** (unless using a local model)

> Weft never executes code automatically and never sends secrets or source code without your approval.

## Choose an installation method

### Method 1: Homebrew (Recommended for macOS/Linux)

Recommended for most macOS and Linux users.

```bash
# Add the Weft tap
brew tap weftlabs/tap

# Install weft
brew install weft

# Verify installation
weft --version
```

**Update to latest version:**
```bash
brew upgrade weft
```

### Method 2: pipx (Recommended for Python Developers)

Recommended if you prefer Python-isolated CLI tools.

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install weft
pipx install git+https://github.com/weftlabs/weft-cli.git

# Or install from PyPI (once published)
# pipx install weft
```

**Update to latest version:**
```bash
pipx upgrade weft
```

**Uninstall:**
```bash
pipx uninstall weft
```

### Method 3: Quick Install Script

Useful for CI, containers, or quick evaluation.

```bash
# Download and run the install script
curl -fsSL https://raw.githubusercontent.com/weftlabs/weft-cli/main/install.sh | sh

# Or using wget
wget -qO- https://raw.githubusercontent.com/weftlabs/weft-cli/main/install.sh | sh
```

**Note:** This method uses `pip install --user`, which installs to your user directory. You may need to add `~/.local/bin` to your PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

### Method 4: From Source (For Development)

Intended for contributors and development.

```bash
# Clone the repository
git clone https://github.com/weftlabs/weft-cli.git
cd weft-cli

# Install in development mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

See [development.md](development.md) for complete development setup.

## First-time setup

### 1. Initialize Your First Project

```bash
# Navigate to your project
cd ~/projects/my-app

# Initialize Weft
weft init

# This creates the project configuration and runtime directory
```

### 2. Configure Claude API Key

Weft requires an LLM provider. By default it uses Claude, but local models are supported as well.

```bash
# Set environment variable
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Or create a .env file in your project
echo "ANTHROPIC_API_KEY=sk-ant-api03-your-key-here" > .env
```

**Security Note:** Never commit `.env` files to version control.

### 3. Start the Runtime

```bash
# Start agent watchers
weft up

# View logs
weft logs meta --follow
```

Docker is required to run agents in isolated containers.

```bash
# Check Docker is running
docker --version
docker compose version

# Test Docker access
docker ps
```

## Next Steps

- Learn how agents work → agents.md  
- Explore configuration options → configuration.md  
- See all CLI commands → cli-reference.md  

## Getting help

- Check the troubleshooting guide  
- Search existing GitHub issues  
- Open a new issue with logs and reproduction steps  
