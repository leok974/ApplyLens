const fs = require('fs');
const file = 'src/pages/extension/ExtensionLanding.tsx';
let content = fs.readFileSync(file, 'utf8');

// 1. Add Link import
if (!content.includes('react-router-dom')) {
  content = content.replace(
    /import \{ (.*?) \} from "lucide-react";/,
    'import { Link } from "react-router-dom";\nimport { $1 } from "lucide-react";\n\nconst MAIN_APP_PATH = "/"; // Main app route (Job Inbox)'
  );
}

// 2. Add Back to ApplyLens button
const oldButtonSection = `            <div className="mt-6 flex flex-wrap items-center gap-3">
              <InstallButton />
              <a
                href="/extension/support"
                className="text-sm underline opacity-80 hover:opacity-100"
              >
                Need help?
              </a>
            </div>`;

const newButtonSection = `            <div className="mt-6 flex flex-wrap items-center gap-3">
              <InstallButton />

              <Link
                to={MAIN_APP_PATH}
                className="inline-flex items-center gap-2 rounded-2xl px-5 py-3 shadow hover:shadow-md transition
                           border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                data-testid="companion-back-to-app"
              >
                Back to ApplyLens
              </Link>

              <a
                href="/extension/support"
                className="text-sm underline opacity-80 hover:opacity-100"
              >
                Need help?
              </a>
            </div>`;

content = content.replace(oldButtonSection, newButtonSection);

fs.writeFileSync(file, content, 'utf8');
console.log('✅ File updated successfully');
