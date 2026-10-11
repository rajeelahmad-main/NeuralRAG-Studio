# 🎓 Artificial Intelligence Lab: Retrieval-Augmented Generation (RAG)
**Course:** Applied Artificial Intelligence / Natural Language Processing  
**Lab Title:** Document Grounding & Semantic Search using RAG Architectures  
**Student Name:** ________________________  
**Student ID:** __________________________  
**Date:** _________________________________  

---

## 🎯 Lab Objectives
1. Understand the core difference between **Parametric Memory** (LLM internal weights) and **Non-Parametric Memory** (external vector knowledge base).
2. Trace the 5-step RAG pipeline: Document Ingestion → Text Chunking → Vector Embedding → Top-K Semantic Retrieval → Augmented Generation.
3. Compare **Dense Semantic Retrieval** (Sentence Transformers / Cosine Similarity) vs. **Sparse Lexical Retrieval** (TF-IDF).
4. Measure the impact of hyperparameters: `Chunk Size`, `Chunk Overlap`, and `Top-K Retrieval Count`.
5. Observe and prevent LLM hallucinations using strict grounding prompts.

---

## 🔬 Hands-On Experimental Tasks

### Task 1: Document Indexing & Chunk Exploration
1. Launch the Streamlit RAG Dashboard and upload a course PDF or research paper.
2. Note the initial metrics displayed in the top KPI bar:
   - **Total Pages:** _________
   - **Total Word Count:** _________
   - **Number of Chunks Generated:** _________
3. Go to the **Chunk & Vector Space Inspector** tab.
4. Select Chunk #1 and Chunk #2.
   - What is the character length of Chunk #1? _________
   - Notice the overlapping text at the boundary. Why is chunk overlap necessary in RAG?  
     *Answer:* ____________________________________________________________________

---

### Task 2: Grounded Fact Retrieval (True Positive Test)
1. Formulate a specific question whose answer is explicitly stated in your uploaded PDF.
   - **Question:** ______________________________________________________________
2. Run the query and inspect the **Retrieved Source Passages**:
   - Top-1 Similarity Score: _________
   - Did the top passage contain the exact information needed? `[ ] Yes  [ ] No`
3. Compare the generated LLM answer with the retrieved passage:
   - Did the model stay faithful to the context without fabricating details?  
     *Answer:* ____________________________________________________________________

---

### Task 3: Unanswerable Query & Hallucination Stress-Test (Negative Test)
1. Ask a question about an imaginary topic or something **NOT** mentioned anywhere in the PDF (e.g., "What does this paper say about quantum teleportation in 2050?").
   - **Question:** ______________________________________________________________
2. What was the highest similarity score among retrieved chunks? _________
3. What did the LLM answer?
   - Did the system prompt successfully stop it from hallucinating?  
     *Answer:* ____________________________________________________________________

---

### Task 4: Retrieval Strategy Comparison (Dense vs. Sparse)
In the sidebar, switch the **Embedding Engine**:
- Test Query: *"Summarize the core methodology and computational results"*

| Metric | Dense Neural Embedding (`all-MiniLM-L6-v2`) | Sparse Lexical Retrieval (TF-IDF) |
|---|---|---|
| **Top-1 Match Score** | | |
| **Semantic Relevance** *(1 to 5)* | | |
| **Handling of Synonyms** | | |
| **Processing Speed (ms)** | | |

*Discussion Question:* Why does Dense Retrieval typically outperform TF-IDF when user queries use synonyms rather than exact keywords?  
*Answer:* ____________________________________________________________________

---

### Task 5: Hyperparameter Tuning
Vary the `Top-K` slider from **1** to **6**:
- When `Top-K = 1`: Is the answer complete or missing details?  
  *Answer:* _________________________________________________________________
- When `Top-K = 6`: Does the context become noisy or dilute the LLM's attention?  
  *Answer:* _________________________________________________________________

---

## 💡 Conceptual Analysis Questions

1. **Why does RAG not require model fine-tuning or GPU training?**
   __________________________________________________________________________
   __________________________________________________________________________

2. **What is the mathematical definition of Cosine Similarity between vector $A$ and vector $B$?**
   $$\text{Cosine Similarity} = \frac{A \cdot B}{\|A\| \|B\|}$$
   Explain why normalized vectors allow dot product calculation instead of full cosine formula:
   __________________________________________________________________________

3. **In production AI systems, what vector databases are used instead of in-memory NumPy arrays? (Name at least two)**
   __________________________________________________________________________

---

### 📝 Lab Submission Checklist
- [ ] Completed all experimental tables above.
- [ ] Attached screenshot of your Streamlit RAG Dashboard with a query.
- [ ] Answered conceptual analysis questions.
