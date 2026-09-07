/**
 * Agentic AI Copilot - Omnipresent Floating Widget Script
 * Handles real-time communication with the Flask ReAct backend,
 * renders reasoning traces, tool executions, and interactive cards.
 */

document.addEventListener('DOMContentLoaded', () => {
    initFloatingCopilot();
});

function initFloatingCopilot() {
    const copilotBtn = document.getElementById('floating-copilot-btn');
    const copilotDrawer = document.getElementById('floating-copilot-drawer');
    const closeBtn = document.getElementById('copilot-close-btn');
    const chatForm = document.getElementById('copilot-chat-form');
    const inputField = document.getElementById('copilot-user-input');

    if (!copilotBtn || !copilotDrawer) return;

    copilotBtn.addEventListener('click', () => {
        copilotDrawer.classList.toggle('active');
        if (copilotDrawer.classList.contains('active')) {
            if (inputField) inputField.focus();
            const badge = document.getElementById('copilot-unread-badge');
            if (badge) badge.classList.add('d-none');
        }
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            copilotDrawer.classList.remove('active');
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const message = inputField.value.trim();
            if (!message) return;

            appendCopilotUserMsg(message);
            inputField.value = '';

            // Show Thinking Indicator
            const loadingId = appendCopilotThinking();

            try {
                const response = await fetch('/api/ai/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const data = await response.json();
                removeCopilotElement(loadingId);
                renderCopilotAgentMsg(data);
            } catch (err) {
                removeCopilotElement(loadingId);
                appendCopilotErrorMsg(err.message);
            }
        });
    }
}

function sendCopilotQuickPrompt(promptText) {
    const drawer = document.getElementById('floating-copilot-drawer');
    const inputField = document.getElementById('copilot-user-input');
    if (drawer && !drawer.classList.contains('active')) {
        drawer.classList.add('active');
    }
    if (inputField) {
        inputField.value = promptText;
        const form = document.getElementById('copilot-chat-form');
        if (form) form.dispatchEvent(new Event('submit'));
    }
}

function appendCopilotUserMsg(text) {
    const stream = document.getElementById('copilot-chat-stream');
    if (!stream) return;
    const msgEl = document.createElement('div');
    msgEl.className = 'copilot-msg user-msg mb-3';
    msgEl.innerHTML = `
        <div class="d-flex justify-content-end gap-2">
            <div class="copilot-bubble user-bubble bg-primary text-white p-2 px-3 rounded-4 small">
                ${escapeCopilotHtml(text)}
            </div>
            <div class="copilot-avatar user-avatar small rounded-circle bg-dark text-white d-flex align-items-center justify-content-center" style="width:28px;height:28px;">
                <i class="bi bi-person-fill"></i>
            </div>
        </div>
    `;
    stream.appendChild(msgEl);
    stream.scrollTop = stream.scrollHeight;
}

function appendCopilotThinking() {
    const stream = document.getElementById('copilot-chat-stream');
    if (!stream) return '';
    const id = 'copilot-think-' + Date.now();
    const thinkEl = document.createElement('div');
    thinkEl.id = id;
    thinkEl.className = 'copilot-msg agent-msg mb-3';
    thinkEl.innerHTML = `
        <div class="d-flex gap-2">
            <div class="copilot-avatar agent-avatar rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center" style="width:28px;height:28px;">
                <i class="bi bi-robot"></i>
            </div>
            <div class="copilot-bubble bg-light p-2 px-3 rounded-4 small border">
                <span class="spinner-grow spinner-grow-sm text-primary me-1" role="status"></span>
                <span class="text-secondary">Agent reasoning & executing tools...</span>
            </div>
        </div>
    `;
    stream.appendChild(thinkEl);
    stream.scrollTop = stream.scrollHeight;
    return id;
}

