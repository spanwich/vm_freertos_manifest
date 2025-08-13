# Custom CAmkES VM Examples Manifest with vm_freertos

This repository contains a custom repo manifest for the CAmkES VM Examples project that integrates the custom vm_freertos implementation.

## Overview

This manifest is based on the official [seL4/camkes-vm-examples-manifest](https://github.com/seL4/camkes-vm-examples-manifest) but includes the custom vm_freertos project from https://github.com/spanwich/camkes-vm-freertos.git

## Key Differences from Upstream

1. **Added remote**: `spanwich` remote pointing to https://github.com/spanwich/
2. **Added project**: `camkes-vm-freertos.git` that clones directly to `projects/vm-examples/apps/Arm/vm_freertos`
3. **Preserved upstream**: All other components remain identical to upstream manifest

## Usage

### Fresh Environment Setup

```bash
# Install dependencies first
sudo apt update
sudo apt install -y \
    cmake ninja-build \
    gcc-arm-none-eabi \
    gcc-aarch64-linux-gnu \
    protobuf-compiler \
    libusb-1.0-0-dev \
    cpio \
    libxml2-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    build-essential \
    git \
    python3 python3-pip python3-venv

# Install Haskell Stack
curl -sSL https://get.haskellstack.org/ | sh

# Install repo tool
curl https://storage.googleapis.com/git-repo-downloads/repo > repo
chmod a+x repo
sudo mv repo /usr/local/bin/

# Set up Python environment
python3 -m venv ~/phd/sel4-dev-env
source ~/phd/sel4-dev-env/bin/activate

# Create workspace and sync
mkdir -p ~/phd/camkes-vm-freertos-workspace && cd ~/phd/camkes-vm-freertos-workspace
repo init -u https://github.com/spanwich/vm_freertos_manifest.git
repo sync

# Install CAmkES Python dependencies
cd projects/camkes-tool/tools/python-deps
pip install --editable .
cd ../../../..

# Build and test
mkdir build && cd build
source ../../sel4-dev-env/bin/activate
../init-build.sh -DCAMKES_VM_APP=vm_freertos -DPLATFORM=qemu-arm-virt -DSIMULATION=1 -DLibUSB=OFF
ninja
./simulate
```

### Update vm_freertos

```bash
# Update just vm_freertos
cd projects/vm-examples/apps/Arm/vm_freertos
git pull origin main

# Or update all projects
cd ~/phd/camkes-vm-freertos-workspace
repo sync
```

## Advantages of This Approach

1. **Clean Integration**: vm_freertos is managed just like any other seL4 project
2. **Easy Updates**: Use `repo sync` to update all components including vm_freertos
3. **Version Consistency**: All components stay in sync with known-good versions
4. **No Submodules**: Avoids git submodule complexity
5. **Team Friendly**: Others can easily clone the complete environment

## Manifest Structure

The manifest includes:
- All upstream CAmkES VM Examples components
- Custom vm_freertos project from GitHub
- Proper remote configuration for your repositories
- Preserved commit hashes for reproducible builds

## For Collaborators

To use this environment, collaborators only need:

```bash
repo init -u https://github.com/spanwich/vm_freertos_manifest.git
repo sync
```

No need to manually add submodules or remember specific setup steps.