import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Tuple

from dotenv import load_dotenv
from groq import Groq, RateLimitError

from app.schemas.schemas import (
    CourseOutlinePayload,
    EduByteAIResponse,
    FollowUpPayload,
    ModuleContentPayload,
    ModuleOutline,
    ResponseType,
)

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

SUBTOPIC_MIN_WORDS = 500
SUBTOPIC_MIN_PARAGRAPHS = 4

SUBTOPIC_CONTENT_PROMPT = """
You are the high-depth textbook parsing node of EduByte AI. Your role is to write a comprehensive textbook section for ONE specific subtopic.
You are given the Master Module Title and a list of all accompanying subtopics to understand the architectural context and flow, but you must focus your core writing on the target subtopic.

### CONTENT DEPTH MANDATES
- Provide an extensive, exhaustive academic explanation for the target subtopic.
- `content_markdown` must contain at least 500 words.
- `content_markdown` must contain at least 4 distinct paragraphs separated by blank lines.
- Use clear Markdown formatting headers, bold terms, and descriptive bullet lists inside `content_markdown`.
- Provide real-world code snippets, solved examples, practical execution steps, or applied scenarios inside the `examples` array.
- The `examples` array may contain 0 to 5 entries depending on topic requirements, but each entry must be concrete and useful when included.
- CRITICAL: Never truncate text, use ellipses, or output shorthand summaries. Write every section completely with full academic rigor.

### JSON-SAFETY RULES
- Return only one valid JSON object.
- Return exactly these keys: `title`, `content_markdown`, and `examples`.
- Do not wrap the JSON in Markdown.
- Do not use raw triple-backtick code fences. If code is needed, place it as a JSON string inside the `examples` array with escaped newline characters.
- Inline code backticks are allowed only when the final JSON string remains valid.

### OUTPUT JSON FORMAT
{
  "title": "Target Subtopic Name",
  "content_markdown": "### Conceptual Deep Dive\\n\\nDetailed academic text here with at least 500 words across at least 4 paragraphs.",
  "examples": [
    "Example implementation step, solved scenario, command sequence, or code sample."
  ]
}

### FEW-SHOT DEPTH CALIBRATION EXAMPLE
Use the following example as a direct template for expected depth, paragraph count, JSON structure, Markdown richness, and complete lack of placeholders.

INPUT CONTEXT:
- Master Module Title: Modern JavaScript Engine Architecture
- Target Subtopic: Asynchronous Programming with Async/Await
- Accompanying Subtopics: ["The Event Loop and Call Stack", "Promises and Futures", "Asynchronous Programming with Async/Await", "Advanced Exception Handling in Async Environments"]

EXPECTED OUTPUT:
{
  "title": "Asynchronous Programming with Async/Await",
  "content_markdown": "### Conceptual Deep Dive\\n\\nAsynchronous programming with `async` and `await` is one of the most important readability improvements in modern JavaScript because it allows developers to express non-blocking operations in a structure that resembles ordinary sequential code. Before this syntax became standard, JavaScript developers often coordinated network calls, timer operations, and file I/O through nested callbacks. That pattern worked technically, but it made control flow hard to inspect because the main business logic became scattered across several callback layers. Promises improved the situation by representing a future value as an object that could be chained with `.then()` and `.catch()`, yet Promise chains could still become difficult to follow when a workflow required multiple dependent steps, conditional branches, and centralized error handling. `async` and `await` solve this readability problem by letting the programmer write a clear sequence of operations while the runtime continues to execute those operations through the event loop rather than blocking the main thread.\\n\\nA function declared with the `async` keyword always returns a Promise, even when the function appears to return an ordinary value. If the function returns a number, string, object, or array, JavaScript automatically wraps that value in a resolved Promise. If the function throws an exception, JavaScript converts that exception into a rejected Promise. Inside the function, the `await` keyword pauses only the execution of that async function until the awaited Promise settles. This distinction is essential: `await` does not freeze the browser, stop Node.js from handling other requests, or lock the JavaScript engine. Instead, the paused function yields control so other queued tasks and microtasks can continue. When the awaited Promise resolves, the engine schedules the continuation of the async function and injects the resolved value back into the local expression where `await` was used.\\n\\nThe underlying execution model depends on the relationship between the call stack, task queue, and microtask queue. When an awaited operation begins, the current async function frame is suspended, and the JavaScript engine preserves the relevant local state needed to resume execution later. Promise resolution callbacks are placed into the microtask queue, which has priority over ordinary macrotasks such as timers and user-interface events. This design makes async/await efficient for I/O-heavy programs because the engine can keep processing other work while external systems, such as web APIs, database drivers, or file systems, complete their operations. **Error handling** also becomes more coherent because rejected Promises can be caught with ordinary `try` and `catch` blocks around awaited statements, allowing a single error boundary to cover several asynchronous operations.\\n\\nAlthough async/await improves clarity, it does not automatically optimize concurrency. A common performance mistake is awaiting independent operations one after another, which forces them to run sequentially even when they could have started at the same time. For example, if a dashboard needs a user profile, notification count, and billing status, those three requests should usually be launched together and awaited with `Promise.all()` so the total wait time is closer to the slowest individual request rather than the sum of all three. Developers must therefore distinguish between **dependent awaits**, where one result is needed before starting the next operation, and **independent awaits**, where parallel execution is correct.\\n\\nKey practical rules include:\\n- Use `try` and `catch` around awaited operations that may fail.\\n- Start independent Promises before awaiting them together.\\n- Avoid using `await` inside loops unless each iteration truly depends on the previous one.\\n- Return meaningful errors from async functions so callers can recover intelligently.",
  "examples": [
    "// Example 1: Sequential async/await with explicit error handling\\nasync function fetchUserProfile(userId) {\\n  try {\\n    const response = await fetch(`https://api.example.com/users/${userId}`);\\n    if (!response.ok) {\\n      throw new Error(`HTTP error: ${response.status}`);\\n    }\\n    return await response.json();\\n  } catch (error) {\\n    console.error('Failed to retrieve user profile:', error.message);\\n    throw error;\\n  }\\n}",
    "// Example 2: Parallel async operations for independent dashboard requests\\nasync function getDashboardData(userId) {\\n  const profileRequest = fetch(`https://api.example.com/users/${userId}`);\\n  const notificationsRequest = fetch(`https://api.example.com/users/${userId}/notifications`);\\n  const billingRequest = fetch(`https://api.example.com/users/${userId}/billing`);\\n\\n  const [profileRes, notificationsRes, billingRes] = await Promise.all([\\n    profileRequest,\\n    notificationsRequest,\\n    billingRequest\\n  ]);\\n\\n  return {\\n    profile: await profileRes.json(),\\n    notifications: await notificationsRes.json(),\\n    billing: await billingRes.json()\\n  };\\n}"
  ]
}
""".strip()

