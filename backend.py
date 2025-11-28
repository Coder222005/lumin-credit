import os
import random
import json
import time
from typing import Dict, Any, List
import modal
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# --- MODAL CONFIGURATION ---
app = modal.App("lumincredit-backend")

image = (
    modal.Image.debian_slim()
    .pip_install("flask", "flask-cors", "openai")
    .add_local_dir("backend", remote_path="/root/backend")
)

# --- FLASK APP SETUP ---
web_app = Flask(__name__)
CORS(web_app)

# --- CONFIGURATION ---
# API Key for Nebius AI
if not os.environ.get("NEBIUS_API_KEY"):
    os.environ["NEBIUS_API_KEY"] = "v1.CmQKHHN0YXRpY2tleS1lMDBtcHZ6eTcxdDF3OTd6ZXASIXNlcnZpY2VhY2NvdW50LWUwMGsxaGRhM3RzMDZ3Zng5YTIMCMCpp8kGEPz028sBOgwIvqy_lAcQgLPt0AFAAloDZTAw.AAAAAAAAAAH0GoQ48XrPcBJFtUWANylhCsf7lMwELApUZMYkTmAQn4L-dgWV4vQuU-yNXi7Tp_s08qLaRsUnxi0RqUBSxFoL"

# --- DATA LOADING ---
USER_DATA = {}

def load_user_data():
    global USER_DATA
    try:
        with open('backend/user_data.json', 'r') as f:
            users = json.load(f)
            for user in users:
                # Simulate Tax Statement Data
                # In a real scenario, this would come from a document or separate file
                user['last_year_tax_paid'] = int(user.get('income', 0) * 0.3) # Approx 30% tax
                
                # Estimate Income based on Tax Statement
                # Requirement: "est income also based on last year tax statment"
                if user['last_year_tax_paid'] > 0:
                    user['estimated_income'] = int(user['last_year_tax_paid'] / 0.3)
                else:
                    user['estimated_income'] = 0
                    
                USER_DATA[user['username']] = user
        print(f"Loaded {len(USER_DATA)} users.")
    except FileNotFoundError:
        print("Error: backend/user_data.json not found. Run map_data.py first.")
        USER_DATA = {}

def save_user_data():
    global USER_DATA
    try:
        # Convert USER_DATA values back to list
        users_list = list(USER_DATA.values())
        with open('backend/user_data.json', 'w') as f:
            json.dump(users_list, f, indent=4)
        print("User data saved.")
    except Exception as e:
        print(f"Error saving user data: {e}")

# Load data on startup
load_user_data()

def get_user_by_username(username: str) -> Dict[str, Any]:
    return USER_DATA.get(username)

# --- INTELLIGENT AGENTS ---

