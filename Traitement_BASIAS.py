from os import listdir
from os.path import isfile, join
import os
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime

dossier_pages = 'BASIAS_pages/'
dossiers_regions = os.listdir(dossier_pages)

# Création du répertoire des résultats par région
dossier_resultats = 'BASIAS_resultats/'
if not os.path.exists(dossier_resultats):
    os.mkdir(dossier_resultats)


def nettoyerChamp(string) :
    string = re.sub("\xa0", " ", string)
    string = re.sub("\n", " ", string)
    string = re.sub('(.*)\\.(\s+|)$', '\\1', string)
    string = string.strip()
    return(string)

def extraireInfo(balTitre, chaine) :
    try : 
        info = [x for x in balTitre if x.text.startswith(chaine)][0].findNext('td').text
    except : 
        return('')
    return(info)

def traiterTableauSuivant(balTitre, chaine, colonnes) :     
    info = []
    try :
        tableau = [x for x in balTitre if x.text.startswith(chaine)][0].findNext("table")
    except : 
        return('')
    corps = tableau.find_all('tr')[1:]
    for ligne in corps :
        info_elem = {}
        ligne = ligne.find_all('td')
        ligne = [x.text for x in ligne]

        for i in range(len(ligne)) :
            if ligne[i] == '' : continue
            info_elem[colonnes[i]] = ligne[i]
        info.append(info_elem)

    return(info)

def traiterTableau(tableaux, chaine, colonnes) : 
    info = []
    try :
        tableau = [x for x in tableaux if chaine in x.text][0]
    except : 
        return('')

    corps = tableau.find_all('tr')[1:]
    for ligne in corps :
        info_elem = {}
        ligne = ligne.find_all('td')
        ligne = [x.text for x in ligne]

        for i in range(len(colonnes)) :
            info_elem[colonnes[i]] = ligne[i]
        info.append(info_elem)

    return(info)

def extraireCommentaire (balSec, section) :
    try : 
        div = [x for x in balSec if x.text.startswith(chaine)][0].findPrevious('div')
        info = div.find(text = lambda value: value and value.startswith("Commentaire"))
        info = info.findNext('td').text
    except : 
        info = ''
    return(info)

def allegerSection (section) : 
    cles_vides = []
    for cle in section :
        if section[cle] in ('', [], [''], {}) :
            cles_vides.append(cle)
    for cle in cles_vides : 
        del(section[cle])
    return(section)

