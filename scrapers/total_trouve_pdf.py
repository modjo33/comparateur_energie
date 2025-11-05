from playwright.sync_api import sync_playwright

URL = "https://www.totalenergies.fr/particuliers/electricite-et-gaz/offres-electricite"

print(f"Analyse approfondie de {URL}...\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=300)
    page = browser.new_page()
    page.goto(URL, timeout=90000)

    # On attend un peu que le JS charge les boutons
    page.wait_for_timeout(5000)

    # On clique sur tout ce qui ressemble à “grille tarifaire”, “tarif”, “télécharger”
    boutons = page.query_selector_all("a, button")
    print(f"{len(boutons)} éléments cliquables trouvés.\n")

    for b in boutons:
        texte = (b.inner_text() or "").lower()
        if any(mot in texte for mot in ["grille", "tarif", "pdf", "télécharger"]):
            print(f"[+] Tentative de clic sur : {texte[:60]}...")
            try:
                b.click(timeout=5000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"   - Échec du clic : {e}")

    # Après avoir cliqué un peu partout, on cherche les PDF dans les liens réseau
    liens = page.query_selector_all("a[href$='.pdf']")
    if not liens:
        print("Aucun PDF détecté même après interactions.")
    else:
        print("\nLiens PDF trouvés :")
        for a in liens:
            href = a.get_attribute("href")
            if href:
                print("-", href)

    browser.close()

print("\nAnalyse terminée.")
