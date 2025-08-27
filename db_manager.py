import os
import sqlite3
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Use absolute path in project root for both interview and dashboard
            project_root = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(project_root, 'talentscout_chat.db')
        
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Existing tables...
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            years_experience INTEGER,
            desired_position TEXT,
            current_location TEXT,
            tech_stack TEXT,
            raw_resume_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            current_state TEXT DEFAULT 'INTERVIEW_PREP',
            user_name TEXT,
            candidate_id INTEGER,
            current_question_number INTEGER DEFAULT 0,
            generated_questions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            message_type TEXT,
            message_content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            question_number INTEGER,
            question_text TEXT,
            user_answer TEXT,
            feedback_score REAL,
            feedback_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            email TEXT,
            overall_score REAL,
            technical_score REAL,
            communication_score REAL,
            problem_solving_score REAL,
            key_strengths TEXT,
            areas_for_growth TEXT,
            specific_recommendations TEXT,
            hiring_recommendation TEXT,
            summary_feedback TEXT,
            detailed_analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id)
        )
        ''')
        
        # New table for conversation memory
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            role TEXT,
            content TEXT,
            timestamp REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS manager_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_id INTEGER,
            manager_id TEXT,
            action TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (candidate_id) REFERENCES candidates (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    # Conversation Memory Methods
    def save_conversation_exchange(self, email, user_input, bot_response):
        """Save conversation exchange to memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().timestamp()
        
        cursor.execute('''
        INSERT INTO conversation_memory (email, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (email, 'user', user_input, timestamp))
        
        cursor.execute('''
        INSERT INTO conversation_memory (email, role, content, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (email, 'assistant', bot_response, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_conversation_context(self, email, last_n=6):
        """Get recent conversation context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT role, content, timestamp FROM conversation_memory 
        WHERE email = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (email, last_n))
        
        results = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order
        return [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in reversed(results)]
    
    def get_conversation_exchange_count(self, email):
        """Get number of conversation exchanges"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) FROM conversation_memory 
        WHERE email = ? AND role = 'user'
        ''', (email,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def clear_conversation_memory(self, email):
        """Clear conversation memory for email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversation_memory WHERE email = ?", (email,))
        conn.commit()
        conn.close()
    
    # Enhanced Interview Q&A Methods
    def save_interview_qa_with_feedback(self, email, question_number, question_text, user_answer, feedback_score=None, feedback_text=None):
        """Save interview Q&A with real-time feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO interview_qa (email, question_number, question_text, user_answer, feedback_score, feedback_text)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (email, question_number, question_text, user_answer, feedback_score, feedback_text))
        
        conn.commit()
        conn.close()
    
    def get_interview_qa_with_feedback(self, email):
        """Get all interview Q&A with feedback"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT question_text, user_answer, feedback_score, feedback_text, question_number 
        FROM interview_qa 
        WHERE email = ? 
        ORDER BY question_number ASC
        ''', (email,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'question': r[0], 
            'answer': r[1], 
            'feedback_score': r[2],
            'feedback_text': r[3],
            'question_number': r[4]
        } for r in results]
    
    # Existing methods (keeping the essential ones)...
    def get_conversation_state(self, email):
        """Get current conversation state from database"""
        if not email:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM conversations WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'email': result[1],
                'current_state': result[2],
                'user_name': result[3],
                'candidate_id': result[4],
                'current_question_number': result[5],
                'generated_questions': json.loads(result[6]) if result[6] else [],
                'created_at': result[7],
                'updated_at': result[8]
            }
        return None
    
    def create_or_update_conversation(self, email, state=None, user_name=None, candidate_id=None, question_number=None, generated_questions=None):
        """Create or update conversation state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        existing = self.get_conversation_state(email)
        
        if existing:
            updates = []
            values = []
            
            if state: 
                updates.append("current_state = ?")
                values.append(state)
            if user_name: 
                updates.append("user_name = ?")
                values.append(user_name)
            if candidate_id: 
                updates.append("candidate_id = ?")
                values.append(candidate_id)
            if question_number is not None: 
                updates.append("current_question_number = ?")
                values.append(question_number)
            if generated_questions is not None:
                updates.append("generated_questions = ?")
                values.append(json.dumps(generated_questions))
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(email)
            
            query = f"UPDATE conversations SET {', '.join(updates)} WHERE email = ?"
            cursor.execute(query, values)
        else:
            cursor.execute('''
            INSERT INTO conversations (email, current_state, user_name, candidate_id, current_question_number, generated_questions)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, state or 'INTERVIEW_PREP', user_name, candidate_id, question_number or 0, json.dumps(generated_questions) if generated_questions else None))
        
        conn.commit()
        conn.close()
    
    def save_candidate_to_db(self, candidate_data, resume_text=""):
        """Save candidate information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            tech_stack = candidate_data.get('tech_stack', [])
            if isinstance(tech_stack, list):
                tech_stack_json = json.dumps(tech_stack)
            else:
                tech_stack_json = tech_stack
                
            cursor.execute('''
            INSERT INTO candidates (full_name, email, phone, years_experience, 
                                  desired_position, current_location, tech_stack, raw_resume_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_data.get('full_name', ''),
                candidate_data.get('email', ''),
                candidate_data.get('phone', ''),
                candidate_data.get('years_experience', 0),
                candidate_data.get('desired_position', ''),
                candidate_data.get('current_location', ''),
                tech_stack_json,
                resume_text or ''
            ))
            
            conn.commit()
            candidate_id = cursor.lastrowid
            return candidate_id
        except Exception as e:
            print(f"Error saving to database: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_candidate_data(self, email):
        """Get candidate data by email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM candidates WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'full_name': result[1],
                'email': result[2],
                'phone': result[3],
                'years_experience': result[4],
                'desired_position': result[5],
                'current_location': result[6],
                'tech_stack': result[7],
                'raw_resume_text': result[8],
                'created_at': result[9]
            }
        return None
    
    def save_comprehensive_analysis(self, candidate_id, email, analysis_data):
        """Save comprehensive interview analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM candidate_analysis WHERE email = ?", (email,))
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute('''
                UPDATE candidate_analysis SET
                    overall_score = ?, technical_score = ?, communication_score = ?,
                    problem_solving_score = ?, key_strengths = ?, areas_for_growth = ?,
                    specific_recommendations = ?, hiring_recommendation = ?, 
                    summary_feedback = ?, detailed_analysis = ?
                WHERE email = ?
                ''', (
                    analysis_data.get('overall_score', 0),
                    analysis_data.get('technical_score', 0),
                    analysis_data.get('communication_score', 0),
                    analysis_data.get('problem_solving_score', 0),
                    json.dumps(analysis_data.get('key_strengths', [])),
                    json.dumps(analysis_data.get('areas_for_growth', [])),
                    json.dumps(analysis_data.get('specific_recommendations', [])),
                    analysis_data.get('hiring_recommendation', ''),
                    analysis_data.get('summary_feedback', ''),
                    analysis_data.get('detailed_analysis', ''),
                    email
                ))
            else:
                cursor.execute('''
                INSERT INTO candidate_analysis 
                (candidate_id, email, overall_score, technical_score, communication_score,
                 problem_solving_score, key_strengths, areas_for_growth, specific_recommendations,
                 hiring_recommendation, summary_feedback, detailed_analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    candidate_id, email,
                    analysis_data.get('overall_score', 0),
                    analysis_data.get('technical_score', 0),
                    analysis_data.get('communication_score', 0),
                    analysis_data.get('problem_solving_score', 0),
                    json.dumps(analysis_data.get('key_strengths', [])),
                    json.dumps(analysis_data.get('areas_for_growth', [])),
                    json.dumps(analysis_data.get('specific_recommendations', [])),
                    analysis_data.get('hiring_recommendation', ''),
                    analysis_data.get('summary_feedback', ''),
                    analysis_data.get('detailed_analysis', '')
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving analysis: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_candidate_analysis(self, email):
        """Get comprehensive candidate analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM candidate_analysis WHERE email = ?", (email,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'candidate_id': result[1],
                'email': result[2],
                'overall_score': result[3],
                'technical_score': result[4],
                'communication_score': result[5],
                'problem_solving_score': result[6],
                'key_strengths': result[7],
                'areas_for_growth': result[8],
                'specific_recommendations': result[9],
                'hiring_recommendation': result[10],
                'summary_feedback': result[11],
                'detailed_analysis': result[12],
                'created_at': result[13]
            }
        return None
    
    # Manager Dashboard Methods
    def get_completed_candidates(self):
        """Get all candidates who completed interviews"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT c.* FROM candidates c
        JOIN conversations conv ON c.email = conv.email
        WHERE conv.current_state IN ('REAL_TIME_ANALYSIS', 'POST_INTERVIEW_QA', 'CONVERSATION_TERMINATED')
        ORDER BY c.created_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        candidates = []
        for result in results:
            candidates.append({
                'id': result[0], 'full_name': result[1], 'email': result[2],
                'phone': result[3], 'years_experience': result[4],
                'desired_position': result[5], 'current_location': result[6],
                'tech_stack': result[7], 'raw_resume_text': result[8], 'created_at': result[9]
            })
        
        return candidates
    
    def clear_conversation(self, email):
        """Clear all conversation data for an email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations WHERE email = ?", (email,))
        cursor.execute("DELETE FROM chat_messages WHERE email = ?", (email,))
        cursor.execute("DELETE FROM interview_qa WHERE email = ?", (email,))
        cursor.execute("DELETE FROM conversation_memory WHERE email = ?", (email,))
        
        conn.commit()
        conn.close()
    
    def save_message(self, email, message_type, content):
        """Save chat message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO chat_messages (email, message_type, message_content)
        VALUES (?, ?, ?)
        ''', (email, message_type, content))
        
        conn.commit()
        conn.close()
    
    def get_chat_history(self, email):
        """Get chat history from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT message_type, message_content, timestamp 
        FROM chat_messages 
        WHERE email = ? 
        ORDER BY timestamp ASC
        ''', (email,))
        
        messages = cursor.fetchall()
        conn.close()
        
        return [{'type': msg[0], 'content': msg[1], 'timestamp': msg[2]} for msg in messages]
