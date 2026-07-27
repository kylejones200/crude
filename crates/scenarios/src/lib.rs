//! Scenario input contract — single stable YAML format for all optimization.

mod blend_schedule;
mod error;
mod horizon;
mod inventory;
mod monte_carlo;
mod schema;

pub use blend_schedule::{
    AssayStreamSpec, BlendCandidateSpec, BlendComponentSpec, BlendScheduleScenario,
};
pub use error::{ScenarioError, ScenarioResult};
pub use horizon::{days_in_month, lead_time_for_source};
pub use inventory::InventoryScenario;
pub use monte_carlo::{
    estimate_gbm_params, simulate_gbm, MonteCarloConfig, MonteCarloResult, PriceSeries,
};
pub use schema::{
    AvailableCrude, BlendScenarioFile, CrudeAssayRef, Objective, ObjectiveType, ProductConstraint,
    ProductSpec, PropertyConstraint, Scenario,
};
