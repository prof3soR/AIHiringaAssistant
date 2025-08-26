import sqlite3
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='talentscout_chat.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Candidates table
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
        
        # Conversations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            current_state TEXT DEFAULT 'GREETING',
            user_name TEXT,
            candidate_id INTEGER,
            current_question_number INTEGER DEFAULT 0,
            generated_questions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Chat messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            message_type TEXT,
            message_content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Interview Q&A table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_qa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            question_number INTEGER,
            question_text TEXT,
            user_answer TEXT,
            follow_up_generated BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
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
            # Update existing conversation
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
            # Create new conversation
            cursor.execute('''
            INSERT INTO conversations (email, current_state, user_name, candidate_id, current_question_number, generated_questions)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (email, state or 'GREETING', user_name, candidate_id, question_number or 0, json.dumps(generated_questions) if generated_questions else None))
        
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
    
    def save_candidate_to_db(self, candidate_data, resume_text):
        """Save candidate information to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO candidates (full_name, email, phone, years_experience, 
                                  desired_position, current_location, tech_stack, raw_resume_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                candidate_data['full_name'],
                candidate_data['email'],
                candidate_data['phone'],
                candidate_data['years_experience'],
                candidate_data['desired_position'],
                candidate_data['current_location'],
                json.dumps(candidate_data['tech_stack']),
                resume_text
            ))
            
            conn.commit()
            candidate_id = cursor.lastrowid
            return candidate_id
        except Exception as e:
            print(f"Error saving to database: {str(e)}")
            return None
        finally:
            conn.close()
    
    def update_candidate_info(self, email, field, value):
        """Update specific candidate information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f'''
            UPDATE candidates SET {field} = ? WHERE email = ?
            ''', (value, email))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating candidate info: {str(e)}")
            return False
        finally:
            conn.close()
    
    def save_interview_qa(self, email, question_number, question_text, user_answer):
        """Save interview Q&A to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO interview_qa (email, question_number, question_text, user_answer)
        VALUES (?, ?, ?, ?)
        ''', (email, question_number, question_text, user_answer))
        
        conn.commit()
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
                'tech_stack': json.loads(result[7]) if result[7] else [],
                'raw_resume_text': result[8]
            }
        return None
    
    def clear_conversation(self, email):
        """Clear all conversation data for an email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM conversations WHERE email = ?", (email,))
        cursor.execute("DELETE FROM chat_messages WHERE email = ?", (email,))
        cursor.execute("DELETE FROM interview_qa WHERE email = ?", (email,))
        
        conn.commit()
        conn.close()
        
    def get_interview_qa(self, email):
        """Get all interview Q&A for an email"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT question_text, user_answer FROM interview_qa 
        WHERE email = ? 
        ORDER BY question_number ASC
        ''', (email,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'question': r[0], 'answer': r[1]} for r in results]

    def update_interview_answer(self, email, question_number, new_answer):
        """Update an interview answer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE interview_qa SET user_answer = ? 
        WHERE email = ? AND question_number = ?
        ''', (new_answer, email, question_number))
        
        conn.commit()
        conn.close()
