mod request;

use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    routing::{get, post},
    Json, Router,
};
use crude_assay::{import_assay_report, import_assay_report_bytes};
use crude_blending::{evaluate_blend, get_blend_property};
use crude_constraints::{
    evaluate_compatibility, evaluate_product_constraints, ProductConstraints, PropertyBound,
    DEFAULT_COMPATIBILITY_K,
};
use crude_doctor::{run_doctor, run_lp_benchmarks};
use crude_domain::PropertyId;
use crude_economics::{fetch_history_cached, fetch_live_cached, PriceCacheConfig};
use crude_optimization::{optimize_blend_schedule, optimize_inventory, optimize_scenario};
use crude_scenarios::{
    simulate_gbm, BlendScenarioFile, BlendScheduleScenario, InventoryScenario, MonteCarloConfig,
    PriceSeries, Scenario,
};
use crude_storage::{
    compare_runs, get_run, list_runs, save_blend_schedule_run, save_inventory_run, save_run,
};
use request::{path_buf, require_path_or_yaml};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tower_http::cors::CorsLayer;

#[derive(Clone)]
struct AppState {
    runs_dir: PathBuf,
}

#[derive(Deserialize)]
struct AssayImportRequest {
    #[serde(default)]
    path: Option<String>,
    #[serde(default)]
    format: Option<String>,
    #[serde(default)]
    content_base64: Option<String>,
}

#[derive(Deserialize)]
struct BlendEvaluateRequest {
    #[serde(default)]
    path: Option<String>,
    #[serde(default)]
    yaml: Option<String>,
}

#[derive(Deserialize)]
struct ScenarioRequest {
    #[serde(default)]
    path: Option<String>,
    #[serde(default)]
    yaml: Option<String>,
    #[serde(default)]
    save: bool,
}

#[derive(Deserialize)]
struct CompatibilityRequest {
    sbn_values: Vec<f64>,
    in_values: Vec<f64>,
    fractions: Vec<f64>,
    #[serde(default)]
    k: Option<f64>,
}

#[derive(Deserialize)]
struct SimulateRequest {
    closes: Vec<f64>,
    #[serde(default = "default_iterations")]
    iterations: usize,
    #[serde(default = "default_days")]
    forecast_days: usize,
    seed: Option<u64>,
}

fn default_iterations() -> usize {
    1000
}
fn default_days() -> usize {
    63
}

#[derive(Deserialize)]
struct PricesQuery {
    /// Yahoo chart range for daily history (`1y`, `2y`, `5y`). Omit for spot only.
    history: Option<String>,
    #[serde(default)]
    no_cache: bool,
}

#[derive(Deserialize)]
struct DoctorQuery {
    #[serde(default)]
    online: bool,
}

#[derive(Deserialize)]
struct CompareRequest {
    paths: Vec<String>,
}