QUIZ_GENERATION_PROMPT = """
Generate a JSON object for a 10-question multiple-choice quiz.

Requirements:
- Exactly 10 questions.
- Plain text options only.
- correct_option must be A, B, C, or D.
- No answer letter should appear more than 3 times.
- Keep all strings JSON-safe.

### EVALUATION QUIZ CRITICAL BALANCING CONSTRAINTS
- For any generated quiz, you must provide exactly 10 questions numbered 1 to 10.
- 🚨 ANTI-BIAS ALGORITHM: You are FORBIDDEN from choosing the same letter for more than 3 answers across the entire quiz.
- You must actively shuffle and alternate the correct option keys. Aim for a balanced distribution across the entire exam block (e.g., approximately two or three As, Bs, Cs, and Ds).
- Double-check that your 'correct_option' character explicitly maps to the exact index of your text array option string (A=Index 0, B=Index 1, C=Index 2, D=Index 3).
- Options arrays must be clean text choice strings without alphabetical prefixes like 'A)', 'B.', or 'A. '.

examples:

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

    @staticmethod
    def _build_rate_limit_fallback_response(current_message: str) -> EduByteAIResponse:
        lowered_message = current_message.lower()
        if any(keyword in lowered_message for keyword in ["learn", "study", "course", "roadmap", "syllabus", "outline"]):
            modules = [
                ModuleOutline(module_number=1, module_title="Python Foundations", subtopic_titles=["Variables and Data Types", "Control Flow", "Functions and Modules"]),
                ModuleOutline(module_number=2, module_title="Web Basics", subtopic_titles=["HTTP Concepts", "Client-Server Flow", "Request and Response Lifecycle"]),
                ModuleOutline(module_number=3, module_title="Backend Frameworks", subtopic_titles=["Flask Basics", "Routing and Views", "Templates and Forms"]),
                ModuleOutline(module_number=4, module_title="Data and APIs", subtopic_titles=["Database Fundamentals", "CRUD APIs", "JSON Serialization"]),
                ModuleOutline(module_number=5, module_title="Deployment and Testing", subtopic_titles=["Environment Variables", "Testing Strategies", "Deployment Basics"]),
            ]
            return EduByteAIResponse(
                response_type=ResponseType.COURSE_OUTLINE,
                message="I drafted a local course outline because the model hit its request limit.",
                payload=CourseOutlinePayload(
                    response_type=ResponseType.COURSE_OUTLINE,
                    course_title="Introductory Backend Web Development with Python",
                    subject="Backend Development",
                    modules=modules,  # type: ignore[arg-type]
                ),
            )

        return EduByteAIResponse(
            response_type=ResponseType.FOLLOW_UP,
            message="I hit a temporary model request limit.",
            payload=FollowUpPayload(
                response_type=ResponseType.FOLLOW_UP,
                clarification_text="Please try again in a few minutes, or send a shorter request so I can answer locally.",
            ),
        )

    @staticmethod
    def _normalize_outline_payload(payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload

        normalized = dict(payload)
        if "title" in normalized and "course_title" not in normalized:
            normalized["course_title"] = normalized.pop("title")

        modules = normalized.get("modules")
        if isinstance(modules, list):
            normalized_modules = []
            for module in modules:
                if not isinstance(module, dict):
                    normalized_modules.append(module)
                    continue

                normalized_module = dict(module)
                if "module_id" in normalized_module and "module_number" not in normalized_module:
                    normalized_module["module_number"] = normalized_module.pop("module_id")
                if "module_name" in normalized_module and "module_title" not in normalized_module:
                    normalized_module["module_title"] = normalized_module.pop("module_name")
                if "subtopics" in normalized_module and "subtopic_titles" not in normalized_module:
                    subtopics = normalized_module.pop("subtopics")
                    if isinstance(subtopics, list):
                        normalized_module["subtopic_titles"] = [
                            item.get("title") if isinstance(item, dict) else item for item in subtopics
                        ]
                if "subtopic_list" in normalized_module and "subtopic_titles" not in normalized_module:
                    subtopics = normalized_module.pop("subtopic_list")
                    if isinstance(subtopics, list):
                        normalized_module["subtopic_titles"] = [
                            item.get("title") if isinstance(item, dict) else item for item in subtopics
                        ]

                normalized_modules.append(normalized_module)

            normalized["modules"] = normalized_modules

        return normalized

    @staticmethod
    def _content_depth_stats(content_markdown: Any) -> Tuple[int, int]:
        if not isinstance(content_markdown, str):
            return 0, 0

        words = re.findall(r"\b[\w'-]+\b", content_markdown)
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", content_markdown.strip())
            if paragraph.strip()
        ]
        return len(words), len(paragraphs)

    @classmethod
    def _subtopic_content_meets_depth(cls, content_block: Any) -> bool:
        if not isinstance(content_block, dict):
            return False
        word_count, paragraph_count = cls._content_depth_stats(content_block.get("content_markdown"))
        return word_count >= SUBTOPIC_MIN_WORDS and paragraph_count >= SUBTOPIC_MIN_PARAGRAPHS

    @classmethod
    async def generate_subtopic_text_block(cls, module_title: str, all_subtopics: List[str], target_subtopic: str) -> Dict[str, Any]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "parent_module_title": module_title,
            "sibling_context_subtopics": all_subtopics,
            "target_subtopic_to_explain": target_subtopic,
        }

        latest_content: Dict[str, Any] = {}
        user_content = json.dumps(input_payload)

        for attempt in range(3):
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SUBTOPIC_CONTENT_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0.25,
                max_tokens=3500,
            )
            normalized_content = cls._normalize_response_content(response.choices[0].message.content or "{}")
            latest_content = normalized_content if isinstance(normalized_content, dict) else {}

            if cls._subtopic_content_meets_depth(latest_content):
                return latest_content

            word_count, paragraph_count = cls._content_depth_stats(latest_content.get("content_markdown"))
            user_content = json.dumps(
                {
                    **input_payload,
                    "retry_instruction": (
                        f"The previous output had {word_count} words and {paragraph_count} paragraphs. "
                        f"Regenerate the same target subtopic with at least {SUBTOPIC_MIN_WORDS} words "
                        f"and at least {SUBTOPIC_MIN_PARAGRAPHS} paragraphs in content_markdown."
                    ),
                    "attempt": attempt + 2,
                }
            )

        return latest_content

    @classmethod
    async def generate_isolated_quiz_block(cls, module_title: str, subtopic_titles: List[str], history_meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not client:
            raise RuntimeError("Groq Client uninitialized.")

        input_payload = {
            "module_title": module_title,
            "subtopics_covered": subtopic_titles,
            "historical_chat_context": history_meta,
        }

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": QUIZ_GENERATION_PROMPT},
                {"role": "user", "content": json.dumps(input_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.17,
            max_tokens=2000,
        )

        raw_data = cls._normalize_response_content(response.choices[0].message.content or "{}")
        if not isinstance(raw_data, dict):
            return []

        payload = raw_data.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("questions"), list):
            return payload["questions"]

        questions = raw_data.get("questions")
        if isinstance(questions, list):
            return questions

        return []

    @classmethod
    async def generate_module_content_block(
        cls,
        *,
        module_number: int,
        module_title: str,
        subtopic_titles: List[str],
        history_meta: List[Dict[str, Any]],
    ) -> ModuleContentPayload:
        text_tasks = [
            cls.generate_subtopic_text_block(module_title, subtopic_titles, subtopic_title)
            for subtopic_title in subtopic_titles
        ]
        quiz_task = cls.generate_isolated_quiz_block(module_title, subtopic_titles, history_meta)
        gathered_results = await asyncio.gather(*text_tasks, quiz_task)
        completed_quiz = gathered_results[-1]

        return ModuleContentPayload.model_validate(
            {
                "response_type": ResponseType.MODULE_CONTENT.value,
                "module_number": module_number,
                "module_title": module_title,
                "subtopics": gathered_results[:-1],
                "module_quiz": completed_quiz,
            }
        )

    @classmethod
    async def process_user_intent(cls, current_message: str, history_meta: List[Dict[str, Any]]) -> EduByteAIResponse:
        compiled_contents = cls.format_history_context(history_meta, current_message)

        response = None
        if client:
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
                )
            except RateLimitError:
                logging.warning("Groq rate limit reached; using local fallback response.")
                return cls._build_rate_limit_fallback_response(current_message)

        raw_content = None
        if response and getattr(response, "choices", None):
            try:
                raw_content = response.choices[0].message.content
            except Exception:
                raw_content = None

        parsed_content = cls._normalize_response_content(raw_content)
        if isinstance(parsed_content, dict) and ("message" not in parsed_content or "payload" not in parsed_content):
            alias_map = {
                "course_outline": ResponseType.COURSE_OUTLINE,
                "practice_quiz": ResponseType.PRACTICE_QUIZ,
                "general_question_answer": ResponseType.GENERAL_QUESTION_ANSWER,
                "follow_up": ResponseType.FOLLOW_UP,
            }
            for alias_key, response_type in alias_map.items():
                alias_payload = parsed_content.get(alias_key)
                if isinstance(alias_payload, dict):
                    parsed_content = {
                        "response_type": response_type.value,
                        "message": alias_payload.get("message") or parsed_content.get("message") or "",
                        "payload": cls._normalize_outline_payload(alias_payload.get("payload") or {k: v for k, v in alias_payload.items() if k != "message"}),
                    }
                    break

        if isinstance(parsed_content, dict) and not parsed_content.get("message"):
            parsed_content["message"] = ""

        if isinstance(parsed_content, dict) and "payload" not in parsed_content:
            parsed_content["payload"] = {}

        if not parsed_content.get("response_type"):
            parsed_content["response_type"] = ResponseType.FOLLOW_UP.value

        if parsed_content.get("response_type") == ResponseType.COURSE_OUTLINE.value:
            payload_data = parsed_content.get("payload", {})
            modules_list = payload_data.get("modules", [])
            if modules_list:
                mod_one = modules_list[0]
                m_title = mod_one.get("module_title") or "Untitled Module"
                raw_subtopics = mod_one.get("subtopic_titles", [])
                subs = raw_subtopics if isinstance(raw_subtopics, list) else []
                print(f"⚡️ [Orchestrator] Firing {len(subs)} Text and 1 Quiz generation tasks parallelly...")

                try:
                    module_content = await cls.generate_module_content_block(
                        module_number=mod_one.get("module_number", 1),
                        module_title=m_title,
                        subtopic_titles=subs,
                        history_meta=history_meta,
                    )
                except Exception:
                    logging.exception("Failed to hydrate first module content.")
                else:
                    parsed_content["payload"]["modules"][0] = module_content.model_dump(mode="json")

        if isinstance(parsed_content.get("payload"), dict):
            parsed_content["payload"].setdefault("response_type", parsed_content.get("response_type"))

        def _validate_quiz_questions(questions: list[dict]) -> Tuple[bool, str]:
            if not isinstance(questions, list):
                return False, "questions must be a list"
            if len(questions) < 1:
                return False, "quiz must contain at least 1 question"
            counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for question in questions:
                opt = question.get("correct_option")
                if opt in counts:
                    counts[opt] += 1
            if any(value > 4 for value in counts.values()):
                return False, "correct options distribution is unbalanced"
            return True, ""

        def _scan_and_validate(obj: Any) -> Tuple[bool, str]:
            if isinstance(obj, dict):
                questions = obj.get("questions")
                if isinstance(questions, list):
                    return _validate_quiz_questions(questions)
                module_quiz = obj.get("module_quiz")
                if isinstance(module_quiz, list):
                    return _validate_quiz_questions(module_quiz)
                modules = obj.get("modules")
                if isinstance(modules, list):
                    for module in modules:
                        ok, reason = _scan_and_validate(module)
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
            def _find_quiz_location(obj: Any) -> Tuple[str, dict, str, list] | None:
                if isinstance(obj, dict):
                    if obj.get("questions") is not None:
                        return ("practice", obj, obj.get("quiz_title", "General"), [])
                    if obj.get("module_quiz") is not None:
                        subtopics = []
                        raw_subtopics = obj.get("subtopics") or obj.get("subtopic_titles")
                        if isinstance(raw_subtopics, list):
                            for subtopic in raw_subtopics:
                                if isinstance(subtopic, dict):
                                    subtopics.append(subtopic.get("title"))
                                else:
                                    subtopics.append(subtopic)
                        return ("module", obj, obj.get("module_title") or obj.get("title", "Module"), subtopics)
                    modules = obj.get("modules")
                    if isinstance(modules, list):
                        for module in modules:
                            found = _find_quiz_location(module)
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
                for question in questions:
                    opt = question.get("correct_option")
                    if opt in counts:
                        counts[opt] += 1

                attempts = 0
                while any(value > 4 for value in counts.values()):
                    over = max(counts, key=lambda key: counts[key])
                    under = min(counts, key=lambda key: counts[key])
                    for question in questions:
                        if question.get("correct_option") == over:
                            question["correct_option"] = under
                            counts[over] -= 1
                            counts[under] += 1
                            break
                    attempts += 1
                    if attempts > 20:
                        break
                return questions

            location = _find_quiz_location(parsed_content.get("payload"))
            regenerated = False
            if location:
                kind, parent, module_title, subtopics = location
                for _ in range(2):
                    try:
                        new_questions = await cls.generate_isolated_quiz_block(module_title or "General", subtopics or [], history_meta)
                    except Exception:
                        new_questions = None
                    if new_questions:
                        valid, _ = _validate_quiz_questions(new_questions)
                        if valid:
                            if kind == "practice":
                                parent["questions"] = new_questions
                            else:
                                parent["module_quiz"] = new_questions
                            regenerated = True
                            break

                if not regenerated:
                    existing_questions = parent.get("questions") or parent.get("module_quiz")
                    if isinstance(existing_questions, list):
                        balanced = _rebalance_questions(existing_questions)
                        valid, _ = _validate_quiz_questions(balanced)
                        if valid:
                            if kind == "practice":
                                parent["questions"] = balanced
                            else:
                                parent["module_quiz"] = balanced
                            regenerated = True

            if not regenerated:
                return EduByteAIResponse(
                    response_type=ResponseType.FOLLOW_UP,
                    message="Generated quiz failed validation and automatic recovery.",
                    payload=FollowUpPayload(
                        response_type=ResponseType.FOLLOW_UP,
                        clarification_text=f"Quiz validation failed: {reason}",
                    ),
                )

        return EduByteAIResponse.model_validate(parsed_content)
