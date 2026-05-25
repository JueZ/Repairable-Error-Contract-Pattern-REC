import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

const root = process.cwd();

function readJson(relativePath) {
  const fullPath = path.join(root, relativePath);
  return JSON.parse(fs.readFileSync(fullPath, "utf8"));
}

function walk(dir) {
  const fullDir = path.join(root, dir);
  if (!fs.existsSync(fullDir)) {
    return [];
  }

  const entries = fs.readdirSync(fullDir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const relative = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(relative));
    } else {
      files.push(relative);
    }
  }

  return files;
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const ajv = new Ajv2020({
  allErrors: true,
  strict: true
});

addFormats(ajv);

const repairableProblemSchema = readJson("schemas/repairable-problem.schema.json");
const diagnosticCapsuleSchema = readJson("schemas/diagnostic-capsule.schema.json");

const validateRepairableProblem = ajv.compile(repairableProblemSchema);
const validateDiagnosticCapsule = ajv.compile(diagnosticCapsuleSchema);

const validRepairableExamples = walk("examples")
  .filter((file) => file.endsWith(".rec.json"))
  .filter((file) => !file.startsWith("examples/invalid/"));

const validDiagnosticCapsules = walk("examples")
  .filter((file) => file.endsWith("diagnostic-capsule.example.json"))
  .filter((file) => !file.startsWith("examples/invalid/"));

const invalidExamples = walk("examples/invalid").filter((file) => file.endsWith(".json"));

assert(validRepairableExamples.length > 0, "No valid REC examples found.");
assert(validDiagnosticCapsules.length > 0, "No valid diagnostic capsule examples found.");
assert(invalidExamples.length > 0, "No invalid examples found.");

for (const file of validRepairableExamples) {
  const data = readJson(file);
  const valid = validateRepairableProblem(data);

  if (!valid) {
    console.error(`Validation failed for ${file}`);
    console.error(validateRepairableProblem.errors);
  }

  assert(valid, `${file} should be a valid RepairableProblem.`);
}

for (const file of validDiagnosticCapsules) {
  const data = readJson(file);
  const valid = validateDiagnosticCapsule(data);

  if (!valid) {
    console.error(`Validation failed for ${file}`);
    console.error(validateDiagnosticCapsule.errors);
  }

  assert(valid, `${file} should be a valid DiagnosticCapsule.`);
}

for (const file of invalidExamples) {
  const data = readJson(file);
  const validator = file.includes("diagnostic-capsule")
    ? validateDiagnosticCapsule
    : validateRepairableProblem;

  const valid = validator(data);

  assert(!valid, `${file} is an invalid fixture and must fail validation.`);
}

const textFilesToScan = walk(".")
  .filter((file) => {
    if (file.startsWith("node_modules/")) {
      return false;
    }
    if (file.startsWith(".git/")) {
      return false;
    }
    return [".md", ".json", ".yml", ".yaml", ".cff", ".js", ".mjs"].includes(path.extname(file));
  });

const staleVersionPatterns = [
  /"rec_version"\s*:\s*"1\.0"/,
  /recVersion:\s*"1\.0"/
];

for (const file of textFilesToScan) {
  const content = fs.readFileSync(path.join(root, file), "utf8");
  for (const pattern of staleVersionPatterns) {
    assert(!pattern.test(content), `${file} contains stale REC version 1.0.`);
  }
}

console.log("REC schema validation passed.");
console.log(`Validated ${validRepairableExamples.length} public REC example(s).`);
console.log(`Validated ${validDiagnosticCapsules.length} diagnostic capsule example(s).`);
console.log(`Confirmed ${invalidExamples.length} invalid fixture(s) fail validation.`);
