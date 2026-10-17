import { NextRequest, NextResponse } from "next/server";
import { getGeminiApiKey } from "@/lib/serverStore";

export async function POST(req: NextRequest) {
  try {
    const { model_id } = await req.json();
    const apiKey = getGeminiApiKey();

    if (!apiKey) {
      return NextResponse.json({
        model_id,
        verified: false,
        status: "missing_key",
        latency_ms: 0,
        message: "GEMINI_API_KEY is not configured.",
      });
    }

    const t0 = Date.now();
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model_id}:generateContent?key=${apiKey}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: "ping" }] }],
        generationConfig: { maxOutputTokens: 2 },
      }),
    });

    const latency = Date.now() - t0;
    if (res.ok) {
      return NextResponse.json({
        model_id,
        verified: true,
        status: "verified",
        latency_ms: latency,
        message: "Connectivity verified successfully.",
      });
    } else {
      const errText = await res.text();
      return NextResponse.json({
        model_id,
        verified: false,
        status: "error",
        latency_ms: latency,
        message: `HTTP ${res.status}: ${errText.slice(0, 150)}`,
      });
    }
  } catch (err: any) {
    return NextResponse.json({
      model_id: "unknown",
      verified: false,
      status: "error",
      latency_ms: 0,
      message: err?.message || "Unexpected verification error.",
    });
  }
}
