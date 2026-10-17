import { NextRequest } from "next/server";
import {
  expandQueryForCrag,
  getGeminiApiKey,
  getServerState,
  isSummaryIntent,
  searchChunks,
} from "@/lib/serverStore";
import { ChatMessage, Citation, CragTrace } from "@/types/api";

export const dynamic = "force-dynamic";

export async function POST(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const convId = params.id;
  const state = getServerState();
  const apiKey = getGeminiApiKey();

  const conv = state.conversations.find((c) => c.id === convId);
  const {
    content,
    model_id = "gemini-3.1-flash-lite",
    retrieval_mode = "corrective_rag",
    collection_id = "default",
    top_k = 5,
  } = await req.json();

  const userMsgId = `msg-${Date.now()}`;
  const userMsg: ChatMessage = {
    id: userMsgId,
    conversation_id: convId,
    role: "user",
    content,
    model_id,
    retrieval_mode,
    citations: [],
    crag_trace: {} as CragTrace,
    follow_ups: [],
    latency_ms: 0,
    created_at: new Date().toISOString(),
  };

  const newTitle =
    conv && conv.title === "New Chat"
      ? content.slice(0, 32) + (content.length > 32 ? "..." : "")
      : conv?.title || "New Chat";

  if (conv) {
    conv.title = newTitle;
    if (!conv.messages) conv.messages = [];
    conv.messages.push(userMsg);
  }

  // File Scoping: Prioritize documents uploaded to THIS conversation (like ChatGPT)
  let targetChunks = state.chunks.filter((c) => c.conversation_id === convId);
  if (targetChunks.length === 0) {
    // Fallback to collection-scoped documents if no per-chat files exist
    const collectionDocIds = new Set(
      state.documents.filter((d) => d.collection_id === collection_id).map((d) => d.id)
    );
    targetChunks = state.chunks.filter((c) => collectionDocIds.has(c.document_id));
  }

  const isSummary = isSummaryIntent(content);
  const effectiveTopK = isSummary ? Math.max(top_k, 6) : top_k;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      function sendEvent(data: Record<string, any>) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      }

      sendEvent({
        type: "user_message",
        message: userMsg,
        conversation_title: newTitle,
      });

      sendEvent({
        type: "status",
        stage: "retrieval",
        detail: isSummary
          ? "Performing multi-page structural document sampling for complete summary..."
          : "Analyzing target files and searching indexed evidence...",
      });

      // 1. Initial Retrieval with File Targeting & Summary Handling
      let ranked = searchChunks(content, targetChunks, effectiveTopK);
      const topScore = ranked.length > 0 ? ranked[0].score : 0;
      let retriesUsed = 0;
      const rewrittenQueries: string[] = [];

      // 2. Corrective RAG (CRAG) loop (skip if already broad summary)
      if (
        !isSummary &&
        retrieval_mode === "corrective_rag" &&
        (topScore < 0.25 || ranked.length < 2)
      ) {
        sendEvent({
          type: "status",
          stage: "crag_eval",
          detail: "Evidence confidence below threshold. Expanding queries for corrective retrieval...",
        });

        const rewrites = expandQueryForCrag(content);
        for (const rw of rewrites) {
          rewrittenQueries.push(rw);
          retriesUsed++;
          const extra = searchChunks(rw, targetChunks, effectiveTopK);
          const seen = new Set(ranked.map((r) => r.chunk.id));
          for (const item of extra) {
            if (!seen.has(item.chunk.id)) {
              ranked.push(item);
              seen.add(item.chunk.id);
            }
          }
        }
        ranked.sort((a, b) => b.score - a.score);
        ranked = ranked.slice(0, effectiveTopK);
      }

      const citations: Citation[] = ranked.map((item, idx) => ({
        citation_index: idx + 1,
        chunk_id: item.chunk.id,
        document_id: item.chunk.document_id,
        filename: item.chunk.filename,
        page_number: item.chunk.page_number,
        heading: item.chunk.heading,
        sheet_name: "",
        row_range: "",
        location_label: item.chunk.location_label,
        score: item.score,
        relevance_grade: item.score >= 0.2 ? "relevant" : "ambiguous",
        excerpt: item.chunk.text,
      }));

      const cragTrace: CragTrace = {
        mode: retrieval_mode,
        status: topScore >= 0.25 || isSummary ? "sufficient" : "ambiguous",
        initial_candidates: targetChunks.length,
        relevant_count: citations.filter((c) => c.relevance_grade === "relevant").length,
        ambiguous_count: citations.filter((c) => c.relevance_grade === "ambiguous").length,
        rewritten_queries: rewrittenQueries,
        retries_used: retriesUsed,
        final_evidence_count: citations.length,
        confidence: isSummary ? 0.95 : topScore,
      };

      sendEvent({
        type: "crag_trace",
        crag_trace: cragTrace,
        citations,
      });

      sendEvent({
        type: "status",
        stage: "synthesis",
        detail: `Synthesizing grounded response using ${model_id}...`,
      });

      // 3. Gemini Generation with Enterprise Prompting
      let assistantText = "";
      const t0 = Date.now();

      if (!apiKey) {
        assistantText =
          "⚠️ **Server GEMINI_API_KEY is not configured.**\n\nPlease add `GEMINI_API_KEY` to your environment variables to enable grounded AI document chat.";
        sendEvent({ type: "token", delta: assistantText });
      } else if (citations.length === 0) {
        assistantText =
          "💡 **No documents found in this chat.**\n\nPlease attach or upload your PDF, DOCX, or Excel documents using the paperclip or the **Document Workspace** panel to ask questions.";
        sendEvent({ type: "token", delta: assistantText });
      } else {
        const evidenceBlocks = citations
          .map(
            (c) =>
              `<source id="Source ${c.citation_index}" file="${c.filename}" location="${c.location_label}">\n${c.excerpt}\n</source>`
          )
          .join("\n\n");

        let systemInstruction = "";

        if (isSummary) {
          systemInstruction =
            "You are NeuralRAG, a premier enterprise document intelligence system.\n" +
            "Provide a comprehensive, beautifully structured summary of the document based strictly on the provided sources.\n" +
            "STRUCTURE YOUR SUMMARY AS FOLLOWS:\n" +
            "1. **### Document Overview & Purpose**: State the core objective, subject matter, and target audience.\n" +
            "2. **### Step-by-Step Breakdown & Core Sections**: Detail key instructions, procedures, prerequisites, account registration steps, or methodologies.\n" +
            "3. **### Key Parameters, Specifications & Links**: Mention any important URLs, credentials, security requirements, or limits.\n" +
            "4. **### Important Notes & Best Practices**.\n" +
            "Cite every claim with its source tag [Source N]. Do NOT output raw font names, file metadata, or unformatted text.";
        } else if (retrieval_mode === "compare_documents") {
          systemInstruction =
            "You are NeuralRAG in COMPARE DOCUMENTS mode.\n" +
            "Compare the claims, metrics, and procedures across the provided sources side-by-side.\n" +
            "Provide:\n" +
            "1. **### Executive Comparison Summary**\n" +
            "2. **### Comparison Matrix (Markdown Table)**\n" +
            "3. **### Agreements, Discrepancies & Distinctions**\n" +
            "Every statement must cite its passage with [Source N].";
        } else {
          systemInstruction =
            "You are NeuralRAG, an enterprise AI document intelligence assistant.\n" +
            "Answer the user's inquiry thoroughly and accurately using the provided document evidence.\n" +
            "RULES:\n" +
            "1. Base your answer strictly on the facts in the provided sources.\n" +
            "2. Cite every factual assertion, number, step, or quote with an inline citation [Source N] (e.g. [Source 1], [Source 2]).\n" +
            "3. If the user refers to a specific file, address that file directly.\n" +
            "4. Format your output clearly with Markdown headings, bullet points, and tables where appropriate.\n" +
            "5. Never output font definitions, internal binary tags, or raw encoding declarations.";
        }

        const userPrompt =
          `<retrieved_evidence>\n{evidenceBlocks}\n</retrieved_evidence>\n\n`
            .replace("{evidenceBlocks}", evidenceBlocks) +
          `User Question: ${content}\n\n` +
          `Provide your grounded Markdown response with [Source N] citations:`;

        try {
          const geminiRes = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/${model_id}:streamGenerateContent?alt=sse&key=${apiKey}`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                system_instruction: { parts: [{ text: systemInstruction }] },
                contents: [{ parts: [{ text: userPrompt }] }],
                generationConfig: { temperature: 0.0, maxOutputTokens: 2500 },
              }),
            }
          );

          if (!geminiRes.ok) {
            const errText = await geminiRes.text();
            assistantText = `Gemini API Error (HTTP ${geminiRes.status}): ${errText.slice(0, 220)}`;
            sendEvent({ type: "token", delta: assistantText });
          } else if (geminiRes.body) {
            const reader = geminiRes.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let sseBuf = "";

            while (true) {
              const { value, done } = await reader.read();
              if (done) break;
              sseBuf += decoder.decode(value, { stream: true });
              const lines = sseBuf.split("\n");
              sseBuf = lines.pop() || "";

              for (const line of lines) {
                if (line.startsWith("data: ")) {
                  try {
                    const parsed = JSON.parse(line.slice(6));
                    const delta =
                      parsed.candidates?.[0]?.content?.parts?.[0]?.text || "";
                    if (delta) {
                      assistantText += delta;
                      sendEvent({ type: "token", delta });
                    }
                  } catch {
                    // Ignore JSON parse errors on partial frames
                  }
                }
              }
            }
          }
        } catch (err: any) {
          assistantText = `Synthesis Error: ${err?.message || "Unexpected failure"}`;
          sendEvent({ type: "token", delta: assistantText });
        }
      }

      const latencyMs = Date.now() - t0;
      const asstMsgId = `asst-${Date.now()}`;
      const asstMsg: ChatMessage = {
        id: asstMsgId,
        conversation_id: convId,
        role: "assistant",
        content: assistantText,
        model_id,
        retrieval_mode,
        citations,
        crag_trace: cragTrace,
        follow_ups: [
          "Can you break down the step-by-step procedures?",
          "Are there any prerequisites or account limits mentioned?",
          "What are the main technical requirements?",
        ],
        latency_ms: latencyMs,
        created_at: new Date().toISOString(),
      };

      if (conv) {
        conv.messages?.push(asstMsg);
        conv.updated_at = new Date().toISOString();
      }

      sendEvent({
        type: "done",
        assistant_message: asstMsg,
      });

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
