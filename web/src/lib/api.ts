const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Recommendation {
  bet_type: string;
  subject: string;
  insight: string;
  confidence: "high" | "medium" | "low" | "none";
  supporting_stats: { label: string; value: string }[];
}

export interface GameOdds {
  spread?: {
    home_line: number;
    home_odds: number;
    away_line: number;
    away_odds: number;
  };
  total?: {
    line: number;
    over_odds: number;
    under_odds: number;
  };
  moneyline?: {
    home_odds: number;
    away_odds: number;
  };
}

export interface GameSummary {
  game_id: number;
  home_team: string;
  away_team: string;
  home_team_name: string;
  away_team_name: string;
  home_record: string;
  away_record: string;
  is_completed: boolean;
  home_score: number | null;
  away_score: number | null;
  game_time: string | null;  // ISO datetime string
  recommendations_count: number;
  recommendations: Recommendation[];
  odds?: GameOdds;
}

export interface TodaysGames {
  date: string;
  games_count: number;
  games: GameSummary[];
}

export interface TeamTrend {
  category: string;
  description: string;
  record: string;
  win_pct: number;
  sample_size: number;
  confidence: string;
}

export interface RecentGame {
  date: string;
  opponent: string;
  home: boolean;
  result: "W" | "L";
  score: string;
}

export interface TeamInsights {
  id: number;
  name: string;
  abbreviation: string;
  last_result: "W" | "L" | null;
  rest_days: number | null;
  trends: TeamTrend[];
  recent_games: RecentGame[];
}

export interface GameDetail {
  game_id: number;
  date: string;
  season: string;
  home_team: {
    id: number;
    abbreviation: string;
    name: string;
    score: number | null;
    record: string;
  };
  away_team: {
    id: number;
    abbreviation: string;
    name: string;
    score: number | null;
    record: string;
  };
  is_completed: boolean;
  odds?: GameOdds;
  insights: {
    home_team: TeamInsights;
    away_team: TeamInsights;
    head_to_head: {
      home_record: string;
      away_record: string;
    };
  };
  recommendations: Recommendation[];
}

export interface Team {
  id: number;
  name: string;
  abbreviation: string;
  city: string;
  conference: string;
  division: string;
}

async function fetchAPI<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export interface WeeklyGames {
  start_date: string;
  end_date: string;
  total_games: number;
  days: {
    date: string;
    games_count: number;
    games: GameSummary[];
  }[];
}

export async function getTodaysGames(): Promise<TodaysGames> {
  return fetchAPI<TodaysGames>("/api/games/today");
}

export async function getWeeklyGames(days: number = 7): Promise<WeeklyGames> {
  return fetchAPI<WeeklyGames>(`/api/games/week?days=${days}`);
}

export async function getGamesByDate(date: string): Promise<{ date: string; games: GameSummary[] }> {
  return fetchAPI(`/api/games/date/${date}`);
}

export async function getGameDetail(gameId: number): Promise<GameDetail> {
  return fetchAPI<GameDetail>(`/api/games/${gameId}`);
}

export async function getTeams(): Promise<{ count: number; teams: Team[] }> {
  return fetchAPI("/api/teams/");
}

export async function getTeamTrends(abbrev: string): Promise<{
  team: string;
  team_name: string;
  trends: TeamTrend[];
}> {
  return fetchAPI(`/api/teams/${abbrev}/trends`);
}
