class PromptsManager:
    
    @staticmethod
    def get_resume_extraction_prompt(resume_text):
        """Prompt for extracting information from resume"""
        return f"""
        You are an expert HR assistant. Extract the following information from the resume text provided.
        Return the information in JSON format with these exact keys:
        
        {{
            "full_name": "candidate's full name",
            "email": "email address", 
            "phone": "phone number",
            "years_experience": "total years of experience (number only)",
            "desired_position": "job title or position they're applying for",
            "current_location": "city, state/country",
            "tech_stack": ["list", "of", "technical", "skills", "programming", "languages", "frameworks", "tools"]
        }}
        
        Rules:
        1. If information is not found, use "Not found" for strings, 0 for numbers, or empty array for lists
        2. For years_experience, calculate total years based on work history
        3. Extract all technical skills, programming languages, frameworks, databases, tools
        4. Be accurate and don't hallucinate information
        5. For tech_stack, include everything technical mentioned in the resume
        
        Resume Text:
        {resume_text}
        
        Return only the JSON object, no other text:
        """
    
    @staticmethod
    def get_question_generation_prompt(candidate_data, search_results):
        """Prompt for generating interview questions"""
        tech_stack_str = ", ".join(candidate_data['tech_stack'])
        
        return f"""
        You are an expert technical interviewer. Based on the candidate's profile and web search results, 
        generate exactly 5 technical interview questions.
        
        Candidate Profile:
        - Name: {candidate_data['full_name']}
        - Position: {candidate_data['desired_position']}
        - Experience: {candidate_data['years_experience']} years
        - Tech Stack: {tech_stack_str}
        
        Web Search Results for Reference:
        {search_results[:3000]}
        
        Requirements:
        1. Generate exactly 5 questions
        2. Adjust difficulty for {candidate_data['years_experience']} years experience
        3. Focus on their tech stack: {tech_stack_str}
        4. Mix of conceptual and practical questions
        5. Progressive difficulty (easier to harder)
        6. Make questions complete and clear
        
        Return as JSON array:
        {{
            "questions": [
                {{"id": 1, "question": "Complete question text here", "focus_area": "Technology area"}},
                {{"id": 2, "question": "Complete question text here", "focus_area": "Technology area"}},
                {{"id": 3, "question": "Complete question text here", "focus_area": "Technology area"}},
                {{"id": 4, "question": "Complete question text here", "focus_area": "Technology area"}},
                {{"id": 5, "question": "Complete question text here", "focus_area": "Technology area"}}
            ]
        }}
        
        Make sure each question is complete and properly formatted.
        """
    
    @staticmethod
    def get_follow_up_prompt(previous_qa, candidate_data):
        """Prompt for generating follow-up questions"""
        return f"""
        You are conducting a technical interview. Based on the candidate's previous answer, 
        generate ONE relevant follow-up question.
        
        Candidate: {candidate_data['full_name']}
        Position: {candidate_data['desired_position']}
        Experience: {candidate_data['years_experience']} years
        
        Previous Question: {previous_qa['question']}
        Candidate's Answer: {previous_qa['answer']}
        
        Generate a follow-up question that:
        1. Digs deeper into their answer
        2. Tests practical knowledge
        3. Is appropriate for their experience level
        4. Stays relevant to the tech stack
        5. Is complete and clear
        
        Return ONLY the question text, nothing else. Make sure the question is complete.
        """
    
    @staticmethod
    def get_information_update_prompt(user_input, current_info):
        """Prompt for parsing information updates"""
        return f"""
        The user wants to update their information. Parse their input and return what field they want to update.
        
        Current Information:
        {current_info}
        
        User Input: "{user_input}"
        
        Return JSON with the field to update:
        {{
            "field": "field_name", 
            "value": "new_value",
            "action": "update" or "confirm"
        }}
        
        Common fields: full_name, email, phone, years_experience, desired_position, current_location
        If they're just confirming, set action to "confirm".
        If updating location, the field should be "current_location".
        """
    @staticmethod
    def get_info_parsing_prompt(user_input, step):
        """Prompt for parsing user information input"""
        return f"""
        Parse the user's input for step: {step}
        
        User Input: "{user_input}"
        
        Return JSON:
        {{
            "parsed_info": "cleaned user input"
        }}
        """
    @staticmethod
    def get_context_based_response_prompt(user_question, candidate_data, interview_qa, conversation_context):
        """Prompt for generating context-aware responses after interview"""
        tech_stack_str = ", ".join(candidate_data.get('tech_stack', [])) if isinstance(candidate_data.get('tech_stack'), list) else candidate_data.get('tech_stack', '')
        
        qa_context = ""
        for i, qa in enumerate(interview_qa, 1):
            qa_context += f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}\n\n"
        
        return f"""
        You are TalentScout AI, a professional hiring assistant. A candidate has just completed their technical interview and is asking a follow-up question. 

        Provide a helpful, professional response based on the full context of their interview.

        **Candidate Profile:**
        - Name: {candidate_data.get('full_name', 'Unknown')}
        - Position: {candidate_data.get('desired_position', 'Unknown')}
        - Experience: {candidate_data.get('years_experience', 0)} years
        - Tech Stack: {tech_stack_str}
        - Location: {candidate_data.get('current_location', 'Unknown')}

        **Interview Q&A Context:**
        {qa_context}

        **User's Question:** {user_question}

        **Instructions:**
        1. Answer professionally as TalentScout AI
        2. Reference their interview responses when relevant
        3. Provide helpful information about next steps, timeline, process, etc.
        4. Be encouraging and supportive
        5. If asked about their performance, be diplomatic and positive
        6. If asked about company info, provide general professional responses
        7. Keep responses concise but informative

        Generate a helpful response:
        """
