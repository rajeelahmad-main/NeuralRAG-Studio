import { NextRequest, NextResponse } from "next/server";
import { getServerState } from "@/lib/serverStore";

export async function GET() {
  const state = getServerState();
  return NextResponse.json(state.settings);
}

export async function PUT(req: NextRequest) {
  const updates = await req.json();
  const state = getServerState();
  state.settings = { ...state.settings, ...updates };
  return NextResponse.json(state.settings);
}
