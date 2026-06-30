// =====================================================
// RISK API DASHBOARD
// dashboard.js
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
// HELPER FUNCTIONS
// ==============================

/**
 * Get an element by ID.
 */
function $(id) {

    return document.getElementById(id);

}

/**
 * Update the dashboard status message.
 */
function setStatus(message, color = "gray") {

    const status = $("status");

    status.className =
        `mb-4 font-semibold text-${color}-600`;

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
 * Safely update text content.
 */
function setText(id, value) {

    $(id).innerText = value;

}

/**
 * Update the subscription status color.
 */
function updateSubscriptionStatus(status) {

    const element = $("subStatus");

    element.innerText = status;

    switch (status) {

        case "ACTIVE":

            element.className =
                "font-semibold text-green-600";
            break;

        case "TRIALING":

            element.className =
                "font-semibold text-blue-600";
            break;

        case "PAST_DUE":

            element.className =
                "font-semibold text-yellow-600";
            break;

        default:

            element.className =
                "font-semibold text-red-600";

    }

}

/**
 * Update the usage progress bar.
 */
function updateUsageBar(percent) {

    const usageBar = $("usageBar");

    const safePercent = Math.min(
        Math.max(percent, 0),
        100
    );

    usageBar.style.width = `${safePercent}%`;

    usageBar.innerText = `${safePercent}%`;

}

/**
 * Clear recent requests list.
 */
function clearRecentRequests() {

    $("recent").innerHTML = "";

}

/**
 * Show "No requests" placeholder.
 */
function showNoRequests() {

    $("recent").innerHTML =
        "<li class='text-gray-500'>No requests yet</li>";

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

        let message =
            `Request failed (${response.status})`;

        try {

            const error =
                await response.json();

            if (error.detail) {

                message = error.detail;

            }

        } catch (_) {}

        throw new Error(message);

    }

    return response.json();

    

}

// ==============================
// LOAD DASHBOARD
// ==============================

async function loadDashboard() {

    setStatus(
        "Loading dashboard...",
        "blue"
    );

    try {

        // ==============================
        // USER INFO (UPDATED FOR PHASE 2)
        // ==============================

        const user = await apiRequest(
            "/user/me"
        );

        setText(
            "apiKey",
            user.api_key || "No API key returned"
        );

        // 🧠 NEW: PLAN INFO (DAY 1 PHASE 2)

        setText(
            "plan",
            user.plan || "FREE"
        );

        updateSubscriptionStatus(
            user.subscription?.status ||
            "NO SUBSCRIPTION"
        );

        setText(
            "stripeStatus",
            user.stripe_customer_id
                ? "LINKED"
                : "NOT LINKED"
        );

                // ==============================
        // 🧠 DAY 4 PHASE 2
        // METERED BILLING
        // ==============================

        const usage = user.usage || {};

        const currentUsage =
            usage.current ?? 0;

        const usageLimit =
            usage.limit ?? 0;

        const remainingUsage =
            usage.remaining ?? 0;

        const usagePercent =
            usage.percent_used ?? 0;

        setText(
            "currentUsage",
            currentUsage
        );

        setText(
            "usageLimit",
            usageLimit
        );

        setText(
            "remainingUsage",
            remainingUsage
        );

        setText(
            "usagePercent",
            `${usagePercent}%`
        );

        updateUsageBar(usagePercent);

        // ==============================
        // 🧠 DAY 5 PHASE 2
        // BILLING CYCLE
        // ==============================

        const billingCycle =
            user.billing_cycle || {};

        const billingStart =
            billingCycle.current_period?.start
                ? formatDate(
                    billingCycle.current_period.start
                )
                : "--";

        const billingEnd =
            billingCycle.current_period?.end
                ? formatDate(
                    billingCycle.current_period.end
                )
                : "--";

        const nextReset =
            billingCycle.next_reset
                ? formatDate(
                    billingCycle.next_reset
                )
                : "--";

        setText(
            "billingStart",
            billingStart
        );

        setText(
            "billingEnd",
            billingEnd
        );

        setText(
            "nextReset",
            nextReset
        );

        // ==============================
        // USAGE
        // ==============================

        const usageStats =
            await apiRequest("/admin/usage");

        setText(
            "total",
            usageStats.total_requests ?? 0
        );

        setText(
            "avg",
            usageStats.average_risk_score?.toFixed(2) ??
            "0.00"
        );

        // ==============================
        // RECENT REQUESTS
        // ==============================

        const list = $("recent");

        clearRecentRequests();

        if (!usageStats.recent_requests?.length) {

            showNoRequests();

        } else {

            usageStats.recent_requests.forEach(r => {

                const item =
                    document.createElement("li");

                item.className =
                    "border p-2 rounded bg-gray-50";

                item.innerHTML = `
<div class="font-semibold">
${r.email || "N/A"}
</div>

<div class="text-sm text-gray-500">
IP:
${r.ip || "N/A"}
</div>

<div class="text-red-600 font-bold">
Risk Score:
${r.risk_score}
</div>
`;

                list.appendChild(item);

            });

        }

        setStatus(
            "✅ Dashboard loaded successfully",
            "green"
        );

    } catch (error) {

        console.error(error);

        setStatus(
            `❌ ${error.message}`,
            "red"
        );

    }

}



// ==============================
// AUTO REFRESH
// ==============================

loadDashboard();

setInterval(
    loadDashboard,
    30000
);


// ==============================
// BILLING ACTIONS
// ==============================

async function upgradeToPro(button) {

    const statusEl = $("billingStatus");

    const originalText = button.innerText;

    button.disabled = true;
    button.innerText = "Processing...";

    try {

        const data = await apiRequest(
            "/billing/checkout/pro",
            {
                method: "POST"
            }
        );

           statusEl.innerText =
    "Redirecting to Stripe...";

        window.location.href = data.checkout_url;

    } catch (error) {

        statusEl.innerText = error.message;

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

        const data = await apiRequest(
            "/billing/checkout/enterprise",
            {
                method: "POST"
            }
        );

        statusEl.innerText =
    "Redirecting to Stripe...";

        window.location.href = data.checkout_url;

    } catch (error) {

        statusEl.innerText = error.message;

    } finally {

        button.disabled = false;
        button.innerText = originalText;

    }

}


// ==============================
// REMAINING HELPER FUNCTIONS
// ==============================





        

