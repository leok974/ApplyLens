import { useMailboxTheme } from "@/hooks/useMailboxTheme";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import type { MailboxThemeId } from "@/themes/mailbox";

export function MailboxThemePanel() {
  const { themeId, setThemeId, availableThemes } = useMailboxTheme();

  return (
    <Card data-testid="mailbox-theme-settings">
      <CardHeader>
        <CardTitle>Mailbox theme</CardTitle>
        <p className="text-sm text-muted-foreground">
          Choose how the Mailbox Assistant /chat page looks. This only affects
          the assistant view, not your inbox layout.
        </p>
      </CardHeader>
      <CardContent>
        <RadioGroup
          value={themeId}
          onValueChange={(value) => setThemeId(value as MailboxThemeId)}
          className="grid gap-3 md:grid-cols-3"
        >
          {availableThemes.map((t) => {
            const isActive = themeId === t.id;

            return (
              <Label
                key={t.id}
                htmlFor={`mailbox-theme-${t.id}`}
                className="group cursor-pointer"
              >
                <Card
                  className={[
                    "flex h-full flex-col justify-between gap-2 border transition",
                    "p-3",
                    isActive
                      ? "ring-1 ring-primary border-primary"
                      : "hover:border-muted-foreground/50",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  style={{
                    backgroundColor: t.colors.bgSurfaceElevated,
                    boxShadow: isActive ? t.shadows.ambientGlow : undefined,
                  }}
                  data-testid={`mailbox-theme-option-${t.id}`}
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <RadioGroupItem
                          id={`mailbox-theme-${t.id}`}
                          value={t.id}
                        />
                        <span className="text-sm font-medium" style={{ color: t.colors.textPrimary }}>
                          {t.label}
                        </span>
                      </div>
                      {isActive && (
                        <Badge variant="outline" className="text-[10px]">
                          Active
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs" style={{ color: t.colors.textMuted }}>
                      {t.description}
                    </p>
                  </div>
                  {/* Tiny preview strip using the theme's accent or intent colors */}
                  <div className="mt-2 flex h-2 w-full overflow-hidden rounded-full">
                    <div
                      className="flex-1"
                      style={{ backgroundColor: t.colors.accentPrimary }}
                    />
                    <div
                      className="flex-1"
                      style={{ backgroundColor: t.colors.intentInfo }}
                    />
                    <div
                      className="flex-1"
                      style={{ backgroundColor: t.colors.intentSuccess }}
                    />
                  </div>
                </Card>
              </Label>
            );
          })}
        </RadioGroup>
      </CardContent>
    </Card>
  );
}
