import { NextRequest, NextResponse } from "next/server";
import {
  getGeminiApiKey,
  getServerState,
  StoredChunk,
  tokenize,
} from "@/lib/serverStore";
import { DocumentItem } from "@/types/api";

// PDF & Word Parsers
// eslint-disable-next-line @typescript-eslint/no-var-requires
const pdfParse = require("pdf-parse");
// eslint-disable-next-line @typescript-eslint/no-var-requires
const mammoth = require("mammoth");

function cleanExtractedText(raw: string): string {
  // Remove binary PDF font dictionaries, PostScript streams, and null bytes
  return raw
    .replace(/\/Font\s*<<[^>]*>>/gi, "")
    .replace(/\/Encoding\s*\/[A-Za-z0-9_-]+/gi, "")
    .replace(/obj\s*<<[\s\S]*?>>\s*endobj/gi, "")
    .replace(/stream[\s\S]*?endstream/gi, "")
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, "")
    .replace(/[ \t]+/g, " ")
    .replace(/\n\s*\n\s*\n+/g, "\n\n")
    .trim();
}

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const collectionId = (formData.get("collection_id") as string) || "default";
    const conversationId = (formData.get("conversation_id") as string) || "";
    const files = formData.getAll("files") as File[];
    const state = getServerState();
    const apiKey = getGeminiApiKey();

    const uploadedItems: DocumentItem[] = [];

    for (const file of files) {
      const buffer = Buffer.from(await file.arrayBuffer());
      const filename = file.name;
      const ext = filename.split(".").pop()?.toLowerCase() || "txt";
      const docId = `doc-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

      let extractedText = "";
      let pageCount = 1;

      if (ext === "pdf") {
        try {
          const pdfData = await pdfParse(buffer);
          pageCount = Math.max(1, pdfData.numpages || 1);
          extractedText = cleanExtractedText(pdfData.text || "");
        } catch (pdfErr) {
          console.error("pdfParse error:", pdfErr);
        }

        // If digital text extraction is sparse or empty, fallback to Gemini PDF OCR
        if (extractedText.length < 60 && apiKey) {
          try {
            const b64 = buffer.toString("base64");
            const ocrRes = await fetch(
              `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=${apiKey}`,
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  contents: [
                    {
                      parts: [
                        {
                          text: "You are an enterprise document OCR transcriber. Transcribe the full textual contents, headings, instructions, tables (as Markdown), numbers, and technical procedures of this PDF completely and accurately without omitting anything.",
                        },
                        { inlineData: { mimeType: "application/pdf", data: b64 } },
                      ],
                    },
                  ],
                  generationConfig: { maxOutputTokens: 3500 },
                }),
              }
            );
            if (ocrRes.ok) {
              const resData = await ocrRes.json();
              extractedText =
                resData.candidates?.[0]?.content?.parts?.[0]?.text || "";
            }
          } catch (ocrErr) {
            console.error("Gemini PDF OCR error:", ocrErr);
          }
        }
      } else if (ext === "docx") {
        try {
          const docxResult = await mammoth.extractRawText({ buffer });
          extractedText = cleanExtractedText(docxResult.value || "");
        } catch (docxErr) {
          console.error("Mammoth docx error:", docxErr);
          extractedText = buffer.toString("utf-8");
        }
      } else if (["png", "jpg", "jpeg", "webp"].includes(ext) && apiKey) {
        // Multimodal Image Vision OCR via Gemini
        try {
          const b64 = buffer.toString("base64");
          const mime = ext === "png" ? "image/png" : "image/jpeg";
          const ocrRes = await fetch(
            `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key=${apiKey}`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                contents: [
                  {
                    parts: [
                      {
                        text: "Transcribe this document image with full fidelity. Convert tables to Markdown grids. Extract text, diagram labels, and figures.",
                      },
                      { inlineData: { mimeType: mime, data: b64 } },
                    ],
                  },
                ],
                generationConfig: { maxOutputTokens: 2500 },
              }),
            }
          );
          if (ocrRes.ok) {
            const data = await ocrRes.json();
            extractedText =
              data.candidates?.[0]?.content?.parts?.[0]?.text || "";
          }
        } catch {
          extractedText = `[Image Document: ${filename}]`;
        }
      } else {
        // Plain text, Markdown, CSV, JSON
        extractedText = cleanExtractedText(buffer.toString("utf-8"));
      }

      if (!extractedText.trim()) {
        extractedText = `[Uploaded document: ${filename} - Document was parsed but contained minimal readable text]`;
      }

      // Chunking: 700 chars with 120 overlap, tracking approximate page positions
      const chunkSize = 700;
      const overlap = 120;
      const chunks: StoredChunk[] = [];
      let start = 0;
      let chunkIdx = 1;

      while (start < extractedText.length) {
        const end = Math.min(start + chunkSize, extractedText.length);
        const chunkText = extractedText.slice(start, end).trim();
        if (chunkText) {
          const approxPage = Math.min(
            pageCount,
            Math.max(1, Math.ceil((start / extractedText.length) * pageCount))
          );
          const cId = `chunk-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
          chunks.push({
            id: cId,
            document_id: docId,
            conversation_id: conversationId,
            filename,
            page_number: approxPage,
            heading: `${filename} • Page ${approxPage} (Part ${chunkIdx})`,
            location_label: `${filename} • Page ${approxPage}`,
            text: chunkText,
            tokens: tokenize(chunkText),
          });
          chunkIdx++;
        }
        if (end >= extractedText.length) break;
        start = Math.max(end - overlap, start + 1);
      }

      state.chunks.push(...chunks);

      const docItem: DocumentItem = {
        id: docId,
        collection_id: collectionId,
        conversation_id: conversationId,
        filename,
        safe_path: `storage/${docId}_${filename}`,
        file_type: ext.toUpperCase(),
        file_size: buffer.length,
        page_count: pageCount,
        chunk_count: chunks.length,
        status: "indexed",
        error_message: "",
        metadata: {
          original_name: filename,
          extracted_characters: extractedText.length,
        },
        created_at: new Date().toISOString(),
      };

      state.documents.push(docItem);
      uploadedItems.push(docItem);
    }

    const totalCollectionChunks = state.chunks.filter((c) =>
      conversationId
        ? c.conversation_id === conversationId
        : true
    ).length;

    return NextResponse.json({
      collection_id: collectionId,
      uploaded: uploadedItems,
      total_collection_chunks: totalCollectionChunks,
    });
  } catch (err: any) {
    console.error("Upload error:", err);
    return NextResponse.json(
      { detail: err?.message || "Failed to process upload" },
      { status: 500 }
    );
  }
}
