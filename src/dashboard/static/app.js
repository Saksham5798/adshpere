// Global state
let spendChart = null;
let selectedUserId = null;
let usersList = [];

// API Base URL (defaults to origin since served from same server)
const API_BASE = "";

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    refreshAllData();
    
    // Bind simulator user select listener
    document.getElementById("sim-user-select").addEventListener("change", (e) => {
        updateUserPreview(e.target.value);
    });
});

// Tab Navigation
function switchTab(tabId) {
    // Hide all tab panes
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.classList.remove("active");
    });
    
    // Show target tab pane
    const targetPane = document.getElementById(`tab-${tabId}`);
    if (targetPane) {
        targetPane.classList.add("active");
    }
    
    // Update active nav button
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.classList.remove("active");
    });
    
    // Find button that has onclick referring to tabId
    const activeBtn = Array.from(document.querySelectorAll(".nav-item")).find(btn => {
        return btn.getAttribute("onclick").includes(tabId);
    });
    if (activeBtn) {
        activeBtn.classList.add("active");
    }
    
    // Update Page Header Title
    const headers = {
        'overview': 'Analytics Overview',
        'campaigns': 'Campaigns Manager',
        'users': 'User Profiles Database',
        'simulator': 'Real-Time Bidding Simulator',
        'logs': 'Auction Transaction & Fraud Logs'
    };
    document.getElementById("page-title").innerText = headers[tabId] || "Dashboard";
}

// Refresh all components
async function refreshAllData() {
    console.log("Refreshing dashboard data...");
    await loadUsers();
    await loadCampaigns();
    await loadAnalytics();
    await loadLogs();
    
    // Refresh icons
    lucide.createIcons();
}

