"""
A03:2025 — Software Supply Chain Failures.

Za razliku od ostalih modula, ovaj NE gadja pokrenutu aplikaciju preko HTTP-a,
nego skenira zavisnosti projekta na poznate ranjivosti (CVE/advisory):

  Python  -> pip-audit nad requirements.txt (baza: PyPI Advisory / OSV)
  Node    -> npm audit nad frontend/package-lock.json

Ranjiva biblioteka u zavisnostima je supply-chain rizik i savrseno napisan kod
je ugrozen ako vuce paket sa poznatom rupom. Zato se zavisnosti redovno skeniraju
i azuriraju.

U sustini, samo proverava da li koriscene biblioteke imaju pronadjene rupe.
"""

import json
import os
import subprocess
import sys

NAME = "Ranjive zavisnosti — pip/npm audit (A03)"
DESCRIPTION = "Skenira Python (pip-audit) i Node (npm audit) zavisnosti na CVE-ove."

_BASEDIR = os.path.abspath(os.path.dirname(__file__))
KOREN = os.path.abspath(os.path.join(_BASEDIR, "..", ".."))
REQ = os.path.join(KOREN, "requirements.txt")
FRONTEND = os.path.join(KOREN, "frontend")


def _pip_audit(ctx):
    ctx.log("--- Python zavisnosti (pip-audit nad requirements.txt) ---")
    if not os.path.isfile(REQ):
        ctx.info("requirements.txt nije pronadjen."); return
    try:
        p = subprocess.run([sys.executable, "-m", "pip_audit", "-r", REQ, "-f", "json"],
                           capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        ctx.info("pip-audit nije instaliran (pip install pip-audit)."); return
    except subprocess.TimeoutExpired:
        ctx.info("pip-audit je istekao (mreza?)."); return
    try:
        data = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        ctx.info(f"Ne mogu da procitam pip-audit izlaz: {(p.stderr or '')[:120]}"); return

    deps = data.get("dependencies", data if isinstance(data, list) else [])
    ranjivi = [d for d in deps if d.get("vulns")]
    ukupno = sum(len(d.get("vulns", [])) for d in ranjivi)
    if ukupno:
        ctx.exposed(f"{ukupno} poznatih ranjivosti u {len(ranjivi)} Python paketa:")
        for d in ranjivi:
            ids = ", ".join(v.get("id", "?") for v in d.get("vulns", []))
            fix = ", ".join(sorted({f for v in d.get("vulns", []) for f in v.get("fix_versions", [])}))
            ctx.log(f"    {d.get('name')} {d.get('version')} -> {ids}"
                    + (f"  (popravka: {fix})" if fix else ""))
    else:
        ctx.blocked("pip-audit nije nasao poznate ranjivosti u Python zavisnostima.")


def _npm_audit(ctx):
    ctx.log("--- Node zavisnosti (npm audit u frontend/) ---")
    if not os.path.isfile(os.path.join(FRONTEND, "package-lock.json")):
        ctx.info("frontend/package-lock.json nije pronadjen."); return
    npm = "npm.cmd" if os.name == "nt" else "npm"
    try:
        p = subprocess.run([npm, "audit", "--json"], cwd=FRONTEND,
                           capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        ctx.info("npm nije pronadjen u PATH-u."); return
    except subprocess.TimeoutExpired:
        ctx.info("npm audit je istekao (mreza?)."); return
    try:
        data = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        ctx.info(f"Ne mogu da procitam npm audit izlaz: {(p.stderr or '')[:120]}"); return

    meta = (data.get("metadata") or {}).get("vulnerabilities") or {}
    ukupno = meta.get("total", 0)
    if ukupno:
        delovi = [f"{k}: {meta.get(k)}" for k in ("critical", "high", "moderate", "low")
                  if meta.get(k)]
        ctx.exposed(f"{ukupno} ranjivosti u Node zavisnostima ({', '.join(delovi)}):")
        for ime, info in list((data.get("vulnerabilities") or {}).items())[:12]:
            ctx.log(f"    {ime} ({info.get('severity')})")
    else:
        ctx.blocked("npm audit nije nasao ranjivosti u Node zavisnostima.")


def run(ctx):
    ctx.log(f"Projekat: {KOREN}")
    ctx.log("(skener zavisnosti - ne gadja pokrenutu aplikaciju)")
    ctx.log("")
    _pip_audit(ctx)
    ctx.log("")
    _npm_audit(ctx)
    ctx.log("")
    ctx.log(ctx.summary())
