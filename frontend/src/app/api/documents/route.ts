import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const colId = searchParams.get("collection_id");
  const convId = searchParams.get("conversation_id");
  const state = getServerState();

  let docs = state.documents;
  if (convId) {
    docs = docs.filter((d) => d.conversation_id === convId);
  } else if (colId) {
    docs = docs.filter((d) => d.collection_id === colId);
  }

  return NextResponse.json({ documents: docs });
}
