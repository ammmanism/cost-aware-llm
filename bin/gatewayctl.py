import typer
import httpx
import json
import os
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="LLM Gateway Administrative CLI")
console = Console()

ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "admin-secret-change-me")
BASE_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")

@app.command()
def create_key(tenant_id: str, prefix: str = "sk"):
    """Generate a new API key for a tenant."""
    headers = {"X-Admin-Key": ADMIN_KEY}
    payload = {"tenant_id": tenant_id, "prefix": prefix}
    
    try:
        response = httpx.post(f"{BASE_URL}/admin/keys", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        console.print(f"[bold green]Success![/bold green] Key created for {tenant_id}")
        console.print(f"Key: [yellow]{data['api_key']}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def list_keys(tenant_id: str):
    """List all key hashes for a tenant."""
    headers = {"X-Admin-Key": ADMIN_KEY}
    
    try:
        response = httpx.get(f"{BASE_URL}/admin/keys/{tenant_id}", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        table = Table(title=f"API Keys for {tenant_id}")
        table.add_column("Key Hash (SHA-256)", style="cyan")
        
        for kw in data.get("key_hashes", []):
            table.add_row(kw)
        
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def status():
    """Check gateway and provider health status."""
    headers = {"X-Admin-Key": ADMIN_KEY}
    
    try:
        response = httpx.get(f"{BASE_URL}/admin/providers/status", headers=headers)
        response.raise_for_status()
        data = response.json()
        
        table = Table(title="Gateway Provider Status")
        table.add_column("Provider", style="bold")
        table.add_column("Status", style="magenta")
        
        for name, stat in data.get("providers", {}).items():
            status_color = "green" if stat == "healthy" else "red"
            table.add_row(name, f"[{status_color}]{stat}[/{status_color}]")
        
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def chaos(mode: str = "latency", rate: float = 0.1):
    """Enable chaos mode (failure or latency)."""
    headers = {"X-Admin-Key": ADMIN_KEY}
    params = {"failure_rate": rate, "latency_ms": 500}
    
    try:
        response = httpx.post(f"{BASE_URL}/admin/chaos/{mode}", headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        console.print(f"[bold yellow]Chaos Enabled:[/bold yellow] {data['chaos_mode']}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()
