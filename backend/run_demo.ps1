# CloudIntelliGuard — Automated End-to-End Pipeline Execution Script
$ErrorActionPreference = "Stop"

$baseUrl = "http://127.0.0.1:8001"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " CloudIntelliGuard: Phase 1 ML & Anomaly Detection Pipeline" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Server
Write-Host "`n[1/6] Checking API server at $baseUrl..." -ForegroundColor Yellow
try {
    $info = Invoke-RestMethod -Uri "$baseUrl/openapi.json" -Method Get
    Write-Host "      Server is ONLINE: $($info.info.title) v$($info.info.version)" -ForegroundColor Green
} catch {
    Write-Host "      Error connecting to server. Please start Uvicorn first." -ForegroundColor Red
    exit 1
}

# 2. Authentication
Write-Host "`n[2/6] Authenticating as Admin..." -ForegroundColor Yellow
$loginBody = @{
    username = "admin"
    password = "Admin123!"
}
$authResp = Invoke-RestMethod -Uri "$baseUrl/api/v1/auth/login" -Method Post -Body $loginBody
$token = $authResp.access_token
$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}
Write-Host "      Authentication SUCCESS (JWT token acquired)" -ForegroundColor Green

# 3. Upload Dataset
Write-Host "`n[3/6] Ingesting CloudTrail demo dataset..." -ForegroundColor Yellow
$filePath = "$PSScriptRoot\data\demo\sample_cloudtrail.csv"
$form = @{
    name = "CloudTrail Demo Batch"
    description = "Observational multi-user AWS activity dataset"
    file = Get-Item -Path $filePath
}
$dsResp = Invoke-RestMethod -Uri "$baseUrl/api/v1/datasets/upload" -Headers @{ Authorization = "Bearer $token" } -Method Post -Form $form
$datasetId = $dsResp.id
Write-Host "      Dataset uploaded: ID = $datasetId, Name = '$($dsResp.name)', Status = '$($dsResp.status)'" -ForegroundColor Green

# 4. Construct Dynamic Temporal Graph Windows
Write-Host "`n[4/6] Preprocessing and constructing temporal graph windows..." -ForegroundColor Yellow
$processBody = @{
    window_type = "fixed"
    window_hours = 24
} | ConvertTo-Json
$procResp = Invoke-RestMethod -Uri "$baseUrl/api/v1/datasets/$datasetId/process" -Headers $headers -Method Post -Body $processBody
Write-Host "      Graph construction SUCCESS: $($procResp.message)" -ForegroundColor Green

# 5. Train Model & Run Anomaly Detection Inference
Write-Host "`n[5/6] Training baseline GCN model and running inference..." -ForegroundColor Yellow
$trainBody = @{
    dataset_id = $datasetId
    model_type = "baseline"
} | ConvertTo-Json
$trainResp = Invoke-RestMethod -Uri "$baseUrl/api/v1/detection/models/train" -Headers $headers -Method Post -Body $trainBody
Write-Host "      Model trained: Run ID = $($trainResp.id), Status = '$($trainResp.status)'" -ForegroundColor Green

$inferBody = @{
    graph_window_id = $datasetId
    model_type = "baseline"
    threshold = 0.5
} | ConvertTo-Json
$inferResp = Invoke-RestMethod -Uri "$baseUrl/api/v1/detection/models/infer" -Headers $headers -Method Post -Body $inferBody
Write-Host "      Inference complete: Evaluated $($inferResp.Count) user nodes" -ForegroundColor Green

Write-Host "`n---------------- User Anomaly Scores ----------------" -ForegroundColor Magenta
foreach ($user in $inferResp) {
    if ($user.is_anomaly) {
        Write-Host " [!] ANOMALY DETECTED -> User: $($user.cloud_user_id) | Score: $([math]::Round($user.anomaly_score, 4))" -ForegroundColor Red
    } else {
        Write-Host " [ok] Normal Activity -> User: $($user.cloud_user_id) | Score: $([math]::Round($user.anomaly_score, 4))" -ForegroundColor Green
    }
}

# 6. Fetch Dashboard Summary
Write-Host "`n[6/6] Fetching live security dashboard metrics..." -ForegroundColor Yellow
$summary = Invoke-RestMethod -Uri "$baseUrl/api/v1/evaluation/dashboard/summary" -Headers $headers -Method Get
Write-Host "      Total Datasets    : $($summary.total_datasets)" -ForegroundColor White
Write-Host "      Total Events      : $($summary.total_events)" -ForegroundColor White
Write-Host "      Total Anomalies   : $($summary.total_anomalies)" -ForegroundColor White
Write-Host "      Open Incidents    : $($summary.open_incidents)" -ForegroundColor White
Write-Host "      Total Alerts      : $($summary.total_alerts)" -ForegroundColor White

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Pipeline Task Execution Completed Successfully!" -ForegroundColor Cyan
Write-Host " Interactive Swagger UI available at: $baseUrl/docs" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
