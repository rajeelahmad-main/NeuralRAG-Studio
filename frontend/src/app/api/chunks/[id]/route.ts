import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const chunkId = params.id;
  const state = getServerState();
  const chunk = state.chunks.find((c) => c.id === chunkId);

  if (!chunk) {
    return NextResponse.json({ detail: "Chunk not found" }, { status: 404 });
  }

  const siblings = state.chunks.filter((c) => c.document_id === chunk.document_id);

  return NextResponse.json({
    chunk: {
      id: chunk.id,
      document_id: chunk.document_id,
      filename: chunk.filename,
      page_number: chunk.page_number,
      heading: chunk.heading,
      location_label: chunk.location_label,
      text: chunk.text,
      score: 1.0,
      char_count: chunk.text.length,
      token_count: chunk.tokens.length,
    },
    sibling_chunks: siblings.map((s) => ({
      id: s.id,
      page_number: s.page_number,
      heading: s.heading,
      preview: s.text.slice(0, 100),
    })),
  });
}
