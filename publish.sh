#!/bin/bash

# Ferma lo script se un qualsiasi comando dà errore
set -e

echo "Pulizia delle build precedenti..."
rm -rf dist/ build/ *.egg-info

echo "Aggiornamento setuptools, build e twine..."
pip install --upgrade setuptools build twine

echo "Costruzione del pacchetto..."
python3 -m build

echo "Caricamento su PyPI..."
twine upload dist/*

echo "Fatto! Pacchetto pubblicato su PyPI."
