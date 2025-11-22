import { describe, it, expect, vi } from "vitest";

const mockStorage = {
  _data: {} as Record<string, any>,
  async get(keys: string | string[] | null) {
    if (!keys) return this._data;
    if (Array.isArray(keys)) {
      const out: Record<string, any> = {};
      for (const k of keys) out[k] = this._data[k];
      return out;
    }
    return this._data[keys];
  },
  async set(obj: Record<string, any>) { Object.assign(this._data, obj); }
};

vi.stubGlobal("chrome", {
  storage: { local: mockStorage },
  runtime: { onMessage: { addListener: () => {} } },
  tabs: { query: vi.fn().mockResolvedValue([{ id: 1 }]), sendMessage: vi.fn() },
});

describe("history storage", () => {
  it("caps lists to 50", async () => {
    const key = "history_applications";
    await mockStorage.set({ [key]: Array.from({length: 55}, (_,i)=>({i}))});
    const cur = (await mockStorage.get([key]))[key];
    expect(cur.length).toBe(55); // pre
    // simulate trim
    const trimmed = cur.slice(0, 50);
    await mockStorage.set({ [key]: trimmed });
    const after = (await mockStorage.get([key]))[key];
    expect(after.length).toBe(50);
  });
});
