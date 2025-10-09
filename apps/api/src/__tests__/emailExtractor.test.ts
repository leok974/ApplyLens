// NOTE: Install test types if missing: npm install --save-dev @types/jest
// @ts-ignore - Test framework may not be configured
import { extractFromEmail } from '../services/emailExtractor'

// Global test declarations for environments without test types
declare global {
  function describe(name: string, fn: () => void): void
  function it(name: string, fn: () => void): void
  function expect(actual: any): any
}

describe('email extractor', () => {
  it('extracts company from sender domain', () => {
    const r = extractFromEmail({
      from: 'Jane Doe <jane@acme.ai>',
      subject: 'Re: Application for ML Engineer',
      text: 'Thanks, Jane\nAcme AI — Recruiting',
    })
    expect(r.company).toMatch(/acme/i)
  })

  it('extracts role from subject', () => {
    const r = extractFromEmail({
      subject: 'Next steps — Senior Software Engineer',
    })
    expect(r.role?.toLowerCase()).toContain('senior software engineer')
  })

  it('detects Greenhouse with high confidence', () => {
    const r = extractFromEmail({
      headers: { 'List-Unsubscribe': '<mailto:unsub@mailer.greenhouse.io>' },
      text: 'You received this message via Greenhouse. Unsubscribe here.',
    })
    expect(r.source).toBe('Greenhouse')
    expect(r.source_confidence).toBeGreaterThan(0.9)
  })

  it('detects Lever via headers', () => {
    const r = extractFromEmail({
      headers: { 'X-Mailer': 'mailer.lever.co' },
      text: 'Sent via Lever',
    })
    expect(r.source).toBe('Lever')
  })
})
