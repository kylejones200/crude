//! HTTP API for crude (Landmark API blueprint).

use std::net::SocketAddr;
use std::path::PathBuf;

use axum::response::Redirect;
use axum::routing::{get, post};
use axum::Json;
use clap::Parser;
use serde::Deserialize;
use serde_json::json;
use tower_http::cors::CorsLayer;

const SERVICE_NAME: &str = "crude";
const API_VERSION: &str = env!("CARGO_PKG_VERSION");

#[derive(Clone)]
struct AppState {
    work_dir: PathBuf,
}

#[derive(Parser)]
struct Args {
    #[arg(long, env = "WORK_DIR", default_value = "output")]
    work_dir: PathBuf,
    #[arg(long, env = "HOST", default_value = "127.0.0.1")]
    host: String,
    #[arg(long, env = "PORT", default_value = "8080")]
    port: u16,
}

#[derive(Debug, Deserialize)]
struct RunBody {
    input: PathBuf,
    #[serde(default)]
    output: Option<PathBuf>,
    #[serde(default)]
    args: Vec<String>,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();
    let state = AppState { work_dir: args.work_dir.clone() };
    let app = router(state);
    let addr: SocketAddr = format!("{}:{}", args.host, args.port).parse()?;
    println!("{service}-api listening on http://{addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

fn router(state: AppState) -> axum::Router {
    axum::Router::new()
        .route("/health", get(health))
        .route("/version", get(version))
        .route("/metadata", get(metadata))
        .route("/openapi.json", get(openapi_spec))
        .route("/swagger", get(|| async { Redirect::temporary("/openapi.json") }))
        .route("/validate", post(validate))
        .route("/preview", post(preview))
        .route("/run", post(run_handler))
        .layer(CorsLayer::permissive())
        .with_state(state)
}

async fn health() -> Json<serde_json::Value> {
    Json(json!({ "status": "ok", "service": SERVICE_NAME, "version": API_VERSION }))
}

async fn version() -> Json<serde_json::Value> {
    Json(json!({ "service": SERVICE_NAME, "version": API_VERSION, "api": "v1" }))
}

async fn metadata(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({
        "service": SERVICE_NAME,
        "version": API_VERSION,
        "description": "Landmark portfolio service",
        "work_dir": state.work_dir
    }))
}

async fn openapi_spec() -> Json<serde_json::Value> {
    Json(json!({
        "openapi": "3.1.0",
        "info": { "title": SERVICE_NAME, "version": API_VERSION },
        "paths": { "/run": { "post": { "summary": "Run processing job" } } }
    }))
}

async fn validate(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({ "valid": true, "work_dir": state.work_dir }))
}

async fn preview(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({ "preview": true, "work_dir": state.work_dir }))
}

async fn run_handler(
    State(state): State<AppState>,
    Json(body): Json<RunBody>,
) -> Result<Json<serde_json::Value>, (axum::http::StatusCode, Json<serde_json::Value>)> {
    let cli = std::env::var("DOMAIN_CLI").unwrap_or_else(|_| "crude".into());
    let output = body.output.clone().unwrap_or_else(|| state.work_dir.clone());
    let mut cmd = tokio::process::Command::new(&cli);
    cmd.arg(&body.input);
    if body.input.is_dir() {{
        cmd.arg("--output").arg(&output);
    }} else {{
        cmd.arg(&output);
    }}
    for arg in &body.args {{
        cmd.arg(arg);
    }}
    let out = cmd.output().await.map_err(|e| (
        axum::http::StatusCode::INTERNAL_SERVER_ERROR,
        Json(json!({{ "code": "spawn_failed", "message": e.to_string(), "details": null }})),
    ))?;
    if !out.status.success() {{
        let message = String::from_utf8_lossy(&out.stderr).into_owned();
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(json!({{ "code": "run_failed", "message": message, "details": null }})),
        ));
    }}
    Ok(Json(json!({{
        "status": "ok",
        "cli": cli,
        "input": body.input,
        "output": output,
        "stdout": String::from_utf8_lossy(&out.stdout).chars().take(4000).collect::<String>()
    }})))
}}
