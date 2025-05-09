#!/usr/bin/env bash
set -e

# 1. Vá para a pasta do seu projeto
cd ~/Documents/Clari

# 2. Puxe mudanças remotas para evitar conflitos
git pull origin main

# 3. Adicione arquivos, faça commit e envie para o GitHub
git add .
git commit -m "Deploy automatico em $(date +'%Y-%m-%d')"
git push origin main

# 4. (Opcional) Se tiver a CLI do Streamlit instalada, redeploy:
#    streamlit cloud deploy fsambugaro/Clari --branch main --path app.py
