import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const convId = params.id;
  const state = getServerState();
  const conv = state.conversations.find((c) => c.id === convId);

  if (!conv) {
    return NextResponse.json({ detail: "Conversation not found" }, { status: 404 });
  }

  return NextResponse.json(conv);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  const convId = params.id;
  const updates = await req.json();
  const state = getServerState();
  const conv = state.conversations.find((c) => c.id === convId);

  if (!conv) {
    return NextResponse.json({ detail: "Conversation not found" }, { status: 404 });
  }

  if (updates.title !== undefined) conv.title = updates.title;
  if (updates.collection_id !== undefined) conv.collection_id = updates.collection_id;
  if (updates.model_id !== undefined) conv.model_id = updates.model_id;
  if (updates.retrieval_mode !== undefined) conv.retrieval_mode = updates.retrieval_mode;
  if (updates.pinned !== undefined) conv.pinned = updates.pinned;
  conv.updated_at = new Date().toISOString();

  return NextResponse.json(conv);
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { id: string } }
) {
  const convId = params.id;
  const state = getServerState();
  state.conversations = state.conversations.filter((c) => c.id !== convId);
  return NextResponse.json({ deleted: true, conversation_id: convId });
}
