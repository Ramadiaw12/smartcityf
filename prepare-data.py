import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
warnings.filterwarnings('ignore')

# ============================================
# 1. CHARGER TON DATASET RÉEL
# ============================================
df = pd.read_csv('data/smart_city_final_dataset.csv')  # Remplace par le nom de ton fichier

print("=== APERÇU DE TON DATASET ===")
print(df.head())
print(f"\nColonnes disponibles : {df.columns.tolist()}")
print(f"Nombre de lignes : {len(df)}")
print(f"Maisons uniques : {df['household_id'].unique()}")

# ============================================
# 2. NETTOYAGE ET PRÉPARATION DES FEATURES
# ============================================

# Convertir timestamp en datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Créer des features temporelles (utiles pour la prédiction)
df['hour'] = df['timestamp'].dt.hour
df['minute'] = df['timestamp'].dt.minute
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['month'] = df['timestamp'].dt.month
df['day'] = df['timestamp'].dt.day
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

# Encoder target_category (si utile)
target_mapping = {'Low': 0, 'Medium': 1, 'High': 2}
if 'target_category' in df.columns:
    df['target_encoded'] = df['target_category'].map(target_mapping)

print("\n=== FEATURES CRÉÉES ===")
print(f"Heures disponibles : {sorted(df['hour'].unique())}")
print(f"Jours de semaine : {sorted(df['day_of_week'].unique())}")

# ============================================
# 3. PRÉPARATION POUR L'ENTRAÎNEMENT
# ============================================

# Définir les features pour la prédiction
feature_cols = ['hour', 'day_of_week', 'month', 'is_weekend', 'hour_sin', 'hour_cos']

# Vérifier si on a des données de production solaire
if 'production_solaire' in df.columns:
    feature_cols.append('production_solaire')
    print("✅ Production solaire disponible dans le dataset")

# Cible : future_consumption_kWh (déjà dans ton dataset !)
target_col = 'future_consumption_kWh'

# Supprimer les lignes avec valeurs manquantes
df_clean = df[feature_cols + [target_col, 'household_id', 'timestamp', 'energy_consumption_kWh']].dropna()

X = df_clean[feature_cols]
y = df_clean[target_col]

print(f"\n=== PRÉPARATION POUR L'ENTRAÎNEMENT ===")
print(f"Features : {feature_cols}")
print(f"Taille du dataset d'entraînement : {len(X)} lignes")

# ============================================
# 4. ENTRAÎNEMENT DU MODÈLE DE PRÉDICTION
# ============================================

# Normalisation
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Entraînement du modèle
model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
model.fit(X_scaled, y)

# Évaluation
score = model.score(X_scaled, y)
print(f"\n✅ MODÈLE ENTRAÎNÉ AVEC SUCCÈS !")
print(f"   Score R² : {score:.4f}")
print(f"   Erreur moyenne : {np.mean(np.abs(model.predict(X_scaled) - y)):.4f} kWh")

# Sauvegarde du modèle et du scaler
joblib.dump(model, 'energy_prediction_model.pkl')
joblib.dump(scaler, 'feature_scaler.pkl')
print("   Modèle sauvegardé : energy_prediction_model.pkl")

# ============================================
# 5. GÉNÉRER LES DONNÉES POUR CHAQUE MAISON
# ============================================

# Récupérer toutes les maisons uniques
houses = df['household_id'].unique()
print(f"\n=== MAISONS DISPONIBLES ===")
print(f"Maisons : {houses}")

# Créer une correspondance utilisateur -> maison (pour la démo)
# Dans la réalité, tu lieras chaque compte utilisateur à un household_id
user_house_mapping = {}

# Générer les données pour chaque maison
users_data = {}