// 1. Campaigns Module
async function loadCampaigns() {
    try {
        const response = await fetch(`${API_BASE}/campaigns`);
        if (!response.ok) throw new Error("Failed to load campaigns");
        const campaigns = await response.json();
        
        const container = document.getElementById("campaign-cards-container");
        container.innerHTML = "";
        
        if (campaigns.length === 0) {
            container.innerHTML = `<div class="glass-card text-center text-muted py-5">No campaigns created yet. Create one on the right!</div>`;
            return;
        }
        
        campaigns.forEach(c => {
            const spendPercent = c.budget > 0 ? (c.current_spend / c.budget) * 100 : 0;
            const progressColor = spendPercent >= 100 ? "#ef4444" : (spendPercent >= 80 ? "#f59e0b" : "#6366f1");
            const statusBadge = c.is_active 
                ? `<span class="badge badge-active">Active</span>`
                : `<span class="badge badge-inactive">Paused / Cap Met</span>`;
                
            let interestsHtml = "";
            try {
                // target_interests is a list of strings
                const interests = Array.isArray(c.target_interests) ? c.target_interests : JSON.parse(c.target_interests);
                interestsHtml = interests.map(tag => `<span class="tag-badge">${tag}</span>`).join(" ");
            } catch(e) {
                interestsHtml = `<span class="text-muted">None</span>`;
            }

            const card = document.createElement("div");
            card.className = "campaign-card";
            card.innerHTML = `
                <div class="campaign-card-header">
                    <div class="campaign-name-advertiser">
                        <h4>${escapeHtml(c.name)}</h4>
                        <span>Advertiser: <b>${escapeHtml(c.advertiser)}</b></span>
                    </div>
                    ${statusBadge}
                </div>
                
                <div class="budget-progress-container">
                    <div class="budget-stats-row">
                        <span>Spend: <b>$${c.current_spend.toFixed(2)}</b></span>
                        <span>Budget: <b>$${c.budget.toFixed(2)}</b></span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${Math.min(100, spendPercent)}%; background: ${progressColor};"></div>
                    </div>
                </div>
                
                <div class="campaign-details-grid">
                    <div class="camp-detail-item">
                        <span class="camp-detail-label">Bid Amount</span>
                        <span><b>$${c.bid_amount.toFixed(2)}</b> CPM</span>
                    </div>
                    <div class="camp-detail-item">
                        <span class="camp-detail-label">Age Targeting</span>
                        <span><b>${c.target_age_min} - ${c.target_age_max}</b> yrs</span>
                    </div>
                    <div class="camp-detail-item">
                        <span class="camp-detail-label">Location Targeting</span>
                        <span><b>${escapeHtml(c.target_location)}</b></span>
                    </div>
                    <div class="camp-detail-item">
                        <span class="camp-detail-label">Interests Targeting</span>
                        <div class="interest-tag-badges">${interestsHtml}</div>
                    </div>
                </div>
                
                <div class="creative-preview-box">
                    <div class="creative-title">${escapeHtml(c.ad_title)}</div>
                    <div class="creative-body">${escapeHtml(c.ad_body)}</div>
                </div>
                
                <div class="camp-card-actions">
                    <button class="btn btn-secondary btn-icon" onclick="editCampaign(${c.id})" title="Edit Campaign">
                        <i data-lucide="edit-3" style="width:14px;height:14px;"></i> Edit
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
        
        lucide.createIcons();
    } catch (err) {
        console.error(err);
    }
}

async function handleCampaignSubmit(e) {
    e.preventDefault();
    
    const id = document.getElementById("form-campaign-id").value;
    const name = document.getElementById("campaign-name").value;
    const advertiser = document.getElementById("campaign-advertiser").value;
    const bid_amount = parseFloat(document.getElementById("campaign-bid").value);
    const budget = parseFloat(document.getElementById("campaign-budget").value);
    const age_min = parseInt(document.getElementById("campaign-age-min").value);
    const age_max = parseInt(document.getElementById("campaign-age-max").value);
    const location = document.getElementById("campaign-location").value;
    const interestsInput = document.getElementById("campaign-interests").value;
    
    const target_interests = interestsInput ? interestsInput.split(",").map(i => i.trim()).filter(i => i.length > 0) : [];
    
    const ad_title = document.getElementById("campaign-ad-title").value;
    const ad_body = document.getElementById("campaign-ad-body").value;
    const ad_creative_url = document.getElementById("campaign-ad-url").value;

    const payload = {
        name,
        advertiser,
        bid_amount,
        budget,
        target_age_min: age_min,
        target_age_max: age_max,
        target_location: location,
        target_interests,
        ad_title,
        ad_body,
        ad_creative_url
    };

    try {
        let response;
        if (id) {
            // Update Campaign
            response = await fetch(`${API_BASE}/campaign/${id}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        } else {
            // Create Campaign
            response = await fetch(`${API_BASE}/campaign`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
        }
        
        if (!response.ok) throw new Error("Failed to save campaign");
        
        resetCampaignForm();
        refreshAllData();
        alert(id ? "Campaign updated successfully!" : "Campaign published successfully!");
    } catch(err) {
        alert(err.message);
    }
}

async function editCampaign(id) {
    try {
        const response = await fetch(`${API_BASE}/campaign/${id}`);
        if (!response.ok) throw new Error("Campaign not found");
        const c = await response.json();
        
        document.getElementById("form-campaign-id").value = c.id;
        document.getElementById("campaign-name").value = c.name;
        document.getElementById("campaign-advertiser").value = c.advertiser;
        document.getElementById("campaign-bid").value = c.bid_amount;
        document.getElementById("campaign-budget").value = c.budget;
        document.getElementById("campaign-age-min").value = c.target_age_min;
        document.getElementById("campaign-age-max").value = c.target_age_max;
        document.getElementById("campaign-location").value = c.target_location;
        
        const interests = Array.isArray(c.target_interests) ? c.target_interests : JSON.parse(c.target_interests);
        document.getElementById("campaign-interests").value = interests.join(", ");
        
        document.getElementById("campaign-ad-title").value = c.ad_title;
        document.getElementById("campaign-ad-body").value = c.ad_body;
        document.getElementById("campaign-ad-url").value = c.ad_creative_url;
        
        document.getElementById("campaign-form-title").innerText = "Edit Campaign Configuration";
        document.getElementById("btn-campaign-submit").innerText = "Save Updates";
        
        // Scroll to form on mobile/tab
        document.querySelector(".form-column").scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert(err.message);
    }
}

function resetCampaignForm() {
    document.getElementById("form-campaign-id").value = "";
    document.getElementById("campaign-form").reset();
    document.getElementById("campaign-form-title").innerText = "Create New Campaign";
    document.getElementById("btn-campaign-submit").innerText = "Publish Campaign";
}

// 2. Users Module
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/users`);
        if (!response.ok) throw new Error("Failed to load users");
        usersList = await response.json();
        
        // Render user rows in table
        const tbody = document.getElementById("users-table-body");
        tbody.innerHTML = "";
        
        // Render dropdown options in simulator
        const select = document.getElementById("sim-user-select");
        select.innerHTML = '<option value="">-- Choose User Profile --</option>';
        
        usersList.forEach(u => {
            let interestsHtml = "";
            try {
                const interests = Array.isArray(u.interests) ? u.interests : JSON.parse(u.interests);
                interestsHtml = interests.map(tag => `<span class="tag-badge">${tag}</span>`).join(" ");
            } catch(e) {
                interestsHtml = `<span class="text-muted">None</span>`;
            }

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><b>${u.id}</b></td>
                <td><b>${escapeHtml(u.name)}</b></td>
                <td>${u.age}</td>
                <td>${escapeHtml(u.location)}</td>
                <td><div class="interest-tag-badges">${interestsHtml}</div></td>
            `;
            tbody.appendChild(tr);
            
            // Add options to simulator dropdown
            const opt = document.createElement("option");
            opt.value = u.id;
            opt.innerText = `${u.name} (Age: ${u.age}, ${u.location})`;
            select.appendChild(opt);
        });
        
    } catch(err) {
        console.error(err);
    }
}

