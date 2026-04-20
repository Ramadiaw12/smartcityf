import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import hashlib
import warnings
warnings.filterwarnings('ignore')

# ============================================
# 1. CHARGER TON DATASET RÉEL
# ============================================
df = pd.read_csv('data/smart_city_final_dataset.csv')  # Remplace par ton vrai nom

print("=== 📊 CHARGEMENT DE TON DATASET ===")
print(f"Colonnes : {df.columns.tolist()}")
print(f"Maisons trouvées : {df['household_id'].unique()}")
print(f"Nombre de lignes : {len(df)}")

# ============================================
# 2. PRÉPARATION DES FEATURES
# ============================================
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['month'] = df['timestamp'].dt.month
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

feature_cols = ['hour', 'day_of_week', 'month', 'is_weekend', 'hour_sin', 'hour_cos']
target_col = 'future_consumption_kWh' if 'future_consumption_kWh' in df.columns else 'energy_consumption_kWh'

# ============================================
# 3. DICTIONNAIRES POUR TOUTES LES MAISONS
# ============================================
all_houses = sorted(df['household_id'].unique())
print(f"\n🏠 {len(all_houses)} maisons détectées : {all_houses}")

house_names = {
    1: "Maison Verte", 2: "Maison Bleue", 3: "Maison Orange", 
    4: "Maison Rouge", 5: "Maison Violette"
}
house_addresses = {
    1: "Rue des Oliviers", 2: "Boulevard Moulay Youssef", 
    3: "Avenue Hassan II", 4: "Rue Allal Ben Ahmed", 
    5: "Rue de la Liberté"
}
house_colors = {
    1: "#4CAF50", 2: "#2196F3", 3: "#FF9800", 4: "#E91E63", 5: "#9C27B0"
}

# ============================================
# 4. ENTRAÎNEMENT DES MODÈLES
# ============================================
models = {}
scalers = {}

for house_id in all_houses:
    house_df = df[df['household_id'] == house_id].dropna()
    if len(house_df) > 10:
        X = house_df[feature_cols]
        y = house_df[target_col]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_scaled, y)
        models[house_id] = model
        scalers[house_id] = scaler
        print(f"✅ Modèle Maison {house_id} - {house_names[house_id]} (R²: {model.score(X_scaled, y):.3f})")

# ============================================
# 5. GÉNÉRATION DES DONNÉES ET CALCUL DU BILAN
# ============================================
users_data = {}
predictions_data = {}
energy_balances = {}

# Facteur pour créer des déséquilibres (pour démontrer les transferts)
# Une maison surproduit, l'autre sous-produit
production_factors = {
    1: 1.5,   # Maison Verte - surproduction
    2: 0.6,   # Maison Bleue - sous-production
    3: 1.3,   # Maison Orange - surproduction
    4: 0.5,   # Maison Rouge - sous-production
    5: 1.1    # Maison Violette - léger surplus
}

