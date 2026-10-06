// Dynamic API URL: Empty string for same-origin (port 8000), or fallback to host:8000
const API_URL = (window.location.protocol.startsWith('http') && window.location.port === '8000')
    ? ''
    : (window.location.protocol.startsWith('http') && window.location.hostname
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : 'http://127.0.0.1:8000');

// Defensive fallback for translation helper t() and applyLanguageToDOM()
if (typeof window.t !== 'function') {
    window.t = function(key) {
        if (typeof TRANSLATIONS !== 'undefined' && typeof currentLang !== 'undefined' && TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) {
            return TRANSLATIONS[currentLang][key];
        }
        if (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS['en'] && TRANSLATIONS['en'][key]) {
            return TRANSLATIONS['en'][key];
        }
        const FALLBACKS = {
            senderBot: 'FinChat Assistant',
            senderYou: 'You',
            welcomeMessage: 'Hello! I am your AI banking assistant. You can ask me about account balances, recent transactions, spending insights, loans, EMI, or transfer money with OTP verification. I speak English, Kannada (ಕನ್ನಡ) & Hindi (हिंदी)!',
            welcomeGuest: 'Welcome, Guest',
            demoPinHint: 'Demo PIN:',
            errPin: 'Please enter security PIN',
            errInvalidPin: 'Invalid PIN or Customer ID',
            errBackend: 'Error connecting to backend server. Make sure FastAPI is running on port 8000.',
            errServer: 'Sorry, I am having trouble connecting to the banking server.',
            errConnection: 'Connection error. Please ensure the backend server is running on port 8000.',
            errOtp: 'Please enter OTP',
            conversationRestored: '● Conversation restored',
            newConversationStarted: '● New conversation started',
            errNewConvo: 'Unable to start a new conversation',
            bankName: 'FinChat Bank',
            balanceLabel: 'Available Balance',
            recentActivity: 'Recent Activity',
            monthlySpending: 'Monthly Spending',
            principalLabel: 'Principal',
            outstandingLabel: 'Outstanding',
            monthlyEmiLabel: 'Monthly EMI',
            nextDueLabel: 'Next Due Date',
            emiSummary: 'Loan EMI Summary',
            loanAmtLabel: 'Loan Amount',
            totalInterest: 'Total Interest',
            totalRepayment: 'Total Repayment',
            transferSuccess: 'Transfer Completed Successfully',
            remainingBal: 'Remaining Balance:',
            savingsTitle: 'FinChat Growth & Savings Options',
            savingsAccountName: 'Savings Account',
            savingsAccountSub: 'Daily liquidity, 24/7 access',
            fdName: 'Fixed Deposit (FD)',
            fdSub: 'Guaranteed returns (1 to 5 yrs)',
            rdName: 'Recurring Deposit (RD)',
            rdSub: 'Disciplined monthly savings',
            savingsTip: '💡 Tip: Keep a 3-6 month emergency fund in your Savings Account, then lock surplus into FDs!',
            connectHuman: 'Would you like to speak directly with a customer support officer?',
            connectHumanBtn: 'Connect to Human Agent',
            connectedDemo: 'Forwarded to Agent (Demo: Connected)',
            modalTitleTransfer: 'Authorize Fund Transfer',
            modalSubtitleTransfer: 'A simulated OTP has been generated for security',
            modalTitleVerify: 'Security Verification (2FA)',
            modalSubtitleVerify: 'Enter OTP to view your personal financial details',
            modalRecipientLabel: 'Recipient:',
            modalAmountLabel: 'Transfer Amount:',
            modalAccessLabel: 'Access Request:',
            modalSecurityLabel: 'Security Level:',
            modalConfidential: 'Confidential 🔒',
            modalAccessInfo: 'Account Information',
            modalVerifyTransfer: 'Verify & Transfer',
            modalVerifyView: 'Verify & View',
            modalCancel: 'Cancel',
            demoOtpText: 'Demo OTP:',
            enterOtpLabel: 'Enter 6-Digit OTP',
            suggestionsGuest: ['Where can I save my money?', 'What is the home loan interest rate?', 'How does a personal loan work?', 'Calculate EMI for ₹5 lakh loan'],
            suggestionsAuth: ['What is my balance?', 'Show my recent transactions', 'Where am I spending most?', 'Transfer ₹2,000 to Rahul', 'Check my loan details']
        };
        return FALLBACKS[key] || key;
    };
}
if (typeof window.applyLanguageToDOM !== 'function') {
    window.applyLanguageToDOM = function() {};
}

