document.addEventListener("DOMContentLoaded", async () => {
    try {
        const data = await window.api.fetchOutliers(null, 15);
        const outliers = data.outliers;
        const tbody = document.getElementById("outliers-table-body");
        tbody.innerHTML = ""; // Clear
        
        let totalViews = 0;
        let totalSales = 0;
        let highestScore = 0;
        let highestScoreId = null;
        
        outliers.forEach(item => {
            const tr = document.createElement("tr");
            
            // Limit title length
            const shortTitle = item.title.length > 40 ? item.title.substring(0, 40) + '...' : item.title;
            const scoreClass = item.outlier_score > 80 ? 'high' : (item.outlier_score > 40 ? 'medium' : 'low');
            
            // Very rough sales estimation (1.5 multiplier as default)
            const estSales = Math.round((item.fav_velocity_7d || 0) * 1.5);
            totalSales += estSales;
            totalViews += (item.views_velocity_7d || 0);
            
            if (item.outlier_score > highestScore) {
                highestScore = item.outlier_score;
                highestScoreId = item.listing_id;
            }
            
            tr.innerHTML = `
                <td><a href="https://etsy.com/listing/${item.listing_id}" target="_blank" style="color:#e2e8f0; text-decoration:none;">#${item.listing_id}</a></td>
                <td title="${item.title}">${shortTitle}</td>
                <td><span class="text-green">+${item.views_velocity_7d || 0}</span></td>
                <td><span class="text-green">+${item.fav_velocity_7d || 0}</span></td>
                <td><span class="score ${scoreClass}">${item.outlier_score.toFixed(1)}</span></td>
                <td><a href="https://etsy.com/listing/${item.listing_id}" target="_blank" class="btn btn-xs">View</a></td>
            `;
            tbody.appendChild(tr);
        });
        
        // Update KPIs
        document.getElementById("kpi-views").innerText = `+${totalViews}`;
        document.getElementById("kpi-sales").innerText = `~${totalSales}`;
        if (highestScore > 0) {
            document.getElementById("kpi-score").innerText = highestScore.toFixed(1);
            document.getElementById("kpi-score-label").innerText = `Listing ID #${highestScoreId}`;
        }
        
        // Let's fetch top tag from first niche (if any exists) for the KPI
        const nichesData = await window.api.fetchNiches();
        if (nichesData.niches && nichesData.niches.length > 0) {
            const firstNicheId = nichesData.niches[0].id;
            const tagsData = await window.api.fetchTopTags(firstNicheId, 1);
            if (tagsData.tags && tagsData.tags.length > 0) {
                document.getElementById("kpi-tag").innerText = `"${tagsData.tags[0].tag}"`;
            }
        }
        
    } catch (err) {
        console.error("Failed to load dashboard data:", err);
        const tbody = document.getElementById("outliers-table-body");
        if(tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#ef4444;">Failed to connect to API. Have you started the backend with 'uvicorn backend.main:app'?</td></tr>`;
        }
    }
});
