document.addEventListener("DOMContentLoaded", () => {
    const extractBtn = document.getElementById("extract-btn");
    const seedBtn = document.getElementById("seed-btn");
    const input = document.getElementById("niche-input");
    const tbody = document.getElementById("tags-table-body");
    
    const showMessage = (msg, color = "var(--text-muted)") => {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: ${color}; padding: 2rem;">${msg}</td></tr>`;
    };

    extractBtn.addEventListener("click", async () => {
        const keyword = input.value.trim().toLowerCase();
        if (!keyword) return alert("Please enter a niche keyword to analyze.");
        
        showMessage("🔍 Searching database for niche...");
        
        try {
            const nichesData = await window.api.fetchNiches();
            const targetNiche = nichesData.niches.find(n => n.keyword.toLowerCase() === keyword);
            
            if (!targetNiche) {
                showMessage(`Niche "${keyword}" not found in local database. Click "Seed Niche Data" to pull it from Etsy!`, "var(--warning)");
                return;
            }
            
            showMessage("✨ Extracting top performing tags based on 7-Day Velocity...");
            
            const tagsData = await window.api.fetchTopTags(targetNiche.id, 15);
            
            if (!tagsData.tags || tagsData.tags.length === 0) {
                showMessage(`No tags found for "${keyword}". Wait for tomorrow's tracker run to establish velocity!`);
                return;
            }
            
            tbody.innerHTML = "";
            
            tagsData.tags.forEach((t, i) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>#${i+1}</strong> <span style="margin-left:8px; padding: 4px 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">${t.tag}</span></td>
                    <td><span class="text-green">${t.frequency} uses</span> in top 50 listings</td>
                    <td><span class="score medium">Pending...</span></td>
                `;
                tbody.appendChild(tr);
            });
            
        } catch (err) {
            console.error(err);
            showMessage("❌ Failed to connect to API.", "#ef4444");
        }
    });

    seedBtn.addEventListener("click", async () => {
        const keyword = input.value.trim().toLowerCase();
        if (!keyword) return alert("Please enter a niche keyword to seed.");
        
        seedBtn.innerText = "Seeding...";
        seedBtn.disabled = true;
        
        try {
            await window.api.seedNiche(keyword, "score");
            alert(`Seed job for "${keyword}" has started in the background! It takes a few seconds. You can click Extract Tags shortly.`);
        } catch (err) {
            console.error(err);
            alert("Failed to start seed job.");
        } finally {
            seedBtn.innerText = "Seed Niche Data";
            seedBtn.disabled = false;
        }
    });
});
