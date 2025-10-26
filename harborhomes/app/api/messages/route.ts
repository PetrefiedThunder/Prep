import { NextResponse } from "next/server";
import { messageThreads } from "@/lib/mock-data";

export async function GET() {
  return NextResponse.json({ items: messageThreads });
}
