import { useEffect, useState } from "react";
import {
  fetchSenderOverrides,
  addMutedSender,
  addSafeSender,
  deleteSenderOverride,
  SenderOverride,
} from "../lib/api";

import { useRuntimeConfig } from "../hooks/useRuntimeConfig";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function SettingsSendersPage() {
  const { config } = useRuntimeConfig();
  const readOnly = config.readOnly ?? false;

  const [overrides, setOverrides] = useState<SenderOverride[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSender, setNewSender] = useState("");
  const [addingBusy, setAddingBusy] = useState<"mute" | "safe" | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await fetchSenderOverrides();
      setOverrides(data.overrides || []);
      setErrorMsg(null);
    } catch (err: any) {
      setErrorMsg("Failed to load overrides");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleAdd(type: "mute" | "safe") {
    if (!newSender.trim()) return;
    if (readOnly) return;
    setAddingBusy(type);
    try {
      if (type === "mute") {
        await addMutedSender(newSender.trim());
      } else {
        await addSafeSender(newSender.trim());
      }
      setNewSender("");
      await refresh();
    } catch (err: any) {
      setErrorMsg("Failed to add override");
    } finally {
      setAddingBusy(null);
    }
  }

  async function handleDelete(id: string) {
    if (readOnly) return;
    setDeletingId(id);
    try {
      await deleteSenderOverride(id);
      await refresh();
    } catch (err: any) {
      setErrorMsg("Failed to delete override");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="p-4 flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-white">Sender Controls</h1>
        <p className="text-sm text-muted-foreground">
          Auto-mute noisy senders (future emails go straight to Archived) or
          mark trusted senders as safe (we stop flagging them as risky).
        </p>
      </div>

      <Card className="p-4 bg-card/50 border-border/50 space-y-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-white">
            Add sender or domain
          </label>
          <Input
            placeholder="e.g. recruiter@company.com or @company.com"
            value={newSender}
            onChange={(e) => setNewSender(e.target.value)}
            className="bg-background text-white"
            disabled={readOnly || addingBusy !== null}
          />
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="secondary"
              disabled={readOnly || addingBusy !== null}
              onClick={() => handleAdd("mute")}
            >
              {addingBusy === "mute" ? "Muting..." : "Mute sender"}
            </Button>
            <Button
              variant="default"
              disabled={readOnly || addingBusy !== null}
              onClick={() => handleAdd("safe")}
            >
              {addingBusy === "safe" ? "Marking safe..." : "Mark safe"}
            </Button>
          </div>
          {readOnly ? (
            <p className="text-[11px] text-yellow-400">
              Restricted mode: changes are disabled.
            </p>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              Muted senders are auto-archived. Safe senders won't get flagged
              as risky.
            </p>
          )}
        </div>
      </Card>

      <Card className="p-4 bg-card/50 border-border/50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">Your overrides</h2>
          {loading ? (
            <span className="text-xs text-muted-foreground">Loading…</span>
          ) : (
            <span className="text-xs text-muted-foreground">
              {overrides.length} total
            </span>
          )}
        </div>

        {errorMsg && (
          <div className="text-xs text-red-400 mb-2">{errorMsg}</div>
        )}

        {!loading && overrides.length === 0 ? (
          <div className="text-sm text-muted-foreground py-8 text-center">
            You haven't muted or safelisted anyone yet.
          </div>
        ) : (
          <ul className="divide-y divide-border/50">
            {overrides.map((ov) => (
              <li
                key={ov.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between py-3 gap-2"
              >
                <div className="min-w-0">
                  <div className="text-white text-sm font-medium break-all">
                    {ov.sender}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    {ov.safe && (
                      <Badge variant="secondary" className="bg-green-600/20 text-green-200 border-green-700">Safe</Badge>
                    )}
                    {ov.muted && (
                      <Badge variant="outline">Muted</Badge>
                    )}
                    <div className="text-[10px] text-muted-foreground">
                      Updated {new Date(ov.updated_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex-shrink-0">
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={readOnly || deletingId === ov.id}
                    onClick={() => handleDelete(ov.id)}
                  >
                    {deletingId === ov.id ? "Removing…" : "Remove"}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
