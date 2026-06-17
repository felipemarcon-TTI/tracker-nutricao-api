import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

LISBOA = ZoneInfo("Europe/Lisbon")
DATABASE_URL = os.environ.get("DATABASE_URL")
API_KEY = os.environ.get("DASHBOARD_API_KEY", "")
PORT = int(os.environ.get("PORT", 8000))

METAS = {
    "cal": 1721, "prot": 170.9, "carbs": 146.4, "fat": 53.4, "fibra": 32.6,
    "ca": 1000, "mg": 420, "fe": 8, "k": 3400, "na": 885.7,
    "vit_c": 90, "vit_d": 15.0, "vit_b12": 2.4, "zn": 11,
}
ESCALATION_THRESHOLDS = {
    "zinco_mg": 2, "potassio_mg": 2, "vitamina_c_mg": 2,
    "ferro_mg": 3, "magnesio_mg": 3, "calcio_mg": 3,
    "vitamina_d_mcg": 5, "vitamina_b12_mcg": 6, "sodio_mg": 3,
}
NUTRIENT_NAMES = {
    "calcio_mg": "Cálcio", "ferro_mg": "Ferro", "magnesio_mg": "Magnésio",
    "potassio_mg": "Potássio", "sodio_mg": "Sódio", "vitamina_c_mg": "Vitamina C",
    "vitamina_d_mcg": "Vitamina D", "vitamina_b12_mcg": "Vitamina B12", "zinco_mg": "Zinco",
}

app = FastAPI(title="Tracker Nutrição API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","OPTIONS"], allow_headers=["*"])


def check_auth(key: Optional[str]):
    if not API_KEY or key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def db_q(sql, params=None):
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or [])
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def hoje() -> str:
    return datetime.now(LISBOA).date().isoformat()


def pct(val, meta) -> float:
    return round(float(val) / meta * 100, 1) if meta and val else 0.0


