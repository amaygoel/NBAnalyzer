import { getWeeklyGames } from "@/lib/api";
import WeeklyGamesTabs from "@/components/WeeklyGamesTabs";

export const dynamic = "force-dynamic";

export default async function Home() {
  let data;
  let error = null;

  try {
    data = await getWeeklyGames(7);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load games";
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">
                <span style={{ color: '#1D428A' }}>NB</span>
                <span style={{ color: '#C8102E' }}>A</span>
                <span className="text-slate-900">nalyzer</span>
              </h1>
              <p className="text-slate-500 text-sm mt-1">
                Betting insights based on historical patterns
              </p>
            </div>
            <p className="text-slate-500 text-sm mt-1">
              by Amay Goel
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-600 font-medium">Error: {error}</p>
            <p className="text-sm text-red-400 mt-2">
              Make sure the API server is running at http://localhost:8000
            </p>
          </div>
        ) : data ? (
          <WeeklyGamesTabs data={data} />
        ) : null}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white mt-12">
        <div className="max-w-6xl mx-auto px-4 py-6 text-center text-sm text-slate-400">
          NBAnalyzer · Not financial advice · Data from nba_api
        </div>
      </footer>
    </div>
  );
}
