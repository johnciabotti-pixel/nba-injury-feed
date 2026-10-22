import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from nba_injury_report import get_injury_report

FIELDS = ['game_date','team','player','status','reason','matchup','report_asof_et','source']
OUT = Path('data/injuries.csv')


def fetch_latest():
    now = datetime.now(ZoneInfo('America/New_York'))
    # The NBA publishes snapshots each 15 minutes; retry older slots to tolerate publication lag.
    snapped = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    failures=[]
    for n in range(17):
        at = snapped - timedelta(minutes=15*n)
        try:
            report = get_injury_report(at.strftime('%Y-%m-%dT%H:%M:%S'))
            entries = report.to_list()
            if not isinstance(entries, list) or not entries:
                failures.append(f'{at.isoformat()}: empty report')
                continue
            rows=[]
            for e in entries:
                if not isinstance(e, dict):
                    continue
                player = str(e.get('Player Name') or '').strip()
                team = str(e.get('Team') or '').strip()
                status = str(e.get('Current Status') or '').strip()
                if not (player and team and status):
                    continue
                rows.append({
                    'game_date': str(e.get('Game Date') or '').strip(),
                    'team': team,
                    'player': player,
                    'status': status,
                    'reason': str(e.get('Reason') or '').strip(),
                    'matchup': str(e.get('Matchup') or '').strip(),
                    'report_asof_et': at.strftime('%Y-%m-%d %H:%M ET'),
                    'source': 'NBA official injury report',
                })
            if len(rows) < 1:
                failures.append(f'{at.isoformat()}: no valid rows')
                continue
            # Successful fetch replaces CSV atomically. Failed runs preserve previous snapshot.
            OUT.parent.mkdir(parents=True, exist_ok=True)
            temp = OUT.with_suffix('.tmp')
            with temp.open('w', newline='', encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            temp.replace(OUT)
            print(f'Saved {len(rows)} rows from snapshot {at.isoformat()}')
            return
        except Exception as ex:
            failures.append(f'{at.isoformat()}: {type(ex).__name__}: {ex}')
    raise RuntimeError('Unable to retrieve a valid report; existing CSV preserved. Recent attempts: ' + '; '.join(failures[:4]))


if __name__ == '__main__':
    fetch_latest()