def f(val) -> float:
    return round(float(val), 2) if val is not None else 0.0


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    try:
        db_q("SELECT 1")
        return {"status": "ok", "timestamp": datetime.now(LISBOA).isoformat()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Nutrição ──────────────────────────────────────────────────────────────────

@app.get("/api/daily-summary")
async def daily_summary(
    date_param: Optional[str] = Query(None, alias="date"),
    x_api_key: Optional[str] = Header(None),
):
    check_auth(x_api_key)
    d = date_param or hoje()
    rows = db_q("""
        SELECT COALESCE(SUM(calories),0) as cal, COALESCE(SUM(protein_g),0) as prot,
               COALESCE(SUM(carbs_g),0) as carbs, COALESCE(SUM(fat_g),0) as fat,
               COALESCE(SUM(fiber_g),0) as fibra,
               COALESCE(SUM(calcium_mg),0) as ca, COALESCE(SUM(iron_mg),0) as fe,
               COALESCE(SUM(magnesium_mg),0) as mg_, COALESCE(SUM(potassium_mg),0) as k,
               COALESCE(SUM(sodium_mg),0) as na, COALESCE(SUM(vitamin_c_mg),0) as vit_c,
               COALESCE(SUM(vitamin_d_mcg),0) as vit_d, COALESCE(SUM(vitamin_b12_mcg),0) as vit_b12,
               COALESCE(SUM(zinc_mg),0) as zn,
               COUNT(*) as total, COUNT(*) FILTER (WHERE is_on_plan) as on_plan
        FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date = %s
    """, [d])
    r = rows[0] if rows else {}
    return {
        "data": d,
        "calorias":   {"valor": f(r.get("cal")),   "meta": METAS["cal"],   "pct": pct(r.get("cal"),   METAS["cal"])},
        "proteina_g": {"valor": f(r.get("prot")),  "meta": METAS["prot"],  "pct": pct(r.get("prot"),  METAS["prot"])},
        "carbs_g":    {"valor": f(r.get("carbs")), "meta": METAS["carbs"], "pct": pct(r.get("carbs"), METAS["carbs"])},
        "gordura_g":  {"valor": f(r.get("fat")),   "meta": METAS["fat"],   "pct": pct(r.get("fat"),   METAS["fat"])},
        "fibra_g":    {"valor": f(r.get("fibra")), "meta": METAS["fibra"], "pct": pct(r.get("fibra"), METAS["fibra"])},
        "micronutrientes": {
            "calcio_mg":      {"valor": f(r.get("ca")),     "meta": METAS["ca"],    "pct": pct(r.get("ca"),     METAS["ca"])},
            "ferro_mg":       {"valor": f(r.get("fe")),     "meta": METAS["fe"],    "pct": pct(r.get("fe"),     METAS["fe"])},
            "magnesio_mg":    {"valor": f(r.get("mg_")),    "meta": METAS["mg"],    "pct": pct(r.get("mg_"),    METAS["mg"])},
            "potassio_mg":    {"valor": f(r.get("k")),      "meta": METAS["k"],     "pct": pct(r.get("k"),      METAS["k"])},
            "sodio_mg":       {"valor": f(r.get("na")),     "meta": METAS["na"],    "pct": pct(r.get("na"),     METAS["na"])},
            "vitamina_c_mg":  {"valor": f(r.get("vit_c")),  "meta": METAS["vit_c"], "pct": pct(r.get("vit_c"),  METAS["vit_c"])},
            "vitamina_d_mcg": {"valor": f(r.get("vit_d")),  "meta": METAS["vit_d"], "pct": pct(r.get("vit_d"),  METAS["vit_d"])},
            "vitamina_b12_mcg":{"valor": f(r.get("vit_b12")),"meta": METAS["vit_b12"],"pct": pct(r.get("vit_b12"),METAS["vit_b12"])},
            "zinco_mg":       {"valor": f(r.get("zn")),     "meta": METAS["zn"],    "pct": pct(r.get("zn"),     METAS["zn"])},
        },
        "refeicoes_total": int(r.get("total") or 0),
        "refeicoes_plano": int(r.get("on_plan") or 0),
    }


@app.get("/api/range-summary")
async def range_summary(start: str, end: str, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    rows = db_q("""
        SELECT (meal_time AT TIME ZONE 'Europe/Lisbon')::date as data,
               COALESCE(SUM(calories),0) as calorias, COALESCE(SUM(protein_g),0) as proteina_g,
               COALESCE(SUM(carbs_g),0) as carbs_g, COALESCE(SUM(fat_g),0) as gordura_g,
               COALESCE(SUM(fiber_g),0) as fibra_g, COALESCE(SUM(sodium_mg),0) as sodio_mg
        FROM meals
        WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date BETWEEN %s AND %s
        GROUP BY 1 ORDER BY 1
    """, [start, end])
    return [{"data": str(r["data"]), "calorias": f(r["calorias"]), "proteina_g": f(r["proteina_g"]),
             "carbs_g": f(r["carbs_g"]), "gordura_g": f(r["gordura_g"]),
             "fibra_g": f(r["fibra_g"]), "sodio_mg": f(r["sodio_mg"])} for r in rows]


@app.get("/api/micronutrient-status")
async def micronutrient_status(weeks: int = 8, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today()
    start = (today - timedelta(weeks=weeks)).isoformat()
    rows = db_q("""
        SELECT (meal_time AT TIME ZONE 'Europe/Lisbon')::date as d,
               COALESCE(SUM(calcium_mg),0) as ca,   COALESCE(SUM(iron_mg),0) as fe,
               COALESCE(SUM(magnesium_mg),0) as mg_, COALESCE(SUM(potassium_mg),0) as k,
               COALESCE(SUM(sodium_mg),0) as na,     COALESCE(SUM(vitamin_c_mg),0) as vit_c,
               COALESCE(SUM(vitamin_d_mcg),0) as vit_d, COALESCE(SUM(vitamin_b12_mcg),0) as vit_b12,
               COALESCE(SUM(zinc_mg),0) as zn
        FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date BETWEEN %s AND %s
        GROUP BY 1 ORDER BY 1
    """, [start, today.isoformat()])
    col_map = {"calcio_mg":"ca","ferro_mg":"fe","magnesio_mg":"mg_","potassio_mg":"k",
               "sodio_mg":"na","vitamina_c_mg":"vit_c","vitamina_d_mcg":"vit_d",
               "vitamina_b12_mcg":"vit_b12","zinco_mg":"zn"}
    metas_map = {"calcio_mg":METAS["ca"],"ferro_mg":METAS["fe"],"magnesio_mg":METAS["mg"],
                 "potassio_mg":METAS["k"],"sodio_mg":METAS["na"],"vitamina_c_mg":METAS["vit_c"],
                 "vitamina_d_mcg":METAS["vit_d"],"vitamina_b12_mcg":METAS["vit_b12"],"zinco_mg":METAS["zn"]}
    weeks_data = defaultdict(lambda: defaultdict(list))
    for r in rows:
        iso_week = r["d"].strftime("%G-W%V")
        for nut, col in col_map.items():
            weeks_data[iso_week][nut].append(float(r.get(col) or 0))
    result = {}
    for nut, col in col_map.items():
        meta = metas_map[nut]; threshold = ESCALATION_THRESHOLDS.get(nut, 3); is_na = nut == "sodio_mg"
        weekly = [{"semana": w, "media": round(sum(v)/len(v), 1)} for w, vals in sorted(weeks_data.items()) for v in [weeks_data[w][nut]]]
        consec = 0
        for w in reversed(weekly):
            if (is_na and w["media"] > meta) or (not is_na and w["media"] < meta): consec += 1
            else: break
        media_g = sum(w["media"] for w in weekly) / len(weekly) if weekly else 0
        result[nut] = {"nome": NUTRIENT_NAMES[nut], "meta": meta, "media_diaria": round(media_g, 1),
                       "pct_meta": pct(media_g, meta),
                       "semanas_consecutivas_abaixo": 0 if is_na else consec,
                       "semanas_consecutivas_acima": consec if is_na else 0,
                       "alerta": consec >= threshold, "threshold_semanas": threshold,
                       "historico_semanal": weekly[-4:]}
    alertas = db_q("SELECT nutrient,escalation_level,weeks_below,last_suggestion FROM nutrient_alerts WHERE is_active=TRUE ORDER BY weeks_below DESC")
    return {"nutrientes": result, "alertas_ativos": alertas}


@app.get("/api/weight-history")
async def weight_history(days: int = 90, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today(); start = (today - timedelta(days=days)).isoformat()
    rows = db_q("""
        SELECT bm.measurement_date as data, bm.weight_kg, bm.waist_cm,
               (SELECT AVG(m.sodium_mg) FROM meals m
                WHERE (m.meal_time AT TIME ZONE 'Europe/Lisbon')::date
                      BETWEEN bm.measurement_date - INTERVAL '3 days' AND bm.measurement_date - INTERVAL '1 day'
               ) as sodio_medio_3d
        FROM body_metrics bm
        WHERE bm.measurement_date BETWEEN %s AND %s AND bm.weight_kg IS NOT NULL
        ORDER BY bm.measurement_date
    """, [start, today.isoformat()])
    return [{"data": str(r["data"]), "peso_kg": f(r["weight_kg"]),
             "cintura_cm": f(r["waist_cm"]) if r["waist_cm"] else None,
             "sodio_medio_3d_anteriores": round(float(r["sodio_medio_3d"]),1) if r["sodio_medio_3d"] else None}
            for r in rows]


@app.get("/api/meals")
async def list_meals(date_param: Optional[str] = Query(None, alias="date"), x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    d = date_param or hoje()
    rows = db_q("""
        SELECT id, meal_time AT TIME ZONE 'Europe/Lisbon' as horario, meal_type, description,
               is_on_plan, deviation_notes, calories, protein_g, carbs_g, fat_g, fiber_g,
               calcium_mg, iron_mg, magnesium_mg, potassium_mg, sodium_mg,
               vitamin_c_mg, vitamin_d_mcg, vitamin_b12_mcg, zinc_mg, notes
        FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date = %s ORDER BY meal_time
    """, [d])
    return [{k: str(v) if hasattr(v, "isoformat") else v for k, v in r.items()} for r in rows]


@app.get("/api/protein-distribution")
async def protein_distribution(date_param: Optional[str] = Query(None, alias="date"), x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    d = date_param or hoje()
    rows = db_q("""
        SELECT meal_time AT TIME ZONE 'Europe/Lisbon' as t, meal_type, protein_g
        FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date = %s AND COALESCE(protein_g,0) > 5
        ORDER BY meal_time
    """, [d])
    total = float((db_q("SELECT COALESCE(SUM(protein_g),0) as t FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date=%s",[d]) or [{"t":0}])[0]["t"])
    anchor_s = datetime.fromisoformat(d + "T06:00:00").replace(tzinfo=LISBOA)
    anchor_e = datetime.now(LISBOA) if d == hoje() else datetime.fromisoformat(d + "T23:59:00").replace(tzinfo=LISBOA)
    times = [r["t"] for r in rows if r["t"]]
    if not times:
        janela = round((anchor_e - anchor_s).total_seconds() / 3600, 1)
    else:
        pts = [anchor_s] + sorted(times) + [anchor_e]
        janela = round(max((pts[i+1]-pts[i]).total_seconds()/3600 for i in range(len(pts)-1)), 1)
    return {"data": d, "total_proteina_g": round(total,1), "meta_proteina_g": METAS["prot"],
            "refeicoes": [{"horario": str(r["t"]), "tipo": r["meal_type"], "proteina_g": f(r["protein_g"])} for r in rows],
            "maior_janela_sem_proteina_horas": janela,
            "refeicoes_com_30g_ou_mais": sum(1 for r in rows if float(r.get("protein_g") or 0) >= 30)}


# ── Treino ────────────────────────────────────────────────────────────────────

@app.get("/api/workouts")
async def list_workouts(days: int = 30, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today(); start = (today - timedelta(days=days)).isoformat()
    wkts = db_q("""
        SELECT id, workout_date, workout_type, location, notes, skipped,
               skip_reason, energy_level, sleep_quality, split_day
        FROM workouts WHERE workout_date BETWEEN %s AND %s ORDER BY workout_date DESC
    """, [start, today.isoformat()])
    result = []
    for w in wkts:
        sets_ = db_q("SELECT exercise_name,set_number,reps,weight_kg,rpe,is_alternative,alternative_for FROM workout_sets WHERE workout_id=%s ORDER BY set_number", [w["id"]])
        result.append({**{k: str(v) if hasattr(v,"isoformat") else v for k,v in w.items()}, "sets": sets_})
    return result


@app.get("/api/workout-volume")
async def workout_volume(weeks: int = 8, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today(); start = (today - timedelta(weeks=weeks)).isoformat()
    rows = db_q("""
        SELECT DATE_TRUNC('week', w.workout_date::timestamptz)::date as semana,
               COALESCE(e.muscle_group, 'outro') as grupo_muscular,
               COALESCE(SUM(ws.reps * ws.weight_kg), 0) as volume
        FROM workout_sets ws JOIN workouts w ON w.id=ws.workout_id
        LEFT JOIN exercises e ON LOWER(e.name)=LOWER(ws.exercise_name)
        WHERE w.workout_date BETWEEN %s AND %s AND NOT COALESCE(w.skipped,false)
        GROUP BY 1,2 ORDER BY 1,2
    """, [start, today.isoformat()])
    return [{"semana": str(r["semana"]), "grupo_muscular": r["grupo_muscular"], "volume": f(r["volume"])} for r in rows]


@app.get("/api/exercise-progression")
async def exercise_progression(exercise: str, weeks: int = 12, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today(); start = (today - timedelta(weeks=weeks)).isoformat()
    rows = db_q("""
        SELECT DATE_TRUNC('week', w.workout_date::timestamptz)::date as semana,
               MAX(ws.weight_kg) as kg_max, MAX(ws.reps) as reps_max,
               MAX(ws.weight_kg * (1 + ws.reps::float/30)) as rm_estimado
        FROM workout_sets ws JOIN workouts w ON w.id=ws.workout_id
        WHERE LOWER(ws.exercise_name) LIKE LOWER(%s) AND w.workout_date BETWEEN %s AND %s
        GROUP BY 1 ORDER BY 1
    """, [f"%{exercise}%", start, today.isoformat()])
    return [{"semana": str(r["semana"]), "kg_max": f(r["kg_max"]),
             "reps_max": int(r["reps_max"]) if r["reps_max"] else 0,
             "rm_estimado_kg": round(float(r["rm_estimado"]),1) if r["rm_estimado"] else 0.0} for r in rows]


@app.get("/api/training-adherence")
async def training_adherence(weeks: int = 4, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today()
    plan = db_q("SELECT days_per_week_min,days_per_week_max,split_type,cardio_days FROM training_plan WHERE is_active=TRUE ORDER BY id DESC LIMIT 1")
    p = plan[0] if plan else {"days_per_week_min":3,"days_per_week_max":4,"split_type":"PPL","cardio_days":1}
    split_grupos = {"PPL":{"push","pull","legs"},"upper_lower":{"upper","lower"},"fullbody":{"fullbody"}}.get(p["split_type"],set())
    monday = today - timedelta(days=today.weekday())
    result = []
    for i in range(weeks):
        ws = monday - timedelta(weeks=i); we = ws + timedelta(days=6)
        realizados = db_q("SELECT split_day FROM workouts WHERE workout_date BETWEEN %s AND %s AND NOT COALESCE(skipped,false)",[ws.isoformat(),we.isoformat()])
        pulados = db_q("SELECT COUNT(*) as n FROM workouts WHERE workout_date BETWEEN %s AND %s AND COALESCE(skipped,false)",[ws.isoformat(),we.isoformat()])
        grupos = list({r["split_day"] for r in realizados if r["split_day"]})
        n = len(realizados)
        result.append({"semana": f"{ws.isoformat()} a {we.isoformat()}", "treinos_realizados": n,
                       "treinos_pulados": int(pulados[0]["n"]) if pulados else 0,
                       "aderencia_pct": round(n/p["days_per_week_max"]*100,1) if p["days_per_week_max"] else 0,
                       "grupos_treinados": grupos,
                       "grupos_negligenciados": sorted(split_grupos - set(grupos)) if split_grupos else []})
    return {"plano":{"min_por_semana":p["days_per_week_min"],"max_por_semana":p["days_per_week_max"],"split":p["split_type"]},"semanas":result}


@app.get("/api/exercise-list")
async def exercise_list(x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    rows = db_q("""
        SELECT DISTINCT ws.exercise_name, COALESCE(e.muscle_group,'outro') as grupo_muscular
        FROM workout_sets ws LEFT JOIN exercises e ON LOWER(e.name)=LOWER(ws.exercise_name)
        ORDER BY grupo_muscular, ws.exercise_name
    """)
    return [{"exercicio": r["exercise_name"], "grupo_muscular": r["grupo_muscular"]} for r in rows]


@app.get("/api/suspicious-days")
async def suspicious_days(days: int = 7, x_api_key: Optional[str] = Header(None)):
    check_auth(x_api_key)
    today = date.today(); start = (today - timedelta(days=days)).isoformat()
    rows = db_q("""
        SELECT (meal_time AT TIME ZONE 'Europe/Lisbon')::date as data,
               COUNT(*) as n, COALESCE(SUM(calories),0) as kcal,
               EXTRACT(EPOCH FROM (MAX(meal_time)-MIN(meal_time)))/3600 as janela_h
        FROM meals WHERE (meal_time AT TIME ZONE 'Europe/Lisbon')::date BETWEEN %s AND %s
        GROUP BY 1 ORDER BY 1
    """, [start, today.isoformat()])
    suspeitos = []
    for r in rows:
        flags = []
        if float(r["kcal"]) < 1200: flags.append("kcal_baixa")
        if int(r["n"]) < 3: flags.append("poucas_refeicoes")
        if r["janela_h"] and float(r["janela_h"]) < 6: flags.append("janela_curta")
        if flags: suspeitos.append({"data": str(r["data"]), "total_kcal": f(r["kcal"]), "num_refeicoes": int(r["n"]), "flags": flags})
    return {"periodo": f"{start} a {today.isoformat()}", "dias_suspeitos": suspeitos}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)