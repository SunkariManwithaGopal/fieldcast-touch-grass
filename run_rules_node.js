const fs = require('fs');

// 1. Read index.html and extract the exact snippet
const html = fs.readFileSync('index.html', 'utf8');
const lines = html.split(/\r?\n/);

// Lines 1822 to 1844 (0-indexed: 1821 to 1844)
// Let's locate dynamically by content to be robust
const startIdx = lines.findIndex(l => l.includes('let probs = {') && lines[lines.indexOf(l) - 1].includes('catch (e)'));
const endIdx = lines.findIndex((l, idx) => idx > startIdx && l.includes('return {') && lines[idx + 1].includes('engine:'));
const finalReturnIdx = lines.findIndex((l, idx) => idx > endIdx && l.includes('};') && lines[idx - 1].includes('best_window_today:'));

if (startIdx === -1 || finalReturnIdx === -1) {
    console.error("Could not find exact rule block in index.html!");
    process.exit(1);
}

const extractedBody = lines.slice(startIdx, finalReturnIdx + 1).join('\n');
console.error(`[Node Runner] Extracted ${finalReturnIdx - startIdx + 1} lines from index.html (lines ${startIdx + 1} to ${finalReturnIdx + 1}).`);

// Create function dynamically
const ruleClassifier = new Function('payload', extractedBody);

// Read input payloads
const inputFile = process.argv[2];
if (!inputFile) {
    console.error("Usage: node run_rules_node.js <inputs.json>");
    process.exit(1);
}

const rows = JSON.parse(fs.readFileSync(inputFile, 'utf8'));
const results = rows.map(r => ruleClassifier(r));

console.log(JSON.stringify(results));
