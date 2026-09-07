import type { BandPosition } from "@/lib/api/types";
import { bandPositionLabel, bandPositionToColorClasses } from "@/lib/format";
import { cn } from "@/lib/utils";

export function BandPositionBadge({
  position,
  className,
}: {
  position: BandPosition;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        bandPositionToColorClasses(position),
        className,
      )}
    >
      {bandPositionLabel(position)}
    </span>
  );
}