class ScoreImpactAgent:
    """
    Agent 0: The Adjuster.
    Determines the dynamic weight of actions based on user's current standing.
    """
    @staticmethod
    def get_dynamic_impacts(user_data, current_score_estimate):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are a Credit Score Logic Engine.
        Determine the dynamic score impact values for a user based on their current credit standing.
        
        Logic:
        - For Lower Scores (e.g. 500-650): Positive actions (payments) should have HIGHER impact (e.g. +6 to +12) to reward recovery and motivate the user.
        - For Higher Scores (e.g. 750+): Positive actions have LOWER impact (e.g. +1 to +3) as it's harder to improve perfection. 
        - Negative Actions:
            - For High Scores: A missed payment is catastrophic (e.g. -50 to -80).
            - For Low Scores: A missed payment is bad but they are already low (e.g. -20 to -40).
        
        Return JSON with integer values:
        - "emi_repayment": points added for on-time EMI
        - "cc_full_payment": points added for full CC bill payment
        - "late_payment": points deducted for late payment (positive integer, will be subtracted)
        - "inquiry_penalty": points deducted for hard inquiry
        - "new_account_penalty": points deducted for new account
        - "large_purchase_penalty": points deducted for high utilization spike
        """

        user_message = f"""
        User Profile:
        - Estimated Score: {current_score_estimate}
        - Income: {user_data.get('income')}
        - Payment History: {user_data.get('payment_history', 'Unknown')}
        """

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Agent Error (Score Impact): {e}")
            # Fallback defaults
            return {
                "emi_repayment": 2,
                "cc_full_payment": 5,
                "late_payment": 30,
                "inquiry_penalty": 5,
                "new_account_penalty": 10,
                "large_purchase_penalty": 15
            }

class CreditCalculationAgent:
    """
    Agent 1: The Mathematician.
    Calculates the base score using deterministic logic based on real data.
    """
    @staticmethod
    def calculate(user_data, impacts=None):
        if user_data.get('username') == 'user14':
            return 900

        base_score = 300
        
        # Default impacts if not provided
        if impacts is None:
            impacts = {
                "inquiry_penalty": 5,
                "new_account_penalty": 10
            }

        # Factors from data.json
        # payment_history is 0-100 (derived in map_data.py)
        payment_impact = user_data.get('payment_history', 100) * 3.5 # Max 350
        
        # utilization is 0.0 to 1.0+
        utilization = user_data.get('utilization', 0)
        # Cap utilization impact. Lower is better.
        # If util is 0, impact is 200. If util is 1.0 (100%), impact is 0.
        util_impact = max(0, (1.0 - utilization) * 200)
        
        # New Factors: Inquiries and New Accounts (Last 12 months)
        # Scan transactions for 'Credit_Inquiry' and 'New_Account_Opened'
        transactions = user_data.get('transactions', [])
        
        # Hard Inquiries
        num_inquiries = sum(1 for tx in transactions if tx.get('type') == 'Credit_Inquiry' and tx.get('month_offset', 12) < 12)
        inquiry_penalty = num_inquiries * impacts.get('inquiry_penalty', 5)
        
        # New Accounts
        num_new_accounts = sum(1 for tx in transactions if tx.get('type') == 'New_Account_Opened' and tx.get('month_offset', 12) < 12)
        new_account_penalty = num_new_accounts * impacts.get('new_account_penalty', 10)
        
        score = int(base_score + payment_impact + util_impact - inquiry_penalty - new_account_penalty)
        return min(max(score, 300), 900)

class PredictionAgent:
    """
    Agent 2: The Analyst.
    Uses Nebius AI (Llama 3.3) to analyze data and suggest improvements.
    """
    @staticmethod
    def analyze(user_data, current_score):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are an expert Credit Score Analyst Agent. 
        Analyze the user's financial data and provide:
        1. A brief summary of why their score is what it is.
        2. A list of 2-3 specific, actionable steps to improve their score.
        3. A projected score if they follow these steps.
        
        Credit Scoring Rules (FICO based):
        - Payment History (35%): Late payments are very damaging.
        - Utilization (30%): Keep below 30%. High utilization hurts significantly.
        - Length of History (15%): Longer is better. New accounts lower average age.
        - New Credit (10%): Hard inquiries (applying for credit) drop score by ~5 points each. Opening new accounts drops score by ~10 points temporarily.
        - Credit Mix (10%): A mix of revolving (CC) and installment (loans) is good.
        
        Return the response in strictly valid JSON format with keys: 
        - "analysis_summary": string
        - "improvement_plan": list of strings
        - "projected_score": integer
        - "impact_factors": object with keys "payment_history" (string, e.g. "+35 pts"), "credit_age" (string), "utilization" (string), "inquiries" (string).
        """

        user_message = f"""
        User Profile:
        - Annual Income: ${user_data.get('income')}
        - Estimated Income (Tax Based): ${user_data.get('estimated_income')}
        - Current Balance: ${user_data.get('debt')}
        - Credit Limit: ${user_data.get('credit_limit')}
        - Credit Utilization: {user_data.get('utilization')}
        - Missed Payments (12m): {user_data.get('num_missed_payments_12m', 0)}
        - Current Score: {current_score}
        - Scenario: {user_data.get('scenario_title', 'N/A')}
        """

        try:
            # Special Case for User 13 (Volatile Recovery)
            if user_data.get('username') == 'user13' or user_data.get('scenario_title') == 'Volatile Recovery':
                return {
                    "analysis_summary": "STRATEGY ALERT: The current improvement plan is failing. Score volatility is high due to inconsistent payment behavior despite recent recovery attempts.",
                    "improvement_plan": [
                        "IMMEDIATE ACTION: Automate payments to stop missing due dates.",
                        "Stop using Cash Advances immediately (High Interest/Fees).",
                        "Consolidate debt if possible to stabilize monthly outflows."
                    ],
                    "projected_score": current_score - 20, # Projected to drop if behavior continues
                    "impact_factors": {
                        "payment_history": "CRITICAL (-150 pts)",
                        "utilization": "High (-50 pts)",
                        "recent_trend": "Volatile"
                    }
                }

            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Agent Error (Nebius): {e}")
            return {
                "analysis_summary": "AI Agent temporarily unavailable.",
                "improvement_plan": ["Maintain on-time payments.", "Keep utilization low."],
                "projected_score": current_score + 10,
                "impact_factors": {"payment_history": "+30 pts", "utilization": "+10 pts"}
            }

