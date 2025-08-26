import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
from groq import Groq

from db_manager import DatabaseManager
from prompts import PromptsManager
from utils import SearchManager, ConversationStates

load_dotenv()

# Initialize clients
@st.cache_resource
def init_groq_client():
    """Initialize Groq client"""
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

@st.cache_resource
def init_search_manager():
    """Initialize search manager"""
    return SearchManager()

class HiringAssistant:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.groq_client = init_groq_client()
        self.search_manager = init_search_manager()
        self.prompts = PromptsManager()
    
    def generate_custom_questions(self, candidate_data, search_results):
        """Generate customized interview questions"""
        # Parse tech stack safely
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                tech_stack = json.loads(tech_stack_raw)
            except:
                tech_stack = []
        elif isinstance(tech_stack_raw, list):
            tech_stack = tech_stack_raw
        else:
            tech_stack = []
        
        # Create candidate data with parsed tech stack
        candidate_for_prompt = candidate_data.copy()
        candidate_for_prompt['tech_stack'] = tech_stack
        
        question_prompt = self.prompts.get_question_generation_prompt(candidate_for_prompt, search_results)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": question_prompt}],
                temperature=0.3,
                max_tokens=3000
            )
            
            questions_data = json.loads(response.choices[0].message.content.strip())
            return questions_data['questions']
        except Exception as e:
            st.error(f"Error generating questions: {str(e)}")
            # Fallback questions
            return [
                {"id": 1, "question": f"Tell me about your experience with {tech_stack[0] if tech_stack else 'programming'}.", "focus_area": "General"},
                {"id": 2, "question": "Describe a challenging project you've worked on and how you approached it.", "focus_area": "Problem solving"},
                {"id": 3, "question": "How do you handle debugging and troubleshooting in your development process?", "focus_area": "Technical skills"},
                {"id": 4, "question": "What's your approach to learning new technologies and staying updated?", "focus_area": "Learning"},
                {"id": 5, "question": "Where do you see yourself in the next 2 years in terms of career growth?", "focus_area": "Career goals"}
            ]
    
    def generate_context_based_response(self, user_question, email):
        """Generate response based on full interview context"""
        candidate_data = self.db.get_candidate_data(email)
        interview_qa = self.db.get_interview_qa(email)
        conversation_context = self.db.get_chat_history(email)
        
        # Parse tech stack safely for candidate data
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                candidate_data['tech_stack'] = json.loads(tech_stack_raw)
            except:
                candidate_data['tech_stack'] = []
        
        context_prompt = self.prompts.get_context_based_response_prompt(
            user_question, candidate_data, interview_qa, conversation_context
        )
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": context_prompt}],
                temperature=0.4,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your question right now. Our team will be in touch with you soon regarding next steps. Is there anything else I can help you with?"
    
    def process_conversation(self, email, user_input):
        """Main conversation processing logic"""
        conv_state = self.db.get_conversation_state(email)
        
        if not conv_state:
            return "Error: Conversation state not found."
        
        current_state = conv_state['current_state']
        
        # Save user message
        self.db.save_message(email, "user", user_input)
        
        # Process based on current state
        if current_state == ConversationStates.INTERVIEW_ACTIVE:
            return self._handle_interview_answer(email, user_input, conv_state)
        
        elif current_state == ConversationStates.ANSWER_CONFIRMATION:
            return self._handle_answer_confirmation(email, user_input, conv_state)
        
        elif current_state == ConversationStates.FINAL_SUMMARY:
            return self._handle_final_summary(email, user_input, conv_state)
        
        elif current_state == ConversationStates.POST_INTERVIEW_QA:
            return self._handle_post_interview_qa(email, user_input, conv_state)
        
        elif current_state == ConversationStates.CONVERSATION_TERMINATED:
            return self._handle_terminated_state(email, user_input, conv_state)
        
        return "I'm not sure how to help with that. Could you please clarify?"
    
    def _handle_interview_answer(self, email, user_answer, conv_state):
        """Handle interview answers"""
        current_q_num = conv_state['current_question_number']
        generated_questions = conv_state['generated_questions']
        
        # Get current question
        if generated_questions and current_q_num <= len(generated_questions):
            current_question = generated_questions[current_q_num - 1]['question']
        else:
            current_question = "Previous question"
        
        # Save the answer
        self.db.save_interview_qa(email, current_q_num, current_question, user_answer)
        
        # Check if we've asked all questions (5)
        if current_q_num >= 5:
            # Move to answer confirmation
            self.db.create_or_update_conversation(email, ConversationStates.ANSWER_CONFIRMATION)
            
            response = f"Great job, {conv_state['user_name']}! You've answered all 5 questions. 🎉\n\nBefore we conclude, would you like to review or edit any of your answers?\n\nType **'review'** to see all your answers, **'edit [question number]'** to modify a specific answer (e.g., 'edit 3'), or **'done'** if you're satisfied with your responses."
            
            self.db.save_message(email, "assistant", response)
            return response
        
        else:
            # Move to next question
            next_q_num = current_q_num + 1
            
            if generated_questions and next_q_num <= len(generated_questions):
                next_question = generated_questions[next_q_num - 1]['question']
                response = f"Great answer! 👍\n\n**Question {next_q_num}:**\n{next_question}"
            else:
                response = f"Thank you for your answer! 👍\n\n**Question {next_q_num}:**\nTell me about a time you had to solve a complex technical problem. What was your approach?"
            
            # Update question number
            self.db.create_or_update_conversation(email, question_number=next_q_num)
            self.db.save_message(email, "assistant", response)
            return response
    
    def _handle_answer_confirmation(self, email, user_input, conv_state):
        """Handle answer confirmation and editing"""
        user_input_lower = user_input.lower().strip()
        
        if "review" in user_input_lower:
            # Show all Q&As
            qa_pairs = self.db.get_interview_qa(email)
            review_text = f"📋 **Your Interview Responses:**\n\n"
            
            for i, qa in enumerate(qa_pairs, 1):
                review_text += f"**Q{i}:** {qa['question']}\n"
                review_text += f"**A{i}:** {qa['answer']}\n\n"
            
            response = review_text + "Would you like to edit any answer? Type **'edit [number]'** (e.g., 'edit 2') or **'done'** if satisfied."
            self.db.save_message(email, "assistant", response)
            return response
        
        elif "edit" in user_input_lower and any(str(i) in user_input for i in range(1, 6)):
            # Handle editing specific question
            q_num = next((i for i in range(1, 6) if str(i) in user_input), 1)
            qa_pairs = self.db.get_interview_qa(email)
            
            if q_num <= len(qa_pairs):
                question = qa_pairs[q_num-1]['question']
                response = f"**Question {q_num}:** {question}\n\n**Your current answer:** {qa_pairs[q_num-1]['answer']}\n\nPlease provide your new answer:"
                
                # Store the question number being edited
                self.db.create_or_update_conversation(email, question_number=q_num)
                self.db.save_message(email, "assistant", response)
                return response
        
        elif "done" in user_input_lower:
            # Move to final summary
            self.db.create_or_update_conversation(email, ConversationStates.FINAL_SUMMARY)
            return self._show_final_summary(email, conv_state)
        
        else:
            # This might be a new answer for editing
            current_q_num = conv_state['current_question_number']
            if current_q_num > 0:
                # Update the answer
                self.db.update_interview_answer(email, current_q_num, user_input)
                response = f"Perfect! I've updated your answer for Question {current_q_num}.\n\nAnything else to edit? Type **'edit [number]'**, **'review'** to see all answers, or **'done'** to finish."
                self.db.save_message(email, "assistant", response)
                return response
        
        response = "I'm not sure what you'd like to do. Type **'review'** to see your answers, **'edit [number]'** to edit a specific answer, or **'done'** to finish."
        self.db.save_message(email, "assistant", response)
        return response
    
    def _show_final_summary(self, email, conv_state):
        """Show final summary of all Q&As"""
        candidate_data = self.db.get_candidate_data(email)
        qa_pairs = self.db.get_interview_qa(email)
        
        # Parse tech stack safely
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                tech_stack = json.loads(tech_stack_raw)
            except:
                tech_stack = []
        elif isinstance(tech_stack_raw, list):
            tech_stack = tech_stack_raw
        else:
            tech_stack = []
        
        tech_stack_str = ", ".join(tech_stack) if tech_stack else "Not specified"
        
        summary = f"""🎉 **Interview Complete!** Thank you, {conv_state['user_name']}!

📊 **Your Profile Summary:**
• **Position:** {candidate_data['desired_position']}
• **Experience:** {candidate_data['years_experience']} years  
• **Tech Stack:** {tech_stack_str}
• **Location:** {candidate_data['current_location']}

📋 **Your Complete Interview Responses:**

"""
        
        for i, qa in enumerate(qa_pairs, 1):
            summary += f"**Q{i}:** {qa['question']}\n"
            summary += f"**A{i}:** {qa['answer']}\n\n"
        
        summary += """🚀 **Next Steps:**
• Our technical team will review your responses
• We'll evaluate your answers against our requirements  
• You'll hear back from us within 2-3 business days
• If selected, we'll schedule a detailed technical interview

Thank you for your time and interest! We appreciate the effort you put into this assessment.

💬 **Have any questions?** Feel free to ask me anything about the process, timeline, or next steps! 
Or say **'goodbye'** when you're ready to end our conversation. 👋"""
        
        self.db.save_message(email, "assistant", summary)
        self.db.create_or_update_conversation(email, ConversationStates.POST_INTERVIEW_QA)
        return summary
    
    def _handle_final_summary(self, email, user_input, conv_state):
        """Handle final summary state"""
        return self._show_final_summary(email, conv_state)
    
    def _handle_post_interview_qa(self, email, user_input, conv_state):
        """Handle post-interview questions using full context"""
        # Check for termination keywords first
        ending_keywords = ["thank you", "goodbye", "bye", "thanks", "end", "finish", "done", "exit", "quit"]
        if any(keyword in user_input.lower() for keyword in ending_keywords):
            self.db.create_or_update_conversation(email, ConversationStates.CONVERSATION_TERMINATED)
            
            response = f"Thank you for your time, {conv_state['user_name']}! 🙏\n\nYour interview has been completed and recorded. Our team will review your responses and get back to you soon.\n\nWe appreciate your interest in joining our team. Have a great day! ✨\n\n*This conversation has ended. You can close this window.*"
            self.db.save_message(email, "assistant", response)
            return response
        
        # Generate context-based response
        response = self.generate_context_based_response(user_input, email)
        
        # Add helpful reminder
        response += f"\n\nAnything else you'd like to know? Feel free to ask, or say **'goodbye'** when you're ready to end our conversation."
        
        self.db.save_message(email, "assistant", response)
        return response
    
    def _handle_terminated_state(self, email, user_input, conv_state):
        """Handle terminated conversation state - should not be reached if UI hides chat"""
        response = "This conversation has ended. Thank you for your time!"
        self.db.save_message(email, "assistant", response)
        return response
    
    def prepare_interview_questions(self, email):
        """Prepare and store interview questions"""
        candidate_data = self.db.get_candidate_data(email)
        
        if not candidate_data:
            return False
        
        # Parse tech stack safely
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                tech_stack = json.loads(tech_stack_raw)
            except:
                tech_stack = []
        elif isinstance(tech_stack_raw, list):
            tech_stack = tech_stack_raw
        else:
            tech_stack = []
        
        # Search for questions
        search_results = self.search_manager.search_interview_questions(
            tech_stack,
            candidate_data['desired_position'], 
            candidate_data['years_experience']
        )
        
        # Generate custom questions
        questions = self.generate_custom_questions(candidate_data, search_results)
        
        # Store questions in conversation
        self.db.create_or_update_conversation(
            email, 
            ConversationStates.INTERVIEW_ACTIVE, 
            question_number=1, 
            generated_questions=questions
        )
        
        # Start with first question
        first_question = questions[0]['question'] if questions else "Tell me about your programming experience."
        
        interview_start = f"""Excellent! I've prepared 5 technical questions tailored to your background. 🎯

Let's begin your technical assessment.

**Question 1:**
{first_question}

Take your time to provide a detailed answer!"""
        
        self.db.save_message(email, "assistant", interview_start)
        return interview_start

