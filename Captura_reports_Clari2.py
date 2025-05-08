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
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads")

REPORTS = [
    #("LATAM FY25 This Quarter all pipe", "LATAM_CQ_W{w}.csv"),
    #("LATAM FY25 NQ all pipe",         "LATAM_NQ_W{w}.csv"),
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

    # 1) Abre menu de ações
    menu = wait.until(EC.element_to_be_clickable((By.XPATH,
        "/html/body/div[1]/div/div/div[1]/div[2]/div/div[1]/div/div[2]/div/div/div[4]/div/div/button"
    )))
    menu.click()
    time.sleep(2)

    if report_name != "Pipe LATAM FY25 full year":
        # === fluxo original para primeiros dois relatórios ===
        # 2) Export > CSV
        export_xpath = "/html/body/div[5]/div/button[5]/div[2]/div"
        wait.until(EC.element_to_be_clickable((By.XPATH, export_xpath))).click()
        time.sleep(90)

        # 3) Abre notificações
        notif_xpath = "/html/body/div[1]/div/div/div[1]/nav/div[2]/div/button[1]"
        wait.until(EC.element_to_be_clickable((By.XPATH, notif_xpath))).click()
        time.sleep(2)

        # 4) Captura link fixo e dispara
        link_xpath = "//div[@role='dialog']//article//div[3]/a"
        link_el = wait.until(EC.element_to_be_clickable((By.XPATH, link_xpath)))
        href = link_el.get_attribute('href') or link_el.get_attribute('data-url')
        logging.info(f"Baixando via href: {href}")
        driver.get(href)
        time.sleep(1)
    else:
        # === fluxo especial para full year ===
        # 2) Export > CSV
        export_xpath = "/html/body/div[5]/div/button[5]/div[2]/div"
        wait.until(EC.element_to_be_clickable((By.XPATH, export_xpath))).click()
        time.sleep(90)

        # 3) Abre notificações
        notif_xpath = "/html/body/div[1]/div/div/div[1]/nav/div[2]/div/button[1]"
        wait.until(EC.element_to_be_clickable((By.XPATH, notif_xpath))).click()
        time.sleep(2)

        # 4) Loop: dispara download ao encontrar <a> com <svg>, encerra ao detectar arquivo
        start = time.time()
        downloaded_file = None
        link_el = None

        while time.time() - start < 180:
            if not link_el:
                anchors = driver.find_elements(By.XPATH, "//div[@role='dialog']//a")
                for a in anchors:
                    if a.find_elements(By.TAG_NAME, "svg"):
                        link_el = a
                        href = a.get_attribute("href") or a.get_attribute("data-url")
                        logging.info(f"Link SVG detectado, disparando download: {href}")
                        driver.get(href)
                        time.sleep(1)
                        break

            # Verifica chegada do CSV
            candidates = [
                f for f in os.listdir(DOWNLOAD_FOLDER)
                if f not in before and f.lower().endswith(".csv")
            ]
            if candidates:
                downloaded_file = max(
                    (os.path.join(DOWNLOAD_FOLDER, f) for f in candidates),
                    key=os.path.getctime
                )
                break

            # Aguarda e reclica notificações
            time.sleep(5)
            try:
                driver.find_element(By.XPATH, notif_xpath).click()
                time.sleep(1)
            except:
                pass

        if not downloaded_file:
            dump = f"debug_no_csv_{report_name.replace(' ', '_')}.html"
            with open(dump, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise RuntimeError(f"Timeout aguardando CSV para {report_name}. Veja {dump}")

        os.rename(downloaded_file, out_path)
        logging.info(f"Relatório salvo em {out_path}")
        return

    # Para os dois primeiros, aguarda o CSV pós-link
    start = time.time()
    latest_file = None
    while time.time() - start < 180:
        new = [
            f for f in os.listdir(DOWNLOAD_FOLDER)
            if f not in before and f.lower().endswith('.csv')
        ]
        if new:
            latest_file = max(
                (os.path.join(DOWNLOAD_FOLDER, f) for f in new),
                key=os.path.getctime
            )
            break
        time.sleep(1)

    if not latest_file:
        raise RuntimeError(f"Timeout aguardando CSV para {report_name}")

    os.rename(latest_file, out_path)
    logging.info(f"Relatório salvo em {out_path}")

def main():
    week = week_in_quarter(datetime.date.today())
    opts = Options()
    srv  = Service(ChromeDriverManager().install())
    drv  = webdriver.Chrome(service=srv, options=opts)

    drv.get("https://app.clari.com/login")
    print("Faça login manualmente (email+Okta) e pressione Enter para continuar...")
    input()

    for title, tpl in REPORTS:
        out = os.path.join(REPO_PATH, tpl.format(w=week))
        download_report(drv, title, out)

    drv.quit()

    repo = Repo(REPO_PATH)
    repo.git.add(A=True)
    repo.index.commit(f"Atualiza CSVs FY Week {week}")
    repo.remotes.origin.push()
    print("Relatórios atualizados e enviados ao GitHub com sucesso.")

if __name__ == "__main__":
    main()
