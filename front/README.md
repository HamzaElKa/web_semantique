# Foot Explorer - Frontend

Interface web pour l'exploration du Web Sémantique du football (projet 4IF-WS - INSA Lyon)

## 📁 Structure

```
front/
├── index.html          # Page de recherche (point d'entrée)
├── entity.html         # Page détail d'une entité
├── graph.html          # Visualisation de graphe
├── similarity.html     # Recommandations par similarité
├── ask.html            # Chat IA / NL2SPARQL
├── static/
│   ├── app.js          # Client API + utilitaires
│   └── style.css       # Styles personnalisés
└── mock/
    ├── search.json     # Données de test (recherche)
    ├── entity.json     # Données de test (entité)
    ├── graph.json      # Données de test (graphe)
    ├── similarity.json # Données de test (similarité)
    └── ask.json        # Données de test (IA)
```

## 🚀 Lancement

### Prérequis

1. **Backend API** : Assurez-vous que l'API backend est lancée sur `http://localhost:8000`
   ```bash
   cd ../backend
   uvicorn run:app --reload
   ```

2. **Serveur web** : Le frontend nécessite un serveur HTTP (pas de `file://`)

### Option 1 : Serveur Python simple

```bash
cd front
python3 -m http.server 8080
```

Puis ouvrir : **http://localhost:8080**

### Option 2 : Live Server (VS Code)

1. Installer l'extension **Live Server**
2. Clic droit sur `index.html` → "Open with Live Server"

### Option 3 : Node.js

```bash
npx http-server front -p 8080
```

## 🔧 Configuration

Dans [static/app.js](static/app.js), ligne 6 :

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000',  // URL de votre backend
  USE_MOCK_ON_ERROR: true,            // Fallback vers mock/ si API down
  DEFAULT_LIMIT: 50,
  // ...
};
```

## 📖 Pages principales

### 1. **Recherche** (`index.html`)
- Recherche d'entités (joueurs, clubs, stades)
- Filtrage par type et source (DBpedia/Wikidata)
- Résultats cliquables vers page entité

### 2. **Entité** (`entity.html`)
- Affichage des propriétés RDF (facts)
- Liste des voisins (relations sortantes)
- Actions rapides : voir graphe, trouver similaires

### 3. **Graphe** (`graph.html`)
- Visualisation Cytoscape.js (interactive)
- Vue tableau (fallback)
- Export JSON
- Stats : nombre de nœuds/arêtes

### 4. **Similarité** (`similarity.html`)
- Recommandations d'entités similaires
- Score + explication des features communes
- Lien vers entité et graphe

### 5. **Chat IA** (`ask.html`)
- Question en langage naturel
- Génération de requête SPARQL (NL2SPARQL)
- Affichage des résultats + synthèse

## 🎨 Technologies

- **HTML5 / CSS3**
- **JavaScript vanilla** (pas de framework lourd)
- **Bootstrap 5.3** (UI/composants)
- **Cytoscape.js** (visualisation de graphes)
- **Fetch API** (appels asynchrones)

## 🧪 Mode offline / Mock

Si le backend n'est pas disponible, le frontend bascule automatiquement sur les fichiers mock :

```
fetch API → erreur → charge ./mock/<endpoint>.json
```

Pour tester :
1. Arrêter le backend
2. Ouvrir le frontend
3. Les données de `mock/` s'affichent

## 🔗 Intégration avec le backend

Le frontend appelle ces routes :

| Route | Méthode | Utilisation |
|-------|---------|-------------|
| `/search` | GET | Recherche d'entités |
| `/entity` | GET | Détails d'une entité |
| `/graph` | GET | Construction de graphe |
| `/similarity` | GET | Entités similaires |
| `/ask` | POST | NL2SPARQL + synthèse |
| `/health` | GET | Statut de l'API |

### Exemple d'appel (JavaScript)

```javascript
const data = await api.search('messi', 'player', 'dbpedia', 50);
// Retourne : { meta, query, entity_type, results: [...] }
```

Voir [static/app.js](static/app.js) pour tous les appels.

## 📊 Format des données

### Recherche

```json
{
  "meta": { "endpoint": "dbpedia", "limit": 50 },
  "query": "messi",
  "entity_type": "player",
  "results": [
    {
      "uri": "http://dbpedia.org/resource/Lionel_Messi",
      "label": "Lionel Messi",
      "description": "...",
      "type": "player"
    }
  ]
}
```

### Entité

```json
{
  "meta": { "endpoint": "dbpedia", "limit": 50 },
  "uri": "http://...",
  "label": "Lionel Messi",
  "facts": {
    "dbo:birthDate": [{ "value": "1987-06-24", "label": "..." }]
  },
  "neighbors": [
    { "predicate": "dbo:team", "uri": "...", "label": "..." }
  ]
}
```

### Graphe

```json
{
  "nodes": [
    { "id": "http://...", "label": "..." }
  ],
  "edges": [
    { "source": "http://...", "target": "http://...", "label": "team" }
  ]
}
```

## 🐛 Dépannage

### Le frontend ne charge rien

1. Vérifier la console navigateur (F12)
2. Vérifier que le backend tourne sur port 8000
3. Vérifier les CORS (le backend doit autoriser `http://localhost:8080`)

### CORS Error

Ajouter dans le backend FastAPI :

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Les graphes ne s'affichent pas

- Vérifier que Cytoscape.js est chargé (CDN)
- Ouvrir la console : chercher erreurs JavaScript
- Tester avec la vue "Tableau" (bouton)

## 📝 Personnalisation

### Changer les couleurs

Éditer [static/style.css](static/style.css), lignes 3-10 :

```css
:root {
  --primary: #0066cc;    /* Bleu principal */
  --success: #28a745;    /* Vert (graphe) */
  --warning: #ffc107;    /* Jaune (similarité) */
}
```

### Ajouter une page

1. Créer `nouvelle_page.html`
2. Inclure Bootstrap + `static/app.js`
3. Ajouter le lien dans la navbar
4. Utiliser `api.*` pour appeler le backend

## 👥 Contribution

Ce frontend est conçu pour s'intégrer avec :

- **Backend API** (FastAPI, routes `/search`, `/entity`, etc.)
- **Module SPARQL** (requêtes DBpedia/Wikidata)
- **Module Graphe** (NetworkX + Gephi)
- **Module Similarité** (calcul de scores)
- **Module LLM** (NL2SPARQL + synthèse)

Chacun peut travailler en parallèle sur son module et brancher ensuite.

## 📚 Ressources

- [Bootstrap 5 docs](https://getbootstrap.com/docs/5.3/)
- [Cytoscape.js docs](https://js.cytoscape.org/)
- [DBpedia SPARQL endpoint](https://dbpedia.org/sparql)
- [Wikidata Query Service](https://query.wikidata.org/)

## ✅ Checklist avant soutenance

- [ ] Backend API fonctionnel
- [ ] Recherche retourne des résultats
- [ ] Page entité affiche facts + voisins
- [ ] Graphe visualise avec Cytoscape
- [ ] Similarité affiche top N (si implémenté)
- [ ] Chat IA génère SPARQL (si implémenté)
- [ ] Mock data fonctionne en fallback
- [ ] Responsive mobile (Bootstrap)

---

**Projet 4IF-WS** - Web Sémantique - INSA Lyon  
**Thème** : Football (DBpedia + Wikidata)  
**Stack Frontend** : HTML/CSS/JS + Bootstrap + Cytoscape.js
