"""Registro de uso e histórico (Postgres/Neon). Tudo opcional: sem DATABASE_URL o app funciona igual.

Tabelas (criadas automaticamente):
  ep_sessions  — cada conversa (nível, cenário, início/fim, resumo)
  ep_turns     — cada fala (sua e da parceira) com a correção
  ep_usage     — cada chamada de IA: etapa, serviço, modelo, ok/erro, custo estimado
"""

import json
import threading

import streamlit as st

from config import FREE_PROVIDERS, PRICES

SCHEMA = [
    """create table if not exists ep_sessions (
        id bigserial primary key, user_email text, started_at timestamptz default now(),
        ended_at timestamptz, level text, context_label text, summary text)""",
    """create table if not exists ep_turns (
        id bigserial primary key, session_id bigint references ep_sessions(id) on delete cascade,
        ts timestamptz default now(), role text, text text, correction jsonb)""",
    """create table if not exists ep_usage (
        id bigserial primary key, ts timestamptz default now(), user_email text, session_id bigint,
        step text, provider text, model text, ok boolean, input_tokens int, output_tokens int,
        audio_seconds numeric, chars int, latency_ms int, est_cost_usd numeric, error text)""",
    "create index if not exists ep_usage_ts on ep_usage (ts desc)",
    """create table if not exists ep_users (
        email text primary key, name text, active boolean default true, is_admin boolean default false,
        level text, level_locked boolean default false, daily_turns int, live_enabled boolean default false,
        live_daily_minutes int, key_policy jsonb default '{}'::jsonb, keys_enc jsonb default '{}'::jsonb,
        created_at timestamptz default now(), updated_at timestamptz default now())""",
    """create table if not exists ep_exercises (
        level text, num int, topic text, content jsonb, created_at timestamptz default now(),
        primary key (level, num))""",
    """create table if not exists ep_exercise_done (
        id bigserial primary key, user_email text, level text, num int, score int, total int,
        answers jsonb, ts timestamptz default now())""",
    """create table if not exists ep_videos (
        id bigserial primary key, level text, title text, url text, youtube_id text unique,
        notes jsonb, added_by text, created_at timestamptz default now())""",
    """create table if not exists ep_video_done (
        id bigserial primary key, user_email text, video_id bigint references ep_videos(id) on delete cascade,
        score int, total int, answers jsonb, ts timestamptz default now())""",
    "alter table ep_videos add column if not exists position int",
    "alter table ep_videos add column if not exists series text",
    """create table if not exists ep_prefs (
        user_email text, key text, value text, primary key (user_email, key))""",
]

_lock = threading.Lock()


def _url() -> str:
    """Acha o DATABASE_URL no topo dos Secrets ou dentro de qualquer seção (ex.: colado abaixo de [auth])."""
    try:
        if st.secrets.get("DATABASE_URL"):
            return str(st.secrets["DATABASE_URL"])
        for k in st.secrets.keys():
            sec = st.secrets.get(k)
            if hasattr(sec, "get") and sec.get("DATABASE_URL"):
                return str(sec.get("DATABASE_URL"))
    except Exception:
        pass
    return ""


def enabled() -> bool:
    return bool(_url())


@st.cache_resource
def _holder() -> dict:
    return {"conn": None, "schema": False}


def _conn():
    import psycopg

    h = _holder()
    if h["conn"] is None or h["conn"].closed:
        h["conn"] = psycopg.connect(_url(), autocommit=True, connect_timeout=8)
    version = hash(tuple(SCHEMA))  # muda quando o código ganha tabelas novas → cria na hora
    if h["schema"] != version:
        with h["conn"].cursor() as cur:
            for sql in SCHEMA:
                cur.execute(sql)
        h["schema"] = version
    return h["conn"]


