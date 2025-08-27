import streamlit as st
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

from db_manager import DatabaseManager
from prompts import PromptsManager
from utils import SearchManager, ConversationStates, ConversationMemory, ScoreCalculator
from analysis_engine import ConversationalAnalyzer

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

@st.cache_data
def init_conversation_memory():
    """Initialize conversation memory"""
    return ConversationMemory()

class TalentScoutApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.groq_client = init_groq_client()
        self.search_manager = init_search_manager()
        self.prompts = PromptsManager()
        self.analyzer = ConversationalAnalyzer(self.groq_client, self.db)
        self.memory = init_conversation_memory()

    def run(self):
        """Main app with navigation"""
        st.set_page_config(
            page_title="🎯 TalentScout AI Platform",
            page_icon="🎯",
            layout="wide"
        )

        # Sidebar Navigation
        with st.sidebar:
            st.title("🎯 TalentScout AI")
            st.markdown("**AI-Powered Hiring Platform**")
            st.divider()
            
            page = st.radio(
                "Navigate to:",
                ["👤 Candidate Interview", "👨‍💼 Manager Dashboard"],
                key="navigation"
            )
            
            st.divider()
            st.markdown("### 📊 Quick Stats")
            
            # Quick stats in sidebar
            try:
                candidates = self.db.get_completed_candidates()
                total_candidates = len(candidates)
                analyzed_count = len([c for c in candidates if self.db.get_candidate_analysis(c['email'])])
                
                st.metric("Total Candidates", total_candidates)
                st.metric("Analyzed", analyzed_count)
                
                if analyzed_count > 0:
                    avg_score = sum([
                        self.db.get_candidate_analysis(c['email'])['overall_score'] 
                        for c in candidates 
                        if self.db.get_candidate_analysis(c['email'])
                    ]) / analyzed_count
                    st.metric("Avg Score", f"{avg_score:.1f}/10")
                
            except Exception as e:
                st.metric("Status", "Loading...")

        # Route to appropriate page
        if page == "👤 Candidate Interview":
            self.candidate_interview_page()
        elif page == "👨‍💼 Manager Dashboard":
            self.manager_dashboard_page()

    def candidate_interview_page(self):
        """Candidate interview interface"""
        # Header
        st.title("🎯 TalentScout AI Hiring Assistant")
        st.markdown("**Intelligent Conversational Technical Screening**")
        st.divider()

        # Session state management
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None
            st.session_state.form_submitted = False

        # Email input
        if not st.session_state.user_email:
            st.subheader("Get Started")
            with st.form("email_form"):
                st.write("**Please enter your email to start:**")
                email_input = st.text_input("Email Address", placeholder="your.email@example.com")
                submit_email = st.form_submit_button("Start Interview", type="primary")
                
                if submit_email and email_input:
                    if "@" in email_input and "." in email_input:
                        st.session_state.user_email = email_input
                        st.rerun()
                    else:
                        st.error("Please enter a valid email address.")
            return

        email = st.session_state.user_email
        conv_state = self.db.get_conversation_state(email)

        # Information form (if no conversation exists)
        if not conv_state and not st.session_state.form_submitted:
            st.subheader("📋 Candidate Information")
            st.write("Please fill out the form below to get started with your conversational technical interview.")
            
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
                
                submit_info = st.form_submit_button("🚀 Start Conversational Interview", type="primary")
                
                if submit_info:
                    if not full_name or not desired_position or not tech_stack_input:
                        st.error("Please fill in all required fields marked with *")
                    else:
                        tech_stack = [tech.strip() for tech in tech_stack_input.split(',') if tech.strip()]
                        
                        candidate_data = {
                            'full_name': full_name.strip(),
                            'email': email,
                            'phone': phone.strip() if phone else "Not provided",
                            'years_experience': years_experience,
                            'desired_position': desired_position.strip(),
                            'current_location': current_location.strip() if current_location else "Not provided",
                            'tech_stack': json.dumps(tech_stack)
                        }
                        
                        candidate_id = self.db.save_candidate_to_db(candidate_data, "")
                        
                        if candidate_id:
                            candidate_data['id'] = candidate_id
                            intro_message = self.start_conversational_intro(email, full_name, candidate_data)
                            
                            st.session_state.form_submitted = True
                            st.success("✅ Information saved! Starting conversational interview...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("There was an error saving your information. Please try again.")
            return

        # Chat interface for active conversations
        if conv_state or st.session_state.form_submitted:
            if not conv_state:
                conv_state = self.db.get_conversation_state(email)

            # Display conversation history
            chat_history = self.db.get_chat_history(email)
            
            for message in chat_history:
                with st.chat_message(message['type']):
                    st.write(message['content'])

            # Show conversation ended message if terminated
            if conv_state and conv_state['current_state'] == ConversationStates.CONVERSATION_TERMINATED:
                st.success("✅ Interview Complete! Thank you for completing your conversational interview! You can now close this window.")

            # Chat input (hide when terminated)
            if conv_state and conv_state['current_state'] != ConversationStates.CONVERSATION_TERMINATED:
                if prompt := st.chat_input("Type your message here..."):
                    # Display user message
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # Process conversation
                    with st.spinner('🤔 Thinking...'):
                        response = self.process_conversation(email, prompt)
                    
                    # Display assistant response
                    with st.chat_message("assistant"):
                        st.write(response)
                    
                    st.rerun()

            # Interview status in main area (since sidebar is used for navigation)
            if conv_state:
                with st.expander("📊 Interview Status", expanded=False):
                    candidate_data = self.db.get_candidate_data(email)
                    if candidate_
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Candidate:** {candidate_data['full_name']}")
                        with col2:
                            st.write(f"**Position:** {candidate_data['desired_position']}")
                        with col3:
                            st.write(f"**Experience:** {candidate_data['years_experience']} years")
                    
                    status_display = {
                        ConversationStates.CONVERSATIONAL_INTRO: "Getting to Know You 💭",
                        ConversationStates.DYNAMIC_INTERVIEW: "Technical Interview 🎯",
                        ConversationStates.REAL_TIME_ANALYSIS: "Performance Analysis 📊",
                        ConversationStates.POST_INTERVIEW_QA: "Q&A Session 💬",
                        ConversationStates.CONVERSATION_TERMINATED: "Complete ✅"
                    }
                    
                    current_status = status_display.get(conv_state['current_state'], conv_state['current_state'])
                    st.write(f"**Status:** {current_status}")
                    
                    if conv_state['current_state'] == ConversationStates.DYNAMIC_INTERVIEW:
                        st.write(f"**Questions Asked:** {conv_state['current_question_number'] - 1}")
                
                if st.button("🔄 Start New Interview"):
                    self.db.clear_conversation(email)
                    self.memory.clear_memory(email)
                    st.session_state.user_email = None
                    st.session_state.form_submitted = False
                    st.rerun()

    def manager_dashboard_page(self):
        """Manager dashboard interface"""
        st.title("🎯 Manager Dashboard")
        st.markdown("**Complete candidate analysis and interview management**")
        st.divider()

        candidates = self.db.get_completed_candidates()

        if not candidates:
            st.info("No completed interviews yet. Candidates will appear here after they complete their interviews.")
            st.markdown("💡 **Tip:** Use the 'Candidate Interview' page to test the system or share the link with candidates.")
            return

        # Stats overview
        st.subheader("📊 Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Candidates", len(candidates))
        
        with col2:
            analyzed_count = len([c for c in candidates if self.db.get_candidate_analysis(c['email'])])
            st.metric("Analyzed", analyzed_count)
        
        with col3:
            if analyzed_count > 0:
                avg_score = sum([
                    self.db.get_candidate_analysis(c['email'])['overall_score'] 
                    for c in candidates 
                    if self.db.get_candidate_analysis(c['email'])
                ]) / analyzed_count
                st.metric("Avg Score", f"{avg_score:.1f}/10")
            else:
                st.metric("Avg Score", "N/A")
        
        with col4:
            excellent_count = len([
                c for c in candidates 
                if self.db.get_candidate_analysis(c['email']) and self.db.get_candidate_analysis(c['email'])['overall_score'] >= 8
            ])
            st.metric("Excellent (8+)", excellent_count)

        st.divider()

        # Candidates Overview
        st.subheader("📋 Candidates Overview")
        
        for i, candidate in enumerate(candidates):
            analysis = self.db.get_candidate_analysis(candidate['email'])
            qa_pairs = self.db.get_interview_qa_with_feedback(candidate['email'])
            
            # Parse tech stack
            tech_stack_raw = candidate.get('tech_stack', '[]')
            if isinstance(tech_stack_raw, str):
                try:
                    tech_stack = json.loads(tech_stack_raw)
                except:
                    tech_stack = []
            else:
                tech_stack = tech_stack_raw
            
            # Create card-like display for each candidate
            with st.expander(f"👤 {candidate['full_name']} - {candidate['desired_position']}", expanded=False):
                
                # Basic info row
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.write("**📧 Contact**")
                    st.write(f"Email: {candidate['email']}")
                    st.write(f"Phone: {candidate.get('phone', 'N/A')}")
                    st.write(f"Location: {candidate.get('current_location', 'N/A')}")
                
                with col2:
                    st.write("**💼 Role & Experience**")
                    st.write(f"Position: {candidate['desired_position']}")
                    st.write(f"Experience: {candidate['years_experience']} years")
                    st.write(f"Questions Asked: {len(qa_pairs)}")
                
                with col3:
                    st.write("**💻 Tech Stack**")
                    tech_display = ", ".join(tech_stack[:4]) + ("..." if len(tech_stack) > 4 else "")
                    st.write(tech_display if tech_stack else "Not specified")
                    
                    st.write("**📊 Scores**")
                    if analysis:
                        st.write(f"Overall: **{analysis['overall_score']:.1f}/10**")
                        st.write(f"Technical: {analysis['technical_score']:.1f}/10")
                        st.write(f"Communication: {analysis['communication_score']:.1f}/10")
                    else:
                        st.write("Not analyzed yet")
                
                with col4:
                    st.write("**🎯 Status**")
                    if analysis:
                        score = analysis['overall_score']
                        if score >= 8:
                            st.success(f"Excellent - {analysis['hiring_recommendation']}")
                        elif score >= 6:
                            st.info(f"Good - {analysis['hiring_recommendation']}")
                        else:
                            st.warning(f"Average - {analysis['hiring_recommendation']}")
                    else:
                        st.write("⏳ Pending Analysis")
                        if st.button(f"🤖 Analyze {candidate['full_name']}", key=f"analyze_{i}"):
                            with st.spinner("Analyzing..."):
                                candidate_data = self.db.get_candidate_data(candidate['email'])
                                conversation_context = self.db.get_conversation_context(candidate['email'])
                                
                                analysis_result = self.analyzer.generate_comprehensive_analysis(
                                    candidate['email'], candidate_data, qa_pairs, conversation_context
                                )
                                
                                if analysis_result:
                                    st.success("Analysis completed!")
                                    st.rerun()
                                else:
                                    st.error("Analysis failed. Please try again.")
                
                # Detailed analysis section (if analysis exists)
                if analysis:
                    st.divider()
                    
                    tab1, tab2, tab3 = st.tabs(["💬 Full Conversation", "📊 Analysis", "📝 Feedback"])
                    
                    with tab1:
                        self.show_conversation_tab(candidate, qa_pairs)
                    
                    with tab2:
                        self.show_analysis_tab(analysis)
                    
                    with tab3:
                        self.show_feedback_tab(analysis, qa_pairs)

        st.divider()
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data"):
                st.rerun()
        
        with col2:
            if st.button("📊 Export Summary"):
                export_data = []
                for candidate in candidates:
                    analysis = self.db.get_candidate_analysis(candidate['email'])
                    qa_count = len(self.db.get_interview_qa_with_feedback(candidate['email']))
                    
                    export_data.append({
                        'Name': candidate['full_name'],
                        'Email': candidate['email'],
                        'Position': candidate['desired_position'],
                        'Experience': f"{candidate['years_experience']} years",
                        'Questions': qa_count,
                        'Overall Score': f"{analysis['overall_score']:.1f}/10" if analysis else 'Not analyzed',
                        'Recommendation': analysis['hiring_recommendation'] if analysis else 'Pending'
                    })
                
                if export_
                    st.download_button(
                        label="📥 Download CSV",
                        data=str(export_data),
                        file_name="candidates_summary.txt",
                        mime="text/plain"
                    )
        
        with col3:
            unanalyzed = [c for c in candidates if not self.db.get_candidate_analysis(c['email'])]
            if unanalyzed and st.button(f"🤖 Analyze All ({len(unanalyzed)})"):
                with st.spinner("Analyzing all candidates..."):
                    progress_bar = st.progress(0)
                    
                    for i, candidate in enumerate(unanalyzed):
                        candidate_data = self.db.get_candidate_data(candidate['email'])
                        qa_pairs = self.db.get_interview_qa_with_feedback(candidate['email'])
                        conversation_context = self.db.get_conversation_context(candidate['email'])
                        
                        self.analyzer.generate_comprehensive_analysis(
                            candidate['email'], candidate_data, qa_pairs, conversation_context
                        )
                        
                        progress_bar.progress((i + 1) / len(unanalyzed))
                    
                    st.success(f"Analyzed {len(unanalyzed)} candidates!")
                    st.rerun()

    def show_conversation_tab(self, candidate, qa_pairs):
        """Show full conversation history"""
        st.write("**Complete Interview Conversation**")
        
        chat_history = self.db.get_chat_history(candidate['email'])
        
        if chat_history:
            st.info(f"📊 **Conversation Stats:** {len(chat_history)} total messages | {len([m for m in chat_history if m['type'] == 'user'])} candidate responses | {len([m for m in chat_history if m['type'] == 'assistant'])} AI messages")
            
            st.markdown("---")
            
            for j, message in enumerate(chat_history):
                timestamp = message.get('timestamp', '')
                if timestamp:
                    try:
                        if 'T' in str(timestamp):
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(float(timestamp))
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        time_str = "Unknown"
                else:
                    time_str = f"Msg {j+1}"
                
                if message['type'] == 'user':
                    st.markdown(f"""
                    <div style="background-color: rgba(0, 123, 255, 0.1); padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #007bff;">
                        <strong>👤 {candidate['full_name']} ({time_str})</strong><br>
                        {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background-color: rgba(40, 167, 69, 0.1); padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #28a745;">
                        <strong>🤖 TalentScout AI ({time_str})</strong><br>
                        {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Conversation insights
            st.markdown("---")
            st.write("**💡 Conversation Insights:**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                user_messages = [m for m in chat_history if m['type'] == 'user']
                avg_response_length = sum(len(m['content']) for m in user_messages) / len(user_messages) if user_messages else 0
                st.metric("Avg Response Length", f"{avg_response_length:.0f} chars")
            
            with col2:
                total_words = sum(len(m['content'].split()) for m in user_messages)
                st.metric("Total Words (Candidate)", total_words)
            
            with col3:
                conversation_duration = len(chat_history)
                engagement_level = "High" if conversation_duration > 15 else "Medium" if conversation_duration > 10 else "Low"
                st.metric("Engagement Level", engagement_level)
        
        else:
            st.warning("No conversation history found for this candidate.")

    def show_analysis_tab(self, analysis):
        """Show performance analysis"""
        st.write("**Performance Breakdown**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Technical", f"{analysis['technical_score']:.1f}/10")
        with col2:
            st.metric("Communication", f"{analysis['communication_score']:.1f}/10")
        with col3:
            st.metric("Problem Solving", f"{analysis['problem_solving_score']:.1f}/10")
        
        st.write("**Key Strengths:**")
        strengths = analysis['key_strengths']
        if isinstance(strengths, str):
            try:
                strengths = json.loads(strengths)
            except:
                strengths = [strengths]
        
        for strength in strengths:
            st.write(f"✅ {strength}")
        
        st.write("**Areas for Growth:**")
        growth_areas = analysis['areas_for_growth']
        if isinstance(growth_areas, str):
            try:
                growth_areas = json.loads(growth_areas)
            except:
                growth_areas = [growth_areas]
        
        for area in growth_areas:
            st.write(f"📈 {area}")

    def show_feedback_tab(self, analysis, qa_pairs):
        """Show detailed feedback and recommendations"""
        st.write("**Hiring Recommendation:**")
        recommendation = analysis['hiring_recommendation']
        
        if "strong" in recommendation.lower() or "excellent" in recommendation.lower():
            st.success(f"✅ {recommendation}")
        elif "recommend" in recommendation.lower():
            st.info(f"👍 {recommendation}")
        else:
            st.warning(f"⚠️ {recommendation}")
        
        st.write("**Summary:**")
        st.write(analysis['summary_feedback'])
        
        st.write("**Individual Question Scores:**")
        for k, qa in enumerate(qa_pairs, 1):
            if qa.get('feedback_score') and qa.get('feedback_text'):
                score = qa['feedback_score']
                question_preview = qa['question'][:80] + "..." if len(qa['question']) > 80 else qa['question']
                
                if score >= 8:
                    st.success(f"**Q{k}:** {question_preview} - Score: {score}/10")
                elif score >= 6:
                    st.info(f"**Q{k}:** {question_preview} - Score: {score}/10")
                else:
                    st.warning(f"**Q{k}:** {question_preview} - Score: {score}/10")
                
                st.write(f"*Feedback:* {qa['feedback_text']}")
                st.write("---")
        
        st.write("**Specific Recommendations:**")
        recommendations = analysis['specific_recommendations']
        if isinstance(recommendations, str):
            try:
                recommendations = json.loads(recommendations)
            except:
                recommendations = [recommendations]
        
        for rec in recommendations:
            st.write(f"💡 {rec}")

    # All the conversation processing methods from original main.py
    def process_conversation(self, email, user_input):
        """Main conversational processing logic"""
        conv_state = self.db.get_conversation_state(email)
        
        if not conv_state:
            return "Error: Conversation state not found."
        
        current_state = conv_state['current_state']
        
        # Save user message to chat history
        self.db.save_message(email, "user", user_input)
        
        # Route to appropriate handler
        if current_state == ConversationStates.CONVERSATIONAL_INTRO:
            return self._handle_conversational_intro(email, user_input, conv_state)
        
        elif current_state == ConversationStates.DYNAMIC_INTERVIEW:
            return self._handle_dynamic_interview(email, user_input, conv_state)
        
        elif current_state == ConversationStates.REAL_TIME_ANALYSIS:
            return self._handle_real_time_analysis(email, user_input, conv_state)
        
        elif current_state == ConversationStates.POST_INTERVIEW_QA:
            return self._handle_post_interview_qa(email, user_input, conv_state)
        
        elif current_state == ConversationStates.CONVERSATION_TERMINATED:
            return self._handle_terminated_state(email, user_input, conv_state)
        
        return "I'm not sure how to help with that. Could you please clarify?"

    def _handle_conversational_intro(self, email, user_input, conv_state):
        """Handle natural conversation before technical questions"""
        candidate_data = self.db.get_candidate_data(email)
        
        # Parse tech stack for prompts
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                candidate_data['tech_stack'] = json.loads(tech_stack_raw)
            except:
                candidate_data['tech_stack'] = []
        
        # Get conversation context
        conversation_context = self.db.get_conversation_context(email)
        
        # Generate conversational response
        response = self._generate_conversational_response(candidate_data, conversation_context, user_input)
        
        # Save conversation exchange to memory
        self.db.save_conversation_exchange(email, user_input, response)
        
        # Check if ready for technical questions (after 3-4 exchanges)
        exchange_count = self.db.get_conversation_exchange_count(email)
        
        if exchange_count >= 3:
            # Transition to technical interview
            response += "\n\n🎯 **Great! I have a good sense of your background now. Let's start with some technical questions that build on what you've shared. Ready?**"
            
            self.db.create_or_update_conversation(email, ConversationStates.DYNAMIC_INTERVIEW, question_number=1)
        
        self.db.save_message(email, "assistant", response)
        return response

    def _handle_dynamic_interview(self, email, user_answer, conv_state):
        """Handle dynamic interview with real-time feedback"""
        candidate_data = self.db.get_candidate_data(email)
        current_q_num = conv_state['current_question_number']
        
        # Parse tech stack
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                candidate_data['tech_stack'] = json.loads(tech_stack_raw)
            except:
                candidate_data['tech_stack'] = []
        
        # Get previous Q&As and conversation context
        previous_qa = self.db.get_interview_qa_with_feedback(email)
        conversation_context = self.db.get_conversation_context(email)
        
        # If this is an answer to a question
        if previous_qa or current_q_num > 1:
            # Get the last question that was asked
            last_question = previous_qa[-1]['question'] if previous_qa else "Introduction question"
            
            # Generate real-time feedback for the answer
            feedback = self.analyzer.analyze_answer_realtime(last_question, user_answer, candidate_data)
            
            # Save Q&A with feedback
            self.db.save_interview_qa_with_feedback(
                email, current_q_num, last_question, user_answer, 
                feedback.get('score', 0), feedback.get('encouraging_feedback', '')
            )
            
            # Update previous Q&A list
            previous_qa = self.db.get_interview_qa_with_feedback(email)
            
            # Check if we've completed enough questions (5-6)
            if len(previous_qa) >= 5:
                # Move to comprehensive analysis
                self.db.create_or_update_conversation(email, ConversationStates.REAL_TIME_ANALYSIS)
                
                comprehensive_analysis = self.analyzer.generate_comprehensive_analysis(
                    email, candidate_data, previous_qa, conversation_context
                )
                
                return self._present_comprehensive_analysis(email, conv_state, comprehensive_analysis)
            
            # Generate next question with feedback
            next_question = self._generate_next_dynamic_question(
                candidate_data, previous_qa, conversation_context, feedback
            )
            
            # Combine feedback and next question
            response = f"**{feedback.get('encouraging_feedback', 'Great answer!')}** 👍\n\n{next_question}"
            
        else:
            # This is the start - generate first technical question
            first_question = self._generate_first_technical_question(candidate_data, conversation_context)
            response = f"Perfect! Let's dive into some technical areas now.\n\n{first_question}"
        
        # Update question number for next iteration
        next_q_num = current_q_num + 1
        self.db.create_or_update_conversation(email, question_number=next_q_num)
        
        self.db.save_message(email, "assistant", response)
        return response

    def _handle_real_time_analysis(self, email, user_input, conv_state):
        """Handle post-analysis interactions"""
        # Check for continuation keywords
        continue_keywords = ["yes", "continue", "more", "tell me more", "explain"]
        end_keywords = ["no", "done", "finish", "goodbye", "bye", "thanks"]
        
        if any(keyword in user_input.lower() for keyword in end_keywords):
            self.db.create_or_update_conversation(email, ConversationStates.POST_INTERVIEW_QA)
            
            response = f"Perfect! Thank you for completing the interview, {conv_state['user_name']}! 🎉\n\n💬 **Feel free to ask me any questions about the process, timeline, or next steps. I'm here to help!**\n\nOr say **'goodbye'** when you're ready to end our conversation."
            
        elif any(keyword in user_input.lower() for keyword in continue_keywords):
            # Provide more detailed analysis or tips
            analysis = self.db.get_candidate_analysis(email)
            if analysis:
                response = self._provide_detailed_tips(analysis, conv_state['user_name'])
            else:
                response = "I'd love to provide more details, but I'm having trouble accessing your analysis. Feel free to ask any other questions!"
        
        else:
            # General response
            response = "Is there anything specific you'd like to know more about regarding your performance or next steps? You can ask for more details or say 'done' when you're ready to finish."
        
        self.db.save_message(email, "assistant", response)
        return response

    def _handle_post_interview_qa(self, email, user_input, conv_state):
        """Handle post-interview questions using full context"""
        ending_keywords = ["thank you", "goodbye", "bye", "thanks", "end", "finish", "done", "exit", "quit"]
        
        if any(keyword in user_input.lower() for keyword in ending_keywords):
            self.db.create_or_update_conversation(email, ConversationStates.CONVERSATION_TERMINATED)
            
            response = f"Thank you for your time, {conv_state['user_name']}! 🙏\n\nYour interview has been completed and recorded. Our team will review your responses and get back to you soon.\n\nWe appreciate your interest in joining our team. Have a great day! ✨\n\n*This conversation has ended. You can close this window.*"
            
            self.db.save_message(email, "assistant", response)
            return response
        
        # Generate context-based response
        candidate_data = self.db.get_candidate_data(email)
        interview_qa = self.db.get_interview_qa_with_feedback(email)
        conversation_context = self.db.get_conversation_context(email)
        
        response = self._generate_context_based_response(
            user_input, candidate_data, interview_qa, conversation_context
        )
        
        response += f"\n\nAnything else you'd like to know? Feel free to ask, or say **'goodbye'** when you're ready to end our conversation."
        
        self.db.save_message(email, "assistant", response)
        return response

    def _handle_terminated_state(self, email, user_input, conv_state):
        """Handle terminated conversation state"""
        response = "This conversation has ended. Thank you for your time!"
        self.db.save_message(email, "assistant", response)
        return response

    # Helper methods for generating responses
    def _generate_conversational_response(self, candidate_data, conversation_history, user_input):
        """Generate natural conversational response"""
        prompt = self.prompts.get_conversational_response_prompt(candidate_data, conversation_history, user_input)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "That's interesting! Tell me more about your experience and what you're currently working on."

    def _generate_first_technical_question(self, candidate_data, conversation_context):
        """Generate first technical question based on conversation"""
        prompt = self.prompts.get_first_technical_question_prompt(candidate_data, conversation_context)
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=600
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating first question: {str(e)}")
            tech_stack = candidate_data.get('tech_stack', [])
            main_tech = tech_stack[0] if tech_stack else 'programming'
            return f"Let's start with your experience in {main_tech}. Can you walk me through a project where you used {main_tech} and what you learned from it?"

    def _generate_next_dynamic_question(self, candidate_data, previous_qa, conversation_context, last_feedback):
        """Generate next dynamic question based on previous performance"""
        prompt = self.prompts.get_dynamic_next_question_prompt(
            candidate_data, previous_qa, conversation_context, last_feedback
        )
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=600
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating next question: {str(e)}")
            return "That's a good foundation! Let's explore another area. Can you tell me about a technical challenge you faced recently and how you solved it?"

    def _generate_context_based_response(self, user_question, candidate_data, interview_qa, conversation_context):
        """Generate context-aware post-interview response"""
        prompt = self.prompts.get_context_based_response_prompt(
            user_question, candidate_data, interview_qa, conversation_context
        )
        
        try:
            response = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=700
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            return "I apologize, but I'm having trouble processing your question right now. Our team will be in touch with you soon regarding next steps."

    def _present_comprehensive_analysis(self, email, conv_state, analysis):
        """Present comprehensive interview analysis to candidate"""
        if not analysis:
            return "I'm having trouble generating your analysis right now. Let me know if you have any questions about the interview process."
        
        # Calculate performance level
        overall_score = analysis.get('overall_score', 0)
        performance_level = ScoreCalculator.get_performance_level(overall_score)
        
        # Format strengths and growth areas
        strengths = analysis.get('key_strengths', [])
        growth_areas = analysis.get('areas_for_growth', [])
        recommendations = analysis.get('specific_recommendations', [])
        
        if isinstance(strengths, str):
            try:
                strengths = json.loads(strengths)
            except:
                strengths = [strengths]
        
        if isinstance(growth_areas, str):
            try:
                growth_areas = json.loads(growth_areas)
            except:
                growth_areas = [growth_areas]
        
        if isinstance(recommendations, str):
            try:
                recommendations = json.loads(recommendations)
            except:
                recommendations = [recommendations]
        
        strengths_text = "\n".join([f"• {strength}" for strength in strengths])
        growth_text = "\n".join([f"• {area}" for area in growth_areas])
        recommendations_text = "\n".join([f"• {rec}" for rec in recommendations])
        
        analysis_response = f"""🎉 **Interview Complete!** Thank you, {conv_state['user_name']}!

📊 **Your Performance Analysis:**

**Overall Score: {overall_score}/10** ({performance_level})
• **Technical Knowledge:** {analysis.get('technical_score', 0)}/10
• **Communication Skills:** {analysis.get('communication_score', 0)}/10
• **Problem Solving:** {analysis.get('problem_solving_score', 0)}/10

💪 **Your Key Strengths:**
{strengths_text}

📈 **Areas for Growth:**
{growth_text}

🎯 **Personalized Recommendations:**
{recommendations_text}

**Summary:** {analysis.get('summary_feedback', 'You showed good technical understanding and communication skills.')}

**Next Steps Suggestion:** {analysis.get('next_steps_suggestion', 'Continue building your skills and gaining practical experience.')}

---

🚀 **What's Next?**
• Our technical team will review your complete performance
• We'll be in touch within 2-3 business days with next steps
• Keep building on your strengths while working on growth areas

Would you like me to explain any part of this analysis in more detail? Or do you have questions about the next steps?"""
        
        self.db.save_message(email, "assistant", analysis_response)
        return analysis_response

    def _provide_detailed_tips(self, analysis, user_name):
        """Provide detailed tips based on analysis"""
        growth_areas = analysis.get('areas_for_growth', [])
        recommendations = analysis.get('specific_recommendations', [])
        
        if isinstance(growth_areas, str):
            try:
                growth_areas = json.loads(growth_areas)
            except:
                growth_areas = [growth_areas]
        
        if isinstance(recommendations, str):
            try:
                recommendations = json.loads(recommendations)
            except:
                recommendations = [recommendations]
        
        if growth_areas and recommendations:
            tips_text = f"""Here are some detailed tips for your growth, {user_name}:

**Specific Areas to Focus On:**
"""
            for i, (area, rec) in enumerate(zip(growth_areas, recommendations), 1):
                tips_text += f"\n**{i}. {area}**\n   💡 {rec}\n"
            
            tips_text += """\n**General Tips:**
• Set up a regular learning schedule (even 30 minutes daily helps)
• Build small projects to practice new concepts
• Join tech communities and forums for support
• Consider online courses or tutorials for structured learning
• Practice explaining technical concepts to improve communication

Remember, growth takes time. Focus on one area at a time and celebrate your progress! 🌟"""
            
            return tips_text
        else:
            return f"You're doing great, {user_name}! Keep building on your current strengths and stay curious about new technologies. The key to growth is consistent practice and learning."

    def start_conversational_intro(self, email, user_name, candidate_data):
        """Initialize conversational introduction"""
        # Create conversation state
        self.db.create_or_update_conversation(
            email, 
            ConversationStates.CONVERSATIONAL_INTRO, 
            user_name, 
            candidate_data['id']
        )
        
        # Parse tech stack for display
        tech_stack_raw = candidate_data.get('tech_stack', '[]')
        if isinstance(tech_stack_raw, str):
            try:
                tech_stack = json.loads(tech_stack_raw)
            except:
                tech_stack = []
        else:
            tech_stack = tech_stack_raw
        
        # Generate intro message
        intro_message = f"""👋 Hello {user_name}! Welcome to TalentScout AI.

I've received your information:
• **Position:** {candidate_data['desired_position']}
• **Experience:** {candidate_data['years_experience']} years
• **Tech Stack:** {', '.join(tech_stack)}
• **Location:** {candidate_data['current_location']}

Before we dive into technical questions, I'd love to get to know you better! 

**Tell me - what got you interested in {candidate_data['desired_position']}? Are you currently working on any interesting projects or learning something specific?**"""
        
        self.db.save_message(email, "assistant", intro_message)
        return intro_message

# Run the app
def main():
    app = TalentScoutApp()
    app.run()

if __name__ == "__main__":
    main()
