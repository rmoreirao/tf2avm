import asyncio
import argparse
from framework.e2e_test_runner import E2ETestRunner

async def main():
    parser = argparse.ArgumentParser(description='Run E2E tests for agents')
    parser.add_argument('--agent', type=str, help='Specific agent to test')
    parser.add_argument('--output', type=str, default='test_results.json', help='Output file for results')
    args = parser.parse_args()
    
    # Initialize and run tests
    runner = E2ETestRunner()
    await runner.initialize()
    
    # Run tests
    summary = await runner.run_all_tests(agent_name=args.agent)
    
    # Save results
    runner.save_results(args.output)
    
    # Exit with appropriate code
    exit(0 if summary['failed'] == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())