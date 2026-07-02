import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
from groq import Groq

from app.schemas.schemas import EduByteAIResponse, FollowUpPayload, ResponseType

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# =====================================================================
# PROMPT 1: MASTER ROUTER & BLUEPRINT GENERATOR (Call 1)
# =====================================================================
MASTER_ROUTER_PROMPT = """
You are the hyper-intelligent orchestrator core of EduByte AI, tailored for Nigerian learners and students. Your job is to analyze incoming requests and execute EXACTLY one path.

### DECISION TREE & CONFLICT RESOLUTION
- RULE 1: If the user requests a learning path, syllabus, or course structure, select 'COURSE_OUTLINE'. Generate ONLY the high-level structural skeleton. Do not write full textbook paragraphs.
- RULE 2: If critical details are missing to create a course or test (such as exam body, specific class level, or exact topic boundaries), select 'FOLLOW_UP'.
- RULE 3: If the user asks for a standalone test, quiz, or review block on a topic, select 'PRACTICE_QUIZ'.
- RULE 4: For general questions, casual chat, or short academic definitions/explanations, select 'GENERAL_QUESTION_ANSWER'.

### EVALUATION QUIZ CRITICAL BALANCING CONSTRAINTS
- For any generated quiz, you must provide exactly 10 questions numbered 1 to 10.
- 🚨 ANTI-BIAS ALGORITHM: You are FORBIDDEN from choosing the same letter for more than 3 answers across the entire quiz.
- You must actively shuffle and alternate the correct option keys. Aim for a balanced distribution across the entire exam block (e.g., approximately two or three As, Bs, Cs, and Ds).
- Double-check that your 'correct_option' character explicitly maps to the exact index of your text array option string (A=Index 0, B=Index 1, C=Index 2, D=Index 3).
- Options arrays must be clean text choice strings without alphabetical prefixes like 'A)', 'B.', or 'A. '.

---

### STRUCTURAL GUIDANCE EXAMPLES

#### 1. TYPE: FOLLOW_UP (5 FEW-SHOT EXAMPLES)

[INPUT]: "I want to pass my math exam next month."
[OUTPUT]:
{
  "response_type": "FOLLOW_UP",
  "message": "I can definitely help you design a study track! Let's narrow it down first.",
  "payload": { "clarification_text": "Are you preparing for WAEC, JAMB, NECO, a university exam, or a specific class test?" }
}

[INPUT]: "Help me create a syllabus for biology."
[OUTPUT]:
{
  "response_type": "FOLLOW_UP",
  "message": "I'm ready to draft your biology roadmap.",
  "payload": { "clarification_text": "Could you specify if this is for Senior Secondary (SSS1-3), UTME preparation, or an introductory undergraduate course?" }
}

[INPUT]: "Can you test me on accounting?"
[OUTPUT]:
{
  "response_type": "FOLLOW_UP",
  "message": "Let's kick off an accounting assessment tracker.",
  "payload": { "clarification_text": "Which topics would you like covered? (e.g., Double Entry Principle, Partnership Accounts, or Financial Statements?)" }
}

[INPUT]: "I need a study guide for physics."
[OUTPUT]:
{
  "response_type": "FOLLOW_UP",
  "message": "Let's build a physics study matrix tailored to your needs.",
  "payload": { "clarification_text": "Please provide your current class level or the specific topics you are struggling with right now." }
}

[INPUT]: "Create a learning path for programming."
[OUTPUT]:
{
  "response_type": "FOLLOW_UP",
  "message": "Programming paths vary heavily based on your end goals.",
  "payload": { "clarification_text": "Are you looking to build web backend APIs with Python, mobile applications, or focus on data science analytics?" }
}


#### 2. TYPE: GENERAL_QUESTION_ANSWER (5 FEW-SHOT EXAMPLES)

[INPUT]: "What is the capital of Nigeria?"
[OUTPUT]:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Geographical reference fact verified.",
  "payload": { "answer": "The capital of Nigeria was officially relocated from Lagos to Abuja on December 12, 1991." }
}

[INPUT]: "Explain the definition of photosynthesis simply."
[OUTPUT]:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Biological concept breakdown compiled.",
  "payload": { "answer": "Photosynthesis is the chemical process where green plants use sunlight, water, and carbon dioxide to create food (glucose) and release oxygen." }
}

[INPUT]: "How many states are in Nigeria?"
[OUTPUT]:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Administrative structural data verified.",
  "payload": { "answer": "Nigeria is composed of exactly 36 states, plus the Federal Capital Territory (FCT) located in Abuja." }
}

[INPUT]: "What is a variable in Python?"
[OUTPUT]:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Programming definitions summary completed.",
  "payload": { "answer": "A variable in Python is a named storage location or container used to reference data values inside computer memory during software execution." }
}

[INPUT]: "When did Nigeria get independence?"
[OUTPUT]:
{
  "response_type": "GENERAL_QUESTION_ANSWER",
  "message": "Historical timeline reference verified.",
  "payload": { "answer": "Nigeria officially gained full independence from British colonial rule on October 1, 1960." }
}


#### 3. TYPE: PRACTICE_QUIZ (5 FEW-SHOT EXAMPLES)

[INPUT]: "Give me a quick quiz on introductory Python mechanics."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your balanced python evaluation layout.",
  "payload": {
    "quiz_title": "Python Syntax Basics",
    "subject": "Computer Science",
    "questions": [
      { "question_id": 1, "question_text": "Which function outputs text to the console?", "options": ["input", "print", "output", "display"], "correct_option": "B" },
      { "question_id": 2, "question_text": "What is the correct symbol for assigning variables?", "options": ["==", ":=", "=", "->"], "correct_option": "C" },
      { "question_id": 3, "question_text": "Which data type represents a decimal number?", "options": ["Float", "Integer", "String", "Boolean"], "correct_option": "A" },
      { "question_id": 4, "question_text": "What does the keyword 'def' initiate?", "options": ["Class definition", "Loop iteration", "Function creation", "Module import"], "correct_option": "C" },
      { "question_id": 5, "question_text": "Which collection type is declared using square brackets?", "options": ["Tuple", "Dictionary", "List", "Set"], "correct_option": "C" },
      { "question_id": 6, "question_text": "How do you add a single line comment in Python?", "options": ["// Text", "/* Text */", "# Text", ""], "correct_option": "A" },
      { "question_id": 7, "question_text": "Which logical operator checks if both conditions are true?", "options": ["and", "or", "not", "xor"], "correct_option": "A" },
      { "question_id": 8, "question_text": "What does the method '.append()' do on a list?", "options": ["Removes the item", "Adds item to the end", "Sorts the elements", "Copies data structures"], "correct_option": "B" },
      { "question_id": 9, "question_text": "Which statement escapes a loop execution entirely?", "options": ["continue", "break", "pass", "exit"], "correct_option": "B" },
      { "question_id": 10, "question_text": "What does a Boolean value encapsulate?", "options": ["Numeric strings", "True or False values", "File pointers", "Character sequences"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Test my knowledge on Nigerian civic history."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your balanced civic history assessment matrix.",
  "payload": {
    "quiz_title": "Nigerian National Identity",
    "subject": "Civic Education",
    "questions": [
      { "question_id": 1, "question_text": "Who is recognized as Nigeria's first Prime Minister?", "options": ["Nnamdi Azikiwe", "Abubakar Tafawa Balewa", "Obafemi Awolowo", "Ahmadu Bello"], "correct_option": "B" },
      { "question_id": 2, "question_text": "What color represents peace on the national flag?", "options": ["Green", "White", "Red", "Yellow"], "correct_option": "B" },
      { "question_id": 3, "question_text": "Which year did Nigeria become a republic?", "options": ["1960", "1963", "1970", "1999"], "correct_option": "B" },
      { "question_id": 4, "question_text": "What does the eagle on the coat of arms stand for?", "options": ["Dignity", "Strength", "Peace", "Agriculture"], "correct_option": "B" },
      { "question_id": 5, "question_text": "How many geopolitical zones exist in Nigeria?", "options": ["Four", "Six", "Eight", "Ten"], "correct_option": "B" },
      { "question_id": 6, "question_text": "Which tier handles local government administration?", "options": ["State", "Federal", "Third tier", "Judicial branch"], "correct_option": "C" },
      { "question_id": 7, "question_text": "What represents the rich agricultural land on our coat of arms?", "options": ["The Horses", "The Black Shield", "The Coiling Ribbon", "The Green Bloomed Flowers"], "correct_option": "B" },
      { "question_id": 8, "question_text": "Who is known as the doyen of Nigerian nationalism?", "options": ["Herbert Macaulay", "Gani Fawehinmi", "Wole Soyinka", "Chinua Achebe"], "correct_option": "A" },
      { "question_id": 9, "question_text": "What is the supreme code of law in Nigeria?", "options": ["Customary Decrees", "The Constitution", "State Edicts", "Local Ordinances"], "correct_option": "B" },
      { "question_id": 10, "question_text": "Which currency token replaced the Pound system in 1973?", "options": ["Dollar", "Naira", "Cedi", "Franc"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Create a test checking basic english grammar conjunctions."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Conjunction mechanics testing module mapped.",
  "payload": {
    "quiz_title": "Grammar Conjunctions",
    "subject": "English Language",
    "questions": [
      { "question_id": 1, "question_text": "I wanted to attend, ___ I was too tired.", "options": ["and", "but", "or", "so"], "correct_option": "B" },
      { "question_id": 2, "question_text": "You can have either the apple ___ the orange.", "options": ["nor", "or", "and", "but"], "correct_option": "B" },
      { "question_id": 3, "question_text": "He wore a thick coat ___ it was freezing.", "options": ["because", "although", "unless", "while"], "correct_option": "A" },
      { "question_id": 4, "question_text": "She studied hard, ___ she cleared the exam.", "options": ["yet", "so", "but", "since"], "correct_option": "B" },
      { "question_id": 5, "question_text": "We cannot play soccer ___ it stops raining.", "options": ["until", "because", "while", "though"], "correct_option": "A" },
      { "question_id": 6, "question_text": "He is neither smart ___ hardworking.", "options": ["or", "nor", "and", "but"], "correct_option": "B" },
      { "question_id": 7, "question_text": "Take an umbrella ___ it rains heavily.", "options": ["in case", "although", "but", "unless"], "correct_option": "A" },
      { "question_id": 8, "question_text": "Chidi won the prize ___ he practiced daily.", "options": ["unless", "for", "since", "yet"], "correct_option": "C" },
      { "question_id": 9, "question_text": "I like both milk ___ cheese products.", "options": ["or", "and", "but", "also"], "correct_option": "B" },
      { "question_id": 10, "question_text": "He managed to finish ___ starting quite late.", "options": ["despite", "although", "because", "whereas"], "correct_option": "A" }
    ]
  }
}

[INPUT]: "Test me on introductory biology cell organelle components."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Cell structures parsing layout complete.",
  "payload": {
    "quiz_title": "Cell Biology Structures",
    "subject": "Biology",
    "questions": [
      { "question_id": 1, "question_text": "Which organelle serves as the cell powerhouse?", "options": ["Nucleus", "Mitochondrion", "Ribosome", "Lysosome"], "correct_option": "B" },
      { "question_id": 2, "question_text": "Where is the genetic master blueprint DNA located?", "options": ["Cytoplasm", "Nucleus", "Golgi Body", "Cell Wall"], "correct_option": "B" },
      { "question_id": 3, "question_text": "Which asset performs structural protein synthesis?", "options": ["Ribosome", "Vacuole", "Centriole", "Chloroplast"], "correct_option": "A" },
      { "question_id": 4, "question_text": "What wrapper maintains exclusive shape inside plants?", "options": ["Cell Membrane", "Cell Wall", "Capsule", "Cytoskeleton"], "correct_option": "B" },
      { "question_id": 5, "question_text": "Which organelle packages molecular secretory materials?", "options": ["Golgi apparatus", "Endoplasmic Reticulum", "Peroxisome", "Nucleolus"], "correct_option": "A" },
      { "question_id": 6, "question_text": "What green element executes plant photosynthesis?", "options": ["Mitochondria", "Chloroplast", "Leucoplast", "Chromoplast"], "correct_option": "B" },
      { "question_id": 7, "question_text": "Which sack handles waste disposal processing?", "options": ["Ribosome", "Lysosome", "Centrosome", "Plasmid"], "correct_option": "B" },
      { "question_id": 8, "question_text": "What fluid fills space inside cell boundaries?", "options": ["Cytoplasm", "Nucleoplasm", "Sap", "Water"], "correct_option": "A" },
      { "question_id": 9, "question_text": "Which structure controls incoming traffic flux?", "options": ["Nuclear Wall", "Cell Membrane", "Capsule Layers", "Tonoplast"], "correct_option": "B" },
      { "question_id": 10, "question_text": "What huge center acts as fluid storage in plants?", "options": ["Nucleus", "Central Vacuole", "Lysosome Unit", "Golgi Sack"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Generate an economics quiz testing basic market demand laws."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Market mechanics testing sequence initiated.",
  "payload": {
    "quiz_title": "Demand Laws Analysis",
    "subject": "Economics",
    "questions": [
      { "question_id": 1, "question_text": "What path does a normal demand curve assume?", "options": ["Upward sloping", "Downward sloping", "Horizontal", "Vertical"], "correct_option": "B" },
      { "question_id": 2, "question_text": "If pricing points drop, consumer demand volume ___", "options": ["Contracts", "Expands", "Stagnates", "Disappears"], "correct_option": "B" },
      { "question_id": 3, "question_text": "What primary variable dictates demand curve shifting?", "options": ["Product price", "Consumer Income levels", "Production costs", "Tax changes"], "correct_option": "B" },
      { "question_id": 4, "question_text": "Goods consumed jointly are known as ___", "options": ["Substitutes", "Complementary goods", "Giffen items", "Inferior items"], "correct_option": "B" },
      { "question_id": 5, "question_text": "What metric charts buyer responsive sensitivity?", "options": ["Utility scales", "Elasticity of Demand", "Supply indexation", "Equilibrium margins"], "correct_option": "B" },
      { "question_id": 6, "question_text": "An elasticity coefficient exactly matching zero means:", "options": ["Perfect elastic", "Perfect inelastic", "Unitary elastic", "Relative elastic"], "correct_option": "B" },
      { "question_id": 7, "question_text": "If the price of beef jumps, the demand for fish will ___", "options": ["Contract", "Increase", "Drop completely", "Flatten out"], "correct_option": "B" },
      { "question_id": 8, "question_text": "What scheduling table aligns pricing to buying intents?", "options": ["Supply plan", "Demand Schedule", "Market Registry", "Cost Curve Chart"], "correct_option": "B" },
      { "question_id": 9, "question_text": "Which item represents an exception to demand laws?", "options": ["Normal goods", "Veblen luxury goods", "Complementary goods", "Substitutes"], "correct_option": "B" },
      { "question_id": 10, "question_text": "Market equilibrium occurs precisely when ___", "options": ["Supply exceeds demands", "Demand equals Supply values", "Prices drop to absolute zero", "Governments freeze standard trading"], "correct_option": "B" }
    ]
  }
}


#### 4. TYPE: COURSE_OUTLINE (2 REGULAR OUTLINE EXAMPLES)

[INPUT]: "I want to learn introductory web development with Python from scratch for my university semester preparation."
[OUTPUT]:
{
  "response_type": "COURSE_OUTLINE",
  "message": "I have successfully mapped out your academic skeleton timeline.",
  "payload": {
    "course_title": "Introduction to Web Development with Python",
    "subject": "Computer Science",
    "modules": [
      { "module_number": 1, "module_title": "Foundations of Backend Execution", "subtopic_titles": ["Definition of a Server", "Understanding HTTP Request Protocols", "Intro to Routing Systems"] },
      { "module_number": 2, "module_title": "Database Interactivity & Persistence", "subtopic_titles": ["SQL Foundations", "Object Relational Mappers (ORMs)", "Database Migrations"] },
      { "module_number": 3, "module_title": "API Design and Data Exchange", "subtopic_titles": ["REST Principles", "JSON Payload Structure", "Request and Response Validation"] },
      { "module_number": 4, "module_title": "Authentication and Authorization", "subtopic_titles": ["Session Handling", "Token-Based Authentication", "Role-Based Access Control"] },
      { "module_number": 5, "module_title": "Deployment, Scaling, and Monitoring", "subtopic_titles": ["Environment Configuration", "Application Logging", "Production Deployment Basics"] },
      { "module_number": 6, "module_title": "Automated Testing Suites", "subtopic_titles": ["Unit Testing Frameworks", "Integration Endpoint Testing", "Mocking Mock Objects Injection"] },
      { "module_number": 7, "module_title": "Performance Optimization & Caching", "subtopic_titles": ["Database Indexing Strategies", "Redis Cache Layers Integration", "Asynchronous Background Task Processing"] }
    ]
  }
}

[INPUT]: "Prepare a structured learning timeline for my JAMB UTME Economics exam syllabus."
[OUTPUT]:
{
  "response_type": "COURSE_OUTLINE",
  "message": "Your complete high-yield UTME Economics syllabus framework is locked in.",
  "payload": {
    "course_title": "JAMB UTME Economics Intensive",
    "subject": "Economics",
    "modules": [
      { "module_number": 1, "module_title": "Basic Economic Concepts", "subtopic_titles": ["Scarcity and Choice Systems", "Opportunity Cost Definitions", "Production Possibility Frontiers"] },
      { "module_number": 2, "module_title": "Price Determination Theory", "subtopic_titles": ["Laws of Demand and Supply Mechanics", "Determinants of Market Equilibrium", "Price Elasticity Analysis Indexes"] },
      { "module_number": 3, "module_title": "Production & Utility Structures", "subtopic_titles": ["Diminishing Marginal Utility Scales", "Factors of Production Configurations", "Cost and Revenue Curve Schemas"] },
      { "module_number": 4, "module_title": "Market Formations Profiles", "subtopic_titles": ["Perfect Competition Attributes", "Monopolistic Exploitation Structures", "Oligopoly Interactivity Models"] },
      { "module_number": 5, "module_title": "National Income Accounts", "subtopic_titles": ["Gross Domestic Product Calculations", "Income Circulation Flow Paths", "Inflation Indexation Gauges"] }
    ]
  }
}
""".strip()

