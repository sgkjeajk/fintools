#!/usr/bin/env python3
"""Refresh fintools JSON price histories from Yahoo Finance's chart endpoint."""
import argparse, datetime as dt, json, pathlib, sys, time, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
EPOCH = dt.date(2000, 1, 1)
SPECS = {
    "backtest": ("data/backtest-history.json", {
        "ST Engineering":"S63.SI", "Gold":"GC=F", "S&P 500":"^GSPC",
        "Nasdaq-100":"^NDX", "UOB":"U11.SI", "OCBC":"O39.SI", "DBS":"D05.SI"}),
    "investment": ("data/investment-history.json", {"SPX_DATA":"^GSPC", "NDX_DATA":"^NDX"}),
    "crash": ("data/crash-history.json", {"dbs":"D05.SI", "ocbc":"O39.SI"}),
}
def fetch(symbol, start):
    query = urllib.parse.urlencode({"period1":int(dt.datetime.combine(start,dt.time(),dt.timezone.utc).timestamp()),
        "period2":int(time.time()), "interval":"1d", "events":"history"})
    url = BASE + urllib.parse.quote(symbol, safe="") + "?" + query
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 fintools-history-refresh/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = json.load(response)
    result = ((payload.get("chart") or {}).get("result") or [None])[0]
    error = (payload.get("chart") or {}).get("error")
    if error or not result: raise RuntimeError(f"{symbol}: Yahoo returned no chart data ({error or 'empty result'})")
    quote = (result.get("indicators",{}).get("quote") or [{}])[0]
    timestamps, closes = result.get("timestamp") or [], quote.get("close") or []
    offset = int((result.get("meta") or {}).get("gmtoffset") or 0)
    rows = []
    for stamp, close in zip(timestamps, closes):
        if close is None: continue
        day = dt.datetime.fromtimestamp(int(stamp)+offset,dt.timezone.utc).date().isoformat()
        value = float(close)
        if value > 0: rows.append({"date":day,"close":value})
    rows.sort(key=lambda x:x["date"])
    if len(rows) < 500: raise RuntimeError(f"{symbol}: only {len(rows)} usable daily closes; refusing to replace saved history")
    if len({r["date"] for r in rows}) != len(rows): raise RuntimeError(f"{symbol}: duplicate trading dates")
    return rows
def get_history(cache, symbol):
    if symbol not in cache: cache[symbol] = fetch(symbol, EPOCH)
    return cache[symbol]
def encoded_series(rows):
    days=[]; prices=[]; previous=0
    for row in rows:
        serial=(dt.date.fromisoformat(row["date"])-EPOCH).days
        days.append(serial-previous); prices.append(row["close"]); previous=serial
    return {"d":days,"p":prices}
def market_rows(rows, start, decimals):
    full=[]; peak=0.0
    for r in rows:
        if r["date"] < start: continue
        p=round(r["close"],decimals); peak=max(peak,p)
        full.append({"d":len(full)+1,"dt":r["date"],"p":p,"pk":round(peak,decimals),"dd":round(p/peak-1,6)})
    return full
def refresh_one(key, path, symbols, cache, now):
    file=ROOT/path
    doc=json.loads(file.read_text(encoding="utf-8"))
    if key=="backtest":
        for name,symbol in symbols.items():
            rows=get_history(cache,symbol); doc["series"][name]=encoded_series(rows)
            old=(doc.get("meta") or {}).get(name,{})
            old.update({"file":"Yahoo Finance daily history","rows":len(rows),"first":rows[0]["date"],"last":rows[-1]["date"],
                "reconstructed":0,"holidayRowsRemoved":0,"addedFromScreenshot":0,"provisionalLast":False,"weekend":0,
                "symbol":symbol,"source":"Yahoo Finance chart","retrievedAt":now})
            doc["meta"][name]=old
    elif key=="investment":
        for field,symbol in symbols.items():
            history=get_history(cache,symbol)
            doc[field]=market_rows(history,"2016-01-04",2)
            if not doc[field]: raise RuntimeError(f"{symbol}: no rows from 2016-01-04 onward")
        doc["generated_at"]=now
        doc["source"]="Yahoo Finance chart daily close; peak calculated from full history since 2000-01-01"
    else:
        for asset_id,symbol in symbols.items():
            history=get_history(cache,symbol); asset=doc["assets"][asset_id]
            asset["data"]=market_rows(history,"2000-01-01",4)
            if not asset["data"]: raise RuntimeError(f"{symbol}: no historical rows")
        doc["generated_at"]=now
        doc["source"]="Yahoo Finance chart daily close; dividends excluded"
    tmp=file.with_suffix(file.suffix+".tmp")
    tmp.write_text(json.dumps(doc,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(file)
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--tools",default="all")
    args=parser.parse_args()
    selected=set(SPECS) if args.tools=="all" else set(args.tools.split(","))
    if not selected or not selected.issubset(SPECS): raise SystemExit("tools must be backtest, investment, crash, or a comma-separated combination")
    cache={}; now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    for key in ("backtest","investment","crash"):
        if key in selected:
            path,symbols=SPECS[key]
            print(f"Retrieving {key} history ({len(symbols)} Yahoo symbols)",flush=True)
            refresh_one(key,path,symbols,cache,now)
            print(f"Updated {path}",flush=True)
    print("Refresh complete at "+now)
if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"Refresh failed; keep the prior JSON data. {exc}",file=sys.stderr); raise
