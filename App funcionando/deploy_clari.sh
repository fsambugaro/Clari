#!/usr/bin/env bash
set -euo pipefail

# 1. Vá para a pasta do seu projeto
cd ~/Documents/Clari

# 2. Puxe mudanças remotas para evitar conflitos
git pull origin main

# 3. Certifique-se de que a pasta Data/ está sendo rastreada
git add Data/

# 4. Adicione todo o resto (código, .gitignore atualizado etc.)
git add .

# 5. Faça commit com carimbo de data
git commit -m "Deploy automático em $(date +'%Y-%m-%d %H:%M')"

# 6. Envie para o GitHub
git push origin main

# 7. (Opcional) Redeploy no Streamlit Cloud
streamlit cloud deploy fsambugaro/Clari --branch main --path app.py
