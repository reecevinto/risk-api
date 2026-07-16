// =====================================================
// RISK API DASHBOARD
// dashboard.js
// All UI behavior (sidebar, dark mode, charts, filters,
// copy-to-clipboard, user menu, logout) plus the original
// data-loading / billing logic now live in this one file.
// =====================================================

// ==============================
// CONSTANTS
// ==============================

const API_BASE = "http://localhost:8000";

const API_KEY = localStorage.getItem("api_key");

// Redirect to login if no API key exists
if (!API_KEY) {

    window.location.href = "login.html";

    throw new Error("No API Key found.");

}

// ==============================
// GENERIC HELPER FUNCTIONS
// ==============================

/**
 * Get an element by ID.
 */
function $(id) {

    return document.getElementById(id);

}

/**
 * Safely update text content.
 */
function setText(id, value) {

    const el = $(id);

    if (el) el.innerText = value;

}

/**
 * Update the dashboard status message (header, next to the live dot).
 */
function setStatus(message, color = "gray") {

    const status = $("status");

    if (!status) return;

    status.className = `font-medium text-${color}-600 dark:text-${color}-400`;

    status.innerText = message;

}

/**
 * Format an ISO date into the user's locale.
 */
function formatDate(dateString) {

    if (!dateString) {

        return "--";

    }

    return new Date(dateString).toLocaleString(
        undefined,
        {
            dateStyle: "medium",
            timeStyle: "short"
        }
    );

}

/**
 * Update the subscription status color.
 */
function updateSubscriptionStatus(status) {

    const element = $("subStatus");

    if (!element) return;

    element.innerText = status;

    switch (status) {

        case "ACTIVE":

            element.className = "font-semibold text-green-600 dark:text-green-400";
            break;

        case "TRIALING":

            element.className = "font-semibold text-blue-600 dark:text-blue-400";
            break;

        case "PAST_DUE":

            element.className = "font-semibold text-yellow-600 dark:text-yellow-400";
            break;

        default:

            element.className = "font-semibold text-red-600 dark:text-red-400";

    }

}

/**
 * Update the usage progress bar (the wide bar in "Usage Overview").
 * The mini bar on the KPI card is kept in sync automatically via
 * the MutationObserver set up in the UI section below.
 */
function updateUsageBar(percent) {

    const usageBar = $("usageBar");

    if (!usageBar) return;

    const safePercent = Math.min(Math.max(percent, 0), 100);

    usageBar.style.width = `${safePercent}%`;

}

/**
 * Bucket a numeric risk score into low / medium / high.
 * Thresholds are an assumption (0-30 low, 30-70 medium, 70+ high) —
 * adjust to match your backend's actual scoring scale if different.
 */
function riskLevel(score) {

    const value = Number(score) || 0;

    if (value >= 70) return "high";
    if (value >= 30) return "medium";
    return "low";

}

/**
 * Small emoji + label badge for risk level.
 */
function riskBadge(level) {

    const map = {
        low: { emoji: "🟢", label: "Low", cls: "risk-badge-low" },
        medium: { emoji: "🟡", label: "Medium", cls: "risk-badge-medium" },
        high: { emoji: "🔴", label: "High", cls: "risk-badge-high" },
    };

    return map[level] || map.low;

}

/**
 * Clear recent requests list.
 */
function clearRecentRequests() {

    const el = $("recent");

    if (el) el.innerHTML = "";

}

/**
 * Show "No requests" placeholder.
 */