for house_id in houses:
    # Filtrer les données de cette maison uniquement
    house_df = df[df['household_id'] == house_id].sort_values('timestamp')
    
    if len(house_df) == 0:
        continue
    
    # Récupérer les 24 dernières heures de consommation
    last_24h = house_df.tail(24)
    hourly_consumption = last_24h['energy_consumption_kWh'].tolist()
    
    # Si pas assez de données, compléter
    while len(hourly_consumption) < 24:
        hourly_consumption.insert(0, hourly_consumption[0] if hourly_consumption else 0.3)
    
    # Faire des prédictions pour les 24 prochaines heures
    predictions = []
    
    # Obtenir le dernier timestamp
    last_timestamp = house_df['timestamp'].max()
    
    for i in range(1, 25):
        future_time = last_timestamp + timedelta(minutes=5 * i)  # Pas de 5 minutes comme dans ton dataset
        
        # Créer les features pour la prédiction
        future_features = pd.DataFrame([{
            'hour': future_time.hour,
            'minute': future_time.minute,
            'day_of_week': future_time.weekday(),
            'month': future_time.month,
            'day': future_time.day,
            'is_weekend': 1 if future_time.weekday() >= 5 else 0,
            'hour_sin': np.sin(2 * np.pi * future_time.hour / 24),
            'hour_cos': np.cos(2 * np.pi * future_time.hour / 24)
        }])
        
        # Ajouter production solaire si disponible
        if 'production_solaire' in df.columns:
            # Simuler production solaire (ou prendre la moyenne historique)
            if 6 <= future_time.hour <= 18:
                solar = 0.5 * np.sin(np.pi * (future_time.hour - 6) / 12)
                future_features['production_solaire'] = max(0, solar)
            else:
                future_features['production_solaire'] = 0
        else:
            future_features['production_solaire'] = 0
        
        # Prédire
        future_scaled = scaler.transform(future_features[feature_cols])
        pred = model.predict(future_scaled)[0]
        predictions.append(round(pred, 3))
    
    # Calculer les statistiques pour cette maison
    stats = {
        'total_consumption_today': house_df.tail(24)['energy_consumption_kWh'].sum(),
        'avg_consumption': house_df['energy_consumption_kWh'].mean(),
        'peak_consumption': house_df['energy_consumption_kWh'].max(),
        'min_consumption': house_df['energy_consumption_kWh'].min(),
        'total_production': house_df['production_solaire'].sum() if 'production_solaire' in house_df.columns else 0,
        'avg_flux': house_df['flux_energetique'].mean() if 'flux_energetique' in house_df.columns else 0,
        'efficiency_score': 100 * (1 - (house_df['energy_consumption_kWh'].std() / house_df['energy_consumption_kWh'].mean())) if house_df['energy_consumption_kWh'].mean() > 0 else 70
    }
    
    # Créer un email fictif pour chaque maison (pour la démo)
    user_email = f"maison{house_id}@smartcas.ma"
    user_house_mapping[user_email] = house_id
    
    users_data[user_email] = {
        'user_email': user_email,
        'user_name': f"Propriétaire Maison {house_id}",
        'household_id': int(house_id),
        'address': f"Quartier Maarif, Casablanca - Maison {house_id}",
        'hourly_consumption': hourly_consumption[-24:],  # Dernières 24 valeurs
        'predictions': predictions,
        'stats': stats,
        'historical_data': house_df[['timestamp', 'energy_consumption_kWh', 'production_solaire']].tail(100).to_dict('records'),
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    print(f"\n🏠 Maison {house_id}:")
    print(f"   Consommation moyenne: {stats['avg_consumption']:.3f} kWh")
    print(f"   Consommation totale aujourd'hui: {stats['total_consumption_today']:.2f} kWh")
    print(f"   Score efficacité: {stats['efficiency_score']:.1f}%")

# ============================================
# 6. SAUVEGARDER LES DONNÉES POUR LE DASHBOARD
# ============================================

with open('user_energy_data.json', 'w', encoding='utf-8') as f:
    json.dump(users_data, f, indent=2, default=str)

print(f"\n✅ DONNÉES GÉNÉRÉES POUR {len(users_data)} MAISONS")
print(f"   Fichier sauvegardé : user_energy_data.json")

# ============================================
# 7. GÉNÉRER UN COMPTE DE DÉMONSTRATION
# ============================================

# Créer des utilisateurs dans localStorage (format HTML/JS)
demo_users = []
for email, data in users_data.items():
    demo_users.append({
        'id': data['household_id'],
        'name': data['user_name'],
        'email': email,
        'password': 'demo123',  # Mot de passe par défaut
        'address': data['address'],
        'household_id': data['household_id']
    })

# Sauvegarder aussi dans un fichier JSON pour référence
with open('demo_users.json', 'w', encoding='utf-8') as f:
    json.dump(demo_users, f, indent=2)

print(f"\n👥 COMPTES DE DÉMONSTRATION CRÉÉS :")
for user in demo_users:
    print(f"   {user['email']} / mot de passe: demo123")

print("\n" + "="*50)
print("🎯 PROCHAINES ÉTAPES :")
print("1. Ouvre dashboard_personal.html dans ton navigateur")
print("2. Connecte-toi avec une des adresses email ci-dessus")
print("3. Mot de passe: demo123")
print("="*50)