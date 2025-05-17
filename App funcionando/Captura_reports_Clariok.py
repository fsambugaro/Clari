#!/usr/bin/env python3

import os
import time
import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from git import Repo
from dotenv import load_dotenv

# Configuração de logging
logging.basicConfig(level=logging.INFO)
load_dotenv(os.path.expanduser("~/.clari.env"))

CLARI_USER      = os.getenv("CLARI_USER")
REPO_PATH       = os.path.expanduser("~/Documents/Clari")
DATA_PATH       = os.path.join(REPO_PATH, "Data")
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads")

# Garante que a pasta Data exista
os.makedirs(DATA_PATH, exist_ok=True)

REPORTS = [
    ("LATAM FY25 This Quarter all pipe", "LATAM_CQ_W{w}.csv"),
    ("LATAM FY25 NQ all pipe",         "LATAM_NQ_W{w}.csv"),
    ("Pipe LATAM FY25 full year",      "LATAM_Year_W{w}.csv"),
]
REPORT_URLS = {
    "LATAM FY25 This Quarter all pipe": "https://app.clari.com/opportunities/68154b1c2385aa673b611594",
    "LATAM FY25 NQ all pipe":           "https://app.clari.com/opportunities/681a6248209b07709f9ccc6b",
    "Pipe LATAM FY25 full year":        "https://app.clari.com/opportunities/681c333553fea2471096c4ba",
}

def week_in_quarter(dt: datetime.date) -> int:
    fiscal_month = ((dt.month - 12) % 12) + 1
    fiscal_year  = dt.year if dt.month == 12 else dt.year - 1
    quarter      = (fiscal_month - 1) // 3
    start_months = [12, 3, 6, 9]
    sm = start_months[quarter]
    sy = fiscal_year if sm == 12 else fiscal_year + 1
    sd = datetime.date(sy, sm, 1)
    return ((dt - sd).days // 7) + 1

def download_report(driver, report_name: str, out_path: str):
    logging.info(f"*** Iniciando download: {report_name}")
    before = set(os.listdir(DOWNLOAD_FOLDER))
    wait   = WebDriverWait(driver, 60)

    # Fecha modais abertos
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(1)
    except:
        pass

    # 1) Acessa página do relatório
    driver.get(REPORT_URLS[report_name])
    time.sleep(5)

    # 2) Abre menu de ações (⋮)
    menu_xpath = "/html/body/div[1]/div/div/div[1]/div[2]/div/div[1]/div/div[2]/div/div/div[4]/div/div/button"
    wait.until(EC.element_to_be_clickable((By.XPATH, menu_xpath))).click()
    time.sleep(2)

    # 3) Seleciona Export > CSV
    export_xpath = "/html/body/div[5]/div/button[5]/div[2]/div"
    wait.until(EC.element_to_be_clickable((By.XPATH, export_xpath))).click()
    time.sleep(90)

    # 4) Abre notificações
    notif_xpath = "/html/body/div[1]/div/div/div[1]/nav/div[2]/div/button[1]"
    wait.until(EC.element_to_be_clickable((By.XPATH, notif_xpath))).click()
    time.sleep(2)

    # 5) Captura link de download
    if report_name == "Pipe LATAM FY25 full year":
        link_xpath = "/html/body/div[5]/div/div/div[2]/article[1]/div[3]/a"
    else:
        link_xpath = "//div[@role='dialog']//article//div[3]/a"

    links = driver.find_elements(By.XPATH, link_xpath)
    if links:
        href = links[0].get_attribute('href') or links[0].get_attribute('data-url')
        logging.info(f"Baixando via href: {href}")
        driver.get(href)
        time.sleep(1)
    else:
        logging.warning(f"Nenhum link encontrado com XPath: {link_xpath}")

    # 6) Aguarda o arquivo .csv
    start = time.time()
    latest_file = None
    while time.time() - start < 180:
        candidates = [
            f for f in os.listdir(DOWNLOAD_FOLDER)
            if f not in before and f.lower().endswith('.csv')
        ]
        if candidates:
            latest_file = max(
                (os.path.join(DOWNLOAD_FOLDER, f) for f in candidates),
                key=os.path.getctime
            )
            break
        time.sleep(1)

    if not latest_file:
        raise RuntimeError(f"Timeout aguardando CSV para {report_name}")

    # 7) Move e renomeia para Data/
    os.rename(latest_file, out_path)
    logging.info(f"Relatório salvo em {out_path}")

    # 8) Fecha notificações/modal
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
    except:
        pass

def main():
    week = week_in_quarter(datetime.date.today())
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    # —> Initialize Chrome using Homebrew-installed chromedriver
    opts = Options()
    opts.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    # opts.add_argument("--headless") # faz ocultar o clari na tela
    opts.add_argument("--disable-gpu")

    # assume chromedriver is in your PATH (via `brew install --cask chromedriver`)
    driver = webdriver.Chrome(options=opts)

    driver.get("https://app.clari.com/login")
    print("Faça login manualmente (email+Okta) e pressione Enter para continuar…")
    input()

    total_start = time.time()
    for title, tpl in REPORTS:
        base_name = tpl.format(w=week)
        name, ext  = os.path.splitext(base_name)
        filename   = f"{name}_{ts}{ext}"
        out_path   = os.path.join(DATA_PATH, filename)

        start = time.time()
        download_report(driver, title, out_path)
        elapsed = time.time() - start
        print(f"⏱️  Relatório '{title}' gerado em {elapsed:.1f}s — salvo como {filename}")

    total_elapsed = (time.time() - total_start) / 60
    print(f"✅ Todos finalizados em {total_elapsed:.1f} minutos.")

    driver.quit()

    repo = Repo(REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Atualiza CSVs FY Week {week}_{ts}")
    repo.remotes.origin.push()
    print("Relatórios enviados ao GitHub com sucesso.")

if __name__ == "__main__":
    main()
