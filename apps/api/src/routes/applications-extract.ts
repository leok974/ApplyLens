// NOTE: Install Express types if missing: npm install --save-dev @types/express
// @ts-ignore - Express may not be installed in this workspace
import { Router, Request, Response } from 'express'
import { extractFromEmail } from '../services/emailExtractor'

// You likely already have a db module; we keep this minimal & defensive
type DB = {
  run: (sql: string, params?: any[]) => { lastID?: number }
  get: <T = any>(sql: string, params?: any[]) => T
  all: <T = any>(sql: string, params?: any[]) => T[]
}

export default function applicationsExtractRoutes(db: DB) {
  const r = Router()

  /**
   * POST /api/applications/extract
   * Body: { subject?, from?, headers?, text?, html? }
   * Returns: { company?, role?, source?, source_confidence, debug? }
   */
  r.post('/extract', async (req: Request, res: Response) => {
    try {
      const result = extractFromEmail(req.body || {})
      res.json(result)
    } catch (e) {
      console.error('extract error', e)
      res.status(400).json({ error: 'bad_request' })
    }
  })

  /**
   * POST /api/applications/backfill-from-email
   * Body: {
   *   subject?, from?, headers?, text?, html?,
   *   gmail_thread_id?, // optional linkage
   *   defaults?: { source?: string } // optional forced fields
   * }
   * Behavior:
   *   - extract fields
   *   - create application row (if not exists for same company+role+thread) or update existing
   *   - return saved row
   */
  r.post('/backfill-from-email', async (req: Request, res: Response) => {
    try {
      const payload = req.body || {}
      const ext = extractFromEmail(payload)
      const company = (payload.company || ext.company || '').trim()
      const role = (payload.role || ext.role || '').trim()
      const source =
        (payload.defaults?.source || ext.source || payload.source || '').trim() || null
      const source_confidence = Number.isFinite(ext.source_confidence)
        ? ext.source_confidence
        : 0.5
      const gmail_thread_id = payload.gmail_thread_id || null

      if (!company && !role) {
        return res
          .status(422)
          .json({ error: 'insufficient_fields', hint: 'Need at least company or role' })
      }

      // Try find existing row by gmail_thread_id or (company+role)
      let existing: any = null
      if (gmail_thread_id) {
        existing = db.get('SELECT * FROM applications WHERE thread_id = ?', [gmail_thread_id])
      }
      if (!existing && company && role) {
        existing = db.get(
          'SELECT * FROM applications WHERE company = ? AND role = ? ORDER BY id DESC LIMIT 1',
          [company, role]
        )
      }

      const now = new Date().toISOString()
      if (!existing) {
        const result = db.run(
          `INSERT INTO applications (company, role, source, source_confidence, status, thread_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
          [company || null, role || null, source, source_confidence, 'applied', gmail_thread_id, now, now]
        )
        const row = db.get('SELECT * FROM applications WHERE id = ?', [result.lastID])
        return res.json({ saved: row, extracted: ext })
      } else {
        // merge, don't clobber manually-set fields unless missing
        const nextCompany = existing.company || company || null
        const nextRole = existing.role || role || null
        const nextSource = existing.source || source || null
        const nextThread = existing.thread_id || gmail_thread_id || null
        const nextConf = existing.source_confidence ?? source_confidence
        db.run(
          `UPDATE applications SET company = ?, role = ?, source = ?, source_confidence = ?, thread_id = ?, updated_at = ?
           WHERE id = ?`,
          [nextCompany, nextRole, nextSource, nextConf, nextThread, now, existing.id]
        )
        const row = db.get('SELECT * FROM applications WHERE id = ?', [existing.id])
        return res.json({ saved: row, extracted: ext, updated: true })
      }
    } catch (e) {
      console.error('backfill-from-email error', e)
      res.status(400).json({ error: 'bad_request' })
    }
  })

  return r
}
