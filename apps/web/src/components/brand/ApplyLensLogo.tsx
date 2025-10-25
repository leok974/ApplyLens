import { cn } from "@/lib/utils";

export function ApplyLensLogo(props: React.SVGProps<SVGSVGElement>) {
  return (
    <img
      src="/ApplyLensLogo.png"
      alt="ApplyLens"
      className={cn("h-7 w-7", props.className)}
      aria-hidden="true"
    />
  );
}
