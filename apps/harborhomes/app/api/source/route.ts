import { NextRequest, NextResponse } from "next/server";
import { JSDOM } from "jsdom";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const eli = searchParams.get("eli") ?? "";
  // TODO: fetch AKN XML from object store by ELI
  const aknXml = `<?xml version="1.0"?><akomaNtoso><act><mainBody><section><paragraph>Cold storage logging is required.</paragraph></section><section><paragraph>Records must be retained for 24 months.</paragraph></section></mainBody></act></akomaNtoso>`;
  const dom = new JSDOM(aknXml, { contentType: "text/xml" });
  const paras = Array.from(dom.window.document.getElementsByTagName("paragraph")).map((p) => p.textContent || "");

  return NextResponse.json({ eli, sections: paras });
}
