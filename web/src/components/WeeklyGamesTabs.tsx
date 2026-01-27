"use client";

import { useState } from "react";
import Image from "next/image";
import GameCard from "@/components/GameCard";
import type { WeeklyGames } from "@/lib/api";
import { getTeamLogo } from "@/lib/logos";

interface WeeklyGamesTabsProps {
  data: WeeklyGames;
}

function formatDate(dateStr: string): string {
  // Parse date string as local date (YYYY-MM-DD format)
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, day);

  const today = new Date();
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  const tomorrow = new Date(todayOnly);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (date.getTime() === todayOnly.getTime()) {
    return "Today";
  } else if (date.getTime() === tomorrow.getTime()) {
    return "Tomorrow";
  }

  return date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function formatTabDate(dateStr: string): { short: string; full: string } {
  // Parse date string as local date (YYYY-MM-DD format)
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, day);

  const today = new Date();
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());

  const tomorrow = new Date(todayOnly);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (date.getTime() === todayOnly.getTime()) {
    return { short: "Today", full: "Today" };
  } else if (date.getTime() === tomorrow.getTime()) {
    return { short: "Tomorrow", full: "Tomorrow" };
  }

  const weekday = date.toLocaleDateString("en-US", { weekday: "short" });
  const monthDay = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  return {
    short: `${weekday} ${date.getDate()}`,
    full: `${weekday}, ${monthDay}`,
  };
}

