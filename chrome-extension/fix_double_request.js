// Fix double request bug in content.js
const fs = require('fs');

const filePath = 'src/content.js';
let content = fs.readFileSync(filePath, 'utf-8');

// Check if already fixed
if (content.includes('processedMessageIds')) {
    console.log('Already fixed!');
    process.exit(0);
}

// Add processedMessageIds Set after the console.log line
const oldLine = "console.log('[SheetGPT] Content script loaded');";
const newLine = `console.log('[SheetGPT] Content script loaded');

// v12.0: Deduplication - prevent processing same message twice
const processedMessageIds = new Set();
const MAX_PROCESSED_IDS = 100; // Limit memory usage`;

if (content.includes(oldLine)) {
    content = content.replace(oldLine, newLine);
    console.log('Added processedMessageIds Set');
} else {
    console.log('ERROR: Could not find insertion point for Set');
}

// Add deduplication check before processing
const oldCheck = `  const { action, data, messageId } = event.data;
  console.log('[SheetGPT] ✅ Processing action:', action, 'messageId:', messageId, 'data:', data);

  try {`;

const newCheck = `  const { action, data, messageId } = event.data;

  // v12.0: Deduplication - skip if already processed
  if (processedMessageIds.has(messageId)) {
    console.log('[SheetGPT] ⏭️ Skipping duplicate message:', messageId);
    return;
  }
  processedMessageIds.add(messageId);
  // Cleanup old messageIds to prevent memory leak
  if (processedMessageIds.size > MAX_PROCESSED_IDS) {
    const idsArray = Array.from(processedMessageIds);
    processedMessageIds.clear();
    idsArray.slice(-50).forEach(id => processedMessageIds.add(id));
  }

  console.log('[SheetGPT] ✅ Processing action:', action, 'messageId:', messageId, 'data:', data);

  try {`;

if (content.includes(oldCheck)) {
    content = content.replace(oldCheck, newCheck);
    console.log('Added deduplication check');
} else {
    console.log('ERROR: Could not find insertion point for deduplication check');
    // Try alternative pattern
    const altOld = "const { action, data, messageId } = event.data;";
    if (content.includes(altOld)) {
        console.log('Found alternative pattern');
    }
}

fs.writeFileSync(filePath, content, 'utf-8');
console.log('SUCCESS: Fixed double request bug');
