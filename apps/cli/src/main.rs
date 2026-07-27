mod doctor;

use clap::{Parser, Subcommand};
use crude_assay::import_assay;
use crude_blending::{evaluate_blend, get_blend_property};
use crude_constraints::{
    evaluate_compatibility, evaluate_product_constraints, ProductConstraints, PropertyBound,
    DEFAULT_COMPATIBILITY_K,
};
use crude_domain::PropertyId;
use crude_economics::{fetch_history_cached, fetch_live_cached, PriceCacheConfig};
use crude_optimization::{
    optimize_blend_schedule, optimize_inventory, optimize_scenario, BlendScheduleOutput,
    InventoryOptimizationOutput, SolverStatus,
};
use crude_scenarios::{
    simulate_gbm, BlendScenarioFile, BlendScheduleScenario, InventoryScenario, MonteCarloConfig,
    PriceSeries, Scenario,
};
use crude_storage::{
    compare_runs, get_run, list_runs, save_blend_schedule_run, save_inventory_run, save_run,
};
use doctor::run_doctor;
use serde::Deserialize;
use serde::Serialize;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Parser)]
#[command(name = "crude", about = "Crude oil assay, blending, and optimization")]
struct Cli {
    #[command(flatten)]
    global: GlobalOpts,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Parser)]
struct GlobalOpts {
    /// Emit compact JSON on stdout (no pretty-print)
    #[arg(long, global = true)]
    json: bool,
    /// Suppress stderr progress messages
    #[arg(long, short = 'q', global = true)]
    quiet: bool,
}