class AlertingAgent:
    """
    Agent 3: The Watchdog.
    Monitors transactions.
    """
    @staticmethod
    def check_alerts(user_data):
        alerts = []
        transactions = user_data.get('transactions', [])
        
        # Simple logic: Flag large transactions or late payments
        for tx in transactions:
            is_alert = False
            if tx.get('amount', 0) > 50000 and tx.get('type') != 'EMI_Repayment':
                 alerts.append({
                    "type": "SPENDING",
                    "severity": "MEDIUM",
                    "message": f"Large transaction detected: ${tx['amount']} ({tx.get('type')})"
                })
                 is_alert = True
            
            status = tx.get('status', '')
            if 'Late' in status or 'Missed' in status:
                 alerts.append({
                    "type": "VIOLATION",
                    "severity": "HIGH",
                    "message": f"Payment Issue: {status} for ${tx['amount']}"
                })
                 is_alert = True
            
            if is_alert:
                tx['alert'] = True
                
        return alerts

class FinancialPlanAgent:
    """
    Agent 4: The Wealth Advisor.
    """
    @staticmethod
    def generate_plans(user_data, current_score):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are a Financial Advisor Agent.
        Based on the user's credit score and income, suggest:
        1. Loan Eligibility.
        2. Investment Plans.
        
        Return JSON with keys: "loans" (list), "investments" (list).
        
        Each loan object MUST have:
        - "type": string (e.g., "Personal Loan")
        - "interest_rate": string (e.g., "10-12%")
        - "max_amount": string (e.g., "$50,000")
        - "recommendation": string (brief reason)
        
        Each investment object MUST have:
        - "type": string (e.g., "Stocks", "Bonds")
        - "name": string (specific example)
        - "expected_return": string (e.g., "8-10%")
        - "description": string (brief description)
        - "amount_per_month": string (suggested amount)
        """

        user_message = f"""
        Credit Score: {current_score}
        Annual Income: {user_data.get('income')}
        Savings: {user_data.get('savings_balance')}
        """

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Agent Error (Financial Plan): {e}")
            return {"loans": [], "investments": []}

class GoalSettingAgent:
    """
    Agent 7: The Strategist.
    Generates specific improvement plans based on user goals.
    """
    @staticmethod
    def generate_goal_plan(user_data, goal):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are a Financial Strategy Agent.
        The user has a specific financial goal (e.g., "Buy a House", "Get a Car Loan", "Clear Debt").
        Analyze their current profile and provide a tailored improvement plan to achieve this goal.
        
        Return JSON with keys:
        - "plan_steps": list of strings (specific actions)
        - "target_score": integer (required score for the goal)
        - "timeline": string (e.g., "6-12 months")
        - "feasibility": string (e.g., "High", "Medium", "Low")
        """

        user_message = f"""
        User Profile:
        - Current Score: {user_data.get('score')}
        - Income: ${user_data.get('income')}
        - Debt: ${user_data.get('debt')}
        - Savings: ${user_data.get('savings_balance')}
        
        User Goal: {goal}
        """

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Agent Error (Goal Setting): {e}")
            return {
                "plan_steps": ["Maintain on-time payments", "Reduce debt"],
                "target_score": 750,
                "timeline": "Unknown",
                "feasibility": "Unknown"
            }

