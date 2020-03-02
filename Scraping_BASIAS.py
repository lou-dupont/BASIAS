from bs4 import BeautifulSoup
import requests
import re
import time
import json
import pandas as pd
from os import listdir
from os.path import isfile, join
import urllib.request
import os

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool


# ### Chargement et scraping
url_racine = "http://www.georisques.gouv.fr/webappReport/ws/basias/"
url_page = "http://fiches-risques.brgm.fr/georisques/basias-detaillee/"

# Création du répertoire des résultats par département
dossier_departement = 'BASIAS_departements/'
if not os.path.exists(dossier_departement) :
    os.mkdir(dossier_departement)

url_departements = url_racine + "departements"
departements = json.loads(requests.get(url_departements).text)

def trouverSitesDep(departement) :
    codeDep = departement['codedepartement']
    url_resultat = url_racine + "sites/_search?dept=%s&start=0&size=%s"
    nb_resultats = json.loads(requests.get(url_resultat%(codeDep, '1'), timeout=100).text)['count']
    print('Département %s : %s résultats'%(codeDep, nb_resultats))
    resultat_tous = json.loads(requests.get(url_resultat%(codeDep, str(nb_resultats)), timeout=100).text)
    
    with open(dossier_departement + 'sites_%s.json'%codeDep, 'w', encoding='utf-8') as outfile:
        json.dump(resultat_tous, outfile, ensure_ascii=False)

# Parallélisation à 10
pool = ThreadPool(10)
pool.map(trouverSitesDep, departements)
pool.close()
pool.join()


# Traitement du descriptif --> 130 Mo
# Premier fichier recap
departements = [f for f in listdir(dossier_departement) if isfile(join(dossier_departement, f))]
basias_light = []

def traiterSiteSimple(site):
    resultat = {}
    for k, v in site.items():
        if v is None : continue
        resultat[k] = v.replace('\r', '').replace('\n', '')
    return resultat

for departement in departements : 
    print(departement)
    with open(dossier_departement + departement, encoding='utf-8') as f:
        json_data = json.load(f)
        propre = [traiterSiteSimple(site) for site in json_data['data']]
        ordre_colonnes = list(propre[0].keys())
        basias_light_prov = pd.DataFrame(propre)
        basias_light_prov = basias_light_prov[ordre_colonnes]
        basias_light.append(basias_light_prov)
        
basias_light = pd.concat(basias_light, sort = False)
basias_light.to_csv("basias_light.csv", index=False, encoding='utf-8')


# ### Chargement des 300.000 pages
# Création du répertoire des résultats par département
dossier_pages = 'BASIAS_pages/'
if not os.path.exists(dossier_pages) :
    os.mkdir(dossier_pages)

# Création des dossiers régionaux
indices = basias_light['indiceDepartemental']
regions = list(set([x[:3] for x in indices]))
regions = sorted(regions)

for region in regions:
    if not os.path.exists(dossier_pages + region) :
        os.mkdir(dossier_pages + region)

def telechargerFichier(fichier) :
    url = "https://fiches-risques.brgm.fr/georisques/basias-detaillee/" + fichier
    nom_sauvegarde = 'BASIAS_pages/' + fichier[:3] + '/' + fichier + '.html'
    try : 
        urllib.request.urlretrieve(url, nom_sauvegarde)
    except Exception as error:
        print(error)

# Téléchargement très lent -- la version commentée ci-dessous est plus rapide
# for region in regions : 
    # indices_reg = [x for x in indices if x[:3] == region]
    # print("***", region, "***", len(indices_reg), "fiches")
    # dossier_region = dossier_pages + region
    # fichiers_sauvegardes = [f for f in listdir(dossier_region) if isfile(join(dossier_region, f))]
    # fichiers_manquants = [x for x in indices_reg if x + '.html' not in fichiers_sauvegardes]
    # if len(fichiers_manquants)>0 : 
        # print("\tNouveaux fichiers : " + len(fichiers_manquants))
    # for fichier in fichiers_manquants : 
        # telechargerFichier(fichier)

# # Parallélisation à 10 par seconde, environ 9h :)
for region in regions : 
    indices_reg = [x for x in indices if x[:3] == region]
    dossier_region = dossier_pages + region
    fichiers_sauvegardes = [f for f in listdir(dossier_region) if isfile(join(dossier_region, f))]
    fichiers_manquants = [x for x in indices_reg if x + '.html' not in fichiers_sauvegardes]
    print('INFO: Traitement de la région %s, %d fichiers manquants.' % (region, len(fichiers_manquants))) 
    if len(fichiers_manquants) > 0:
        pool = ThreadPool(10)
        results = pool.map(telechargerFichier, fichiers_manquants)
        pool.close()
        pool.join()
