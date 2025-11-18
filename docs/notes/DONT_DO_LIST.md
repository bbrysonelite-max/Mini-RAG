# ⚠️ RAG System - Things NOT To Do

## 🚫 DON'T INGEST THESE:

### 1. **Codebases / Source Code**
   - ❌ Don't ingest `.py`, `.js`, `.java`, `.cpp`, etc. files
   - ❌ Don't paste code directly into the system
   - ✅ **Why:** Code has structure, dependencies, and context that RAG doesn't understand well
   - ✅ **Better:** Use code search tools (GitHub, grep, IDEs) for code
   - ✅ **Use RAG for:** Documentation ABOUT code, tutorials, explanations

### 2. **Sensitive Information**
   - ❌ Don't ingest passwords, API keys, secrets
   - ❌ Don't ingest personal data (SSNs, credit cards, etc.)
   - ❌ Don't ingest confidential business data
   - ✅ **Why:** Security risk - data is stored in chunks.jsonl
   - ✅ **Better:** Keep sensitive data separate, use secure systems

### 3. **Binary Files**
   - ❌ Don't try to ingest images, videos, executables
   - ❌ Don't ingest compressed files (.zip, .tar, etc.)
   - ✅ **Why:** RAG works with text only
   - ✅ **Better:** Extract text from these first, then ingest

### 4. **Very Large Single Documents**
   - ❌ Don't ingest single documents > 50MB
   - ❌ Don't ingest entire book libraries at once
   - ✅ **Why:** Performance issues, memory problems
   - ✅ **Better:** Break into smaller chunks, ingest in batches

### 5. **Duplicate Content**
   - ❌ Don't ingest the same document multiple times
   - ❌ Don't ingest both PDF and DOCX of the same content
   - ✅ **Why:** Creates duplicate chunks, wastes space
   - ✅ **Better:** Use "Dedupe" button after ingestion

### 6. **Poor Quality Content**
   - ❌ Don't ingest garbled text, OCR errors
   - ❌ Don't ingest incomplete transcripts
   - ❌ Don't ingest content with lots of special characters/encoding issues
   - ✅ **Why:** Garbage in = garbage out
   - ✅ **Better:** Clean content first, fix encoding issues

### 7. **YouTube URLs vs Transcripts**
   - ✅ **BEST:** Paste YouTube URLs - system extracts transcripts automatically
   - ✅ **ALTERNATIVE:** Download transcripts (.vtt/.srt) and upload files directly
   - ❌ Don't paste raw transcript text in the URL field
   - ❌ Don't paste 100+ YouTube URLs at once
   - ✅ **Why:** URLs are easier - system handles transcript extraction
   - ✅ **Better:** Do 10-20 URLs at a time, or upload transcript files directly

### 8. **Non-Text Content**
   - ❌ Don't ingest spreadsheets (.xlsx, .csv) directly
   - ❌ Don't ingest databases
   - ❌ Don't ingest presentations (.pptx) without text extraction
   - ✅ **Why:** Structure matters - RAG needs plain text
   - ✅ **Better:** Convert to text/CSV first, then ingest

---

## ✅ DO INGEST THESE:

### **Perfect for RAG:**
- ✅ **Documentation** - User guides, manuals, wikis
- ✅ **Video Transcripts** - YouTube, webinars, tutorials
- ✅ **Articles & Blog Posts** - Knowledge bases, research papers
- ✅ **Meeting Notes** - Transcripts, summaries
- ✅ **Training Materials** - Course content, tutorials
- ✅ **FAQ Documents** - Help docs, Q&A
- ✅ **Project Notes** - Your own notes, ideas, plans
- ✅ **Text-based PDFs** - Reports, whitepapers, ebooks
- ✅ **Markdown Files** - Documentation, READMEs

### **Good for RAG:**
- ✅ **Email Threads** (if exported as text)
- ✅ **Chat Logs** (Slack, Discord exports)
- ✅ **Interview Transcripts**
- ✅ **Podcast Transcripts**
- ✅ **Subtitles/Captions** (.vtt, .srt files)

---

## 🎯 BEST PRACTICES:

### **Before Ingesting:**
1. ✅ Review content for sensitive information
2. ✅ Check file sizes (keep under 10MB per file)
3. ✅ Ensure text is readable and well-formatted
4. ✅ Remove duplicates
5. ✅ Organize by topic/project

### **After Ingesting:**
1. ✅ Use "Dedupe" button to remove duplicates
2. ✅ Use "Rebuild Index" if search seems off
3. ✅ Check "Browser" tab to see what was ingested
4. ✅ Test with a few questions to verify quality

### **For Best Results:**
1. ✅ Ingest related content together (same project/topic)
2. ✅ Use clear, descriptive filenames
3. ✅ Add system prompt with project context
4. ✅ Ingest in logical batches
5. ✅ Clean up old/unused content periodically

---

## 🔒 SECURITY REMINDERS:

- ⚠️ **chunks.jsonl** contains all your ingested text - keep it secure
- ⚠️ **users.json** contains user data - don't share publicly
- ⚠️ **.env** file has API keys - NEVER commit to git
- ⚠️ **uploads/** folder may contain original files - secure it

---

## 💡 PRO TIPS:

1. **Start Small:** Ingest 5-10 documents first, test, then add more
2. **Quality > Quantity:** Better to have 100 good chunks than 1000 bad ones
3. **Use System Prompt:** Tell the system about your project for better answers
4. **Organize by Project:** Consider separate RAG instances for different projects
5. **Regular Cleanup:** Remove outdated content to keep search fast

---

## 🚨 IF YOU MAKE A MISTAKE:

- **Ingested sensitive data?** → Delete the source, rebuild index
- **Too much content?** → Use Browser tab to delete specific sources
- **Bad quality chunks?** → Delete and re-ingest cleaned version
- **System slow?** → Check chunk count, dedupe, rebuild index

---

**Remember:** RAG is for **knowledge retrieval**, not code search. Use the right tool for the right job! 🎯

