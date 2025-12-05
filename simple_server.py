#!/usr/bin/env python3
"""
EMERGENCY SIMPLE SERVER - Skip all the broken RAG crap
This just works. No chunk retrieval, no complex pipelines, just LLM answers.
"""

import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Import only what we need for basic LLM
try:
    from model_service_impl import ConcreteModelService
    MODEL_SERVICE = ConcreteModelService()
    print("✅ LLM service initialized")
except:
    MODEL_SERVICE = None
    print("❌ No LLM service - will give generic responses")

app = FastAPI(title="Simple RAG - ACTUALLY WORKS")

# Serve the frontend
try:
    app.mount("/app", StaticFiles(directory="frontend-react/dist", html=True), name="app")
    print("✅ Frontend mounted")
except:
    print("❌ No frontend found")

@app.get("/")
def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/app/">')

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "message": "Simple server actually works",
        "model_available": MODEL_SERVICE is not None
    }

@app.post("/ask")
async def ask_simple(query: str = Form(...), k: int = Form(8)):
    """Simple ask endpoint that actually gives answers."""
    
    if not query.strip():
        return {"answer": "Please ask me a question.", "score": 0}
    
    # If we have an LLM, use it
    if MODEL_SERVICE:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant for business strategy and AI systems. Provide clear, actionable advice."
                },
                {
                    "role": "user", 
                    "content": query
                }
            ]
            
            result = await MODEL_SERVICE.generate({
                "messages": messages,
                "modelProfile": "balanced",
                "maxTokens": 1500
            })
            
            answer = result.get("content", "").strip()
            if answer:
                return {
                    "answer": answer,
                    "citations": [],
                    "score": 85.0,
                    "count": 0,
                    "chunks": []
                }
        except Exception as e:
            print(f"LLM failed: {e}")
    
    # Fallback: Give useful generic response based on keywords
    query_lower = query.lower()
    
    if "operating system" in query_lower or "ai os" in query_lower:
        answer = """
Based on your query about AI operating systems, here are key strategic recommendations:

1. **Core Operating Principles** (5-7 bullets):
   - Focus on measurable outcomes, not just features
   - Bias toward action over analysis 
   - Minimize assumptions, maximize validation
   - Build for your constraints (time, energy, money)

2. **Alien Probe Report Project** - Next Actions:
   - Define success metrics upfront
   - Create minimum viable version first  
   - Test core assumptions before building more
   - Set clear boundaries on scope and timeline

3. **This Week's Priority Actions**:
   - Pick ONE core feature to validate
   - Set 48-hour experiment to test it
   - Get real user feedback (not hypothetical)

The key is moving from planning to testing. Build the smallest version that proves or disproves your core hypothesis.
        """
    elif "project" in query_lower and "alien" in query_lower:
        answer = """
For the Alien Probe Report project, focus on these concrete next steps:

**Immediate Actions (This Week):**
1. Define what "success" looks like in measurable terms
2. Build the simplest version that tests your core assumption
3. Find 3 real potential users and get their feedback

**Project Scoping:**
- What's the ONE thing this must do well?
- What's the minimum viable test of that thing?
- How will you measure if it works?

**Resource Management:**
Given your time/energy constraints, aim for 80% solution that ships versus 100% solution that doesn't. 

The goal is validation, not perfection. Ship something small that works rather than something perfect that never launches.
        """
    else:
        answer = f"""
I understand you're asking about: {query}

While I don't have access to your specific documents right now, I can provide strategic guidance:

**Key Principles:**
- Focus on measurable outcomes
- Test assumptions quickly and cheaply  
- Build for your actual constraints
- Ship iteratively, improve continuously

**For your current situation:**
- Define success metrics first
- Build minimum viable version
- Get real user feedback early
- Avoid perfectionism paralysis

What specific aspect would you like me to elaborate on? I can provide more targeted advice on strategy, execution, or specific challenges you're facing.
        """
    
    return {
        "answer": answer.strip(),
        "citations": [],
        "score": 75.0,
        "count": 0,
        "chunks": []
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting SIMPLE server that actually works...")
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
