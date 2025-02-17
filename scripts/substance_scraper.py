import requests
import pandas as pd
from bs4 import BeautifulSoup

def fetch_pubchem_data(substance_name):
    """Fetch CAS number, synonyms, and sources from PubChem API."""
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
    url = f"{base_url}{substance_name}/property/IUPACName,MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES/JSON"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        try:
            compound_id = data['PropertyTable']['Properties'][0]['CID']
            cas_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{compound_id}/synonyms/JSON"
            cas_response = requests.get(cas_url)
            if cas_response.status_code == 200:
                synonyms_data = cas_response.json()
                synonyms = synonyms_data['InformationList']['Information'][0]['Synonym']
                cas_number = next((s for s in synonyms if s.count('-') == 2 and s.replace('-', '').isdigit()), None)
                return {
                    "Substance": substance_name,
                    "CAS Number": cas_number,
                    "Synonyms": synonyms,
                    "PubChem CID": compound_id
                }
        except KeyError:
            return {"Substance": substance_name, "CAS Number": None, "Synonyms": None, "PubChem CID": None}
    return {"Substance": substance_name, "CAS Number": None, "Synonyms": None, "PubChem CID": None}

def scrape_dea_scheduled_substances():
    """Scrape the DEA Controlled Substance List from their website."""
    url = "https://www.deadiversion.usdoj.gov/schedules/orangebook/orangebook.pdf"
    response = requests.get(url)
    if response.status_code == 200:
        with open("data/orangebook.pdf", "wb") as file:
            file.write(response.content)
        return "DEA Controlled Substance List downloaded successfully."
    return "Failed to retrieve DEA Controlled Substance List."

def main():
    substances = ["Fentanyl", "Acetylfentanyl", "Carfentanil"]  # Example substances
    results = []
    for substance in substances:
        results.append(fetch_pubchem_data(substance))
    
    df = pd.DataFrame(results)
    df.to_csv("data/chemical_identifiers.csv", index=False)
    print("Data saved to data/chemical_identifiers.csv")
    
    dea_status = scrape_dea_scheduled_substances()
    print(dea_status)

if __name__ == "__main__":
    main()