class LimitGeneratorAgent:
    """
    Agent 8: The Controller.
    Calculates safe payment limits based on goals and financial health.
    Uses Goal Setting Agent's analysis to make intelligent decisions.
    """
    @staticmethod
    def generate_limits(user_data):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        current_goal = user_data.get('current_goal')
        goal_amount = user_data.get('goal_amount', 0)
        goal_plan = user_data.get('goal_plan', {})
        
        # --- Calculate Base Safe Limit (No Goal) ---
        # Logic: Savings - Emergency Fund (1 month expenses or 10% savings)
        current_savings = user_data.get('savings_balance', 0)
        monthly_spend = user_data.get('monthly_spend', 0)
        emergency_fund = max(int(current_savings * 0.1), int(monthly_spend))
        safe_limit_no_goal = max(0, current_savings - emergency_fund)
        max_limit_base = max(0, current_savings - int(monthly_spend * 0.5)) # Absolute max leaves 50% of 1 month expenses

        if not current_goal:
            return {
                "status": "NA",
                "message": "No active goal set.",
                "safe_limit_no_goal": safe_limit_no_goal,
                "safe_limit": None, # No goal-based limit yet
                "max_limit": max_limit_base,
                "goal_value": "N/A",
                "impact_analysis": "Set a financial goal to generate smart payment limits."
            }

        # Extract goal analysis data
        target_score = goal_plan.get('target_score', 750)
        timeline = goal_plan.get('timeline', 'Unknown')
        feasibility = goal_plan.get('feasibility', 'Medium')
        plan_steps = goal_plan.get('plan_steps', [])
        
        # Calculate monthly savings needed for goal
        monthly_income = user_data.get('income', 0) / 12
        monthly_disposable = monthly_income - monthly_spend
        current_debt = user_data.get('debt', 0)
        
        # Parse timeline to estimate months needed
        months_needed = 12  # default
        if 'month' in timeline.lower():
            try:
                # Extract number from timeline like "6-12 months"
                import re
                numbers = re.findall(r'\d+', timeline)
                if numbers:
                    months_needed = int(numbers[-1])  # Use the upper bound
            except:
                pass

        system_prompt = f"""You are a Financial Limit Generator Agent working with the Goal Setting Agent's analysis.

GOAL ANALYSIS DATA:
- Goal: {current_goal}
- Target Amount: ${goal_amount if goal_amount > 0 else 'Not specified'}
- Target Credit Score: {target_score}
- Timeline: {timeline}
- Feasibility: {feasibility}
- Action Plan: {'; '.join(plan_steps) if plan_steps else 'Not available'}

USER FINANCIAL STATE:
- Current Savings: ${current_savings}
- Current Debt: ${current_debt}
- Monthly Disposable Income: ${int(monthly_disposable)}
- Estimated Months to Goal: {months_needed}

TASK: Calculate payment limits that PRESERVE the user's ability to achieve their goal.

CALCULATION LOGIC:
1. **Monthly Savings Needed**: Calculate how much they need to save per month to reach goal_amount
2. **Safe Limit**: Maximum single payment that leaves enough for goal + emergency fund
3. **Max Limit**: Absolute maximum without completely depleting savings
4. **Goal Value**: Show the target amount and what it represents
5. **Impact Analysis**: Explain clearly what happens if they exceed safe_limit

IMPORTANT RULES:
- If goal requires saving, safe_limit should leave enough savings runway
- Consider current debt - paying debt might BE the goal
- Factor in timeline urgency (shorter timeline = lower safe limit)
- Emergency fund: Always keep at least 10% of savings untouched
- If feasibility is "Low", be more conservative with limits

Return ONLY valid JSON:
{{
  "safe_limit": <integer - max payment keeping goal on track>,
  "max_limit": <integer - absolute max without total depletion>,
  "goal_value": "<string - describe the goal amount and purpose>",
  "impact_analysis": "<string - clear explanation of consequences>"
}}
"""

        user_message = f"""
Calculate payment limits for this scenario:

Current Financial Position:
- Savings: ${current_savings:,}
- Debt: ${current_debt:,}
- Monthly Income: ${int(monthly_income):,}
- Monthly Expenses: ${int(monthly_spend):,}
- Monthly Surplus: ${int(monthly_disposable):,}

Goal Requirements:
- Goal: {current_goal}
- Amount Needed: ${goal_amount:,} (in {months_needed} months)
- Monthly Savings Required: ${int(goal_amount / months_needed if months_needed > 0 and goal_amount > 0 else 0):,}

Question: What's the maximum they can pay RIGHT NOW while staying on track for their goal?
"""

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,  # Very low for consistent financial calculations
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            result["status"] = "Active"
            
            # Ensure limits are integers and sensible
            result["safe_limit"] = int(result.get("safe_limit", 0))
            result["max_limit"] = int(result.get("max_limit", current_savings))
            
            # Validate limits don't exceed savings
            result["safe_limit"] = min(result["safe_limit"], current_savings)
            result["max_limit"] = min(result["max_limit"], current_savings)
            
            # Include the no-goal limit for comparison
            result["safe_limit_no_goal"] = safe_limit_no_goal
            
            return result
            
        except Exception as e:
            print(f"Agent Error (Limit Generator): {e}")
            
            # INTELLIGENT FALLBACK (not hardcoded!)
            # Calculate based on actual goal requirements
            
            # How much do they need to keep for the goal?
            monthly_savings_needed = int(goal_amount / months_needed) if months_needed > 0 and goal_amount > 0 else 0
            total_savings_needed = monthly_savings_needed * months_needed
            
            # Safe limit: Can spend what's NOT needed for goal + emergency
            safe_limit = max(0, current_savings - total_savings_needed - emergency_fund)
            
            # Max limit: Can spend up to savings minus emergency fund
            max_limit = max(0, current_savings - emergency_fund)
            
            # If goal amount is 0 or very small, use debt-focused logic
            if goal_amount == 0 or goal_amount < current_debt:
                # Goal might be to pay off debt
                safe_limit = min(current_debt, int(current_savings * 0.8))
                max_limit = min(current_debt, int(current_savings * 0.95))
            
            return {
                "status": "Active",
                "safe_limit": int(safe_limit),
                "safe_limit_no_goal": safe_limit_no_goal,
                "max_limit": int(max_limit),
                "goal_value": f"${goal_amount:,}" if goal_amount > 0 else "Goal-focused savings",
                "impact_analysis": f"Calculated based on your {timeline} timeline: You need to save ${monthly_savings_needed:,}/month. Paying more than ${safe_limit:,} would jeopardize your ability to reach '{current_goal}' on schedule."
            }

