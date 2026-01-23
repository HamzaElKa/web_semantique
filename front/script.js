document.addEventListener('DOMContentLoaded', () => {
    // On charge les données d'exemple au lancement de la page
    loadFeaturedData();
    loadAnalyticsData(); // Fonction fictive pour charger les données d'analytics

  // --- NEW: Search handlers ---
  const btn = document.getElementById('searchBtn');
  const input = document.getElementById('searchQuery');

  if (btn) btn.addEventListener('click', runSearch);
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') runSearch();
    });
  }
});


function saveDataToFile(data, filename = 'data') {
    // 1. Convertir les données en chaîne JSON formatée
    const jsonString = JSON.stringify(data, null, 2);

    // 2. Créer un Blob (objet binaire) contenant le texte
    const blob = new Blob([jsonString], { type: 'application/json' });

    // 3. Créer une URL temporaire pointant vers ce Blob
    const url = URL.createObjectURL(blob);

    // 4. Créer un lien <a> invisible pour déclencher le téléchargement
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}.json`; // Nom du fichier final
    
    // 5. Ajouter au DOM, cliquer et nettoyer
    document.body.appendChild(link);
    link.click();
    
    // Nettoyage
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log(`Fichier ${filename}.json généré !`);
}

async function loadFeaturedData() {
    const endpoints = [
        { url: 'http://127.0.0.1:8000/dbpedia-foot/players', id: 'featured-players', icon: 'bi-person' },
        { url: 'http://127.0.0.1:8000/dbpedia-foot/clubs', id: 'featured-clubs', icon: 'bi-shield' },
        { url: 'http://127.0.0.1:8000/dbpedia-foot/competitions', id: 'featured-competitions', icon: 'bi-trophy' }
    ];

    try {
        const promises = endpoints.map(ep => 
            fetch(ep.url)
                .then(response => {
                    if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
                    return response.json();
                })
                .then(data => ({ ...ep, data })) // On garde l'info de l'endpoint avec la donnée
        );

        const results = await Promise.all(promises);

        let i = 0;
        results.forEach(result => {
            console.log(result);
            // saveDataToFile(result,endpoints[i].id); i++;
            renderFeaturedItems(result.id, result.data);
        });

    } catch (error) {
        console.error("Erreur lors du chargement des données d'exemple:", error);
        // En cas d'erreur globale, on peut afficher un message dans les listes
        endpoints.forEach(ep => {
            const container = document.getElementById(ep.id);
            if(container) container.innerHTML = '<div class="p-3 text-muted text-center small">Indisponible</div>';
        });
    }
}

function renderFeaturedItems(containerId, dataPayload) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = ''; // Nettoyer le conteneur

    // Sécurisation : on cherche le tableau de résultats
    // L'API semble renvoyer : { lang: "fr", results: [...] }
    const items = dataPayload.results || dataPayload || [];

    if (items.length === 0) {
        container.innerHTML = '<div class="list-group-item text-muted">Aucune donnée disponible</div>';
        return;
    }

    // On parcourt les éléments (limité aux 5 premiers)
    items.slice(0, 5).forEach(item => {
        // 1. Détection du contexte pour l'affichage (Joueur vs Club vs Compétition)
        let subtitle = '';
        let iconFallback = 'bi-question-circle';
        let detailIcon = '';

        if (item.club && !item.stade) { 
            // C'est un JOUEUR (il a un club mais pas de stade)
            subtitle = item.club;
            iconFallback = 'bi-person-circle';
            detailIcon = 'bi-shirt'; // Icone maillot pour le club
        } else if (item.stade) {
            // C'est un CLUB (il a un stade)
            subtitle = `Stade : ${item.stade}`;
            iconFallback = 'bi-shield-shaded';
            detailIcon = 'bi-geo-alt'; // Icone lieu pour le stade
        } else if (item.pays) {
            // C'est une COMPÉTITION (elle a un pays)
            subtitle = item.pays;
            iconFallback = 'bi-trophy';
            detailIcon = 'bi-flag'; // Icone drapeau pour le pays
        }

        const imageUrl = item.image || '';
        
        // 3. Création de l'élément HTML
        const a = document.createElement('a');
        a.href = '#'; 
        a.className = 'list-group-item list-group-item-action d-flex align-items-center gap-3 py-3';
        
        // Injection du HTML
        a.innerHTML = `
            <div class="avatar-container flex-shrink-0">
                ${imageUrl 
                    ? `<img src="${imageUrl}" alt="${item.nom}" class="rounded-circle object-fit-cover border" width="50" height="50" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">` 
                    : ''
                }
            </div>
            
            <div class="d-flex flex-column overflow-hidden">
                <h6 class="mb-0 text-truncate fw-semibold">${item.nom}</h6>
                <small class="text-muted text-truncate">
                    ${subtitle ? `<i class="bi ${detailIcon} me-1"></i>${subtitle}` : ''}
                </small>
            </div>
            
            <i class="bi bi-chevron-right ms-auto text-light-gray"></i>
        `;

        // Interaction au clic (remplit la barre de recherche)
        a.addEventListener('click', (e) => {
            e.preventDefault();
            const searchInput = document.getElementById('searchQuery');
            if(searchInput) {
                searchInput.value = item.nom;
                searchInput.focus();
                // Optionnel : document.getElementById('searchBtn').click();
            }
        });

        container.appendChild(a);
    });
}

async function loadAnalyticsData() {
  const endpoints = [
    { url: "http://127.0.0.1:8000/dbpedia-foot/analytics/club-degree?lang=fr&limit=8", id: "analytics-club-degree", kind: "clubDegree" },
    { url: "http://127.0.0.1:8000/dbpedia-foot/analytics/player-mobility?lang=fr&min_clubs=3&limit=8", id: "analytics-player-mobility", kind: "playerMobility" }
  ];

  try {
    const results = await Promise.all(
      endpoints.map(ep =>
        fetch(ep.url)
          .then(r => {
            if (!r.ok) throw new Error(`Erreur HTTP ${r.status} sur ${ep.url}`);
            return r.json();
          })
          .then(data => ({ ...ep, data }))
      )
    );

    results.forEach(r => renderAnalyticsItems(r.id, r.data, r.kind));
  } catch (err) {
    console.error("Erreur loadAnalyticsData:", err);
    endpoints.forEach(ep => {
      const container = document.getElementById(ep.id);
      if (container) container.innerHTML = '<div class="p-3 text-muted text-center small">Indisponible</div>';
    });
  }
}

function renderAnalyticsItems(containerId, payload, kind) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const items = payload?.results || [];
  container.innerHTML = "";

  if (!items.length) {
    container.innerHTML = '<div class="list-group-item text-muted">Aucune donnée disponible</div>';
    return;
  }

  items.forEach(item => {
    const a = document.createElement("a");
    a.href = "#";
    a.className = "list-group-item list-group-item-action d-flex align-items-center gap-3 py-3";

    // libellés
    let title = "";
    let subtitle = "";
    let badge = "";
    let imageUrl = item.image || "";

    if (kind === "clubDegree") {
      title = item.club || item.club_uri || "Club";
      subtitle = "Nb joueurs liés (degré)";
      badge = item.nbPlayers ?? "";
    } else if (kind === "playerMobility") {
      title = item.player || item.player_uri || "Joueur";
      subtitle = "Nb clubs distincts";
      badge = item.nbClubs ?? "";
    }

    a.innerHTML = `
      <div class="avatar-container flex-shrink-0">
        ${
          imageUrl
            ? `<img src="${imageUrl}" alt="${title}" class="rounded-circle object-fit-cover border" width="50" height="50"
                 onerror="this.style.display='none';">`
            : `<div class="rounded-circle border d-flex align-items-center justify-content-center" style="width:50px;height:50px;background:#fff;">
                 <i class="bi bi-graph-up text-secondary"></i>
               </div>`
        }
      </div>

      <div class="d-flex flex-column overflow-hidden">
        <h6 class="mb-0 text-truncate fw-semibold">${title}</h6>
        <small class="text-muted text-truncate">${subtitle}</small>
      </div>

      <span class="badge bg-dark ms-auto">${badge}</span>
    `;

    // UX: au clic, on remplit la barre de recherche avec le nom (comme vos “featured”)
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const searchInput = document.getElementById("searchQuery");
      if (searchInput) {
        searchInput.value = title;
        searchInput.focus();
      }
    });

    container.appendChild(a);
  });
}

const API_BASE = "http://127.0.0.1:8000";

async function runSearch() {
  const input = document.getElementById('searchQuery');
  const query = (input?.value || "").trim();
  const type = document.getElementById("searchType")?.value || ""; // player/club/stadium/competition/""
  const resultsDiv = document.getElementById('results');
  const infoDiv = document.getElementById('searchInfo');
  const countSpan = document.getElementById('resultCount');
  const endpointSpan = document.getElementById('endpointUsed');

  if (!query) {
    if (resultsDiv) resultsDiv.innerHTML = "";
    if (infoDiv) infoDiv.style.display = "none";
    return;
  }

  // UI: loader
  if (resultsDiv) {
    resultsDiv.innerHTML = `
      <div class="text-center p-4">
        <div class="spinner-border text-primary"></div>
        <div class="mt-2 text-muted">Recherche en cours…</div>
      </div>
    `;
  }

  try {
    const lang = "fr";
    const kind = type || "player";
    const url = `${API_BASE}/dbpedia-foot/search?q=${encodeURIComponent(query)}&kind=${encodeURIComponent(kind)}&lang=${encodeURIComponent(lang)}&limit=20`;

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    // attendu: { lang, kind, count, results:[...] }
    const data = await resp.json();
    const items = data.results || [];

    if (infoDiv) infoDiv.style.display = "block";
    if (countSpan) countSpan.textContent = String(items.length);
    if (endpointSpan) endpointSpan.textContent = "DBpedia (dbpedia-foot)";

    renderSearchResults(items);
  } catch (err) {
    console.error("Search error:", err);
    if (resultsDiv) {
      resultsDiv.innerHTML = `<div class="alert alert-danger">Erreur pendant la recherche.</div>`;
    }
    if (infoDiv) infoDiv.style.display = "none";
  }
}

function renderSearchResults(items) {
  const resultsDiv = document.getElementById('results');
  if (!resultsDiv) return;

  if (!items.length) {
    resultsDiv.innerHTML = `<div class="alert alert-secondary">Aucun résultat.</div>`;
    return;
  }

  resultsDiv.innerHTML = "";
  items.forEach(item => {
    // dbpedia-foot/search returns: { uri, label, comment, img, kind }
    const name = item.label || item.nom || item.name || "Sans nom";
    const uri = item.uri || item.id || item.resource || "";
    const image = item.img || item.image || "";
    const comment = item.comment || item.description || "";

    const card = document.createElement('div');
    card.className = "card result-card p-3";

    card.innerHTML = `
      <div class="d-flex align-items-center gap-3">
        ${image ? `<img src="${image}" class="rounded-circle object-fit-cover border" width="52" height="52" alt="${name}" onerror="this.style.display='none'">` : ""}
        <div class="flex-grow-1 overflow-hidden">
          <div class="fw-semibold text-truncate">${name}</div>
          ${comment ? `<div class="small text-muted text-truncate">${comment}</div>` : ""}
          ${uri ? `<div class="small text-muted text-truncate">${uri}</div>` : ""}
        </div>
        ${uri ? `<a class="btn btn-outline-primary btn-sm" href="detail.html?uri=${uri}">Détails</a>` : ""}
      </div>
    `;


    resultsDiv.appendChild(card);
  });
}
