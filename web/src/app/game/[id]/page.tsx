import Link from "next/link";
import Image from "next/image";
import { getGameDetail } from "@/lib/api";
import { getTeamLogo } from "@/lib/logos";
import RecommendationCard from "@/components/RecommendationCard";

export const dynamic = "force-dynamic";

interface PageProps {
  params: Promise<{ id: string }>;
}

function TeamSection({
  team,
  isHome,
}: {
  team: {
    id: number;
    name: string;
    abbreviation: string;
    last_result: "W" | "L" | null;
    rest_days: number | null;
    trends: {
      category: string;
      description: string;
      record: string;
      win_pct: number;
      sample_size: number;
      confidence: string;
    }[];
    recent_games: {
      date: string;
      opponent: string;
      home: boolean;
      result: "W" | "L";
      score: string;
    }[];
  };
  isHome: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Image
            src={getTeamLogo(team.abbreviation)}
            alt={team.abbreviation}
            width={48}
            height={48}
            className="object-contain"
          />
          <div>
            <h3 className="text-lg font-bold text-slate-900">{team.abbreviation}</h3>
            <p className="text-sm text-slate-500">{team.name}</p>
          </div>
        </div>
        <div className="text-right">
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              isHome
                ? "bg-blue-100 text-blue-700"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {isHome ? "HOME" : "AWAY"}
          </span>
          {team.last_result && (
            <div className="mt-2">
              <span
                className={`text-xs font-medium ${
                  team.last_result === "W" ? "text-emerald-600" : "text-red-500"
                }`}
              >
                Last game: {team.last_result}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Trends */}
      <div className="mb-4">
        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-3">
          Key Trends
        </h4>
        <div className="space-y-2">
          {team.trends.length > 0 ? (
            team.trends.slice(0, 5).map((trend, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg text-sm"
              >
                <span className="text-slate-700">{trend.description}</span>
                <span
                  className={`font-semibold ${
                    trend.win_pct >= 65
                      ? "text-emerald-600"
                      : trend.win_pct <= 40
                      ? "text-red-500"
                      : "text-slate-500"
                  }`}
                >
                  {trend.win_pct}%
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-400">No significant trends</p>
          )}
        </div>
      </div>

      {/* Recent games */}
      <div>
        <h4 className="text-xs font-semibold text-slate-400 uppercase mb-3">
          Last 5 Games
        </h4>
        <div className="flex gap-2">
          {team.recent_games.slice(0, 5).map((game, idx) => (
            <div
              key={idx}
              className={`flex-1 text-center p-2.5 rounded-lg text-xs ${
                game.result === "W"
                  ? "bg-emerald-50 border border-emerald-200"
                  : "bg-red-50 border border-red-200"
              }`}
              title={`${game.home ? "vs" : "@"} ${game.opponent}: ${game.score}`}
            >
              <div className={`font-bold ${game.result === "W" ? "text-emerald-700" : "text-red-600"}`}>
                {game.result}
              </div>
              <div className="text-slate-500 mt-0.5">{game.opponent}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default async function GamePage({ params }: PageProps) {
  const { id } = await params;
  let game;
  let error = null;

  try {
    game = await getGameDetail(parseInt(id));
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load game";
  }

  if (error || !game) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-500 mb-4">Error: {error || "Game not found"}</p>
          <Link href="/" className="text-blue-600 hover:underline">
            ← Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <Link
            href="/"
            className="text-sm text-slate-500 hover:text-slate-900 mb-4 inline-flex items-center gap-1"
          >
            ← Back to dashboard
          </Link>

          {/* Matchup */}
          <div className="flex items-center justify-center gap-8 mt-4">
            <div className="flex items-center gap-3 text-right">
              <div>
                <div className="text-2xl font-bold text-slate-900">
                  {game.away_team.abbreviation}
                </div>
                <div className="text-sm text-slate-500">{game.away_team.name}</div>
              </div>
              <Image
                src={getTeamLogo(game.away_team.abbreviation)}
                alt={game.away_team.abbreviation}
                width={56}
                height={56}
                className="object-contain"
              />
            </div>

            <div className="text-slate-300 text-2xl font-light">@</div>

            <div className="flex items-center gap-3">
              <Image
                src={getTeamLogo(game.home_team.abbreviation)}
                alt={game.home_team.abbreviation}
                width={56}
                height={56}
                className="object-contain"
              />
              <div>
                <div className="text-2xl font-bold text-slate-900">
                  {game.home_team.abbreviation}
                </div>
                <div className="text-sm text-slate-500">{game.home_team.name}</div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-6 mt-3 text-sm">
            <div className="text-slate-400">{game.date}</div>
            <div className="w-1 h-1 bg-slate-300 rounded-full"></div>
            <div className="text-slate-600">
              <span className="font-medium">{game.away_team.record}</span>
              <span className="text-slate-400 mx-1">vs</span>
              <span className="font-medium">{game.home_team.record}</span>
            </div>
            <div className="w-1 h-1 bg-slate-300 rounded-full"></div>
            <div className="text-slate-400">{game.season}</div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Betting Lines */}
        {game.odds && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Betting Lines</h2>
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="grid grid-cols-3 gap-6 text-center">
                {/* Spread */}
                {game.odds.spread && (
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase mb-3">Spread</div>
                    <div className="space-y-2">
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">{game.home_team.abbreviation}</div>
                        <div className="text-lg font-bold text-slate-900">
                          {game.odds.spread.home_line > 0 ? '+' : ''}{game.odds.spread.home_line}
                        </div>
                        <div className="text-sm text-slate-400">
                          {game.odds.spread.home_odds > 0 ? '+' : ''}{game.odds.spread.home_odds}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">{game.away_team.abbreviation}</div>
                        <div className="text-lg font-bold text-slate-900">
                          {game.odds.spread.away_line > 0 ? '+' : ''}{game.odds.spread.away_line}
                        </div>
                        <div className="text-sm text-slate-400">
                          {game.odds.spread.away_odds > 0 ? '+' : ''}{game.odds.spread.away_odds}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Total */}
                {game.odds.total && (
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase mb-3">Total</div>
                    <div className="space-y-2">
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">Over</div>
                        <div className="text-lg font-bold text-slate-900">{game.odds.total.line}</div>
                        <div className="text-sm text-slate-400">
                          {game.odds.total.over_odds > 0 ? '+' : ''}{game.odds.total.over_odds}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">Under</div>
                        <div className="text-lg font-bold text-slate-900">{game.odds.total.line}</div>
                        <div className="text-sm text-slate-400">
                          {game.odds.total.under_odds > 0 ? '+' : ''}{game.odds.total.under_odds}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Moneyline */}
                {game.odds.moneyline && (
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase mb-3">Moneyline</div>
                    <div className="space-y-2">
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">{game.home_team.abbreviation}</div>
                        <div className="text-lg font-bold text-slate-900">
                          {game.odds.moneyline.home_odds > 0 ? '+' : ''}{game.odds.moneyline.home_odds}
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg">
                        <div className="text-sm text-slate-600 mb-1">{game.away_team.abbreviation}</div>
                        <div className="text-lg font-bold text-slate-900">
                          {game.odds.moneyline.away_odds > 0 ? '+' : ''}{game.odds.moneyline.away_odds}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Recommendations */}
        {game.recommendations.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
              <h2 className="text-lg font-semibold text-slate-900">Betting Insights</h2>
            </div>
            <div className="space-y-4">
              {game.recommendations.map((rec, idx) => (
                <RecommendationCard key={idx} recommendation={rec} />
              ))}
            </div>
          </section>
        )}

        {/* Team Analysis */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Team Analysis</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <TeamSection team={game.insights.away_team} isHome={false} />
            <TeamSection team={game.insights.home_team} isHome={true} />
          </div>
        </section>

        {/* Head to Head */}
        <section className="mb-10">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Head to Head</h2>
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <Image
                  src={getTeamLogo(game.away_team.abbreviation)}
                  alt={game.away_team.abbreviation}
                  width={40}
                  height={40}
                  className="object-contain mx-auto mb-2"
                />
                <div className="text-2xl font-bold text-slate-900">
                  {game.insights.head_to_head.away_record}
                </div>
                <div className="text-sm text-slate-500">
                  {game.away_team.abbreviation}
                </div>
              </div>
              <div className="flex items-center justify-center">
                <span className="text-slate-300 text-lg">vs</span>
              </div>
              <div>
                <Image
                  src={getTeamLogo(game.home_team.abbreviation)}
                  alt={game.home_team.abbreviation}
                  width={40}
                  height={40}
                  className="object-contain mx-auto mb-2"
                />
                <div className="text-2xl font-bold text-slate-900">
                  {game.insights.head_to_head.home_record}
                </div>
                <div className="text-sm text-slate-500">
                  {game.home_team.abbreviation}
                </div>
              </div>
            </div>
            <p className="text-xs text-slate-400 text-center mt-4">
              Last 3 seasons
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