def _run(sql: str, params=(), fetch: bool = False):
    """Executa com 1 nova tentativa (o Neon derruba conexões ociosas)."""
    if not enabled():
        return [] if fetch else None
    for attempt in (1, 2):
        try:
            with _lock:
                with _conn().cursor() as cur:
                    cur.execute(sql, params)
                    if fetch:
                        cols = [d.name for d in cur.description]
                        return [dict(zip(cols, r)) for r in cur.fetchall()]
                    return cur.fetchone()[0] if cur.description else None
        except Exception as e:
            _holder()["conn"] = None
            if attempt == 2:
                print(f"[db] falha: {e}", flush=True)
                return [] if fetch else None


# --- custo -----------------------------------------------------------------------
def estimate_cost(provider: str, model: str, input_tokens=0, output_tokens=0,
                  audio_seconds=None, chars=None) -> float:
    if provider in FREE_PROVIDERS:
        return 0.0
    if model in PRICES and isinstance(PRICES[model], tuple):
        pin, pout = PRICES[model]
        return (input_tokens or 0) / 1e6 * pin + (output_tokens or 0) / 1e6 * pout
    per_min = PRICES.get(f"{model}_per_min")
    if per_min:
        if audio_seconds:
            return float(audio_seconds) / 60 * per_min
        if chars:  # fala gerada: ~15 caracteres por segundo
            return chars / 15 / 60 * per_min
    return 0.0