for house_id in all_houses:
    house_df = df[df['household_id'] == house_id].sort_values('timestamp')
    
    # Consommation réelle (dernières 24 valeurs)
    real_consumption = house_df['energy_consumption_kWh'].tail(24).tolist()
    while len(real_consumption) < 24:
        real_consumption.insert(0, real_consumption[0] if real_consumption else 0.5)
    
    # Prédictions
    predictions = []
    last_timestamp = house_df['timestamp'].max()
    for i in range(1, 25):
        future_time = last_timestamp + timedelta(minutes=5 * i)
        future_features = pd.DataFrame([{
            'hour': future_time.hour, 'day_of_week': future_time.weekday(),
            'month': future_time.month, 'is_weekend': 1 if future_time.weekday() >= 5 else 0,
            'hour_sin': np.sin(2 * np.pi * future_time.hour / 24),
            'hour_cos': np.cos(2 * np.pi * future_time.hour / 24)
        }])
        if house_id in models:
            X_pred = future_features[feature_cols]
            X_pred_scaled = scalers[house_id].transform(X_pred)
            pred = models[house_id].predict(X_pred_scaled)[0]
        else:
            pred = np.mean(real_consumption) * (0.9 + np.random.rand() * 0.2)
        predictions.append(round(max(0.1, pred), 3))
    
    # Production solaire avec facteur de déséquilibre (pour créer des transferts!)
    solar_production = []
    for h in range(24):
        if 6 <= h <= 18:
            solar = (0.5 * np.sin(np.pi * (h - 6) / 12) + 0.2) * production_factors.get(house_id, 1.0)
        else:
            solar = 0
        solar_production.append(round(max(0, solar + np.random.rand() * 0.1), 2))
    
    # Bilan énergétique (production - consommation)
    total_consumption = sum(real_consumption)
    total_production = sum(solar_production)
    net_balance = round(total_production - total_consumption, 2)
    
    energy_balances[house_id] = {
        'house_name': house_names[house_id],
        'consumption': round(total_consumption, 2),
        'production': round(total_production, 2),
        'balance': net_balance,
        'status': 'surplus' if net_balance > 0 else 'deficit',
        'amount': abs(net_balance)
    }
    
    stats = {
        'total_consumption_today': round(total_consumption, 2),
        'avg_consumption': round(np.mean(house_df['energy_consumption_kWh']), 3),
        'peak_consumption': round(house_df['energy_consumption_kWh'].max(), 3),
        'total_production_today': round(total_production, 2),
        'energy_balance': net_balance,
        'efficiency_score': round(100 - (np.std(real_consumption) / np.mean(real_consumption) * 30), 1) if np.mean(real_consumption) > 0 else 70
    }
    
    users_data[f"maison{house_id}@smartcas.ma"] = {
        'user_email': f"maison{house_id}@smartcas.ma",
        'user_name': f"Propriétaire {house_names[house_id]}",
        'household_id': int(house_id),
        'house_name': house_names[house_id],
        'house_color': house_colors[house_id],
        'address': f"{house_addresses[house_id]}, Maarif, Casablanca",
        'hourly_consumption': [round(x, 3) for x in real_consumption],
        'solar_production': solar_production,
        'predictions': predictions,
        'stats': stats,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    print(f"\n📊 {house_names[house_id]}:")
    print(f"   Consommation: {total_consumption:.2f} kWh | Production: {total_production:.2f} kWh")
    print(f"   BILAN: {net_balance:+.2f} kWh ({'🔋 SURPLUS' if net_balance > 0 else '⚠️ DÉFICIT'})")

# ============================================
# 6. TRANSFERT D'ÉNERGIE OPTIMISÉ
# ============================================

print("\n" + "="*60)
print("🔄 CALCUL DES TRANSFERTS D'ÉNERGIE")
print("="*60)

# Séparer surplus et déficit
surplus_houses = [h for h in energy_balances.values() if h['status'] == 'surplus']
deficit_houses = [h for h in energy_balances.values() if h['status'] == 'deficit']

# Trier par quantité (du plus gros au plus petit)
surplus_houses.sort(key=lambda x: x['amount'], reverse=True)
deficit_houses.sort(key=lambda x: x['amount'], reverse=True)

print(f"\n🔋 Maisons avec SURPLUS (productrices) :")
for s in surplus_houses:
    print(f"   ✅ {s['house_name']}: +{s['amount']} kWh disponibles")

print(f"\n⚠️ Maisons avec DÉFICIT (consommatrices) :")
for d in deficit_houses:
    print(f"   ❌ {d['house_name']}: -{d['amount']} kWh nécessaires")

# Calculer les transferts
exchanges = []
remaining_surplus = {s['house_name']: s['amount'] for s in surplus_houses}
remaining_deficit = {d['house_name']: d['amount'] for d in deficit_houses}

for surplus in surplus_houses:
    for deficit in deficit_houses:
        if remaining_surplus[surplus['house_name']] <= 0:
            break
        if remaining_deficit[deficit['house_name']] <= 0:
            continue
        
        transfer_amount = min(remaining_surplus[surplus['house_name']], remaining_deficit[deficit['house_name']])
        
        if transfer_amount > 0.05:  # Seuil minimum pour un transfert
            # Trouver les IDs
            from_id = [k for k, v in house_names.items() if v == surplus['house_name']][0]
            to_id = [k for k, v in house_names.items() if v == deficit['house_name']][0]
            
            exchanges.append({
                'from_house': surplus['house_name'],
                'from_id': from_id,
                'to_house': deficit['house_name'],
                'to_id': to_id,
                'amount': round(transfer_amount, 2),
                'energy_saved': round(transfer_amount * 1.2, 2),  # kg CO2 économisés
                'timestamp': datetime.now().isoformat()
            })
            
            remaining_surplus[surplus['house_name']] -= transfer_amount
            remaining_deficit[deficit['house_name']] -= transfer_amount
            
            print(f"\n   🔄 TRANSFERT: {surplus['house_name']} → {deficit['house_name']}")
            print(f"      📦 Quantité: {transfer_amount} kWh")
            print(f"      💚 CO₂ économisé: {round(transfer_amount * 1.2, 2)} kg")

print("\n" + "="*60)
print("⚡ RÉSUMÉ DES TRANSFERTS")
print("="*60)

if exchanges:
    total_transferred = sum(e['amount'] for e in exchanges)
    total_co2 = sum(e['energy_saved'] for e in exchanges)
    print(f"   ✅ {len(exchanges)} transferts programmés")
    print(f"   📦 Total énergie transférée: {total_transferred} kWh")
    print(f"   💚 Total CO₂ économisé: {total_co2} kg")
else:
    print("   ⚠️ Aucun transfert trouvé - Vérification des bilans...")
    # Forcer un transfert de démonstration si nécessaire
    if len(surplus_houses) > 0 and len(deficit_houses) > 0:
        print("   🔄 Création d'un transfert de démonstration...")
        exchanges.append({
            'from_house': surplus_houses[0]['house_name'],
            'from_id': 1,
            'to_house': deficit_houses[0]['house_name'],
            'to_id': 2,
            'amount': 2.5,
            'energy_saved': 3.0,
            'timestamp': datetime.now().isoformat()
        })

# ============================================
# 7. SIMULATION BLOCKCHAIN
# ============================================

class BlockchainEnergyExchange:
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.create_genesis_block()
    
    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': datetime.now().isoformat(),
            'transactions': [],
            'previous_hash': '0',
            'hash': self.calculate_hash(0, [], '0')
        }
        self.chain.append(genesis_block)
    
    def calculate_hash(self, index, transactions, previous_hash):
        block_string = f"{index}{transactions}{previous_hash}{datetime.now()}"
        return hashlib.sha256(block_string.encode()).hexdigest()[:16]
    
    def add_transaction(self, from_house, to_house, amount_kwh, reason):
        transaction = {
            'from': from_house,
            'to': to_house,
            'amount_kwh': round(amount_kwh, 3),
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'transaction_id': hashlib.sha256(f"{from_house}{to_house}{amount_kwh}{datetime.now()}".encode()).hexdigest()[:8]
        }
        self.pending_transactions.append(transaction)
        return transaction
    
    def mine_block(self):
        if not self.pending_transactions:
            return None
        previous_block = self.chain[-1]
        new_block = {
            'index': len(self.chain),
            'timestamp': datetime.now().isoformat(),
            'transactions': self.pending_transactions.copy(),
            'previous_hash': previous_block['hash'],
            'hash': self.calculate_hash(len(self.chain), self.pending_transactions, previous_block['hash'])
        }
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block
    
    def get_all_transactions(self):
        """Récupère toutes les transactions de la blockchain"""
        all_transactions = []
        for block in self.chain:
            all_transactions.extend(block['transactions'])
        return all_transactions
    
    def get_transaction_count(self):
        """Compte le nombre total de transactions"""
        return len(self.get_all_transactions())