def traiterPage (page) :
    # Lecture de la page
    raw_page = open(page, encoding="utf-8")
    content = BeautifulSoup(raw_page, "lxml")
    infos = {}
    balStrong = content.findAll('td', {"valign" : "top"}, text = re.compile(":$"))
    balSection = content.findAll('h3')
    balTableau = content.findAll('table', {"class" : "data"})
    
    # 1- Identification du site
    identification = {}
    identification["identifiant_site"] = content.find('h1', {"class" : "with-tabs"}).text
    identification["unite_gestionnaire"] = extraireInfo(balStrong, "Unité gestionnaire")
    identification["date_creation_fiche"] = extraireInfo(balStrong, "Date de création de la fiche")
    identification["noms_usuels"] = extraireInfo(balStrong, "Nom(s) usuel(s)")
    identification["raison_sociale"] = traiterTableauSuivant(balStrong, "Raison(s) sociale(s)",
                                                           ["nom", "date_connue"])
    identification["etat_connaissance"] = extraireInfo(balStrong, "Etat de connaissance")
    identification["visite_site"] = extraireInfo(balStrong, "Visite du site")
    identification["sieges_sociaux"] = traiterTableauSuivant(balStrong, "Siège(s) social(aux)",
                                                         ["nom", "date"])
    identification["sous_surveillance"] = extraireInfo(balStrong, "Sous surveillance")
    identification["modificateurs"] = traiterTableauSuivant(balStrong, "Modificateur(s) de la fiche",
                                                         ["nom", "date"])
    identification["autres_identifications"] = traiterTableauSuivant(balStrong, "Autre(s) identification(s)",
                                                         ["numero", "organisme_bd_associe"])
    identification['commentaire'] = extraireCommentaire(balSection, "1 - Identification du site")

    # 2- Consultation
    consultation = {}
    consultation['consultation_sd_ct'] = traiterTableauSuivant(balStrong, 'Consultation des services déconcentrés',
                                    ['nom_service', 'consultation_service', 'date_consultation_service',
                                    'reponse_service', 'date_reponse_service'])
    consultation['commentaire'] = extraireCommentaire(balSection, "2 - Consultation à propos du site")

    # 3-Localisation
    localisation = {}
    localisation['adresses'] = traiterTableauSuivant(balStrong, "Adresses",
                            ['numero', 'bis_ter', 'type_voie', 'nom_voie', 'date_modification'])
    localisation['derniere_adresse'] = extraireInfo(balStrong, 'Dernière adresse')
    localisation['localisation'] = extraireInfo(balStrong, 'Localisation')
    localisation['code_insee'] = extraireInfo(balStrong, 'Code INSEE')
    localisation['commune_principale'] = extraireInfo(balStrong, 'Commune principale')
    localisation['zone_lambert_initiale'] = extraireInfo(balStrong, 'Zone Lambert initiale')
    localisation['precision_centroide'] = extraireInfo(balStrong, 'Précision centroïde')

    coordonnees = {}
    try : 
        tableau = [x for x in balTableau if "Projection" in x.text][0]
        X = tableau.find_all('tr')[1]
        Y = tableau.find_all('tr')[2]

        X = [x.text for x in X.find_all('td')]
        Y = [y.text for y in Y.find_all('td')]
        coordonnees['L_zone_centroide'] = [X[0], Y[0]]
        coordonnees['L2e_centroide'] = [X[1], Y[1]]
        coordonnees['L93_centroide'] = [X[2], Y[2]]
        coordonnees['L2e_adresse'] = [X[3], Y[3]]
        localisation['coordonnees'] = coordonnees
    except : 
        pass

    localisation['commentaire'] = extraireCommentaire(balSection, "3 - Localisation du site")

    # Cartes et plans consultés
    localisation['cartes'] = traiterTableauSuivant(balStrong, "Carte(s) et plan(s)",
                            ["carte", "echelle", "annee_edition", "presence_site", "reference_dossier"])

    # Autres communes
    localisation['autres_communes_concernees'] = traiterTableauSuivant(balStrong, "Autre(s) commune(s) concernée(s)",
                            ["code_insee", "nom", "arrondissement"])
    localisation['altitude_m'] = extraireInfo(balStrong, "Altitude (m)")
    localisation['precision_altitude_z'] = extraireInfo(balStrong, "Précision altitude (Z)")
    localisation['carte_geologique'] = traiterTableauSuivant(balStrong, "Carte géologique",
                            ["carte", "numero", "huitieme"])

    # 4- Propriétaires du site
    proprietaires = {}
    proprietaires['proprietaires'] = traiterTableauSuivant(balStrong, "Propriétaires",
                                                   ["nom", "date_reference", "type", "exploitant"])
    proprietaires['nombre_proprietaires_actuels'] = extraireInfo(balStrong, "Nombre de propriétaires")
    proprietaires['cadastre'] = traiterTableauSuivant(balStrong, "Cadastre :",
                            ['nom', 'date', 'echelle', 'precision', 'section', 'num_parcelle'])
    proprietaires['commentaire'] = extraireCommentaire(balSection, "4 - Propriété du site")

    # 5- Activités du site
    activites = {}
    activites['etat_occupation_site'] = extraireInfo(balStrong, "Etat d'occupation")
    activites['date_premiere_activite'] = extraireInfo(balStrong, "Date de première activité")
    activites['date_fin_activite'] = extraireInfo(balStrong, "Date de fin d'activité")
    activites['origine_date'] = extraireInfo(balStrong, "Origine de la date")
    activites['historique_activites'] = traiterTableauSuivant(balStrong, "Historique des activités", 
                                ['libelle_activite', 'code_activite', 
                                'date_debut', 'date_fin', 'importance', 'groupe_sei', 
                                 'origine_date', 'ref_dossier', 'autres_infos'])
    activites["accidents"] = traiterTableauSuivant(balStrong, "Accidents", 
                                          ["date", "type_accident", "type_pollution", "milieu_touche", "impact", "reference_rapport"])

    activites['exploitants'] = traiterTableauSuivant(balStrong, 'Exploitant(s)',
                                             ['nom_raison_sociale', 'date_debut', 'date_fin'])
    activites['commentaire'] = extraireCommentaire(balSection, "5 - Activités du site")

    # 6- Utilisations et projets
    utilisation = {}
    utilisation['nombre_utilisateurs_actuels'] = extraireInfo(balStrong, "Nombre d'utilisateur(s)")
    utilisation['site_friche'] = extraireInfo(balStrong, "Site en friche")
    utilisation['site_reamenage'] = extraireInfo(balStrong, "Site réaménagé")
    utilisation['reamenagement_sensible'] = extraireInfo(balStrong, "Réaménagement sensible")
    utilisation['code_pos'] = extraireInfo(balStrong, "Code POS")
    utilisation['surface_batie'] = extraireInfo(balStrong, "Surface bâtie")
    utilisation['surface_totale'] = extraireInfo(balStrong, "Surface totale")
    utilisation['type_reamenagement'] = extraireInfo(balStrong, "Type de réaménagement")
    utilisation['projet_reamenagement'] = extraireInfo(balStrong, "Projet de réaménagement")
    utilisation['commentaire'] = extraireCommentaire(balSection, "6 - Utilisations et projets")

    ### 7- Utilisateurs
    utilisateurs = {}
    utilisateurs['utilisateurs'] = traiterTableauSuivant(balStrong, "Utilisateurs :", 
                                                         ["nom", "type", "statut"])
    utilisateurs['commentaire'] = extraireCommentaire(balSection, "7 - Utilisateurs")

    ### 8- Environnement
    environnement = {}
    environnement['milieu_implantation'] = extraireInfo(balStrong, "Milieu d'implantation")
    environnement['reference_bss'] = extraireInfo(balStrong, "Référence BSS")
    environnement['captage_aep'] = extraireInfo(balStrong, "Captage AEP")
    environnement['milieu_aep'] = extraireInfo(balStrong, "Milieu AEP")
    environnement['position_aep'] = extraireInfo(balStrong, "Position AEP")
    environnement['distance_captage_aep'] = extraireInfo(balStrong, "Distance captage AEP")
    environnement['type_nappe'] = extraireInfo(balStrong, "Type de nappe")
    environnement['type_aquifere'] = extraireInfo(balStrong, "Type d'aquifère")
    environnement['nom_nappe'] = extraireInfo(balStrong, "Nom de la nappe")
    environnement['profondeur_minimale'] = extraireInfo(balStrong, "Profondeur minimale")
    environnement['amplitude_piezo'] = extraireInfo(balStrong, "Amplitude piézo")
    environnement['perimetre_protection'] = extraireInfo(balStrong, "Périmètre de protection")
    environnement['formation_superficielle'] = extraireInfo(balStrong, "Formation superficielle")
    environnement['substratum'] = extraireInfo(balStrong, "Substratum")
    environnement['zones_contraintes'] = traiterTableauSuivant(balStrong, "Zones de contraintes",
                                        ["type_zone", "distance_m", "commentaires"])
    environnement['nom_nappe'] = extraireInfo(balStrong, "Nom de la nappe")
    environnement['code_systeme_aquifere'] = extraireInfo(balStrong, "Code du système aquifère")
    environnement['nom_systeme_aquifere'] = extraireInfo(balStrong, "Nom du système aquifère")
    environnement['coefficient_permeabilite'] = extraireInfo(balStrong, "Coefficient de perméabilité")
    environnement['reference_etude'] = extraireInfo(balStrong, "référence étude :")
    environnement['commentaire'] = extraireCommentaire(balSection, "8 - Environnement")

    # 9- Etudes et actions
    etudes = {}
    etudes['etudes_connues'] = extraireInfo(balStrong, "Etude(s) connue(s)")
    etudes['requalification_paysagere_connue'] = extraireInfo(balStrong, "Requalification paysagère")
    
    etudes["decisions"] = traiterTableau(balTableau, "Décision", ["type", "date", "nature", "decision"])
    etudes["actions"] = traiterTableau(balTableau, "Test de sélection des sites", 
                                ["selection_site", "test", "date_premiere_etude", "decision"])

    # 10- Documents associés
    documents = {}

    # 11- Sources d'informations
    sources_information = {}
    sources_information['principale'] = extraireInfo(balStrong, "Source d'information")
    sources_information['autres'] = extraireInfo(balStrong, "Autre(s) source(s)")
    sources_information["chronologie"] = extraireInfo(balStrong, "Chronologie de l'information")
    sources_information['donnees_complementaires'] = extraireInfo(balStrong, "Donnée(s) complémentaire(s)")

    # 12- Synthèse historique
    infos['synthese_historique'] = extraireInfo(balStrong, "Historique :").split('\n')

    # 13- Etudes et actions BASOL - exemple LIM2300058
    # On renvoie à Basol plutot que de remonter toutes les infos
    infos['identifiant_basol'] = extraireInfo(balStrong, 'Identifiant')

    infos['identification'] = allegerSection(identification)
    infos['consultation'] = allegerSection(consultation)
    infos['localisation']  = allegerSection(localisation)
    infos['proprietaires'] = allegerSection(proprietaires)
    infos['activites']  = allegerSection(activites)
    infos["utilisations"] = allegerSection(utilisation)
    infos["utilisateurs"]  = allegerSection(utilisateurs)
    infos["environnement"]  = allegerSection(environnement)
    infos["etudes"]  = allegerSection(etudes)
    infos["documents"]  = allegerSection(documents)
    infos["sources_information"]  = allegerSection(sources_information)
    
    infos = allegerSection(infos)
    return(infos)


# Extraction de toutes les informations
for region in dossiers_regions : 
    print(region)
    chemin = 'BASIAS_pages/%s/' % region
    fichiers = [chemin + f for f in listdir(chemin) if isfile(join(chemin, f))]
    
    print(datetime.now())
    with open("BASIAS_resultats/BASIAS_%s.txt" % region, 'w') as f:
        for fichier in fichiers : 
            f.write(json.dumps(traiterPage(fichier)) + "\n")
    print(datetime.now())

# Vérification du nombre de lignes
for region in dossiers_regions :
    chemin = 'BASIAS_pages/%s/' % region
    fichiers = [chemin + f for f in listdir(chemin) if isfile(join(chemin, f))]
    with open("BASIAS_resultats/BASIAS_%s.txt" % region, 'r') as f:
        for i, l in enumerate(f):
            pass
    print(region + " " + ("Erreur" if i + 1 != len(fichiers) else "valide"))