#[tokio::main]
async fn main() {
    let runs_dir = PathBuf::from(std::env::var("CRUDE_RUNS_DIR").unwrap_or_else(|_| "runs".into()));
    let state = Arc::new(AppState { runs_dir });

    let app = Router::new()
        .route("/health", get(health))
        .route("/assay/import", post(assay_import))
        .route("/blend/evaluate", post(blend_evaluate))
        .route("/blend/schedule/optimize", post(blend_schedule_optimize))
        .route("/optimize", post(optimize_blend))
        .route("/inventory/optimize", post(optimize_inventory_route))
        .route("/compatibility/evaluate", post(compatibility_evaluate))
        .route("/prices/fetch", get(prices_fetch))
        .route("/runs", get(list_runs_route))
        .route("/runs/{run_id}", get(get_run_route))
        .route("/doctor", get(doctor_route))
        .route("/benchmark/lp", get(benchmark_lp_route))
        .route("/compare", post(compare_runs_route))
        .route("/simulate", post(simulate_prices))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = SocketAddr::from(([127, 0, 0, 1], 8080));
    println!("crude-api listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health() -> &'static str {
    "ok"
}

async fn assay_import(
    Json(req): Json<AssayImportRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let report = if let Some(path) = req.path {
        import_assay_report(path_buf(&path).as_path()).map_err(err)?
    } else {
        let format = req
            .format
            .ok_or_else(|| err("format required when path is omitted"))?;
        let b64 = req
            .content_base64
            .ok_or_else(|| err("content_base64 required when path is omitted"))?;
        let bytes = base64_decode(&b64).map_err(err)?;
        import_assay_report_bytes(&bytes, &format).map_err(err)?
    };
    Ok(Json(serde_json::to_value(report).unwrap()))
}

async fn blend_evaluate(
    Json(req): Json<BlendEvaluateRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let file = load_blend_scenario(&req.path, &req.yaml).map_err(err)?;
    let recipe = file.to_blend_recipe();
    let crudes = file.build_crude_library();
    let prices = file.price_map();
    let eval = evaluate_blend(
        &recipe,
        &crudes,
        if prices.is_empty() {
            None
        } else {
            Some(&prices)
        },
        file.total_volume_bbl,
    )
    .map_err(err)?;

    let mut body = serde_json::json!({
        "api_gravity": get_blend_property(&eval, PropertyId::ApiGravity),
        "sulfur_wt_pct": get_blend_property(&eval, PropertyId::SulfurWtPct),
        "feed_cost_per_bbl": eval.feed_cost_per_bbl,
    });

    if let Some(c) = file.constraints {
        let report = evaluate_product_constraints(
            &eval,
            &ProductConstraints {
                api_gravity: c.api_gravity.map(|b| PropertyBound {
                    min: b.min,
                    max: b.max,
                }),
                sulfur_wt_pct: c.sulfur_wt_pct.map(|b| PropertyBound {
                    min: b.min,
                    max: b.max,
                }),
                total_acid_number: c.total_acid_number.map(|b| PropertyBound {
                    min: b.min,
                    max: b.max,
                }),
            },
        );
        body["constraints_satisfied"] = serde_json::json!(report.satisfied);
    }

    Ok(Json(body))
}

async fn optimize_blend(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ScenarioRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let scenario = load_static_scenario(&req.path, &req.yaml).map_err(err)?;
    let result = optimize_scenario(&scenario).map_err(err)?;
    if req.save {
        let path = state.runs_dir.join(format!("{}.json", scenario.name));
        let _ = save_run(&path, &result);
    }
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn optimize_inventory_route(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ScenarioRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let scenario = load_inventory_scenario(&req.path, &req.yaml).map_err(err)?;
    let result = optimize_inventory(&scenario).map_err(err)?;
    if req.save {
        let path = state
            .runs_dir
            .join(format!("{}-inventory.json", scenario.name));
        let _ = save_inventory_run(&path, &result);
    }
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn blend_schedule_optimize(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ScenarioRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let scenario = load_blend_schedule_scenario(&req.path, &req.yaml).map_err(err)?;
    let result = optimize_blend_schedule(&scenario).map_err(err)?;
    if req.save {
        let path = state
            .runs_dir
            .join(format!("{}-blend-schedule.json", scenario.name));
        let _ = save_blend_schedule_run(&path, &result);
    }
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn compatibility_evaluate(
    Json(req): Json<CompatibilityRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let k = req.k.unwrap_or(DEFAULT_COMPATIBILITY_K);
    let result = evaluate_compatibility(&req.sbn_values, &req.in_values, &req.fractions, k);
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn prices_fetch(
    Query(query): Query<PricesQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let cache = PriceCacheConfig::from_env();
    let force = query.no_cache;
    if let Some(range) = query.history {
        let history = fetch_history_cached(&cache, &range, force).map_err(err)?;
        Ok(Json(serde_json::json!({
            "range": range,
            "cached": !force,
            "history": history,
        })))
    } else {
        let live = fetch_live_cached(&cache, force).map_err(err)?;
        Ok(Json(serde_json::json!({
            "cached": !force,
            "live": live,
        })))
    }
}

async fn list_runs_route(
    State(state): State<Arc<AppState>>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let runs = list_runs(&state.runs_dir).map_err(storage_err)?;
    Ok(Json(serde_json::to_value(runs).unwrap()))
}

async fn get_run_route(
    State(state): State<Arc<AppState>>,
    Path(run_id): Path<String>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    match get_run(&state.runs_dir, &run_id) {
        Ok(record) => Ok(Json(serde_json::to_value(record).unwrap())),
        Err(e) => Err(storage_err(e)),
    }
}

async fn simulate_prices(
    Json(req): Json<SimulateRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let config = MonteCarloConfig {
        iterations: req.iterations,
        forecast_days: req.forecast_days,
        seed: req.seed,
    };
    let result = simulate_gbm(&PriceSeries { closes: req.closes }, &config).map_err(err)?;
    Ok(Json(serde_json::to_value(result).unwrap()))
}

async fn doctor_route(
    Query(query): Query<DoctorQuery>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let report = run_doctor(None, query.online);
    Ok(Json(serde_json::to_value(report).unwrap()))
}

async fn benchmark_lp_route() -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let results = run_lp_benchmarks(None);
    Ok(Json(serde_json::to_value(results).unwrap()))
}

async fn compare_runs_route(
    Json(req): Json<CompareRequest>,
) -> Result<Json<serde_json::Value>, (StatusCode, Json<ErrorBody>)> {
    let paths: Vec<PathBuf> = req.paths.into_iter().map(|p| path_buf(&p)).collect();
    let comparison = compare_runs(&paths).map_err(storage_err)?;
    Ok(Json(serde_json::to_value(comparison).unwrap()))
}

#[derive(Serialize)]
struct ErrorBody {
    error: String,
}

fn load_blend_scenario(
    path: &Option<String>,
    yaml: &Option<String>,
) -> Result<BlendScenarioFile, String> {
    match require_path_or_yaml(path.as_deref(), yaml.as_deref())? {
        request::PathOrYaml::Path(p) => {
            BlendScenarioFile::from_yaml_file(&path_buf(&p)).map_err(|e| e.to_string())
        }
        request::PathOrYaml::Yaml(text) => {
            BlendScenarioFile::from_yaml_str(&text).map_err(|e| e.to_string())
        }
    }
}

fn load_static_scenario(path: &Option<String>, yaml: &Option<String>) -> Result<Scenario, String> {
    match require_path_or_yaml(path.as_deref(), yaml.as_deref())? {
        request::PathOrYaml::Path(p) => {
            Scenario::from_yaml_file(path_buf(&p).as_path()).map_err(|e| e.to_string())
        }
        request::PathOrYaml::Yaml(text) => {
            Scenario::from_yaml_str(&text).map_err(|e| e.to_string())
        }
    }
}

fn load_inventory_scenario(
    path: &Option<String>,
    yaml: &Option<String>,
) -> Result<InventoryScenario, String> {
    match require_path_or_yaml(path.as_deref(), yaml.as_deref())? {
        request::PathOrYaml::Path(p) => {
            InventoryScenario::from_yaml_file(&path_buf(&p)).map_err(|e| e.to_string())
        }
        request::PathOrYaml::Yaml(text) => {
            InventoryScenario::from_yaml_str(&text).map_err(|e| e.to_string())
        }
    }
}

fn load_blend_schedule_scenario(
    path: &Option<String>,
    yaml: &Option<String>,
) -> Result<BlendScheduleScenario, String> {
    match require_path_or_yaml(path.as_deref(), yaml.as_deref())? {
        request::PathOrYaml::Path(p) => {
            BlendScheduleScenario::from_yaml_file(&path_buf(&p)).map_err(|e| e.to_string())
        }
        request::PathOrYaml::Yaml(text) => {
            BlendScheduleScenario::from_yaml_str(&text).map_err(|e| e.to_string())
        }
    }
}

fn base64_decode(input: &str) -> Result<Vec<u8>, String> {
    use base64::Engine;
    base64::engine::general_purpose::STANDARD
        .decode(input)
        .map_err(|e| e.to_string())
}

fn err(e: impl ToString) -> (StatusCode, Json<ErrorBody>) {
    (
        StatusCode::BAD_REQUEST,
        Json(ErrorBody {
            error: e.to_string(),
        }),
    )
}

fn storage_err(e: crude_storage::StorageError) -> (StatusCode, Json<ErrorBody>) {
    let status = match &e {
        crude_storage::StorageError::NotFound(_) => StatusCode::NOT_FOUND,
        _ => StatusCode::BAD_REQUEST,
    };
    (
        status,
        Json(ErrorBody {
            error: e.to_string(),
        }),
    )
}