// Apply saved language preference as soon as the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (typeof applyLanguageToDOM === 'function') {
        applyLanguageToDOM();
    }
});

let currentUser = { mode: 'guest', name: 'Guest' };
let pendingTransferData = null;
let isSending = false;

// Demo customer PIN map for convenience
const PIN_MAP = {
    'CUST001': '1234',
    'CUST002': '5678',
    'CUST003': '2468',
    'CUST004': '4321',
    'CUST005': '9876'
};

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const customerSelect = document.getElementById('customer-select');
const pinContainer = document.getElementById('pin-container');
const pinInput = document.getElementById('pin-input');
const pinHint = document.getElementById('pin-hint');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const newConversationBtn = document.getElementById('new-conversation-btn');
const userGreeting = document.getElementById('user-greeting');
const conversationStatus = document.getElementById('conversation-status');
const headerBalanceBadge = document.getElementById('header-balance-badge');
const chatContainer = document.getElementById('chat-container');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const suggestedQueriesContainer = document.getElementById('suggested-queries');

// OTP Modal Elements
const otpModal = document.getElementById('otp-modal');
const modalRecipient = document.getElementById('modal-recipient');
const modalAmount = document.getElementById('modal-amount');
const otpCodeInput = document.getElementById('otp-code-input');
const modalVerifyBtn = document.getElementById('modal-verify-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');

// ── Send message on button click ──────────────────────────────
sendBtn.addEventListener('click', () => sendMessage());

// ── Send message on Enter key (Shift+Enter = new line) ────────
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});


// Setup Login Screen PIN selector
customerSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val === 'guest') {
        pinContainer.style.display = 'none';
    } else {
        pinContainer.style.display = 'flex';
        const expectedPin = PIN_MAP[val] || '1234';
        pinInput.value = '';
        pinHint.textContent = `${t('demoPinHint')} ${expectedPin}`;
    }
});