# =====================================================================
# 💡 MICRO-PROMPT 2: SINGLE SUBTOPIC CONTENT GENERATOR
# =====================================================================
SUBTOPIC_CONTENT_PROMPT = """
You are the high-depth textbook parsing node of EduByte AI. Your role is to write a comprehensive textbook section for ONE specific subtopic. 
You are given the Master Module Title and a list of all accompanying subtopics to help you understand the architectural context and flow, but you must focus your core writing on the target subtopic.

### CONTENT DEPTH MANDATES
- Provide an extensive, exhaustive academic explanation for the target subtopic (minimum 350 words across 4 paragraphs).
- Use clear Markdown formatting headers, bold terms, and descriptive bullet lists.
- Provide a list of real-world code snippets or practical execution examples inside the `examples` array.

### JSON SAFETY NOTE
- When producing `content_markdown` or any string fields, do NOT use triple quotes (\"\"\"), raw code fences (```), unescaped backticks, or any constructs that would make the JSON invalid when parsed in Python. Keep strings plain and JSON-safe. Escape quotes and newlines as needed.

### OUTPUT JSON FORMAT
{
  "title": "Target Subtopic Name",
  "content_markdown": "### Conceptual Deep Dive...\\n\\nDetailed academic text here...",
  "examples": [
    "Example implementation step or code block sample configuration."
  ]
}
""".strip()

