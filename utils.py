import streamlit as st
import time
from langchain_community.tools import DuckDuckGoSearchRun

class SearchManager:
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()
    
    def search_interview_questions(self, tech_stack, desired_position, experience_level):
        """Search web for relevant interview questions"""
        try:
            tech_str = ", ".join(tech_stack[:3])  # Top 3 technologies
            
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
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    st.warning(f"Search failed for: {query}")
                    continue
            
            return "\n".join(all_results)
        except Exception as e:
            st.error(f"Error searching for questions: {str(e)}")
            return ""

class ConversationStates:
    INTERVIEW_PREP = "INTERVIEW_PREP"
    INTERVIEW_ACTIVE = "INTERVIEW_ACTIVE"
    ANSWER_CONFIRMATION = "ANSWER_CONFIRMATION"
    FINAL_SUMMARY = "FINAL_SUMMARY"
    POST_INTERVIEW_QA = "POST_INTERVIEW_QA"  # NEW STATE
    CONVERSATION_TERMINATED = "CONVERSATION_TERMINATED"  # NEW STATE
