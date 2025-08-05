# Vivibot - Prédicteur de Cartes Baccarat - Version Corrigée

Bot Telegram spécialisé dans l'analyse et la prédiction automatique des jeux Baccarat.

## ✅ CORRECTION IMPORTANTE

**SYSTÈME DE PRÉDICTION AUTOMATIQUE :**
- Détecte 3 costumes différents (♠️♥️♦️♣️) **UNIQUEMENT dans le PREMIER parenthèse**
- Génère automatiquement une prédiction pour le numéro suivant (+1)
- Format: `🔵[N+1] 🔵3K: statut :⏳`

## Fonctionnalités Principales

### 🔮 Système de Prédiction Automatique
- **CORRECTION** : Analyse SEULEMENT le premier parenthèse pour 3 costumes différents
- Génère automatiquement une prédiction pour le numéro suivant (+1)
- Format: `🔵[N+1] 🔵3K: statut :⏳`

### 🔍 Système de Vérification
- Vérifie les prédictions existantes sur messages édités
- Analyse SEULEMENT le premier parenthèse pour validation
- Statuts: ✅0️⃣/✅1️⃣/✅2️⃣/✅3️⃣ ou ❌⭕

### 📊 Gestion des Messages
- Messages temporaires (⏰▶️🕐➡️): Stockés et ignorés
- Messages finaux (✅🔰): Traités pour prédiction/vérification
- Double protection contre les doublons

## Configuration Déploiement

### Variables d'environnement requises:
```
BOT_TOKEN=votre_token_telegram
WEBHOOK_URL=https://votre-app.onrender.com (optionnel)
PORT=10000
```

### Canal surveillé:
- **Baccarat Kouamé** (-1002682552255)
- **Groupe de statistiques** (-1002646551216)

## Instructions de Déploiement

1. **Render.com:**
   - Uploadez ce package complet
   - Configurez les variables d'environnement
   - Le bot démarre automatiquement avec webhook

2. **Fonctionnement:**
   - Surveille le canal en temps réel
   - Analyse automatique des messages
   - Prédictions et vérifications automatiques

## Architecture Technique

- **Flask**: Serveur web pour webhooks
- **Mode dual**: Webhook (production) + Polling (développement)
- **Système anti-doublon**: Hash des messages traités
- **Logs détaillés**: 🔮 PRÉDICTION vs 🔍 VÉRIFICATION

## Exemple d'Utilisation

```
Message reçu: #N123. ✅6(K♠️Q♥️A♦️) - 5(J♣️4♣️)
↓
Bot détecte: 3 costumes différents dans PREMIER parenthèse SEULEMENT
↓
Génère: 🔵124 🔵3K: statut :⏳
↓
Attend vérification sur message N124 édité
```

## 🎯 Commandes Disponibles

- `/start` - Message d'accueil
- `/help` - Guide complet
- `/deploy` - Obtenir fichier de déploiement
- `/redirect <chat_id>` - Rediriger prédictions
- `/status` - État du système
- `/test` - Tester envoi multi-canaux

Version mise à jour - Août 2025
Correction: Prédiction UNIQUEMENT sur PREMIER parenthèse