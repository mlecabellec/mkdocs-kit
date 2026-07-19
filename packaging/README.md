# 📦 MkDocs-Kit Multi-Distribution Packaging

This directory contains the packaging specifications, control files, and build script integration for **MkDocs-Kit** across target Linux distributions.

---

## 🎯 Targeted Distributions & Formats

| Distribution | Package Format | Packaging Spec / Config | Build Script | Output Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Debian / Ubuntu** | `.deb` | [`packaging/debian/control`](file:///home/m/git/mkdocs-kit/packaging/debian/control) | [`scripts/build-debian.sh`](file:///home/m/git/mkdocs-kit/scripts/build-debian.sh) | `output/mkdocs-kit_1.0.0-1_amd64.deb` |
| **Fedora / RHEL** | `.rpm` | [`packaging/fedora/mkdocs-kit.spec`](file:///home/m/git/mkdocs-kit/packaging/fedora/mkdocs-kit.spec) | [`scripts/build-fedora.sh`](file:///home/m/git/mkdocs-kit/scripts/build-fedora.sh) | `output/mkdocs-kit-1.0.0-1.x86_64.rpm` |
| **Arch Linux** | `.pkg.tar.zst` | [`packaging/arch/PKGBUILD`](file:///home/m/git/mkdocs-kit/packaging/arch/PKGBUILD) | [`scripts/build-arch.sh`](file:///home/m/git/mkdocs-kit/scripts/build-arch.sh) | `output/mkdocs-kit_1.0.0-1_archlinux.pkg.tar.zst` |

---

## 🚀 Automated Build Scripts

Each distribution has a dedicated, self-contained, and deterministic build script located in `scripts/` (with convenience execution wrappers in `packaging/<distro>/build.sh`).

### 1. Build Orchestrator (Auto-detect Host Distribution)

The master script automatically detects the host system distribution and triggers the corresponding build pipeline:

```bash
# Auto-detect host OS and build native package
./scripts/build-all.sh

# Target a specific distribution explicitly
./scripts/build-all.sh --distro debian
./scripts/build-all.sh --distro fedora
./scripts/build-all.sh --distro arch
./scripts/build-all.sh --distro all
```

### 2. Individual Distribution Build Scripts

You can also run the build scripts directly for any targeted distribution:

#### Debian / Ubuntu
```bash
./scripts/build-debian.sh [OPTIONS]
# Or using the local packaging wrapper:
./packaging/debian/build.sh
```

#### Fedora / RHEL
```bash
./scripts/build-fedora.sh [OPTIONS]
# Or using the local packaging wrapper:
./packaging/fedora/build.sh
```

#### Arch Linux
```bash
./scripts/build-arch.sh [OPTIONS]
# Or using the local packaging wrapper:
./packaging/arch/build.sh
```

---

## ⚙️ Common CLI Options

All distribution build scripts support the following standard parameters:

| Flag | Long Option | Description | Default |
| :--- | :--- | :--- | :--- |
| `-o` | `--output-dir DIR` | Output directory for compiled packages | `./output` |
| `-v` | `--version VER` | Package version | `1.0.0` |
| | `--skip-tests` | Skip Python unit tests and documentation compilation test | `false` |
| | `--skip-deps-check` | Skip system package pre-requisite verification | `false` |
| `-c` | `--clean` | Wipe build directories and virtual environment prior to build | `false` |
| `-h` | `--help` | Display script usage and required system packages | |

---

## 🏗️ Build Pipeline Lifecycle

Every distribution build script enforces a strict, deterministic sequence:

1. **System Pre-requisite Verification**: Validates required compilers, graphics rendering libraries, and system tools (`dpkg-deb`, `rpmbuild`, `makepkg`, `plantuml`, `graphviz`).
2. **Virtual Environment Isolation**: Initializes a clean Python virtual environment and installs pinned dependencies (`setuptools<82.0.0`, `weasyprint`, `wireviz`, `pyinstaller`, etc.).
3. **Unit Test Suite Execution**: Runs unit tests (`tests/test_all.py`) to validate in-memory diagram rendering and man page generation.
4. **PyInstaller Binary Compilation**: Compiles `src/mkdocs_kit/cli.py` into a single standalone executable using `mkdocs-kit.spec`.
5. **Binary CLI & Documentation Validation**: Validates executable CLI behavior and runs test documentation compilation (`mkdocs-kit build`).
6. **Package Assembly**: Packages the binary and metadata into native distribution format (`.deb`, `.rpm`, or `.pkg.tar.zst`).
7. **Package Integrity Inspection**: Inspects generated archive headers and file structures.