# =====================================================================
# 💡 MICRO-PROMPT 3: TARGETED MODULE ASSESSMENT BLOCK GENERATOR
# =====================================================================
QUIZ_GENERATION_PROMPT = """
You are the assessment engine of EduByte AI. Your task is to generate a rigorous, multi-option 10-question quiz explicitly matching a module and its subtopics.
You are provided with the conversation history and context records to ensure alignment with any previous explanations or specialized themes discussed with the user.

### QUIZ ANTI-BIAS RULES (CRITICAL MANDATE)
- You must generate exactly 10 questions, numbered sequentially from 1 to 10.
- 🚨 ANTI-BIAS ALGORITHM: You are FORBIDDEN from choosing the same letter for more than 3 answers across the entire quiz. Shuffling and alternating correct keys across the entire exam block is mandatory.
- Double-check that your 'correct_option' character explicitly maps to the exact index of your text array option string (A=Index 0, B=Index 1, C=Index 2, D=Index 3).
- Options arrays must be clean text choice strings without alphabetical prefixes like 'A)' or '1. '.

### JSON SAFETY NOTE
- Produce JSON-safe strings only: avoid triple quotes (\"\"\"), code fences, and raw backticks. Ensure all string fields are safe to embed in Python JSON parsing.

[INPUT]: "Give me a quick quiz on introductory Python mechanics."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your balanced python evaluation layout.",
  "payload": {
    "quiz_title": "Python Syntax Basics",
    "subject": "Computer Science",
    "questions": [
      { "question_id": 1, "question_text": "Which function outputs text to the console?", "options": ["input", "print", "output", "display"], "correct_option": "B" },
      { "question_id": 2, "question_text": "What is the correct symbol for assigning variables?", "options": ["==", ":=", "=", "->"], "correct_option": "C" },
      { "question_id": 3, "question_text": "Which data type represents a decimal number?", "options": ["Float", "Integer", "String", "Boolean"], "correct_option": "A" },
      { "question_id": 4, "question_text": "What does the keyword 'def' initiate?", "options": ["Class definition", "Loop iteration", "Function creation", "Module import"], "correct_option": "C" },
      { "question_id": 5, "question_text": "Which collection type is declared using square brackets?", "options": ["Tuple", "Dictionary", "List", "Set"], "correct_option": "C" },
      { "question_id": 6, "question_text": "How do you add a single line comment in Python?", "options": ["// Text", "/* Text */", "# Text", ""], "correct_option": "A" },
      { "question_id": 7, "question_text": "Which logical operator checks if both conditions are true?", "options": ["and", "or", "not", "xor"], "correct_option": "A" },
      { "question_id": 8, "question_text": "What does the method '.append()' do on a list?", "options": ["Removes the item", "Adds item to the end", "Sorts the elements", "Copies data structures"], "correct_option": "B" },
      { "question_id": 9, "question_text": "Which statement escapes a loop execution entirely?", "options": ["continue", "break", "pass", "exit"], "correct_option": "B" },
      { "question_id": 10, "question_text": "What does a Boolean value encapsulate?", "options": ["Numeric strings", "True or False values", "File pointers", "Character sequences"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Test my knowledge on Nigerian civic history."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Here is your balanced civic history assessment matrix.",
  "payload": {
    "quiz_title": "Nigerian National Identity",
    "subject": "Civic Education",
    "questions": [
      { "question_id": 1, "question_text": "Who is recognized as Nigeria's first Prime Minister?", "options": ["Nnamdi Azikiwe", "Abubakar Tafawa Balewa", "Obafemi Awolowo", "Ahmadu Bello"], "correct_option": "B" },
      { "question_id": 2, "question_text": "What color represents peace on the national flag?", "options": ["Green", "White", "Red", "Yellow"], "correct_option": "B" },
      { "question_id": 3, "question_text": "Which year did Nigeria become a republic?", "options": ["1960", "1963", "1970", "1999"], "correct_option": "B" },
      { "question_id": 4, "question_text": "What does the eagle on the coat of arms stand for?", "options": ["Dignity", "Strength", "Peace", "Agriculture"], "correct_option": "B" },
      { "question_id": 5, "question_text": "How many geopolitical zones exist in Nigeria?", "options": ["Four", "Six", "Eight", "Ten"], "correct_option": "B" },
      { "question_id": 6, "question_text": "Which tier handles local government administration?", "options": ["State", "Federal", "Third tier", "Judicial branch"], "correct_option": "C" },
      { "question_id": 7, "question_text": "What represents the rich agricultural land on our coat of arms?", "options": ["The Horses", "The Black Shield", "The Coiling Ribbon", "The Green Bloomed Flowers"], "correct_option": "B" },
      { "question_id": 8, "question_text": "Who is known as the doyen of Nigerian nationalism?", "options": ["Herbert Macaulay", "Gani Fawehinmi", "Wole Soyinka", "Chinua Achebe"], "correct_option": "A" },
      { "question_id": 9, "question_text": "What is the supreme code of law in Nigeria?", "options": ["Customary Decrees", "The Constitution", "State Edicts", "Local Ordinances"], "correct_option": "B" },
      { "question_id": 10, "question_text": "Which currency token replaced the Pound system in 1973?", "options": ["Dollar", "Naira", "Cedi", "Franc"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Create a test checking basic english grammar conjunctions."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Conjunction mechanics testing module mapped.",
  "payload": {
    "quiz_title": "Grammar Conjunctions",
    "subject": "English Language",
    "questions": [
      { "question_id": 1, "question_text": "I wanted to attend, ___ I was too tired.", "options": ["and", "but", "or", "so"], "correct_option": "B" },
      { "question_id": 2, "question_text": "You can have either the apple ___ the orange.", "options": ["nor", "or", "and", "but"], "correct_option": "B" },
      { "question_id": 3, "question_text": "He wore a thick coat ___ it was freezing.", "options": ["because", "although", "unless", "while"], "correct_option": "A" },
      { "question_id": 4, "question_text": "She studied hard, ___ she cleared the exam.", "options": ["yet", "so", "but", "since"], "correct_option": "B" },
      { "question_id": 5, "question_text": "We cannot play soccer ___ it stops raining.", "options": ["until", "because", "while", "though"], "correct_option": "A" },
      { "question_id": 6, "question_text": "He is neither smart ___ hardworking.", "options": ["or", "nor", "and", "but"], "correct_option": "B" },
      { "question_id": 7, "question_text": "Take an umbrella ___ it rains heavily.", "options": ["in case", "although", "but", "unless"], "correct_option": "A" },
      { "question_id": 8, "question_text": "Chidi won the prize ___ he practiced daily.", "options": ["unless", "for", "since", "yet"], "correct_option": "C" },
      { "question_id": 9, "question_text": "I like both milk ___ cheese products.", "options": ["or", "and", "but", "also"], "correct_option": "B" },
      { "question_id": 10, "question_text": "He managed to finish ___ starting quite late.", "options": ["despite", "although", "because", "whereas"], "correct_option": "A" }
    ]
  }
}

[INPUT]: "Test me on introductory biology cell organelle components."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Cell structures parsing layout complete.",
  "payload": {
    "quiz_title": "Cell Biology Structures",
    "subject": "Biology",
    "questions": [
      { "question_id": 1, "question_text": "Which organelle serves as the cell powerhouse?", "options": ["Nucleus", "Mitochondrion", "Ribosome", "Lysosome"], "correct_option": "B" },
      { "question_id": 2, "question_text": "Where is the genetic master blueprint DNA located?", "options": ["Cytoplasm", "Nucleus", "Golgi Body", "Cell Wall"], "correct_option": "B" },
      { "question_id": 3, "question_text": "Which asset performs structural protein synthesis?", "options": ["Ribosome", "Vacuole", "Centriole", "Chloroplast"], "correct_option": "A" },
      { "question_id": 4, "question_text": "What wrapper maintains exclusive shape inside plants?", "options": ["Cell Membrane", "Cell Wall", "Capsule", "Cytoskeleton"], "correct_option": "B" },
      { "question_id": 5, "question_text": "Which organelle packages molecular secretory materials?", "options": ["Golgi apparatus", "Endoplasmic Reticulum", "Peroxisome", "Nucleolus"], "correct_option": "A" },
      { "question_id": 6, "question_text": "What green element executes plant photosynthesis?", "options": ["Mitochondria", "Chloroplast", "Leucoplast", "Chromoplast"], "correct_option": "B" },
      { "question_id": 7, "question_text": "Which sack handles waste disposal processing?", "options": ["Ribosome", "Lysosome", "Centrosome", "Plasmid"], "correct_option": "B" },
      { "question_id": 8, "question_text": "What fluid fills space inside cell boundaries?", "options": ["Cytoplasm", "Nucleoplasm", "Sap", "Water"], "correct_option": "A" },
      { "question_id": 9, "question_text": "Which structure controls incoming traffic flux?", "options": ["Nuclear Wall", "Cell Membrane", "Capsule Layers", "Tonoplast"], "correct_option": "B" },
      { "question_id": 10, "question_text": "What huge center acts as fluid storage in plants?", "options": ["Nucleus", "Central Vacuole", "Lysosome Unit", "Golgi Sack"], "correct_option": "B" }
    ]
  }
}

[INPUT]: "Generate an economics quiz testing basic market demand laws."
[OUTPUT]:
{
  "response_type": "PRACTICE_QUIZ",
  "message": "Market mechanics testing sequence initiated.",
  "payload": {
    "quiz_title": "Demand Laws Analysis",
    "subject": "Economics",
    "questions": [
      { "question_id": 1, "question_text": "What path does a normal demand curve assume?", "options": ["Upward sloping", "Downward sloping", "Horizontal", "Vertical"], "correct_option": "B" },
      { "question_id": 2, "question_text": "If pricing points drop, consumer demand volume ___", "options": ["Contracts", "Expands", "Stagnates", "Disappears"], "correct_option": "B" },
      { "question_id": 3, "question_text": "What primary variable dictates demand curve shifting?", "options": ["Product price", "Consumer Income levels", "Production costs", "Tax changes"], "correct_option": "B" },
      { "question_id": 4, "question_text": "Goods consumed jointly are known as ___", "options": ["Substitutes", "Complementary goods", "Giffen items", "Inferior items"], "correct_option": "B" },
      { "question_id": 5, "question_text": "What metric charts buyer responsive sensitivity?", "options": ["Utility scales", "Elasticity of Demand", "Supply indexation", "Equilibrium margins"], "correct_option": "B" },
      { "question_id": 6, "question_text": "An elasticity coefficient exactly matching zero means:", "options": ["Perfect elastic", "Perfect inelastic", "Unitary elastic", "Relative elastic"], "correct_option": "B" },
      { "question_id": 7, "question_text": "If the price of beef jumps, the demand for fish will ___", "options": ["Contract", "Increase", "Drop completely", "Flatten out"], "correct_option": "B" },
      { "question_id": 8, "question_text": "What scheduling table aligns pricing to buying intents?", "options": ["Supply plan", "Demand Schedule", "Market Registry", "Cost Curve Chart"], "correct_option": "B" },
      { "question_id": 9, "question_text": "Which item represents an exception to demand laws?", "options": ["Normal goods", "Veblen luxury goods", "Complementary goods", "Substitutes"], "correct_option": "B" },
      { "question_id": 10, "question_text": "Market equilibrium occurs precisely when ___", "options": ["Supply exceeds demands", "Demand equals Supply values", "Prices drop to absolute zero", "Governments freeze standard trading"], "correct_option": "B" }
    ]
  }
}
""".strip()


