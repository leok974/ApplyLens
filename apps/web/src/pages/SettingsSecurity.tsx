import { PolicyPanel } from "@/components/security/PolicyPanel";

export default function SettingsSecurity() {
  return (
    <div className="mx-auto max-w-3xl p-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Security Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure automated security policies for email protection.
        </p>
      </div>
      <PolicyPanel />
    </div>
  );
}
