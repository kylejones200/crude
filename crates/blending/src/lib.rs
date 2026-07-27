//! Volume-weighted blend property calculation.

use crude_domain::{BlendRecipe, Crude, DomainError, DomainResult, PropertyId, PropertyValue};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendProperties {
    pub properties: Vec<PropertyValue>,
    pub total_volume_bbl: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct BlendEvaluation {
    pub properties: BlendProperties,
    pub feed_cost_per_bbl: Option<f64>,
    pub component_volumes_bbl: HashMap<String, f64>,
}

/// Evaluate a blend recipe against a crude library.
///
/// Properties are volume-weighted linear blends (API gravity, sulfur, TAN, SBN).
pub fn evaluate_blend(
    recipe: &BlendRecipe,
    crudes: &HashMap<crude_domain::CrudeId, Crude>,
    prices_usd_per_bbl: Option<&HashMap<crude_domain::CrudeId, f64>>,
    total_volume_bbl: Option<f64>,
) -> DomainResult<BlendEvaluation> {
    recipe.validate()?;

    let mut weighted: HashMap<PropertyId, f64> = HashMap::new();
    let mut component_volumes = HashMap::new();
    let mut feed_cost = 0.0;
    let mut has_prices = false;

    for component in &recipe.components {
        let crude = crudes
            .get(&component.crude_id)
            .ok_or_else(|| DomainError::UnknownCrude(component.crude_id.to_string()))?;

        let vol = total_volume_bbl.map(|t| t * component.fraction);
        if let Some(v) = vol {
            component_volumes.insert(component.crude_id.to_string(), v);
        }

        if let Some(prices) = prices_usd_per_bbl {
            if let Some(price) = prices.get(&component.crude_id) {
                feed_cost += component.fraction * price;
                has_prices = true;
            }
        }

        for measurement in &crude.assay.bulk_properties {
            *weighted.entry(measurement.property).or_insert(0.0) +=
                component.fraction * measurement.value;
        }
    }

    let properties: Vec<PropertyValue> = weighted
        .into_iter()
        .map(|(property, value)| PropertyValue { property, value })
        .collect();

    Ok(BlendEvaluation {
        properties: BlendProperties {
            properties,
            total_volume_bbl,
        },
        feed_cost_per_bbl: if has_prices { Some(feed_cost) } else { None },
        component_volumes_bbl: component_volumes,
    })
}

pub fn get_blend_property(evaluation: &BlendEvaluation, property: PropertyId) -> Option<f64> {
    evaluation
        .properties
        .properties
        .iter()
        .find(|p| p.property == property)
        .map(|p| p.value)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crude_domain::{BlendComponent, CrudeId, PropertyMeasurement};

    fn wti() -> Crude {
        Crude {
            id: CrudeId::new("wti"),
            name: "WTI".into(),
            origin: None,
            assay: crude_domain::Assay {
                bulk_properties: vec![
                    PropertyMeasurement::new(PropertyId::ApiGravity, 39.6),
                    PropertyMeasurement::new(PropertyId::SulfurWtPct, 0.24),
                ],
                cuts: vec![],
            },
        }
    }

    fn maya() -> Crude {
        Crude {
            id: CrudeId::new("maya"),
            name: "Maya".into(),
            origin: None,
            assay: crude_domain::Assay {
                bulk_properties: vec![
                    PropertyMeasurement::new(PropertyId::ApiGravity, 21.3),
                    PropertyMeasurement::new(PropertyId::SulfurWtPct, 3.4),
                ],
                cuts: vec![],
            },
        }
    }

    #[test]
    fn volume_weighted_api_and_sulfur() {
        let mut crudes = HashMap::new();
        crudes.insert(CrudeId::new("wti"), wti());
        crudes.insert(CrudeId::new("maya"), maya());

        let recipe = BlendRecipe {
            components: vec![
                BlendComponent {
                    crude_id: CrudeId::new("wti"),
                    fraction: 0.7,
                },
                BlendComponent {
                    crude_id: CrudeId::new("maya"),
                    fraction: 0.3,
                },
            ],
        };

        let eval = evaluate_blend(&recipe, &crudes, None, Some(100_000.0)).unwrap();
        let api = get_blend_property(&eval, PropertyId::ApiGravity).unwrap();
        let sulfur = get_blend_property(&eval, PropertyId::SulfurWtPct).unwrap();

        assert!((api - (0.7 * 39.6 + 0.3 * 21.3)).abs() < 1e-9);
        assert!((sulfur - (0.7 * 0.24 + 0.3 * 3.4)).abs() < 1e-9);
    }
}
