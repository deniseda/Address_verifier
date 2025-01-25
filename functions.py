
import pandas as pd 
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from geopy.distance import geodesic
import folium
import requests



#### funzione per la verifica degli indirizzi


def verifica_indirizzi(lista_indirizzi):
    geolocator = Nominatim(user_agent='MyAPP')
    risultati = {}
    for ind in lista_indirizzi:
        try :
            location = geolocator.geocode(ind, timeout = 30, addressdetails=True)
            print(location)
            if location : 
                dettagli = location.raw.get('address',{})
                print(f"Dettagli indirizzo per '{ind}': {dettagli}")
                # citta
                citta = dettagli.get('city') or dettagli.get('village') or ('Non disponibile')
                # regione
                regione = dettagli.get('state', 'Non disponibile')
                # nazione
                stato = dettagli.get('country', 'Non disponibile')
                

                risultati[ind] = (True, location.latitude, location.longitude, citta, regione, stato)
            else:
                risultati[ind] =(False, None, None, None, None, None)
        except GeocoderTimedOut:
            risultati[ind] = (False, None, None, 'Timeout', 'Non disponibile', 'Non disponibile')
        except Exception as e:
            risultati[ind] = (False, None, None, f'Errore: {e}', 'Non disponibile', 'Non disponibile')
    
    return risultati

######## funzione per creare una mappa dinamica 

def mappa_dinamica(risultati):
    indirizzi_corretti = [val for val in risultati.values() if val[0]]
    if indirizzi_corretti:
        centro_lat, centro_long = indirizzi_corretti[0][1], indirizzi_corretti[0][2]
    else:
        centro_lat, centro_long = 0,0
    mappa = folium.Map(location=[centro_lat, centro_long], zoom_start=6)
 
 
    for indirizzo, (valido, lat,log, citta, regione, stato) in risultati.items():
        if valido:
            popup_info = f"Indirizzo : {indirizzo} <br> Città: {citta}  <br> Regione: {regione} <br> Stato: {stato} <br>  coordinate ({lat}, {log})"
            folium.Marker(
                [lat, log],
                popup=folium.Popup(popup_info, max_width=300),
                tooltip=f"{citta}"
            ).add_to(mappa)

    return mappa




####################################
### Funzione che calcola la distanza (km) tra due indirizzi se questi sono realmente esistenti
### esegue diversi check iniziali
# 1) entrambe le liste non devono essere vuote 
# 2) entrambe le liste devono avere le medesime dimensioni


def distance_coordinate_addresses(list_address1, list_address2):
    
    if not list_address1 or not list_address2:
        raise ValueError("Entrambe le liste devono essere popolate da almeno un indirizzo")
    
    if len(list_address1) != len(list_address2):
        raise ValueError("Le due liste sono di dimensione differente")
    

    geolocator = Nominatim(user_agent= "MyAPP", timeout= 10)
    distance = []
    coordinate = []

    for i , (indirizzo1, indirizzo2) in enumerate(zip(list_address1, list_address2), start=1):
        if not indirizzo1:
            raise ValueError(f"L'indirizzo in posizione {i} della prima lista è vuoto")
        location_ind1 = geolocator.geocode(indirizzo1)
        if location_ind1 is None:
            raise ValueError(f"L'indirizzo {indirizzo1} in posizione {i} della prima lista non è valido o non è stato trovato")
        
        ##### stessa cosa per gli indirizzi della seconda lista
        if not indirizzo2:
            raise ValueError(f"L'indirizzo in posizione {i} della seconda lista è vuoto")
        location_ind2 = geolocator.geocode(indirizzo2)
        if location_ind2 is None:
            raise ValueError(f"L'indirizzo {indirizzo2} in posizione {i} della seconda lista non è valido o non è stato trovato")
        
        coordinate_1 = (location_ind1.latitude, location_ind1.longitude)
        coordinate_2 = (location_ind2.latitude, location_ind2.longitude)
        distanze = geodesic(coordinate_1, coordinate_2).kilometers
        distance.append(distanze)
        coordinate.append((coordinate_1, coordinate_2))

    
    return distance, coordinate



######################
##### calcolo del centro mappa (html)

def centro_mappa(coordinates):
    latitudes = [coord[0] for pair in coordinates for coord in pair]
    longitudes = [coord[1] for pair in coordinates for coord in pair]
    
    center_lat = sum(latitudes) / len(latitudes)
    center_lon = sum(longitudes) / len(longitudes)
    
    return [center_lat, center_lon]




###########
## genera la mappa geografica (html) centrata dinamicamente vedi funzione Centro_mappa
## data una coppia di indirizzi traccia la distanza che vi intercorre sulla cartina


def mappa_distanze_geo(coordinate):

    map_center = centro_mappa(coordinate)
    

    my_map = folium.Map(location=map_center, zoom_start=4)
    
    # Aggiungi i marker e la linea per ogni coppia di coordinate
    for coord1, coord2 in coordinate:
        # Aggiungi i marker per i due punti
        folium.Marker(location=coord1, popup="Indirizzo 1", icon=folium.Icon(color='blue')).add_to(my_map)
        folium.Marker(location=coord2, popup="Indirizzo 2", icon=folium.Icon(color='red')).add_to(my_map)
        
        # Aggiungi una linea tra i due punti
        folium.PolyLine(locations=[coord1, coord2], color="black", weight=2.5, opacity=0.5).add_to(my_map)
    
    # Salva la mappa come file HTML
    nome_mappa = "mappa_distanze_tra_indirizzi.html"
    my_map.save(nome_mappa)
    print(f"Mappa salvata come {nome_mappa}")
    
    return nome_mappa




############################
## funzione per recuperare tutte le vie che presentano la parola chiave presente nella città

def cerca_vie_con_nome(citta, nome_via):
    # Query Overpass API per cercare vie con la parola chiave nella città
    # si basa su OSM
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    area["name"="{citta}"]->.searchArea;
    way["highway"]["name"~"{nome_via}", i](area.searchArea);
    out body;
    """
    # Esegui la richiesta
    response = requests.get(overpass_url, params={'data': query})
    
    if response.status_code == 200:
        dati = response.json()
        vie = set()  # mi evita di avere duplicati nel nome delle vie che ha identificato
        for elemento in dati.get("elements", []):
            if "tags" in elemento and "name" in elemento["tags"]:
                vie.add(elemento["tags"]["name"])  # aggiungo il nome trovato
        return sorted(vie)  #ordinamento
    else:
        return f"Errore: {response.status_code}"