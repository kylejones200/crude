#[tokio::main]
async fn main() {
    if let Err(e) = crude_api::serve().await {
        eprintln!("crude-api error: {e}");
        std::process::exit(1);
    }
}
