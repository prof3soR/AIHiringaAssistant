import streamlit as st
import json
import os
from dotenv import load_dotenv
from groq import Groq

from db_manager import DatabaseManager
from prompts import PromptsManager
from utils import ResumeProcessor, SearchManager, ConversationStates

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
        self.resume_processor = ResumeProcessor()
        self.prompts = PromptsManager()
    
    def extract_candidate_info_with_rag(self, resume_text):
        """Use Groq to extract structured information from resume"""
        extraction_prompt = self.prompts.get_resume_extraction_prompt(resume_text)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            extracted_info = json.loads(response.choices[0].message.content.strip())
            return extracted_info
        except Exception as e:
            st.error(f"Error extracting information: {str(e)}")
            return None
    
    def generate_custom_questions(self, candidate_data, search_results):
        """Generate customized interview questions"""
        question_prompt = self.prompts.get_question_generation_prompt(candidate_data, search_results)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": question_prompt}],
                temperature=0.3,
                max_tokens=3000  # Increased for complete questions
            )
            
            questions_data = json.loads(response.choices[0].message.content.strip())
            return questions_data['questions']
        except Exception as e:
            st.error(f"Error generating questions: {str(e)}")
            # Fallback questions
            return [
                {"id": 1, "question": f"Tell me about your experience with {candidate_data['tech_stack'][0] if candidate_data['tech_stack'] else 'programming'}.", "focus_area": "General"},
                {"id": 2, "question": "Describe a challenging project you've worked on and how you approached it.", "focus_area": "Problem solving"},
                {"id": 3, "question": "How do you handle debugging and troubleshooting in your development process?", "focus_area": "Technical skills"},
                {"id": 4, "question": "What's your approach to learning new technologies and staying updated?", "focus_area": "Learning"},
                {"id": 5, "question": "Where do you see yourself in the next 2 years in terms of career growth?", "focus_area": "Career goals"}
            ]
    
    def generate_follow_up_question(self, previous_qa, candidate_data):
        """Generate follow-up question based on previous answer"""
        follow_up_prompt = self.prompts.get_follow_up_prompt(previous_qa, candidate_data)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": follow_up_prompt}],
                temperature=0.4,
                max_tokens=500  # Increased for complete questions
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.warning(f"Error generating follow-up: {str(e)}")
            return None
    
    def parse_information_update(self, user_input, current_info):
        """Parse user input for information updates"""
        update_prompt = self.prompts.get_information_update_prompt(user_input, current_info)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": update_prompt}],
                temperature=0.1,
                max_tokens=200
            )
            
            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            return {"action": "confirm"}  # Default to confirm if parsing fails
    
    def process_conversation(self, email, user_input):
        """Main conversation processing logic"""
        conv_state = self.db.get_conversation_state(email)
        
        if not conv_state:
            return "Error: Conversation state not found."
        
        current_state = conv_state['current_state']
        
        # Save user message
        self.db.save_message(email, "user", user_input)
        
        # Process based on current state
        if current_state == ConversationStates.GREETING:
            return self._handle_greeting(email, user_input)
        
        elif current_state == ConversationStates.RESUME_REQUEST:
            return self._handle_resume_request()
        
        elif current_state == ConversationStates.RESUME_PROCESSING:
            return self._handle_resume_processing(email, user_input, conv_state)
        
        elif current_state == ConversationStates.INTERVIEW_ACTIVE:
            return self._handle_interview_answer(email, user_input, conv_state)
        
        elif current_state == ConversationStates.INTERVIEW_END:
            return self._handle_interview_end(email, user_input, conv_state)
        
        return "I'm not sure how to help with that. Could you please clarify?"
    
    def _handle_greeting(self, email, user_input):
        """Handle greeting state"""
        user_name = user_input.strip()
        self.db.create_or_update_conversation(email, ConversationStates.RESUME_REQUEST, user_name)
        
        response = f"Nice to meet you, {user_name}! 😊\n\nTo better understand your background and skills, I'd like you to upload your resume. This will help me ask you more relevant technical questions.\n\nPlease upload your resume using the file uploader below (PDF or DOCX format)."
        self.db.save_message(email, "assistant", response)
        return response
    
    def _handle_resume_request(self):
        """Handle resume request state"""
        response = "I'm still waiting for your resume upload. Please use the file uploader below to share your resume in PDF or DOCX format."
        return response
    
    def _handle_resume_processing(self, email, user_input, conv_state):
        """Handle resume processing state with better update handling"""
        candidate_data = self.db.get_candidate_data(email)
        
        if not candidate_data:
            return "I couldn't find your candidate data. Please upload your resume again."
        
        # Parse the user input to see if they want to update something
        update_info = self.parse_information_update(user_input, candidate_data)
        
        if update_info.get("action") == "update":
            field = update_info.get("field")
            value = update_info.get("value")
            
            if field and value:
                # Update the database
                success = self.db.update_candidate_info(email, field, value)
                if success:
                    response = f"Great! I've updated your {field} to: {value}\n\nIs all the information correct now? Please type 'yes' to confirm or let me know if you need any other changes."
                else:
                    response = "I had trouble updating that information. Please try again or type 'yes' to proceed with the current information."
                
                self.db.save_message(email, "assistant", response)
                return response
        
        elif "yes" in user_input.lower() or "correct" in user_input.lower() or "confirm" in user_input.lower():
            self.db.create_or_update_conversation(email, ConversationStates.INTERVIEW_PREP)
            
            response = f"Perfect! Thank you for confirming, {conv_state['user_name']}! 🎯\n\nNow I'm going to search for relevant technical questions based on your profile and conduct a quick technical assessment. This will take just a moment..."
            self.db.save_message(email, "assistant", response)
            return response
        
        else:
            response = "I'm not sure what you'd like to update. You can say something like 'update my location to Mumbai' or 'change my phone number to +91-9876543210', or just type 'yes' if everything is correct."
            self.db.save_message(email, "assistant", response)
            return response
    
    def _handle_interview_answer(self, email, user_answer, conv_state):
        """Handle interview answers with better question management"""
        current_q_num = conv_state['current_question_number']
        generated_questions = conv_state['generated_questions']
        
        # Get current question
        if generated_questions and current_q_num <= len(generated_questions):
            current_question = generated_questions[current_q_num - 1]['question']
        else:
            current_question = "Previous question"
        
        # Save the answer
        self.db.save_interview_qa(email, current_q_num, current_question, user_answer)
        
        # Check if we've asked enough questions (5)
        if current_q_num >= 5:
            # End interview
            self.db.create_or_update_conversation(email, ConversationStates.INTERVIEW_END)
            
            conclusion_response = f"""
            Excellent! Thank you for answering all the questions, {conv_state['user_name']}! 🎉
            
            📋 **Interview Summary:**
            You've successfully completed the technical assessment covering various aspects of your expertise. 
            
            🚀 **Next Steps:**
            • Our technical team will review your responses
            • We'll evaluate your answers against our requirements  
            • You'll hear back from us within 2-3 business days
            • If selected, we'll schedule a detailed technical interview
            
            Thank you for your time and interest! We appreciate the effort you put into this assessment. 
            
            Feel free to say goodbye or ask any questions about the process! 👋
            """
            
            self.db.save_message(email, "assistant", conclusion_response)
            return conclusion_response
        
        else:
            # Move to next question
            next_q_num = current_q_num + 1
            
            if generated_questions and next_q_num <= len(generated_questions):
                # Use pre-generated question
                next_question = generated_questions[next_q_num - 1]['question']
                response = f"Great answer! 👍\n\n**Question {next_q_num}:**\n{next_question}"
            else:
                # Generate follow-up or use fallback
                candidate_data = self.db.get_candidate_data(email)
                follow_up = self.generate_follow_up_question({
                    'question': current_question,
                    'answer': user_answer
                }, candidate_data)
                
                if follow_up and len(user_answer.strip()) > 20:
                    response = f"Great answer! 👍\n\n**Follow-up Question {next_q_num}:**\n{follow_up}"
                else:
                    response = f"Thank you for your answer! 👍\n\n**Question {next_q_num}:**\nTell me about a time you had to solve a complex technical problem. What was your approach and what tools did you use?"
            
            # Update question number
            self.db.create_or_update_conversation(email, question_number=next_q_num)
            self.db.save_message(email, "assistant", response)
            return response
    
    def _handle_interview_end(self, email, user_input, conv_state):
        """Handle interview end state"""
        ending_keywords = ["thank you", "goodbye", "bye", "thanks", "end", "finish", "done"]
        if any(keyword in user_input.lower() for keyword in ending_keywords):
            response = f"Thank you for your time, {conv_state['user_name']}! 🙏\n\nYour responses have been recorded and our team will review them. We'll be in touch soon regarding next steps.\n\nHave a great day!"
            self.db.save_message(email, "assistant", response)
            return response
        else:
            response = "Is there anything else you'd like to know about the process or do you have any questions for me?"
            self.db.save_message(email, "assistant", response)
            return response
    
    def handle_resume_upload(self, uploaded_file, email):
        """Process uploaded resume and update conversation state"""
        
        # Extract text from resume
        if uploaded_file.type == "application/pdf":
            resume_text = self.resume_processor.extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            resume_text = self.resume_processor.extract_text_from_docx(uploaded_file)
        else:
            return "Sorry, I can only process PDF and DOCX files. Please upload your resume in one of these formats."
        
        if not resume_text:
            return "I had trouble reading your resume. Could you try uploading it again?"
        
        # Extract candidate information
        extracted_data = self.extract_candidate_info_with_rag(resume_text)
        
        if not extracted_data:
            return "I had trouble processing your resume. Could you try uploading it again or check if the file is readable?"
        
        # Update email in extracted data
        extracted_data['email'] = email
        
        # Save candidate data
        candidate_id = self.db.save_candidate_to_db(extracted_data, resume_text)
        
        if candidate_id:
            # Update conversation state
            self.db.create_or_update_conversation(email, ConversationStates.RESUME_PROCESSING, candidate_id=candidate_id)
            
            # Create confirmation message
            tech_stack_str = ", ".join(extracted_data['tech_stack']) if extracted_data['tech_stack'] else "Not specified"
            
            confirmation = f"""
            Perfect! I've processed your resume. Here's what I extracted:
            
            📝 **Your Information:**
            • **Name:** {extracted_data['full_name']}
            • **Email:** {extracted_data['email']}
            • **Phone:** {extracted_data['phone']}
            • **Experience:** {extracted_data['years_experience']} years
            • **Desired Position:** {extracted_data['desired_position']}
            • **Location:** {extracted_data['current_location']}
            • **Tech Stack:** {tech_stack_str}
            
            Is this information correct? Please type 'yes' to confirm, or let me know what needs to be updated (e.g., "update my location to Mumbai").
            """
            
            self.db.save_message(email, "assistant", confirmation)
            return confirmation
        else:
            return "I had an issue saving your information. Could you try again?"
    
    def prepare_interview_questions(self, email):
        """Prepare and store interview questions"""
        candidate_data = self.db.get_candidate_data(email)
        
        if not candidate_data:
            return False
        
        # Search for questions
        search_results = self.search_manager.search_interview_questions(
            candidate_data['tech_stack'],
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
        
        interview_start = f"""
        Excellent! I've prepared some technical questions tailored to your background. 🎯
        
        Let's begin your technical assessment. I'll ask you 5 questions covering different aspects of your expertise.
        
        **Question 1:**
        {first_question}
        
        Take your time to provide a detailed answer!
        """
        
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
    
    if not st.session_state.user_email:
        with st.form("email_form"):
            st.write("**Please enter your email to start the conversation:**")
            email_input = st.text_input("Email Address", placeholder="your.email@example.com")
            submit_email = st.form_submit_button("Start Conversation")
            
            if submit_email and email_input:
                if "@" in email_input and "." in email_input:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")
        return
    
    email = st.session_state.user_email
    
    # Initialize conversation if it doesn't exist
    conv_state = assistant.db.get_conversation_state(email)
    if not conv_state:
        # Create new conversation and show initial greeting
        assistant.db.create_or_update_conversation(email, ConversationStates.GREETING)
        greeting_message = "👋 Hello! I'm TalentScout AI, your intelligent hiring assistant. I'm here to help evaluate your technical skills for potential job opportunities.\n\nTo get started, could you please tell me your name?"
        assistant.db.save_message(email, "assistant", greeting_message)
        conv_state = assistant.db.get_conversation_state(email)
    
    # Display conversation history
    chat_history = assistant.db.get_chat_history(email)
    
    # Create chat container
    chat_container = st.container()
    
    with chat_container:
        for message in chat_history:
            with st.chat_message(message['type']):
                st.write(message['content'])
    
    # Resume upload section
    if conv_state and conv_state['current_state'] == ConversationStates.RESUME_REQUEST:
        st.markdown("### 📄 Upload Your Resume")
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx'],
            help="Upload your resume in PDF or DOCX format",
            key="resume_uploader"
        )
        
        if uploaded_file is not None:
            with st.spinner('🔍 Processing your resume...'):
                response = assistant.handle_resume_upload(uploaded_file, email)
                
                # Save and display the response
                assistant.db.save_message(email, "assistant", response)
                with st.chat_message("assistant"):
                    st.write(response)
                
                # Force refresh to update conversation state
                st.rerun()
    
    # Handle interview preparation
    if conv_state and conv_state['current_state'] == ConversationStates.INTERVIEW_PREP:
        with st.spinner('🔍 Searching for relevant interview questions...'):
            interview_start = assistant.prepare_interview_questions(email)
            
            if interview_start:
                with st.chat_message("assistant"):
                    st.write(interview_start)
                
                # Force refresh to update state
                st.rerun()
    
    # Chat input - Only show when not in RESUME_REQUEST state
    if conv_state and conv_state['current_state'] != ConversationStates.RESUME_REQUEST:
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
        st.markdown("### 🎯 Conversation Status")
        
        if conv_state:
            st.write(f"**User:** {conv_state['user_name'] or 'Not provided'}")
            st.write(f"**State:** {conv_state['current_state']}")
            st.write(f"**Questions Asked:** {conv_state['current_question_number']}")
            if conv_state['generated_questions']:
                st.write(f"**Total Questions Generated:** {len(conv_state['generated_questions'])}")
        
        if st.button("🔄 Start New Conversation"):
            assistant.db.clear_conversation(email)
            st.session_state.user_email = None
            st.rerun()

if __name__ == "__main__":
    main()
