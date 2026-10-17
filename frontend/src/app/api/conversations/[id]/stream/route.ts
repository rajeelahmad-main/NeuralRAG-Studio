import { NextRequest } from "next/server";
import {
  expandQueryForCrag,
  getGeminiApiKey,
  getServerState,
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

  // Filter chunks by collection
  const collectionDocIds = new Set(
    state.documents.filter((d) => d.collection_id === collection_id).map((d) => d.id)
  );
  const targetChunks = state.chunks.filter((c) => collectionDocIds.has(c.document_id));

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
        detail: "Searching indexed documents with hybrid keyword + vector ranking...",
      });

      // 1. Initial Retrieval
      let ranked = searchChunks(content, targetChunks, top_k);
      const topScore = ranked.length > 0 ? ranked[0].score : 0;
      let retriesUsed = 0;
      const rewrittenQueries: string[] = [];

      // 2. Corrective RAG (CRAG) loop
      if (retrieval_mode === "corrective_rag" && (topScore < 0.25 || ranked.length < 2)) {
        sendEvent({
          type: "status",
          stage: "crag_eval",
          detail: "Evidence confidence below threshold. Expanding queries for corrective retrieval...",
        });

        const rewrites = expandQueryForCrag(content);
        for (const rw of rewrites) {
          rewrittenQueries.push(rw);
          retriesUsed++;
          const extra = searchChunks(rw, targetChunks, top_k);
          const seen = new Set(ranked.map((r) => r.chunk.id));
          for (const item of extra) {
            if (!seen.has(item.chunk.id)) {
              ranked.push(item);
              seen.add(item.chunk.id);
            }
          }
        }
        ranked.sort((a, b) => b.score - a.score);
        ranked = ranked.slice(0, top_k);
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
        relevance_grade: item.score >= 0.25 ? "relevant" : "ambiguous",
        excerpt: item.chunk.text,
      }));

      const cragTrace: CragTrace = {
        mode: retrieval_mode,
        status: topScore >= 0.25 ? "sufficient" : "ambiguous",
        initial_candidates: targetChunks.length,
        relevant_count: citations.filter((c) => c.relevance_grade === "relevant").length,
        ambiguous_count: citations.filter((c) => c.relevance_grade === "ambiguous").length,
        rewritten_queries: rewrittenQueries,
        retries_used: retriesUsed,
        final_evidence_count: citations.length,
        confidence: topScore,
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

      // 3. Gemini Generation
      let assistantText = "";
      const t0 = Date.now();

      if (!apiKey) {
        assistantText =
          "⚠️ **Server GEMINI_API_KEY is not configured.**\n\nPlease add `GEMINI_API_KEY` to your Vercel project environment variables to enable grounded AI document chat.";
        sendEvent({ type: "token", delta: assistantText });
      } else if (citations.length === 0) {
        assistantText =
          "💡 **No relevant documents found in General Workspace.**\n\nPlease upload PDF, DOCX, Excel, or Markdown documents in the right-side **Document Workspace** panel to ground responses.";
        sendEvent({ type: "token", delta: assistantText });
      } else {
        const evidenceBlocks = citations
          .map(
            (c) =>
              `<source id="Source ${c.citation_index}" location="${c.location_label}">\n${c.excerpt}\n</source>`
          )
          .join("\n\n");

        let systemInstruction =
          "You are NeuralRAG Studio, an enterprise AI document intelligence assistant.\n" +
          "Answer strictly using the provided context passages. Every claim MUST include an inline citation [Source N].\n" +
          "Never speculate or invent facts not present in the sources.";

        if (retrieval_mode === "compare_documents") {
          systemInstruction =
            "You are NeuralRAG Studio in COMPARE DOCUMENTS mode.\n" +
            "Provide: 1) Executive Comparison Summary, 2) Markdown Comparison Matrix Table, 3) Agreements & Discrepancies.\n" +
            "Every claim must cite [Source N].";
        }

        const userPrompt =
          `<retrieved_evidence>\n${evidenceBlocks}\n</retrieved_evidence>\n\n` +
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
                generationConfig: { temperature: 0.0, maxOutputTokens: 1600 },
              }),
            }
          );

          if (!geminiRes.ok) {
            const errText = await geminiRes.text();
            assistantText = `Gemini API Error (HTTP ${geminiRes.status}): ${errText.slice(0, 200)}`;
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
          "Can you elaborate on the key findings?",
          "Compare these results with other sections",
          "What are the main risks or limitations?",
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
