# Homebrew Formula for Weft CLI
# This file should be placed in a homebrew-tap repository:
# https://github.com/weftlabs/homebrew-tap/blob/main/Formula/weft.rb
class Weft < Formula
  include Language::Python::Virtualenv

  desc "Enterprise-grade AI-assisted software development workflow"
  homepage "https://github.com/weftlabs/weft-cli"
  url "https://github.com/weftlabs/weft-cli/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "" # Will be generated during release process
  license "MIT"

  depends_on "python@3.11"
  depends_on "docker"

  resource "anthropic" do
    url "https://files.pythonhosted.org/packages/source/a/anthropic/anthropic-0.27.0.tar.gz"
    sha256 ""
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 ""
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 ""
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.5.0.tar.gz"
    sha256 ""
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python-dotenv-1.0.0.tar.gz"
    sha256 ""
  end

  resource "tabulate" do
    url "https://files.pythonhosted.org/packages/source/t/tabulate/tabulate-0.9.0.tar.gz"
    sha256 ""
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "weft, version", shell_output("#{bin}/weft --version")
  end
end
