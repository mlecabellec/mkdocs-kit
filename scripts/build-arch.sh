#!/usr/bin/env bash
# ==============================================================================
# Script Name   : build-arch.sh
# Description   : Automated build, test, and packaging script for Arch Linux (.pkg.tar.zst)
# Author        : Mickael Lecabellec <mickael.lecabellec@gmail.com>
# License       : MIT
# Requirements  : bash 4+, python, git, makepkg, plantuml, graphviz
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# Global Constants & Paths
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_DIR="$ROOT_DIR/.venv-build-arch"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build/arch"
DEFAULT_OUTPUT_DIR="$ROOT_DIR/output"
PKG_VERSION="1.0.0"
PKG_REVISION="1"

# ------------------------------------------------------------------------------
# Terminal Color Formatting
# ------------------------------------------------------------------------------
if [[ -t 1 ]]; then
    COLOR_RED='\033[0;31m'
    COLOR_GREEN='\033[0;32m'
    COLOR_YELLOW='\033[0;33m'
    COLOR_BLUE='\033[0;34m'
    COLOR_PURPLE='\033[0;35m'
    COLOR_CYAN='\033[0;36m'
    COLOR_BOLD='\033[1m'
    COLOR_RESET='\033[0m'
else
    COLOR_RED=''
    COLOR_GREEN=''
    COLOR_YELLOW=''
    COLOR_BLUE=''
    COLOR_PURPLE=''
    COLOR_CYAN=''
    COLOR_BOLD=''
    COLOR_RESET=''
fi

# ------------------------------------------------------------------------------
# Logging Functions
# ------------------------------------------------------------------------------
log_info()    { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"; }
log_step()    { echo -e "${COLOR_PURPLE}${COLOR_BOLD}[STEP] $1${COLOR_RESET}"; }
log_success() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"; }
log_warn()    { echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $1"; }
log_error()   { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2; }

# ------------------------------------------------------------------------------
# Usage & Help Function
# ------------------------------------------------------------------------------
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Robust build, test, and packaging script for Arch Linux (.pkg.tar.zst) distribution.

Options:
  -o, --output-dir DIR   Directory to output final Arch package (default: $DEFAULT_OUTPUT_DIR)
  -v, --version VER      Specify package version (default: $PKG_VERSION)
  --skip-tests           Skip Python unit tests and binary documentation test
  --skip-deps-check      Skip system dependency verification
  -c, --clean            Clean build directory and virtualenv before starting
  -h, --help             Display this help message and exit

System Dependencies Required (Arch Linux):
  python, python-pip, python-setuptools, python-wheel, base-devel,
  graphviz, plantuml, cairo, pango, gdk-pixbuf2, shared-mime-info, sudo

Example:
  ./scripts/build-arch.sh -o ./dist-pkg --version 1.0.0
EOF
}

# ------------------------------------------------------------------------------
# Argument Parsing
# ------------------------------------------------------------------------------
OUTPUT_DIR="$DEFAULT_OUTPUT_DIR"
SKIP_TESTS=false
SKIP_DEPS=false
DO_CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -v|--version)
            PKG_VERSION="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-deps-check)
            SKIP_DEPS=true
            shift
            ;;
        -c|--clean)
            DO_CLEAN=true
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            show_help
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# Cleanup Handler
# ------------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Build process failed with exit code $exit_code."
    fi
}
trap cleanup EXIT

# ------------------------------------------------------------------------------
# Step 0: Optional Clean Task
# ------------------------------------------------------------------------------
clean_workspace() {
    log_step "Cleaning build workspace..."
    rm -rf "$BUILD_DIR" "$VENV_DIR"
    log_success "Workspace cleaned."
}

# ------------------------------------------------------------------------------
# Step 1: System Dependency Check
# ------------------------------------------------------------------------------
check_system_deps() {
    if [[ "$SKIP_DEPS" == "true" ]]; then
        log_warn "Skipping system dependency checks as requested."
        return 0
    fi

    log_step "Verifying system build dependencies for Arch Linux..."
    local missing_tools=()

    local required_tools=("python3" "git" "makepkg" "plantuml" "graphviz")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required system tools: ${missing_tools[*]}"
        log_info "Install them using:"
        log_info "  sudo pacman -Syu --needed python python-pip python-setuptools python-wheel base-devel graphviz plantuml cairo pango gdk-pixbuf2 shared-mime-info sudo"
        exit 1
    fi

    log_success "All system dependencies verified."
}

# ------------------------------------------------------------------------------
# Step 2: Virtual Environment & Python Dependency Setup
# ------------------------------------------------------------------------------
setup_python_env() {
    log_step "Setting up isolated Python virtual environment..."

    if [[ ! -d "$VENV_DIR" ]]; then
        log_info "Creating virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    else
        log_info "Reusing existing virtual environment at $VENV_DIR..."
    fi

    local venv_pip="$VENV_DIR/bin/pip"

    log_info "Upgrading pip and installing wheel..."
    "$venv_pip" install --upgrade pip wheel

    log_info "Installing setuptools<82.0.0 (required for blockdiag compatibility)..."
    "$venv_pip" install "setuptools<82.0.0"

    log_info "Installing Python dependencies (mkdocs, material, weasyprint, wireviz, nwdiag, bit_field, pyinstaller)..."
    "$venv_pip" install mkdocs mkdocs-material weasyprint wireviz nwdiag bit_field pyinstaller

    log_info "Installing local mkdocs-kit package in editable mode..."
    cd "$ROOT_DIR"
    "$venv_pip" install -e .

    log_success "Python virtual environment configured successfully."
}

