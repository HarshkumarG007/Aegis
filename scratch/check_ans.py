import sqlite3
conn = sqlite3.connect('aegis_eval.db')
c = conn.cursor()
c.execute("SELECT answer FROM evaluation_traces WHERE query_id='sib-004-01' ORDER BY timestamp DESC LIMIT 1")
print(c.fetchall())
