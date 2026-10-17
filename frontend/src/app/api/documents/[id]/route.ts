import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const docId = params.id;
  const state = getServerState();

  state.documents = state.documents.filter((d) => d.id !== docId);
  state.chunks = state.chunks.filter((c) => c.document_id !== docId);

  return NextResponse.json({
    deleted: true,
    document_id: docId,
    remaining_chunks: state.chunks.length,
  });
}
