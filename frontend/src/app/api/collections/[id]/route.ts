import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const colId = params.id;
  const state = getServerState();
  if (colId === "default") {
    return NextResponse.json({ error: "Cannot delete default collection" }, { status: 400 });
  }

  state.collections = state.collections.filter((c) => c.id !== colId);
  const deletedDocIds = new Set(
    state.documents.filter((d) => d.collection_id === colId).map((d) => d.id)
  );
  state.documents = state.documents.filter((d) => d.collection_id !== colId);
  state.chunks = state.chunks.filter((c) => !deletedDocIds.has(c.document_id));

  return NextResponse.json({ deleted: true, collection_id: colId });
}