function removeCopilotElement(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function renderCopilotAgentMsg(data) {
    const stream = document.getElementById('copilot-chat-stream');
    if (!stream) return;

    const msgEl = document.createElement('div');
    msgEl.className = 'copilot-msg agent-msg mb-3';

    // Steps accordion
    let stepsHtml = '';
    if (data.steps && data.steps.length > 0) {
        const stepId = 'c-step-' + Date.now();
        const stepItems = data.steps.map(s => `
            <div class="p-1 px-2 mb-1 bg-white rounded border small">
                <span class="badge bg-primary-subtle text-primary">${s.action}</span>
                <div class="text-muted" style="font-size:0.75rem;">${escapeCopilotHtml(s.thought)}</div>
            </div>
        `).join('');

        stepsHtml = `
            <div class="mb-2">
                <button class="btn btn-sm btn-light border py-0 px-2 rounded-pill small w-100 text-start" 
                        type="button" data-bs-toggle="collapse" data-bs-target="#${stepId}" style="font-size:0.75rem;">
                    <i class="bi bi-cpu text-warning me-1"></i> Reasoning (${data.steps.length} steps)
                </button>
                <div class="collapse mt-1" id="${stepId}">
                    ${stepItems}
                </div>
            </div>
        `;
    }

    // Quick chips
    let chipsHtml = '';
    if (data.quick_replies && data.quick_replies.length > 0) {
        chipsHtml = `
            <div class="d-flex flex-wrap gap-1 mt-2">
                ${data.quick_replies.map(r => `
                    <button class="btn btn-sm btn-outline-secondary py-0 px-2 rounded-pill small" 
                            style="font-size:0.75rem;" 
                            onclick="sendCopilotQuickPrompt('${escapeCopilotHtml(r)}')">
                        ${escapeCopilotHtml(r)}
                    </button>
                `).join('')}
            </div>
        `;
    }

    // Render Rich Cards if present
    let cardsHtml = '';
    if (data.cards && data.cards.length > 0) {
        cardsHtml = renderCardsHtml(data.cards);
    }

    const formattedAnswer = formatCopilotMarkdown(data.answer);

    msgEl.innerHTML = `
        <div class="d-flex gap-2">
            <div class="copilot-avatar agent-avatar rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center" style="width:28px;height:28px;flex-shrink:0;">
                <i class="bi bi-robot"></i>
            </div>
            <div class="copilot-bubble bg-light p-2 px-3 rounded-4 small border flex-grow-1" style="max-width: 88%;">
                ${stepsHtml}
                ${cardsHtml}
                <div class="copilot-text mt-1" style="font-size: 0.85rem; line-height: 1.45;">
                    ${formattedAnswer}
                </div>
                ${chipsHtml}
            </div>
        </div>
    `;

    stream.appendChild(msgEl);
    stream.scrollTop = stream.scrollHeight;
}

function renderCardsHtml(cards) {
    if (!cards || !cards.length) return '';
    return cards.map(c => {
        if (c.type === 'affordability') {
            const d = c.data;
            const ev = d.evaluation;
            const ratio = ev ? ev.rent_to_income_ratio : 30;
            const vClass = ev ? (ev.verdict_class || 'primary') : 'primary';
            const verdict = ev ? ev.verdict : 'Budget Estimate';
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="badge bg-${vClass}-subtle text-${vClass} fw-bold" style="font-size:0.75rem;">
                            <i class="bi bi-shield-check me-1"></i>${verdict}
                        </span>
                        <span class="text-muted" style="font-size:0.75rem;">Safe Ceiling: <strong>₹${Math.round(d.safe_rent_ceiling).toLocaleString()}</strong></span>
                    </div>
                    <div class="progress mb-2" style="height: 6px;">
                        <div class="progress-bar bg-${vClass}" style="width: ${Math.min(100, ratio)}%"></div>
                    </div>
                    ${ev ? `
                        <div class="row g-1 text-center text-secondary mb-1" style="font-size:0.75rem;">
                            <div class="col-6 bg-light p-1 rounded">
                                <span class="d-block text-muted">Upfront Capital</span>
                                <strong class="text-dark">₹${Math.round(ev.upfront_capital_required.total_upfront).toLocaleString()}</strong>
                            </div>
                            <div class="col-6 bg-light p-1 rounded">
                                <span class="d-block text-muted">Monthly Leftover</span>
                                <strong class="text-dark">₹${Math.round(ev.disposable_after_rent).toLocaleString()}</strong>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        } else if (c.type === 'neighborhood') {
            const n = c.data;
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="text-primary" style="font-size:0.85rem;"><i class="bi bi-geo-alt-fill text-danger me-1"></i>${n.name}</strong>
                        <span class="badge bg-success-subtle text-success" style="font-size:0.75rem;">
                            Safety: ${n.safety_rating}/10
                        </span>
                    </div>
                    <div class="text-muted mb-1" style="font-size:0.75rem;">
                        <i class="bi bi-train-front me-1"></i><strong>Transit:</strong> ${n.nearest_metro || n.transit_rating + '/10'}
                    </div>
                    <div class="text-secondary small" style="font-size:0.75rem;">
                        <i class="bi bi-star-fill text-warning me-1"></i><strong>Livability Index:</strong> ${n.livability_index}/10
                    </div>
                </div>
            `;
        } else if (c.type === 'visit_booking') {
            const v = c.data;
            const h = v.house || {};
            const a = v.appointment || {};
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white border-start border-4 border-primary">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="badge bg-primary text-white" style="font-size:0.75rem;">
                            <i class="bi bi-ticket-perforated me-1"></i>${v.ticket_code}
                        </span>
                        <span class="text-success small fw-bold" style="font-size:0.75rem;">Confirmed Slot</span>
                    </div>
                    <div class="fw-bold text-dark" style="font-size:0.85rem;">${h.title || 'Rental Listing'}</div>
                    <div class="text-muted mb-2" style="font-size:0.75rem;"><i class="bi bi-clock me-1"></i>${a.time_slot}</div>
                    <div class="d-flex gap-2">
                        <a href="tel:${h.owner_phone || ''}" class="btn btn-sm btn-outline-success py-0 px-2 rounded-pill" style="font-size:0.75rem;">
                            <i class="bi bi-telephone-fill me-1"></i>Call Landlord
                        </a>
                        <a href="/houses/${h.id || 1}" class="btn btn-sm btn-outline-primary py-0 px-2 rounded-pill" style="font-size:0.75rem;">
                            View Property
                        </a>
                    </div>
                </div>
            `;
        } else if (c.type === 'lease_checklist') {
            const l = c.data;
            const terms = l.lease_terms || {};
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="text-dark" style="font-size:0.85rem;"><i class="bi bi-file-earmark-ruled-fill text-primary me-1"></i>11-Month Lease Checklist</strong>
                        <span class="badge bg-info-subtle text-info-emphasis" style="font-size:0.72rem;">${l.clauses ? l.clauses.length : 8} Clauses</span>
                    </div>
                    <div class="text-muted mb-1" style="font-size:0.75rem;">
                        Rent: <strong>₹${Math.round(terms.monthly_rent || 0).toLocaleString()}/mo</strong> &bull; Deposit: <strong>₹${Math.round(terms.security_deposit || 0).toLocaleString()}</strong>
                    </div>
                    <div class="p-1 bg-light rounded text-secondary" style="font-size:0.72rem;">
                        <i class="bi bi-shield-check text-success me-1"></i>${terms.recommended_stamp_paper || 'e-Stamp Paper'}
                    </div>
                </div>
            `;
        } else if (c.type === 'comparison') {
            const comp = c.data;
            const props = comp.properties || [];
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="text-dark" style="font-size:0.85rem;"><i class="bi bi-arrow-left-right text-primary me-1"></i>Comparison (${props.length} homes)</strong>
                        <span class="badge bg-success-subtle text-success" style="font-size:0.72rem;">Benchmarked</span>
                    </div>
                    <div class="list-group list-group-flush" style="font-size:0.75rem;">
                        ${props.map(p => `
                            <div class="list-group-item px-1 py-1 d-flex justify-content-between align-items-center">
                                <span class="text-truncate" style="max-width: 140px;">#${p.id} ${p.title}</span>
                                <span class="fw-bold text-primary">₹${Math.round(p.rent).toLocaleString()}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        } else if (c.type === 'valuation') {
            const val = c.data;
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <strong class="text-dark" style="font-size:0.85rem;"><i class="bi bi-graph-up text-success me-1"></i>Valuation: ${val.location}</strong>
                        <span class="badge bg-success-subtle text-success" style="font-size:0.72rem;">${val.market_demand} Demand</span>
                    </div>
                    <div class="h6 mb-1 text-primary fw-bold">₹${Math.round(val.estimated_rent).toLocaleString()} <span class="small text-muted fw-normal">/ month</span></div>
                    <div class="text-muted" style="font-size:0.72rem;">Target Range: ${val.recommended_rent_range} &bull; Conf: ${val.confidence_score}%</div>
                </div>
            `;
        } else if (c.type === 'platform_stats') {
            const st = c.data;
            return `
                <div class="card border-0 shadow-sm rounded-3 mb-2 p-2 bg-white">
                    <strong class="text-dark d-block mb-1" style="font-size:0.85rem;"><i class="bi bi-pie-chart-fill text-primary me-1"></i>Platform Intelligence</strong>
                    <div class="row g-1 text-center" style="font-size:0.75rem;">
                        <div class="col-4 bg-light p-1 rounded">
                            <span class="text-muted d-block">Listings</span>
                            <strong class="text-dark">${st.total_houses}</strong>
                        </div>
                        <div class="col-4 bg-light p-1 rounded">
                            <span class="text-muted d-block">Available</span>
                            <strong class="text-success">${st.available_houses}</strong>
                        </div>
                        <div class="col-4 bg-light p-1 rounded">
                            <span class="text-muted d-block">Avg Rent</span>
                            <strong class="text-primary">₹${Math.round(st.avg_rent).toLocaleString()}</strong>
                        </div>
                    </div>
                </div>
            `;
        } else if (c.type === 'property_list') {
            const items = c.items || [];
            return `
                <div class="mb-2">
                    <div class="d-flex flex-wrap gap-1">
                        ${items.map(p => `
                            <a href="/houses/${p.id}" class="badge bg-white text-dark border text-decoration-none p-1 px-2 rounded-pill hover-shadow-sm" style="font-size:0.75rem;">
                                🏡 #${p.id} ${p.title.substring(0, 18)}... <span class="text-primary fw-bold">₹${Math.round(p.rent).toLocaleString()}</span>
                            </a>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        return '';
    }).join('');
}

function appendCopilotErrorMsg(errorText) {
    const stream = document.getElementById('copilot-chat-stream');
    if (!stream) return;
    const msgEl = document.createElement('div');
    msgEl.className = 'copilot-msg agent-msg mb-3';
    msgEl.innerHTML = `
        <div class="d-flex gap-2">
            <div class="copilot-avatar text-danger rounded-circle bg-danger-subtle d-flex align-items-center justify-content-center" style="width:28px;height:28px;">
                <i class="bi bi-exclamation-circle"></i>
            </div>
            <div class="copilot-bubble bg-danger-subtle text-danger p-2 px-3 rounded-4 small border border-danger">
                Error: ${escapeCopilotHtml(errorText)}
            </div>
        </div>
    `;
    stream.appendChild(msgEl);
    stream.scrollTop = stream.scrollHeight;
}

function escapeCopilotHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function formatCopilotMarkdown(text) {
    if (!text) return '';
    let html = escapeCopilotHtml(text);
    html = html.replace(/### (.*?)\n/g, '<strong class="d-block text-primary mb-1">$1</strong>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/```text\n([\s\S]*?)```/g, '<div class="p-2 my-1 bg-white border rounded font-monospace small" style="white-space: pre-wrap; font-size:0.75rem;">$1</div>');
    html = html.replace(/^- (.*?)$/gm, '<li class="mb-0.5">$1</li>');
    html = html.replace(/(<li.*<\/li>)/s, '<ul class="ps-3 mb-1" style="font-size:0.8rem;">$1</ul>');
    html = html.replace(/\[(.*?)\]\(file:\/\/\/houses\/(\d+)\)/g, '<a href="/houses/$2" class="fw-semibold text-primary text-decoration-none">$1 &nearr;</a>');
    html = html.replace(/\n\n/g, '<br>');
    return html;
}