async function handleUserSubmit(e) {
    e.preventDefault();
    
    const name = document.getElementById("user-name").value;
    const age = parseInt(document.getElementById("user-age").value);
    const location = document.getElementById("user-location").value;
    const interestsInput = document.getElementById("user-interests").value;
    
    const interests = interestsInput ? interestsInput.split(",").map(i => i.trim()).filter(i => i.length > 0) : [];

    const payload = { name, age, location, interests };
    
    try {
        const response = await fetch(`${API_BASE}/user`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error("Failed to create user");
        
        document.getElementById("user-form").reset();
        refreshAllData();
        alert("User profile added successfully!");
    } catch(err) {
        alert(err.message);
    }
}

function updateUserPreview(userId) {
    const preview = document.getElementById("sim-user-preview");
    if (!userId) {
        preview.innerHTML = `<span class="text-muted italic">No user selected</span>`;
        return;
    }
    
    const user = usersList.find(u => u.id == userId);
    if (!user) return;
    
    let interestsHtml = "";
    try {
        const interests = Array.isArray(user.interests) ? user.interests : JSON.parse(user.interests);
        interestsHtml = interests.map(tag => `<span class="tag-badge">${tag}</span>`).join(" ");
    } catch(e) {
        interestsHtml = `<span class="text-muted">None</span>`;
    }

    preview.innerHTML = `
        <h5>${escapeHtml(user.name)}</h5>
        <div class="user-preview-details">
            <span>Age: <b>${user.age}</b></span>
            <span>Location: <b>${escapeHtml(user.location)}</b></span>
        </div>
        <div style="margin-top: 6px;">
            <span style="font-size:11px;color:var(--text-muted);display:block;margin-bottom:2px;">Interests:</span>
            <div class="interest-tag-badges">${interestsHtml}</div>
        </div>
    `;
}

// 3. Analytics & Charts Module
async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/analytics/summary`);
        if (!response.ok) throw new Error("Failed to load analytics");
        const data = await response.json();
        
        // Update KPI values
        document.getElementById("kpi-revenue").innerText = `$${data.aggregate.revenue.toFixed(2)}`;
        document.getElementById("kpi-impressions").innerText = data.aggregate.impressions.toLocaleString();
        document.getElementById("kpi-clicks").innerText = data.aggregate.clicks.toLocaleString();
        document.getElementById("kpi-ctr").innerText = `${(data.aggregate.ctr * 100).toFixed(2)}%`;
        
        // Render Performance Table
        const tbody = document.getElementById("performance-table-body");
        tbody.innerHTML = "";
        
        if (data.campaigns.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No campaign data available.</td></tr>`;
            return;
        }

        const labels = [];
        const spendData = [];
        const budgets = [];
        
        data.campaigns.forEach(c => {
            labels.push(c.campaign_name);
            spendData.push(c.current_spend);
            budgets.push(c.budget);

            const statusClass = c.is_active ? "badge-won" : "badge-lost";
            const statusText = c.is_active ? "Active" : "Cap Met";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><b>${escapeHtml(c.campaign_name)}</b></td>
                <td>${escapeHtml(c.advertiser)}</td>
                <td>
                    <div style="font-size:11px;color:var(--text-secondary);margin-bottom:2px;">$${c.current_spend.toFixed(2)} / $${c.budget.toFixed(2)}</div>
                    <div class="progress-bar-bg" style="height: 4px; width: 100px;">
                        <div class="progress-bar-fill" style="width: ${Math.min(100, (c.current_spend / c.budget)*100)}%;"></div>
                    </div>
                </td>
                <td><b>${(c.ctr * 100).toFixed(2)}%</b><br><span style="font-size:10px;color:var(--text-muted);">${c.clicks} clicks / ${c.impressions} imps</span></td>
                <td><b>$${c.revenue.toFixed(2)}</b></td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            `;
            tbody.appendChild(tr);
        });
        
        // Draw Chart
        renderSpendChart(labels, spendData, budgets);
        
    } catch(err) {
        console.error(err);
    }
}

function renderSpendChart(labels, spend, budgets) {
    const ctx = document.getElementById("campaignSpendChart").getContext("2d");
    
    if (spendChart) {
        spendChart.destroy();
    }
    
    spendChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Current Spend ($)',
                    data: spend,
                    backgroundColor: 'rgba(99, 102, 241, 0.75)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Total Budget ($)',
                    data: budgets,
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#9ca3af' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: '#f3f4f6', font: { family: 'Plus Jakarta Sans' } }
                }
            }
        }
    });
}

// 4. Logs and Fraud Module
async function loadLogs() {
    try {
        // Load Auction History
        const histRes = await fetch(`${API_BASE}/history?limit=30`);
        const history = await histRes.json();
        
        const histTbody = document.getElementById("history-table-body");
        histTbody.innerHTML = "";
        
        history.forEach(h => {
            const timeStr = formatTimestamp(h.timestamp);
            let badgeClass = "badge-lost";
            if (h.status === "WON") badgeClass = "badge-won";
            if (h.status.startsWith("FILTERED")) badgeClass = "badge-filtered";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-family:var(--font-mono);font-size:12px;">${timeStr}</td>
                <td><b>${escapeHtml(h.campaign_name)}</b><br><span style="font-size:10px;color:var(--text-muted);">${escapeHtml(h.advertiser)}</span></td>
                <td>${escapeHtml(h.user_name)} <span style="font-size:11px;color:var(--text-muted);">(ID ${h.user_id})</span></td>
                <td>$${h.bid_amount.toFixed(2)}</td>
                <td style="font-family:var(--font-mono);">${h.score.toFixed(4)}</td>
                <td>
                    <span class="badge ${badgeClass}">${h.status}</span>
                    ${h.reason ? `<div style="font-size:10px;color:var(--text-muted);margin-top:2px;">${escapeHtml(h.reason)}</div>` : ''}
                </td>
            `;
            histTbody.appendChild(tr);
        });

        // Load Fraud Logs
        const fraudRes = await fetch(`${API_BASE}/fraud?limit=30`);
        const fraud = await fraudRes.json();
        
        const fraudTbody = document.getElementById("fraud-table-body");
        fraudTbody.innerHTML = "";
        
        if (fraud.length === 0) {
            fraudTbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No security anomalies detected. System secure.</td></tr>`;
            return;
        }

        fraud.forEach(f => {
            const timeStr = formatTimestamp(f.timestamp);
            const scoreClass = f.score >= 0.9 ? "color:var(--color-danger);font-weight:600;" : "color:var(--color-warning);";
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-family:var(--font-mono);font-size:12px;">${timeStr}</td>
                <td><b style="font-family:var(--font-mono);">${f.ip_address}</b></td>
                <td>${f.user_id ? `${escapeHtml(f.user_name)} (ID ${f.user_id})` : '<span class="text-muted">N/A</span>'}</td>
                <td><span style="color:#f87171;">${escapeHtml(f.reason)}</span></td>
                <td><span style="${scoreClass}">${(f.score * 100).toFixed(0)}% (HIGH)</span></td>
            `;
            fraudTbody.appendChild(tr);
        });

    } catch(err) {
        console.error(err);
    }
}

