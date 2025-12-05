# Expert RAG Guidance - 5 Sources

## 1️⃣ Anthropic – Contextual Retrieval & Hybrid Search

**Core Principle:** Fix retrieval first, not the model.

**Moves:**
1. **Contextualized chunks:** Prepend LLM-generated explanation of each chunk's role in the whole document, then embed that
2. **Hybrid retrieval:** Build both semantic embeddings AND BM25 sparse index, combine via rank fusion (dense + keyword)
3. **Rerank on top:** After hybrid retrieval, run a reranker to pick best chunks

**Results:** Big drops in retrieval failure rates when combining contextual chunking + hybrid search + reranking.

**Mindset:** Don't just index raw text; index context-augmented chunks, and always combine dense + sparse, then rerank.

---

## 2️⃣ Fudan "Best Practices in RAG" (EMNLP 2024)

**Core Principle:** RAG is a modular pipeline. Tune each block, not just embeddings.

**Pipeline:**
1. **Query classification** – decide if retrieval is even needed
2. **Retrieval** – hybrid + HyDE (hypothetical document embedding)
3. **Reranking** – cross-encoder models like monoT5
4. **Repacking** – reorganize retrieved docs into coherent sequence
5. **Summarization/compression** – compress large retrieved context before LLM

**Recipes:**
- **Max performance:** Query classification → Hybrid + HyDE → strong reranker (monoT5) → "Reverse" repacking → RECOMP summarization
- **Balanced efficiency:** Query classification → simpler Hybrid → lighter reranker → same repacking/summarization

**Mindset:** Treat RAG as: classifier → retriever → reranker → repacker → summarizer → generator.

---

## 3️⃣ Pinecone / James Briggs – Hybrid, Two-Stage & Metrics

**Core Principle:** Use hybrid + rerankers + metrics. Don't ship naive "top-k cosine".

**Key Practices:**
1. **Hybrid search:** Combine sparse (BM25/SPLADE) and dense embeddings; use alpha parameter to trade off lexical vs semantic
2. **Two-stage retrieval:**
   - Stage 1: High-recall dense/hybrid with big top_k
   - Stage 2: Reranker (cross-encoder) to refine to final chunks
3. **Metadata-aware retrieval:** Use metadata filters (project, time, doc type) plus hybrid search
4. **Metrics-driven development:** Evaluate with explicit metrics, NOT VIBES ONLY

**Mindset:** Don't ship naive "top-k cosine" as if that's real RAG.

---

## 4️⃣ LlamaIndex / Jerry Liu – LLM-based Reranking

**Core Principle:** Embedding search is a coarse filter; then LLM decides which chunks truly matter.

**Core Ideas:**
1. **Two-stage pipeline:**
   - First: Fast vector retriever with generous top_k
   - Then: LLM-based reranker that reads candidate chunks and chooses/scores the most relevant
2. **Prompted reranker:** LLM prompted to output which documents are relevant and why
3. **Smaller chunks:** 128–512 tokens with summaries when needed

**Mindset:** Embedding search is coarse; LLM reranking is precise.

---

## 5️⃣ Chroma / Weaviate / NVIDIA – Chunking as First-Class Design

**Core Principle:** Before blaming vector DB or model, fix chunking.

**Shared Findings:**
- **Chunking is often THE MAIN BOTTLENECK**
- Many "bad RAG" systems are really "bad chunks" systems
- Different chunking strategies differ by ~9%+ recall or more

**Practical Guidance:**
- Start around **~512 tokens with 10–20% overlap** as baseline
- Chunks must be **semantically coherent and readable alone**
- Too large → embeddings become "averaged mush"
- Too small → model lacks context, answers become brittle

**Advanced Strategies:**
- Semantic/LLM chunking
- Hierarchical chunking
- Late/post-chunking

**Mindset:** Fix chunking and PROVE retrieval is actually working before blaming anything else.

---

## Synthesized Action Plan

### Diagnostic Steps (In Order)
1. **Verify chunks exist and have content** - before anything else
2. **Verify BM25 retrieval returns chunks** - does search even work?
3. **Verify chunk content reaches LLM prompt** - is context being assembled?
4. **Measure retrieval quality** - metrics, not vibes

### Fix Priority
1. **Bug fix:** Chunk ID mismatch causing empty context (immediate)
2. **Enable hybrid search:** BM25 + vector (short-term)
3. **Add reranking:** Cross-encoder or LLM-based (medium-term)
4. **Improve chunking:** Semantic boundaries, contextual prepending (longer-term)

