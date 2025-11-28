# Lumin Credit
Get clarity and a plan for your credit.

## AI Credit Scoring Agent Prototype

This project demonstrates a multi-agent credit scoring system. It includes a Python backend (running on Modal.com) and a React frontend.

### Architecture

**Data Generator**: Creates 30 fake users with realistic financial profiles using Faker.

**Credit Calculation Agent**: Algorithms to determine baseline credit score.

**Prediction Agent**: Analyzes user weak points (e.g., high utilization) and generates text-based improvement plans.

**Alerting Agent**: Watches simulated transactions. If a user on a "debt reduction plan" spends drastically, it flags an alert.

### How to Run

#### 1. The Backend (Modal.com)

You need the modal python client installed.

Install dependencies:

```bash
pip install modal faker
```

Authenticate with Modal:

```bash
modal setup
```

Run the backend in dev mode (hot reload):

```bash
modal serve backend.py
```

Copy the URL provided in the terminal (e.g., https://your-username--credit-api.modal.run).

#### 2. The Frontend (React)

The CreditApp.jsx file provided is a self-contained React component.

In the CreditApp.jsx code, look for the generateMockUsers function.

To connect to the real backend:
Replace the useEffect mock data generation in CreditApp.jsx with a fetch call to your Modal URL:

```javascript
useEffect(() => {
  fetch('https://your-username--credit-api.modal.run')
    .then(res => res.json())
    .then(response => {
       setUsers(response.data);
       // ... rest of setup
    });
}, []);
```

### Token Bus IO / LLM Integration

Currently, the agents use deterministic logic for speed and stability in the prototype. To use a real LLM (via TokenBus or OpenAI):

In backend.py, import your request library.

Update PredictionAgent.analyze:

```python
def analyze(user_data, current_score):
    # Example pseudo-code
    prompt = f"User has income {user_data['income']} and debt {user_data['debt']}. Suggest improvements."
    response = requests.post("https://api.tokenbus.io/...", json={"prompt": prompt})
    return response.json()['plan']
```

### UI Standards

The UI follows the "Modal.com" aesthetic:

**Font**: Sans-serif for UI, Monospace for numbers/code.

**Colors**: Zinc-950 background, Zinc-800 borders, Emerald-500 accents.

**Interactivity**: Hover states on all cards, interactive Recharts graphs.
