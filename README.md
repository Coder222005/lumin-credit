# Lumin Credit

**Get clarity and a plan for your credit.**

Lumin Credit is an advanced AI-powered credit scoring and financial planning system. It leverages a multi-agent architecture to provide users with dynamic credit score analysis, personalized improvement plans, and intelligent financial advice.

## 🚀 Key Features

### 🤖 Intelligent Agent Swarm
The core of Lumin Credit is a swarm of specialized AI agents working together:

*   **Score Impact Agent (The Adjuster):** Determines dynamic score impact values based on the user's current credit standing (e.g., rewarding recovery for lower scores).
*   **Credit Calculation Agent (The Mathematician):** Calculates the base credit score using deterministic logic and real financial data.
*   **Prediction Agent (The Analyst):** Uses **Nebius AI (Llama 3.3)** to analyze user data and generate specific, actionable text-based improvement plans.
*   **Alerting Agent (The Watchdog):** Monitors transactions for risky behavior (e.g., large spending, late payments) and flags alerts.
*   **Financial Plan Agent (The Wealth Advisor):** Suggests personalized loan eligibility and investment plans based on income and score.
*   **Goal Setting Agent (The Strategist):** Generates tailored strategies to achieve specific financial goals (e.g., "Buy a House").
*   **Limit Generator Agent (The Controller):** Calculates "Safe" and "Max" payment limits to ensure users don't overspend while saving for their goals.
*   **Payment Agent (The Gatekeeper):** Evaluates payment requests against the user's balance and financial health, preventing dangerous overpayments.

### 📊 Interactive Dashboard
*   **Real-time Score Visualization:** Dynamic credit score meter and historical trend analysis.
*   **Financial Health Overview:** Detailed breakdown of income, debt, utilization, and payment history.
*   **Goal Tracking:** Set and monitor progress towards financial goals.
*   **Transaction History:** Scrollable list of past transactions with status indicators.

### 💳 Smart Payment System
*   **Payment Verification:** Intelligent "Make Payment" functionality that checks for sufficient funds and prevents inefficient overpayments.
*   **Safe Limit Calculation:** Automatically suggests safe payment amounts to maintain financial stability.

## 🛠️ Tech Stack

*   **Frontend:** React, Vite, Tailwind CSS, Recharts, Chart.js, Lucide React.
*   **Backend:** Python, Flask, Modal.com (Serverless Deployment).
*   **AI/LLM:** Nebius AI (Llama 3.3-70B-Instruct) for intelligent agent logic.

## ⚙️ Installation & Setup

### 1. Backend Setup (Modal.com)

The backend runs on Modal.com for serverless scalability.

1.  **Install Dependencies:**
    ```bash
    pip install modal flask flask-cors openai
    ```

2.  **Authenticate with Modal:**
    ```bash
    modal setup
    ```

3.  **Run Locally (Dev Mode):**
    ```bash
    modal serve backend.py
    ```
    *Copy the URL provided in the terminal (e.g., `https://your-username--lumincredit-backend-web-app.modal.run`).*

### 2. Frontend Setup

1.  **Navigate to Frontend Directory:**
    ```bash
    cd frontend
    ```

2.  **Install Dependencies:**
    ```bash
    npm install
    ```

3.  **Configure Backend URL:**
    *   Update the fetch URL in `src/Dashboard.jsx` (or relevant components) to point to your Modal backend URL.

4.  **Run Development Server:**
    ```bash
    npm run dev
    ```

## 📂 Project Structure

*   `backend.py`: Main backend application file containing all agent classes and Flask routes.
*   `frontend/`: React frontend application.
    *   `src/Dashboard.jsx`: Main dashboard component integrating all UI elements.
    *   `src/components/`: Reusable UI components (AgentSwarm, Navbar, etc.).
*   `data.json` / `user_data.json`: Synthetic user data storage.

---

*Built with ❤️ by the Lumin Credit Team.*
