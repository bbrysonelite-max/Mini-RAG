#!/usr/bin/env python3
"""
End-to-end integration test for RAG system.
Tests: Chunks → Retrieval → Context → LLM → Answer
"""
import os
import sys
import asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from raglite import load_chunks
from rag_pipeline import RAGPipeline
from model_service_impl import ConcreteModelService

async def test_end_to_end():
    print("\n" + "="*70)
    print("END-TO-END RAG INTEGRATION TEST")
    print("="*70)
    
    # Step 1: Load chunks
    print("\n[1/6] Loading chunks from JSONL...")
    chunks = load_chunks('out/chunks.jsonl')
    print(f"✓ Loaded {len(chunks)} chunks")
    
    # Step 2: Initialize RAG pipeline
    print("\n[2/6] Initializing RAG pipeline...")
    pipeline = RAGPipeline(chunks_path='out/chunks.jsonl')
    print(f"✓ Pipeline ready with {len(pipeline.chunks)} chunks")
    
    # Step 3: Test retrieval
    print("\n[3/6] Testing retrieval...")
    test_query = "What are the key principles for a solo entrepreneur building AI systems?"
    
    result = await pipeline.retrieve({
        'projectId': 'default',
        'userQuery': test_query,
        'topK_bm25': 10,
        'maxChunksForContext': 5,
    })
    
    chunk_entries = result.get('chunks', [])
    print(f"✓ Retrieved {len(chunk_entries)} chunks")
    print(f"  Abstained: {result.get('abstained', False)}")
    
    if result.get('abstained'):
        print(f"  ✗ Abstention reason: {result.get('abstentionReason')}")
        return False
    
    # Step 4: Extract context (simulate server.py)
    print("\n[4/6] Extracting context...")
    context_sections = []
    
    for idx, entry in enumerate(chunk_entries):
        chunk_meta = entry.get('chunk', {}) or {}
        content = (
            chunk_meta.get('text', '') or 
            chunk_meta.get('content', '')
        ).strip()
        
        if content:
            context_sections.append(f"Source {idx+1}:\n{content}")
    
    context_text = '\n\n'.join(context_sections)
    print(f"✓ Context assembled: {len(context_text)} chars")
    print(f"  Sections: {len(context_sections)}")
    print(f"  Preview: {context_text[:150]}...")
    
    if not context_text.strip():
        print("✗ Context is EMPTY - BUG DETECTED")
        return False
    
    # Step 5: Test LLM (if API key present)
    print("\n[5/6] Testing LLM generation...")
    
    # Check for valid API keys (not placeholder values)
    openai_key = os.getenv('OPENAI_API_KEY', '')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
    
    valid_openai = openai_key and not openai_key.startswith('sk-your_')
    valid_anthropic = anthropic_key and anthropic_key != ''
    
    if not valid_openai and not valid_anthropic:
        print("⚠ No valid API key set - skipping LLM test")
        print("  Set OPENAI_API_KEY or ANTHROPIC_API_KEY to test full flow")
        print("\n✅ CORE PIPELINE TEST PASSED (Retrieval + Context OK)")
        return True
    
    try:
        model_service = ConcreteModelService()
        
        user_prompt = (
            "Answer the user's question using the context below. "
            "Be helpful and synthesize information from the context when possible. "
            "Cite your sources by referencing which part of the context you used. "
            f"\n\nContext:\n{context_text}\n\nQuestion:\n{test_query}"
        )
        
        generate_result = await model_service.generate({
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': user_prompt}
            ],
            'modelProfile': 'balanced',
            'maxTokens': 1000,
        })
        
        answer = (generate_result.get('content') or '').strip()
        
        if not answer:
            print("✗ LLM returned empty response")
            return False
        
        print(f"✓ LLM generated answer: {len(answer)} chars")
        print(f"\nAnswer preview:")
        print("-" * 70)
        print(answer[:500] + ("..." if len(answer) > 500 else ""))
        print("-" * 70)
        
        # Check for abstention phrases
        if "don't have enough information" in answer.lower() or "i don't see" in answer.lower():
            print("\n⚠ WARNING: LLM still abstaining despite having context")
            print("  This suggests the context may not be relevant to the query")
        else:
            print("\n✓ LLM provided substantive answer")
        
    except Exception as e:
        print(f"✗ LLM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Summary
    print("\n[6/6] Test Summary")
    print("="*70)
    print("✓ Chunks loaded successfully")
    print("✓ Retrieval working")
    print("✓ Context extraction working")
    print("✓ LLM generation working")
    print("\n✅ END-TO-END TEST PASSED")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_end_to_end())
    sys.exit(0 if success else 1)

