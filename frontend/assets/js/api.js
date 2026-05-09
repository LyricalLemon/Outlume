const API_BASE = "http://localhost:8000/api";

const api = {
    async fetchOutliers(nicheId = null, limit = 50) {
        let url = `${API_BASE}/analysis/outliers?limit=${limit}`;
        if (nicheId) url += `&niche_id=${nicheId}`;
        const res = await fetch(url);
        return await res.json();
    },
    
    async fetchTopTags(nicheId, limit = 10) {
        const res = await fetch(`${API_BASE}/analysis/tags?niche_id=${nicheId}&limit=${limit}`);
        return await res.json();
    },
    
    async fetchNiches() {
        const res = await fetch(`${API_BASE}/niches`);
        return await res.json();
    },
    
    async seedNiche(keyword, sortOn = "score") {
        const res = await fetch(`${API_BASE}/niches/seed`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keyword, sort_on: sortOn })
        });
        return await res.json();
    },
    
    async fetchListings() {
        const res = await fetch(`${API_BASE}/listings`);
        return await res.json();
    },
    
    async fetchMetrics(listingId) {
        const res = await fetch(`${API_BASE}/metrics/${listingId}`);
        return await res.json();
    }
};

window.api = api;
