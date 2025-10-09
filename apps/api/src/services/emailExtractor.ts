// Email extractor: company, role, source (+confidence)
// Heuristics: sender domain, signature lines, subject patterns, headers
export type ExtractInput = {
  subject?: string
  from?: string // e.g., "Jane @ Acme <jane@acme.ai>"
  headers?: Record<string, string | undefined>
  text?: string // plain text body (best effort)
  html?: string // optional; we will strip tags lightly
}

export type ExtractResult = {
  company?: string
  role?: string
  source?: string
  source_confidence: number // 0..1
  debug?: Record<string, unknown>
}

const KNOWN_SOURCES: Array<{
  name: string
  test: (h: Record<string, string | undefined>, body: string) => boolean
}> = [
  {
    name: 'Greenhouse',
    test: (h, body) =>
      /greenhouse\.io|mailer[-.]greenhouse\.io/i.test(headersConcat(h)) ||
      (/Greenhouse/i.test(body) && /unsubscribe.*greenhouse/i.test(body)),
  },
  {
    name: 'Lever',
    test: (h, body) =>
      /hire\.lever\.co|lever\.co|mailer\..*lever/i.test(headersConcat(h)) ||
      (/Lever/i.test(body) && /unsubscribe.*lever/i.test(body)),
  },
  {
    name: 'Workday',
    test: (h, body) =>
      /workday\.com|myworkday/i.test(headersConcat(h)) || /Workday/i.test(body),
  },
]

function headersConcat(h: Record<string, string | undefined> = {}) {
  return Object.entries(h)
    .map(([k, v]) => `${k}:${v ?? ''}`)
    .join('\n')
}

function sanitizeText(s?: string) {
  if (!s) return ''
  // strip basic HTML tags if any leaked into text
  return s
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function extractCompanyFromFromHeader(from?: string): string | undefined {
  if (!from) return
  // Try display name portion first: "Jane from Acme" or "Acme Recruiting"
  const display =
    from.replace(/.*</, '').replace(/>.*/, '').trim() !== from
      ? from.replace(/<.*>/, '').trim()
      : from
  const mFrom = display.match(/\bfrom\s+([A-Z][\w&.\- ]{1,40})/i)
  if (mFrom) return cleanCompany(mFrom[1])
  const mRecruit = display.match(
    /\b([A-Z][\w&.\- ]{1,40})\s+(Recruiting|Careers|Talent|HR)\b/i
  )
  if (mRecruit) return cleanCompany(mRecruit[1])
  // Domain-based: jane@acme.ai → acme
  const mEmail = from.match(/[\w.+-]+@([\w.-]+\.[a-z]{2,})/i)
  if (mEmail) {
    const domain = mEmail[1].toLowerCase()
    const parts = domain.split('.')
    // strip common subdomains/tlds
    const core = parts
      .filter(
        (p) =>
          !['mail', 'email', 'jobs', 'careers', 'apply', 'recruiting', 'hr', 'www'].includes(p)
      )
      .slice(0, -1) // remove tld
      .pop()
    if (core && !['gmail', 'outlook', 'yahoo', 'icloud', 'hotmail'].includes(core)) {
      return cleanCompany(core)
    }
  }
  return
}

function cleanCompany(c: string) {
  return c
    .replace(/[^A-Za-z0-9&.\- ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function extractCompanyFromSignature(text: string): string | undefined {
  // look for signature blocks with company lines
  const lines = text
    .split(/\n|\r/)
    .map((l) => l.trim())
    .filter(Boolean)
  for (let i = 0; i < Math.min(lines.length, 30); i++) {
    const l = lines[i]
    // "Acme AI — Recruiting", "Acme • Talent", "Acme, Inc."
    if (
      /^[A-Z][\w&.\- ]{1,40}(,? (Inc\.?|LLC|Ltd\.?))?(\s*[•—-]\s*(Talent|Recruiting|Careers))?$/.test(
        l
      )
    ) {
      // filter out generic words
      if (!/^(Thanks|Best|Regards|Sent from|On \w{3}|\w+@\w+)/i.test(l)) {
        return cleanCompany(l.replace(/\s*[•—-].*$/, ''))
      }
    }
  }
  return
}

// role from subject: "(?:for|–|—)\s*(.*(engineer|designer|manager).*)"
const ROLE_RE = new RegExp(
  String.raw`(?:\bfor\b|[–—-])\s*([A-Za-z0-9()\/,&.\- ]*(engineer|designer|manager|scientist|analyst|developer|lead)[A-Za-z0-9()\/,&.\- ]*)`,
  'i'
)

function extractRoleFromSubject(subject?: string): string | undefined {
  if (!subject) return
  const m = subject.match(ROLE_RE)
  if (m && m[1]) {
    return m[1].replace(/\s+/g, ' ').trim()
  }
  return
}

function detectSource(headers: Record<string, string | undefined>, body: string) {
  const hay = headersConcat(headers)
  // list-unsubscribe heuristics
  const lu = ((headers['list-unsubscribe'] || headers['List-Unsubscribe'] || '') as string)
  const via = ((headers['x-mailer'] ||
    headers['X-Mailer'] ||
    headers['x-ses-outgoing'] ||
    '') as string)
  // Known ATS
  for (const s of KNOWN_SOURCES) {
    if (s.test(headers, body)) return { source: s.name, confidence: 0.9 }
  }
  // generic
  if (/unsubscribe/i.test(lu)) return { source: 'mailing-list', confidence: 0.6 }
  if (/ses\.amazonaws\.com/i.test(via)) return { source: 'SES', confidence: 0.5 }
  if (/sendgrid|mailgun|postmark/i.test(hay)) return { source: 'ESP', confidence: 0.5 }
  return { source: undefined, confidence: 0.4 }
}

export function extractFromEmail(input: ExtractInput): ExtractResult {
  const subject = sanitizeText(input.subject)
  const body = sanitizeText(input.text || input.html || '')
  const headers = input.headers || {}

  const role = extractRoleFromSubject(subject)
  const companyFromFrom = extractCompanyFromFromHeader(input.from)
  const companyFromSig = extractCompanyFromSignature(body)
  const company = companyFromFrom || companyFromSig

  const src = detectSource(headers, body)
  const source = src.source
  let source_confidence = src.confidence

  // Confidence tweaks
  if (source && /Greenhouse|Lever|Workday/.test(source)) source_confidence = 0.95
  if (!source && /apply|requisition|job|opening/i.test(body))
    source_confidence = Math.max(source_confidence, 0.55)

  return {
    company: company || undefined,
    role: role || undefined,
    source,
    source_confidence,
    debug: { companyFromFrom, companyFromSig, matchedRole: !!role },
  }
}
