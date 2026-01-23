document.addEventListener("DOMContentLoaded", () => {

    const params = new URLSearchParams(window.location.search);
    let uri = params.get("uri");

    if (!uri) {
        showError("Aucune URI spécifiée.");
        return;
    }

    if (uri.includes("/page/")) {
        uri = uri.replace("/page/", "/resource/");
    }

    loadEntityDetailsDirect(uri);
});

async function loadEntityDetailsDirect(resourceUri) {
    const loader = document.getElementById("loading");
    const content = document.getElementById("entity-content");

    document.getElementById("error-msg").style.display = "none";

    const sparqlQuery = `
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>

        SELECT DISTINCT ?property ?value ?propLabel ?valLabel WHERE {
            <${resourceUri}> ?property ?value .
            
            # Filtres pour ne garder que les propriétés utiles
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/") || 
                   STRSTARTS(STR(?property), "http://www.w3.org/2000/01/rdf-schema#") ||
                   ?property = foaf:depiction || ?property = foaf:name)

            # Récupérer le label de la propriété en français
            OPTIONAL { 
                ?property rdfs:label ?propLabel . 
                FILTER(LANG(?propLabel) = "fr") 
            }

            # Si la valeur est une ressource, essayer d'avoir son label en français
            OPTIONAL { 
                ?value rdfs:label ?valLabel . 
                FILTER(ISIRI(?value) && LANG(?valLabel) = "fr") 
            }

            # Garder français ou anglais ou sans langue
            FILTER(!ISLITERAL(?value) || LANG(?value) = "" || LANG(?value) = "fr" || LANG(?value) = "en")
        }
    `;

    const endpointUrl = `https://dbpedia.org/sparql?default-graph-uri=http%3A%2F%2Fdbpedia.org&query=${encodeURIComponent(sparqlQuery)}&format=application%2Fsparql-results%2Bjson`;

    try {
        const response = await fetch(endpointUrl);
        if (!response.ok) throw new Error(`Erreur DBpedia: ${response.status}`);
        
        const json = await response.json();
        const bindings = json.results.bindings;

        if (bindings.length === 0) {
            showError("Aucune donnée trouvée sur DBpedia pour cette URI.");
            return;
        }

        renderData(resourceUri, bindings);
        
        loader.style.display = "none";
        content.style.display = "block";

    } catch (err) {
        console.error(err);
        showError("Impossible de contacter DBpedia directement.");
    }
}

function renderData(uri, bindings) {
    let label = "";
    let image = "";
    const properties = {};

    bindings.forEach(b => {
        const propUri = b.property.value;
        const val = b.value.value;
        const valLabel = b.valLabel ? b.valLabel.value : null;
        const propLabel = b.propLabel ? b.propLabel.value : extractNameFromUri(propUri);

        if (propUri === "http://dbpedia.org/ontology/abstract") return;

        if (propUri === "http://www.w3.org/2000/01/rdf-schema#label" && b.value["xml:lang"] === "fr") {
            label = val;
        } 
        else if ((propUri === "http://dbpedia.org/ontology/thumbnail" || propUri === "http://xmlns.com/foaf/0.1/depiction") && !image) {
            image = val;
        } 
        else {
            const displayValue = valLabel || val;
            
            if (!properties[propLabel]) {
                properties[propLabel] = [];
            }

            const exists = properties[propLabel].some(item => item.raw === val);
            if (!exists) {
                properties[propLabel].push({ raw: val, display: displayValue });
            }
        }
    });

    if (!label) {
        const labelEn = bindings.find(b => b.property.value === "http://www.w3.org/2000/01/rdf-schema#label" && b.value["xml:lang"] === "en");
        label = labelEn ? labelEn.value.value : extractNameFromUri(uri);
    }

    document.getElementById("entity-label").textContent = label;
    document.getElementById("entity-uri").textContent = uri;

    const imgEl = document.getElementById("entity-img");
    const placeholderEl = document.getElementById("img-placeholder");
    if (image) {
        imgEl.src = image;
        imgEl.style.display = "block";
        placeholderEl.style.display = "none";
    } else {
        imgEl.style.display = "none";
        placeholderEl.style.display = "flex";
    }

    const listGroup = document.getElementById("entity-properties");
    listGroup.innerHTML = "";
    
    Object.keys(properties).sort().forEach(key => {
        if (key.toLowerCase().includes("thumbnail")) return;

        const valuesObj = properties[key];
        const htmlContent = formatValueList(valuesObj);

        const item = document.createElement("div");
        item.className = "list-group-item d-flex justify-content-between align-items-start flex-wrap";
        item.innerHTML = `
            <span class="fw-semibold text-muted small text-uppercase mt-1" style="max-width: 35%; word-wrap: break-word;">${escapeHtml(key)}</span>
            <div class="text-end text-break ms-2" style="max-width: 60%;">${htmlContent}</div>
        `;
        listGroup.appendChild(item);
    });
}

function formatValueList(values) {
    if (!values || values.length === 0) return "";

    const isImgUrl = (raw) => {
         return typeof raw === 'string' && 
              !raw.includes("dbpedia.org/resource/") &&
              (/\.(jpg|jpeg|png|gif|svg|webp)$/i.test(raw) || raw.includes("commons.wikimedia.org/wiki/Special:FilePath"));
    };

    const renderOne = (vObj) => {
        const raw = vObj.raw;     
        const text = vObj.display;

        if (isImgUrl(raw)) {
            return `<a href="${raw}" target="_blank">
                      <img src="${raw}" class="img-thumbnail" style="width: 70px; height: 70px; object-fit: cover;" alt="img">
                    </a>`;
        }
        
        return formatValue(raw, text);
    };

    if (values.length === 1) {
        return renderOne(values[0]);
    }

    const isGallery = isImgUrl(values[0].raw);

    const max = 15;
    const visible = values.slice(0, max);
    const hiddenCount = values.length - max;

    let html = "";

    if (isGallery) {
        html = `<div class="d-flex flex-wrap gap-2 justify-content-end">`;
        visible.forEach(v => {
            html += renderOne(v);
        });
        html += `</div>`;
    } else {
        html = `<div class="d-flex flex-column align-items-end gap-1">`;
        visible.forEach(v => {
            html += `<div>${renderOne(v)}</div>`;
        });
        html += `</div>`;
    }

    if (hiddenCount > 0) {
        html += `<div class="text-end w-100"><small class="text-muted fst-italic">+ ${hiddenCount} autres...</small></div>`;
    }
    
    return html;
}

function extractNameFromUri(uri) {
    const parts = uri.split('/');
    return parts[parts.length - 1].replace(/_/g, ' ');
}

function formatValue(raw, display) {
    const valStr = String(raw);
    
    if (valStr.startsWith("http")) {
        if (valStr.includes("dbpedia.org/resource")) {
            const shortName = extractNameFromUri(valStr);
            const labelToShow = (display && display !== valStr) ? display : shortName;
            
            return `<a href="detail.html?uri=${encodeURIComponent(valStr)}" class="badge bg-light text-dark border text-decoration-none fw-normal" title="${valStr}">
                        ${escapeHtml(labelToShow)}
                    </a>`;
        }
        return `<a href="${valStr}" target="_blank" class="text-decoration-none">
                    <i class="bi bi-box-arrow-up-right small me-1"></i>Lien
                </a>`;
    }
    return escapeHtml(display);
}

function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showError(msg) {
    document.getElementById("loading").style.display = "none";
    const err = document.getElementById("error-msg");
    err.textContent = msg;
    err.style.display = "block";
}