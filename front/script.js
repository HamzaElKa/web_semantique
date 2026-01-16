document.addEventListener('DOMContentLoaded', () => {
    // On charge les données d'exemple au lancement de la page
    loadFeaturedData();
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
        { url: 'http://localhost:8000/dbpedia-foot/players', id: 'featured-players', icon: 'bi-person' },
        { url: 'http://localhost:8000/dbpedia-foot/clubs', id: 'featured-clubs', icon: 'bi-shield' },
        { url: 'http://localhost:8000/dbpedia-foot/competitions', id: 'featured-competitions', icon: 'bi-trophy' }
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