export default function WeeklyGamesTabs({ data }: WeeklyGamesTabsProps) {
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  if (!data.days || data.days.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-slate-400 text-lg">No games scheduled this week</p>
      </div>
    );
  }

  const selectedDay = data.days[selectedDayIndex];

  // Calculate how many days out this date is
  const getDaysOut = (dateStr: string): number => {
    const [year, month, day] = dateStr.split("-").map(Number);
    const date = new Date(year, month - 1, day);
    const today = new Date();
    const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    const diffTime = date.getTime() - todayOnly.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const daysOut = getDaysOut(selectedDay.date);
  const isToday = daysOut === 0;
  const isTomorrow = daysOut === 1;
  const isFuture = daysOut >= 2;

  // Categorize games based on current time and game_time
  const now = new Date();

  const categorizedGames = selectedDay.games.map((game) => {
    const isCompleted = game.is_completed;
    let isLive = false;

    if (!isCompleted && game.game_time) {
      const gameStart = new Date(game.game_time.endsWith('Z') ? game.game_time : game.game_time + 'Z');
      isLive = now >= gameStart;
    }

    return { ...game, isLive };
  });

  const upcomingGames = categorizedGames.filter((g) => !g.is_completed && !g.isLive);
  const liveGames = categorizedGames.filter((g) => !g.is_completed && g.isLive);
  const completedGames = categorizedGames.filter((g) => g.is_completed);

  // Sort upcoming games (with recommendations first)
  const upcomingWithRecs = upcomingGames.filter((g) => g.recommendations_count > 0);
  const upcomingWithoutRecs = upcomingGames.filter((g) => g.recommendations_count === 0);

  return (
    <div>
      {/* Week header */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-slate-900">
          This Week&apos;s Games
        </h2>
        <p className="text-slate-500 text-sm mt-1">
          {data.total_games} games total
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-8">
        <div className="border-b border-slate-200">
          <div className="flex gap-1 overflow-x-auto">
            {data.days.map((day, index) => {
              const tabDate = formatTabDate(day.date);
              const isSelected = selectedDayIndex === index;
              const hasInsights = day.games.some((g) => g.recommendations_count > 0);

              return (
                <button
                  key={day.date}
                  onClick={() => setSelectedDayIndex(index)}
                  className={`
                    relative px-4 py-3 text-sm font-medium whitespace-nowrap
                    transition-colors duration-200
                    ${
                      isSelected
                        ? "text-slate-900 border-b-2 border-slate-900"
                        : "text-slate-500 hover:text-slate-700 border-b-2 border-transparent"
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <span>{tabDate.full}</span>
                    {hasInsights && (
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {day.games_count} {day.games_count === 1 ? "game" : "games"}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected day content */}
      <div>
        {/* Day header */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-slate-900">
            {formatDate(selectedDay.date)}
            <span className="text-slate-400 font-normal ml-2 text-sm">
              {selectedDay.date}
            </span>
          </h3>
          <p className="text-slate-500 text-sm mt-1">
            {selectedDay.games_count} games
            {isToday && liveGames.length > 0 && (
              <span className="text-red-600 font-medium"> · {liveGames.length} live</span>
            )}
            {(isToday || isTomorrow) && upcomingWithRecs.length > 0 && ` · ${upcomingWithRecs.length} with insights`}
          </p>
        </div>

        {/* Future days (2+ days out) - Simple schedule view */}
        {isFuture && (
          <div className="bg-slate-50 rounded-lg p-6 mb-6 border border-slate-200">
            <div className="flex items-start gap-3 mb-4">
              <svg
                className="w-5 h-5 text-slate-400 mt-0.5 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div>
                <h4 className="text-sm font-medium text-slate-900 mb-1">
                  Betting Lines Coming Soon
                </h4>
                <p className="text-sm text-slate-600">
                  Odds and recommendations will be available 1 day before game time.
                  Check back tomorrow for the latest betting insights.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Today & Tomorrow: Show full game cards with odds */}
        {(isToday || isTomorrow) && (
          <>
            {/* Upcoming games with recommendations */}
            {upcomingWithRecs.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                  <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Recommended Games
                  </h4>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {upcomingWithRecs.map((game) => (
                    <GameCard key={game.game_id} game={game} />
                  ))}
                </div>
              </div>
            )}

            {/* Upcoming games without recommendations */}
            {upcomingWithoutRecs.length > 0 && (
              <div className="mb-6">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                  Other Upcoming Games
                </h4>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {upcomingWithoutRecs.map((game) => (
                    <GameCard key={game.game_id} game={game} />
                  ))}
                </div>
              </div>
            )}

            {/* Live games */}
            {liveGames.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                  <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                    Live Games
                  </h4>
                </div>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {liveGames.map((game) => (
                    <GameCard key={game.game_id} game={game} />
                  ))}
                </div>
              </div>
            )}

            {/* Completed games */}
            {completedGames.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
                  Completed
                </h4>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {completedGames.map((game) => (
                    <GameCard key={game.game_id} game={game} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Future days: Simple schedule list */}
        {isFuture && (
          <div className="space-y-2">
            {selectedDay.games.map((game) => (
              <div
                key={game.game_id}
                className="bg-white border border-slate-200 rounded-lg p-4 hover:border-slate-300 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    {/* Away team with logo */}
                    <div className="flex items-center gap-2">
                      <Image
                        src={getTeamLogo(game.away_team)}
                        alt={game.away_team}
                        width={32}
                        height={32}
                        className="object-contain"
                      />
                      <div className="text-right">
                        <div className="text-sm font-medium text-slate-900">
                          {game.away_team}
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {game.away_team_name}
                        </div>
                      </div>
                    </div>

                    <div className="text-slate-400 text-sm">@</div>

                    {/* Home team with logo */}
                    <div className="flex items-center gap-2">
                      <Image
                        src={getTeamLogo(game.home_team)}
                        alt={game.home_team}
                        width={32}
                        height={32}
                        className="object-contain"
                      />
                      <div>
                        <div className="text-sm font-medium text-slate-900">
                          {game.home_team}
                        </div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {game.home_team_name}
                        </div>
                      </div>
                    </div>
                  </div>
                  {game.game_time && (
                    <div className="text-sm text-slate-500">
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
            ))}
          </div>
        )}

        {selectedDay.games.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-400">No games scheduled for this day</p>
          </div>
        )}
      </div>
    </div>
  );
}
