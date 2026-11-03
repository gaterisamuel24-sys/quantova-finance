import { CircleAlert, CircleCheck, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

const TONES: Record<
  "info" | "success" | "warning" | "error",
  { box: string; icon: string; Icon: LucideIcon }
> = {
  info: { box: "border-brand/30 bg-brand/5", icon: "text-brand", Icon: Info },
  success: { box: "border-positive/30 bg-positive/5", icon: "text-positive", Icon: CircleCheck },
  warning: { box: "border-warning/40 bg-warning/10", icon: "text-warning", Icon: TriangleAlert },
  error: { box: "border-negative/30 bg-negative/5", icon: "text-negative", Icon: CircleAlert },
};

type AlertProps = {
  tone?: keyof typeof TONES;
  title?: string;
  children?: ReactNode;
  className?: string;
};

export function Alert({ tone = "info", title, children, className }: AlertProps) {
  const { box, icon, Icon } = TONES[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-xl border p-4 text-sm", box, className)}
    >
      <Icon className={cn("mt-0.5 size-4 shrink-0", icon)} aria-hidden="true" />
      <div className="grid gap-1">
        {title && <p className="font-medium text-foreground">{title}</p>}
        {children && <div className="text-muted-foreground">{children}</div>}
      </div>
    </div>
  );
}
