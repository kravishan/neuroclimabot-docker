"""
Test TruLens integration with NeuroClimaBot RAG system
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.rag.chain import get_rag_service
from app.services.evaluation.rag_evaluator import get_rag_evaluator


async def test_basic_evaluation():
    """Test basic TruLens evaluation"""

    print("=" * 60)
    print("TruLens Integration Test")
    print("=" * 60)

    print("\n1️⃣  Initializing services...")
    try:
        rag_service = await get_rag_service()
        evaluator = await get_rag_evaluator(enabled=True)
        print("   ✅ Services initialized successfully\n")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return

    # Test queries
    test_queries = [
        "What are social tipping points in climate systems?",
        "How does climate change affect biodiversity?",
        "What are the main causes of global warming?"
    ]

    for idx, test_query in enumerate(test_queries, 1):
        print(f"\n{'=' * 60}")
        print(f"Test Query {idx}/{len(test_queries)}")
        print(f"{'=' * 60}")
        print(f"📝 Query: {test_query}\n")

        try:
            # Process query
            result = await rag_service.query(
                question=test_query,
                session_id=f"test-trulens-{idx:03d}",
                language="en",
                conversation_type="start"
            )

            # Display response
            content = result.get("content", "")
            print(f"💬 Response ({len(content)} chars):")
            print(f"   {content[:200]}...")
            print()

            # Check evaluation scores
            if "evaluation" in result:
                eval_data = result["evaluation"]

                print("📊 TruLens Evaluation Scores:")
                print(f"   • Context Relevance:  {eval_data['context_relevance']:.3f} {'✅' if eval_data['context_relevance'] >= 0.7 else '⚠️'}")
                print(f"   • Groundedness:       {eval_data['groundedness']:.3f} {'✅' if eval_data['groundedness'] >= 0.7 else '⚠️'}")
                print(f"   • Answer Relevance:   {eval_data['answer_relevance']:.3f} {'✅' if eval_data['answer_relevance'] >= 0.7 else '⚠️'}")
                print(f"   • Overall Score:      {eval_data['overall_score']:.3f} {'✅' if eval_data['overall_score'] >= 0.7 else '⚠️'}")

                # Per-source scores
                if eval_data.get('milvus_context_relevance'):
                    print(f"\n   Source-specific Scores:")
                    print(f"   • Milvus Quality:     {eval_data['milvus_context_relevance']:.3f}")
                if eval_data.get('graphrag_context_relevance'):
                    print(f"   • GraphRAG Quality:   {eval_data['graphrag_context_relevance']:.3f}")

                # Performance
                print(f"\n   ⏱️  Evaluation Time:   {eval_data['evaluation_time_ms']:.0f}ms")
                print(f"   🤖 Eval Model:        {eval_data.get('model_used', 'unknown')}")

                # Quality flags
                quality = result.get("quality_flags", {})
                print("\n🎯 Quality Analysis:")
                if quality.get("excellent_response"):
                    print("   ✅ Excellent response quality!")
                if quality.get("high_quality"):
                    print("   ✅ High quality response")
                if quality.get("potential_hallucination"):
                    print("   ⚠️  WARNING: Potential hallucination detected!")
                if quality.get("irrelevant_context"):
                    print("   ⚠️  WARNING: Irrelevant context retrieved")
                if quality.get("off_topic_answer"):
                    print("   ⚠️  WARNING: Answer may be off-topic")

                # Sources used
                sources_used = result.get("sources_used", {})
                if sources_used:
                    print(f"\n📚 Data Sources Used:")
                    for source, count in sources_used.items():
                        print(f"   • {source}: {count}")

            else:
                print("❌ No evaluation data found in response")

        except Exception as e:
            print(f"❌ Query processing failed: {e}")
            import traceback
            traceback.print_exc()

    # Display overall statistics
    print(f"\n{'=' * 60}")
    print("Overall Evaluation Statistics")
    print(f"{'=' * 60}\n")

    try:
        stats = evaluator.get_statistics()
        print(f"📈 Session Statistics:")
        print(f"   Total Evaluations:    {stats.get('total_evaluations', 0)}")
        print(f"   Avg Context Rel:      {stats.get('avg_context_relevance', 0):.3f}")
        print(f"   Avg Groundedness:     {stats.get('avg_groundedness', 0):.3f}")
        print(f"   Avg Answer Rel:       {stats.get('avg_answer_relevance', 0):.3f}")
        print(f"   Hallucination Rate:   {stats.get('hallucination_rate', 0):.2%}")
        print(f"   Hallucination Count:  {stats.get('low_groundedness_count', 0)}")
    except Exception as e:
        print(f"❌ Failed to get statistics: {e}")

    print(f"\n{'=' * 60}")
    print("✅ Test Complete!")
    print(f"{'=' * 60}\n")


async def test_direct_evaluation():
    """Test direct evaluation without RAG service"""

    print("\n" + "=" * 60)
    print("Direct Evaluation Test (Manual Input)")
    print("=" * 60 + "\n")

    try:
        from app.services.evaluation.trulens_service import get_trulens_service

        print("Initializing TruLens service...")
        trulens = await get_trulens_service()
        print("✅ TruLens initialized\n")

        # Test data
        query = "What are the effects of climate change on polar ice caps?"
        contexts = [
            "Climate change is causing polar ice caps to melt at an accelerating rate. "
            "Arctic sea ice has declined by about 13% per decade since 1979.",
            "The Greenland and Antarctic ice sheets are losing mass due to rising temperatures. "
            "This contributes to sea level rise globally.",
            "Polar bears are losing habitat as Arctic ice melts. "
            "This affects their ability to hunt seals, their primary food source."
        ]
        answer = (
            "Climate change is significantly impacting polar ice caps. "
            "The Arctic sea ice is declining rapidly, with a 13% reduction per decade since 1979. "
            "Both Greenland and Antarctic ice sheets are losing mass, contributing to sea level rise. "
            "This also affects wildlife like polar bears who depend on ice for hunting."
        )

        print("Test Input:")
        print(f"  Query: {query}")
        print(f"  Contexts: {len(contexts)} chunks")
        print(f"  Answer: {len(answer)} chars\n")

        print("Running evaluation...")
        scores = await trulens.evaluate_rag_response(
            query=query,
            retrieved_contexts=contexts,
            generated_answer=answer
        )

        print("\n📊 Evaluation Results:")
        print(f"  Context Relevance: {scores.context_relevance:.3f}")
        print(f"  Groundedness:      {scores.groundedness:.3f}")
        print(f"  Answer Relevance:  {scores.answer_relevance:.3f}")
        print(f"  Overall Score:     {scores.overall_score:.3f}")
        print(f"  Eval Time:         {scores.evaluation_time:.2f}s")
        print(f"  Model Used:        {scores.model_used}")

        # Interpretation
        print("\n🎯 Interpretation:")
        if scores.overall_score >= 0.8:
            print("  ✅ Excellent response quality!")
        elif scores.overall_score >= 0.7:
            print("  ✅ Good response quality")
        elif scores.overall_score >= 0.6:
            print("  ⚠️  Moderate quality - room for improvement")
        else:
            print("  ❌ Poor quality - needs attention")

        if scores.groundedness < 0.7:
            print("  ⚠️  WARNING: Potential hallucination (low groundedness)")

    except Exception as e:
        print(f"❌ Direct evaluation failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    print("\n🧪 Starting TruLens Integration Tests\n")

    # Test 1: Full RAG pipeline with evaluation
    await test_basic_evaluation()

    # Test 2: Direct evaluation
    await test_direct_evaluation()

    print("\n✅ All tests complete!\n")
    print("Next steps:")
    print("  1. Launch TruLens dashboard: python scripts/launch_trulens_dashboard.py")
    print("  2. Review evaluation trends in the dashboard")
    print("  3. Adjust RAG parameters based on scores\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