# ------------------------------------------------------------------------------
# Step 3: Run Unit Test Suite
# ------------------------------------------------------------------------------
run_unit_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warn "Skipping unit tests as requested."
        return 0
    fi

    log_step "Executing Python unit test suite..."
    cd "$ROOT_DIR"
    "$VENV_DIR/bin/python3" -m unittest tests/test_all.py
    log_success "All unit tests passed successfully."
}

# ------------------------------------------------------------------------------
# Step 4: Build Standalone Binary with PyInstaller
# ------------------------------------------------------------------------------
build_standalone_binary() {
    log_step "Building standalone binary with PyInstaller..."
    cd "$ROOT_DIR"

    # Execute PyInstaller with project spec file
    "$VENV_DIR/bin/pyinstaller" --noconfirm mkdocs-kit.spec

    local binary_path="$DIST_DIR/mkdocs-kit"
    if [[ ! -f "$binary_path" ]]; then
        log_error "Compiled binary not found at $binary_path."
        exit 1
    fi

    chmod +x "$binary_path"
    log_success "Standalone binary successfully created at $binary_path."

    log_info "Verifying precompiled binary functionality..."
    "$binary_path" --help > /dev/null
    log_success "Binary CLI executed successfully."

    if [[ "$SKIP_TESTS" == "false" ]]; then
        log_info "Testing documentation compilation using precompiled binary..."
        cd "$ROOT_DIR/doc"
        "$binary_path" build
        if [[ ! -d "$ROOT_DIR/doc/site" ]]; then
            log_error "Documentation build failed: site directory not generated."
            exit 1
        fi
        log_success "Binary documentation build test passed."
    fi
}

# ------------------------------------------------------------------------------
# Step 5: Package Arch Linux (.pkg.tar.zst) Archive
# ------------------------------------------------------------------------------
package_arch() {
    log_step "Packaging Arch Linux (.pkg.tar.zst) release artifact..."

    local arch_pkg_dir="$ROOT_DIR/packaging/arch"
    if [[ ! -f "$arch_pkg_dir/PKGBUILD" ]]; then
        log_error "PKGBUILD missing at $arch_pkg_dir/PKGBUILD"
        exit 1
    fi

    mkdir -p "$OUTPUT_DIR"
    cp "$DIST_DIR/mkdocs-kit" "$arch_pkg_dir/"

    cd "$arch_pkg_dir"

    # makepkg refuses to run as root by default. Handle root execution gracefully.
    if [[ "$(id -u)" -eq 0 ]]; then
        log_info "Running as root. Setting up unprivileged build user for makepkg..."
        if ! id builduser &>/dev/null; then
            useradd -m builduser
            passwd -d builduser
            printf 'builduser ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/builduser
        fi
        chown -R builduser:builduser "$arch_pkg_dir"
        sudo -u builduser makepkg --nodeps --cleanbuild --force
    else
        makepkg --nodeps --cleanbuild --force
    fi

    local generated_pkg
    generated_pkg=$(find "$arch_pkg_dir" -type f -name "mkdocs-kit-*.pkg.tar.zst" | head -n 1)

    if [[ -z "$generated_pkg" || ! -f "$generated_pkg" ]]; then
        log_error "Failed to generate Arch Linux package."
        exit 1
    fi

    local final_target="$OUTPUT_DIR/mkdocs-kit_${PKG_VERSION}-${PKG_REVISION}_archlinux.pkg.tar.zst"
    cp "$generated_pkg" "$final_target"

    log_success "Arch Linux package successfully built: $final_target"
}

# ------------------------------------------------------------------------------
# Step 6: Verify Package Output
# ------------------------------------------------------------------------------
verify_package() {
    log_step "Verifying Arch Linux package integrity..."
    local final_target="$OUTPUT_DIR/mkdocs-kit_${PKG_VERSION}-${PKG_REVISION}_archlinux.pkg.tar.zst"

    if command -v tar &>/dev/null; then
        log_info "Package Contents:"
        tar -tf "$final_target"
    else
        log_info "Package file details: $(ls -lh "$final_target")"
    fi

    log_success "Arch Linux package verification completed."
}

# ------------------------------------------------------------------------------
# Main Pipeline Execution
# ------------------------------------------------------------------------------
main() {
    log_info "Starting MkDocs-Kit Arch Linux Build Pipeline v${PKG_VERSION}"
    log_info "Repository root: $ROOT_DIR"
    log_info "Output directory: $OUTPUT_DIR"

    if [[ "$DO_CLEAN" == "true" ]]; then
        clean_workspace
    fi

    check_system_deps
    setup_python_env
    run_unit_tests
    build_standalone_binary
    package_arch
    verify_package

    log_success "========================================================"
    log_success "Arch Linux Build Pipeline completed successfully!"
    log_success "Artifact location: $OUTPUT_DIR/mkdocs-kit_${PKG_VERSION}-${PKG_REVISION}_archlinux.pkg.tar.zst"
    log_success "========================================================"
}

main
