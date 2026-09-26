import { eventStateLabel, reviewStatusLabel } from "../lib/format";

export function EventStateBadge({ state }: { state: string }) {
  return (
    <span className={`badge badge-state-${state.toLowerCase()}`}>
      {eventStateLabel(state)}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`badge badge-status-${status.toLowerCase()}`}>
      {reviewStatusLabel(status)}
    </span>
  );
}
