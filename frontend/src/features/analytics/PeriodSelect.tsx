import { Select } from "../../components/ui/Select";
import { GRANULARITIES, PERIODS, type Granularity, type Period } from "./periods";

export function PeriodSelect({
  value,
  onChange,
}: {
  value: Period;
  onChange: (period: Period) => void;
}) {
  return (
    <Select
      aria-label="Period"
      className="w-48"
      value={value}
      onChange={(event) => onChange(event.target.value as Period)}
    >
      {PERIODS.map((period) => (
        <option key={period.value} value={period.value}>
          {period.label}
        </option>
      ))}
    </Select>
  );
}

export function GranularitySelect({
  value,
  onChange,
}: {
  value: Granularity;
  onChange: (granularity: Granularity) => void;
}) {
  return (
    <Select
      aria-label="Group by"
      className="w-36"
      value={value}
      onChange={(event) => onChange(event.target.value as Granularity)}
    >
      {GRANULARITIES.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </Select>
  );
}
