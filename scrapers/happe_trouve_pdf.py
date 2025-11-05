from playwright.sync_api import sync_playwright

def chercher_pdfs():
    url = "https://www.happ-e.fr/offre-electricite/"
    print(f"Analyse de {url} ...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # fenêtre visible
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle")

        # Récupération de tous les liens de la page
        links = page.eval_on_selector_all("a", "els => els.map(e => e.href)")
        browser.close()

    # Filtre sur les fichiers PDF
    pdf_links = [l for l in links if l and ".pdf" in l.lower()]

    if not pdf_links:
        print("\nAucun lien PDF trouvé sur la page.")
    else:
        print("\nLiens PDF trouvés :")
        for l in pdf_links:
            print("-", l)

if __name__ == "__main__":
    chercher_pdfs()
