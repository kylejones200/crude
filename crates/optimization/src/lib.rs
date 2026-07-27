//! Linear programming optimization for crude blending scenarios.

mod blend_schedule;
mod diagnostics;
mod error;
mod inventory;
mod shadow;
mod solver;

pub use blend_schedule::{
    optimize_blend_schedule, AssayInventoryRow, AssayPurchaseRow, BlendScheduleOutput,
};
pub use diagnostics::{
    diagnose_blend_schedule, diagnose_inventory, preflight_blend_schedule, preflight_inventory,
    InfeasibilityHint,
};
pub use error::{OptimizationError, OptimizationResult};
pub use inventory::{optimize_inventory, InventoryOptimizationOutput, InventoryRow, PurchaseRow};
pub use shadow::ShadowPrice;
pub use solver::{optimize_scenario, OptimizationOutput, SolverStatus, VolumeAllocation};
