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
df = pd.read_csv('ton_fichier.csv')  # Remplace par ton vrai nom de fichier

print("=== 📊 CHARGEMENT DE TON DATASET ===")
print(f"Colonnes : {df.columns.tolist()}")
print(f"Maisons trouvées : {df['household_id'].unique()}")
print(f"Nombre de lignes : {len(df)}")

# ============================================
# 2. PRÉPARATION DES FEATURES POUR LA PRÉDICTION
# ============================================
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['month'] = df['timestamp'].dt.month
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Features pour la prédiction
feature_cols = ['hour', 'day_of_week', 'month', 'is_weekend', 'hour_sin', 'hour_cos']
target_col = 'future_consumption_kWh' if 'future_consumption_kWh' in df.columns else 'energy_consumption_kWh'

# ============================================
# 3. ENTRAÎNEMENT D pulsaUN MODÈLE PAR MAISON
# ============================================
models = {}
scalers = {}

for house_id in df['household_id'].unique():
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
        print(f"✅ Modèle entraîné pour Maison {house_id} (R²: {model.score(X_scaled, y):.3f})")

# ============================================
# 4. GÉNÉRER LES PRÉDICTIONS POUR CHAQUE MAISON
# ============================================
house_names = {1: "Maison Verte", 2: "Maison Bleue", 3: "Maison Orange", 4: "Maison Rouge"}
house_addresses = {1: "Rue des Oliviers", 2: "Boulevard Moulay Youssef", 3: "Avenue Hassan II", 4: "Rue Allal Ben Ahmed"}

users_data = {}
predictions_data = {}

