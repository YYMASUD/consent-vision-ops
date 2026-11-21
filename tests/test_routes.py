from app.main import app

def test_reporting_routes_registered():
    paths = {r.path for r in app.routes}
    assert "/v1/reports/occupancy" in paths
    assert "/v1/reports/health" in paths
