import { useMailboxTheme } from "@/hooks/useMailboxTheme";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { MailboxThemeId } from "@/themes/mailbox";

export function MailboxThemePanel() {
  const { themeId, setThemeId, availableThemes } = useMailboxTheme();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mailbox theme</CardTitle>
        <p className="text-sm text-muted-foreground">
          Switch between Classic, Banana Pro, and Deep Space layouts.
        </p>
      </CardHeader>
      <CardContent>
        <RadioGroup
          value={themeId}
          onValueChange={(value) => setThemeId(value as MailboxThemeId)}
          className="grid gap-3 md:grid-cols-3"
        >
          {availableThemes.map((t) => (
            <div
              key={t.id}
              className="flex flex-col gap-2 rounded-xl border p-3 cursor-pointer hover:border-primary"
            >
              <div className="flex items-center gap-2">
                <RadioGroupItem id={t.id} value={t.id} />
                <Label htmlFor={t.id} className="font-medium cursor-pointer">
                  {t.label}
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                {t.description}
              </p>
            </div>
          ))}
        </RadioGroup>
      </CardContent>
    </Card>
  );
}
