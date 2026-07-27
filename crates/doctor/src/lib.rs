//! Environment checks and LP benchmark harness.

mod benchmark;
mod checks;

pub use benchmark::{run_lp_benchmarks, LpBenchmarkResult};
pub use checks::{run_doctor, DoctorCheck, DoctorReport};
