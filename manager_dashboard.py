import streamlit as st
import json
import os
from dotenv import load_dotenv
from db_manager import DatabaseManager
from analysis_engine import ConversationalAnalyzer

load_dotenv()

@st.cache_resource
def init_systems():
    db = DatabaseManager()
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    analyzer = ConversationalAnalyzer(groq_client, db)
    return db, analyzer

def main():
    st.set_page_config(page_title="Manager Dashboard", page_icon="🎯", layout="wide")
    
    st.title("🎯 Candidate Interview Dashboard")
    st.markdown("**Summary, feedback, and all candidate interview results at a glance.**")
    st.divider()

    db, analyzer = init_systems()
    candidates = db.get_completed_candidates()

    if not candidates:
        st.info("No completed interviews yet.")
        return

    # Stats overview
    st.subheader("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Candidates", len(candidates))
    
    with col2:
        analyzed_count = len([c for c in candidates if db.get_candidate_analysis(c['email'])])
        st.metric("Analyzed", analyzed_count)
    
    with col3:
        if analyzed_count > 0:
            avg_score = sum([
                db.get_candidate_analysis(c['email'])['overall_score'] 
                for c in candidates 
                if db.get_candidate_analysis(c['email'])
            ]) / analyzed_count
            st.metric("Avg Score", f"{avg_score:.1f}/10")
        else:
            st.metric("Avg Score", "N/A")
    
    with col4:
        excellent_count = len([
            c for c in candidates 
            if db.get_candidate_analysis(c['email']) and db.get_candidate_analysis(c['email'])['overall_score'] >= 8
        ])
        st.metric("Excellent (8+)", excellent_count)

    st.divider()

    # Clean Candidates Table
    st.subheader("📋 Candidates Overview")
    
    # Create clean table data
    for i, candidate in enumerate(candidates):
        analysis = db.get_candidate_analysis(candidate['email'])
        qa_pairs = db.get_interview_qa_with_feedback(candidate['email'])
        
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
                            candidate_data = db.get_candidate_data(candidate['email'])
                            conversation_context = db.get_conversation_context(candidate['email'])
                            
                            analysis_result = analyzer.generate_comprehensive_analysis(
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
                    st.write("**Complete Interview Conversation**")
                    
                    # Get full chat history
                    chat_history = db.get_chat_history(candidate['email'])
                    
                    if chat_history:
                        st.info(f"📊 **Conversation Stats:** {len(chat_history)} total messages | {len([m for m in chat_history if m['type'] == 'user'])} candidate responses | {len([m for m in chat_history if m['type'] == 'assistant'])} AI messages")
                        
                        # Display conversation in a chat-like format
                        st.markdown("---")
                        
                        for j, message in enumerate(chat_history):
                            # Format timestamp
                            timestamp = message.get('timestamp', '')
                            if timestamp:
                                try:
                                    from datetime import datetime
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
                                # Candidate message (right aligned style)
                                st.markdown(f"""
                                <div style="background-color: rgba(0, 123, 255, 0.1); padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #007bff;">
                                    <strong>👤 {candidate['full_name']} ({time_str})</strong><br>
                                    {message['content']}
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                # AI message (left aligned style)
                                st.markdown(f"""
                                <div style="background-color: rgba(40, 167, 69, 0.1); padding: 10px; border-radius: 10px; margin: 5px 0; border-left: 3px solid #28a745;">
                                    <strong>🤖 TalentScout AI ({time_str})</strong><br>
                                    {message['content']}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Conversation quality metrics
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
                
                with tab2:
                    st.write("**Performance Breakdown**")
                    
                    # Score visualization
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
                
                with tab3:
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

    st.divider()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    with col2:
        if st.button("📊 Export Summary"):
            # Create export data
            export_data = []
            for candidate in candidates:
                analysis = db.get_candidate_analysis(candidate['email'])
                qa_count = len(db.get_interview_qa_with_feedback(candidate['email']))
                
                export_data.append({
                    'Name': candidate['full_name'],
                    'Email': candidate['email'],
                    'Position': candidate['desired_position'],
                    'Experience': f"{candidate['years_experience']} years",
                    'Questions': qa_count,
                    'Overall Score': f"{analysis['overall_score']:.1f}/10" if analysis else 'Not analyzed',
                    'Recommendation': analysis['hiring_recommendation'] if analysis else 'Pending'
                })
            
            # Convert to CSV-like format
            if export_data:
                st.download_button(
                    label="📥 Download CSV",
                    data=str(export_data),
                    file_name="candidates_summary.txt",
                    mime="text/plain"
                )
    
    with col3:
        unanalyzed = [c for c in candidates if not db.get_candidate_analysis(c['email'])]
        if unanalyzed and st.button(f"🤖 Analyze All ({len(unanalyzed)})"):
            with st.spinner("Analyzing all candidates..."):
                progress_bar = st.progress(0)
                
                for i, candidate in enumerate(unanalyzed):
                    candidate_data = db.get_candidate_data(candidate['email'])
                    qa_pairs = db.get_interview_qa_with_feedback(candidate['email'])
                    conversation_context = db.get_conversation_context(candidate['email'])
                    
                    analyzer.generate_comprehensive_analysis(
                        candidate['email'], candidate_data, qa_pairs, conversation_context
                    )
                    
                    progress_bar.progress((i + 1) / len(unanalyzed))
                
                st.success(f"Analyzed {len(unanalyzed)} candidates!")
                st.rerun()

if __name__ == "__main__":
    main()
