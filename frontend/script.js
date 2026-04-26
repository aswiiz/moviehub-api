document.addEventListener('DOMContentLoaded', () => {
    const CONFIG = {
        API_BASE_URL: window.location.origin.includes('localhost') ? 'http://localhost:8000' : 
                      (window.location.origin.includes('vercel.app') ? 'https://moviehub-api-9qb3.onrender.com' : ''),
        BOT_USERNAME: 'greenmoviebot'
    };

    const elements = {
        searchInput: document.getElementById('search-input'),
        searchButton: document.getElementById('search-button'),
        resultsGrid: document.getElementById('results-grid'),
        statusInfo: document.getElementById('status-info'),
        loader: document.getElementById('loader'),
        suggestions: document.getElementById('suggestions')
    };

    console.log("MovieHub Search System Initialized");

    // Base64 encoding for Telegram deep links (URL safe)
    function encodeFileId(fileId) {
        try {
            const encoded = btoa(fileId)
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=+$/, '');
            return encoded;
        } catch (e) {
            console.error('Encoding error:', e);
            return fileId;
        }
    }

    function showLoader(show) {
        if (elements.loader) elements.loader.style.display = show ? 'flex' : 'none';
    }

    async function performSearch(query) {
        console.log("Search triggered for:", query);
        if (!query || query.trim().length < 2) {
            console.warn("Query too short");
            return;
        }

        showLoader(true);
        elements.resultsGrid.innerHTML = '';
        elements.statusInfo.textContent = `Searching for "${query}"...`;

        try {
            const searchUrl = `${CONFIG.API_BASE_URL}/search?query=${encodeURIComponent(query.trim())}`;
            console.log("Fetching from:", searchUrl);
            
            const response = await fetch(searchUrl);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            renderResults(data, query.trim());
        } catch (error) {
            console.error('Search error:', error);
            const fullUrl = `${CONFIG.API_BASE_URL}/search?query=${encodeURIComponent(query)}`;
            elements.resultsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Search Failed</h3>
                    <p>Could not reach the backend API.</p>
                    <code style="display:block; margin-top:1rem; font-size:0.8rem; color:#f87171; word-break: break-all;">
                        URL: ${fullUrl}
                    </code>
                    <p style="margin-top:1rem; font-size:0.9rem;">
                        <b>Hint:</b> If you're on Render free tier, the server might be "sleeping". Please wait 30 seconds and try again.
                    </p>
                </div>
            `;
        } finally {
            showLoader(false);
        }
    }

    function renderResults(movies, query) {
        if (!movies || movies.length === 0) {
            elements.statusInfo.textContent = `No results found for "${query}"`;
            elements.resultsGrid.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h3>No movies found</h3>
                    <p>Try different keywords or check for typos.</p>
                </div>
            `;
            return;
        }

        elements.statusInfo.textContent = `Found ${movies.length} titles for "${query}"`;
        
        movies.forEach(movie => {
            const card = document.createElement('div');
            card.className = 'movie-card';
            
            const filesHtml = movie.files.map(file => `
                <div class="file-item">
                    <div class="file-info">
                        <span class="file-quality">${file.quality}</span>
                        <span class="file-meta">${file.size} | ${file.language || 'Multi'}</span>
                    </div>
                    <a href="https://t.me/${CONFIG.BOT_USERNAME}?start=${encodeFileId(file.movie_id)}" 
                       class="download-btn" 
                       target="_blank"
                       title="Get file on Telegram">
                        <i class="fas fa-download"></i>
                    </a>
                </div>
            `).join('');

            card.innerHTML = `
                <div class="movie-header">
                    <h3 class="movie-title">${movie.title}</h3>
                    ${movie.year ? `<span class="movie-year">${movie.year}</span>` : ''}
                </div>
                <div class="movie-files">
                    ${filesHtml}
                </div>
            `;
            
            elements.resultsGrid.appendChild(card);
        });
    }

    // Event Listeners
    if (elements.searchButton) {
        elements.searchButton.addEventListener('click', () => {
            performSearch(elements.searchInput.value);
        });
    }

    if (elements.searchInput) {
        elements.searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch(elements.searchInput.value);
            }
        });
    }

    // Auto-fetch bot username on load
    async function init() {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/api/info`);
            const data = await response.json();
            if (data.bot_username) {
                CONFIG.BOT_USERNAME = data.bot_username;
            }
        } catch (e) {
            console.warn('Could not fetch bot username, using default.');
        }
    }

    init();
});
