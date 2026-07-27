use axum::body::Body;
use axum::http::{Request, StatusCode};
use base64::Engine;
use crude_api::{init_state, router};
use http_body_util::BodyExt;
use tower::ServiceExt;

#[tokio::test]
async fn health_returns_ok() {
    let state = init_state().expect("state");
    let app = router(state);
    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    assert_eq!(body, "ok");
}

#[tokio::test]
async fn rejects_path_outside_data_roots() {
    let state = init_state().expect("state");
    let app = router(state);
    let body = serde_json::json!({
        "path": "../../../etc/passwd"
    });
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/assay/import")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn assay_import_from_inline_base64() {
    let state = init_state().expect("state");
    let app = router(state);
    let json = r#"{"name":"West Texas Intermediate","api":39.6,"sulfur":0.24}"#;
    let b64 = base64::engine::general_purpose::STANDARD.encode(json.as_bytes());
    let body = serde_json::json!({
        "format": "json",
        "content_base64": b64
    });
    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/assay/import")
                .header("content-type", "application/json")
                .body(Body::from(body.to_string()))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::OK);
}
