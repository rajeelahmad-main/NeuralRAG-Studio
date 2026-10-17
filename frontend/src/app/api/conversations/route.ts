import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const q = (searchParams.get("q") || "").toLowerCase();
  const state = getServerState();

  const convs = state.conversations.filter(
    (c) => !q || c.title.toLowerCase().includes(q)
  );

  return NextResponse.json({ conversations: convs });
}

export async function POST(req: NextRequest) {
  const { title, collection_id, model_id, retrieval_mode } = await req.json();
  const state = getServerState();

  const newConv = {
    id: `conv-${Date.now()}`,
    title: title || "New Chat",
    collection_id: collection_id || "default",
    model_id: model_id || state.settings.default_model,
    retrieval_mode: retrieval_mode || state.settings.retrieval_mode,
    pinned: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    messages: [],
  };

  state.conversations.unshift(newConv);
  return NextResponse.json(newConv, { status: 201 });
}

export async function DELETE() {
  const state = getServerState();
  const count = state.conversations.length;
  state.conversations = [];
  return NextResponse.json({ cleared: true, deleted_count: count });
}