# Streamlit UI
def main():
    st.set_page_config(
        page_title="🎯 TalentScout - AI Hiring Assistant",
        page_icon="🎯",
        layout="wide"
    )
    
    # Custom CSS for chat interface
    st.markdown("""
    <style>
    .main > div {
        padding-top: 1rem;
    }
    .stChatMessage {
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .chat-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .info-form {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
    .conversation-ended {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
        color: #155724;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize assistant
    assistant = HiringAssistant()
    
    # Header
    st.markdown("""
    <div class="chat-header">
        <h1>🎯 TalentScout AI Hiring Assistant</h1>
        <p>Intelligent Technical Screening for Technology Positions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Email input for session management
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
        st.session_state.form_submitted = False
    
    if not st.session_state.user_email:
        with st.form("email_form"):
            st.write("**Please enter your email to start:**")
            email_input = st.text_input("Email Address", placeholder="your.email@example.com")
            submit_email = st.form_submit_button("Start Interview")
            
            if submit_email and email_input:
                if "@" in email_input and "." in email_input:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")
        return
    
    email = st.session_state.user_email
    
    # Check if conversation exists
    conv_state = assistant.db.get_conversation_state(email)
    
    # If no conversation exists and form not submitted, show information form
    if not conv_state and not st.session_state.form_submitted:
        st.markdown('<div class="info-form">', unsafe_allow_html=True)
        st.markdown("## 📋 Candidate Information")
        st.markdown("Please fill out the form below to get started with your technical interview.")
        
        with st.form("candidate_info_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name *", placeholder="John Doe")
                desired_position = st.text_input("Desired Position *", placeholder="AI Engineer, Software Developer, etc.")
                years_experience = st.number_input("Years of Experience", min_value=0, max_value=50, value=0)
            
            with col2:
                phone = st.text_input("Phone Number", placeholder="+1-234-567-8900")
                current_location = st.text_input("Current Location", placeholder="City, State/Country")
            
            tech_stack_input = st.text_area(
                "Technical Skills & Tech Stack *", 
                placeholder="List your technical skills separated by commas\nExample: Python, JavaScript, React, Django, MySQL, AWS, Docker",
                height=100
            )
            
            submit_info = st.form_submit_button("🚀 Start Technical Interview", type="primary")
            
            if submit_info:
                # Validate required fields
                if not full_name or not desired_position or not tech_stack_input:
                    st.error("Please fill in all required fields marked with *")
                else:
                    # Parse tech stack
                    tech_stack = [tech.strip() for tech in tech_stack_input.split(',') if tech.strip()]
                    
                    # Prepare candidate data with JSON string for tech_stack
                    candidate_data = {
                        'full_name': full_name.strip(),
                        'email': email,
                        'phone': phone.strip() if phone else "Not provided",
                        'years_experience': years_experience,
                        'desired_position': desired_position.strip(),
                        'current_location': current_location.strip() if current_location else "Not provided",
                        'tech_stack': json.dumps(tech_stack)  # Convert to JSON string
                    }
                    
                    # Save to database
                    candidate_id = assistant.db.save_candidate_to_db(candidate_data, "")
                    
                    if candidate_id:
                        # Create conversation
                        assistant.db.create_or_update_conversation(
                            email, 
                            ConversationStates.INTERVIEW_PREP, 
                            full_name, 
                            candidate_id
                        )
                        
                        # Show welcome message
                        welcome_message = f"👋 Hello {full_name}! Welcome to TalentScout AI.\n\nI've received your information and I'm now preparing customized technical questions based on your profile:\n\n📊 **Your Profile:**\n• Position: {desired_position}\n• Experience: {years_experience} years\n• Tech Stack: {', '.join(tech_stack)}\n• Location: {current_location or 'Not provided'}\n\nPlease wait while I generate your personalized interview questions..."
                        assistant.db.save_message(email, "assistant", welcome_message)
                        
                        st.session_state.form_submitted = True
                        st.success("✅ Information saved! Preparing your interview questions...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("There was an error saving your information. Please try again.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # If conversation exists or form submitted, show chat interface
    if not conv_state and st.session_state.form_submitted:
        # This means form was just submitted, get the new conversation state
        conv_state = assistant.db.get_conversation_state(email)
    
    if conv_state:
        # Display conversation history
        chat_history = assistant.db.get_chat_history(email)
        
        # Create chat container
        for message in chat_history:
            with st.chat_message(message['type']):
                st.write(message['content'])
        
        # Handle interview preparation
        if conv_state['current_state'] == ConversationStates.INTERVIEW_PREP:
            with st.spinner('🔍 Searching for relevant interview questions...'):
                interview_start = assistant.prepare_interview_questions(email)
                
                if interview_start:
                    with st.chat_message("assistant"):
                        st.write(interview_start)
                    
                    # Force refresh to update state
                    st.rerun()
        
        # Show conversation ended message if terminated
        if conv_state['current_state'] == ConversationStates.CONVERSATION_TERMINATED:
            st.markdown("""
            <div class="conversation-ended">
                <h3>✅ Conversation Ended</h3>
                <p>Thank you for completing the interview! You can now close this window.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Chat input - Only show during active conversation states (HIDE when terminated)
        if conv_state['current_state'] in [
            ConversationStates.INTERVIEW_ACTIVE, 
            ConversationStates.ANSWER_CONFIRMATION, 
            ConversationStates.FINAL_SUMMARY,
            ConversationStates.POST_INTERVIEW_QA  # NEW: Allow chat in post-interview Q&A
            # NOTE: CONVERSATION_TERMINATED is NOT included - chat input hidden
        ]:
            if prompt := st.chat_input("Type your message here..."):
                # Display user message
                with st.chat_message("user"):
                    st.write(prompt)
                
                # Process conversation
                with st.spinner('Thinking...'):
                    response = assistant.process_conversation(email, prompt)
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.write(response)
                
                # Force refresh for state changes
                st.rerun()
        
        # Sidebar with conversation info
        with st.sidebar:
            st.markdown("### 🎯 Interview Status")
            
            if conv_state:
                candidate_data = assistant.db.get_candidate_data(email)
                if candidate_data:
                    st.write(f"**Candidate:** {candidate_data['full_name']}")
                    st.write(f"**Position:** {candidate_data['desired_position']}")
                    st.write(f"**Experience:** {candidate_data['years_experience']} years")
                
                # Show user-friendly status
                status_display = {
                    ConversationStates.INTERVIEW_PREP: "Preparing Questions",
                    ConversationStates.INTERVIEW_ACTIVE: "Technical Interview",
                    ConversationStates.ANSWER_CONFIRMATION: "Answer Review",
                    ConversationStates.FINAL_SUMMARY: "Interview Summary",
                    ConversationStates.POST_INTERVIEW_QA: "Post-Interview Q&A",
                    ConversationStates.CONVERSATION_TERMINATED: "Completed ✓"
                }
                
                st.write(f"**Status:** {status_display.get(conv_state['current_state'], conv_state['current_state'])}")
                st.write(f"**Questions Asked:** {conv_state['current_question_number']}")
                if conv_state['generated_questions']:
                    st.write(f"**Total Questions:** {len(conv_state['generated_questions'])}")
            
            if st.button("🔄 Start New Interview"):
                assistant.db.clear_conversation(email)
                st.session_state.user_email = None
                st.session_state.form_submitted = False
                st.rerun()

if __name__ == "__main__":
    main()