# --- escrita ---------------------------------------------------------------------
def log_usage(user_email: str, session_id, step: str, provider: str, model: str, ok: bool = True,
              input_tokens=None, output_tokens=None, audio_seconds=None, chars=None,
              latency_ms=None, error=None) -> None:
    cost = estimate_cost(provider, model, input_tokens, output_tokens, audio_seconds, chars) if ok else 0.0
    _run("""insert into ep_usage (user_email, session_id, step, provider, model, ok, input_tokens, output_tokens,
                                  audio_seconds, chars, latency_ms, est_cost_usd, error)
            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
         (user_email, session_id, step, provider, model, ok, input_tokens, output_tokens,
          audio_seconds, chars, latency_ms, round(cost, 6), error))


def start_session(user_email: str, level: str, context_label: str):
    return _run("insert into ep_sessions (user_email, level, context_label) values (%s,%s,%s) returning id",
                (user_email, level, context_label))


def add_turn(session_id, role: str, text: str, correction: dict | None = None) -> None:
    if session_id is None:
        return
    _run("insert into ep_turns (session_id, role, text, correction) values (%s,%s,%s,%s)",
         (session_id, role, text, json.dumps(correction) if correction else None))


def end_session(session_id, summary: str | None) -> None:
    if session_id is None:
        return
    _run("update ep_sessions set ended_at = now(), summary = coalesce(%s, summary) where id = %s",
         (summary, session_id))


# --- leitura (tela de uso) ---------------------------------------------------------
def usage_by_provider(user_email: str, days: int = 30) -> list[dict]:
    return _run("""select step as etapa, provider as servico, model as modelo,
                          count(*) filter (where ok) as chamadas, count(*) filter (where not ok) as falhas,
                          round(sum(est_cost_usd)::numeric, 4) as custo_usd
                   from ep_usage where user_email = %s and ts > now() - make_interval(days => %s)
                   group by 1,2,3 order by 1, custo_usd desc, chamadas desc""",
                (user_email, days), fetch=True)


def usage_recent(user_email: str, limit: int = 60) -> list[dict]:
    return _run("""select to_char(ts at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI:SS') as quando,
                          step as etapa, provider as servico, model as modelo, ok,
                          round(est_cost_usd::numeric, 5) as custo_usd, latency_ms as ms, error as erro
                   from ep_usage where user_email = %s order by ts desc limit %s""",
                (user_email, limit), fetch=True)


def sessions_recent(user_email: str, limit: int = 30) -> list[dict]:
    return _run("""select s.id, to_char(s.started_at at time zone 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI') as inicio,
                          s.level as nivel, s.context_label as conversa,
                          (select count(*) from ep_turns t where t.session_id = s.id and t.role = 'user') as falas,
                          (select round(coalesce(sum(u.est_cost_usd),0)::numeric, 4) from ep_usage u
                             where u.session_id = s.id) as custo_usd,
                          s.summary
                   from ep_sessions s where s.user_email = %s order by s.started_at desc limit %s""",
                (user_email, limit), fetch=True)


def session_turns(session_id: int) -> list[dict]:
    return _run("select role, text, correction from ep_turns where session_id = %s order by id",
                (session_id,), fetch=True)


# --- usuários (painel do administrador) -----------------------------------------------
def get_user(email: str) -> dict | None:
    rows = _run("select * from ep_users where lower(email) = lower(%s)", (email,), fetch=True)
    return rows[0] if rows else None


def list_users() -> list[dict]:
    return _run("select * from ep_users order by is_admin desc, email", fetch=True)


def upsert_user(email: str, **fields) -> None:
    fields = {k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in fields.items()}
    cols = ["email"] + list(fields)
    vals = [email.strip().lower()] + list(fields.values())
    sets = ", ".join(f"{c} = excluded.{c}" for c in fields) + ", updated_at = now()"
    _run(f"insert into ep_users ({', '.join(cols)}) values ({', '.join(['%s'] * len(cols))}) "
         f"on conflict (email) do update set {sets}", tuple(vals))


def delete_user(email: str) -> None:
    _run("delete from ep_users where lower(email) = lower(%s)", (email,))


# --- limites do dia (dia de Brasília) ------------------------------------------------------
def turns_today(user_email: str) -> int:
    rows = _run("""select count(*) as n from ep_turns t join ep_sessions s on s.id = t.session_id
                   where s.user_email = %s and t.role = 'user'
                     and (t.ts at time zone 'America/Sao_Paulo')::date = (now() at time zone 'America/Sao_Paulo')::date""",
                (user_email,), fetch=True)
    return int(rows[0]["n"]) if rows else 0


def live_seconds_today(user_email: str) -> float:
    rows = _run("""select coalesce(sum(audio_seconds), 0) as s from ep_usage
                   where user_email = %s and step = 'ao vivo' and ok
                     and (ts at time zone 'America/Sao_Paulo')::date = (now() at time zone 'America/Sao_Paulo')::date""",
                (user_email,), fetch=True)
    return float(rows[0]["s"]) if rows else 0.0


def live_blocked_since_reset(reset_hour_brt: int) -> bool:
    """True se o Gemini Live recusou por cota depois da última renovação (≈5h de Brasília)."""
    rows = _run("""select count(*) as n from ep_usage
                   where step = 'ao vivo' and not ok and error ilike '%%cota%%'
                     and ts > (date_trunc('day', (now() at time zone 'America/Sao_Paulo') - make_interval(hours => %s))
                               + make_interval(hours => %s)) at time zone 'America/Sao_Paulo'""",
                (reset_hour_brt, reset_hour_brt), fetch=True)
    return bool(rows and rows[0]["n"])


def known_users() -> list[str]:
    rows = _run("select distinct user_email from ep_sessions where user_email is not null order by 1", fetch=True)
    return [r["user_email"] for r in rows]


# --- trilha de gramática --------------------------------------------------------------
def get_exercise(level: str, num: int) -> dict | None:
    rows = _run("select topic, content from ep_exercises where level = %s and num = %s", (level, num), fetch=True)
    return rows[0] if rows else None


def save_exercise(level: str, num: int, topic: str, content: dict, replace: bool = False) -> None:
    action = "update set topic = excluded.topic, content = excluded.content, created_at = now()" if replace else "nothing"
    _run("insert into ep_exercises (level, num, topic, content) values (%s,%s,%s,%s) "
         f"on conflict (level, num) do {action}", (level, num, topic, json.dumps(content, ensure_ascii=False)))


def exercise_done(user_email: str, level: str, num: int, score: int, total: int, answers: dict) -> None:
    _run("insert into ep_exercise_done (user_email, level, num, score, total, answers) values (%s,%s,%s,%s,%s,%s)",
         (user_email, level, num, score, total, json.dumps(answers, ensure_ascii=False)))


def exercises_done_map(user_email: str, level: str) -> dict:
    """num -> melhor nota (score, total)."""
    rows = _run("""select num, max(score) as score, max(total) as total from ep_exercise_done
                   where user_email = %s and level = %s group by num""", (user_email, level), fetch=True)
    return {r["num"]: (r["score"], r["total"]) for r in rows}


def exercise_history(user_email: str, limit: int = 100) -> list[dict]:
    return _run("""select to_char(d.ts at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando, d.level as nivel,
                          d.num as exercicio, e.topic as tema, d.score || '/' || d.total as nota
                   from ep_exercise_done d left join ep_exercises e on e.level = d.level and e.num = d.num
                   where d.user_email = %s order by d.ts desc limit %s""", (user_email, limit), fetch=True)


# --- trilha de vídeos -------------------------------------------------------------------
def add_video(level: str, title: str, url: str, youtube_id: str, added_by: str,
              position: int | None = None, series: str | None = None) -> None:
    _run("""insert into ep_videos (level, title, url, youtube_id, added_by, position, series)
            values (%s,%s,%s,%s,%s,%s,%s)
            on conflict (youtube_id) do update set level = excluded.level, title = excluded.title,
              position = coalesce(excluded.position, ep_videos.position), series = coalesce(excluded.series, ep_videos.series)""",
         (level, title, url, youtube_id, added_by, position, series))


def list_videos(level: str | None = None) -> list[dict]:
    if level:
        return _run("select * from ep_videos where level = %s order by series nulls first, position nulls last, id", (level,), fetch=True)
    return _run("select * from ep_videos order by level, series nulls first, position nulls last, id", fetch=True)


def set_video_notes(video_id: int, notes: str, title: str | None = None) -> None:
    _run("update ep_videos set notes = %s::jsonb, title = coalesce(%s, title) where id = %s", (notes, title, video_id))


def delete_video(video_id: int) -> None:
    _run("delete from ep_videos where id = %s", (video_id,))


def video_done(user_email: str, video_id: int, score: int, total: int, answers: dict) -> None:
    _run("insert into ep_video_done (user_email, video_id, score, total, answers) values (%s,%s,%s,%s,%s)",
         (user_email, video_id, score, total, json.dumps(answers, ensure_ascii=False)))


def videos_done_map(user_email: str) -> dict:
    rows = _run("""select video_id, max(score) as score, max(total) as total from ep_video_done
                   where user_email = %s group by video_id""", (user_email,), fetch=True)
    return {r["video_id"]: (r["score"], r["total"]) for r in rows}


def video_history(user_email: str, limit: int = 100) -> list[dict]:
    return _run("""select to_char(d.ts at time zone 'America/Sao_Paulo', 'DD/MM HH24:MI') as quando, v.level as nivel,
                          v.title as video, d.score || '/' || d.total as nota
                   from ep_video_done d join ep_videos v on v.id = d.video_id
                   where d.user_email = %s order by d.ts desc limit %s""", (user_email, limit), fetch=True)


# --- preferências por pessoa (ex.: nome do astronauta no modo infantil) ---------------
def get_pref(user_email: str, key: str) -> str | None:
    rows = _run("select value from ep_prefs where user_email = %s and key = %s", (user_email, key), fetch=True)
    return rows[0]["value"] if rows else None


def set_pref(user_email: str, key: str, value: str) -> None:
    _run("""insert into ep_prefs (user_email, key, value) values (%s,%s,%s)
            on conflict (user_email, key) do update set value = excluded.value""", (user_email, key, value))


def pref_all(key: str) -> dict:
    """{pessoa: valor} de uma preferência para todo mundo (ex.: recorde do desafio, avatar)."""
    rows = _run("select user_email, value from ep_prefs where key = %s", (key,), fetch=True)
    return {r["user_email"]: r["value"] for r in rows}


def week_activity() -> dict:
    """Atividade de todo mundo desde segunda-feira (horário de Brasília), para a Corrida Espacial."""
    wk = "date_trunc('week', now() at time zone 'America/Sao_Paulo') at time zone 'America/Sao_Paulo'"
    ex = _run(f"""select user_email, level, num, max(score) as score, max(total) as total from ep_exercise_done
                  where ts >= {wk} group by user_email, level, num""", fetch=True)
    vids = _run(f"select user_email, count(*) as n from ep_video_done where ts >= {wk} group by user_email", fetch=True)
    talk = _run(f"""select s.user_email, count(t.*) as n from ep_sessions s join ep_turns t on t.session_id = s.id
                    where t.role = 'user' and s.started_at >= {wk} group by s.user_email""", fetch=True)
    return {"exercises": ex, "videos": {r["user_email"]: r["n"] for r in vids},
            "turns": {r["user_email"]: r["n"] for r in talk}}


# --- séries de vídeos (admin) ------------------------------------------------------------
def series_summary() -> list[dict]:
    return _run("""select coalesce(series, 'Avulsos') as series, mode() within group (order by level) as level, count(*) as n
                   from ep_videos group by 1 order by 1""", fetch=True)


def set_series_level(series: str, level: str) -> None:
    _run("update ep_videos set level = %s where coalesce(series, 'Avulsos') = %s", (level, series))


def delete_series(series: str) -> None:
    _run("delete from ep_videos where coalesce(series, 'Avulsos') = %s", (series,))


# --- modo infantil: dias jogados (sequência 🔥 e meta do dia) ---------------------------------
def kid_days(user_email: str, level: str) -> list:
    """Datas (horário de Brasília) em que a pessoa concluiu pelo menos um planeta, da mais recente para a mais antiga."""
    rows = _run("""select distinct (ts at time zone 'America/Sao_Paulo')::date as d from ep_exercise_done
                   where user_email = %s and level = %s order by d desc limit 400""", (user_email, level), fetch=True)
    return [r["d"] for r in rows]


def kid_today_nums(user_email: str, level: str) -> set:
    # só planetas NOVOS de hoje (refazer um planeta antigo não conta no limite do dia)
    rows = _run("""select num from ep_exercise_done where user_email = %s and level = %s group by num
                   having (min(ts) at time zone 'America/Sao_Paulo')::date = (now() at time zone 'America/Sao_Paulo')::date""",
                (user_email, level), fetch=True)
    return {r["num"] for r in rows}


def week_report(user_email: str) -> dict:
    """Resumo dos últimos 7 dias para a família."""
    ex = _run("""select level, num, max(score) as score, max(total) as total, max(ts) as ts from ep_exercise_done
                 where user_email = %s and ts > now() - interval '7 days' group by level, num order by ts""",
              (user_email,), fetch=True)
    vids = _run("""select count(*) as n from ep_video_done where user_email = %s and ts > now() - interval '7 days'""",
                (user_email,), fetch=True)
    talks = _run("""select count(*) as n, coalesce(sum(turns), 0) as turns from (
                      select s.id, count(t.*) filter (where t.role = 'user') as turns from ep_sessions s
                      left join ep_turns t on t.session_id = s.id
                      where s.user_email = %s and s.started_at > now() - interval '7 days' group by s.id) x""",
                 (user_email,), fetch=True)
    return {"exercises": ex, "videos": vids[0]["n"] if vids else 0,
            "talks": talks[0]["n"] if talks else 0, "talk_turns": talks[0]["turns"] if talks else 0}
