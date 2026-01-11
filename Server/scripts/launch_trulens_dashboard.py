#!/usr/bin/env python3
"""
Launch TruLens Dashboard for RAG Evaluation Monitoring

This script launches the TruLens web dashboard where you can:
- View evaluation trends over time
- Analyze score distributions
- Identify hallucinations and quality issues
- Compare different queries and responses
- Export reports

Usage:
    python scripts/launch_trulens_dashboard.py [--port PORT]
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.evaluation.trulens_service import get_trulens_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def main(port: int = 8501):
    """Launch TruLens dashboard"""

    print("=" * 70)
    print("TruLens RAG Evaluation Dashboard")
    print("=" * 70)
    print()

    try:
        print("🔄 Initializing TruLens service...")
        service = await get_trulens_service()
        print("✅ TruLens service initialized")
        print()

        # Get current statistics
        stats = service.get_statistics()
        print("📊 Current Evaluation Statistics:")
        print(f"   Total Evaluations:    {stats.get('total_evaluations', 0)}")
        print(f"   Avg Context Rel:      {stats.get('avg_context_relevance', 0):.3f}")
        print(f"   Avg Groundedness:     {stats.get('avg_groundedness', 0):.3f}")
        print(f"   Avg Answer Rel:       {stats.get('avg_answer_relevance', 0):.3f}")
        print(f"   Hallucination Rate:   {stats.get('hallucination_rate', 0):.2%}")
        print()

        print("=" * 70)
        print("🚀 Launching TruLens Dashboard...")
        print("=" * 70)
        print()
        print(f"📊 Dashboard URL:    http://localhost:{port}")
        print(f"📂 Database:         {service.db_path}")
        print()
        print("Dashboard Features:")
        print("  • Real-time evaluation metrics")
        print("  • Score distributions and trends")
        print("  • Query-level drill-down")
        print("  • Hallucination detection alerts")
        print("  • Export and reporting")
        print()
        print("Press Ctrl+C to stop the dashboard")
        print("=" * 70)
        print()

        # Launch dashboard (blocking call)
        service.launch_dashboard(port=port)

    except KeyboardInterrupt:
        print("\n\n⚠️  Dashboard stopped by user")
        print("✅ Shutdown complete")
    except ImportError as e:
        print(f"\n❌ TruLens not installed: {e}")
        print("\n💡 Install TruLens with:")
        print("   pip install trulens-eval")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Failed to launch dashboard: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch TruLens Dashboard for RAG evaluation monitoring"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run the dashboard on (default: 8501)"
    )

    args = parser.parse_args()

    asyncio.run(main(port=args.port))
