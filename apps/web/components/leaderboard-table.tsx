type LeaderboardRow = {
  rank: number;
  participant: string;
  score: number;
  approvedTasks: number;
};

export function LeaderboardTable({ rows }: { rows: LeaderboardRow[] }) {
  return (
    <div className="leaderboard-table" role="table" aria-label="Leaderboard">
      <div className="leaderboard-row leaderboard-header" role="row">
        <span>Rank</span>
        <span>Participant</span>
        <span>Tasks</span>
        <span>Points</span>
      </div>
      {rows.map((row) => (
        <div
          className="leaderboard-row"
          role="row"
          key={`${row.rank}-${row.participant}`}
        >
          <strong>#{row.rank}</strong>
          <span>{row.participant}</span>
          <span>{row.approvedTasks}</span>
          <strong>{row.score}</strong>
        </div>
      ))}
    </div>
  );
}
