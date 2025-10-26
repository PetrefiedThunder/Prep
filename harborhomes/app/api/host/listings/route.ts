import { NextResponse } from "next/server";
import { hostListings } from "@/lib/mock-data";

export async function GET() {
  return NextResponse.json({ items: hostListings });
}
