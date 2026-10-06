# FinChat — AI-Powered Conversational Banking Assistant

A working prototype of an AI-powered conversational banking assistant that allows customers to interact with a fictional retail banking system using natural language in **English** and **Kannada (ಕನ್ನಡ)**.

Built for the hackathon using **Google Gemini**, **FastAPI**, and a controlled mock banking dataset.

---

## 🌟 Key Features

1. **Dual Language Support (English + Kannada)**
   - Understands native queries in both English and Kannada script (e.g., *"Show my recent transactions"* & *"ನನ್ನ ಇತ್ತೀಚಿನ ವ್ಯವಹಾರಗಳನ್ನು ತೋರಿಸು"*).
   - Generates natural, context-aware responses in the user's selected language.

2. **Strict Controlled Banking Architecture**
   - Natural language processing and entity extraction powered by Gemini / resilient parser.
   - All banking operations (balances, transactions, loans, spending calculations) are executed by deterministic Python backend functions using mock JSON data.
   - Zero hallucination of customer account numbers, balances, or financial records.

3. **Two Operating Modes**
   - **Guest Mode**: General inquiries, home/personal loan interest rates, EMI calculations, FAQs. Personal data access is strictly blocked.
   - **Authenticated Mode**: PIN-based demo login with fictional customer profiles. Unlocks balances, transactions, spending analysis, and secure transfers.

4. **AI-Powered Spending Insights**
   - Categorizes debit transactions (Food, Shopping, Travel, Bills, Other).
   - Identifies highest expense categories and monthly totals.
   - Delivers friendly, non-guaranteed financial awareness tips.

5. **Simulated Secure 2FA OTP Protection**
   - **Personal Financial Access**: Requests for sensitive money information (balance, transactions, spending) require a simulated One-Time Password (Demo OTP: `123456`) before releasing personal financial data.
   - **Fund Transfers**: Strict OTP verification required for fund transfers, confirming recipient, amount, and sender balance before debiting.
   - Dedicated OTP modal & conversational OTP verification supported seamlessly.
   - Automatically records debits/credits in mock storage and updates balances live.

6. **Modern Banking-Style Web Interface**
   - Responsive UI with sleek bank cards, transaction feeds, spending progress bars, and loan summaries.
   - Simulated Human Agent escalation with a single click.

---

## 🏗️ Architecture

```
User Query (English / Kannada)
         │
         ▼
Web Chat Interface (HTML / CSS / JS)
         │
         ▼
FastAPI Backend (Port 8000)
         │
         ▼
Gemini API / Resilient NLU (Intent + Entity Extraction)
         │
         ▼
Python Banking Services (get_balance, analyze_spending, transfer_money)
         │
         ▼
Controlled Mock JSON Dataset (customers.json, transactions.json, loans.json, banking_info.json)
         │
         ▼
Gemini Response Generation (Natural Language in English / Kannada)
         │
         ▼
User Interface (Rich Visual Cards & Conversational Bubble)
```

---

## 👥 Fictional Customer Profiles

| Customer ID | Name | Demo PIN | Account Type | Account No. | Baseline Balance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CUST001** | **Rahul Sharma** | `1234` | Savings | `XXXXXX4521` | **₹52,430.00** |
| **CUST002** | Priya Patel | `5678` | Current | `XXXXXX8932` | ₹150,000.00 |
| **CUST003** | Suresh Kumar | `2468` | Savings | `XXXXXX1098` | ₹28,750.00 |
| **CUST004** | Ananya Rao | `4321` | Savings | `XXXXXX7741` | ₹94,300.00 |
| **CUST005** | Vikram Singh | `9876` | Current | `XXXXXX3320` | ₹215,000.00 |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed
- Web browser (Chrome, Edge, Firefox, Safari)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Gemini API Key (Optional)
Add your Gemini API key in the `.env` file:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
> **Note**: FinChat features an intelligent built-in multilingual fallback parser. If a Gemini API key is not configured or network access is restricted during testing, the assistant automatically provides full functionality, entity extraction, and Kannada/English responses.

### Session-cookie configuration

FinChat stores only an opaque, random `bank_session` identifier in an HttpOnly cookie. For local HTTP development, the default `APP_ENV=development` permits a non-Secure cookie. Set these values when deploying over HTTPS:

