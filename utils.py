import PyPDF2
import docx
import streamlit as st
import time
from langchain_community.tools import DuckDuckGoSearchRun

class ResumeProcessor:
    
    @staticmethod
    def extract_text_from_pdf(file):
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return None
    
    @staticmethod
    def extract_text_from_docx(file):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            st.error(f"Error reading DOCX: {str(e)}")
            return None

class SearchManager:
    
    def __init__(self):
        self.search_tool = DuckDuckGoSearchRun()
    
    def search_interview_questions(self, tech_stack, desired_position, experience_level):
        """Search web for relevant interview questions"""
        try:
            # Create search queries
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
    GREETING = "GREETING"
    RESUME_REQUEST = "RESUME_REQUEST" 
    RESUME_PROCESSING = "RESUME_PROCESSING"
    INTERVIEW_PREP = "INTERVIEW_PREP"
    INTERVIEW_ACTIVE = "INTERVIEW_ACTIVE"
    INTERVIEW_END = "INTERVIEW_END"
