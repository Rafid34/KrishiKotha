import os, sqlite3, sys

def q(db, sql):
    if not os.path.exists(db):
        return ("missing",)
    try:
        return sqlite3.connect(db).execute(sql).fetchone()
    except Exception as e:
        return ("error", str(e))

ev = q("data/krishi_kotha.db",
       "select (select count(*) from risk_snapshots where date between '2022-05-15' and '2022-06-30'),"
       " (select count(distinct date) from observations where source='SMAP_L4' and value is not null"
       " and date between '2022-05-15' and '2022-06-30')")
yr = q("data/cache/validation_2022.db", "select count(*), min(date), max(date) from risk_snapshots")
print("event:", ev, "(ready if (376, 47))")
print("year:", yr, "(ready if (2920, '2022-01-01', '2022-12-31'))")
ok = ev == (376, 47) and yr == (2920, "2022-01-01", "2022-12-31")
print("READY" if ok else "NOT READY")
sys.exit(0 if ok else 1)
