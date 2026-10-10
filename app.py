from io import BytesIO
import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st
from PIL import Image

REPORTLAB_AVAILABLE = True
REPORTLAB_ERROR = ""

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
except ModuleNotFoundError as exc:
    REPORTLAB_AVAILABLE = False
    REPORTLAB_ERROR = str(exc)

# Configurazione Pagina
st.set_page_config(page_title="Generatore Ricevute", page_icon="📄")

# Dati personali: letti da dati_personali_da_non_caricare_su_git.json (escluso da git).
# In sua assenza si usa dati_personali.example.json, che contiene solo placeholder.
BASE_DIR = Path(__file__).parent


def carica_dati_personali() -> dict:
    for nome_file in ("dati_personali_da_non_caricare_su_git.json", "dati_personali.example.json"):
        percorso = BASE_DIR / nome_file
        if percorso.exists():
            with percorso.open(encoding="utf-8") as f:
                return json.load(f)
    return {"mittente": {}, "cliente": {}}


DATI = carica_dati_personali()
MITTENTE = DATI.get("mittente", {})
CLIENTE = DATI.get("cliente", {})


MESI_ITALIANI = [
    "GENNAIO", "FEBBRAIO", "MARZO", "APRILE", "MAGGIO", "GIUGNO",
    "LUGLIO", "AGOSTO", "SETTEMBRE", "OTTOBRE", "NOVEMBRE", "DICEMBRE"
]


def format_euro(importo: float) -> str:
    valore = f"{importo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"€. {valore}"


def format_data_lunga(data_input) -> str:
    mese = MESI_ITALIANI[data_input.month - 1]
    return f"{data_input.day} {mese} {data_input.year}"


def draw_wrapped_text(pdf, testo, x, y, larghezza_max, font_name="Helvetica", font_size=12, line_height=17):
    pdf.setFont(font_name, font_size)
    parole = testo.split()
    riga_corrente = ""

    for parola in parole:
        prova_riga = f"{riga_corrente} {parola}".strip()
        if pdf.stringWidth(prova_riga, font_name, font_size) <= larghezza_max:
            riga_corrente = prova_riga
        else:
            pdf.drawString(x, y, riga_corrente)
            y -= line_height
            riga_corrente = parola

    if riga_corrente:
        pdf.drawString(x, y, riga_corrente)
        y -= line_height

    return y


