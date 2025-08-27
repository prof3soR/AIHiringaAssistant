# Hiring Assistant Chatbot 🤖

## 📌 Project Overview
The **Hiring Assistant Chatbot** is an AI-powered recruitment tool that simplifies the candidate screening process. It interactively gathers candidate details, asks technical and HR-related questions, stores responses in a database, and provides a manager dashboard for evaluation.  

Key features include:
- AI-driven candidate conversations.  
- Technical + HR question generation via prompt design.  
- Candidate response storage using SQLite.  
- Manager dashboard for reviewing applicants.  

![Chatbot Demo](/demo/sample.png)  


## ⚙️ Installation Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/hiring-assistant-chatbot.git
cd hiring-assistant-chatbot
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies
This project uses `pyproject.toml` for dependency management.  

Option A – Install via pip:
```bash
pip install -r requirements.txt
```

Option B – Install via uv (recommended):
```bash
uv sync
```

### 4. Database Setup
The application uses **SQLite** (`talentscout_chat.db`) for storing candidate responses.  
To initialize/reset the database:
```bash
python db_manager.py --init
```

### 5. Run the Application
Start the chatbot:
```bash
streamlit run main.py
```

![Dashboard Demo](demo/dashboard.png)  


---

## 🚀 Usage Guide

1. **Candidate Side**
   - The chatbot will introduce itself and ask for personal details.  
   - It will generate **technical and HR questions** dynamically.  
   - All answers are logged into the database.  

2. **Manager Side**
   - View candidate responses, filter by skill/experience, and analyze interview results.  
   - Use exported reports for hiring decisions.  

---

## 🛠️ Technical Details

### 📂 Core Files
- **`main.py`** – Entry point for candidate-chatbot interaction.  
- **`analysis_engine.py`** – Analysis of candidate answers.  
- **`db_manager.py`** – SQLite database utilities.  
- **`prompts.py`** – Prompt templates for candidate conversations.  
- **`utils.py`** – Helper functions (data cleaning, parsing, etc.).  
- **`talentscout_chat.db`** – SQLite database file.  

### 🧰 Libraries & Tools
- **LangChain** – LLM orchestration and prompt handling.  
- **SQLite3** – Lightweight relational database.  
- **Streamlit** – For serving and dashboards.  
- **Groq could Model** – openai/gpt-oss-20b.


---

## ✍️ Prompt Design

Prompts in `prompts.py` were engineered to:
- Collect structured candidate information.  
- Generate domain-specific **technical questions**.  
- Ask **behavioral and HR questions**.  
- Adjust flow based on candidate responses.  

Example prompt categories:
- Candidate introduction.  
- Technical depth checks.  
- HR / cultural fit questions.  
- Closing conversation.  

---

## ⚡ Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Handling unstructured candidate responses | Normalized inputs and regex-based parsing in `utils.py`. |
| Maintaining structured storage with dynamic prompts | Modular database schema in `db_manager.py`. |
| Balancing technical & HR prompts | Iterative tuning of `prompts.py` templates. |
| Scaling for multiple candidates | Built `manager_dashboard.py` to manage and visualize multiple sessions. |

---

## 📊 Future Improvements
- Voice-based interview support.  
- Real-time candidate scoring system.  
- ATS integration (export to HR platforms).  
- Deploy as a SaaS web application.  

---


---

## 🙌 Acknowledgements
Thanks to open-source tools like **LangChain**, **SQLite**, and the Python ecosystem for making this project possible.  
