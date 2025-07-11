# prompts.py

extract_deceased_info_prompt = """
Task Requirements:

1. Filter Unnecessary Characters
    - Remove characters like (*, #, ~, etc.).

2. Case Sensitivity  
    - Don't change any case because I Identify fname and lname with case.
         
3. Extract Information About the Deceased Person
    - For "Deceased person full name": 
        - Extract from the beginning of the text.
    - For "Date of Birth": 
        - Format as dd/mm/yyyy.
    - For "Date of Death": 
        - Format as dd/mm/yyyy.
    - For "City":
        - City of the Deceased person. (only City) (domicile, domicilié, domiciliée, habitant, demeurant, etc...)
    - For "Department Number":
        - Department Number of City of the Deceased person.
    - For "City of death": 
        - Extract the city name of death.
    - For "Declarant Name": 
        - Extract from Déclarant section.
        - Extract the name of the relative.
        - not the relationship.
        - if there no relative name in Déclarant section then "".
        - hints : search for word like (fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...) in Déclarant section.
    - For "Declarant Address": 
        - Extract Address from the full address from the declaration section.
    - For "Declarant City": 
        - Extract only City of full address from the declaration section.
    - For "Declarant Address Zip code":
        - Return the Zip code of Declarant Address.
        - It may not be in the Text but return it yourself
    - For "Relation with Deceased person": 
        - return "" if the declarant is not a relative of deceased.
        - Extract from Déclarant section
        - Extract the relation of the Declarant.
        - e.g., fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, Epoux, Epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami, amie, etc...
    - For "Name of spouse": 
        - Search before Déclarant section.
        - Extract the name of the spouse.
        - hints : search for word like (époux, épouse, concubin, concubine, mari, femme, pacsé etc.) before Déclarant section.
        - skip divorce info.
    - For "Certificate notary name": 
        - return "" if not exist
        - Name of the notary mentioned after "Acte de notorieti"
        - omit the title "Maitre" and only include the name.
        
Output Format:
Return the results as a JSON object, strictly adhering to this structure:

json
{
    "about_deceased_person": {
        "Deceased person full name": "",
        "Date of Birth": "dd/mm/yyyy",
        "Date of Death": "dd/mm/yyyy",
        "City": "",
        "Department Number": "",
        "City of death": "",
        "Declarant Full Name": "",
        "Declarant Address": "",
        "Declarant City": "",
        "Declarant Address Zip code":"",
        "Relation with Deceased person": "",
        "Name of spouse": "",
        "Certificate notary name": ""
    }
}
    """

classify_declarant_prompt = """     
    - For "notary":
        - Return 1 if the word "Acte de notoriété" / "notoriete" is found in the text.
        - Note: If there is "mentions marginales" and contains the word Neant then return 0.
    - For "undertaker":
        - Return 1 if any of the following keywords are found:
            (Funéraire, Assistant funéraire , Assistante funéraire, Chef d'entreprise , Cheffe d'entreprise, Conseiller Funéraire , Conseillère Funéraire, Conservateur du Cimetière , Conservatrice du Cimetière, Conservateur du cimetière, Chef d'entreprise de Pompes Funèbres , Cheffe d'entreprise de Pompes Funèbres, Services Funéraires, Employé PF , Employée PF, Employé Pompes Funèbres , Employée Pompes Funèbres, Dirigeant de PF , Dirigeante de PF, Dirigeant de Pompes Funèbres , Dirigeante de Pompes Funèbres, Gérant de Société , Gérante de Société, Gérant de la société , Gérante de la société, Gérant , Gérante, Directeur d'agence , Directrice d'agence, Responsable des services, Responsable d'agence, Porteur funéraire, Pompes Funèbres, Pompe Funèbre, Opérateur Funéraire , Opératrice Funéraire, démarcheur etc...)
        - Search only in Déclarant section.
        - Otherwise, return 0.
    -for "hospital":
        - return 1 if the declarant is likely from a Hospital.
        - Return 1 if any of the following keywords are found:
            (Infirmier, Infirmière, Infirmiers, Infirmières, attache d'administration, Directeur d'hôpital, Directrice d'hôpital, Directeurs d'hôpital, Directrices d'hôpital, Directeur d'hôpital délégué, Directrice d'hôpital déléguée, Directeurs d'hôpital délégués, Directrices d'hôpital déléguées, Agent hospitalier, Agente hospitalière, Agents hospitaliers, Agentes hospitalières, Adjointe hospitalière, Adjoint hospitalier, Agent médico-administratif, Agente médico-administrative, Agents médico-administratifs, Agentes médico-administratives, Aide médico-psychologique, Aides médico-psychologiques, Cadre hospitalier, Cadre hospitalière, Cadres hospitaliers, Cadres hospitalières, Cadre hospitalier responsable, Cadre hospitalière responsable, Cadres hospitaliers responsables, Cadres hospitalières responsables, Praticien hospitalier, Praticienne hospitalière, Praticiens hospitaliers, Praticiennes hospitalièresetc, responsable du secteur Recettes, EPHAD ...)
        - Search only in Déclarant section.
        - Otherwise, return 0.
    - for "heir":
        - It is to check wheather a relative info of Deceased person exist in the text or not.
        - Analyze text properly. Don't return 1 for someone from the hospital or the police or an official from the Townhall or there relative.
        - Hints : search for word fils, fille, père, mère, frère, sœur, cousin, cousine, neveu, nièce, oncle, tante, epoux, epouse, petits fils, petite fille, compagne, compagnon, concubin, concubine, ex-époux, ex-épouse, ex-mari, ex-femme, ami or amie.
        - Return 1 if any of the word exist in the text.
        - Or Return 1 if there any relative of Deceased person name like same last name.
        - Search only in Déclarant section.
        - Otherwise, return 0.
        
return json:
{
    "notary": 0/1,
    "undertaker": 0/1,
    "hospital": 0/1,
    "heir": 0/1,
    "why?": name and relation if heir,
}
"""

undertaker_keywords = [
    "Funéraire",
    "Assistant funéraire",
    "Assistante funéraire",
    "Chef d'entreprise",
    "Cheffe d'entreprise",
    "Conseiller Funéraire",
    "Conseillère Funéraire",
    "Conservateur du Cimetière",
    "Conservatrice du Cimetière",
    "Conservateur du cimetière",
    "Chef d'entreprise de Pompes Funèbres",
    "Cheffe d'entreprise de Pompes Funèbres",
    "Services Funéraires",
    "chef d'agence",
    "Employé PF",
    "Employée PF",
    "Employé Pompes Funèbres",
    "Employée Pompes Funèbres",
    "Dirigeant de PF",
    "Dirigeante de PF",
    "Dirigeant de Pompes Funèbres",
    "Dirigeante de Pompes Funèbres",
    "Gérant de Société",
    "Gérante de Société",
    "Gérant de la société",
    "Gérante de la société",
    "Gérant",
    "Gérante",
    "Directeur d'agence",
    "Directrice d'agence",
    "Responsable des services",
    "Responsable d'agence",
    "Porteur funéraire",
    "Pompes Funèbres",
    "Pompe Funèbre",
    "Opérateur Funéraire",
    "Opératrice Funéraire",
    "chauffeur porteur",
    "Directrice commerciale",
    "démarcheur",
]
hospital_keywords = [
    "Vaguemestre",
    "gestionnaire admissions",
    "Infirmier",
    "hospital",
    "psychologique",
    "adjoint des cadres",
    "assistante de direction",
    "assistant de direction",
    "responsable du secteur recette",
    "administrati",
    "admissionniste",
    "accueil",
    "EPHAD",
]