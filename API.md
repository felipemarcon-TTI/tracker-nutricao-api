# Tracker Nutrição — API de Leitura

Base URL: `https://<seu-servico>.up.railway.app`

Autenticação: header `x-api-key: <DASHBOARD_API_KEY>` em todos os endpoints exceto `/api/health`.

---

## Saúde

### `GET /api/health`
Sem auth. Verifica conexão ao banco.
```json
{"status": "ok", "timestamp": "2026-06-11T10:00:00+01:00"}
```

---

## Nutrição

### `GET /api/daily-summary?date=YYYY-MM-DD`
Totais do dia vs metas. `date` omitido = hoje (Lisboa).
```json
{
  "data": "2026-06-09",
  "calorias": {"valor": 1850.0, "meta": 2253, "pct": 82.1},
  "proteina_g": {"valor": 145.0, "meta": 183.3, "pct": 79.1},
  "carbs_g": {"valor": 200.0, "meta": 231.9, "pct": 86.2},
  "gordura_g": {"valor": 55.0, "meta": 70.7, "pct": 77.8},
  "fibra_g": {"valor": 12.0, "meta": 17.7, "pct": 67.8},
  "micronutrientes": {
    "calcio_mg": {"valor": 800.0, "meta": 1145.1, "pct": 69.9},
    "ferro_mg": {"valor": 5.2, "meta": 7.3, "pct": 71.2},
    "...": "..."
  },
  "refeicoes_total": 4,
  "refeicoes_plano": 3
}
```

### `GET /api/range-summary?start=YYYY-MM-DD&end=YYYY-MM-DD`
Array diário de macros para gráficos de tendência.
```json
[
  {"data": "2026-06-01", "calorias": 1900.0, "proteina_g": 150.0, "carbs_g": 210.0, "gordura_g": 60.0, "fibra_g": 14.0, "sodio_mg": 800.0}
]
```

### `GET /api/micronutrient-status?weeks=8`
Médias semanais por micronutriente + flag de alerta.
```json
{
  "nutrientes": {
    "vitamina_d_mcg": {
      "nome": "Vitamina D", "meta": 1.9, "media_diaria": 0.5, "pct_meta": 26.3,
      "semanas_consecutivas_abaixo": 6, "semanas_consecutivas_acima": 0,
      "alerta": true, "threshold_semanas": 5,
      "historico_semanal": [{"semana": "2026-W22", "media": 0.4}]
    }
  },
  "alertas_ativos": [{"nutrient": "vitamina_d_mcg", "escalation_level": "red_flag", "weeks_below": 6}]
}
```

### `GET /api/weight-history?days=90`
Histórico de peso com contexto de sódio.
```json
[{"data": "2026-06-10", "peso_kg": 74.2, "cintura_cm": 82.0, "sodio_medio_3d_anteriores": 920.5}]
```

### `GET /api/meals?date=YYYY-MM-DD`
Refeições do dia com todos os campos de macros e micros.
```json
[{"id": 6, "horario": "2026-06-09T08:30:00+01:00", "meal_type": "cafe_manha", "description": "Ovos mexidos", "calories": 320.0, "protein_g": 24.0, "...": "..."}]
```

### `GET /api/protein-distribution?date=YYYY-MM-DD`
Distribuição de proteína ao longo do dia.
```json
{
  "data": "2026-06-09", "total_proteina_g": 145.0, "meta_proteina_g": 183.3,
  "refeicoes": [{"horario": "2026-06-09T08:30:00", "tipo": "cafe_manha", "proteina_g": 24.0}],
  "maior_janela_sem_proteina_horas": 5.2,
  "refeicoes_com_30g_ou_mais": 3
}
```

---

## Treino

### `GET /api/workouts?days=30`
Sessões com sets, split_day, energia, qualidade_sono.
```json
[{"id": 1, "workout_date": "2026-06-11", "split_day": "push", "energy_level": 4, "sleep_quality": 3,
  "sets": [{"exercise_name": "Supino Reto", "reps": 8, "weight_kg": 80.0, "is_alternative": false}]}]
```

### `GET /api/workout-volume?weeks=8`
Volume (kg×reps) por grupo muscular por semana.
```json
[{"semana": "2026-06-09", "grupo_muscular": "peito", "volume": 1920.0}]
```

### `GET /api/exercise-progression?exercise=supino&weeks=12`
Progressão de carga com 1RM estimado (Epley: `kg × (1 + reps/30)`).
```json
[{"semana": "2026-06-11", "kg_max": 80.0, "reps_max": 8, "rm_estimado_kg": 101.3}]
```

### `GET /api/training-adherence?weeks=4`
Aderência ao plano PPL.
```json
{
  "plano": {"min_por_semana": 3, "max_por_semana": 4, "split": "PPL"},
  "semanas": [{"semana": "2026-06-09 a 2026-06-15", "treinos_realizados": 1,
               "aderencia_pct": 25.0, "grupos_treinados": ["push"], "grupos_negligenciados": ["pull","legs"]}]
}
```

### `GET /api/exercise-list`
Exercícios distintos agrupados por grupo muscular.
```json
[{"exercicio": "Supino Reto", "grupo_muscular": "peito"}]
```

### `GET /api/suspicious-days?days=7`
Dias com pouca ingestão, poucas refeições ou janela alimentar curta.
```json
{"periodo": "2026-06-05 a 2026-06-11", "dias_suspeitos": [{"data": "2026-06-10", "total_kcal": 660.0, "flags": ["kcal_baixa","poucas_refeicoes"]}]}
```

---

## Variáveis de Ambiente Railway

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | PostgreSQL URL (mesma do MCP) |
| `DASHBOARD_API_KEY` | `nutri-dash-2657675800e523afa0f4b110bbfe183a` |
| `PORT` | Definido automaticamente pelo Railway |