def prepara_firma(firma_bytes):
    if not firma_bytes:
        return None

    img = Image.open(BytesIO(firma_bytes)).convert("RGBA")
    gray = img.convert("L")
    px_gray = gray.load()
    px_rgba = img.load()
    width, height = img.size

    angoli = [
        px_gray[0, 0],
        px_gray[width - 1, 0],
        px_gray[0, height - 1],
        px_gray[width - 1, height - 1],
        px_gray[min(width // 2, width - 1), 0],
        px_gray[min(width // 2, width - 1), height - 1],
        px_gray[0, min(height // 2, height - 1)],
        px_gray[width - 1, min(height // 2, height - 1)],
    ]
    sfondo_lum = sum(angoli) / len(angoli)
    contrasto_minimo = 18
    pixel_visibili = 0

    for x in range(width):
        for y in range(height):
            lum = px_gray[x, y]
            contrasto = abs(lum - sfondo_lum)
            if contrasto < contrasto_minimo:
                px_rgba[x, y] = (255, 255, 255, 0)
            else:
                alpha = min(255, int((contrasto - contrasto_minimo) * 6))
                px_rgba[x, y] = (0, 0, 0, alpha)
                pixel_visibili += 1

    if pixel_visibili < max(150, int(width * height * 0.002)):
        return firma_bytes

    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    output = BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def genera_pdf_ricevuta(
    mio_nome,
    mio_cf,
    mio_iban,
    indirizzo_mittente,
    data_nascita_mittente,
    citta_mittente,
    cliente_nome,
    cliente_piva,
    cliente_indirizzo,
    cliente_citta,
    n_ricevuta,
    data_ricevuta,
    periodo_frase,
    importo_lordo,
    ritenuta,
    netto,
    bollo_dovuto,
    bollo_applicata,
    bollo_id,
    bollo_data,
    luogo_firma,
    data_firma,
    descrizione_prestazione,
    firma_bytes,
):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    larghezza, altezza = A4
    margine = 2.0 * cm

    y_top = altezza - 2.5 * cm

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margine, y_top, mio_nome.upper())
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margine, y_top - 18, indirizzo_mittente)
    pdf.drawString(margine, y_top - 36, f"C.f. {mio_cf.upper()}")
    pdf.drawString(margine, y_top - 54, f"Data di nascita: {data_nascita_mittente.strftime('%d/%m/%Y')}")
    pdf.drawString(margine, y_top - 72, citta_mittente)

    x_destra = larghezza - margine
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawRightString(x_destra, y_top, "Spett.le")
    pdf.drawRightString(x_destra, y_top - 18, cliente_nome)
    pdf.drawRightString(x_destra, y_top - 36, cliente_indirizzo)
    pdf.drawRightString(x_destra, y_top - 54, cliente_citta)
    pdf.drawRightString(x_destra, y_top - 72, f"p.iva {cliente_piva}")

    y = y_top - 150
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(
        margine,
        y,
        f"Ricevuta per Prestazione Occasionale n° {n_ricevuta} del {format_data_lunga(data_ricevuta)}",
    )

    y -= 45
    testo_descrittivo = (
        f"Il sottoscritto {mio_nome.upper()} dichiara di ricevere la somma lorda di {format_euro(importo_lordo)} "
        f"per {descrizione_prestazione.strip()} svolta {periodo_frase}. "
        f"Al suddetto importo lordo andrà detratta la ritenuta d’acconto (20%) pari a {format_euro(ritenuta)} "
        f"per un corrispettivo netto pagato sul mio iban {mio_iban} pari a {format_euro(netto)}"
    )
    y = draw_wrapped_text(pdf, testo_descrittivo, margine, y, larghezza - (2 * margine), "Helvetica", 12, 18)

    y -= 8
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(margine, y, "Riepilogo:")

    y -= 42
    x_etichetta = margine + 3.8 * cm
    x_valore = margine + 12.0 * cm
    pdf.setFont("Helvetica", 13)
    pdf.drawString(x_etichetta, y, "Corrispettivo Lordo")
    pdf.drawString(x_valore, y, format_euro(importo_lordo))

    y -= 24
    pdf.drawString(x_etichetta, y, "Ritenuta d’Acconto 20%")
    pdf.drawString(x_valore, y, format_euro(ritenuta))

    y -= 24
    pdf.drawString(x_etichetta, y, "Netto a pagare")
    pdf.drawString(x_valore, y, format_euro(netto))

    if bollo_dovuto:
        y -= 24
        pdf.drawString(x_etichetta, y, "Marca da bollo")
        stato_bollo = "assolta" if bollo_applicata else "da applicare"
        pdf.drawString(x_valore, y, f"€. 2,00 ({stato_bollo})")

    y -= 48
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawCentredString(larghezza / 2, y, "DICHIARA INOLTRE")

    y -= 45
    pdf.setFont("Helvetica", 12)
    pdf.drawString(margine, y, "Sotto la propria responsabilità:")

    y -= 34
    bullet_1 = "• di non avere fruito nell’anno ai fini contributivi, della franchigia di € 5.000 prevista dall’art. 44 del D.L. 30 settembre 2003, n. 269;"
    bullet_2 = "• di non essere soggetto al regime Iva a norma dell’ex art. 5, comma 2, D.P.R. 633/72."
    y = draw_wrapped_text(pdf, bullet_1, margine + 18, y, larghezza - (2 * margine) - 18, "Helvetica-Bold", 12, 18)
    y = draw_wrapped_text(pdf, bullet_2, margine + 18, y - 8, larghezza - (2 * margine) - 18, "Helvetica-Bold", 12, 18)

    if bollo_dovuto:
        y -= 18
        dettaglio_bollo = "Marca da bollo da € 2,00 assolta sull'originale."
        data_bollo_str = format_data_lunga(bollo_data) if bollo_data else ""
        if bollo_applicata and bollo_id and bollo_data:
            dettaglio_bollo = f"Marca da bollo da € 2,00 assolta sull'originale in data {data_bollo_str} - identificativo: {bollo_id}."
        elif bollo_applicata and bollo_data:
            dettaglio_bollo = f"Marca da bollo da € 2,00 assolta sull'originale in data {data_bollo_str}."
        elif not bollo_applicata:
            dettaglio_bollo = "Marca da bollo da € 2,00 da applicare sull'originale prima della consegna."
        y = draw_wrapped_text(pdf, dettaglio_bollo, margine, y, larghezza - (2 * margine), "Helvetica", 11, 16)

    y -= 60

    x_linea_end = larghezza - margine
    larghezza_linea = 6.2 * cm
    x_linea_start = x_linea_end - larghezza_linea
    x_centro_linea = (x_linea_start + x_linea_end) / 2
    y_linea = y - 24

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(x_centro_linea, y_linea + 38, f"{luogo_firma}, {format_data_lunga(data_firma)}")

    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(x_centro_linea, y_linea + 24, "In fede")
    pdf.line(x_linea_start, y_linea-10, x_linea_end, y_linea-10)

    if firma_bytes:
        try:
            immagine_firma = ImageReader(BytesIO(firma_bytes))
            img_w, img_h = immagine_firma.getSize()
            larghezza_max = 5.0 * cm
            altezza_max = 1.9 * cm
            scala = min(larghezza_max / img_w, altezza_max / img_h)
            larghezza_img = img_w * scala
            altezza_img = img_h * scala
            x_img = x_centro_linea - (larghezza_img / 2)
            y_img = y_linea - (altezza_img * 0.42)
            pdf.drawImage(
                immagine_firma,
                x_img,
                y_img,
                width=larghezza_img,
                height=altezza_img,
                mask='auto'
            )
        except Exception:
            pdf.setFont("Helvetica-BoldOblique", 17)
            pdf.drawCentredString((x_linea_start + x_linea_end) / 2, y_linea + 4, mio_nome)
    else:
        pdf.setFont("Helvetica-BoldOblique", 17)
        pdf.drawCentredString((x_linea_start + x_linea_end) / 2, y_linea + 4, mio_nome)

    pdf.showPage()
    pdf.save()

    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

st.title("📄 Generatore Ricevute Professionali")
st.subheader("Inserisci i dati per la prestazione occasionale")

# --- SIDEBAR: I TUOI DATI FISSI (Modificabili se serve) ---
st.sidebar.header("I Tuoi Dati (Mittente)")
mio_nome = st.sidebar.text_input("Nome", MITTENTE.get("nome", ""))
mio_cf = st.sidebar.text_input("Codice Fiscale", MITTENTE.get("codice_fiscale", ""))
indirizzo_mittente = st.sidebar.text_input("Via e numero (Mittente)", MITTENTE.get("indirizzo", ""))
data_nascita_mittente = st.sidebar.date_input(
    "Data di nascita",
    value=date.fromisoformat(MITTENTE.get("data_nascita", "2000-01-01")),
    min_value=date(1900, 1, 1),
    key="data_nascita_mittente",
)
mio_iban = st.sidebar.text_input("Il tuo IBAN", MITTENTE.get("iban", ""))
citta_mittente = st.sidebar.text_input("Città (Mittente)", MITTENTE.get("citta", ""))
luogo_firma = st.sidebar.text_input("Luogo firma", citta_mittente)
data_firma = st.sidebar.date_input("Data firma", value=date.today(), key="data_firma")
firma_file = st.sidebar.file_uploader("Carica firma (PNG/JPG)", type=["png", "jpg", "jpeg"])
firma_elaborata = prepara_firma(firma_file.getvalue()) if firma_file else None
if firma_file:
    st.sidebar.image(firma_elaborata, caption="Anteprima firma usata nel PDF", use_container_width=True)
descrizione_prestazione = st.sidebar.text_area(
    "Descrizione prestazione",
    MITTENTE.get("descrizione_prestazione", ""),
    height=90,
)

# --- COLONNE PER INPUT ---
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Dati Ricevuta")
    n_ricevuta = st.text_input("Numero Ricevuta", "01")
    data_ricevuta = st.date_input("Data Emissione")

    mesi_disponibili = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

    tipo_periodo = st.radio(
        "Periodo di competenza",
        ["Mese/i", "Giorni specifici", "Dal giorno al giorno"],
        horizontal=True,
    )

    mesi_lavoro = []
    giorni_specifici = []
    mese_giorni = mesi_disponibili[10]
    data_inizio_prestazione = None
    data_fine_prestazione = None

    if tipo_periodo == "Mese/i":
        mesi_lavoro = st.multiselect("Mese/i di competenza", mesi_disponibili, default=["Novembre"])
        anno_lavoro = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
    elif tipo_periodo == "Giorni specifici":
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            mese_giorni = st.selectbox("Mese", mesi_disponibili, index=10)
        with col_g2:
            anno_lavoro = st.number_input("Anno", min_value=2024, max_value=2030, value=2026)
        giorni_specifici = st.multiselect("Giorno/i di prestazione", list(range(1, 32)))
    else:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_inizio_prestazione = st.date_input("Dal giorno", value=date.today(), key="data_inizio_prestazione")
        with col_d2:
            data_fine_prestazione = st.date_input("Al giorno", value=date.today(), key="data_fine_prestazione")

with col2:
    st.markdown("### Dati Cliente")
    cliente_nome = st.text_input("Ragione Sociale", CLIENTE.get("ragione_sociale", ""))
    cliente_indirizzo = st.text_input("Indirizzo Cliente", CLIENTE.get("indirizzo", ""))
    cliente_citta = st.text_input("Città Cliente", CLIENTE.get("citta", ""))
    cliente_piva = st.text_input("Partita IVA", CLIENTE.get("partita_iva", ""))
    importo_lordo = st.number_input(
        "Importo Lordo (€)", min_value=0.0, step=50.0, value=float(CLIENTE.get("importo_lordo", 500.0))
    )

# --- CALCOLI AUTOMATICI ---
ritenuta = importo_lordo * 0.20
netto = importo_lordo - ritenuta
bollo = 2.00 if importo_lordo > 77.47 else 0.00

if tipo_periodo == "Mese/i":
    mesi_join = "/".join(mesi_lavoro).upper() if mesi_lavoro else "[SELEZIONA ALMENO UN MESE]"
    periodo_frase = f"nel/i mese/i di {mesi_join} {anno_lavoro}"
    periodo_valido = bool(mesi_lavoro)
    periodo_errore = "Seleziona almeno un mese di competenza."
elif tipo_periodo == "Giorni specifici":
    if giorni_specifici:
        giorni_join = ", ".join(str(g) for g in sorted(giorni_specifici))
        periodo_frase = f"nel/i giorno/i {giorni_join} di {mese_giorni.upper()} {anno_lavoro}"
        periodo_valido = True
    else:
        periodo_frase = "[SELEZIONA ALMENO UN GIORNO]"
        periodo_valido = False
    periodo_errore = "Seleziona almeno un giorno di prestazione."
else:
    if data_inizio_prestazione and data_fine_prestazione and data_inizio_prestazione <= data_fine_prestazione:
        periodo_frase = f"dal {data_inizio_prestazione.strftime('%d/%m/%Y')} al {data_fine_prestazione.strftime('%d/%m/%Y')}"
        periodo_valido = True
    else:
        periodo_frase = "[INTERVALLO DI DATE NON VALIDO]"
        periodo_valido = False
    periodo_errore = "Imposta un intervallo di date valido (dal giorno precedente o uguale al giorno finale)."

bollo_dovuto = importo_lordo > 77.47
bollo_applicata = False
bollo_id = ""
bollo_data = None

if bollo_dovuto:
    st.markdown("### Marca da bollo")
    bollo_applicata = st.checkbox("Marca da bollo già applicata")
    if bollo_applicata:
        col_bollo_1, col_bollo_2 = st.columns(2)
        with col_bollo_1:
            bollo_id = st.text_input("Identificativo marca", "")
        with col_bollo_2:
            bollo_data = st.date_input("Data marca da bollo", value=None, key="data_marca_bollo")

# --- ANTEPRIMA RICEVUTA ---
st.divider()
st.markdown("### Anteprima Documento")

ricevuta_testo = f"""
**{mio_nome}** {indirizzo_mittente}  
C.f. {mio_cf}  
Data di nascita: {data_nascita_mittente.strftime('%d/%m/%Y')}  
{citta_mittente}  

---
**Ricevuta n° {n_ricevuta} del {data_ricevuta.strftime('%d/%m/%Y')}**

**Spett.le {cliente_nome}** {cliente_indirizzo} - {cliente_citta}
P.IVA {cliente_piva}

Il sottoscritto {mio_nome} dichiara di ricevere la somma lorda di **€. {importo_lordo:,.2f}** per {descrizione_prestazione} svolta {periodo_frase}.

| Voce | Importo |
| :--- | :--- |
| **Corrispettivo Lordo** | **€. {importo_lordo:,.2f}** |
| Ritenuta d'Acconto (20%) | €. {ritenuta:,.2f} |
| **NETTO A PAGARE** | **€. {netto:,.2f}** |

*IBAN per il bonifico: {mio_iban}*
"""

st.info(ricevuta_testo)

if not periodo_valido:
    st.warning(f"⚠️ {periodo_errore}")

if bollo > 0:
    st.warning("⚠️ Importo superiore a 77,47€: applicare marca da bollo da 2,00€")

if not REPORTLAB_AVAILABLE:
    st.error("Generazione PDF non disponibile: manca il pacchetto reportlab nell'interprete Python attuale.")
    st.code(f"{sys.executable} -m pip install reportlab")
    st.caption(f"Dettaglio errore: {REPORTLAB_ERROR}")

# Bottone Generazione Documento
if st.button("Genera Documento Finale"):
    if not periodo_valido:
        st.error(periodo_errore)
    elif bollo_dovuto and bollo_applicata and (not bollo_id.strip() or bollo_data is None):
        st.error("Se la marca da bollo è applicata, inserisci obbligatoriamente identificativo e data.")
    elif not REPORTLAB_AVAILABLE:
        st.error("Impossibile generare il PDF finché reportlab non è installato in questo Python.")
    else:
        pdf_bytes = genera_pdf_ricevuta(
            mio_nome=mio_nome,
            mio_cf=mio_cf,
            mio_iban=mio_iban,
            indirizzo_mittente=indirizzo_mittente,
            data_nascita_mittente=data_nascita_mittente,
            citta_mittente=citta_mittente,
            cliente_nome=cliente_nome,
            cliente_piva=cliente_piva,
            cliente_indirizzo=cliente_indirizzo,
            cliente_citta=cliente_citta,
            n_ricevuta=n_ricevuta,
            data_ricevuta=data_ricevuta,
            periodo_frase=periodo_frase,
            importo_lordo=importo_lordo,
            ritenuta=ritenuta,
            netto=netto,
            bollo_dovuto=bollo_dovuto,
            bollo_applicata=bollo_applicata,
            bollo_id=bollo_id,
            bollo_data=bollo_data,
            luogo_firma=luogo_firma,
            data_firma=data_firma,
            descrizione_prestazione=descrizione_prestazione,
            firma_bytes=firma_elaborata,
        )

        st.success("PDF generato con successo.")
        st.download_button(
            "Scarica ricevuta PDF",
            data=pdf_bytes,
            file_name=f"ricevuta_{n_ricevuta.replace('/', '_')}.pdf",
            mime="application/pdf",
        )