for house_id in df['household_id'].unique():
    house_df = df[df['household_id'] == house_id].sort_values('timestamp')
    
    # Consommation réelle (dernières 24h)
    real_consumption = house_df['energy_consumption_kWh'].tail(24).tolist()
    while len(real_consumption) < 24:
        real_consumption.insert(0, real_consumption[0] if real_consumption else 0.5)
    
    # Prédictions pour les 24 prochaines heures
    predictions = []
    last_timestamp = house_df['timestamp'].max()
    
    for i in range(1, 25):
        future_time = last_timestamp + timedelta(minutes=5 * i)
        future_features = pd.DataFrame([{
            'hour': future_time.hour,
            'day_of_week': future_time.weekday(),
            'month': future_time.month,
            'is_weekend': 1 if future_time.weekday() >= 5 else 0,
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
    
    # Calcul du bilan énergétique (production - consommation)
    # Simulation de production solaire (max entre 10h et 16h)
    current_hour = datetime.now().hour
    solar_production = []
    for h in range(24):
        if 6 <= h <= 18:
            solar = 0.5 * np.sin(np.pi * (h - 6) / 12) + 0.2
        else:
            solar = 0
        solar_production.append(round(solar + np.random.rand() * 0.1, 2))
    
    # Bilan énergétique = production solaire - consommation
    energy_balance = [round(solar_production[i] - real_consumption[i] if i < len(real_consumption) else -predictions[i], 3) for i in range(24)]
    
    stats = {
        'total_consumption_today': round(sum(real_consumption[-24:]), 2),
        'avg_consumption': round(np.mean(house_df['energy_consumption_kWh']), 3),
        'peak_consumption': round(house_df['energy_consumption_kWh'].max(), 3),
        'total_production_today': round(sum(solar_production), 2),
        'energy_balance': round(sum(energy_balance), 2),
        'efficiency_score': round(100 - (np.std(real_consumption) / np.mean(real_consumption) * 30), 1) if np.mean(real_consumption) > 0 else 70
    }
    
    users_data[f"maison{house_id}@smartcas.ma"] = {
        'user_email': f"maison{house_id}@smartcas.ma",
        'user_name': f"Propriétaire {house_names[house_id]}",
        'household_id': house_id,
        'house_name': house_names[house_id],
        'address': f"{house_addresses[house_id]}, Maarif, Casablanca",
        'hourly_consumption': [round(x, 3) for x in real_consumption],
        'solar_production': solar_production,
        'energy_balance': energy_balance,
        'predictions': predictions,
        'stats': stats,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    predictions_data[house_id] = {
        'house_name': house_names[house_id],
        'current_consumption': real_consumption[-1] if real_consumption else 0.5,
        'predicted_next_hour': predictions[0] if predictions else 0.5,
        'daily_prediction': sum(predictions),
        'energy_balance': stats['energy_balance']
    }

# ============================================
# 5. SIMULATION BLOCKCHAIN - ÉCHANGE D'ÉNERGIE
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
        transactions = []
        for block in self.chain:
            transactions.extend(block['transactions'])
        return transactions

# Calculer les surplus et déficits
def calculate_surplus_deficit(users_data):
    house_balances = {}
    for email, data in users_data.items():
        house_id = data['household_id']
        balance = data['stats']['energy_balance']
        house_balances[house_id] = {
            'house_name': data['house_name'],
            'balance': balance,
            'status': 'surplus' if balance > 0 else 'deficit',
            'amount': abs(balance)
        }
    return house_balances

# Déterminer les échanges optimaux
def calculate_optimal_exchanges(house_balances):
    surplus_houses = [h for h in house_balances.values() if h['status'] == 'surplus']
    deficit_houses = [h for h in house_balances.values() if h['status'] == 'deficit']
    
    # Trier par quantité
    surplus_houses.sort(key=lambda x: x['amount'], reverse=True)
    deficit_houses.sort(key=lambda x: x['amount'], reverse=True)
    
    exchanges = []
    for surplus in surplus_houses:
        remaining_surplus = surplus['amount']
        for deficit in deficit_houses:
            if remaining_surplus <= 0 or deficit['amount'] <= 0:
                continue
            
            exchange_amount = min(remaining_surplus, deficit['amount'])
            if exchange_amount > 0.1:  # Seuil minimum
                exchanges.append({
                    'from_house': surplus['house_name'],
                    'from_id': list(house_balances.keys())[list(h['house_name'] for h in house_balances.values()).index(surplus['house_name'])],
                    'to_house': deficit['house_name'],
                    'to_id': list(house_balances.keys())[list(h['house_name'] for h in house_balances.values()).index(deficit['house_name'])],
                    'amount': round(exchange_amount, 2),
                    'energy_saved': round(exchange_amount * 1.2, 2)  # CO2 économisé (kg)
                })
                remaining_surplus -= exchange_amount
                deficit['amount'] -= exchange_amount
    
    return exchanges

# Initialiser la blockchain
blockchain = BlockchainEnergyExchange()

# Calculer les échanges
house_balances = calculate_surplus_deficit(users_data)
exchanges = calculate_optimal_exchanges(house_balances)

# Enregistrer les échanges dans la blockchain
for exchange in exchanges:
    blockchain.add_transaction(
        from_house=exchange['from_house'],
        to_house=exchange['to_house'],
        amount_kwh=exchange['amount'],
        reason=f"Optimisation énergétique - Transfert automatique"
    )

# Miner le bloc
new_block = blockchain.mine_block()

# ============================================
# 6. SAUVEGARDER TOUTES LES DONNÉES
# ============================================

# Sauvegarder les données utilisateur
with open('user_energy_data.json', 'w', encoding='utf-8') as f:
    json.dump(users_data, f, indent=2, default=str)

# Sauvegarder les échanges blockchain
exchange_data = {
    'exchanges': exchanges,
    'blockchain': blockchain.chain,
    'total_energy_shared': sum(e['amount'] for e in exchanges),
    'total_co2_saved': sum(e['energy_saved'] for e in exchanges),
    'timestamp': datetime.now().isoformat()
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
# 7. RAPPORT FINAL
# ============================================
print("\n" + "="*60)
print("📊 RAPPORT D'ANALYSE ÉNERGÉTIQUE - QUARTIER MAARIF")
print("="*60)

print("\n🏠 CONSOMMATION PAR MAISON :")
for house_id, pred in predictions_data.items():
    print(f"   {pred['house_name']}: {pred['daily_prediction']:.2f} kWh/jour (prédit)")

print("\n⚡ BILAN ÉNERGÉTIQUE :")
for house_id, balance in house_balances.items():
    status_emoji = "🔋" if balance['status'] == 'surplus' else "⚠️"
    print(f"   {status_emoji} {balance['house_name']}: {balance['balance']:.2f} kWh ({balance['status']})")

print("\n🔄 ÉCHANGES D'ÉNERGIE OPTIMISÉS (via Blockchain) :")
for exchange in exchanges:
    print(f"   🔄 {exchange['from_house']} → {exchange['to_house']}: {exchange['amount']} kWh")
    print(f"      💚 Économie CO2: {exchange['energy_saved']} kg")

print(f"\n📊 STATISTIQUES GLOBALES :")
print(f"   Total énergie partagée: {exchange_data['total_energy_shared']:.2f} kWh")
print(f"   Total CO2 économisé: {exchange_data['total_co2_saved']:.2f} kg")
print(f"   Transactions blockchain: {len(blockchain.get_all_transactions())}")

print("\n✅ Fichiers générés :")
print("   - user_energy_data.json (données des maisons)")
print("   - blockchain_transactions.json (historique des échanges)")
print("   - demo_users.json (comptes de connexion)")

print("\n🔗 NOUVEAU : Page d'échange d'énergie disponible !")
print("   Ouvre energy_exchange.html pour voir les flux blockchain")