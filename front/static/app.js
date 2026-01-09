/* 4IF-WS Foot Explorer - Main JavaScript */

// =====================
// CONFIG
// =====================
const CONFIG = {
  API_BASE: 'http://localhost:8000',
  USE_MOCK_ON_ERROR: true,
  DEFAULT_LIMIT: 50,
  ENDPOINTS: {
    dbpedia: 'DBpedia',
    wikidata: 'Wikidata'
  }
};

// =====================
// API CLIENT
// =====================
class ApiClient {
  constructor(baseUrl = CONFIG.API_BASE) {
    this.baseUrl = baseUrl;
  }

  async _fetch(url, options = {}) {
    const fullUrl = url.startsWith('http') ? url : `${this.baseUrl}${url}`;
    
    try {
      const response = await fetch(fullUrl, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      
      // Fallback to mock if configured
      if (CONFIG.USE_MOCK_ON_ERROR && options.mockFallback) {
        console.warn('Falling back to mock data:', options.mockFallback);
        try {
          const mockResponse = await fetch(options.mockFallback);
          return await mockResponse.json();
        } catch (mockError) {
          console.error('Mock fallback failed:', mockError);
        }
      }
      
      throw error;
    }
  }

  async search(query, entityType = 'player', endpoint = 'dbpedia', limit = CONFIG.DEFAULT_LIMIT) {
    const params = new URLSearchParams({
      q: query,
      entity_type: entityType,
      endpoint: endpoint,
      limit: limit.toString()
    });

    return this._fetch(`/search?${params}`, {
      mockFallback: './mock/search.json'
    });
  }

  async getEntity(uri, endpoint = 'dbpedia', limit = CONFIG.DEFAULT_LIMIT) {
    const params = new URLSearchParams({
      id: uri,
      endpoint: endpoint,
      limit: limit.toString()
    });

    return this._fetch(`/entity?${params}`, {
      mockFallback: './mock/entity.json'
    });
  }

  async getGraph(seedUri, depth = 1, endpoint = 'dbpedia', limit = 80) {
    const params = new URLSearchParams({
      seed: seedUri,
      depth: depth.toString(),
      endpoint: endpoint,
      limit: limit.toString()
    });

    return this._fetch(`/graph?${params}`, {
      mockFallback: './mock/graph.json'
    });
  }

  async getSimilarity(entityType, uri, endpoint = 'dbpedia', limit = 20) {
    const params = new URLSearchParams({
      entity_type: entityType,
      id: uri,
      endpoint: endpoint,
      limit: limit.toString()
    });

    return this._fetch(`/similarity?${params}`, {
      mockFallback: './mock/similarity.json'
    });
  }

  async ask(question, endpoint = 'dbpedia') {
    return this._fetch('/ask', {
      method: 'POST',
      body: JSON.stringify({
        question: question,
        endpoint: endpoint
      }),
      mockFallback: './mock/ask.json'
    });
  }

  async health() {
    return this._fetch('/health');
  }
}

// Global API instance
const api = new ApiClient();

// =====================
// UI UTILITIES
// =====================
const UI = {
  showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `
        <div class="spinner-container">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Chargement...</span>
          </div>
          <p class="mt-3 text-muted">Interrogation du Web sémantique...</p>
        </div>
      `;
    }
  },

  showError(containerId, message, details = '') {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `
        <div class="alert alert-danger" role="alert">
          <h5 class="alert-heading">
            <i class="bi bi-exclamation-triangle"></i> Erreur
          </h5>
          <p>${message}</p>
          ${details ? `<hr><small class="text-muted">${details}</small>` : ''}
        </div>
      `;
    }
  },

  showEmpty(containerId, title = 'Aucun résultat', message = '') {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `
        <div class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <h3>${title}</h3>
          ${message ? `<p>${message}</p>` : ''}
        </div>
      `;
    }
  },

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  truncate(text, maxLength = 150) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  },

  extractLabel(uri) {
    if (!uri) return '';
    const parts = uri.split('/');
    const last = parts[parts.length - 1];
    return decodeURIComponent(last.replace(/_/g, ' '));
  },

  toast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
    toast.style.zIndex = '9999';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.remove();
    }, 3000);
  }
};

// =====================
// URL UTILITIES
// =====================
const URLUtils = {
  getParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    for (const [key, value] of params) {
      result[key] = value;
    }
    return result;
  },

  getParam(key, defaultValue = null) {
    const params = new URLSearchParams(window.location.search);
    return params.get(key) || defaultValue;
  },

  setParams(params) {
    const url = new URL(window.location);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        url.searchParams.set(key, value);
      } else {
        url.searchParams.delete(key);
      }
    });
    window.history.pushState({}, '', url);
  },

  buildEntityUrl(uri) {
    return `entity.html?uri=${encodeURIComponent(uri)}`;
  },

  buildGraphUrl(uri) {
    return `graph.html?seed=${encodeURIComponent(uri)}`;
  },

  buildSimilarityUrl(uri, type = 'player') {
    return `similarity.html?uri=${encodeURIComponent(uri)}&type=${type}`;
  }
};

// =====================
// INIT CHECK
// =====================
async function checkApiHealth() {
  try {
    const status = await api.health();
    console.log('✅ API is healthy:', status);
    return true;
  } catch (error) {
    console.warn('⚠️ API health check failed, will use mock data:', error.message);
    if (CONFIG.USE_MOCK_ON_ERROR) {
      UI.toast('Mode hors ligne : données de démonstration', 'warning');
    }
    return false;
  }
}

// =====================
// EXPORTS (for page scripts)
// =====================
window.FootExplorer = {
  api,
  UI,
  URLUtils,
  CONFIG,
  checkApiHealth
};
