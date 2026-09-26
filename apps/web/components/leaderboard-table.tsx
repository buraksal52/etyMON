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
        <span role="columnheader">Sıra</span>
        <span role="columnheader">Katılımcı</span>
        <span role="columnheader" className="num">
          Görev
        </span>
        <span role="columnheader" className="num">
          Puan
        </span>
      </div>
      {rows.map((row) => (
        <div
          className={`leaderboard-row${row.rank <= 3 ? ` podium podium-${row.rank}` : ""}`}
          role="row"
          key={`${row.rank}-${row.participant}`}
        >
          <strong role="cell" className="rank">
            #{row.rank}
          </strong>
          <span role="cell" className="name">
            {row.participant}
          </span>
          <span role="cell" className="num">
            {row.approvedTasks}
          </span>
          <strong role="cell" className="num">
            {row.score}
          </strong>
        </div>
      ))}
    </div>
  );
}
