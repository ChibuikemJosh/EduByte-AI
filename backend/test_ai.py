import asyncio
import os
import sys

# Ensure the backend root folder is added to your Python path so imports resolve cleanly
# Insert the `backend` folder first so `app` package imports resolve when running this script.
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.ai_engine import AIEngineService
from app.schemas.schemas import (
    EduByteAIResponse, 
    ResponseType, 
    CourseOutlinePayload, 
    ModuleContentPayload
)


async def run_ai_engine_test():
    print("🚀 Initializing EduByte AI Engine Integration Test...")
    
    current_user_message = "I want to learn introductory backend web development with Python Fast API from scratch for my school project. I want to learn it as a complete beginner to fastapi and backend web development but have used python before. I want to learn the basics and everything about python fastapi and backend web development that is needed. I want to learn it within 4 weeks or 1 month. I want to learn the basics of buiulding an entire backend with database too for a website. I have not used database and web development frameworks ever before and i am looking to learn the basics of backen web development, fastapi, and datbase integration with sqlite and yeah recommend aproject after generating the course i want you to generate please do not ask me any othwer follow up question i have answered almost all of them"
    mock_chat_history = []
    try:
        print("\n📡 Dispatching pipeline generation call to Groq...")
        
        response: EduByteAIResponse = await AIEngineService.process_user_intent(
            current_message=current_user_message,
            history_meta=mock_chat_history
        )
        
        print("\n" + "="*50)
        print("✅ SUCCESS: Inference and Schema Validation Succeeded!")
        print("="*50)
        print(f"Parsed Response Type : {response.response_type}")
        print(f"Conversational Message : {response.message}")
        
        # 💡 FIX 1: Use isinstance to narrow down the union type for Pylance
        if isinstance(response.payload, CourseOutlinePayload):
            print(f"Course Generated Title: {response.payload.course_title}")
            print(f"Academic Subject Flag : {response.payload.subject}")
            print(f"Total Modules Created : {len(response.payload.modules)}")
            print("="*50)
            
            if response.payload.modules:
                module_one = response.payload.modules[0]
                
                # 💡 FIX 2: Narrow down the union type for the specific module inside the list
                if isinstance(module_one, ModuleContentPayload):
                    print("\n💎 TWO-STEP HYDRATION VERIFICATION: SUCCESS!")
                    print(f"📦 Module 1 Content Hook: {module_one.module_title}")
                    print(f"📚 Subtopics Count     : {len(module_one.subtopics)}")
                    print(f"📝 Quiz Questions Count : {len(module_one.module_quiz)} (Target: 10)")
                    
                    print("\n🎯 Anti-Bias Option Sample Layout:")
                    for q in module_one.module_quiz[:3]:
                        print(f"  - Q{q.question_id}: {q.question_text[:50]}... -> [Correct: Option {q.correct_option}]")
                else:
                    # Pylance knows module_one is a ModuleOutline here
                    print("\nℹ️ Module 1 returned as a structural outline skeleton.")
                    print(f"Titles found: {module_one.subtopic_titles}")
        else:
            print(f"\n⚠️ The engine returned a non-course layout: {response.response_type}")
            print(f"Payload Data: {response.payload}")

    except Exception as e:
        print("\n" + "❌"*30)
        print("FATAL CRASH: The engine threw an operational validation error!")
        print(f"Error Details: {str(e)}")
        print("❌"*30)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_ai_engine_test())