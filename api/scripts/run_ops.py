"""
Production operations orchestrator.

Calls existing update scripts to keep the database current.
Designed to run via cron without refactoring existing services.
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

SCRIPT_DIR = Path(__file__).parent
API_DIR = SCRIPT_DIR.parent
VENV_PYTHON = API_DIR / "venv" / "bin" / "python"


def log(message: str, level: str = "INFO"):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def run_script(script_name: str, description: str, args: list = None) -> bool:
    """
    Run a script as a subprocess.

    Args:
        script_name: Name of the script file (e.g., "fetch_odds.py")
        description: Human-readable description for logging
        args: Optional list of additional arguments

    Returns:
        True if successful, False otherwise
    """
    script_path = SCRIPT_DIR / script_name
    cmd = [str(VENV_PYTHON), str(script_path)]

    if args:
        cmd.extend(args)

    log(f"Running: {description}")
    log(f"Command: {' '.join(cmd)}", level="DEBUG")

    try:
        result = subprocess.run(
            cmd,
            cwd=str(API_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Print script output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode == 0:
            log(f"✅ SUCCESS: {description}", level="INFO")
            return True
        else:
            log(f"❌ FAILED: {description} (exit code {result.returncode})", level="ERROR")
            return False

    except subprocess.TimeoutExpired:
        log(f"❌ TIMEOUT: {description} (exceeded 5 minutes)", level="ERROR")
        return False
    except Exception as e:
        log(f"❌ ERROR: {description} - {e}", level="ERROR")
        return False


def run_daily(days: int = None):
    """
    Daily operations: fetch upcoming games + odds.

    Args:
        days: Number of days to fetch (passed to upcoming games script if supported)
    """
    log("=" * 70)
    log("DAILY OPERATIONS MODE")
    log("=" * 70)

    success = True

    # Fetch upcoming games
    args = []
    if days:
        args = ["--days", str(days)]
    if not run_script("fetch_upcoming_games.py", "Fetch upcoming games", args):
        success = False

    # Fetch odds
    if not run_script("fetch_odds.py", "Fetch betting odds"):
        success = False

    log("=" * 70)
    if success:
        log("✅ DAILY OPERATIONS COMPLETE", level="INFO")
    else:
        log("❌ DAILY OPERATIONS HAD FAILURES", level="ERROR")
    log("=" * 70)

    return success


def run_odds():
    """Fetch odds only (for frequent updates)."""
    log("=" * 70)
    log("ODDS REFRESH MODE")
    log("=" * 70)

    success = run_script("fetch_odds.py", "Fetch betting odds")

    log("=" * 70)
    if success:
        log("✅ ODDS REFRESH COMPLETE", level="INFO")
    else:
        log("❌ ODDS REFRESH FAILED", level="ERROR")
    log("=" * 70)

    return success


def run_scores():
    """Update scores for today's games."""
    log("=" * 70)
    log("SCORES UPDATE MODE")
    log("=" * 70)

    success = run_script("fetch_todays_games.py", "Update today's game scores")

    log("=" * 70)
    if success:
        log("✅ SCORES UPDATE COMPLETE", level="INFO")
    else:
        log("❌ SCORES UPDATE FAILED", level="ERROR")
    log("=" * 70)

    return success


def run_all(days: int = None):
    """Run all update operations."""
    log("=" * 70)
    log("FULL UPDATE MODE (ALL OPERATIONS)")
    log("=" * 70)

    success = True

    # Fetch upcoming games
    args = []
    if days:
        args = ["--days", str(days)]
    if not run_script("fetch_upcoming_games.py", "Fetch upcoming games", args):
        success = False

    # Fetch odds
    if not run_script("fetch_odds.py", "Fetch betting odds"):
        success = False

    # Update scores
    if not run_script("fetch_todays_games.py", "Update today's game scores"):
        success = False

    log("=" * 70)
    if success:
        log("✅ ALL OPERATIONS COMPLETE", level="INFO")
    else:
        log("❌ SOME OPERATIONS FAILED", level="ERROR")
    log("=" * 70)

    return success


def main():
    parser = argparse.ArgumentParser(
        description="NBA Analyzer production operations orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode daily          # Morning: fetch upcoming + odds
  %(prog)s --mode odds           # Frequent: refresh odds only
  %(prog)s --mode scores         # Evening: update scores
  %(prog)s --mode all            # Full update: upcoming + odds + scores
  %(prog)s --mode daily --days 7 # Fetch 7 days instead of default
        """
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=["daily", "odds", "scores", "all"],
        help="Operation mode to run"
    )

    parser.add_argument(
        "--days",
        type=int,
        help="Number of days to fetch (for daily/all modes, if supported by scripts)"
    )

    args = parser.parse_args()

    # Run the requested operation
    if args.mode == "daily":
        success = run_daily(args.days)
    elif args.mode == "odds":
        success = run_odds()
    elif args.mode == "scores":
        success = run_scores()
    elif args.mode == "all":
        success = run_all(args.days)
    else:
        log(f"Unknown mode: {args.mode}", level="ERROR")
        success = False

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
