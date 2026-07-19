#!/usr/bin/env bash
# ==============================================================================
# Script Name   : build-all.sh
# Description   : Unified Master Orchestrator Script for MkDocs-Kit Multi-Distro Builds
# Author        : Mickael Lecabellec <mickael.lecabellec@gmail.com>
# License       : MIT
# Requirements  : bash 4+
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Terminal Color Formatting
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

log_info()    { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"; }
log_step()    { echo -e "${COLOR_PURPLE}${COLOR_BOLD}[STEP] $1${COLOR_RESET}"; }
log_success() { echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"; }
log_warn()    { echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $1"; }
log_error()   { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2; }

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Master build orchestrator script for MkDocs-Kit package generation across distributions.

Options:
  -d, --distro DISTRO    Target distribution: debian, fedora, arch, auto, or all (default: auto)
  -o, --output-dir DIR   Directory to store output artifacts (default: $ROOT_DIR/output)
  -v, --version VER      Specify package version (default: 1.0.0)
  --skip-tests           Skip unit tests and documentation build test
  --skip-deps-check      Skip system dependency verification
  -c, --clean            Clean virtual environment and build folders before running
  -h, --help             Display this help message and exit

Examples:
  ./scripts/build-all.sh --distro auto
  ./scripts/build-all.sh --distro debian -o ./dist-debian
  ./scripts/build-all.sh --distro all
EOF
}

detect_distro() {
    if [[ -f /etc/os-release ]]; then
        # Load OS release key-value pairs
        # shellcheck disable=SC1091
        source /etc/os-release
        case "${ID:-}" in
            debian|ubuntu|pop|mint|kali)
                echo "debian"
                ;;
            fedora|rhel|centos|rocky|almalinux)
                echo "fedora"
                ;;
            arch|manjaro|endeavouros)
                echo "arch"
                ;;
            *)
                # Check ID_LIKE fallback
                case "${ID_LIKE:-}" in
                    *debian*|*ubuntu*) echo "debian" ;;
                    *fedora*|*rhel*)   echo "fedora" ;;
                    *arch*)            echo "arch" ;;
                    *)                 echo "unknown" ;;
                esac
                ;;
        esac
    else
        echo "unknown"
    fi
}

TARGET_DISTRO="auto"
OUTPUT_DIR="$ROOT_DIR/output"
PKG_VERSION="1.0.0"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--distro)
            TARGET_DISTRO="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            EXTRA_ARGS+=("-o" "$2")
            shift 2
            ;;
        -v|--version)
            PKG_VERSION="$2"
            EXTRA_ARGS+=("-v" "$2")
            shift 2
            ;;
        --skip-tests|--skip-deps-check|-c|--clean)
            EXTRA_ARGS+=("$1")
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

if [[ "$TARGET_DISTRO" == "auto" ]]; then
    TARGET_DISTRO=$(detect_distro)
    log_info "Auto-detected Linux distribution: ${TARGET_DISTRO}"
fi

case "$TARGET_DISTRO" in
    debian)
        log_info "Launching Debian/Ubuntu build pipeline..."
        "$SCRIPT_DIR/build-debian.sh" "${EXTRA_ARGS[@]}"
        ;;
    fedora)
        log_info "Launching Fedora/RHEL build pipeline..."
        "$SCRIPT_DIR/build-fedora.sh" "${EXTRA_ARGS[@]}"
        ;;
    arch)
        log_info "Launching Arch Linux build pipeline..."
        "$SCRIPT_DIR/build-arch.sh" "${EXTRA_ARGS[@]}"
        ;;
    all)
        log_info "Launching multi-distribution build pipeline..."
        log_step "Building Debian (.deb)..."
        "$SCRIPT_DIR/build-debian.sh" "${EXTRA_ARGS[@]}" || log_warn "Debian build failed or skipped."

        log_step "Building Fedora (.rpm)..."
        "$SCRIPT_DIR/build-fedora.sh" "${EXTRA_ARGS[@]}" || log_warn "Fedora build failed or skipped."

        log_step "Building Arch Linux (.pkg.tar.zst)..."
        "$SCRIPT_DIR/build-arch.sh" "${EXTRA_ARGS[@]}" || log_warn "Arch build failed or skipped."
        ;;
    *)
        log_error "Unsupported or unknown distribution target: '$TARGET_DISTRO'"
        log_info "Please specify a valid distribution using --distro (debian | fedora | arch | all)."
        exit 1
        ;;
esac

log_success "Build orchestrator finished execution."