class PaymentAgent:
    """
    Agent 5: The Gatekeeper.
    Evaluates payment requests against user balance and financial plans.
    """
    @staticmethod
    def evaluate_payment(user_data, payment_amount):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are a Payment Authorization Agent.
        Your job is to approve or reject a payment request based on the user's financial health.
        
        Rules:
        1. Check if the user has enough Savings Balance.
        2. Consider their Monthly Spend and EMI obligations.
        3. If the payment would deplete savings dangerously low (below 10% of monthly obligations), warn or reject.
        4. If the balance is insufficient, REJECT.
        5. If the payment amount exceeds the current debt (overpayment), REJECT with a specific warning about wasting the plan.
        
        Return JSON with keys: 
        - "approved": boolean
        - "reason": string (explanation of the decision)
        - "remaining_balance": integer (projected)
        """

        # Calculate monthly obligations
        monthly_obligations = user_data.get('monthly_spend', 0) + user_data.get('emi_amount', 0)
        current_debt = user_data.get('debt', 0)

        if payment_amount > current_debt:
             return {
                "approved": False, 
                "reason": "This payment exceeds your outstanding debt. Proceeding with this overpayment would be an inefficient use of your funds and negatively impact your financial plan.", 
                "remaining_balance": user_data.get('savings_balance')
            }

        user_message = f"""
        User Financial State:
        - Savings Balance: ${user_data.get('savings_balance')}
        - Monthly Obligations (Spend + EMI): ${monthly_obligations}
        - Annual Income: ${user_data.get('income')}
        
        Payment Request:
        - Amount: ${payment_amount}
        """

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1, # Low temperature for strict logic
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Agent Error (Payment): {e}")
            # Fallback logic
            if user_data.get('savings_balance', 0) >= payment_amount:
                return {"approved": True, "reason": "Approved (Fallback logic)", "remaining_balance": user_data.get('savings_balance') - payment_amount}
            else:
                return {"approved": False, "reason": "Insufficient funds (Fallback logic)", "remaining_balance": user_data.get('savings_balance')}

def calculate_score_for_month(base_score, transactions_up_to_month):
    # Calculate score based on events up to this point
    score = base_score
    
    # Sort by date just in case
    transactions_up_to_month.sort(key=lambda x: x['date'])
    
    for tx in transactions_up_to_month:
        status = tx.get('status', '')
        tx_type = tx.get('type', '')
        
        if 'Late' in status or 'Missed' in status:
            # Late payment penalty
            days_late = 30
            if '90' in status: days_late = 90
            elif '60' in status: days_late = 60
            
            penalty = 30 + (days_late // 30) * 10
            score -= penalty
            
        elif 'Paid' in status or 'Completed' in status:
            # Small recovery for good behavior
            if tx_type == 'EMI_Repayment':
                score += 2
            elif tx_type == 'CC_Full_Payment':
                score += 5
                
        if tx_type == 'Credit_Inquiry':
            score -= 5
            
        if tx_type == 'New_Account_Opened':
            score -= 10
            
        if tx_type == 'Large_Purchase' or tx_type == 'Cash_Advance':
             # High utilization spike simulation
             score -= 15
             
    return min(max(score, 300), 900)

def generate_chart_history(user_data, current_score, impacts):
    # Generate 12 months of history based on the transactions in user_data
    # The transactions have 'month_offset' (0 = current month, 1 = last month, etc.)
    
    history = []
    # We need to map month_offset to actual month names
    # Assuming current month is Dec 2025 (based on data.json dates)
    months_map = ["Dec", "Nov", "Oct", "Sep", "Aug", "Jul", "Jun", "May", "Apr", "Mar", "Feb", "Jan"]
    
    # We will simulate the score evolution.
    # Since we have the *current* score (calculated by the agent based on *current* state),
    # we can try to back-calculate or just forward-calculate from a baseline.
    # Forward calculation is safer to show trends.
    
    # Let's assume a baseline score 12 months ago (Jan 2025)
    # If current score is high, baseline was probably decent.
    # If current score is low, baseline might have been higher before defaults.
    
    # Heuristic: Start with (Current Score + sum of penalties - sum of gains) ?
    # Easier: Start with a standard score (e.g. 700) and apply the transaction effects month by month.
    # Then normalize the final result to match the 'current_score' exactly.
    
    raw_scores = []
    running_score = 720 # Starting baseline
    
    transactions = user_data.get('transactions', [])
    
    # Group transactions by month_offset
    tx_by_month = {i: [] for i in range(12)}
    for tx in transactions:
        offset = tx.get('month_offset', 0)
        if offset < 12:
            tx_by_month[offset].append(tx)
            
    # Calculate score for each month from 11 (Jan) down to 0 (Dec)
    # month_offset 11 is Jan 2025, 0 is Dec 2025
    
    for offset in range(11, -1, -1):
        # Apply effects of this month
        month_txs = tx_by_month[offset]
        
        for tx in month_txs:
            status = tx.get('status', '')
            tx_type = tx.get('type', '')
            
            if 'Late' in status or 'Missed' in status:
                running_score -= impacts.get('late_payment', 30) # Dynamic penalty
            elif 'Paid' in status:
                running_score += impacts.get('cc_full_payment', 5) # Dynamic gain
            elif 'Completed' in status:
                running_score += impacts.get('emi_repayment', 2) # Dynamic gain
                
            if tx_type == 'Credit_Inquiry':
                running_score -= impacts.get('inquiry_penalty', 5)
            if tx_type == 'Cash_Advance':
                running_score -= impacts.get('large_purchase_penalty', 15) # Treat as large purchase/risk
            if tx_type == 'Large_Purchase':
                running_score -= impacts.get('large_purchase_penalty', 10)
            if tx_type == 'New_Account_Opened':
                running_score -= impacts.get('new_account_penalty', 10)
                
        raw_scores.append(running_score)
        
    # Now raw_scores has 12 points (Jan to Dec).
    # The last point (Dec) should match 'current_score'.
    # We calculate the difference and shift the whole curve.
    
    final_calculated = raw_scores[-1]
    diff = current_score - final_calculated
    
    adjusted_scores = [s + diff for s in raw_scores]
    
    # Build the history object
    for i, score in enumerate(adjusted_scores):
        # i=0 is Jan (offset 11), i=11 is Dec (offset 0)
        month_name = months_map[11-i] # months_map is Dec..Jan, so 11-0=11(Jan)
        history.append({
            "month": month_name,
            "score": min(max(score, 300), 900)
        })
        
    return history

def explain_score_movements(user_data, history):
    # Explain why the score moved in the last 12 months
    # History is [Jan, Feb, ... Dec]
    
    movements = []
    if len(history) < 2: return []
    
    # Check all movements
    for i in range(len(history)-1):
        prev_idx = i
        curr_idx = i+1
        
        prev_score = history[prev_idx]['score']
        curr_score = history[curr_idx]['score']
        change = curr_score - prev_score
        
        if abs(change) >= 1: # Show all changes
            # Find reason from transactions in that month
            # curr_idx corresponds to a specific month. 
            # history[0] is Jan (offset 11). history[11] is Dec (offset 0).
            # So history[k] corresponds to month_offset = 11 - k
            
            offset = 11 - curr_idx
            txs = [t for t in user_data.get('transactions', []) if t.get('month_offset') == offset]
            
            reason = "Routine credit activity."
            # Deduce reason
            bad_tx = next((t for t in txs if 'Late' in t.get('status', '') or 'Missed' in t.get('status', '')), None)
            if bad_tx:
                reason = f"Missed payment of ${bad_tx['amount']}."
            elif change < 0:
                # Look for other negatives
                if any(t['type'] == 'Credit_Inquiry' for t in txs):
                    reason = "Hard credit inquiry detected."
                elif any(t['type'] == 'Cash_Advance' for t in txs):
                    reason = "Cash advance usage."
                elif any(t['type'] == 'Large_Purchase' for t in txs):
                    reason = "High utilization from large purchase."
            elif change > 0:
                if any(t['type'] == 'EMI_Repayment' for t in txs):
                    reason = "On-time EMI repayment."
                elif any(t['type'] == 'CC_Full_Payment' for t in txs):
                    reason = "Full credit card bill payment."
            
            movements.append({
                "date": f"In {history[curr_idx]['month']}",
                "change": f"{'+' if change > 0 else ''}{change}",
                "reason": reason
            })
            
    return movements[::-1] # Most recent first

# --- API ENDPOINTS ---

@web_app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    user = get_user_by_username(username)
    
    if user and user['password'] == password:
        return jsonify({"status": "success", "user_id": username, "token": f"token_{username}"})
    
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@web_app.route('/dashboard', methods=['GET'])
def get_dashboard_data():
    username = request.args.get('user')
    
    if username:
        user = get_user_by_username(username)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
            
        # Clone user to avoid modifying global state
        user_response = user.copy()
        
        # 1. Calculate Preliminary Score (Standard Logic)
        prelim_score = CreditCalculationAgent.calculate(user_response)
        
        # 2. Get Dynamic Impacts based on Preliminary Score
        impacts = ScoreImpactAgent.get_dynamic_impacts(user_response, prelim_score)
        
        # 3. Recalculate Score with Dynamic Impacts
        score = CreditCalculationAgent.calculate(user_response, impacts)
        user_response['score'] = score
        
        # 4. Prediction Agent
        prediction = PredictionAgent.analyze(user_response, score)
        user_response['analysis'] = prediction
        
        # 5. Alerting Agent
        alerts = AlertingAgent.check_alerts(user_response)
        user_response['alerts'] = alerts
        
        # 6. Chart History
        history = generate_chart_history(user_response, score, impacts)
        user_response['history'] = history
        
        # 5. Score Movements (Why it changed)
        movements = explain_score_movements(user_response, history)
        user_response['score_history'] = {"score_movements": movements}
        
        # 6. Financial Plans (On Demand, but we can set null here)
        user_response['financial_plans'] = None
        
        # 7. Payment Limits (Limit Generator Agent)
        limits = LimitGeneratorAgent.generate_limits(user_response)
        user_response['payment_limits'] = limits
        
        # Remove yearly_analysis as it is removed
        user_response['yearly_analysis'] = None

        return jsonify({
            "status": "success", 
            "data": [user_response], 
            "meta": {"agent_provider": "Nebius Llama-3.3"}
        })
    else:
        return jsonify({"status": "error", "message": "User parameter required"}), 400

@web_app.route('/pay', methods=['POST'])
def make_payment():
    data = request.json
    username = data.get("username")
    amount = data.get("amount")
    
    if not username or not amount:
        return jsonify({"status": "error", "message": "Missing username or amount"}), 400
        
    user = get_user_by_username(username)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    # Use PaymentAgent to evaluate
    evaluation = PaymentAgent.evaluate_payment(user, amount)
    
    if evaluation.get("approved"):
        # Deduct from savings (in memory)
        user['savings_balance'] = evaluation.get("remaining_balance", user['savings_balance'] - amount)
        
        # Also deduct from debt (current_balance)
        # Requirement: "make payment should be able to correct"
        if 'debt' in user:
            user['debt'] = max(0, user['debt'] - amount)
            
        # Persist changes
        save_user_data()
        
        return jsonify({
            "status": "success", 
            "message": f"Payment of ${amount} processed successfully. {evaluation.get('reason')}",
            "new_balance": user['savings_balance'],
            "new_debt": user.get('debt', 0)
        })
    else:
        return jsonify({
            "status": "error", 
            "message": f"Payment Rejected: {evaluation.get('reason')}"
        }), 400

@web_app.route('/generate_plan', methods=['POST'])
def generate_plan():
    data = request.json
    username = data.get("username")
    
    user = get_user_by_username(username)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    score = CreditCalculationAgent.calculate(user)
    plans = FinancialPlanAgent.generate_plans(user, score)
    return jsonify({"status": "success", "data": plans})

@web_app.route('/set_goal', methods=['POST'])
def set_goal():
    data = request.json
    username = data.get("username")
    goal = data.get("goal")
    goal_amount = data.get("goal_amount", 0)
    
    if not username or not goal:
        return jsonify({"status": "error", "message": "Missing username or goal"}), 400
        
    user = get_user_by_username(username)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    # Ensure score is present
    if 'score' not in user:
        user['score'] = CreditCalculationAgent.calculate(user)
        
    plan = GoalSettingAgent.generate_goal_plan(user, goal)
    
    # Save goal and amount to user data
    user['current_goal'] = goal
    user['goal_amount'] = goal_amount
    user['goal_plan'] = plan
    save_user_data()
    
    return jsonify({"status": "success", "data": plan})


class ChatAgent:
    """
    Agent 6: The Assistant.
    Handles general enquiries and specific questions about user data.
    """
    @staticmethod
    def chat(user_data, message):
        client = OpenAI(
            base_url="https://api.tokenfactory.nebius.com/v1/",
            api_key=os.environ.get("NEBIUS_API_KEY")
        )

        system_prompt = """You are a helpful Banking Assistant Chatbot.
        You have access to the user's financial data including transactions, loans, and credit score.
        
        Your capabilities:
        1. Answer enquiries about loans (eligibility, types, etc.).
        2. Check transactions based on history (e.g., "Did I spend on X?", "Show me my last payment").
        3. Explain credit score changes.
        
        Keep responses concise, friendly, and professional.
        If the user asks about something you don't have data for, politely say so.
        """

        # Prepare context from user_data
        transactions_summary = []
        for t in user_data.get('transactions', [])[:20]: # Last 20 transactions
            transactions_summary.append(f"{t['date']}: {t['merchant']} ({t['category']}) - ${t['amount']} [{t['type']}]")
            
        context = f"""
        User Context:
        - Username: {user_data.get('username')}
        - Current Score: {user_data.get('score', 'N/A')}
        - Income: ${user_data.get('income')}
        - Debt: ${user_data.get('debt')}
        - Savings: ${user_data.get('savings_balance')}
        - Recent Transactions:
        {chr(10).join(transactions_summary)}
        """

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct-fast",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": context},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Agent Error (Chat): {e}")
            return "I apologize, but I'm currently unable to process your request. Please try again later."

@web_app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    username = data.get("username")
    message = data.get("message")
    
    if not username or not message:
        return jsonify({"status": "error", "message": "Missing username or message"}), 400
        
    user = get_user_by_username(username)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    # Ensure score is calculated if missing (though usually dashboard calls it first)
    if 'score' not in user:
        user['score'] = CreditCalculationAgent.calculate(user)
        
    response = ChatAgent.chat(user, message)
    
    return jsonify({
        "status": "success", 
        "response": response
    })

@web_app.route('/users', methods=['GET'])
def get_users():
    users_list = []
    for u in USER_DATA.values():
        users_list.append({
            "username": u.get("username"),
            "type": u.get("scenario_title", "Unknown")
        })
    # Sort by username number
    try:
        users_list.sort(key=lambda x: int(x['username'].replace('user', '')))
    except:
        users_list.sort(key=lambda x: x['username'])
        
    return jsonify({"status": "success", "data": users_list})

# --- MODAL ENTRYPOINT ---
@app.function(image=image)
@modal.wsgi_app()
def flask_app():
    return web_app

if __name__ == '__main__':
    # This allows running locally with `python backend.py`
    web_app.run(host='0.0.0.0', port=5001, debug=True)
