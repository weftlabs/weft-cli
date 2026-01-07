# Homebrew Distribution

This directory contains the Homebrew Formula for Weft CLI.

## Setup: Creating a Homebrew Tap

### 1. Create a Homebrew Tap Repository

Create a new repository at: `https://github.com/weftlabs/homebrew-tap`

```bash
# Create and initialize the tap repository
mkdir homebrew-tap
cd homebrew-tap
git init

# Create Formula directory
mkdir Formula

# Copy the formula
cp ../weft-cli/homebrew/weft.rb Formula/weft.rb

# Commit and push
git add Formula/weft.rb
git commit -m "Initial Weft formula"
git remote add origin https://github.com/weftlabs/homebrew-tap.git
git push -u origin main
```

### 2. Formula Structure

The formula at `Formula/weft.rb` follows Homebrew conventions:
- Uses Python virtualenv to isolate dependencies
- Specifies all runtime dependencies
- Includes basic test command

### 3. Installation After Setup

Once the tap is published, users can install via:

```bash
# Add the tap
brew tap weftlabs/tap

# Install weft
brew install weft

# Or in one command
brew install weftlabs/tap/weft
```

## Release Workflow

### Automated Release Process

When creating a new release:

1. **Tag the release in weft-cli:**
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

2. **Update the Formula:**
   ```bash
   # Calculate SHA256 of the tarball
   curl -L https://github.com/weftlabs/weft-cli/archive/refs/tags/v0.2.0.tar.gz | shasum -a 256

   # Update Formula/weft.rb with new version and SHA256
   # Commit and push to homebrew-tap
   ```

3. **Test the formula:**
   ```bash
   brew install --build-from-source weftlabs/tap/weft
   brew test weft
   brew audit --strict weft
   ```

### GitHub Actions Automation

Add `.github/workflows/release.yml` to weft-cli to automate formula updates:

```yaml
name: Update Homebrew Formula
on:
  release:
    types: [published]

jobs:
  homebrew:
    runs-on: ubuntu-latest
    steps:
      - name: Update Homebrew formula
        uses: mislav/bump-homebrew-formula-action@v3
        with:
          formula-name: weft
          formula-path: Formula/weft.rb
          homebrew-tap: weftlabs/homebrew-tap
          download-url: https://github.com/weftlabs/weft-cli/archive/refs/tags/${{ github.ref_name }}.tar.gz
        env:
          COMMITTER_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
```

## Maintenance

### Updating Dependencies

When updating `pyproject.toml` dependencies, update the `resource` blocks in the formula:

```ruby
resource "package-name" do
  url "https://files.pythonhosted.org/packages/source/..."
  sha256 "..."
end
```

### Testing Locally

```bash
# Lint the formula
brew audit --strict --online weft

# Test installation
brew install --build-from-source ./Formula/weft.rb

# Test the binary
brew test weft

# Uninstall for cleanup
brew uninstall weft
```

## Distribution Best Practices

1. **Always test before release** - Use `brew install --build-from-source`
2. **Follow semantic versioning** - Major.Minor.Patch
3. **Update changelogs** - Document breaking changes
4. **Automate when possible** - Use GitHub Actions for formula updates
5. **Keep dependencies minimal** - Only include runtime dependencies

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guide](https://docs.brew.sh/Python-for-Formula-Authors)
- [Acceptable Formulae](https://docs.brew.sh/Acceptable-Formulae)
