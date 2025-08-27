import json
import streamlit as st

class ConversationalAnalyzer:
    def __init__(self, groq_client, db_manager):
        self.groq_client = groq_client
        self.db = db_manager

    def analyze_answer_realtime(self, question, answer, candidate_context):
        """LLM analysis for each answer: encouragement, score, tip."""
        from prompts import PromptsManager
        prompt = PromptsManager.get_real_time_feedback_prompt(question, answer, candidate_context)
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=600
            )
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            st.warning(f"Feedback error: {str(e)}")
            # Fallback
            return {
                "encouraging_feedback": "Nice answer! You gave good technical details.",
                "score": 7.5,
                "key_strength": "Clear technical reasoning",
                "improvement_area": "Consider mentioning edge cases to show depth",
                "confidence_level": "Medium"
            }

    def generate_comprehensive_analysis(self, email, candidate_data, all_qa_pairs, conversation_context):
        """LLM comprehensive analysis on overall interview."""
        from prompts import PromptsManager
        # Get all real-time feedback for this candidate
        feedback_rows = self.db.get_interview_qa_with_feedback(email)
        real_time_feedback = [
            {
                "score": row.get('feedback_score', 0),
                "key_strength": row.get('feedback_text', '').split('.')[0] if row.get('feedback_text') else "",
            }
            for row in feedback_rows
        ]
        prompt = PromptsManager.get_comprehensive_analysis_prompt(
            candidate_data, all_qa_pairs, conversation_context, real_time_feedback
        )
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.15,
                max_tokens=1200,
            )
            analysis = json.loads(response.choices[0].message.content.strip())
            # Save analysis to DB
            self.db.save_comprehensive_analysis(candidate_data['id'], candidate_data['email'], analysis)
            return analysis
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            return None
