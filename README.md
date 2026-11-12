# ClearPay AI — Payment Recovery Copilot

## Phase 3: Dashboard & Payment Recovery Copilot

### Project Overview
ClearPay AI is a Payment Recovery Copilot and Financial Operations Dashboard. The application pairs a React + TypeScript frontend with a Python + FastAPI backend, integrating:
1. **Financial Operations Dashboard**: KPI cards, session transaction tracking, recovery case oversight, recent activity audit, and demo data mode.
2. **Payment Recovery Copilot**: Live Google Gemini AI analysis of failed transactions, structured failure diagnosis, evidence-grounded hypothesis scoring, multi-turn follow-up queries, conditional document requirements, and customer-facing messaging.
3. **PayPal Sandbox Integration**: End-to-end OAuth authentication, order creation, buyer approval redirect, verified payment capture, duplicate capture protection, and simulated Demo Mode.

### Current Implementation Scope
- ✅ **SaaS Dashboard Layout**: Professional sidebar navigation across 5 dedicated sections:
  1. **Overview**: KPI metrics (Total, Successful, Failed, Pending, Recovery Cases), session state notice, demo data toggle, recent transactions, recovery overview, and recent activity.
  2. **Payment Recovery Copilot**: Full diagnostic workbench with transaction incident input, Gemini analysis generation, confirmed facts vs. possible causes, recovery action plan, conditional document checklists, and multi-turn follow-up history.
  3. **Payment Transactions**: Searchable by Order ID, filterable by status, with explicit status badges, honest empty states, and 1-click "Diagnose in Copilot" actions.
  4. **Recovery Cases**: Non-persistent case registry with incident summaries, AI diagnostic indicators, recommended next actions, and direct links to Copilot.
  5. **Settings**: Non-sensitive system status inspection (backend health, Gemini model status, PayPal Sandbox status), safe Demo Mode toggle, and strict zero-secret-leakage security policy.
- ✅ **Backend FastAPI Service**:
  - `GET /` & `GET /health` — Service health
  - `GET /api/settings/status` — Safe integration status flags (no secret exposure)
  - `POST /api/orders` — PayPal Sandbox order creation
  - `POST /api/orders/{order_id}/capture` — Verified payment capture
  - `POST /api/ai/analyze-payment` — Gemini payment failure diagnostic analysis
  - `POST /api/ai/follow-up` — Multi-turn AI follow-up questions
- ✅ **Automated Verification**:
  - 52 passing backend tests (`pytest test_main.py`)
  - 35 passing frontend tests (`vitest run` across 3 test suites)
  - 0 ESLint warnings or errors (`npm run lint`)
  - 0 TypeScript compiler errors (`npx tsc --noEmit`)
  - Clean production build (`vite build`)

### Prerequisites
- Node.js (v20 or later)
- npm or yarn
- Python 3.11 or later
- Git
- PayPal Developer account with Sandbox app credentials

### Project Structure
```
ClearPayAI/
├── frontend/           # React + TypeScript + Vite frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── eslint.config.js
│   ├── src/
│   │   ├── App.tsx     # Main component with backend connection + order UI
│   │   ├── main.tsx
│   │   └── index.css
│   └── index.html
├── backend/            # Python + FastAPI backend
│   ├── main.py         # FastAPI app with PayPal integration
│   ├── test_main.py    # Backend tests
│   ├── requirements.txt
│   ├── .env.example    # Environment variable placeholders
│   └── .venv/          # Python virtual environment
├── .gitignore
└── README.md
```

### Frontend Installation and Startup
```powershell
# Navigate to frontend directory
cd C:\ClearPayAI\frontend

# Install dependencies
npm install

# Start development server
npm run dev
# The app will be available at http://localhost:5173
```

### Backend Virtual Environment Activation (Windows PowerShell)
```powershell
# Navigate to backend directory
cd C:\ClearPayAI\backend

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload
# The API will be available at http://127.0.0.1:8000
```

### Backend Startup Commands
```powershell
# With venv activated
uvicorn main:app --reload

# Alternative: run directly with python
python -m uvicorn main:app --reload
```

### Local Development URLs
- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:8000
- Backend Health: http://127.0.0.1:8000/health
- Backend Root: http://127.0.0.1:8000/
- Create Order: POST http://127.0.0.1:8000/api/orders

### How to Test the Frontend-to-Backend Connection
1. Start the backend server (see Backend Startup Commands above)
2. Start the frontend development server (see Frontend Installation and Startup above)
3. Open http://localhost:5173 in your browser
4. Click the "Check Backend Connection" button
5. If the backend is running, you should see "Backend connected! Status: healthy"
6. If the backend is not running, you will see an error message

### PayPal Sandbox Setup
1. Go to https://developer.paypal.com/dashboard/applications/sandbox
2. Create a Sandbox app (or use an existing one)
3. Copy the Client ID and Client Secret
4. Copy `backend/.env.example` to `backend/.env`
5. Fill in `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_BASE_URL`
6. Restart the backend server
7. Click "Create PayPal Order" on the frontend to test

