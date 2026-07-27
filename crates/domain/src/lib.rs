//! Canonical domain model for crude oil blending and optimization.
//!
//! Every module in the workspace consumes these types. No project-specific equivalents.

mod error;
mod ids;
mod inventory;
mod model;
mod property;
mod units;

pub use error::{DomainError, DomainResult};
pub use ids::CrudeId;
pub use inventory::{
    GradeSlate, LeadTimes, MonthlyPrices, SiteLimits, GRADES, SOURCES,
    UNMET_DEMAND_PENALTY_USD_PER_BBL,
};
pub use model::{Assay, AssayCut, BlendComponent, BlendRecipe, Crude};
pub use property::{PropertyId, PropertyMeasurement, PropertyValue};
pub use units::Unit;
