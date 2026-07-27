fn main() {
    if let Ok(commit) = std::env::var("CRUDE_GIT_COMMIT") {
        println!("cargo:rustc-env=CRUDE_GIT_COMMIT={commit}");
    }
}