### Known Limitation: PayPal Sandbox Currency
- The PayPal Sandbox checkout may block payments with the error "This seller doesn't accept payments in your currency."
- This occurs when both default Sandbox accounts are registered in India, as the order uses USD currency
- Real buyer approval and capture flow remains blocked by this observed Sandbox checkout error
- Demo mode provides a way to demonstrate the application workflow when Sandbox approval is blocked

### Running Tests
```powershell
# Backend tests (52 passing tests)
cd C:\ClearPayAI\backend
.\.venv\Scripts\Activate.ps1
python -m pytest test_main.py -q

# Frontend checks (35 passing tests, 0 lint errors, 0 type errors)
cd C:\ClearPayAI\frontend
npm test          # Vitest: dashboard, copilot, and PayPal return tests (35 passed)
npm run lint      # ESLint checks (0 errors, 0 warnings)
npx tsc --noEmit  # TypeScript strict type checking
npm run build     # Production Vite bundle build
```

### Environment-Variable Safety Notes
- The `backend/.env.example` file contains placeholder values only
- Never commit real `.env` files with credentials to the repository
- The `.gitignore` excludes all `.env*` files to prevent accidental commits
- To use real environment variables, copy `backend/.env.example` to `backend/.env` and fill in your values
- Environment variables are loaded using `python-dotenv` in the FastAPI backend
- The Client Secret and access tokens are never exposed in API responses, logs, or error messages

### Demo Mode
- Demo mode can be enabled by setting `DEMO_MODE=1` in the backend environment
- This is useful when the PayPal Sandbox checkout is blocked (e.g., the "This seller doesn't accept payments in your currency" error observed with India-registered accounts)
- When enabled, all payment operations use simulated data instead of calling PayPal's APIs
- The frontend clearly displays "DEMO MODE — SIMULATED PAYMENT" throughout the workflow
- A clear message "Simulation only. No real payment was processed." is shown
- Status uses `SIMULATED_COMPLETED` instead of the real PayPal status `COMPLETED`
- Demo mode defaults to disabled; enable it by adding `DEMO_MODE=1` to `backend/.env`
- Simulated transactions are distinct from actual PayPal order and capture records
- The capture endpoint returns `SIMULATED_COMPLETED` status without calling PayPal's capture API

### Phase 3: Buyer Approval, Return, and Payment Capture

Phase 3 adds the complete buyer approval and payment capture flow:
- ✅ `return_url` and `cancel_url` configured with frontend routes
- ✅ CAPTURE intent on all orders
- ✅ `POST /api/orders/{order_id}/capture` endpoint
- ✅ Backend obtains its own OAuth token and calls PayPal capture API
- ✅ Verified capture response (never trusts frontend params alone)
- ✅ Frontend states: idle, creating, awaiting_approval, processing, completed, cancelled, failed
- ✅ COMPLETED only shown when PayPal confirms capture
- ✅ Handles already-captured, unapproved, invalid order IDs, timeouts, PayPal errors
- ✅ In-memory duplicate capture prevention
- ✅ 25 backend tests (order creation + capture scenarios)

### Features Intentionally Not Implemented (Phase 3)
- AI model integration
- Database persistence
- Authentication or user accounts
- Payment recovery automation
- Deployment configuration
- Docker setup
- Redis caching

### How to Test the Complete Sandbox Flow
1. Start the backend server (see Backend Startup Commands above)
2. Start the frontend development server (see Frontend Installation and Startup above)
3. Open http://localhost:5173 in your browser
4. Click "Check Backend Connection" → should show "healthy"
5. Click "Create PayPal Order" → should show order ID and approval link
6. Click "Approve Payment on PayPal" → opens PayPal Sandbox checkout
7. Log in with a **USD Sandbox buyer account** (create one at https://developer.paypal.com/dashboard/accounts)
8. Approve the payment on PayPal
9. PayPal redirects back to http://localhost:5173 with order token
10. Frontend automatically calls the capture endpoint
11. Verify "✅ COMPLETED" is displayed with capture ID
12. To test cancellation: click "Cancel" on the PayPal checkout page → frontend shows "Payment cancelled by buyer"

### API Endpoints (Phase 3)
- `GET /` — Welcome message
- `GET /health` — Health check
- `POST /api/orders` — Create a PayPal Sandbox order (returns order_id, approval_url, amount, currency)
- `POST /api/orders/{order_id}/capture` — Capture a PayPal order after buyer approval (returns order_id, status, capture_id, amount, currency)

### Capture Error Handling
- **Unapproved order**: Returns 409 "Order has not been approved by the buyer yet."
- **Already captured**: Returns 409 "Order has already been captured."
- **Order not found**: Returns 404 "Order not found."
- **Invalid order ID**: Returns 400 "Invalid order ID format."
- **Timeout**: Returns 504 "PayPal capture timed out."
- **PayPal error**: Returns 502 "PayPal capture failed."
- **Non-COMPLETED status**: Returns 409 "Payment not completed."
- **Missing credentials**: Returns 500 "PayPal credentials are not configured."