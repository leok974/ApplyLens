import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { loginWithGoogle, startDemo } from "@/api/auth";
import { Mail, Sparkles, Lock, Database, Shield, Zap } from "lucide-react";

export default function Landing() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleDemo = async () => {
    setBusy(true);
    setError(null);
    try {
      console.log('[Landing] Starting demo login');
      await startDemo();
      console.log('[Landing] Demo login successful, navigating to /inbox');
      // Use soft navigation instead of hard redirect
      navigate("/inbox", { replace: true });
      console.log('[Landing] navigate() called');
    } catch (err) {
      setError("Failed to start demo. Please try again.");
      console.error("[Landing] Demo start failed:", err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Hero Section */}
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          {/* Logo and Title */}
          <div className="space-y-4">
            <div className="inline-flex items-center justify-center mb-4">
              <img
                src="/ApplyLensLogo.png"
                alt="ApplyLens Logo"
                className="w-24 h-24 object-contain"
                draggable={false}
              />
            </div>
            <h1 className="text-5xl font-bold tracking-tight">
              ApplyLens
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Intelligent job application tracking powered by your Gmail inbox.
              Parse applications, track status, and stay organized—all automatically.
            </p>
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-8">
            <Button
              size="lg"
              onClick={loginWithGoogle}
              disabled={busy}
              className="min-w-[200px]"
            >
              <Mail className="w-5 h-5 mr-2" />
              Connect Gmail
            </Button>
            <Button
              size="lg"
              variant="secondary"
              onClick={handleDemo}
              disabled={busy}
              className="min-w-[200px]"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Try Demo
            </Button>
          </div>

          {error && (
            <div className="text-destructive text-sm">{error}</div>
          )}

          {/* Privacy Notice */}
          <p className="text-sm text-muted-foreground pt-4">
            <Lock className="w-4 h-4 inline mr-1" />
            Read-only OAuth. Your data stays yours. We never modify or send emails.
          </p>
        </div>

        {/* Features Grid */}
        <div className="max-w-5xl mx-auto mt-24 grid md:grid-cols-3 gap-8">
          <div className="space-y-3 p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Automatic Parsing</h3>
            <p className="text-sm text-muted-foreground">
              Automatically extract company names, job titles, and application status from your emails.
            </p>
          </div>

          <div className="space-y-3 p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <Database className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Centralized Tracking</h3>
            <p className="text-sm text-muted-foreground">
              All your applications in one place. Search, filter, and manage with ease.
            </p>
          </div>

          <div className="space-y-3 p-6 rounded-lg border bg-card">
            <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Privacy First</h3>
            <p className="text-sm text-muted-foreground">
              Read-only access. Your data never leaves your control. No emails sent on your behalf.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="max-w-3xl mx-auto mt-24 space-y-6">
          <h2 className="text-3xl font-bold text-center">How It Works</h2>
          <div className="space-y-4">
            <div className="flex gap-4 items-start p-4 rounded-lg border bg-card">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                1
              </div>
              <div>
                <h4 className="font-semibold mb-1">Connect Your Gmail</h4>
                <p className="text-sm text-muted-foreground">
                  Grant read-only access to your inbox via secure Google OAuth.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start p-4 rounded-lg border bg-card">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                2
              </div>
              <div>
                <h4 className="font-semibold mb-1">Automatic Parsing</h4>
                <p className="text-sm text-muted-foreground">
                  ApplyLens scans your inbox and extracts job application emails automatically.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start p-4 rounded-lg border bg-card">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-semibold">
                3
              </div>
              <div>
                <h4 className="font-semibold mb-1">Track & Manage</h4>
                <p className="text-sm text-muted-foreground">
                  View all applications in one dashboard. Search, filter, and track your progress.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="max-w-3xl mx-auto mt-24 pt-8 border-t text-center text-sm text-muted-foreground">
          <p>© 2025 ApplyLens. Your job search, simplified.</p>
        </div>
      </div>
    </div>
  );
}
