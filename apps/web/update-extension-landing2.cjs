const fs = require('fs');
const file = 'src/pages/extension/ExtensionLanding.tsx';
let content = fs.readFileSync(file, 'utf8');

// Find InstallButton and add the Link button after it
const lines = content.split('\n');
const newLines = [];
let added = false;

for (let i = 0; i < lines.length; i++) {
  newLines.push(lines[i]);

  // Look for the line with <InstallButton />
  if (!added && lines[i].trim() === '<InstallButton />') {
    // Add empty line and the Link button
    newLines.push('              ');
    newLines.push('              <Link');
    newLines.push('                to={MAIN_APP_PATH}');
    newLines.push('                className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 shadow hover:shadow-md transition');
    newLines.push('                           border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"');
    newLines.push('                data-testid="companion-back-to-app"');
    newLines.push('              >');
    newLines.push('                Back to ApplyLens');
    newLines.push('              </Link>');
    added = true;
  }
}

content = newLines.join('\n');
fs.writeFileSync(file, content, 'utf8');
console.log('✅ Back to ApplyLens button added');
