#!/bin/bash
# run_pipeline_app.sh

# 1) Caminho para o seu virtualenv
VENV="$HOME/clari-venv"

# 2) Caminho do diretório do app
APP_DIR="$HOME/Documents/Clari"
APP_FILE="app.py"

# 3) Ative o virtualenv
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
else
    echo "❌ Virtualenv não encontrado em $VENV"
    exit 1
fi

# 4) Garanta que o pip exista no venv
python -m ensurepip --upgrade

# 5) Atualize e instale streamlit-aggrid no venv
python -m pip install --upgrade pip
python -m pip install streamlit-aggrid

# 6) Vá para a pasta do app e execute
cd "$APP_DIR" || exit
streamlit run "$APP_FILE"
