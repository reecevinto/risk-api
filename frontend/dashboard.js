// =====================================================
// RISK API DASHBOARD & DEVICE INTELLIGENCE
// dashboard.js
// Complete implementation matching FastAPI routes:
// - GET /user/me
// - GET /analytics/summary
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

function $(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const el = $(id);
    if (el) el.innerText = value;
}

function setStatus(message, color = "gray") {
    const status = $("status");
    if (!status) return;
    status.className = `font-medium text-${color}-600 dark:text-${color}-400`;
    status.innerText = message;
}

function formatDate(dateString) {
    if (!dateString) return "--";
    const parsed = new Date(dateString);
    if (isNaN(parsed.getTime())) return dateString;
    return parsed.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

function formatNumber(num) {
    const val = Number(num) || 0;
    return val.toLocaleString();
}

function truncateFingerprint(fp) {
    if (!fp) return "--";
    return fp.length > 8 ? `${fp.substring(0, 8)}...` : fp;
}

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

function updateUsageBar(percent) {
    const usageBar = $("usageBar");
    if (!usageBar) return;

    const safePercent = Math.min(Math.max(Number(percent) || 0, 0), 100);
    usageBar.style.width = `${safePercent}%`;
}

function riskLevel(score) {
    const value = Number(score) || 0;
    if (value >= 70) return "high";
    if (value >= 30) return "medium";
    return "low";
}

function riskBadge(level) {
    const map = {
        low: { emoji: "🟢", label: "Low", cls: "risk-badge-low" },
        medium: { emoji: "🟡", label: "Medium", cls: "risk-badge-medium" },
        high: { emoji: "🔴", label: "High", cls: "risk-badge-high" },
    };

    return map[level] || map.low;
}

function clearRecentRequests() {
    const el = $("recent");
    if (el) el.innerHTML = "";
}

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

async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            ...(options.headers || {})
        }
    });

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
// DEVICE INTELLIGENCE MODULE & CHARTS
// =====================================================

let browserDistChart, platformDistChart, osDistChart, reputationTrendChart;

function initDeviceDistributionCharts() {
    const bCtx = $("browserDistChart");
    const pCtx = $("platformDistChart");
    const oCtx = $("osDistChart");
    const rCtx = $("reputationTrendChart");

    if (bCtx) {
        browserDistChart = new Chart(bCtx, {
            type: "doughnut",
            data: { labels: [], datasets: [{ data: [], backgroundColor: ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: chartTextColor(), boxWidth: 8 } } } }
        });
    }

    if (pCtx) {
        platformDistChart = new Chart(pCtx, {
            type: "doughnut",
            data: { labels: [], datasets: [{ data: [], backgroundColor: ["#6366f1", "#ec4899", "#14b8a6", "#f97316"], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: chartTextColor(), boxWidth: 8 } } } }
        });
    }

    if (oCtx) {
        osDistChart = new Chart(oCtx, {
            type: "doughnut",
            data: { labels: [], datasets: [{ data: [], backgroundColor: ["#06b6d4", "#84cc16", "#a855f7", "#e11d48"], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: chartTextColor(), boxWidth: 8 } } } }
        });
    }

    if (rCtx) {
        reputationTrendChart = new Chart(rCtx, {
            type: "line",
            data: {
                labels: ["T-6", "T-5", "T-4", "T-3", "T-2", "T-1", "Now"],
                datasets: [{
                    label: "Reputation Score",
                    data: [100, 100, 100, 100, 100, 100, 100],
                    borderColor: "#10b981",
                    backgroundColor: "rgba(16,185,129,0.1)",
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: chartTextColor() } },
                    y: { min: 0, max: 100, grid: { color: chartGridColor() }, ticks: { color: chartTextColor() } }
                }
            }
        });
    }
}

