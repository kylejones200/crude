//! LP benchmark integration test (run with `cargo test --test benchmarks -- --ignored`).

use crude_doctor::run_lp_benchmarks;
use std::path::PathBuf;

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../fixtures")
}

#[test]
#[ignore = "benchmark; run with --ignored"]
fn lp_fixture_benchmark_report() {
    let results = run_lp_benchmarks(Some(fixture_root()));
    assert_eq!(results.len(), 4);
    for row in &results {
        assert!(row.elapsed_ms >= 0.0);
        assert!(row.status.contains("Optimal"), "{}", row.scenario);
        eprintln!(
            "{}: {:.1} ms, objective ${:.0}",
            row.scenario, row.elapsed_ms, row.objective_value_usd
        );
    }
}