// Login button handler
loginBtn.addEventListener('click', async () => {
    const customerId = customerSelect.value;
    
    if (customerId === 'guest') {
        currentUser = { mode: 'guest', name: 'Guest' };
        initChat();
    } else {
        const pin = pinInput.value.trim();
        if (!pin) {
            alert(t('errPin'));
            return;
        }
        
        try {
            const response = await fetch(`${API_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ customer_id: customerId, pin: pin })
            });
            
            if (response.ok) {
                const data = await response.json();
                currentUser = { mode: 'auth', ...data.customer };
                initChat();
            } else {
                alert(t('errInvalidPin'));
            }
        } catch (error) {
            console.error('Login error:', error);
            alert(t('errBackend'));
        }
    }
});

// Logout handler
logoutBtn.addEventListener('click', () => {
    currentUser = { mode: 'guest', name: 'Guest' };
    renderWelcomeMessage();
    setConversationStatus('');
    pinInput.value = '';
    customerSelect.value = 'CUST001';
    pinContainer.style.display = 'flex';
    pinHint.textContent = `${t('demoPinHint')} 1234`;
    headerBalanceBadge.style.display = 'none';
    
    chatScreen.classList.remove('active');
    loginScreen.classList.add('active');
});

// Initialize Chat Screen
async function initChat() {
    loginScreen.classList.remove('active');
    chatScreen.classList.add('active');
    headerBalanceBadge.style.display = 'none';

    // Show welcome message immediately so chat doesn't look blank
    renderWelcomeMessage();

    // Disable input while loading history
    chatInput.disabled = true;
    sendBtn.disabled = true;

    if (currentUser.mode === 'guest') {
        userGreeting.textContent = t('welcomeGuest');
        populateSuggestions(t('suggestionsGuest'));
    } else {
        userGreeting.textContent = `${currentUser.name} (${currentUser.customer_id})`;
        populateSuggestions(t('suggestionsAuth'));
    }

    // Always re-enable input regardless of backend state
    try {
        await restoreConversation();
    } catch (e) {
        console.warn('restoreConversation failed:', e);
    } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

function renderWelcomeMessage() {
    chatContainer.innerHTML = '';
    addMessage(t('welcomeMessage'), 'bot');
}

function setConversationStatus(message) {
    conversationStatus.textContent = message;
    conversationStatus.style.display = message ? 'inline-flex' : 'none';
}

async function restoreConversation() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);
        const response = await fetch(`${API_URL}/conversation/history`, {
            credentials: 'include',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        if (!response.ok) return;

        const data = await response.json();
        if (!Array.isArray(data.messages) || data.messages.length === 0) {
            setConversationStatus('');
            return;
        }

        chatContainer.innerHTML = '';
        data.messages.forEach((message) => {
            addMessage(message.content, message.role === 'assistant' ? 'bot' : 'user');
        });
        setConversationStatus(t('conversationRestored'));
    } catch (error) {
        console.warn('Unable to restore conversation history:', error);
    }
}

newConversationBtn.addEventListener('click', async () => {
    newConversationBtn.disabled = true;
    try {
        const response = await fetch(`${API_URL}/conversation/new`, {
            method: 'POST',
            credentials: 'include'
        });
        if (!response.ok) throw new Error('Unable to start a new conversation');

        renderWelcomeMessage();
        setConversationStatus(t('newConversationStarted'));
    } catch (error) {
        console.error('New conversation error:', error);
        setConversationStatus(t('errNewConvo'));
    } finally {
        newConversationBtn.disabled = false;
    }
});

function updateHeaderBalance(amount) {
    headerBalanceBadge.style.display = 'inline-block';
    headerBalanceBadge.textContent = `Bal: ₹${Number(amount).toLocaleString('en-IN')}`;
    if (currentUser) {
        currentUser.balance = amount;
    }
}

function populateSuggestions(suggestions) {
    suggestedQueriesContainer.innerHTML = '';
    suggestions.forEach(query => {
        const chip = document.createElement('div');
        chip.className = 'suggestion-chip';
        chip.textContent = query;
        chip.addEventListener('click', () => {
            chatInput.value = query;
            sendMessage();
        });
        suggestedQueriesContainer.appendChild(chip);
    });
}

// Send Message Flow
async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || isSending) return;
    
    isSending = true;
    sendBtn.disabled = true;
    chatInput.value = '';
    
    // 1. Add user message to UI
    addMessage(text, 'user');
    
    // 2. Add animated loading bot bubble
    const loadingId = addLoadingIndicator();
    
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                text: text,
                customer_id: (currentUser && currentUser.mode === 'auth') ? currentUser.customer_id : null
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            // Replace loading bubble with bot response
            updateMessageWithData(loadingId, data.response, data.intent, data.data);
        } else {
            const errData = await response.json().catch(() => null);
            const errMsg = (errData && errData.detail) ? errData.detail : t('errServer');
            updateMessageText(loadingId, errMsg);
        }
    } catch (error) {
        console.error('Chat error:', error);
        updateMessageText(loadingId, t('errConnection'));
    } finally {
        isSending = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

let messageCounter = 0;
function getUniqueMessageId(prefix = 'msg') {
    messageCounter++;
    return `${prefix}-${Date.now()}-${messageCounter}`;
}

// Add user or bot message
function addMessage(text, sender) {
    const messageId = getUniqueMessageId(`msg-${sender}`);
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    msgDiv.id = messageId;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    const senderLabel = document.createElement('div');
    senderLabel.className = 'message-sender';
    senderLabel.textContent = (sender === 'bot') ? t('senderBot') : t('senderYou');
    bubble.appendChild(senderLabel);
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.textContent = text;
    bubble.appendChild(content);
    
    msgDiv.appendChild(bubble);
    chatContainer.appendChild(msgDiv);
    scrollChatToBottom();
    
    return messageId;
}

function addLoadingIndicator() {
    const messageId = getUniqueMessageId('msg-bot-loading');
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';
    msgDiv.id = messageId;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    const senderLabel = document.createElement('div');
    senderLabel.className = 'message-sender';
    senderLabel.textContent = t('senderBot');
    bubble.appendChild(senderLabel);
    
    const dotsDiv = document.createElement('div');
    dotsDiv.className = 'typing-dots';
    dotsDiv.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    bubble.appendChild(dotsDiv);
    
    msgDiv.appendChild(bubble);
    chatContainer.appendChild(msgDiv);
    scrollChatToBottom();
    
    return messageId;
}

function formatBotMarkdown(text) {
    if (!text) return '';
    const tempDiv = document.createElement('div');
    tempDiv.textContent = text;
    let safe = tempDiv.innerHTML;
    safe = safe.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/\*(.*?)\*/g, '<em>$1</em>');
    return safe;
}

function updateMessageText(messageId, text) {
    const msgDiv = document.getElementById(messageId);
    if (!msgDiv) return;
    const bubble = msgDiv.querySelector('.message-bubble');
    // Clear typing dots
    const dots = bubble.querySelector('.typing-dots');
    if (dots) dots.remove();
    
    let content = bubble.querySelector('.message-content');
    if (!content) {
        content = document.createElement('div');
        content.className = 'message-content';
        bubble.appendChild(content);
    }
    content.innerHTML = formatBotMarkdown(text);
    scrollChatToBottom();
}

function updateMessageWithData(messageId, text, intent, data) {
    updateMessageText(messageId, text);
    const msgDiv = document.getElementById(messageId);
    if (!msgDiv || !data) return;
    
    const bubble = msgDiv.querySelector('.message-bubble');
    
    // Visual Card Rendering based on intent & returned data
    if (data.action_required === 'otp_verification') {
        const scope = data.scope || 'fund_transfer';
        openOtpModal(data.recipient || 'Account Details', data.amount || 0, data.demo_otp || '123456', scope);
    } else if (intent === 'balance_enquiry' && data.balance !== undefined) {
        renderBalanceCard(bubble, data.balance);
        updateHeaderBalance(data.balance);
    } else if (intent === 'transaction_history' && Array.isArray(data.transactions)) {
        renderTransactionsCard(bubble, data.transactions);
    } else if (intent === 'spending_analysis' && data.categories) {
        renderSpendingCard(bubble, data);
    } else if (intent === 'loan_information' && Array.isArray(data.loans) && data.loans.length > 0) {
        renderLoanCard(bubble, data.loans);
    } else if (intent === 'emi_calculation' && data.emi) {
        renderEmiCard(bubble, data.emi);
    } else if (intent === 'fund_transfer') {
        if (data.success) {
            renderTransferSuccessCard(bubble, data);
            if (data.remaining_balance !== undefined) {
                updateHeaderBalance(data.remaining_balance);
            }
        }
    } else if ((intent === 'financial_advice' || intent === 'savings_guidance') && data.savings_rates) {
        renderSavingsCard(bubble, data);
    } else if (data.action === 'connect_human' || data.action === 'suggest_human' || intent === 'human_agent') {
        renderHumanAgentCard(bubble);
    }
    
    scrollChatToBottom();
}

/* ==================== RICH COMPONENT RENDERERS ==================== */

// 1. Balance Card Component
function renderBalanceCard(container, balance) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    const accNum = currentUser && currentUser.account_number ? currentUser.account_number : 'XXXXXX4521';
    const accType = currentUser && currentUser.account_type ? currentUser.account_type : 'Savings';
    const holder = currentUser && currentUser.name ? currentUser.name : 'Rahul Sharma';
    
    cardWrap.innerHTML = `
        <div class="bank-card">
            <div class="card-top">
                <span class="bank-name">${t('bankName')}</span>
                <div class="card-chip"></div>
            </div>
            <div class="card-balance-section">
                <div class="card-label">${t('balanceLabel')}</div>
                <div class="card-amount">₹${Number(balance).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
            </div>
            <div class="card-bottom">
                <span>${holder}</span>
                <span>${accType} &bull; ${accNum}</span>
            </div>
        </div>
    `;
    container.appendChild(cardWrap);
}

// 2. Transactions Card Component
function renderTransactionsCard(container, transactions) {
    if (!transactions || transactions.length === 0) return;
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    let itemsHtml = transactions.slice(0, 5).map(t => {
        const isDebit = t.type === 'debit';
        const sign = isDebit ? '-' : '+';
        const colorClass = isDebit ? 'txn-debit' : 'txn-credit';
        return `
            <div class="txn-item">
                <div class="txn-left">
                    <span class="txn-desc">${t.description}</span>
                    <span class="txn-meta">${t.date} &bull; ${t.category}</span>
                </div>
                <div class="txn-amount ${colorClass}">
                    ${sign}₹${Number(t.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}
                </div>
            </div>
        `;
    }).join('');
    
    cardWrap.innerHTML = `
        <div class="transactions-card">
            <div class="txn-header">${t('recentActivity')}</div>
            ${itemsHtml}
        </div>
    `;
    container.appendChild(cardWrap);
}

// 3. Spending Breakdown Card Component
function renderSpendingCard(container, data) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    const total = data.monthly_spending || data.total_spending || 18450;
    const categories = data.categories || {};
    
    let barsHtml = Object.entries(categories).map(([cat, amt]) => {
        const pct = total > 0 ? Math.round((amt / total) * 100) : 0;
        return `
            <div class="category-row">
                <div class="cat-label-row">
                    <span>${cat}</span>
                    <span>₹${Number(amt).toLocaleString('en-IN')} (${pct}%)</span>
                </div>
                <div class="cat-progress">
                    <div class="cat-fill" style="width: ${pct}%"></div>
                </div>
            </div>
        `;
    }).join('');
    
    cardWrap.innerHTML = `
        <div class="spending-card">
            <div class="spending-stat-row">
                <div>
                    <div class="cell-label">${t('monthlySpending')}</div>
                    <div class="spending-total">₹${Number(total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                </div>
                <span class="balance-badge">Top: ${data.largest_category || 'Food'}</span>
            </div>
            <div class="category-bar-group">
                ${barsHtml}
            </div>
            ${data.suggestion ? `
                <div class="ai-observation-box">
                    <span>💡</span>
                    <div>${data.suggestion}</div>
                </div>
            ` : ''}
        </div>
    `;
    container.appendChild(cardWrap);
}

// 4. Loan Information Card Component
function renderLoanCard(container, loans) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    let loansHtml = loans.map(l => `
        <div class="info-card">
            <div class="label-row">
                <strong>${l.type}</strong>
                <span class="balance-badge">${l.interest_rate}% p.a.</span>
            </div>
            <div class="info-grid">
                <div class="info-cell">
                    <div class="cell-label">${t('principalLabel')}</div>
                    <div class="cell-val">₹${Number(l.principal_amount).toLocaleString('en-IN')}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('outstandingLabel')}</div>
                    <div class="cell-val">₹${Number(l.outstanding_amount).toLocaleString('en-IN')}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('monthlyEmiLabel')}</div>
                    <div class="cell-val text-primary">₹${Number(l.emi).toLocaleString('en-IN')}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('nextDueLabel')}</div>
                    <div class="cell-val">${l.next_due_date || '05th Next Mo'}</div>
                </div>
            </div>
        </div>
    `).join('');
    
    cardWrap.innerHTML = loansHtml;
    container.appendChild(cardWrap);
}

// 5. EMI Calculator Card Component
function renderEmiCard(container, emi) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    const monthly = emi.monthly_emi || emi;
    const principal = emi.principal || 500000;
    const rate = emi.interest_rate || 8.5;
    const tenure = emi.tenure_months || 60;
    const interest = emi.total_interest || Math.round(monthly * tenure - principal);
    const total = emi.total_payment || Math.round(monthly * tenure);
    
    cardWrap.innerHTML = `
        <div class="info-card">
            <div class="label-row">
                <strong>${t('emiSummary')}</strong>
                <span class="balance-badge">${rate}% Interest</span>
            </div>
            <div class="info-grid">
                <div class="info-cell">
                    <div class="cell-label">${t('monthlyEmiLabel')}</div>
                    <div class="cell-val text-primary">₹${Number(monthly).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('loanAmtLabel')}</div>
                    <div class="cell-val">₹${Number(principal).toLocaleString('en-IN')}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('totalInterest')}</div>
                    <div class="cell-val">₹${Number(interest).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                </div>
                <div class="info-cell">
                    <div class="cell-label">${t('totalRepayment')}</div>
                    <div class="cell-val">₹${Number(total).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                </div>
            </div>
        </div>
    `;
    container.appendChild(cardWrap);
}

// 6. Transfer Success Card Component
function renderTransferSuccessCard(container, data) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    cardWrap.innerHTML = `
        <div class="success-card">
            <div class="success-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <strong>${t('transferSuccess')}</strong>
            <div style="font-size: 13px;">₹${Number(data.amount).toLocaleString('en-IN', {minimumFractionDigits: 2})} transferred to <strong>${data.recipient}</strong></div>
            <div style="font-size: 12px; color: #047857;">Transaction ID: ${data.transaction_id || 'TXN' + Date.now().toString().slice(-5)}</div>
            <div class="balance-badge" style="margin-top: 4px;">${t('remainingBal')} ₹${Number(data.remaining_balance).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
        </div>
    `;
    container.appendChild(cardWrap);
}

// 6b. Savings & Growth Card Component
function renderSavingsCard(container, data) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    cardWrap.innerHTML = `
        <div class="savings-card">
            <div class="savings-header">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                <span>${t('savingsTitle')}</span>
            </div>
            <div class="savings-products">
                <div class="savings-product-row">
                    <div class="prod-info">
                        <strong>${t('savingsAccountName')}</strong>
                        <span class="prod-sub">${t('savingsAccountSub')}</span>
                    </div>
                    <div class="prod-rate">3.50% p.a.</div>
                </div>
                <div class="savings-product-row">
                    <div class="prod-info">
                        <strong>${t('fdName')}</strong>
                        <span class="prod-sub">${t('fdSub')}</span>
                    </div>
                    <div class="prod-rate">6.00% - 7.00%</div>
                </div>
                <div class="savings-product-row">
                    <div class="prod-info">
                        <strong>${t('rdName')}</strong>
                        <span class="prod-sub">${t('rdSub')}</span>
                    </div>
                    <div class="prod-rate">6.25% p.a.</div>
                </div>
            </div>
            <div class="savings-footer">
                <span>${t('savingsTip')}</span>
            </div>
        </div>
    `;
    container.appendChild(cardWrap);
}

// 7. Human Escalation Card Component
function renderHumanAgentCard(container) {
    const cardWrap = document.createElement('div');
    cardWrap.className = 'card-wrapper';
    
    cardWrap.innerHTML = `
        <div class="escalation-card">
            <div style="font-size: 13px; color: #9a3412;">
                ${t('connectHuman')}
            </div>
            <button class="escalation-btn" id="human-escalation-btn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <span>${t('connectHumanBtn')}</span>
            </button>
        </div>
    `;
    
    const btn = cardWrap.querySelector('#human-escalation-btn');
    btn.addEventListener('click', () => {
        btn.innerHTML = `<span>${t('connectedDemo')}</span>`;
        btn.style.background = '#15803d';
        btn.disabled = true;
    });
    
    container.appendChild(cardWrap);
}

/* ==================== OTP MODAL FLOW ==================== */
function openOtpModal(recipient, amount, demoOtp, scope = 'fund_transfer') {
    pendingTransferData = { recipient, amount, demoOtp, scope };
    
    const modalTitle = document.getElementById('modal-title');
    const modalSubtitle = document.getElementById('modal-subtitle');
    const modalRowLabel = document.getElementById('modal-row-label');
    const modalAmountLabel = document.getElementById('modal-amount-label');
    const modalVerifyBtnText = document.getElementById('modal-verify-btn-text');
    
    if (scope === 'personal_data') {
        if (modalTitle) modalTitle.textContent = t('modalTitleVerify');
        if (modalSubtitle) modalSubtitle.textContent = t('modalSubtitleVerify');
        if (modalRowLabel) modalRowLabel.textContent = t('modalAccessLabel');
        modalRecipient.textContent = t('modalAccessInfo');
        if (modalAmountLabel) modalAmountLabel.textContent = t('modalSecurityLabel');
        modalAmount.textContent = t('modalConfidential');
        if (modalVerifyBtnText) modalVerifyBtnText.textContent = t('modalVerifyView');
    } else {
        if (modalTitle) modalTitle.textContent = t('modalTitleTransfer');
        if (modalSubtitle) modalSubtitle.textContent = t('modalSubtitleTransfer');
        if (modalRowLabel) modalRowLabel.textContent = t('modalRecipientLabel');
        modalRecipient.textContent = recipient;
        if (modalAmountLabel) modalAmountLabel.textContent = t('modalAmountLabel');
        modalAmount.textContent = `₹${Number(amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        if (modalVerifyBtnText) modalVerifyBtnText.textContent = t('modalVerifyTransfer');
    }
    
    otpCodeInput.value = demoOtp || '123456';
    otpModal.style.display = 'flex';
}

function closeOtpModal() {
    otpModal.style.display = 'none';
    pendingTransferData = null;
}

modalCancelBtn.addEventListener('click', closeOtpModal);

modalVerifyBtn.addEventListener('click', () => {
    if (!pendingTransferData) return;
    
    const otp = otpCodeInput.value.trim();
    if (!otp) {
        alert(t('errOtp'));
        return;
    }
    
    closeOtpModal();
    
    // Automatically submit OTP through the chat interface
    chatInput.value = otp;
    sendMessage();
});

function scrollChatToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

