document.addEventListener("DOMContentLoaded", async () => {
    const tbody = document.getElementById("tracked-table-body");
    
    try {
        const data = await window.api.fetchListings();
        const listings = data.listings;
        
        if (!listings || listings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tracked listings yet. Go to Keyword Analyser to seed a niche!</td></tr>`;
            return;
        }
        
        tbody.innerHTML = ""; 
        
        // Show top 100 for UI performance
        const displayListings = listings.slice(0, 100);
        
        displayListings.forEach(item => {
            const tr = document.createElement("tr");
            const shortTitle = item.title.length > 50 ? item.title.substring(0, 50) + '...' : item.title;
            
            tr.innerHTML = `
                <td><a href="https://etsy.com/listing/${item.listing_id}" target="_blank" style="color:#e2e8f0; text-decoration:none;">#${item.listing_id}</a></td>
                <td title="${item.title}">${shortTitle}</td>
                <td>${item.creation_date}</td>
                <td><span style="color: var(--text-muted); font-size:0.9rem;">Loading...</span></td>
                <td><span style="background: rgba(16,185,129,0.2); color: var(--success); padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; border: 1px solid rgba(16,185,129,0.4);">Active</span></td>
            `;
            tbody.appendChild(tr);
            
            // Asynchronously fetch latest views for the table
            window.api.fetchMetrics(item.listing_id).then(metricData => {
                const metrics = metricData.metrics;
                if(metrics && metrics.length > 0) {
                    const latest = metrics[metrics.length - 1];
                    tr.cells[3].innerHTML = `<strong>${latest.views.toLocaleString()}</strong>`;
                } else {
                    tr.cells[3].innerHTML = `<span style="color:var(--text-muted);">N/A</span>`;
                }
            }).catch(() => {
                tr.cells[3].innerHTML = `<span style="color:var(--text-muted);">Error</span>`;
            });
        });
        
    } catch (err) {
        console.error(err);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #ef4444; padding: 2rem;">Failed to connect to API.</td></tr>`;
    }
});
