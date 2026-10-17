import { NextResponse } from "next/server";
import { getGeminiApiKey, getServerState } from "@/lib/serverStore";

export async function GET() {
  const state = getServerState();
  const apiKey = getGeminiApiKey();

  return NextResponse.json({
    status: "healthy",
    timestamp: new Date().toISOString(),
    gemini_api_configured: Boolean(apiKey),
    active_model: state.settings.default_model,
    collections_count: state.collections.length,
    documents_count: state.documents.length,
    conversations_count: state.conversations.length,
  });
}
