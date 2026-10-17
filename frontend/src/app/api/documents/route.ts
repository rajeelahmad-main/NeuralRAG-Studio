import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const colId = searchParams.get("collection_id");
  const state = getServerState();

  const docs = colId
    ? state.documents.filter((d) => d.collection_id === colId)
    : state.documents;

  return NextResponse.json({ documents: docs });
}
