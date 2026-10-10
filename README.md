# Generatore Ricevute per Prestazione Occasionale

Applicazione web locale (Streamlit) per compilare e scaricare in PDF la **ricevuta di prestazione occasionale** con ritenuta d'acconto del 20%, marca da bollo e firma.

## Funzionalità

- Compilazione guidata dei dati del prestatore (mittente) e del cliente
- Calcolo automatico di **ritenuta d'acconto (20%)** e **netto a pagare**
- Gestione della **marca da bollo da 2,00 €** quando l'importo lordo supera 77,47 €
  (con identificativo e data se già applicata)
- Periodo di competenza flessibile: uno o più mesi, giorni specifici, oppure intervallo di date
- Caricamento della **firma** (PNG/JPG): lo sfondo viene reso trasparente automaticamente
- Anteprima del documento e download del **PDF** (A4)

## Requisiti

- Python 3.10 o superiore
- Dipendenze in [requirements.txt](requirements.txt): `streamlit`, `pillow`, `reportlab`

## Installazione

```bash
git clone https://github.com/emmesaux/Prestazione_Occasionale.git
cd Prestazione_Occasionale

python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Avvio

```bash
streamlit run app.py
```

L'app si apre su <http://localhost:8501>.

> Nota: un'app Streamlit si avvia sempre con `streamlit run app.py`, non con `python app.py`.

## Dati personali

I valori precompilati nei campi (nome, codice fiscale, IBAN, cliente, ...) vengono letti da file JSON:

| File | Contenuto | Su Git |
| :--- | :--- | :--- |
| `dati_personali.example.json` | Solo placeholder, modello da copiare | sì |
| `dati_personali_da_non_caricare_su_git.json` | I tuoi dati reali | **no** (in `.gitignore`) |

Per usare i tuoi dati:

1. Copia `dati_personali.example.json` in `dati_personali_da_non_caricare_su_git.json`
2. Sostituisci i placeholder con i tuoi valori
3. Riavvia l'app

Se il file personale non esiste, l'app usa automaticamente quello di esempio.
In ogni caso tutti i campi restano modificabili dall'interfaccia.

## Struttura del progetto

```
.
├── app.py                          # applicazione Streamlit e generazione PDF
├── dati_personali.example.json     # modello dati con placeholder
├── requirements.txt                # dipendenze Python
├── .gitignore                      # esclude venv e dati personali
└── README.md
```

## Come funziona il calcolo

| Voce | Formula |
| :--- | :--- |
| Ritenuta d'acconto | `lordo × 20%` |
| Netto a pagare | `lordo − ritenuta` |
| Marca da bollo | 2,00 € se `lordo > 77,47 €` |

## Avvertenza

Questo strumento genera un documento a partire dai dati inseriti e non costituisce
consulenza fiscale. Verifica con il tuo commercialista che il regime di prestazione
occasionale e le dichiarazioni riportate nel documento siano corretti per il tuo caso.
