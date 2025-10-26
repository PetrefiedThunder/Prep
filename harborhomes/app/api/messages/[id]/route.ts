import { NextResponse } from "next/server";
import { messageThreads } from "@/lib/mock-data";

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const thread = messageThreads.find((item) => item.id === params.id);
  if (!thread) {
    return NextResponse.json({ message: "Thread not found" }, { status: 404 });
  }
  return NextResponse.json(thread);
}
