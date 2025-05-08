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

logging.basicConfig(level=logging.INFO)
load_dotenv(os.path.expanduser("~/.clari.env"))

REPO_PATH       = os.path.expanduser("~/Documents/Clari")
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads")

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
    fm = ((dt.month - 12) % 12) + 1
    fy = dt.year if dt.month == 12 else dt.year - 1
    fq = (fm - 1) // 3
    starts = [12, 3, 6, 9]
    sm = starts[fq]
    sy = fy if sm == 12 else fy + 1
    sd = datetime.date(sy, sm, 1)
    return ((dt - sd).days // 7) + 1

def download_report(driver, report_name: str, out_path: str):
    logging.info(f"*** Iniciando download: {report_name}")
    before = set(os.listdir(DOWNLOAD_FOLDER))
    wait   = WebDriverWait(driver, 60)

    # Fecha modais
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(1)
    except:
        pass

    # Acessa relatório
    driver.get(REPORT_URLS[report_name])
    time.sleep(5)

    # Abre menu de ações
    menu_xpath = "/html/body/div[1]/div/div/div[1]/div[2]/div/div[1]/div/div[2]/div/div/div[4]/div/div/button"
    wait.until(EC.element_to_be_clickable((By.XPATH, menu_xpath))).click()
    time.sleep(2)

    # Export → CSV
    export_xpath = "/html/body/div[5]/div/button[5]/div[2]/div"
    wait.until(EC.element_to_be_clickable((By.XPATH, export_xpath))).click()
    time.sleep(90)

    # Abre notificações
    notif_xpath = "/html/body/div[1]/div/div/div[1]/nav/div[2]/div/button[1]"
    wait.until(EC.element_to_be_clickable((By.XPATH, notif_xpath))).click()
    time.sleep(2)

    # Captura link
    if report_name == "Pipe LATAM FY25 full year":
        notif_link_xpath = "/html/body/div[5]/div/div/div[2]/article[1]/div[3]/a"
    else:
        notif_link_xpath = "//div[@role='dialog']//article//div[3]/a"
    links = driver.find_elements(By.XPATH, notif_link_xpath)
    if links:
        href = links[0].get_attribute('href') or links[0].get_attribute('data-url')
        logging.info(f"Baixando via {href}")
        driver.get(href)
        time.sleep(1)
    else:
        logging.warning(f"Nenhum link encontrado com XPath {notif_link_xpath}")

    # Aguarda CSV
    start = time.time()
    latest = None
    while time.time() - start < 180:
        files = [f for f in os.listdir(DOWNLOAD_FOLDER)
                 if f not in before and f.lower().endswith('.csv')]
        if files:
            latest = max((os.path.join(DOWNLOAD_FOLDER, f) for f in files),
                         key=os.path.getctime)
            break
        time.sleep(1)
    if not latest:
        raise RuntimeError("Timeout aguardando CSV")
    os.rename(latest, out_path)
    logging.info(f"Salvo em {out_path}")

def main():
    week = week_in_quarter(datetime.date.today())
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    logging.info(f"Timestamp= {ts}")

    opts = Options()
    srv  = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=srv, options=opts)

    driver.get("https://app.clari.com/login")
    print("Faça login + Okta e Enter...")
    input()

    total_start = time.time()
    for title, tpl in REPORTS:
        logging.info(f"Processando report title={title!r}")
        base    = tpl.format(w=week)
        if title == "Pipe LATAM FY25 full year":
            name, ext = os.path.splitext(base)
            filename  = f"{name}_{ts}{ext}"
        else:
            filename = base
        logging.info(f"Filename final={filename}")
        out_path = os.path.join(REPO_PATH, filename)

        t0 = time.time()
        download_report(driver, title, out_path)
        delta = time.time() - t0
        print(f"⏱️  '{title}' em {delta:.1f}s")

    total = (time.time() - total_start)/60
    print(f"✅ Todos em {total:.1f}min")

    driver.quit()
    repo = Repo(REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Atualiza FY Week {week}_{ts}")
    repo.remotes.origin.push()
    print("Push completo.")

if __name__ == "__main__":
    main()