// 5. RTB Simulator Engine
async function runRtbSimulation() {
    const userSelect = document.getElementById("sim-user-select");
    const userId = parseInt(userSelect.value);
    const ipAddress = document.getElementById("sim-ip").value;
    const device = document.getElementById("sim-device").value;
    
    if (!userId) {
        alert("Please select a user profile to simulate the bid request.");
        return;
    }
    
    const term = document.getElementById("sim-terminal-body");
    const adArea = document.getElementById("ad-render-area");
    
    // Reset views
    term.innerHTML = `<span class="trace-line info">> Generating Ad Bid Request payload...</span>`;
    adArea.innerHTML = `
        <div class="ad-placeholder">
            <div class="status-indicator online" style="width:20px;height:20px;margin-bottom:8px;"></div>
            <span>Auction in progress...</span>
        </div>
    `;

    try {
        const payload = {
            user_id: userId,
            ip_address: ipAddress,
            device: device,
            page_url: "https://adsphere-ad-network.com/capstone-test"
        };
        
        // POST request to trigger auction
        const response = await fetch(`${API_BASE}/auction/request`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error("RTB Auction Request failed");
        
        const result = await response.json();
        
        // Output trace sequentially with typing delays to simulate real systems
        let delay = 0;
        term.innerHTML = "";
        
        result.trace.forEach((line) => {
            setTimeout(() => {
                const trLine = document.createElement("span");
                trLine.className = "trace-line";
                
                // Color codes for trace keywords
                if (line.includes("filtered:") || line.includes("blocked:") || line.includes("not found")) {
                    trLine.classList.add("danger");
                } else if (line.includes("Winner Selected:") || line.includes("Auction complete")) {
                    trLine.classList.add("success");
                } else if (line.includes("Scored:")) {
                    trLine.classList.add("info");
                } else if (line.includes("Starting") || line.includes("Loaded")) {
                    trLine.classList.add("info");
                }
                
                trLine.innerText = `> ${line}`;
                term.appendChild(trLine);
                term.scrollTop = term.scrollHeight;
            }, delay);
            delay += 100; // 100ms interval per trace log line
        });

        // Display outcome after tracing completes
        setTimeout(() => {
            if (result.auction_status === "completed" && result.winning_ad) {
                const ad = result.winning_ad;
                
                // Fire impression pixel (invisible <img> tag)
                const impImg = document.createElement("img");
                impImg.src = ad.impression_tracking_url;
                impImg.style.display = "none";
                document.body.appendChild(impImg);
                console.log(`Impression pixel triggered: ${ad.impression_tracking_url}`);

                // Render Beautiful Ad layout Card
                adArea.innerHTML = `
                    <div class="rendered-ad-card">
                        <img class="ad-image" src="${ad.ad_creative_url}" alt="Ad image">
                        <div class="ad-content">
                            <span class="ad-sponsored-label">Sponsored by ${escapeHtml(ad.advertiser)}</span>
                            <div class="ad-headline">${escapeHtml(ad.ad_title)}</div>
                            <div class="ad-desc">${escapeHtml(ad.ad_body)}</div>
                            <a class="ad-click-button" href="${ad.click_tracking_url}" target="_blank" onclick="handleAdClick(event, '${ad.click_tracking_url}')">
                                Learn More
                            </a>
                        </div>
                    </div>
                `;
            } else {
                adArea.innerHTML = `
                    <div class="ad-placeholder" style="color:var(--color-danger);">
                        <i data-lucide="x-circle"></i>
                        <span>No Ad Displayed (${result.auction_status})</span>
                    </div>
                `;
                lucide.createIcons();
            }
            
            // Reload logs in background to show this auction
            refreshAllData();
        }, delay);
        
    } catch(err) {
        term.innerHTML += `<br><span class="trace-line danger">> Fatal Simulator Error: ${err.message}</span>`;
        adArea.innerHTML = `<div class="ad-placeholder" style="color:var(--color-danger);">Simulation Failure</div>`;
    }
}

// Track Ad Clicks via background redirect trigger and refresh numbers
function handleAdClick(event, clickUrl) {
    console.log(`Ad Clicked! Tracking URL triggered: ${clickUrl}`);
    // Let the click open in a new tab, but refresh the dashboard metrics after 1 second so the click counts reflect on the graph!
    setTimeout(() => {
        refreshAllData();
    }, 1000);
}

// Helper Utilities
function formatTimestamp(isoStr) {
    if (!isoStr) return "";
    const date = new Date(isoStr);
    const hours = String(date.getHours()).padStart(2, '0');
    const mins = String(date.getMinutes()).padStart(2, '0');
    const secs = String(date.getSeconds()).padStart(2, '0');
    const ms = String(date.getMilliseconds()).padStart(3, '0');
    return `${hours}:${mins}:${secs}.${ms}`;
}

function escapeHtml(text) {
    if (!text) return "";
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
}
