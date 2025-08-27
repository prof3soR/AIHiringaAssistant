import streamlit as st
import time
from langchain_community.tools import DuckDuckGoSearchRun

class SearchManager:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()
    
    def search_interview_questions(self, tech_stack, desired_position, experience_level):
        """Search web for relevant interview questions"""
        try:
            tech_str = ", ".join(tech_stack[:3])
            
            queries = [
                f"{desired_position} interview questions {tech_str}",
                f"entry level {tech_str} interview questions" if experience_level == 0 else f"{tech_str} interview questions {experience_level} years experience",
                f"technical questions {desired_position} {tech_str}"
            ]
            
            all_results = []
            for query in queries:
                try:
                    results = self.search_tool.run(query)
                    all_results.append(results)
                    time.sleep(1)
                except Exception as e:
                    st.warning(f"Search failed for: {query}")
                    continue
            
            return "\n".join(all_results)
        except Exception as e:
            st.error(f"Error searching for questions: {str(e)}")
            return ""

class ConversationStates:
    INTERVIEW_PREP = "INTERVIEW_PREP"
    CONVERSATIONAL_INTRO = "CONVERSATIONAL_INTRO"
    DYNAMIC_INTERVIEW = "DYNAMIC_INTERVIEW"
    REAL_TIME_ANALYSIS = "REAL_TIME_ANALYSIS"
    POST_INTERVIEW_QA = "POST_INTERVIEW_QA"
    CONVERSATION_TERMINATED = "CONVERSATION_TERMINATED"

class ConversationMemory:
    def __init__(self):
        self.memory = {}
    
    def add_exchange(self, email, user_input, bot_response):
        """Add conversation exchange to memory"""
        if email not in self.memory:
            self.memory[email] = []
        
        self.memory[email].extend([
            {'role': 'user', 'content': user_input, 'timestamp': time.time()},
            {'role': 'assistant', 'content': bot_response, 'timestamp': time.time()}
        ])
    
    def get_context(self, email, last_n=6):
        """Get recent conversation context"""
        if email not in self.memory:
            return []
        
        return self.memory[email][-last_n:] if len(self.memory[email]) > last_n else self.memory[email]
    
    def get_exchange_count(self, email):
        """Get number of exchanges (pairs of user/bot messages)"""
        if email not in self.memory:
            return 0
        return len(self.memory[email]) // 2
    
    def clear_memory(self, email):
        """Clear conversation memory for email"""
        if email in self.memory:
            del self.memory[email]

class ScoreCalculator:
    @staticmethod
    def calculate_overall_score(technical_score, communication_score, problem_solving_score):
        """Calculate weighted overall score"""
        return round((technical_score * 0.4) + (communication_score * 0.3) + (problem_solving_score * 0.3), 1)
    
    @staticmethod
    def get_performance_level(score):
        """Get performance level description"""
        if score >= 8:
            return "Excellent"
        elif score >= 6:
            return "Good"
        elif score >= 4:
            return "Average"
        else:
            return "Needs Improvement"
