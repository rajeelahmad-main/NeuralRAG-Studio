import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET() {
  const state = getServerState();
  const withCounts = state.collections.map((c) => {
    const docs = state.documents.filter((d) => d.collection_id === c.id);
    const docIds = new Set(docs.map((d) => d.id));
    const chunkCount = state.chunks.filter((ch) => docIds.has(ch.document_id)).length;
    return {
      ...c,
      document_count: docs.length,
      chunk_count: chunkCount,
    };
  });
  return NextResponse.json({ collections: withCounts });
}

export async function POST(req: NextRequest) {
  const { name, description } = await req.json();
  const state = getServerState();
  const newCol = {
    id: `col-${Date.now()}`,
    name: name || "New Collection",
    description: description || "",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  state.collections.push(newCol);
  return NextResponse.json(newCol, { status: 201 });
}
