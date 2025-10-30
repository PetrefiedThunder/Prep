import fs from "fs";
import path from "path";
import PDFDocument from "pdfkit";

type ManifestSection = "permits" | "temp_logs" | "allergen_labels" | "delivery_proofs" | "insurance_cert";

type ManifestTemplate = {
  sections: ManifestSection[];
  locale: string;
  layout: string;
};

export function renderManifest(jurisdiction: string, data: Record<string, unknown>) {
  const templatePath = path.join(__dirname, "..", "templates", `${jurisdiction}.v3.json`);
  const template = JSON.parse(fs.readFileSync(templatePath, "utf-8")) as ManifestTemplate;
  const doc = new PDFDocument();

  template.sections.forEach((section) => {
    doc.addPage();
    doc.fontSize(16).text(section.toUpperCase(), { underline: true });
    const payload = data[section];
    doc.moveDown();
    doc.fontSize(12).text(JSON.stringify(payload ?? {}, null, 2));
  });

  return doc;
}
