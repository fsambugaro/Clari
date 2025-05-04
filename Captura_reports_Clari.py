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

# ----------------------------------------------------------------------------
# Arquivo de ambiente: ~/.clari.env
# CLARI_USER=seu_email@empresa.com
# GITHUB_TOKEN=seu_personal_access_token
# ----------------------------------------------------------------------------
load_dotenv(os.path.expanduser("~/.clari.env"))
CLARI_USER = os.getenv("CLARI_USER")
REPO_PATH = os.path.expanduser("~/Documents/Clari")
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads")

# Relatórios e URLs
REPORTS = [
    ("LATAM FY25 This Quarter all pipe", "LATAM_CQ_W{w}.csv"),
    ("LATAM FY25 NQ all pipe",         "LATAM_NQ_W{w}.csv"),
    ("Pipe LATAM FY25 full year",      "LATAM_Year_W{w}.csv"),
]
REPORT_URLS = {
    "LATAM FY25 This Quarter all pipe": "https://app.clari.com/opportunities/68154b1c2385aa673b611594",
    "LATAM FY25 NQ all pipe":         "https://app.clari.com/opportunities/681637b3209b07709f94bcda",
    "Pipe LATAM FY25 full year":      "https://app.clari.com/opportunities/67f7dbf2a9815a3705a5152e",
}

# Calcula semana dentro do trimestre
# Ano fiscal Adobe inicia em dezembro
def week_in_quarter(dt: datetime.date) -> int:
    quarter = (dt.month - 1) // 3
    start = datetime.date(dt.year, quarter*3 + 1, 1)
    return ((dt - start).days // 7) + 1

# Função para baixar relatório via Selenium
def download_report(driver, report_name: str, out_path: str):
    logging.info(f"*** Iniciando download: {report_name}")
    before = set(os.listdir(DOWNLOAD_FOLDER))

    # Fecha qualquer modal aberto
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(1)
    except:
        pass

    # Navega para página do relatório
    driver.get(REPORT_URLS[report_name])
    wait = WebDriverWait(driver, 60)
    time.sleep(5)

    # 1) Abre menu de ações (⋮)
    menu_xpath = "/html/body/div[1]/div/div/div[1]/div[2]/div/div[1]/div/div[2]/div/div/div[4]/div/div/button"
    wait.until(EC.element_to_be_clickable((By.XPATH, menu_xpath))).click()
    time.sleep(2)

    # 2) Seleciona Export > CSV e aguarda processamento
    export_xpath = "/html/body/div[5]/div/button[5]/div[2]/div"
    wait.until(EC.element_to_be_clickable((By.XPATH, export_xpath))).click()
    time.sleep(90)

    # 3) Abre notificações para obter link
    notif_xpath = "/html/body/div[1]/div/div/div[1]/nav/div[2]/div/button[1]"
    wait.until(EC.element_to_be_clickable((By.XPATH, notif_xpath))).click()
    time.sleep(2)

    # 4) Captura links de download no painel de notificações
    notif_link_xpath = "//div[@role='dialog']//article//div[3]/a"
    links = driver.find_elements(By.XPATH, notif_link_xpath)
    if not links:
        logging.warning("Nenhum link de download encontrado na notificação com XPath: %s", notif_link_xpath)
    for link in links:
        href = link.get_attribute('href') or link.get_attribute('data-url')
        if href:
            logging.info(f"Baixando via link direto: {href}")
            driver.get(href)
            time.sleep(1)

    # 5) Aguarda download do arquivo
    timeout = 180
    start = time.time()
    latest_file = None
    while time.time() - start < timeout:
        new_files = [f for f in os.listdir(DOWNLOAD_FOLDER)
                     if f not in before and f.lower().endswith('.csv')]
        if new_files:
            latest_file = max(
                (os.path.join(DOWNLOAD_FOLDER, f) for f in new_files),
                key=os.path.getctime
            )
            break
        time.sleep(1)
    if not latest_file:
        raise RuntimeError(f"Timeout: CSV não encontrado para {report_name}")

    # Move para repositório e renomeia
    os.rename(latest_file, out_path)
    logging.info(f"Relatório salvo em {out_path}")
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
    except:
        pass

# Execução principal
def main():
    week = week_in_quarter(datetime.date.today())

    opts = Options()
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    driver.get("https://app.clari.com/login")
    print("Faça login manualmente (email+Okta) e aguarde o dashboard carregar...")
    input("Pressione Enter para continuar...")

    for title, tpl in REPORTS:
        output = os.path.join(REPO_PATH, tpl.format(w=week))
        download_report(driver, title, output)

    driver.quit()

    repo = Repo(REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Atualiza CSVs semana {week}")
    repo.remotes.origin.push()
    print("Relatórios atualizados e enviados ao GitHub com sucesso.")

if __name__ == '__main__':
    main()
