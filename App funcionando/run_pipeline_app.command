#!/usr/bin/env bash
# run_pipeline_app.command
# Inicia o Streamlit app que consome os CSVs
# Salve este arquivo em ~/Desktop/run_pipeline_app.command
# e torne executável com:
# chmod +x ~/Desktop/run_pipeline_app.command

# Caminho para o venv global do usuário (nome clari-venv em home)
VENV_PATH="$HOME/clari-venv"
# Ativa o ambiente virtual
source "$VENV_PATH/bin/activate"
# Navega até a pasta do app
cd "$HOME/Documents/Clari"
# Executa o Streamlit app usando Python do venv
env PYTHONUNBUFFERED=1 "$VENV_PATH/bin/python" -m streamlit run app.py
