import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests


PLAYLISTS = [
    {
        'playlist_id': '37i9dQZF1E39FJtUzeh2UV',
        'source_url': 'https://open.spotify.com/playlist/37i9dQZF1E39FJtUzeh2UV?si=_zf3vFIMT5y3A2CdbfpPuA'
    },
    {
        'playlist_id': '37i9dQZF1E4wwkchMkSBWv',
        'source_url': 'https://open.spotify.com/playlist/37i9dQZF1E4wwkchMkSBWv?si=leedN1noRZGw2fTD14AyZQ'
    }
]


def load_embed_data(playlist_id):
    url = f'https://open.spotify.com/embed/playlist/{playlist_id}'
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        response.text
    )
    if not match:
        raise RuntimeError(f'playlist data not found: {playlist_id}')
    payload = json.loads(html.unescape(match.group(1)))
    return payload['props']['pageProps']['state']['data']['entity']


def collect_tracks(limit_per_playlist=50):
    rows = []
    collected_at = datetime.now(timezone.utc).isoformat(timespec='seconds')

    for playlist in PLAYLISTS:
        entity = load_embed_data(playlist['playlist_id'])
        tracks = entity['trackList'][:limit_per_playlist]
        if len(tracks) != limit_per_playlist:
            raise RuntimeError(
                f"{playlist['playlist_id']}: expected {limit_per_playlist}, got {len(tracks)}"
            )

        for position, track in enumerate(tracks, start=1):
            preview = track.get('audioPreview') or {}
            track_id = track['uri'].split(':')[-1]
            rows.append({
                'playlist_id': playlist['playlist_id'],
                'playlist_name': entity['name'],
                'playlist_position': position,
                'track_id': track_id,
                'track_name': track['title'],
                'artist_name': track['subtitle'],
                'duration_ms': track['duration'],
                'explicit': track['isExplicit'],
                'spotify_url': f'https://open.spotify.com/track/{track_id}',
                'preview_url': preview.get('url'),
                'source_url': playlist['source_url'],
                'collected_at_utc': collected_at
            })

    raw_df = pd.DataFrame(rows)
    if raw_df['preview_url'].isna().any():
        missing = raw_df.loc[raw_df['preview_url'].isna(), 'track_id'].tolist()
        raise RuntimeError(f'preview missing for: {missing}')
    return raw_df


def make_unique_dataset(raw_df):
    grouped = []
    for _, group in raw_df.groupby('track_id', sort=False):
        row = group.iloc[0].to_dict()
        row['playlist_id'] = ' | '.join(group['playlist_id'].unique())
        row['playlist_name'] = ' | '.join(group['playlist_name'].unique())
        row['playlist_position'] = ' | '.join(
            f"{item.playlist_name}: {item.playlist_position}"
            for item in group.itertuples()
        )
        row['source_url'] = ' | '.join(group['source_url'].unique())
        row['playlist_count'] = int(group['playlist_id'].nunique())
        grouped.append(row)
    return pd.DataFrame(grouped)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()

    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)

    raw_df = collect_tracks(args.limit)
    unique_df = make_unique_dataset(raw_df)

    raw_df.to_csv(data_dir / 'spotify_playlist_tracks_raw.csv', index=False, encoding='utf-8-sig')
    unique_df.to_csv(data_dir / 'music_dataset.csv', index=False, encoding='utf-8-sig')

    playlist_sizes = raw_df.groupby(['playlist_id', 'playlist_name']).size()
    stats = {
        'playlist_rows': int(len(raw_df)),
        'unique_tracks': int(raw_df['track_id'].nunique()),
        'duplicate_positions': int(len(raw_df) - raw_df['track_id'].nunique()),
        'tracks_per_playlist': {
            ' | '.join(key): int(value)
            for key, value in playlist_sizes.items()
        },
        'tracks_with_preview': int(raw_df['preview_url'].notna().sum()),
        'collected_at_utc': raw_df['collected_at_utc'].iloc[0]
    }
    (data_dir / 'dataset_stats.json').write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f'playlist rows: {len(raw_df)}')
    print(f'unique tracks: {len(unique_df)}')
    print(f'duplicate positions: {len(raw_df) - len(unique_df)}')
    print(f'tracks with preview: {raw_df.preview_url.notna().sum()}')


if __name__ == '__main__':
    main()