#[derive(Subcommand)]
enum Commands {
    Assay {
        #[command(subcommand)]
        action: AssayCommands,
    },
    Blend {
        #[command(subcommand)]
        action: BlendCommands,
    },
    Optimize {
        scenario: PathBuf,
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    Compare {
        runs: Vec<PathBuf>,
    },
    Inventory {
        #[command(subcommand)]
        action: InventoryCommands,
    },
    Simulate {
        prices: PathBuf,
        #[arg(long, default_value_t = 1000)]
        iterations: usize,
        #[arg(long, default_value_t = 63)]
        days: usize,
        #[arg(long)]
        seed: Option<u64>,
    },
    Compatibility {
        input: PathBuf,
    },
    Prices {
        #[command(subcommand)]
        action: PricesCommands,
    },
    /// List or show saved optimization runs
    Runs {
        #[command(subcommand)]
        action: RunsCommands,
    },
    /// Verify solver, fixtures, and optional live price fetch
    Doctor {
        /// Fixtures directory (default: auto-detect)
        #[arg(long)]
        fixtures: Option<PathBuf>,
        /// Also fetch live WTI/Brent from Yahoo Finance
        #[arg(long)]
        online: bool,
    },
}

#[derive(Subcommand)]
enum AssayCommands {
    Import { path: PathBuf },
}

#[derive(Subcommand)]
enum BlendCommands {
    Evaluate {
        path: PathBuf,
    },
    Optimize {
        scenario: PathBuf,
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
}

#[derive(Subcommand)]
enum InventoryCommands {
    Optimize {
        scenario: PathBuf,
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
}

#[derive(Subcommand)]
enum PricesCommands {
    Fetch {
        #[arg(short, long)]
        output: Option<PathBuf>,
        /// Yahoo chart range for daily history (`1y`, `2y`, `5y`)
        #[arg(long)]
        history: Option<String>,
        /// Bypass disk cache
        #[arg(long)]
        no_cache: bool,
    },
}

#[derive(Subcommand)]
enum RunsCommands {
    /// List runs in ./runs (newest first)
    List {
        #[arg(long, default_value = "runs")]
        dir: PathBuf,
    },
    /// Show a run by id
    Show {
        run_id: String,
        #[arg(long, default_value = "runs")]
        dir: PathBuf,
    },
}

#[derive(Deserialize)]
struct CompatibilityInput {
    sbn_values: Vec<f64>,
    in_values: Vec<f64>,
    fractions: Vec<f64>,
    #[serde(default = "default_k")]
    k: f64,
}

fn default_k() -> f64 {
    DEFAULT_COMPATIBILITY_K
}

fn main() {
    let cli = Cli::parse();
    match run(cli) {
        Ok(code) => std::process::exit(code),
        Err(e) => {
            eprintln!("error: {e}");
            std::process::exit(exit_code_for_error(e.as_ref()));
        }
    }
}

fn exit_code_for_error(err: &dyn std::error::Error) -> i32 {
    let mut current = Some(err);
    while let Some(e) = current {
        if e.to_string().starts_with("infeasible:") {
            return 2;
        }
        current = e.source();
    }
    1
}

/// Returns process exit code: 0 ok/optimal, 2 infeasible.
fn run(cli: Cli) -> Result<i32, Box<dyn std::error::Error>> {
    let opts = cli.global;
    let code = match cli.command {
        Commands::Assay { action } => match action {
            AssayCommands::Import { path } => {
                let crude = import_assay(&path)?;
                emit(&opts, &crude)?;
                0
            }
        },
        Commands::Blend { action } => match action {
            BlendCommands::Evaluate { path } => {
                let report = blend_evaluate_report(&path)?;
                emit(&opts, &report)?;
                0
            }
            BlendCommands::Optimize { scenario, output } => {
                let sc = BlendScheduleScenario::from_yaml_file(&scenario)?;
                let result = optimize_blend_schedule(&sc)?;
                save_blend_schedule_output(&output, &sc.name, &result, &opts)?;
                emit(&opts, &result)?;
                exit_code_for_status(&result.status)
            }
        },
        Commands::Optimize { scenario, output } => {
            let sc = Scenario::from_yaml_file(&scenario)?;
            let result = optimize_scenario(&sc)?;
            let out_path = match &output {
                Some(p) => save_run(p, &result)?,
                None => {
                    let default = PathBuf::from("runs").join(format!("{}.json", sc.name));
                    save_run(&default, &result)?
                }
            };
            if !opts.quiet {
                eprintln!("saved run to {}", out_path.display());
            }
            emit(&opts, &result)?;
            exit_code_for_status(&result.status)
        }
        Commands::Compare { runs } => {
            let comparison = compare_runs(&runs)?;
            emit(&opts, &comparison)?;
            0
        }
        Commands::Inventory { action } => match action {
            InventoryCommands::Optimize { scenario, output } => {
                let sc = InventoryScenario::from_yaml_file(&scenario)?;
                let result = optimize_inventory(&sc)?;
                save_inventory_output(&output, &sc.name, &result, &opts)?;
                emit(&opts, &result)?;
                exit_code_for_status(&result.status)
            }
        },
        Commands::Simulate {
            prices,
            iterations,
            days,
            seed,
        } => {
            let text = fs::read_to_string(&prices)?;
            let series: PriceSeries = serde_json::from_str(&text)?;
            let config = MonteCarloConfig {
                iterations,
                forecast_days: days,
                seed,
            };
            let result = simulate_gbm(&series, &config)?;
            emit(&opts, &result)?;
            0
        }
        Commands::Compatibility { input } => {
            let text = fs::read_to_string(&input)?;
            let req: CompatibilityInput = serde_json::from_str(&text)?;
            let result =
                evaluate_compatibility(&req.sbn_values, &req.in_values, &req.fractions, req.k);
            emit(&opts, &result)?;
            0
        }
        Commands::Prices { action } => match action {
            PricesCommands::Fetch {
                output,
                history,
                no_cache,
            } => {
                let cache = PriceCacheConfig::from_env();
                let payload = if let Some(range) = history {
                    let hist = fetch_history_cached(&cache, &range, no_cache)?;
                    serde_json::json!({
                        "range": range,
                        "history": hist,
                    })
                } else {
                    let live = fetch_live_cached(&cache, no_cache)?;
                    serde_json::to_value(live)?
                };
                if let Some(path) = output {
                    if let Some(parent) = path.parent() {
                        fs::create_dir_all(parent)?;
                    }
                    let json = serde_json::to_string_pretty(&payload)?;
                    fs::write(&path, &json)?;
                    if !opts.quiet {
                        eprintln!("saved to {}", path.display());
                    }
                }
                emit(&opts, &payload)?;
                0
            }
        },
        Commands::Runs { action } => match action {
            RunsCommands::List { dir } => {
                let runs = list_runs(&dir)?;
                emit(&opts, &runs)?;
                0
            }
            RunsCommands::Show { run_id, dir } => {
                let record = get_run(&dir, &run_id)?;
                emit(&opts, &record)?;
                0
            }
        },
        Commands::Doctor { fixtures, online } => {
            let report = run_doctor(fixtures, online);
            emit(&opts, &report)?;
            if report.healthy {
                0
            } else {
                1
            }
        }
    };
    Ok(code)
}

fn emit<T: Serialize>(opts: &GlobalOpts, value: &T) -> Result<(), Box<dyn std::error::Error>> {
    let text = if opts.json {
        serde_json::to_string(value)?
    } else {
        serde_json::to_string_pretty(value)?
    };
    println!("{text}");
    Ok(())
}

fn exit_code_for_status(status: &SolverStatus) -> i32 {
    match status {
        SolverStatus::Optimal => 0,
        SolverStatus::Infeasible => 2,
        SolverStatus::Error => 1,
    }
}

fn save_blend_schedule_output(
    output: &Option<PathBuf>,
    scenario_name: &str,
    result: &BlendScheduleOutput,
    opts: &GlobalOpts,
) -> Result<PathBuf, Box<dyn std::error::Error>> {
    let path = output.clone().unwrap_or_else(|| {
        PathBuf::from("runs").join(format!("{scenario_name}-blend-schedule.json"))
    });
    let saved = save_blend_schedule_run(&path, result)?;
    if !opts.quiet {
        eprintln!("saved to {}", saved.display());
    }
    Ok(saved)
}

fn save_inventory_output(
    output: &Option<PathBuf>,
    scenario_name: &str,
    result: &InventoryOptimizationOutput,
    opts: &GlobalOpts,
) -> Result<(), Box<dyn std::error::Error>> {
    let path = output
        .clone()
        .unwrap_or_else(|| PathBuf::from("runs").join(format!("{scenario_name}-inventory.json")));
    let saved = save_inventory_run(&path, result)?;
    if !opts.quiet {
        eprintln!("saved to {}", saved.display());
    }
    Ok(())
}

fn blend_evaluate_report(path: &Path) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
    let blend_file = BlendScenarioFile::from_yaml_file(path)?;
    let recipe = blend_file.to_blend_recipe();
    let crudes = blend_file.build_crude_library();
    let prices = blend_file.price_map();
    let eval = evaluate_blend(
        &recipe,
        &crudes,
        if prices.is_empty() {
            None
        } else {
            Some(&prices)
        },
        blend_file.total_volume_bbl,
    )?;

    let mut report = serde_json::json!({
        "name": blend_file.name,
        "api_gravity": get_blend_property(&eval, PropertyId::ApiGravity),
        "sulfur_wt_pct": get_blend_property(&eval, PropertyId::SulfurWtPct),
        "feed_cost_per_bbl": eval.feed_cost_per_bbl,
        "component_volumes_bbl": eval.component_volumes_bbl,
    });

    if let Some(c) = blend_file.constraints {
        let constraints = ProductConstraints {
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
        };
        let check = evaluate_product_constraints(&eval, &constraints);
        report["constraints_satisfied"] = serde_json::json!(check.satisfied);
        report["violations"] = serde_json::to_value(&check.violations)?;
    }

    Ok(report)
}
