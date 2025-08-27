class PromptsManager:
    
    @staticmethod
    def get_conversational_response_prompt(candidate_data, conversation_history, user_input):
        """Generate natural conversational responses before technical questions"""
        
        history_text = ""
        for exchange in conversation_history[-4:]:  # Last 2 exchanges
            role = "You" if exchange['role'] == 'assistant' else f"{candidate_data['full_name']}"
            history_text += f"{role}: {exchange['content']}\n"
        
        return f"""
        You are a warm, professional interviewer getting to know {candidate_data['full_name']} before the technical interview.
        
        **Context:**
        - Position: {candidate_data['desired_position']}
        - Experience: {candidate_data['years_experience']} years
        - Tech Stack: {', '.join(candidate_data.get('tech_stack', []))}
        
        **Recent conversation:**
        {history_text}
        
        **They just said:** "{user_input}"
        
        **Your approach:**
        - Respond naturally and show genuine interest
        - Build on what they've shared with thoughtful follow-ups
        - Help them feel comfortable and excited about the interview
        - Keep the conversation flowing naturally (avoid formal interview questions yet)
        - Reference their specific experiences and interests
        
        **Tone:** Friendly, encouraging, professionally curious
        
        Generate a natural, engaging response that builds rapport:
        """
    
    @staticmethod
    def get_first_technical_question_prompt(candidate_data, conversation_context):
        """Generate the first technical question based on conversation"""
        
        context_summary = ""
        for exchange in conversation_context:
            if exchange['role'] == 'user':
                context_summary += f"- {exchange['content'][:100]}...\n"
        
        return f"""
        Create the first technical question for {candidate_data['full_name']} based on your conversation.
        
        **What they've shared:**
        {context_summary}
        
        **Their background:**
        - Position: {candidate_data['desired_position']}
        - Experience: {candidate_data['years_experience']} years
        - Tech Stack: {', '.join(candidate_data.get('tech_stack', []))}
        
        **Question requirements:**
        - Connect to something they mentioned during your chat
        - Match their experience level appropriately
        - Feel like a natural next step, not abrupt
        - Be encouraging and supportive in tone
        - Focus on practical experience over theory
        
        **Style:** Start with a warm transition acknowledging your conversation, then ask one focused technical question that lets them showcase their knowledge.
        
        Create a natural first technical question:
        """
    
    @staticmethod
    def get_dynamic_next_question_prompt(candidate_data, previous_qa, conversation_context, last_feedback):
        """Generate next question based on previous answer and feedback"""
        
        qa_history = ""
        for i, qa in enumerate(previous_qa[-2:], len(previous_qa)-1):  # Last 2 Q&As
            qa_history += f"Q{i}: {qa['question']}\nA{i}: {qa['answer'][:200]}...\n\n"
        
        return f"""
        Continue the technical interview with {candidate_data['full_name']} by asking the next question.
        
        **Recent questions and answers:**
        {qa_history}
        
        **Their performance:** {last_feedback.get('key_strength', 'Solid understanding shown')}
        
        **Next question approach:**
        - Build naturally from their previous response
        - Acknowledge something positive about their last answer
        - Progress to a related but distinct technical area
        - Adjust complexity based on how they're doing
        - Maintain an encouraging, conversational interview style
        
        **Flow:** Brief positive acknowledgment + smooth transition + one clear technical question
        
        **Avoid:** Repeating similar questions, being too formal, overwhelming with multiple questions
        
        Generate the next interview question:
        """
    
    @staticmethod
    def get_real_time_feedback_prompt(question, answer, candidate_context):
        """Generate encouraging real-time feedback for each answer"""
        
        return f"""
        Provide supportive feedback on {candidate_context['full_name']}'s interview response.
        
        **Question asked:** {question}
        **Their answer:** {answer}
        **Background:** {candidate_context['years_experience']} years experience
        
        **Feedback goals:**
        - Highlight specific strengths in their response
        - Show you're actively listening and engaged
        - Build confidence while being honest
        - If improvements needed, suggest gently and constructively
        - Sound natural and supportive, not robotic
        
        **Assessment approach:**
        - Score based on technical accuracy, communication clarity, and problem-solving approach
        - Consider their experience level when scoring
        - Focus on what they did well before noting areas for growth
        
        **Return this exact JSON structure:**
        {{
            "encouraging_feedback": "Natural, specific positive feedback about their response",
            "score": 7.5,
            "key_strength": "Main strength they demonstrated in this answer",
            "improvement_area": "Gentle suggestion for improvement, or 'Strong response overall' if no major issues",
            "confidence_level": "High/Medium/Low based on how confident they seemed"
        }}
        
        Be genuinely encouraging while providing honest assessment.
        """
    
    @staticmethod
    def get_comprehensive_analysis_prompt(candidate_data, all_qa_pairs, conversation_context, real_time_feedback):
        """Generate final comprehensive interview analysis"""
        
        qa_summary = ""
        feedback_summary = ""
        
        for i, qa in enumerate(all_qa_pairs, 1):
            qa_summary += f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}\n\n"
        
        for i, feedback in enumerate(real_time_feedback, 1):
            feedback_summary += f"Q{i} Score: {feedback.get('score', 0)}/10 - {feedback.get('key_strength', '')}\n"
        
        return f"""
        Create a comprehensive interview evaluation for {candidate_data['full_name']}.
        
        **Complete interview record:**
        {qa_summary}
        
        **Question-by-question performance:**
        {feedback_summary}
        
        **Candidate profile:**
        - Position: {candidate_data['desired_position']}
        - Experience: {candidate_data['years_experience']} years
        - Tech Stack: {', '.join(candidate_data.get('tech_stack', []))}
        
        **Analysis requirements:**
        - Evaluate technical knowledge, communication skills, and problem-solving ability
        - Provide specific, actionable strengths and growth areas
        - Give honest but encouraging overall assessment
        - Include practical next steps and recommendations
        - Make hiring recommendation based on role requirements
        
        **Return exactly this JSON format:**
        {{
            "overall_score": 8.2,
            "technical_score": 8.5,
            "communication_score": 7.8,
            "problem_solving_score": 8.0,
            "key_strengths": ["Specific strength based on their answers", "Another demonstrated strength", "Third key strength"],
            "areas_for_growth": ["Constructive growth area", "Another development opportunity"],
            "specific_recommendations": ["Actionable advice for improvement", "Another practical suggestion"],
            "hiring_recommendation": "Strong Recommend/Recommend/Consider/Not Recommend with brief reason",
            "summary_feedback": "Encouraging summary of their overall performance and potential",
            "next_steps_suggestion": "Career development advice based on their goals and performance"
        }}
        
        Focus on their growth potential and be constructively supportive.
        """
    
    @staticmethod
    def get_context_based_response_prompt(user_question, candidate_data, interview_qa, conversation_context):
        """Generate context-aware responses for post-interview questions"""
        
        qa_context = ""
        for i, qa in enumerate(interview_qa, 1):
            qa_context += f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}\n\n"
        
        tech_stack_str = ", ".join(candidate_data.get('tech_stack', [])) if isinstance(candidate_data.get('tech_stack'), list) else candidate_data.get('tech_stack', '')
        
        return f"""
        Answer {candidate_data.get('full_name', 'the candidate')}'s post-interview question professionally.
        
        **Their background:**
        - Position: {candidate_data.get('desired_position', 'Unknown')}
        - Experience: {candidate_data.get('years_experience', 0)} years
        - Skills: {tech_stack_str}
        - Location: {candidate_data.get('current_location', 'Unknown')}
        
        **Their interview performance:**
        {qa_context}
        
        **Their question:** {user_question}
        
        **Response approach:**
        - Provide helpful, accurate information
        - Reference their interview performance when relevant
        - Maintain encouraging and supportive tone
        - Give specific timelines or next steps if asked
        - Offer practical career guidance when appropriate
        
        **Style:** Professional yet warm, informative but concise, focused on being genuinely helpful.
        
        Generate a helpful response to their question:
        """