# Initialiser blockchain et enregistrer les transferts
blockchain = BlockchainEnergyExchange()
for exchange in exchanges:
    blockchain.add_transaction(
        from_house=exchange['from_house'],
        to_house=exchange['to_house'],
        amount_kwh=exchange['amount'],
        reason="Transfert d'énergie optimisé - SmartCas EnergyChain"
    )
blockchain.mine_block()

# ============================================
# 8. SAUVEGARDE
# ============================================

# Sauvegarder les données utilisateur
with open('user_energy_data.json', 'w', encoding='utf-8') as f:
    json.dump(users_data, f, indent=2, default=str)

# Sauvegarder les transferts blockchain
exchange_data = {
    'exchanges': exchanges,
    'blockchain': blockchain.chain,
    'total_energy_shared': sum(e['amount'] for e in exchanges) if exchanges else 0,
    'total_co2_saved': sum(e['energy_saved'] for e in exchanges) if exchanges else 0,
    'timestamp': datetime.now().isoformat(),
    'summary': {
        'surplus_houses': [{'name': s['house_name'], 'amount': s['amount']} for s in surplus_houses],
        'deficit_houses': [{'name': d['house_name'], 'amount': d['amount']} for d in deficit_houses]
    }
}

with open('blockchain_transactions.json', 'w', encoding='utf-8') as f:
    json.dump(exchange_data, f, indent=2, default=str)

# Créer les comptes utilisateurs
demo_users = []
for email, data in users_data.items():
    demo_users.append({
        'id': data['household_id'],
        'name': data['user_name'],
        'email': email,
        'password': 'demo123',
        'address': data['address'],
        'household_id': data['household_id']
    })

with open('demo_users.json', 'w', encoding='utf-8') as f:
    json.dump(demo_users, f, indent=2)

# ============================================
# 9. RAPPORT FINAL AVEC TRANSFERTS
# ============================================
print("\n" + "="*60)
print("📊 RAPPORT FINAL - SMARTCAS ENERGYCHAIN")
print("="*60)

print("\n🏠 BILAN PAR MAISON :")
for house_id, balance in energy_balances.items():
    status_icon = "🔋" if balance['status'] == 'surplus' else "⚠️"
    print(f"   {status_icon} {balance['house_name']}: {balance['balance']:+.2f} kWh")

print("\n🔄 TRANSFERTS RÉALISÉS :")
if exchanges:
    for ex in exchanges:
        print(f"   ✅ {ex['from_house']} → {ex['to_house']}: {ex['amount']} kWh")
else:
    print("   ⚠️ Aucun transfert - Vérifie les facteurs de production")

print(f"\n📈 STATISTIQUES GLOBALES :")
print(f"   Total énergie transférée: {exchange_data['total_energy_shared']:.2f} kWh")
print(f"   Total CO₂ économisé: {exchange_data['total_co2_saved']:.2f} kg")
print(f"   Transactions blockchain: {blockchain.get_transaction_count()}")

print("\n✅ Fichiers générés avec succès !")
print("\n🔗 MAINTENANT :")
print("   1. Ouvre energy_exchange.html pour voir les transferts")
print("   2. Connecte-toi avec maison1@smartcas.ma / demo123")
print("   3. Les flux d'énergie sont animés !")