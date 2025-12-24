// Switch API to v2 SmartAnalyst
const fs = require('fs');

const filePath = 'src/content.js';
let content = fs.readFileSync(filePath, 'utf-8');

// Replace v1 with v2
content = content.replace(/api\/v1\/analyze/g, 'api/v2/analyze');

fs.writeFileSync(filePath, content, 'utf-8');
console.log('Switched to API v2 (SmartAnalyst)');