```env
APP_ENV=production
BANK_COOKIE_SECURE=true
CORS_ORIGINS=https://your-finchat-domain.example
```

The cookie uses `HttpOnly`, `SameSite=Lax`, a 30-day lifetime, and the `Secure` attribute in production. It never contains a PIN, OTP, account information, conversation data, or API key.

### 4. Run the Application
Start the FastAPI server:
```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 5. Access the Web Interface
Open your web browser and navigate to:
```
http://127.0.0.1:8000/
```
The interface will load instantly.

---

## 🎬 Mandatory Demo Walkthrough

Follow these steps for the complete hackathon evaluation:

1. **Guest Mode**:
   - Select **Guest Mode** from profile dropdown and click **Access FinChat**.
   - Click the suggestion chip or ask: `"What is the home loan interest rate?"`
   - *Result*: Assistant displays current loan interest rates (Home Loan: 8.5% p.a.).
   - Ask: `"What is my balance?"`
   - *Result*: Assistant politely blocks request: *"Please log in first to access your personal account information."*

2. **Customer Login**:
   - Click **Logout** at top-right.
   - Select **Rahul Sharma (CUST001)**. PIN pre-fills `1234`.
   - Click **Access FinChat**.

3. **Balance Enquiry**:
   - Ask: `"What is my balance?"`
   - *Result*: Assistant displays **Available Balance: ₹52,430.00** with a FinChat Bank Debit Card widget.

4. **Transaction History**:
   - Ask: `"Show my recent transactions."`
   - *Result*: Assistant renders recent transactions (Amazon Shopping -₹4,100, Swiggy Dining -₹3,200, Salary Credit +₹75,000).

5. **AI Financial Insights**:
   - Ask: `"Where am I spending most?"`
   - *Result*: Assistant displays monthly spending (₹18,450.00), visual category breakdown bars, highlights **Food** as largest category (₹5,200), and provides a savings observation.

6. **Kannada Language Demonstration**:
   - Ask: `"ನನ್ನ ಇತ್ತೀಚಿನ ವ್ಯವಹಾರಗಳನ್ನು ತೋರಿಸು"`
   - *Result*: Assistant understands the intent and lists recent transactions in Kannada.
   - Ask: `"ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?"`
   - *Result*: Assistant answers in Kannada: *"ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಉಳಿತಾಯ ಖಾತೆಯ ಬಾಕಿ ₹52,430.00 ಆಗಿದೆ."*

7. **Simulated Fund Transfer Flow**:
   - Ask: `"Transfer ₹2,000 to Rahul."` (or Priya)
   - *Result*: Assistant triggers OTP verification modal & prompt: *"A verification OTP has been sent. Demo OTP: 123456"*.

8. **OTP Verification**:
   - Enter `123456` in the modal or in the chat input.
   - *Result*: Transfer completes successfully!

9. **Confirmation & Real-time Update**:
   - Assistant displays transfer confirmation card with Transaction ID.
   - Displays new remaining balance: **₹50,430.00** (₹52,430 - ₹2,000).
   - Top balance badge dynamically updates to `Bal: ₹50,430`.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check & service status |
| `POST` | `/login` | Authenticate customer with PIN |
| `POST` | `/chat` | Primary natural language conversational endpoint |
| `GET` | `/customer/{id}/balance` | Retrieve current account balance |
| `GET` | `/customer/{id}/transactions` | Retrieve transaction history |
| `GET` | `/customer/{id}/account` | Retrieve masked account details |
| `GET` | `/customer/{id}/loan` | Retrieve active loan information |
| `POST` | `/emi` | Calculate monthly EMI & interest schedule |
| `GET` | `/interest-rates` | Retrieve latest deposit & lending rates |
| `GET` | `/customer/{id}/insights` | Retrieve AI spending analysis |
| `POST` | `/transfer/initiate` | Validate transfer parameters & issue OTP |
| `POST` | `/transfer/verify` | Verify OTP and execute persistent balance update |

---

## 🔒 Security Principles
- Account numbers and mobile numbers are masked (`XXXXXX4521`, `98XXXXXX21`).
- Fictional data only — strictly simulated banking operations.
- Backend validates sender balance before authorizing transfers.
- OTP verification required before any balance deduction occurs.
- API keys kept securely on the server via `.env` and never exposed to the frontend.