function updateDistributionCharts(devices) {
    const bMap = {}, pMap = {}, oMap = {};
    
    (devices || []).forEach(d => {
        const b = d.browser || "Unknown";
        const p = d.platform || "Unknown";
        const o = d.os || "Unknown";
        
        bMap[b] = (bMap[b] || 0) + 1;
        pMap[p] = (pMap[p] || 0) + 1;
        oMap[o] = (oMap[o] || 0) + 1;
    });

    if (browserDistChart) {
        browserDistChart.data.labels = Object.keys(bMap);
        browserDistChart.data.datasets[0].data = Object.values(bMap);
        browserDistChart.update();
    }

    if (platformDistChart) {
        platformDistChart.data.labels = Object.keys(pMap);
        platformDistChart.data.datasets[0].data = Object.values(pMap);
        platformDistChart.update();
    }

    if (osDistChart) {
        osDistChart.data.labels = Object.keys(oMap);
        osDistChart.data.datasets[0].data = Object.values(oMap);
        osDistChart.update();
    }

    // Update Activity Map UI
    const activityContainer = $("deviceActivityMapContainer");
    if (activityContainer) {
        const total = (devices && devices.length) || 1;
        if (!devices || !devices.length) {
            activityContainer.innerHTML = '<p class="text-xs text-slate-400 text-center py-8">No activity telemetry populated</p>';
        } else {
            activityContainer.innerHTML = Object.entries(bMap).map(([browser, count]) => {
                const pct = Math.round((count / total) * 100);
                return `
                    <div>
                        <div class="flex justify-between text-xs mb-1">
                            <span class="font-medium text-slate-700 dark:text-slate-300">${browser}</span>
                            <span class="font-bold text-slate-500">${pct}%</span>
                        </div>
                        <div class="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div class="bg-blue-500 h-2 rounded-full" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }
}

/**
 * Fetch and populate Device Intelligence UI components safely
 */
async function refreshDeviceIntelligence(userData) {
    try {
        const devIntel = (userData && userData.device_intelligence) || {};
        const summary = devIntel.summary || {};
        const currentDevice = devIntel.current_device || null;
        const devices = devIntel.known_devices || [];
        const timeline = devIntel.timeline || [];
        const health = devIntel.health || {};

        const hasDevices = devices.length > 0;
        const hasCurrentDevice = currentDevice && Object.keys(currentDevice).length > 0;

        // 1. SECTION 1: HERO CARDS
        const isHealthy = health.status === "HEALTHY" || (!hasDevices && (health.risk_level === "LOW" || !health.risk_level));
        setText("devHealthStatus", isHealthy ? "🟢 HEALTHY" : "🔴 ACTION REQUIRED");
        const statusEl = $("devHealthStatus");
        if (statusEl) {
            statusEl.className = isHealthy ? "text-xl font-bold mt-2 text-emerald-600 dark:text-emerald-400" : "text-xl font-bold mt-2 text-rose-600 dark:text-rose-400";
        }
        setText("devHealthRiskLevel", health.risk_level || "LOW");
        setText("devStatsTrustScore", summary.average_reputation ?? 100);
        setText("devStatsKnown", formatNumber(summary.total_devices ?? 0));
        setText("devStatsTrusted", formatNumber(summary.trusted_devices ?? 0));
        setText("devStatsBlocked", formatNumber(summary.blocked_devices ?? 0));

        // 2. STATS CARDS
        const uniqueBrowsers = new Set(devices.map(d => d.browser).filter(Boolean)).size;
        const uniquePlatforms = new Set(devices.map(d => d.platform).filter(Boolean)).size;
        const uniqueOS = new Set(devices.map(d => d.os).filter(Boolean)).size;

        setText("statUniqueBrowsers", uniqueBrowsers);
        setText("statUniquePlatforms", uniquePlatforms);
        setText("statUniqueOS", uniqueOS);

        let mostActive = "--";
        if (hasDevices) {
            const sortedByReq = [...devices].sort((a, b) => (b.request_count || 0) - (a.request_count || 0));
            if (sortedByReq[0]) mostActive = `${sortedByReq[0].browser || ""} ${sortedByReq[0].platform || ""}`.trim();
        }
        setText("statMostActiveDevice", mostActive || "--");

        let oldestTrusted = "--";
        if (hasDevices) {
            const trustedDevs = devices.filter(d => d.is_trusted);
            if (trustedDevs.length > 0) {
                const sortedByAge = trustedDevs.sort((a, b) => new Date(a.first_seen || 0) - new Date(b.first_seen || 0));
                const days = Math.floor((Date.now() - new Date(sortedByAge[0].first_seen).getTime()) / (1000 * 60 * 60 * 24));
                oldestTrusted = `${days} days`;
            }
        }
        setText("statOldestTrusted", oldestTrusted);

        // 3. SECTION 2: CURRENT DEVICE
        if (hasCurrentDevice) {
            setText("currDevBrowser", `${currentDevice.browser || "--"} ${currentDevice.browser_version || ""}`.trim());
            setText("currDevOS", `${currentDevice.os || "--"} ${currentDevice.os_version || ""}`.trim());
            setText("currDevPlatform", currentDevice.platform || "--");
            setText("currDevTimezone", currentDevice.timezone || "--");
            setText("currDevLanguage", currentDevice.language || "--");
            setText("currDevScreen", currentDevice.screen_resolution || "--");
            setText("currDevFirstSeen", formatDate(currentDevice.first_seen));
            setText("currDevLastSeen", formatDate(currentDevice.last_seen));
            setText("currDevRequests", formatNumber(currentDevice.request_count ?? 0));
            setText("currDevTrusted", currentDevice.is_trusted ? "YES" : "NO");
            setText("currDevBlocked", currentDevice.is_blocked ? "YES" : "NO");
            setText("currDevReputation", `Reputation: ${currentDevice.reputation_score ?? 100}`);

            const fpEl = $("currDevFingerprint");
            if (fpEl) {
                const rawFp = currentDevice.device_hash || "";
                fpEl.innerText = truncateFingerprint(rawFp);
                fpEl.title = rawFp;
            }
        } else {
            setText("currDevBrowser", "--");
            setText("currDevOS", "--");
            setText("currDevPlatform", "--");
            setText("currDevTimezone", "--");
            setText("currDevLanguage", "--");
            setText("currDevScreen", "--");
            setText("currDevFirstSeen", "--");
            setText("currDevLastSeen", "--");
            setText("currDevRequests", "0");
            setText("currDevTrusted", "--");
            setText("currDevBlocked", "--");
            setText("currDevReputation", "Reputation: --");
            const fpEl = $("currDevFingerprint");
            if (fpEl) { fpEl.innerText = "--"; fpEl.title = ""; }
        }

        // 4. SECTION 3: TRUST METER DISPLAY
        const trustedPct = health.trusted_percentage ?? (summary.device_trust_percentage ?? 0);
        const blockedPct = health.blocked_percentage ?? 0;
        const newPct = health.new_percentage ?? 0;

        if (!hasDevices) {
            setText("trustMeterValue", "No device data available");
            const tmVal = $("trustMeterValue");
            if (tmVal) tmVal.className = "text-sm font-semibold text-slate-400 dark:text-slate-500";
            setText("healthTrustedPct", "0%");
            setText("healthNewPct", "0%");
            setText("healthBlockedPct", "0%");
            if ($("healthTrustedBar")) $("healthTrustedBar").style.width = "0%";
            if ($("healthNewBar")) $("healthNewBar").style.width = "0%";
            if ($("healthBlockedBar")) $("healthBlockedBar").style.width = "0%";
        } else {
            const tmVal = $("trustMeterValue");
            if (tmVal) tmVal.className = "text-2xl font-extrabold text-blue-600 dark:text-blue-400";
            setText("trustMeterValue", `${trustedPct}%`);
            setText("healthTrustedPct", `${trustedPct}%`);
            setText("healthNewPct", `${newPct}%`);
            setText("healthBlockedPct", `${blockedPct}%`);
            if ($("healthTrustedBar")) $("healthTrustedBar").style.width = `${trustedPct}%`;
            if ($("healthNewBar")) $("healthNewBar").style.width = `${newPct}%`;
            if ($("healthBlockedBar")) $("healthBlockedBar").style.width = `${blockedPct}%`;
        }

        const avgRep = summary.average_reputation ?? 100;
        if ($("reputationGaugeBar")) $("reputationGaugeBar").style.width = `${hasDevices ? avgRep : 100}%`;
        setText("reputationGaugeLabel", avgRep >= 80 ? "Excellent" : avgRep >= 50 ? "Good" : "Poor");

        // 5. SECTION 4: KNOWN DEVICES TABLE
        const knownTable = $("knownDevicesTable");
        if (knownTable) {
            if (!devices.length) {
                knownTable.innerHTML = '<tr><td colspan="8" class="text-center py-6 text-slate-400 text-xs">No known devices recorded</td></tr>';
            } else {
                knownTable.innerHTML = devices.map(d => {
                    const isTrust = d.is_trusted;
                    const isBlock = d.is_blocked;
                    const statusText = isBlock ? "Blocked" : isTrust ? "Trusted" : "New";
                    const trustCls = isBlock 
                        ? "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400"
                        : isTrust
                        ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                        : "bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400";

                    return `
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                            <td class="px-4 py-3 font-medium">${d.browser || "--"} <span class="text-xs text-slate-400">${d.browser_version || ""}</span></td>
                            <td class="px-4 py-3 text-slate-600 dark:text-slate-400">${d.os || "--"}</td>
                            <td class="px-4 py-3 text-slate-600 dark:text-slate-400">${d.platform || "--"}</td>
                            <td class="px-4 py-3 text-center font-bold">${d.reputation_score ?? 100}</td>
                            <td class="px-4 py-3 text-center">${d.shared_users_count ?? 1}</td>
                            <td class="px-4 py-3 text-center">
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${trustCls}">${statusText}</span>
                            </td>
                            <td class="px-4 py-3 text-right font-semibold">${formatNumber(d.request_count ?? 0)}</td>
                            <td class="px-4 py-3 text-right text-xs text-slate-500 dark:text-slate-400">${formatDate(d.last_seen)}</td>
                        </tr>
                    `;
                }).join("");
            }
        }

        // 6. SECTION 5: TIMELINE
        const timelineTable = $("deviceTimelineTable");
        if (timelineTable) {
            if (!timeline.length) {
                timelineTable.innerHTML = '<tr><td colspan="3" class="text-center py-4 text-slate-400 text-xs">No timeline events recorded</td></tr>';
            } else {
                timelineTable.innerHTML = timeline.map(e => {
                    const statusCls = e.status === "Trusted"
                        ? "text-emerald-600 dark:text-emerald-400 font-semibold"
                        : e.status === "Blocked"
                        ? "text-rose-600 dark:text-rose-400 font-semibold"
                        : "text-blue-600 dark:text-blue-400 font-semibold";

                    return `
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                            <td class="px-4 py-2.5 text-xs text-slate-500 dark:text-slate-400">${formatDate(e.last_seen)}</td>
                            <td class="px-4 py-2.5 font-medium">${e.browser || "--"} on ${e.os || "--"} (${e.platform || "--"})</td>
                            <td class="px-4 py-2.5 text-right text-xs ${statusCls}">${e.status || "--"}</td>
                        </tr>
                    `;
                }).join("");
            }
        }

        // 7. SECTION 7: SHARED DEVICE DETECTION SAFEGUARD
        const maxShared = devices.length ? Math.max(...devices.map(d => d.shared_users_count || 1), 1) : 0;
        const sharedUsersEl = $("sharedUsersCount");
        const sharedBadge = $("sharedDeviceStatusBadge");

        if (!hasCurrentDevice) {
            if (sharedUsersEl) {
                sharedUsersEl.innerText = "— No active device";
                sharedUsersEl.className = "text-xl font-extrabold mt-1 text-slate-500";
            }
            if (sharedBadge) {
                sharedBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300";
                sharedBadge.innerText = "Safe";
            }
        } else {
            if (sharedUsersEl) {
                sharedUsersEl.innerText = maxShared;
                sharedUsersEl.className = "text-2xl font-extrabold mt-1";
            }
            if (sharedBadge) {
                if (maxShared >= 3) {
                    sharedBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
                    sharedBadge.innerText = "⚠ Shared Device";
                } else {
                    sharedBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300";
                    sharedBadge.innerText = "Safe";
                }
            }
        }

        // 8. SECURITY RECOMMENDATIONS
        const recContainer = $("securityRecommendations");
        if (recContainer) {
            let recs = [];
            if ((summary.blocked_devices || 0) === 0) recs.push('<p class="text-emerald-600 dark:text-emerald-400">✓ No blocked devices detected</p>');
            else recs.push(`<p class="text-rose-600 dark:text-rose-400">⚠ ${summary.blocked_devices} blocked device(s) on file</p>`);

            if (maxShared < 3) recs.push('<p class="text-emerald-600 dark:text-emerald-400">✓ No suspicious sharing detected</p>');
            else recs.push('<p class="text-amber-600 dark:text-amber-400">⚠ Device shared across multiple accounts</p>');

            if (isHealthy) recs.push('<p class="text-emerald-600 dark:text-emerald-400">✓ No immediate action required</p>');
            else recs.push('<p class="text-rose-600 dark:text-rose-400">⚠ System indicates required security action</p>');

            recContainer.innerHTML = recs.join("");
        }

        // 9. DISTRIBUTION CHARTS
        updateDistributionCharts(devices);

        // 10. RISK MATRIX TABLE
        const riskMatrixTable = $("deviceRiskMatrixTable");
        if (riskMatrixTable) {
            if (!devices.length) {
                riskMatrixTable.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-slate-400 text-xs">No risk matrix telemetry available</td></tr>';
            } else {
                riskMatrixTable.innerHTML = devices.map(d => {
                    const score = d.reputation_score ?? 100;
                    const rLevel = score < 60 ? "HIGH" : score < 80 ? "MEDIUM" : score < 95 ? "LOW" : "SAFE";
                    const rCls = rLevel === "SAFE" || rLevel === "LOW" ? "text-emerald-600 dark:text-emerald-400 font-bold" : rLevel === "MEDIUM" ? "text-amber-600 dark:text-amber-400 font-bold" : "text-rose-600 dark:text-rose-400 font-bold";

                    return `
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                            <td class="px-4 py-2 font-mono text-xs text-blue-600 dark:text-blue-400" title="${d.device_hash || ''}">${truncateFingerprint(d.device_hash)}</td>
                            <td class="px-4 py-2 font-medium">${d.browser || '--'} / ${d.os || '--'}</td>
                            <td class="px-4 py-2 text-center font-bold">${score}</td>
                            <td class="px-4 py-2 text-center ${rCls}">${rLevel}</td>
                            <td class="px-4 py-2 text-right font-semibold">${formatNumber(d.request_count ?? 0)}</td>
                            <td class="px-4 py-2 text-right">${d.shared_users_count ?? 1}</td>
                            <td class="px-4 py-2 text-center font-semibold ${d.is_blocked ? 'text-rose-600' : 'text-slate-400'}">${d.is_blocked ? 'YES' : 'NO'}</td>
                            <td class="px-4 py-2 text-right text-xs text-slate-500">${formatDate(d.last_seen)}</td>
                        </tr>
                    `;
                }).join("");
            }
        }

        // 11. FRAUD SIGNALS
        setText("signalShared", maxShared >= 3 ? "YES" : "NO");
        setText("signalBlocked", (summary.blocked_devices || 0) > 0 ? "YES" : "NO");
        setText("signalMultiBrowser", uniqueBrowsers > 1 ? "YES" : "NO");
        setText("signalMultiPlatform", uniquePlatforms > 1 ? "YES" : "NO");

    } catch (error) {
        console.warn("Error rendering Device Intelligence module UI:", error.message);
    }
}

// =====================================================
// UI BEHAVIOR — sidebar, dark mode, user menu, copy key,
// mini usage bar sync, table search/filter, charts, plan actions
// =====================================================

function toggleSidebar() {
    $("sidebar")?.classList.toggle("open");
    $("sidebarOverlay")?.classList.toggle("hidden");
}

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

const recentBody = $("recent");
if (recentBody) new MutationObserver(filterRequests).observe(recentBody, { childList: true });

// CHARTS (Chart.js)
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

    initDeviceDistributionCharts();
}

function refreshChartTheme() {
    [requestsChart, endpointChart, reputationTrendChart].forEach(chart => {
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
    [browserDistChart, platformDistChart, osDistChart].forEach(chart => {
        if (!chart) return;
        chart.options.plugins.legend.labels.color = chartTextColor();
        chart.update();
    });
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

function updateAnalyticsCharts(analytics) {
    const dailyUsage = analytics.daily_usage || [];
    window.updateRequestsChart(
        dailyUsage.map(d => d.date),
        dailyUsage.map(d => d.requests)
    );

    const endpointUsage = analytics.endpoint_breakdown || [];
    window.updateEndpointChart(
        endpointUsage.map(e => e.endpoint),
        endpointUsage.map(e => e.requests)
    );

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

    const dailyTable = $("dailyUsageTable");
    if (dailyTable) {
        dailyTable.innerHTML = dailyUsage.map(d => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2 font-medium text-slate-600 dark:text-slate-400">${d.date}</td>
                <td class="px-4 py-2 text-right font-semibold text-slate-800 dark:text-slate-200">${d.requests}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }

    const breakdownTable = $("endpointBreakdownTable");
    if (breakdownTable) {
        breakdownTable.innerHTML = endpointUsage.map(e => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2"><span class="px-1.5 py-0.5 rounded text-xs font-mono bg-slate-100 dark:bg-slate-800 text-blue-600">${e.endpoint}</span></td>
                <td class="px-4 py-2 text-right font-semibold text-slate-800 dark:text-slate-200">${e.requests}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }

    const riskTable = $("endpointRiskTable");
    if (riskTable) {
        const endpointAvgRisk = analytics.endpoint_average_risk || [];
        riskTable.innerHTML = endpointAvgRisk.map(r => `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                <td class="px-4 py-2 font-mono text-xs text-slate-600 dark:text-slate-400">${r.endpoint || '--'}</td>
                <td class="px-4 py-2 text-right font-bold text-red-500">${(r.average_risk ?? 0).toFixed(2)}</td>
            </tr>
        `).join('') || '<tr><td colspan="2" class="text-center py-4 text-slate-400 text-xs">No entries</td></tr>';
    }
}

function upgradeToPro(btn) {
    const status = $("billingStatus");
    if (status) status.innerText = "Directing to checkout section...";
    
    const checkoutEl = $("checkout");
    if (checkoutEl) {
        checkoutEl.scrollIntoView({ behavior: "smooth" });
        checkoutEl.classList.add("ring-2", "ring-blue-500");
        setTimeout(() => checkoutEl.classList.remove("ring-2", "ring-blue-500"), 2000);
    } else {
        window.location.hash = "checkout";
    }
}

function upgradeToEnterprise(btn) {
    const status = $("billingStatus");
    if (status) status.innerText = "Enterprise upgrade request submitted. Our team will reach out.";
}

function logout() {
    localStorage.removeItem("api_key");
    window.location.href = "login.html";
}

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
    try {
        setStatus("Syncing network telemetry...", "blue");
        
        const userData = await apiRequest("/user/me");
        const analyticsData = await apiRequest("/analytics/summary");

        // Top KPIs (from /user/me)
        setText("total", formatNumber(userData.total_requests ?? 0));
        setText("avg", (userData.average_risk_score ?? 0).toFixed(2));
        setText("plan", userData.plan_type || "FREE");
        setText("userPlanLabel", userData.plan_type || "PRO");
        setText("usagePercent", `${Math.round(userData.usage_percentage ?? 0)}%`);

        // Key Cards & API Details (from /user/me)
        const apiKeyEl = $("apiKey");
        if (apiKeyEl) {
            apiKeyEl.textContent = userData.api_key ? truncateFingerprint(userData.api_key) : "--";
            apiKeyEl.setAttribute("data-full", userData.api_key || "");
        }
        setText("apiKeyRotated", formatDate(userData.key_last_rotated));
        
        updateSubscriptionStatus(userData.subscription_status || "ACTIVE");
        setText("stripeStatus", userData.stripe_customer_id ? "Connected" : "Unlinked");
        setText("overageEnabled", userData.overage_enabled ? "YES" : "NO");
        setText("overageCharge", `$${(userData.overage_charge || 0).toFixed(2)}`);
        setText("checkoutOverage", `$${(userData.overage_charge || 0).toFixed(2)}`);

        // Usage Overview (from /user/me)
        setText("currentUsage", formatNumber(userData.total_requests ?? 0));
        setText("usageLimit", formatNumber(userData.request_limit ?? 0));
        setText("usagePercentDetail", `${Math.round(userData.usage_percentage ?? 0)}%`);
        setText("remainingUsage", `${formatNumber((userData.request_limit || 0) - (userData.total_requests || 0))} Remaining`);
        updateUsageBar(userData.usage_percentage || 0);

        // Billing Cycle (from /user/me)
        setText("billingStart", formatDate(userData.period_start));
        setText("billingEnd", formatDate(userData.period_end));
        setText("nextReset", formatDate(userData.period_end));
        setText("overageRequests", formatNumber(userData.overage_requests ?? 0));
        setText("overagePrice", `$${(userData.overage_price || 0).toFixed(4)}`);
        setText("planAllowsOverage", userData.plan_allows_overage ? "YES" : "NO");

        // Analytics KPIs (from /analytics/summary)
        setText("requestsToday", formatNumber(analyticsData.requests_today ?? 0));
        setText("requestsWeek", formatNumber(analyticsData.requests_this_week ?? 0));
        setText("mostUsedEndpoint", analyticsData.most_used_endpoint || "--");
        setText("endpointRisk", (analyticsData.most_used_endpoint_risk ?? 0).toFixed(2));
        setText("overagePercentCard", `${Math.round(userData.overage_percentage ?? 0)}%`);
        setText("overageRequestsCard", formatNumber(userData.overage_requests ?? 0));

        // Analytics Charts & Data Tables Population
        updateAnalyticsCharts(analyticsData);

        // Populate Device Intelligence Telemetry
        await refreshDeviceIntelligence(userData);

        // Render Recent Requests Table (from /analytics/summary)
        const recentTable = $("recent");
        if (recentTable) {
            const requests = analyticsData.recent_requests || [];
            if (!requests.length) {
                showNoRequests();
            } else {
                recentTable.innerHTML = requests.map(r => {
                    const level = riskLevel(r.risk_score);
                    const badge = riskBadge(level);
                    return `
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition" data-status="${r.is_overage ? 'overage' : 'normal'}" data-risk="${level}">
                            <td class="px-6 py-4 text-xs text-slate-500">${formatDate(r.timestamp)}</td>
                            <td class="px-6 py-4 font-mono text-xs text-blue-600 dark:text-blue-400">${r.endpoint || '--'}</td>
                            <td class="px-6 py-4 font-medium">${r.email || '--'}</td>
                            <td class="px-6 py-4 font-mono text-xs text-slate-500">${r.ip_address || '--'}</td>
                            <td class="px-6 py-4 text-center">
                                <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${badge.cls}">
                                    ${badge.emoji} ${(r.risk_score || 0).toFixed(1)}
                                </span>
                            </td>
                            <td class="px-6 py-4 text-center">
                                <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${r.is_overage ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}">
                                    ${r.is_overage ? 'Overage' : 'Normal'}
                                </span>
                            </td>
                        </tr>
                    `;
                }).join("");
            }
        }

        lastLoadTimestamp = Date.now();
        setStatus("Live", "green");

    } catch (err) {
        console.error("Dashboard Load Failure:", err);
        setStatus("Connection Failed", "red");
    }
}

// =====================================================
// INITIALIZATION
// =====================================================

document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    loadDashboard();
});