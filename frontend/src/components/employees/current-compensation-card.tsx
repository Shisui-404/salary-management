import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Employee } from "@/lib/api/types";
import {
  compaRatioToBadgeVariant,
  formatCompaRatio,
  formatDate,
  formatMoney,
  humanizeEnum,
} from "@/lib/format";
import { BandGauge } from "./band-gauge";
import { BandPositionBadge } from "./band-position-badge";

export function CurrentCompensationCard({
  employee,
  actions,
}: {
  employee: Employee;
  actions?: React.ReactNode;
}) {
  const salary = employee.current_salary;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Current compensation</CardTitle>
        {actions && <CardAction>{actions}</CardAction>}
      </CardHeader>
      <CardContent className="space-y-6">
        {!salary ? (
          <p className="text-sm text-muted-foreground">
            No salary has been recorded for this employee yet.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat
                label="Local salary"
                value={formatMoney(salary.amount, salary.currency)}
              />
              <Stat
                label={`Base (${salary.base_currency})`}
                value={formatMoney(salary.amount_base, salary.base_currency)}
              />
              <Stat
                label="Compa-ratio"
                value={
                  <Badge
                    variant={compaRatioToBadgeVariant(employee.compa_ratio)}
                    className="tabular-nums"
                  >
                    {formatCompaRatio(employee.compa_ratio)}
                  </Badge>
                }
              />
              <Stat
                label="Band position"
                value={<BandPositionBadge position={employee.band_position} />}
              />
            </div>

            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-muted-foreground">Effective from</dt>
                <dd>{formatDate(salary.effective_from)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Last change reason</dt>
                <dd>{humanizeEnum(salary.change_reason)}</dd>
              </div>
            </dl>

            {employee.band ? (
              <div>
                <p className="mb-2 text-sm font-medium">Band position</p>
                <BandGauge
                  band={employee.band}
                  amountBase={salary.amount_base}
                  baseCurrency={salary.base_currency}
                />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No salary band is defined for this role, level and country —
                compa-ratio can&apos;t be computed.
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="mt-0.5 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}
