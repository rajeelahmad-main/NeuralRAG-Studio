import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function POST(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const docId = params.id;
  const state = getServerState();
  const doc = state.documents.find((d) => d.id === docId);

  if (!doc) {
    return NextResponse.json({ detail: "Document not found" }, { status: 404 });
  }

  const chunks = state.chunks.filter((c) => c.document_id === docId);
  return NextResponse.json({
    document: doc,
    reindexed_chunks: chunks.length,
  });
}
