import { NextRequest, NextResponse } from "next/server";
import { getGeminiApiKey, getServerState, SUPPORTED_MODELS } from "@/lib/serverStore";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const verifyLive = searchParams.get("verify_live") === "true";
  const state = getServerState();
  const apiKey = getGeminiApiKey();

  const models = SUPPORTED_MODELS.map((m) => ({
    ...m,
    is_default: m.id === state.settings.default_model,
    available: Boolean(apiKey),
    verification_status: apiKey ? ("verified" as const) : ("configured" as const),
    status_message: apiKey ? "Active & Ready" : "Requires GEMINI_API_KEY",
  }));

  return NextResponse.json({
    provider: "Google Gemini",
    default_model: state.settings.default_model,
    models,
  });
}