class AIEngineService:
    @staticmethod
    def format_history_context(history_meta: List[Dict[str, Any]], current_message: str) -> str:
        context_block = "CONVERSATION HISTORY RECORDS:\n"
        for turn in history_meta:
            role = "User" if turn.get("role") == "user" else "EduByteAI"
            content = turn.get("content", "")
            context_block += f"[{role}]: {content}\n"
        context_block += f"\nNEW CLIENT CURRENT UTTERANCE: '{current_message}'\n"
        return context_block

    @staticmethod
    def _normalize_response_content(raw_content: Any) -> Any:
      # Accept dicts (already parsed), JSON strings, or None/empty values.
      if isinstance(raw_content, dict):
        return raw_content

      if raw_content is None:
        return {}

      if isinstance(raw_content, str) and raw_content.strip() == "":
        return {}

      try:
        return json.loads(raw_content)
      except (json.JSONDecodeError, TypeError) as exc:
        logging.warning("Groq response was not valid JSON: %s", exc)
        return {}

    # =====================================================================
    # 💡 NEW MICRO-FUNCTION: Generates one isolated subtopic text section
    # =====================================================================
    @classmethod
    async def generate_subtopic_text_block(
        cls, module_title: str, all_subtopics: List[str], target_subtopic: str
    ) -> Dict[str, Any]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "parent_module_title": module_title,
            "sibling_context_subtopics": all_subtopics,
            "target_subtopic_to_explain": target_subtopic
        }

        # Wrapping synchronous Groq call in asyncio.to_thread to maintain asynchronous performance
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SUBTOPIC_CONTENT_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
            max_tokens=2000
        )
        return cls._normalize_response_content(response.choices[0].message.content or "{}")

    # =====================================================================
    # 💡 NEW MICRO-FUNCTION: Generates an isolated 10-question quiz array
    # =====================================================================
    @classmethod
    async def generate_isolated_quiz_block(
        cls, module_title: str, subtopic_titles: List[str], history_meta: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "module_title": module_title,
            "subtopics_covered": subtopic_titles,
            "historical_chat_context": history_meta
        }

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": QUIZ_GENERATION_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.15,
            max_tokens=3000
        )
        raw_data = cls._normalize_response_content(response.choices[0].message.content or "{}")
        # Ensure it returns the list array directly
        return raw_data.get("questions", raw_data) if isinstance(raw_data, dict) else raw_data

    # =====================================================================
    # MAIN COHESIVE SYSTEM FLOW INTERACTION ORCHESTRATOR
    # =====================================================================
    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        compiled_contents = cls.format_history_context(history_meta, current_message)

        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": MASTER_ROUTER_PROMPT},
                    {"role": "user", "content": compiled_contents},
                ],
                response_format={"type": "json_object"},
                temperature=0.10,
            ) if client else None

            raw_content = None
            if response and getattr(response, "choices", None):
              try:
                raw_content = response.choices[0].message.content
              except Exception:
                raw_content = None

            parsed_content = cls._normalize_response_content(raw_content)

            # Default missing top-level response_type to FOLLOW_UP for safety
            if not parsed_content.get("response_type"):
              parsed_content["response_type"] = ResponseType.FOLLOW_UP.value

            # ⚡️ THE ASYNC PARALLEL GATHER INTERACTION PIPELINE
            if parsed_content.get("response_type") == ResponseType.COURSE_OUTLINE.value:
                payload_data = parsed_content.get("payload", {})
                modules_list = payload_data.get("modules", [])

                if modules_list:
                    mod_one = modules_list[0]
                    m_title = mod_one.get("module_title")
                    subs = mod_one.get("subtopic_titles", [])

                    print(f"⚡️ [Orchestrator] Firing {len(subs)} Text and 1 Quiz generation tasks parallelly...")

                    # Step A: Queue up text generation tasks for all subtopics simultaneously
                    text_tasks = [cls.generate_subtopic_text_block(m_title, subs, s) for s in subs]
                    # Step B: Queue up the quiz task concurrently
                    quiz_task = cls.generate_isolated_quiz_block(m_title, subs, history_meta)

                    # Step C: Await execution using asyncio.gather
                    gathered_results = await asyncio.gather(*text_tasks, quiz_task)

                    completed_subtopics = gathered_results[:-1]
                    completed_quiz = gathered_results[-1]

                    # Step D: Construct the hydrated module dictionary matching ModuleContentPayload
                    hydrated_module_one = {
                        "response_type": ResponseType.MODULE_CONTENT.value,
                        "module_number": mod_one.get("module_number", 1),
                        "module_title": m_title,
                        "subtopics": completed_subtopics,
                        "module_quiz": completed_quiz
                    }

                    # Overwrite index 0 with the fully populated component structure
                    parsed_content["payload"]["modules"][0] = hydrated_module_one

            # Inject response discriminator values to satisfy Pydantic validations cleanly
            if "response_type" in parsed_content and "payload" in parsed_content:
              if isinstance(parsed_content["payload"], dict):
                parsed_content["payload"].setdefault("response_type", parsed_content["response_type"])

            # Lightweight quiz validator: find any quiz arrays and validate count and balance
            def _validate_quiz_questions(questions: list[dict]) -> Tuple[bool, str]:
              if not isinstance(questions, list):
                return False, "questions must be a list"
              if len(questions) != 10:
                return False, "quiz must contain exactly 10 questions"
              counts = {"A": 0, "B": 0, "C": 0, "D": 0}
              for q in questions:
                opt = q.get("correct_option")
                if opt in counts:
                  counts[opt] += 1
              if any(v > 4 for v in counts.values()):
                return False, "correct options distribution is unbalanced"
              return True, ""

            # Scan payload for quiz lists at common locations
            def _scan_and_validate(obj: Any) -> Tuple[bool, str]:
              if isinstance(obj, dict):
                # direct practice quiz
                q = obj.get("questions")
                if q is not None:
                  return _validate_quiz_questions(q)
                # module content with module_quiz
                mq = obj.get("module_quiz")
                if mq is not None:
                  return _validate_quiz_questions(mq)
                # nested modules list
                mods = obj.get("modules")
                if mods:
                  for m in mods:
                    ok, reason = _scan_and_validate(m)
                    if not ok:
                      return ok, reason
              elif isinstance(obj, list):
                for item in obj:
                  ok, reason = _scan_and_validate(item)
                  if not ok:
                    return ok, reason
              return True, ""

            ok, reason = _scan_and_validate(parsed_content.get("payload"))
            if not ok:
              # Attempt automated regeneration and rebalancing before asking user for follow-up
              def _find_quiz_location(obj: Any) -> Tuple[str, dict, str, list] | None:
                # returns (kind, parent_dict, module_title, subtopics_list)
                if isinstance(obj, dict):
                  if obj.get("questions") is not None:
                    return ("practice", obj, obj.get("quiz_title", "General"), [])
                  if obj.get("module_quiz") is not None:
                    # try to infer module title and subtopics
                    subs = []
                    subs_raw = obj.get("subtopics") or obj.get("subtopic_titles")
                    if isinstance(subs_raw, list):
                      for s in subs_raw:
                        if isinstance(s, dict):
                          subs.append(s.get("title"))
                        else:
                          subs.append(s)
                    return ("module", obj, obj.get("module_title") or obj.get("title", "Module"), subs)
                  mods = obj.get("modules")
                  if mods:
                    for m in mods:
                      found = _find_quiz_location(m)
                      if found:
                        return found
                elif isinstance(obj, list):
                  for item in obj:
                    found = _find_quiz_location(item)
                    if found:
                      return found
                return None

              def _rebalance_questions(questions: list[dict]) -> list[dict]:
                counts = {"A": 0, "B": 0, "C": 0, "D": 0}
                for q in questions:
                  opt = q.get("correct_option")
                  if opt in counts:
                    counts[opt] += 1

                # while any count >4, move some to the least frequent option
                letters = ["A", "B", "C", "D"]
                idx = 0
                # Create a mutable list of indices by option
                while any(v > 4 for v in counts.values()):
                  # find an overrepresented letter
                  over = max(counts, key=lambda k: counts[k])
                  under = min(counts, key=lambda k: counts[k])
                  # find a question index with over
                  for q in questions:
                    if q.get("correct_option") == over:
                      q["correct_option"] = under
                      counts[over] -= 1
                      counts[under] += 1
                      break
                  idx += 1
                  if idx > 20:
                    break
                return questions

              loc = _find_quiz_location(parsed_content.get("payload"))
              regenerated = False
              if loc:
                kind, parent, m_title, subs = loc
                # Try regenerating up to 2 times
                for attempt in range(2):
                  try:
                    new_questions = await cls.generate_isolated_quiz_block(m_title or "General", subs or [], history_meta)
                  except Exception as ex:
                    new_questions = None
                  if new_questions:
                    valid, why = _validate_quiz_questions(new_questions)
                    if valid:
                      if kind == "practice":
                        parent["questions"] = new_questions
                      else:
                        parent["module_quiz"] = new_questions
                      regenerated = True
                      break

                # If regeneration failed, attempt lightweight rebalancing if questions exist
                if not regenerated and loc:
                  existing_qs = parent.get("questions") or parent.get("module_quiz")
                  if isinstance(existing_qs, list):
                    balanced = _rebalance_questions(existing_qs)
                    # final validate
                    valid, why = _validate_quiz_questions(balanced)
                    if valid:
                      if kind == "practice":
                        parent["questions"] = balanced
                      else:
                        parent["module_quiz"] = balanced
                      regenerated = True

              if not regenerated:
                # as last resort, ask follow-up
                return EduByteAIResponse(
                  response_type=ResponseType.FOLLOW_UP,
                  message="Generated quiz failed validation and automatic recovery.",
                  payload=FollowUpPayload(response_type=ResponseType.FOLLOW_UP, clarification_text=f"Quiz validation failed: {reason}")
                )

            return EduByteAIResponse.model_validate(parsed_content)

        except Exception as e:
            print(f"\n❌ [AI_ENGINE_ERROR] Pipeline Failure: {str(e)}")
            import traceback
            traceback.print_exc()

            return EduByteAIResponse(
                response_type=ResponseType.FOLLOW_UP,
                message="I encountered an extraction error setting up your track paths. Could you clarify your syllabus details?",
                payload=FollowUpPayload(response_type=ResponseType.FOLLOW_UP, clarification_text="Please refine your targeted learning request.")
            )