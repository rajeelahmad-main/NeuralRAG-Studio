import { NextRequest, NextResponse } from "next/server";
import {
  getGeminiApiKey,
  getServerState,
  StoredChunk,
  tokenize,
} from "@/lib/serverStore";
import { DocumentItem } from "@/types/api";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const collectionId = (formData.get("collection_id") as string) || "default";
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

      if (["png", "jpg", "jpeg", "webp"].includes(ext) && apiKey) {
        // Multimodal Vision OCR via Gemini
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
                generationConfig: { maxOutputTokens: 2048 },
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
        // UTF-8 text extraction for txt, md, csv, json, etc.
        // For PDF/binary, extract printable text sequences
        extractedText = buffer.toString("utf-8");
        if (["pdf", "docx", "xlsx"].includes(ext)) {
          // Clean printable ASCII/UTF-8 strings from binary stream
          const match = extractedText.match(/[\x20-\x7E\t\n\r]{4,}/g);
          if (match && match.length > 0) {
            extractedText = match.join(" ");
          }
        }
      }

      if (!extractedText.trim()) {
        extractedText = `[Uploaded document: ${filename} (${(buffer.length / 1024).toFixed(1)} KB)]`;
      }

      // Chunking (600 characters with 100 overlap)
      const chunkSize = 600;
      const overlap = 100;
      const chunks: StoredChunk[] = [];
      let start = 0;
      let pageIdx = 1;

      while (start < extractedText.length) {
        const end = Math.min(start + chunkSize, extractedText.length);
        const chunkText = extractedText.slice(start, end).trim();
        if (chunkText) {
          const cId = `chunk-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
          chunks.push({
            id: cId,
            document_id: docId,
            filename,
            page_number: pageIdx,
            heading: `${filename} • Section ${pageIdx}`,
            location_label: `${filename} • Page ${pageIdx}`,
            text: chunkText,
            tokens: tokenize(chunkText),
          });
          pageIdx++;
        }
        if (end >= extractedText.length) break;
        start = Math.max(end - overlap, start + 1);
      }

      state.chunks.push(...chunks);

      const docItem: DocumentItem = {
        id: docId,
        collection_id: collectionId,
        filename,
        safe_path: `storage/${docId}_${filename}`,
        file_type: ext.toUpperCase(),
        file_size: buffer.length,
        page_count: Math.max(1, Math.ceil(extractedText.length / 1500)),
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
      state.documents
        .filter((d) => d.collection_id === collectionId)
        .map((d) => d.id)
        .includes(c.document_id)
    ).length;

    return NextResponse.json({
      collection_id: collectionId,
      uploaded: uploadedItems,
      total_collection_chunks: totalCollectionChunks,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message || "Failed to process upload" },
      { status: 500 }
    );
  }
}
