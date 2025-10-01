#!/usr/bin/env bash
# This script will setup the virtual environment, install dependencies, and run the experiment script.

set -e
set -o pipefail

# Expect one argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <version>"
    exit 1
fi

VERSION=$1

create_virtual_env() {
    if ! command -v python3 &> /dev/null; then
        echo "python3 could not be found, please install it"
        echo "On Fedora:"
        echo "sudo dnf install python3 python3-venv python3-pip python3-devel"
        echo "On Ubuntu:"
        echo "sudo apt install python3 python3-venv python3-pip python3-dev"
        return 1
    fi

    if ! command -v pip3 &> /dev/null; then
        echo "pip3 could not be found, please install it"
        echo "On Fedora:"
        echo "sudo dnf install python3-pip"
        echo "On Ubuntu:"
        echo "sudo apt install python3-pip"
        return 1
    fi

    if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ] ; then
        echo "Creating virtual environment..."
        pip install virtualenv
        python3 -m virtualenv ./venv
        source ./venv/bin/activate
        pip install --upgrade pip
        pip install pandas numpy matplotlib seaborn rich
    else
        echo "Using existing virtual environment..."
        source ./venv/bin/activate
    fi
}

create_virtual_env

mkdir -p "./results/$VERSION"
./scripts/experiment.py "./results/$VERSION"