function showNoRequests() {

    const el = $("recent");

    if (!el) return;

    el.innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-10 text-slate-400">
                No recent requests
            </td>
        </tr>
    `;

}

// ==============================
// API HELPER
// ==============================

/**
 * Generic API request helper.
 */
async function apiRequest(endpoint, options = {}) {

    const response = await fetch(
        `${API_BASE}${endpoint}`,
        {
            ...options,

            headers: {

                "Content-Type": "application/json",

                "x-api-key": API_KEY,

                ...(options.headers || {})

            }

        }
    );

    if (!response.ok) {

        let message = `Request failed (${response.status})`;

        try {

            const error = await response.json();

            if (error.detail) {

                message = error.detail;

            }

        } catch (_) {}

        throw new Error(message);

    }

    return response.json();

}

// =====================================================
// UI BEHAVIOR — sidebar, dark mode, user menu, copy key,
// mini usage bar sync, table search/filter, charts
// =====================================================

// ------------------------------
// SIDEBAR (mobile)
// ------------------------------
function toggleSidebar() {
    $("sidebar")?.classList.toggle("open");
    $("sidebarOverlay")?.classList.toggle("hidden");
}

// ------------------------------
// DARK MODE
// ------------------------------
function applyDarkModePreference() {
    const saved = window.__theme || "light";
    document.documentElement.classList.toggle("dark", saved === "dark");
}
function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle("dark");
    window.__theme = isDark ? "dark" : "light";
    refreshChartTheme();
}
applyDarkModePreference();

// ------------------------------
// USER MENU
// ------------------------------
function toggleUserMenu() {
    $("userMenu")?.classList.toggle("hidden");
}
document.addEventListener("click", (e) => {
    const menu = $("userMenu");
    if (!menu) return;
    const trigger = e.target.closest("button");
    if (!menu.contains(e.target) && !(trigger && trigger.onclick && trigger.onclick.toString().includes("toggleUserMenu"))) {
        menu.classList.add("hidden");
    }
});

// ------------------------------
// COPY API KEY
// ------------------------------
function copyApiKey() {
    const el = $("apiKey");
    if (!el) return;
    const text = el.getAttribute("data-full") || el.textContent.trim();
    navigator.clipboard.writeText(text).then(() => {
        const btn = $("copyBtn");
        if (!btn) return;
        const original = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = original; }, 1500);
    });
}

// ------------------------------
// KPI usage mini-bar sync (mirrors #usageBar width)
// ------------------------------
function syncUsageMiniBar() {
    const bar = $("usageBar");
    const mini = $("usageBarMini");
    if (bar && mini) mini.style.width = bar.style.width || "0%";
}
if ($("usageBar")) {
    new MutationObserver(syncUsageMiniBar).observe(
        $("usageBar"), { attributes: true, attributeFilter: ["style"] }
    );
}

// ------------------------------
// REQUESTS TABLE — SEARCH & FILTER
// Rows rendered by loadDashboard() carry data-status="normal|overage"
// and data-risk="low|medium|high" attributes for these filters.
// ------------------------------
function filterRequests() {
    const searchEl = $("searchInput");
    const statusEl = $("statusFilter");
    const riskEl = $("riskFilter");
    if (!searchEl || !statusEl || !riskEl) return;

    const search = searchEl.value.trim().toLowerCase();
    const status = statusEl.value;
    const risk = riskEl.value;
    const rows = document.querySelectorAll("#recent tr");
    let visible = 0;

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchesSearch = !search || text.includes(search);
        const matchesStatus = !status || (row.dataset.status || "").toLowerCase() === status;
        const matchesRisk = !risk || (row.dataset.risk || "").toLowerCase() === risk;
        const show = matchesSearch && matchesStatus && matchesRisk;
        row.style.display = show ? "" : "none";
        if (show) visible++;
    });

    const noResults = $("noResults");
    if (noResults) noResults.classList.toggle("hidden", rows.length === 0 || visible > 0);
}
// Re-apply filters whenever loadDashboard() repopulates the table
const recentBody = $("recent");
if (recentBody) new MutationObserver(filterRequests).observe(recentBody, { childList: true });

// ------------------------------
// CHARTS (Chart.js)
// ------------------------------
const chartTextColor = () => document.documentElement.classList.contains("dark") ? "#94a3b8" : "#64748b";
const chartGridColor = () => document.documentElement.classList.contains("dark") ? "rgba(148,163,184,0.1)" : "rgba(100,116,139,0.08)";

let requestsChart, riskChart, endpointChart;

function initCharts() {

    const requestsChartCtx = $("requestsChart");
    const riskChartCtx = $("riskChart");
    const endpointChartCtx = $("endpointChart");

    if (requestsChartCtx) {
        requestsChart = new Chart(requestsChartCtx, {
            type: "line",
            data: {
                labels: [],
                datasets: [{
                    label: "Requests",
                    data: [],
                    borderColor: "#3b82f6",
                    backgroundColor: "rgba(59,130,246,0.1)",
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3,
                    pointBackgroundColor: "#3b82f6",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: chartTextColor() } },
                    y: { beginAtZero: true, grid: { color: chartGridColor() }, ticks: { color: chartTextColor() } }
                }
            }
        });
    }

    if (riskChartCtx) {
        riskChart = new Chart(riskChartCtx, {
            type: "doughnut",
            data: {
                labels: ["Low", "Medium", "High"],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ["#22c55e", "#eab308", "#ef4444"],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "bottom", labels: { color: chartTextColor(), usePointStyle: true, boxWidth: 8 } } }
            }
        });
    }

    if (endpointChartCtx) {
        endpointChart = new Chart(endpointChartCtx, {
            type: "bar",
            data: {
                labels: [],
                datasets: [{
                    label: "Requests",
                    data: [],
                    backgroundColor: "#3b82f6",
                    borderRadius: 6,
                    maxBarThickness: 28,
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: chartGridColor() }, ticks: { color: chartTextColor() } },
                    y: { grid: { display: false }, ticks: { color: chartTextColor() } }
                }
            }
        });
    }
}

function refreshChartTheme() {
    [requestsChart, endpointChart].forEach(chart => {
        if (!chart) return;
        chart.options.scales.x.ticks.color = chartTextColor();
        chart.options.scales.y.ticks.color = chartTextColor();
        if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = chartGridColor();
        if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = chartGridColor();
        chart.update();
    });
    if (riskChart) {
        riskChart.options.plugins.legend.labels.color = chartTextColor();
        riskChart.update();
    }
}

window.updateRequestsChart = function (labels, data) {
    if (!requestsChart) return;
    requestsChart.data.labels = labels;
    requestsChart.data.datasets[0].data = data;
    requestsChart.update();
};
window.updateRiskChart = function (low, medium, high) {
    if (!riskChart) return;
    riskChart.data.datasets[0].data = [low, medium, high];
    riskChart.update();
};
window.updateEndpointChart = function (labels, data) {
    if (!endpointChart) return;
    endpointChart.data.labels = labels;
    endpointChart.data.datasets[0].data = data;
    endpointChart.update();
};

/**
 * Derive chart data from the recent_requests list returned by
 * /admin/usage, since the API doesn't expose a dedicated
 * time-series / endpoint-breakdown endpoint yet.
 */
function updateAnalyticsCharts(analytics) {

    // -------------------------
    // Requests Over Time
    // -------------------------

    const dailyUsage = analytics.daily_usage || [];

    window.updateRequestsChart(
        dailyUsage.map(d => d.date),
        dailyUsage.map(d => d.requests)
    );

    // -------------------------
    // Endpoint Usage
    // -------------------------

    const endpointUsage = analytics.endpoint_breakdown || [];

    window.updateEndpointChart(
        endpointUsage.map(e => e.endpoint),
        endpointUsage.map(e => e.requests)
    );

    // -------------------------
    // Risk Distribution
    // -------------------------

    let low = 0;
    let medium = 0;
    let high = 0;

    (analytics.recent_requests || []).forEach(r => {

        const level = riskLevel(r.risk_score);

        if (level === "low") low++;
        else if (level === "medium") medium++;
        else high++;

    });

    window.updateRiskChart(low, medium, high);

    // =====================================================
    // PLACED HERE: DYNAMIC METRICS TABLES POPULATION
    // =====================================================

    // 1. Populate dailyUsageTable
    const dailyTable = $("dailyUsageTable");
    if (dailyTable && analytics.daily_usage) {
        dailyTable.innerHTML = analytics.daily_usage.map(d => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2 font-medium text-slate-600 dark:text-slate-400">${d.date}</td>
                <td class="px-4 py-2 text-right font-semibold text-slate-800 dark:text-slate-200">${d.requests}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }

    // 2. Populate endpointBreakdownTable
    const breakdownTable = $("endpointBreakdownTable");
    if (breakdownTable && analytics.endpoint_breakdown) {
        breakdownTable.innerHTML = analytics.endpoint_breakdown.map(e => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2"><span class="px-1.5 py-0.5 rounded text-xs font-mono bg-slate-100 dark:bg-slate-800 text-blue-600">${e.endpoint}</span></td>
                <td class="px-4 py-2 text-right font-semibold text-slate-800 dark:text-slate-200">${e.requests}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }

    // 3. Populate endpointRiskTable
    const riskTable = $("endpointRiskTable");
    if (riskTable && analytics.endpoint_average_risk) {
        riskTable.innerHTML = analytics.endpoint_average_risk.map(r => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2 font-mono text-xs text-slate-600 dark:text-slate-400">${r.endpoint || r.path || '--'}</td>
                <td class="px-4 py-2 text-right font-bold text-red-500">${(r.average_risk || 0).toFixed(2)}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }

}

// ------------------------------
// LOGOUT
// ------------------------------
function logout() {
    localStorage.removeItem("api_key");
    window.location.href = "login.html";
}

// ------------------------------
// "Updated Xs ago" live ticker
// ------------------------------
let lastLoadTimestamp = Date.now();

function tickLastUpdated() {
    const el = $("lastUpdated");
    if (!el) return;
    const seconds = Math.floor((Date.now() - lastLoadTimestamp) / 1000);
    if (seconds < 5) {
        el.innerText = "Updated just now";
    } else if (seconds < 60) {
        el.innerText = `Updated ${seconds}s ago`;
    } else {
        el.innerText = `Updated ${Math.floor(seconds / 60)}m ago`;
    }
}
setInterval(tickLastUpdated, 1000);

// =====================================================
// LOAD DASHBOARD
// =====================================================

async function loadDashboard() {

    setStatus("Loading dashboard...", "blue");

    try {

        // ==============================
        // USER INFO
        // ==============================

        const user = await apiRequest("/user/me");

        const apiKeyEl = $("apiKey");
        if (apiKeyEl) {
            const fullKey = user.api_key || "No API key returned";
            apiKeyEl.innerText = fullKey;
            apiKeyEl.setAttribute("data-full", fullKey);
        }

        setText("apiKeyRotated", formatDate(user.api_key_rotated_at || user.api_key_created_at));

        // PLAN INFO
        setText("plan", user.plan || "FREE");
        setText("userPlanLabel", (user.plan || "FREE").toUpperCase());

        updateSubscriptionStatus(user.subscription?.status || "NO SUBSCRIPTION");

        setText("stripeStatus", user.stripe_customer_id ? "LINKED" : "NOT LINKED");

        // ==============================
        // METERED BILLING
        // ==============================

        const usage = user.usage || {};

        const currentUsage = usage.current ?? 0;
        const usageLimit = usage.limit ?? 0;
        const remainingUsage = usage.remaining ?? 0;
        const usagePercent = usage.percent_used ?? 0;

        setText("currentUsage", currentUsage);
        setText("usageLimit", usageLimit);
        setText("remainingUsage", `${remainingUsage} Remaining`);
        setText("usagePercent", `${usagePercent}%`);
        setText("usagePercentDetail", `${usagePercent}%`);

        updateUsageBar(usagePercent);

        // ==============================
        // BILLING CYCLE
        // ==============================

        const billingCycle = user.billing_cycle || {};

        setText("billingStart", billingCycle.current_period?.start ? formatDate(billingCycle.current_period.start) : "--");
        setText("billingEnd", billingCycle.current_period?.end ? formatDate(billingCycle.current_period.end) : "--");
        setText("nextReset", billingCycle.next_reset ? formatDate(billingCycle.next_reset) : "--");

        // ==============================
        // OVERAGE BILLING
        // ==============================

        const billing = user.billing || {};

        setText("overageEnabled", user.overage_enabled ? "YES" : "NO");
        setText("planAllowsOverage", user.plan_allow_overage ? "YES" : "NO");
        setText("overageRequests", billing.overage_requests ?? 0);
        setText("overagePrice", `$${billing.price_per_request ?? 0}`);
        setText("overageCharge", `$${billing.total_charge ?? 0}`);

        // ==============================
        // USAGE STATS
        // ==============================

        const usageStats = await apiRequest("/admin/usage");

        setText("total", usageStats.total_requests ?? 0);
        setText("avg", usageStats.average_risk_score?.toFixed(2) ?? "0.00");
        setText("requestsToday", usageStats.requests_today ?? 0);

setText("requestsWeek", usageStats.requests_this_week ?? 0);

setText("mostUsedEndpoint", usageStats.most_used_endpoint ?? "--");

setText(
    "endpointRisk",
    usageStats.endpoint_average_risk?.length
        ? usageStats.endpoint_average_risk[0].average_risk.toFixed(2)
        : "--"
);

setText("overageRequestsCard", usageStats.overage_requests ?? 0);

setText(
    "overagePercentCard",
    `${usageStats.overage_percentage ?? 0}%`
);

        // ==============================
        // RECENT REQUESTS TABLE
        // ==============================

        const tbody = $("recent");

        if (tbody) {

            tbody.innerHTML = "";

            if (!usageStats.recent_requests?.length) {

                showNoRequests();

            } else {

                usageStats.recent_requests.forEach(r => {

                    const level = riskLevel(r.risk_score);
                    const badge = riskBadge(level);
                    const status = r.is_overage ? "overage" : "normal";

                    const row = document.createElement("tr");
                    row.className = "hover:bg-slate-50 dark:hover:bg-slate-800/50 transition";
                    row.dataset.status = status;
                    row.dataset.risk = level;

                    row.innerHTML = `
                        <td class="px-6 py-3.5 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                            ${formatDate(r.created_at)}
                        </td>
                        <td class="px-6 py-3.5">
                            <span class="inline-block px-2 py-1 rounded-md bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 text-xs font-semibold">
                                ${r.endpoint || "-"}
                            </span>
                        </td>
                        <td class="px-6 py-3.5 text-slate-700 dark:text-slate-300">
                            ${r.email || "-"}
                        </td>
                        <td class="px-6 py-3.5 mono text-xs text-slate-500 dark:text-slate-400">
                            ${r.ip || "-"}
                        </td>
                        <td class="px-6 py-3.5 text-center">
                            <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${badge.cls}">
                                ${badge.emoji} ${r.risk_score ?? "-"}
                            </span>
                        </td>
                        <td class="px-6 py-3.5 text-center">
                            <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${status === "overage" ? "risk-badge-high" : "risk-badge-low"}">
                                ${status === "overage" ? "🔴 Overage" : "🟢 Normal"}
                            </span>
                        </td>
                    `;

                    tbody.appendChild(row);

                });

            }

            filterRequests();

        }

        // ==============================
        // CHARTS
        // ==============================

        updateAnalyticsCharts(usageStats);

        lastLoadTimestamp = Date.now();
        tickLastUpdated();

        setStatus("✅ Dashboard loaded successfully", "green");

    } catch (error) {

        console.error(error);

        setStatus(`❌ ${error.message}`, "red");

    }

}

// ==============================
// BILLING ACTIONS
// ==============================

async function upgradeToPro(button) {

    const statusEl = $("billingStatus");

    const originalText = button.innerText;

    button.disabled = true;
    button.innerText = "Processing...";

    try {

        const data = await apiRequest("/billing/checkout/pro", { method: "POST" });

        if (statusEl) statusEl.innerText = "Redirecting to Stripe...";

        window.location.href = data.checkout_url;

    } catch (error) {

        if (statusEl) statusEl.innerText = error.message;

    } finally {

        button.disabled = false;
        button.innerText = originalText;

    }

}

async function upgradeToEnterprise(button) {

    const statusEl = $("billingStatus");

    const originalText = button.innerText;

    button.disabled = true;
    button.innerText = "Processing...";

    try {

        const data = await apiRequest("/billing/checkout/enterprise", { method: "POST" });

        if (statusEl) statusEl.innerText = "Redirecting to Stripe...";

        window.location.href = data.checkout_url;

    } catch (error) {

        if (statusEl) statusEl.innerText = error.message;

    } finally {

        button.disabled = false;
        button.innerText = originalText;

    }

}

// ==============================
// INIT + AUTO REFRESH
// ==============================

initCharts();
loadDashboard();

setInterval(loadDashboard, 30000);