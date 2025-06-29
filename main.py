#!/usr/bin/env python3
"""
Script d'import pour Grocy
Importe des produits avec leurs unités, emplacements et groupes depuis un fichier CSV
"""

import requests
import csv
import json
from typing import Dict, List, Optional

class GrocyImporter:
    def __init__(self, grocy_url: str, api_key: str):
        """
        Initialise l'importeur Grocy
        
        Args:
            grocy_url: URL de votre instance Grocy (ex: http://localhost:9283)
            api_key: Clé API Grocy (à générer dans les paramètres)
        """
        self.base_url = grocy_url.rstrip('/')
        self.headers = {
            'GROCY-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
        
        # Cache pour éviter les doublons
        self.units_cache = {}
        self.locations_cache = {}
        self.product_groups_cache = {}
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Effectue une requête HTTP vers l'API Grocy"""
        url = f"{self.base_url}/api/{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
        
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la requête {method} {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Réponse du serveur: {e.response.text}")
            raise
    
    def load_existing_data(self):
        """Charge les données existantes pour éviter les doublons"""
        print("Chargement des données existantes...")
        
        # Charger les unités existantes
        units = self._make_request('GET', 'objects/quantity_units')
        self.units_cache = {unit['name']: unit['id'] for unit in units}
        
        # Charger les emplacements existants
        locations = self._make_request('GET', 'objects/locations')
        self.locations_cache = {loc['name']: loc['id'] for loc in locations}
        
        # Charger les groupes de produits existants
        groups = self._make_request('GET', 'objects/product_groups')
        self.product_groups_cache = {group['name']: group['id'] for group in groups}
        
        print(f"Chargé: {len(self.units_cache)} unités, {len(self.locations_cache)} emplacements, {len(self.product_groups_cache)} groupes")
    
    def create_quantity_unit(self, name: str) -> int:
        """Crée une unité de quantité si elle n'existe pas"""
        if name in self.units_cache:
            return self.units_cache[name]
        
        print(f"Création de l'unité: {name}")
        data = {
            'name': name,
            'description': f'Unité {name}',
            'name_plural': name + 's' if not name.endswith('s') else name
        }
        
        result = self._make_request('POST', 'objects/quantity_units', data)
        unit_id = result['created_object_id']
        self.units_cache[name] = unit_id
        return unit_id
    
    def create_location(self, name: str) -> int:
        """Crée un emplacement s'il n'existe pas"""
        if name in self.locations_cache:
            return self.locations_cache[name]
        
        print(f"Création de l'emplacement: {name}")
        data = {
            'name': name,
            'description': f'Emplacement {name}'
        }
        
        result = self._make_request('POST', 'objects/locations', data)
        location_id = result['created_object_id']
        self.locations_cache[name] = location_id
        return location_id
    
    def create_product_group(self, name: str) -> int:
        """Crée un groupe de produits s'il n'existe pas"""
        if name in self.product_groups_cache:
            return self.product_groups_cache[name]
        
        print(f"Création du groupe de produits: {name}")
        data = {
            'name': name,
            'description': f'Groupe {name}'
        }
        
        result = self._make_request('POST', 'objects/product_groups', data)
        group_id = result['created_object_id']
        self.product_groups_cache[name] = group_id
        return group_id
    
    def create_product(self, name: str, unit_id: int, location_id: int, group_id: int, min_stock: float) -> int:
        """Crée un produit"""
        print(f"Création du produit: {name}")
        data = {
            'name': name,
            'description': f'Produit {name}',
            'location_id': location_id,
            'qu_id_stock': unit_id,
            'qu_id_purchase': unit_id,
            'min_stock_amount': min_stock,
            'product_group_id': group_id,
            'enable_tare_weight_handling': 0
        }
        
        result = self._make_request('POST', 'objects/products', data)
        return result['created_object_id']
    
    def import_from_csv(self, csv_file: str):
        """Importe les produits depuis un fichier CSV"""
        print(f"Import depuis le fichier: {csv_file}")
        
        # Charger les données existantes
        self.load_existing_data()
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    name = row['name'].strip()
                    unit_name = row['qu_unit_name'].strip()
                    amount = float(row['qu_amount'])
                    location_name = row['location_name'].strip()
                    group_name = row['product_group_name'].strip()
                    
                    print(f"\nTraitement: {name}")
                    
                    # Créer/récupérer les IDs nécessaires
                    unit_id = self.create_quantity_unit(unit_name)
                    location_id = self.create_location(location_name)
                    group_id = self.create_product_group(group_name)
                    
                    # Créer le produit
                    product_id = self.create_product(name, unit_id, location_id, group_id, amount)
                    print(f"✓ Produit créé avec l'ID: {product_id}")
                    
                except Exception as e:
                    print(f"✗ Erreur lors du traitement de {name}: {e}")
                    continue
        
        print("\n✓ Import terminé!")

def main():
    """Fonction principale"""
    # Configuration - À MODIFIER selon votre installation
    GROCY_URL = "http://localhost:9283"  # URL de votre instance Grocy
    API_KEY = "your_api_key_here"        # Votre clé API Grocy
    CSV_FILE = "products.csv"            # Nom de votre fichier CSV
    
    # Vérification de la configuration
    if API_KEY == "your_api_key_here":
        print("ATTENTION: Vous devez configurer votre clé API!")
        print("1. Connectez-vous à Grocy")
        print("2. Allez dans Paramètres > Gérer les clés API")
        print("3. Créez une nouvelle clé API")
        print("4. Remplacez 'your_api_key_here' par votre clé dans ce script")
        return
    
    try:
        # Créer l'importeur et lancer l'import
        importer = GrocyImporter(GROCY_URL, API_KEY)
        importer.import_from_csv(CSV_FILE)
        
    except FileNotFoundError:
        print(f"Fichier {CSV_FILE} non trouvé!")
        print("Assurez-vous que le fichier CSV est dans le même dossier que ce script.")
    except Exception as e:
        print(f"Erreur générale: {e}")

if __name__ == "__main__":
    main()