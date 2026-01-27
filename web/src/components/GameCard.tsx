"use client";

import Link from "next/link";
import Image from "next/image";
import { GameSummary } from "@/lib/api";
import { getTeamLogo } from "@/lib/logos";

interface GameCardProps {
  game: GameSummary;
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colors = {
    high: "bg-emerald-100 text-emerald-700 border-emerald-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-slate-100 text-slate-600 border-slate-200",
  };

  return (
    <span
      className={`px-2 py-0.5 text-xs font-medium rounded-full border ${
        colors[confidence as keyof typeof colors] || colors.low
      }`}
    >
      {confidence}
    </span>
  );
}

function formatOdds(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

export default function GameCard({ game }: GameCardProps) {
  const isCompleted = game.is_completed;

  // Determine if game is live based on current time vs game start time
  const isLive = (() => {
    if (isCompleted) return false;
    if (!game.game_time) return false;

    const now = new Date();
    // Backend sends UTC times, append 'Z' to ensure proper UTC parsing
    const gameStart = new Date(game.game_time.endsWith('Z') ? game.game_time : game.game_time + 'Z');

    // Game is live if current time is past start time but not completed
    return now >= gameStart;
  })();

  const isUpcoming = !isCompleted && !isLive;

  const hasRecommendations = game.recommendations_count > 0;
  const highConfidenceCount = game.recommendations.filter(
    (r) => r.confidence === "high"
  ).length;
  const hasOdds = !!game.odds;

  const cardContent = (
    <div
      className={`p-5 rounded-xl border bg-white ${
        isUpcoming
          ? `transition-all hover:shadow-lg hover:-translate-y-0.5 ${
              hasRecommendations
                ? "border-emerald-200 shadow-sm"
                : "border-slate-200"
            } ${isUpcoming ? "cursor-pointer" : ""}`
          : "border-slate-200"
      }`}
    >
        {/* Matchup with logos */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            {/* Away team */}
            <div className="flex items-center gap-2">
              <Image
                src={getTeamLogo(game.away_team)}
                alt={game.away_team}
                width={40}
                height={40}
                className="object-contain"
              />
              <div>
                <div className="font-semibold text-slate-900">{game.away_team}</div>
                <div className="text-xs text-slate-500">({game.away_record})</div>
                {isCompleted && (
                  <div className="text-lg font-bold text-slate-900 mt-1">{game.away_score}</div>
                )}
              </div>
            </div>

            <div className="text-slate-300 font-light text-lg">@</div>

            {/* Home team */}
            <div className="flex items-center gap-2">
              <Image
                src={getTeamLogo(game.home_team)}
                alt={game.home_team}
                width={40}
                height={40}
                className="object-contain"
              />
              <div>
                <div className="font-semibold text-slate-900">{game.home_team}</div>
                <div className="text-xs text-slate-500">({game.home_record})</div>
                {isCompleted && (
                  <div className="text-lg font-bold text-slate-900 mt-1">{game.home_score}</div>
                )}
              </div>
            </div>
          </div>

          {/* Status badge or recommendation count */}
          <div className="flex flex-col items-end gap-1">
            {isCompleted && (
              <div className="px-3 py-1 rounded-full bg-slate-100 text-slate-600 text-sm font-medium">
                Final
              </div>
            )}
            {isLive && (
              <div className="px-3 py-1 rounded-full bg-red-100 text-red-600 text-sm font-medium animate-pulse">
                Live
              </div>
            )}
            {isUpcoming && hasRecommendations && (
              <div className="flex items-center gap-1.5 bg-emerald-50 px-2.5 py-1 rounded-full">
                {highConfidenceCount > 0 && (
                  <span className="text-emerald-500">●</span>
                )}
                <span className="text-sm font-medium text-emerald-700">
                  {game.recommendations_count}
                </span>
              </div>
            )}
            {/* Game time for upcoming games */}
            {isUpcoming && game.game_time && (
              <div className="text-xs text-slate-500">
                {new Date(game.game_time.endsWith('Z') ? game.game_time : game.game_time + 'Z').toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                  timeZone: "America/New_York",
                })}
                {" ET"}
              </div>
            )}
          </div>
        </div>

        {/* Betting Lines - Only for upcoming games */}
        {isUpcoming && hasOdds && (
          <div className="mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
            <div className="grid grid-cols-3 gap-3 text-center text-xs">
              {/* Spread */}
              {game.odds?.spread && (
                <div>
                  <div className="text-slate-500 font-medium mb-1">Spread</div>
                  <div className="font-semibold text-slate-900">
                    {game.home_team} {game.odds.spread.home_line > 0 ? '+' : ''}{game.odds.spread.home_line}
                  </div>
                  <div className="text-slate-400">{formatOdds(game.odds.spread.home_odds)}</div>
                </div>
              )}

              {/* Total */}
              {game.odds?.total && (
                <div>
                  <div className="text-slate-500 font-medium mb-1">Total</div>
                  <div className="font-semibold text-slate-900">
                    O/U {game.odds.total.line}
                  </div>
                  <div className="text-slate-400">
                    {formatOdds(game.odds.total.over_odds)} / {formatOdds(game.odds.total.under_odds)}
                  </div>
                </div>
              )}

              {/* Moneyline */}
              {game.odds?.moneyline && (
                <div>
                  <div className="text-slate-500 font-medium mb-1">Moneyline</div>
                  <div className="font-semibold text-slate-900">
                    {game.home_team}
                  </div>
                  <div className="text-slate-400">{formatOdds(game.odds.moneyline.home_odds)}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recommendations preview - Only for upcoming games */}
        {isUpcoming && hasRecommendations && (
          <div className="space-y-2">
            {game.recommendations.slice(0, 2).map((rec, idx) => (
              <div
                key={idx}
                className="flex items-start justify-between gap-2 p-3 bg-slate-50 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-700">{rec.insight}</div>
                </div>
                <ConfidenceBadge confidence={rec.confidence} />
              </div>
            ))}
            {game.recommendations_count > 2 && (
              <div className="text-xs text-slate-400 text-center pt-1">
                +{game.recommendations_count - 2} more insights
              </div>
            )}
          </div>
        )}

        {isUpcoming && !hasRecommendations && (
          <div className="text-sm text-slate-400 text-center py-3 bg-slate-50 rounded-lg">
            {hasOdds ? "No strong value bets found" : "Betting lines coming soon"}
          </div>
        )}
      </div>
    );

  // Only wrap in Link if the game is upcoming
  return isUpcoming ? (
    <Link href={`/game/${game.game_id}`}>{cardContent}</Link>
  ) : (
    cardContent
  );
}
