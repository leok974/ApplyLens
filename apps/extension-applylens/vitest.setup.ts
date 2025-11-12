// Minimal chrome API mocks for unit tests
globalThis.chrome = {
  runtime: {
    sendMessage: vi.fn(async () => ({ ok: true, data: { name: "Leo Klemet" } })),
    onMessage: { addListener: vi.fn(), removeListener: vi.fn(), hasListener: vi.fn(), dispatch: vi.fn() },
    id: "test-ext-id"
  },
  tabs: {
    query: vi.fn(async () => [{ id: 123 }]),
    sendMessage: vi.fn(async () => ({ ok: true })),
  },
  scripting: {
    executeScript: vi.fn(async () => [{}]),
  },
} as any;

Object.defineProperty(window.navigator, "clipboard", {
  value: { writeText: vi.fn(async () => void 0) },
});

// Fetch mock helper
globalThis.fetch = vi.fn(async () =>
  new Response(JSON.stringify({ ok: true, data: { answers: [{ field_id:"cover_letter", answer: "Because ApplyLens!" }] } }), {
    headers: { "content-type": "application/json" }
  })
) as any;
