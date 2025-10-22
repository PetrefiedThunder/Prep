const { test } = require("node:test");
const assert = require("node:assert");
const { execSync } = require("child_process");

test("ESLint security rules", () => {
  try {
    execSync("npx --no-install eslint --version", { stdio: "pipe" });
  } catch (error) {
    console.warn("Skipping ESLint security rules test: eslint not installed");
    return;
  }

  try {
    execSync("npx --no-install eslint . --quiet", { stdio: "pipe" });
  } catch (error) {
    const output =
      error.stdout?.toString() || error.stderr?.toString() || error.message;
    if (output && output.includes("Cannot find module 'eslint-plugin-security'")) {
      console.warn("Skipping ESLint security rules test: eslint-plugin-security not installed");
      return;
    }

    console.error("ESLint security check failed:", output);
    throw new Error("Security linting failed");
  }
});

test("No hardcoded secrets present", () => {
  const forbiddenPatterns = [
    /password\s*=\s*['\"][^'\"]+['\"]/gi,
    /secret\s*=\s*['\"][^'\"]+['\"]/gi,
    /api[_-]?key\s*=\s*['\"][^'\"]+['\"]/gi,
    /token\s*=\s*['\"][^'\"]+['\"]/gi
  ];

  const files = execSync(
    "find . -name \"*.js\" -o -name \"*.ts\" -o -name \"*.json\" | grep -v node_modules | grep -v dist",
    { encoding: "utf8" }
  );

  const fileArray = files.trim().split("\n");
  let foundSecrets = false;

  fileArray.forEach((file) => {
    if (file) {
      try {
        const content = execSync(`cat ${file}`, { encoding: "utf8" });
        forbiddenPatterns.forEach((pattern) => {
          if (pattern.test(content)) {
            console.error(`Hardcoded secret found in ${file}`);
            foundSecrets = true;
          }
        });
      } catch (error) {
        // Ignore unreadable files
      }
    }
  });

  assert.strictEqual(foundSecrets, false, "Hardcoded secrets detected in repository");
});
