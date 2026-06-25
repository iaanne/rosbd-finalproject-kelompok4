from cassandra.cluster import Cluster

CASSANDRA_IP = "100.66.223.98"
KEYSPACE = "dedolarisasi"

try:
    print(f"Menghubungkan ke Cassandra di {CASSANDRA_IP}...")
    cluster = Cluster([CASSANDRA_IP], connect_timeout=10)
    session = cluster.connect(KEYSPACE)
    
    print("\n--- 5 Data Forex Rates Terbaru ---")
    rows = session.execute("SELECT ts, currency_pair, close FROM forex_rates LIMIT 5")
    for r in rows:
        print(f"Timestamp: {r.ts} | Pair: {r.currency_pair} | Close: {r.close}")

    print("\n--- Waktu Terakhir Tiap Currency Pair ---")
    pairs = ["IDR", "THB", "MYR", "SGD", "PHP", "VND", "CNY", "DXY"]
    for p in pairs:
        row = session.execute(f"SELECT ts, close FROM forex_rates WHERE currency_pair='{p}' LIMIT 1")
        rows_list = list(row)
        if rows_list:
            print(f"Pair: {p} | Latest TS: {rows_list[0].ts} | Close: {rows_list[0].close}")
        else:
            print(f"Pair: {p} | Tidak ada data")

    print("\n--- Waktu Terakhir di Tabel Features ---")
    for p in ["IDR", "THB", "MYR", "SGD", "PHP", "VND"]:
        row = session.execute(f"SELECT ts, corr_dxy_20d FROM features WHERE currency_pair='{p}' LIMIT 1")
        rows_list = list(row)
        if rows_list:
            print(f"Pair: {p} | Latest Feature TS: {rows_list[0].ts} | Corr DXY: {rows_list[0].corr_dxy_20d}")
        else:
            print(f"Pair: {p} | Tidak ada data")

    print("\n--- 10 Notifikasi Terbaru (Log Chronological) ---")
    rows_notif = session.execute("SELECT ts, title, message, batch_id FROM notifications WHERE bucket='all' LIMIT 10")
    for r in rows_notif:
        print(f"TS: {r.ts} | Title: {r.title} | Msg: {r.message} | Batch ID: {r.batch_id}")

    print("\n--- 10 Batch ID Terpilih dari Cassandra (Token Order) ---")
    rows_batch = session.execute("SELECT DISTINCT batch_id FROM clustering_results LIMIT 10")
    for r in rows_batch:
        print(f"Batch ID: {r.batch_id}")


except Exception as e:
    print(f"\n[ERROR] Gagal terhubung atau query error: {e}")
