// front/ask.js
const API_BASE = "http://127.0.0.1:8000";
const chatWindow = document.getElementById("chatWindow");
const statusEl = document.getElementById("askStatus");

/**
 * Ajoute un message dans la fenêtre de chat
 * @param {string} text - Contenu du message
 * @param {'user' | 'ai'} side - Expéditeur
 */
function addMessage(text, side) {
    const div = document.createElement("div");
    div.className = `msg msg-${side}`;
    
    if (side === 'ai') {
        // Rendu du gras (Markdown simple) pour les réponses pédagogiques
        div.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    } else {
        div.textContent = text;
    }
    
    chatWindow.appendChild(div);
    // Scroll vers le bas automatique
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function handleAsk() {
    const input = document.getElementById("askQuestion");
    const question = input.value.trim();
    const btn = document.getElementById("askBtn");

    if (!question) return;

    // UI: Ajouter le message utilisateur et bloquer l'input
    addMessage(question, 'user');
    input.value = "";
    btn.disabled = true;
    statusEl.innerHTML = `<span class="loading-dots">L'IA prépare une réponse pédagogique via DBpedia</span>`;

    try {
        const response = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question, endpoint: "dbpedia" })
        });

        if (!response.ok) throw new Error(`Erreur serveur (${response.status})`);

        const data = await response.json();
        
        // Ajouter la réponse formatée de l'IA
        addMessage(data.answer, 'ai');
        statusEl.innerText = "Réponse générée avec succès.";
    } catch (err) {
        console.error(err);
        addMessage("Désolé, une erreur technique est survenue lors de la consultation de DBpedia ou d'Ollama.", 'ai');
        statusEl.innerText = "Erreur détectée.";
    } finally {
        btn.disabled = false;
        input.focus();
    }
}

// Events
document.getElementById("askBtn").addEventListener("click", handleAsk);
document.getElementById("askQuestion").addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleAsk();
});

document.getElementById("clearChat").addEventListener("click", () => {
    chatWindow.innerHTML = '<div class="text-center text-muted small my-3">Conversation effacée</div>';
    statusEl.innerText = "";
});